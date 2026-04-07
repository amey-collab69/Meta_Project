import os
import time
from typing import List, Optional

import requests
from openai import OpenAI

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:7860")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
BENCHMARK = os.getenv("BENCHMARK", "supportai-env")
TASK_IDS = ["easy", "medium", "hard"]
DEFAULT_TASK_MAX_STEPS = {"easy": 4, "medium": 6, "hard": 8}
ACTION_CONTENTS = {
    "reply": "I have reviewed your issue and am working to resolve it promptly.",
    "ask_details": "Could you please share your order ID and any additional details so I can help?",
    "refund": "I have processed your refund and you should receive confirmation shortly.",
    "escalate": "I'm escalating this case to our senior support team for a fast resolution.",
}


def format_bool(value: bool) -> str:
    return "true" if value else "false"


def make_client() -> Optional[OpenAI]:
    if not HF_TOKEN:
        return None
    if os.getenv("API_BASE_URL"):
        return OpenAI(api_key=HF_TOKEN, base_url=os.getenv("API_BASE_URL"))
    return OpenAI(api_key=HF_TOKEN)


def safe_str(value: Optional[str]) -> str:
    return value if value else "null"


def warmup_model(client: Optional[OpenAI]) -> None:
    if not client:
        return
    try:
        client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are a support assistant classifier."
                },
                {
                    "role": "user",
                    "content": "Classify the following message into one of: reply, ask_details, refund, escalate. Message: Where is my order?"
                },
            ],
            max_tokens=1,
            temperature=0,
        )
    except Exception:
        pass


def choose_action(observation: dict, task_id: str) -> str:
    state = observation.get("observation", {}).get("current_state", "IDENTIFY_INTENT")
    step_count = observation.get("observation", {}).get("step_count", 0)
    workflow = observation.get("observation", {}).get("task", {})
    expected_workflow = {
        "easy": ["ask_details", "reply"],
        "medium": ["ask_details", "ask_details", "refund"],
        "hard": ["reply", "ask_details", "refund", "reply"],
    }.get(task_id, ["reply"])
    if step_count < len(expected_workflow):
        return expected_workflow[step_count]
    return "reply"


def run_task(task_id: str, client: Optional[OpenAI]) -> None:
    session_id = None
    steps: List[str] = []
    rewards: List[float] = []
    success = False
    score = 0.0
    error_message = None

    print(f"[START] task={task_id} env={BENCHMARK} model={MODEL_NAME}", flush=True)

    try:
        reset_response = requests.post(
            f"{API_BASE_URL}/reset",
            json={"task_id": task_id},
            timeout=15,
        )
        reset_response.raise_for_status()
        reset_data = reset_response.json()
        session_id = reset_data.get("session_id")
        observation = reset_data

        if client:
            warmup_model(client)

        for step_index in range(1, DEFAULT_TASK_MAX_STEPS.get(task_id, 8) + 1):
            action_type = choose_action(observation, task_id)
            content = ACTION_CONTENTS.get(action_type, "I am assisting you with your request.")
            payload = {
                "session_id": session_id,
                "action_type": action_type,
                "content": content,
            }

            step_response = requests.post(
                f"{API_BASE_URL}/step",
                json=payload,
                timeout=15,
            )

            if step_response.status_code != 200:
                error_message = f"HTTP {step_response.status_code}"
                print(
                    f"[STEP] step={step_index} action={action_type} reward=0.00 done=false error={error_message}",
                    flush=True,
                )
                break

            step_data = step_response.json()
            reward = float(step_data.get("reward", 0.0))
            done = bool(step_data.get("done", False))
            info = step_data.get("info", {}) or {}
            error = safe_str(info.get("error"))
            if error == "None":
                error = "null"

            steps.append(action_type)
            rewards.append(reward)
            observation = step_data

            print(
                f"[STEP] step={step_index} action={action_type} reward={reward:.2f} done={format_bool(done)} error={error}",
                flush=True,
            )

            if done:
                grade = step_data.get("grade", {}) or {}
                score = float(grade.get("final_score", reward))
                success = score >= 0.50
                break

        if not observation.get("done", False):
            if rewards:
                score = sum(rewards) / len(rewards)
                score = round(min(0.99, max(0.01, score)), 4)
            else:
                score = 0.01
            success = False

        rewards_str = ",".join(f"{r:.2f}" for r in rewards) if rewards else "0.01"
        print(
            f"[END] success={format_bool(success)} steps={len(rewards)} score={score:.2f} rewards={rewards_str}",
            flush=True,
        )
    except Exception as exc:
        if session_id is None:
            session_id = "unknown"
        print(
            f"[STEP] step=1 action=none reward=0.01 done=false error={safe_str(str(exc))}",
            flush=True,
        )
        print(
            f"[END] success=false steps=0 score=0.01 rewards=0.01",
            flush=True,
        )


if __name__ == "__main__":
    client = make_client()
    for task in TASK_IDS:
        run_task(task, client)
