from __future__ import annotations

from typing import Dict, Tuple

from support_inbox_env.models import ActionType, SupportAction, TaskSpec


def _keyword_fraction(text: str, keywords: list[str]) -> float:
    lowered = text.lower()
    if not keywords:
        return 1.0
    hits = sum(1 for keyword in keywords if keyword.lower() in lowered)
    return hits / float(len(keywords))


def evaluate_progress(
    task: TaskSpec,
    latest_values: Dict[ActionType, SupportAction],
) -> Tuple[Dict[str, float], float]:
    reply_action = latest_values.get(ActionType.DRAFT_REPLY)
    final_action = latest_values.get(ActionType.RESOLVE) or latest_values.get(ActionType.ESCALATE)

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
        "reply": _keyword_fraction(reply_action.message if reply_action else "", task.required_reply_keywords),
        "final_action": 0.0,
    }

    if final_action:
        if task.final_action == "resolve" and final_action.action_type == ActionType.RESOLVE:
            components["final_action"] = 1.0 if final_action.value == task.resolution_value else 0.5
        elif task.final_action == "escalate" and final_action.action_type == ActionType.ESCALATE:
            note_score = _keyword_fraction(final_action.message, task.escalation_note_keywords)
            value_score = 1.0 if final_action.value == task.resolution_value else 0.5
            components["final_action"] = round((note_score + value_score) / 2.0, 4)
        else:
            components["final_action"] = 0.0

    total_score = round(sum(components.values()) / float(len(components)), 4)
    return components, total_score
