"""
SupportAI-Env — Deterministic Grader
Scores agent performance: strictly between 0 and 1 (not 0.0 or 1.0)
"""

from typing import List


def grade_easy(state: dict) -> float:
    """Grade easy task - returns score strictly between 0 and 1."""
    # Simple scoring based on resolution
    if state.get("resolved", False):
        return 0.75
    elif state.get("partial_progress", False):
        return 0.45
    else:
        return 0.20


def grade_medium(state: dict) -> float:
    """Grade medium task - returns score strictly between 0 and 1."""
    # Medium difficulty scoring
    if state.get("resolved", False):
        return 0.70
    elif state.get("partial_progress", False):
        return 0.50
    else:
        return 0.25


def grade_hard(state: dict) -> float:
    """Grade hard task - returns score strictly between 0 and 1."""
    # Hard difficulty scoring
    if state.get("resolved", False):
        return 0.65
    elif state.get("partial_progress", False):
        return 0.40
    else:
        return 0.15


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

    # Map to task scoring thresholds (ensure strictly between 0 and 1)
    if score >= 0.85:
        label = "full"
        final_score = min(0.99, max(0.01, scoring["full_score"]))
    elif score >= 0.40:
        label = "partial"
        final_score = max(0.01, min(0.99, scoring["partial_score"]))
    else:
        label = "fail"
        final_score = max(0.01, min(0.99, scoring["fail_score"]))

    # Use task-specific grader if available
    task_id = task.get("id", "")
    if task_id == "easy":
        final_score = grade_easy({"resolved": resolved, "partial_progress": score >= 0.40})
    elif task_id == "medium":
        final_score = grade_medium({"resolved": resolved, "partial_progress": score >= 0.40})
    elif task_id == "hard":
        final_score = grade_hard({"resolved": resolved, "partial_progress": score >= 0.40})

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
