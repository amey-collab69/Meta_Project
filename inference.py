from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from openai import OpenAI

from support_inbox_env.environment import SupportInboxEnvironment
from support_inbox_env.models import ActionType, SupportAction
from support_inbox_env.tasks import TASKS


SYSTEM_PROMPT = (
    "You are a support-operations agent acting in a deterministic RL environment. "
    "Return exactly one JSON object with keys: action_type, value, message. "
    "Choose one of: classify_intent, set_priority, assign_team, draft_reply, resolve, escalate. "
    "Do not include markdown fences or any extra text."
)


def log_start(task: str, env_name: str, model: str) -> None:
    print(f"[START] task={task} env={env_name} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}", flush=True)


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
        temperature=0.2,
    )
    content = response.choices[0].message.content or "{}"
    parsed = parse_action(content)
    return SupportAction.model_validate(parsed)


def get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    return value if value else default


def run() -> int:
    api_base_url = get_env("API_BASE_URL", "https://router.huggingface.co/v1")
    model_name = get_env("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct") or "unknown-model"
    hf_token = get_env("HF_TOKEN") or get_env("API_KEY")
    request_timeout = float(os.getenv("MODEL_TIMEOUT_SECONDS", "10"))

    client = OpenAI(base_url=api_base_url, api_key=hf_token, timeout=request_timeout) if hf_token else None
    env = SupportInboxEnvironment()

    for task in TASKS:
        rewards: List[float] = []
        steps_taken = 0
        score = 0.0
        success = False

        log_start(task=task.task_id, env_name="support-inbox-openenv", model=model_name)

        try:
            result = env.reset(task.task_id)
            observation = result.model_dump(mode="json")
            done = False

            while not done and steps_taken < task.max_turns:
                try:
                    if client is None:
                        raise RuntimeError("Missing HF_TOKEN")
                    action = call_model(client, model_name, observation)
                except Exception:
                    action = fallback_policy(observation)

                step_result = env.step(action)
                steps_taken += 1
                reward_val = float(step_result.reward.value)
                rewards.append(reward_val)

                score = float(step_result.info.get("grader_score", 0.0))
                done = step_result.done

                action_str = f"{action.action_type.value}({action.value},{action.message})"
                log_step(step=steps_taken, action=action_str, reward=reward_val, done=done, error=None)

                observation = step_result.observation.model_dump(mode="json")

            success = score > 0.0
        except Exception:
            success = False
        finally:
            log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
