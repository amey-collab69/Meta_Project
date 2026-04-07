import os
from typing import Optional

import requests
from openai import OpenAI

# Environment variables ONLY — no defaults, no fallbacks
API_BASE_URL = os.environ.get("API_BASE_URL")
API_KEY = os.environ.get("API_KEY")
ENV_URL = "http://localhost:7860"
MODEL_NAME = "gpt-4o-mini"
BENCHMARK = "supportai-env"
TASK_IDS = ["easy", "medium", "hard"]
TASK_MAX_STEPS = {"easy": 4, "medium": 6, "hard": 8}


def format_bool(value: bool) -> str:
    return "true" if value else "false"


def safe_str(value: Optional[str]) -> str:
    return value if value else "null"


def make_client():
    """Create OpenAI client pointing to proxy. Returns None if env vars missing."""
    import os
    from openai import OpenAI

    base_url = os.environ.get("API_BASE_URL")
    api_key = os.environ.get("API_KEY")

    if not base_url or not api_key:
        return None

    return OpenAI(base_url=base_url, api_key=api_key)


def choose_action_with_llm(client, customer_msg, state):
    """Call LLM to choose action and content via proxy. Falls back gracefully if client is None or call fails."""
    if not client:
        return "reply", "I'm here to help."

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Respond with ACTION and CONTENT."},
                {"role": "user", "content": f"Customer: {customer_msg}\nState: {state}"}
            ],
            max_tokens=100,
            temperature=0.7,
        )

        text = response.choices[0].message.content.strip()

        action = "reply"
        content = "I'm here to help."

        for line in text.split("\n"):
            if line.startswith("ACTION:"):
                action = line.split(":", 1)[1].strip().lower()
            elif line.startswith("CONTENT:"):
                content = line.split(":", 1)[1].strip()

        return action, content

    except Exception:
        return "reply", "Let me assist you."


def run_task(task_id: str, client: OpenAI) -> None:
    """Run task and emit [START], [STEP], [END] format."""
    print(f"[START] task={task_id} env={BENCHMARK} model={MODEL_NAME}", flush=True)

    session_id = None
    steps = []
    rewards = []

    try:
        # Reset
        reset_resp = requests.post(
            f"{ENV_URL}/reset",
            json={"task_id": task_id},
            timeout=15,
        )
        reset_resp.raise_for_status()
        obs = reset_resp.json()
        session_id = obs.get("session_id")

        max_steps = TASK_MAX_STEPS.get(task_id, 8)

        # Run episode
        for step_num in range(1, max_steps + 1):
            customer_msg = obs.get("observation", {}).get("customer_message", "")
            state = obs.get("observation", {}).get("current_state", "")

            # Call LLM via proxy
            action_type, content = choose_action_with_llm(client, customer_msg, state)

            # Execute step
            step_resp = requests.post(
                f"{ENV_URL}/step",
                json={
                    "session_id": session_id,
                    "action_type": action_type,
                    "content": content,
                },
                timeout=15,
            )
            step_resp.raise_for_status()
            obs = step_resp.json()

            reward = float(obs.get("reward", 0.0))
            done = bool(obs.get("done", False))
            info = obs.get("info", {}) or {}
            error = safe_str(info.get("error"))

            steps.append(action_type)
            rewards.append(reward)

            print(
                f"[STEP] step={step_num} action={action_type} reward={reward:.2f} done={format_bool(done)} error={error}",
                flush=True,
            )

            if done:
                break

        # Final score
        if rewards:
            score = sum(rewards) / len(rewards)
            score = max(0.01, min(0.99, score))
        else:
            score = 0.01

        success = score >= 0.50

        rewards_str = ",".join(f"{r:.2f}" for r in rewards) if rewards else "0.01"
        print(
            f"[END] success={format_bool(success)} steps={len(steps)} score={score:.2f} rewards={rewards_str}",
            flush=True,
        )

    except Exception as e:
        print(
            f"[STEP] step=1 action=none reward=0.01 done=false error={safe_str(str(e))}",
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
