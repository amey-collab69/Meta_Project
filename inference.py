import os
import time
from typing import List, Optional

import requests
from openai import OpenAI

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:7860")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
API_KEY = os.getenv("API_KEY") or os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY")
BENCHMARK = os.getenv("BENCHMARK", "supportai-env")
TASK_IDS = ["easy", "medium", "hard"]
DEFAULT_TASK_MAX_STEPS = {"easy": 4, "medium": 6, "hard": 8}


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


def make_client() -> Optional[OpenAI]:
    """Initialize OpenAI client with proxy if available."""
    if not API_KEY:
        return None
    # Use API_BASE_URL as proxy if set, otherwise use default OpenAI
    if API_BASE_URL and API_BASE_URL != "http://localhost:7860":
        try:
            return OpenAI(api_key=API_KEY, base_url=API_BASE_URL)
        except Exception:
            pass
    return OpenAI(api_key=API_KEY)


def generate_action_with_llm(client: Optional[OpenAI], observation: dict, step_index: int) -> tuple:
    """Use LLM to generate action type and content via proxy.
    Returns: (action_type, content)
    """
    if not client:
        return ("reply", "I'm here to help resolve your issue.")
    
    try:
        customer_msg = observation.get("observation", {}).get("customer_message", "")
        current_state = observation.get("observation", {}).get("current_state", "IDENTIFY_INTENT")
        
        prompt = f"""You are a customer support agent. Based on the customer message and current state, 
determine the BEST action to take.

Customer message: {customer_msg}
Current state: {current_state}
Step #{step_index}

Available actions: reply, ask_details, refund, escalate

Respond with exactly:
ACTION: <action_type>
CONTENT: <brief response message>"""
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are a customer support decision-maker. Respond with ACTION and CONTENT lines."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=100,
            temperature=0.7,
        )
        
        llm_response = response.choices[0].message.content.strip()
        
        # Parse response
        action_type = "reply"
        content = "I'm working to resolve your issue."
        
        for line in llm_response.split("\n"):
            if line.startswith("ACTION:"):
                action_type = line.replace("ACTION:", "").strip().lower()
                if action_type not in ("reply", "ask_details", "refund", "escalate"):
                    action_type = "reply"
            elif line.startswith("CONTENT:"):
                content = line.replace("CONTENT:", "").strip()
        
        return (action_type, content)
    
    except Exception as e:
        # Fallback to default action
        return ("reply", f"I'm here to help. (Error: {str(e)[:30]})")


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
            # Use LLM to generate action via proxy
            action_type, content = generate_action_with_llm(client, observation, step_index)
            
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
