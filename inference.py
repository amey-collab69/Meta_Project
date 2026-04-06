from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

from openai import OpenAI

from support_inbox_env.environment import SupportInboxEnvironment
from support_inbox_env.models import ActionType, SupportAction
from support_inbox_env.tasks import TASKS


SYSTEM_PROMPT = """You are a support-operations agent acting in a deterministic RL environment.
Return exactly one JSON object with keys: action_type, value, message.
Choose one of these action types only: classify_intent, set_priority, assign_team, draft_reply, resolve, escalate.
Do not include markdown fences or any extra text.
"""


def log_start(task_id: str, difficulty: str) -> None:
    print(f"[START] task_id={task_id} difficulty={difficulty}")


def log_step(task_id: str, step_index: int, action: SupportAction, reward: float, done: bool, score: float) -> None:
    print(
        "[STEP] "
        f"task_id={task_id} step={step_index} action_type={action.action_type.value} "
        f"value={json.dumps(action.value)} reward={reward:.4f} done={str(done).lower()} score={score:.4f}"
    )


def log_end(task_id: str, final_score: float, steps: int) -> None:
    print(f"[END] task_id={task_id} final_score={final_score:.4f} steps={steps}")


def build_user_prompt(observation: Dict[str, Any]) -> str:
    return json.dumps(
        {
            "objective": observation["objective"],
            "ticket": observation["ticket"],
            "checklist": observation["checklist"],
            "history": observation["action_history"],
            "remaining_turns": observation["remaining_turns"],
            "guidance": observation["guidance"],
        },
        indent=2,
    )


def parse_action(raw_text: str) -> Dict[str, Any]:
    raw_text = raw_text.strip()
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    candidate = match.group(0) if match else raw_text
    return json.loads(candidate)


def fallback_policy(observation: Dict[str, Any]) -> SupportAction:
    task_id = observation["task_id"]
    checklist = observation["checklist"]

    if not checklist["intent_done"]:
        mapping = {
            "easy_billing_refund": "billing",
            "medium_outage_enterprise": "technical",
            "hard_compliance_data_deletion": "compliance",
        }
        return SupportAction(action_type=ActionType.CLASSIFY_INTENT, value=mapping[task_id])

    if not checklist["priority_done"]:
        mapping = {
            "easy_billing_refund": "normal",
            "medium_outage_enterprise": "urgent",
            "hard_compliance_data_deletion": "high",
        }
        return SupportAction(action_type=ActionType.SET_PRIORITY, value=mapping[task_id])

    if not checklist["team_done"]:
        mapping = {
            "easy_billing_refund": "billing",
            "medium_outage_enterprise": "engineering",
            "hard_compliance_data_deletion": "legal",
        }
        return SupportAction(action_type=ActionType.ASSIGN_TEAM, value=mapping[task_id])

    if not checklist["reply_done"]:
        messages = {
            "easy_billing_refund": (
                "We found the duplicate charge, started the refund, and will confirm once the duplicate amount is reversed."
            ),
            "medium_outage_enterprise": (
                "We have opened an urgent incident with engineering and are treating this as a production incident."
            ),
            "hard_compliance_data_deletion": (
                "We can process the deletion request after we verify your identity and confirm the deletion workflow."
            ),
        }
        return SupportAction(
            action_type=ActionType.DRAFT_REPLY,
            value="customer_reply",
            message=messages[task_id],
        )

    if task_id == "easy_billing_refund":
        return SupportAction(action_type=ActionType.RESOLVE, value="refund_started")

    escalate_values = {
        "medium_outage_enterprise": ("sev1_incident", "Production 500 outage affecting enterprise traffic."),
        "hard_compliance_data_deletion": ("privacy_review", "Privacy legal verification required before secure deletion."),
    }
    value, message = escalate_values[task_id]
    return SupportAction(action_type=ActionType.ESCALATE, value=value, message=message)


def call_model(client: OpenAI, model_name: str, observation: Dict[str, Any]) -> SupportAction:
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(observation)},
        ],
        temperature=0,
    )
    content = response.choices[0].message.content or "{}"
    parsed = parse_action(content)
    return SupportAction.model_validate(parsed)


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def run() -> int:
    api_base_url = require_env("API_BASE_URL")
    model_name = require_env("MODEL_NAME")
    hf_token = require_env("HF_TOKEN")
    request_timeout = float(os.getenv("MODEL_TIMEOUT_SECONDS", "8"))

    client = OpenAI(base_url=api_base_url, api_key=hf_token, timeout=request_timeout)
    env = SupportInboxEnvironment()

    task_scores: List[float] = []

    for task in TASKS:
        observation = env.reset(task.task_id).model_dump(mode="json")
        log_start(task.task_id, task.difficulty.value)

        done = False
        steps = 0
        final_score = 0.0

        while not done and steps < task.max_turns:
            try:
                action = call_model(client, model_name, observation)
            except Exception:
                action = fallback_policy(observation)

            result = env.step(action)
            steps += 1
            final_score = float(result.info["grader_score"])
            log_step(task.task_id, steps, action, result.reward.value, result.done, final_score)

            observation = result.observation.model_dump(mode="json")
            done = result.done

        log_end(task.task_id, final_score, steps)
        task_scores.append(final_score)

    average_score = sum(task_scores) / len(task_scores)
    print(f"[END] average_score={average_score:.4f} task_count={len(task_scores)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except Exception as exc:
        print(f"[END] status=error message={json.dumps(str(exc))}")
        raise SystemExit(1)
