"""
SupportAI-Env — Deterministic Grader
Scores agent performance: 0.0 → 1.0
"""

from typing import List

_EPS = 1e-4


def _strict_unit_interval(value: float, eps: float = _EPS) -> float:
    """
    Clamp to the open interval (0, 1) to satisfy strict validator requirements.
    """
    if value <= 0.0:
        return eps
    if value >= 1.0:
        return 1.0 - eps
    return value


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
    Deterministic grader. Returns score 0.0–1.0 with breakdown.
    """
    expected_workflow = task.get("expected_workflow", [])
    expected_intent = task.get("expected_intent", "any")
    max_steps = task.get("max_steps", 10)
    scoring = task.get("scoring", {"full_score": 1.0, "partial_score": 0.5, "fail_score": 0.0})

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

    score = round(min(1.0, max(0.0, score)), 4)
    score_strict = round(_strict_unit_interval(score), 4)

    # Map to task scoring thresholds
    if score >= 0.85:
        label = "full"
        final_score = scoring["full_score"]
    elif score >= 0.40:
        label = "partial"
        final_score = scoring["partial_score"]
    else:
        label = "fail"
        final_score = scoring["fail_score"]

    final_score = round(_strict_unit_interval(float(final_score)), 4)

    return {
        "raw_score": score_strict,
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
