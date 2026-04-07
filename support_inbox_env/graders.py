from __future__ import annotations

from typing import Dict, Tuple

from support_inbox_env.models import ActionType, SupportAction, TaskSpec

MIN_TASK_SCORE = 0.01
MAX_TASK_SCORE = 0.99


def _keyword_fraction(text: str, keywords: list[str]) -> float:
    lowered = text.lower()
    if not keywords:
        return 1.0
    hits = sum(1 for keyword in keywords if keyword.lower() in lowered)
    return hits / float(len(keywords))


def _latest_text(latest_values: Dict[ActionType, SupportAction], action_type: ActionType) -> str:
    action = latest_values.get(action_type)
    if not action:
        return ""
    return " ".join(part for part in [action.value, action.message] if part).strip()


def _normalize_task_score(raw_score: float) -> float:
    raw_score = max(0.0, min(1.0, raw_score))
    scaled = MIN_TASK_SCORE + raw_score * (MAX_TASK_SCORE - MIN_TASK_SCORE)
    return round(scaled, 4)


def evaluate_progress(
    task: TaskSpec,
    latest_values: Dict[ActionType, SupportAction],
    status_history: list[str],
) -> Tuple[Dict[str, float], float]:
    reply_action = latest_values.get(ActionType.DRAFT_REPLY)
    final_action = latest_values.get(ActionType.RESOLVE) or latest_values.get(ActionType.ESCALATE)
    note_text = _latest_text(latest_values, ActionType.ADD_INTERNAL_NOTE)
    info_text = _latest_text(latest_values, ActionType.REQUEST_MORE_INFO)
    refund_action = latest_values.get(ActionType.APPLY_REFUND)

    components = {
        "intent": 1.0
        if latest_values.get(ActionType.CLASSIFY_INTENT, SupportAction(action_type=ActionType.CLASSIFY_INTENT)).value
        == task.expected_intent
        else 0.0,
        "priority": 1.0
        if latest_values.get(ActionType.SET_PRIORITY, SupportAction(action_type=ActionType.SET_PRIORITY)).value
        == task.expected_priority
        else 0.0,
        "team": 1.0
        if latest_values.get(ActionType.ASSIGN_TEAM, SupportAction(action_type=ActionType.ASSIGN_TEAM)).value
        == task.expected_team
        else 0.0,
        "internal_note": _keyword_fraction(note_text, task.required_internal_note_keywords),
        "status_flow": 0.0,
        "reply": _keyword_fraction(reply_action.message if reply_action else "", task.required_reply_keywords),
        "policy": 1.0,
        "final_action": 0.0,
    }

    if task.expected_status_flow:
        matched = sum(1 for status in task.expected_status_flow if status in status_history)
        components["status_flow"] = matched / float(len(task.expected_status_flow))

    if "identity_verification_required" in task.policy_flags:
        components["policy"] = _keyword_fraction(info_text or (reply_action.message if reply_action else ""), task.required_more_info_keywords)

    if "do_not_resolve_enterprise_outage" in task.policy_flags:
        if latest_values.get(ActionType.RESOLVE):
            components["policy"] = 0.0

    if "do_not_auto_refund_possible_fraud" in task.policy_flags:
        if refund_action or latest_values.get(ActionType.RESOLVE):
            components["policy"] = 0.0

    if task.required_refund_amount:
        if refund_action:
            components["policy"] = min(
                1.0,
                round((components["policy"] + (1.0 if refund_action.value == task.required_refund_amount else 0.0)) / 2.0, 4),
            )
        else:
            components["policy"] = 0.0

    if final_action:
        if task.final_action == "resolve" and final_action.action_type == ActionType.RESOLVE:
            components["final_action"] = 1.0 if final_action.value == task.resolution_value else 0.5
        elif task.final_action == "escalate" and final_action.action_type == ActionType.ESCALATE:
            note_score = _keyword_fraction(final_action.message, task.escalation_note_keywords)
            value_score = 1.0 if final_action.value == task.resolution_value else 0.5
            components["final_action"] = round((note_score + value_score) / 2.0, 4)
        else:
            components["final_action"] = 0.0

    total_score = _normalize_task_score(sum(components.values()) / float(len(components)))
    return components, total_score
