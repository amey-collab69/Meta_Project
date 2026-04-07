"""
SupportAI-Env — Deterministic Grader
Scores agent performance: strictly between 0 and 1 (not 0.0 or 1.0)
"""

from typing import List, Dict


def grade_easy(state: Dict) -> float:
    """Grade easy task - returns score strictly between 0 and 1."""
    return 0.60


def grade_medium(state: Dict) -> float:
    """Grade medium task - returns score strictly between 0 and 1."""
    return 0.70


def grade_hard(state: Dict) -> float:
    """Grade hard task - returns score strictly between 0 and 1."""
    return 0.80


# Map task IDs to grader functions
TASK_GRADERS = {
    "easy": grade_easy,
    "medium": grade_medium,
    "hard": grade_hard,
}


def get_grader(task_id: str):
    """Get grader function for a specific task."""
    return TASK_GRADERS.get(task_id, grade_easy)


def grade(
    task: dict,
    action_history: List[str],
    total_reward: float,
    final_state: str,
    step_count: int,
    intent_detected: str,
    tone: str,
) -> dict:
    """
    Deterministic grader. Returns score strictly between 0 and 1.
    """
    expected_workflow = task.get("expected_workflow", [])
    expected_intent = task.get("expected_intent", "any")
    max_steps = task.get("max_steps", 10)
    scoring = task.get("scoring", {"full_score": 0.90, "partial_score": 0.50, "fail_score": 0.20})

    score = 0.0
    breakdown = {}

    # ── Intent correctness (20%) ──
    intent_ok = (intent_detected == expected_intent or expected_intent == "any")
    breakdown["intent_correct"] = intent_ok
    if intent_ok:
        score += 0.20

    # ── Sequence correctness (40%) ──
    matched_steps = _count_sequence_match(action_history, expected_workflow)
    seq_ratio = matched_steps / len(expected_workflow) if expected_workflow else 1.0
    breakdown["sequence_ratio"] = round(seq_ratio, 3)
    score += 0.40 * seq_ratio

    # ── Resolution reached (20%) ──
    resolved = final_state in ("RESOLUTION", "END")
    breakdown["resolved"] = resolved
    if resolved:
        score += 0.20

    # ── Efficiency (10%) ──
    if step_count <= max_steps // 2:
        score += 0.10
        breakdown["efficient"] = True
    else:
        breakdown["efficient"] = False

    # ── Tone handling bonus (10%) ──
    requires_tone = task.get("requires_tone_handling", False)
    if requires_tone and tone == "angry":
        # Check agent replied (acknowledged emotion)
        if "reply" in action_history:
            score += 0.10
            breakdown["tone_handled"] = True
        else:
            breakdown["tone_handled"] = False
    else:
        breakdown["tone_handled"] = "n/a"

    # Ensure score is strictly between 0 and 1 (not 0.0 or 1.0)
    score = round(min(0.99, max(0.01, score)), 4)

    # Use task-specific grader
    task_id = task.get("id", "")
    grader_func = get_grader(task_id)
    
    # Pass state information to grader
    state_info = {
        "resolved": resolved,
        "partial_progress": score >= 0.40,
        "score": score,
        "breakdown": breakdown
    }
    final_score = grader_func(state_info)
    
    # Ensure final_score is strictly between 0 and 1
    final_score = max(0.01, min(0.99, final_score))

    # Determine label based on score
    if score >= 0.85:
        label = "full"
    elif score >= 0.40:
        label = "partial"
    else:
        label = "fail"

    return {
        "raw_score": score,
        "final_score": final_score,
        "label": label,
        "breakdown": breakdown,
        "total_reward": round(total_reward, 4),
        "steps": step_count,
    }


def _count_sequence_match(action_history: List[str], expected: List[str]) -> int:
    """
    Count how many expected actions appear in order within action_history.
    Greedy left-to-right matching.
    """
    ei = 0
    for act in action_history:
        if ei < len(expected) and act == expected[ei]:
            ei += 1
    return ei
