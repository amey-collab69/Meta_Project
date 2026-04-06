"""
SupportAI-Env — Inference Script
Uses OpenAI API to run baseline agent across all 3 tasks.
Output format (EXACT):
[START] task=<id> env=support model=<model>
[STEP] step=<n> action=<act> reward=<r> done=<bool> error=<null|msg>
[END] success=<bool> steps=<n> score=<s> rewards=<r1,r2,...>
"""

import os
import json
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI
from env import SupportEnv, Action
from tasks import TASKS
from grader import grade

MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
VALID_ACTIONS = ["reply", "refund", "escalate", "ask_details"]


def build_system_prompt() -> str:
    return (
        "You are an AI customer support agent operating inside SupportAI-Env. "
        "Your job is to resolve customer issues by choosing the correct action at each step. "
        "Available actions: reply, ask_details, refund, escalate. "
        "Respond with ONLY a JSON object: {\"action\": \"<action>\", \"content\": \"<optional message>\"}. "
        "No extra text. No markdown."
    )


def build_user_prompt(obs: dict, step: int) -> str:
    return (
        f"Step {step}. Current state: {obs['current_state']}. "
        f"Customer message: \"{obs['customer_message']}\". "
        f"Intent: {obs['intent']}. Tone: {obs['sentiment']}. "
        f"History length: {len(obs['conversation_history'])}. "
        "Choose the best action."
    )


def run_task(task_id: str, client: OpenAI) -> dict:
    task = TASKS[task_id]
    env = SupportEnv(task)
    obs = env.reset()

    rewards = []
    step = 0
    done = False
    lines = []

    lines.append(f"[START] task={task_id} env=support model={MODEL}")

    while not done and step < task.get("max_steps", 10):
        step += 1
        obs_dict = obs.model_dump()

        # LLM decides action (baseline agent)
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": build_system_prompt()},
                    {"role": "user", "content": build_user_prompt(obs_dict, step)},
                ],
                max_tokens=80,
                temperature=0,
            )
            raw = response.choices[0].message.content.strip()
            parsed = json.loads(raw)
            action_type = parsed.get("action", "reply")
            content = parsed.get("content", "")
            if action_type not in VALID_ACTIONS:
                action_type = "reply"
        except Exception as e:
            action_type = "reply"
            content = ""

        action = Action(action_type=action_type, content=content)
        obs, reward, done, info = env.step(action)
        rewards.append(reward)

        error_val = info.get("error") or "null"
        lines.append(
            f"[STEP] step={step} action={action_type} "
            f"reward={reward:.2f} done={str(done).lower()} error={error_val}"
        )

    # Grade
    final_obs = env.state()
    grade_result = grade(
        task=task,
        action_history=env._action_history,
        total_reward=env.total_reward(),
        final_state=final_obs.current_state,
        step_count=final_obs.step_count,
        intent_detected=final_obs.intent,
        tone=final_obs.sentiment,
    )

    success = grade_result["label"] in ("full", "partial")
    score = grade_result["final_score"]
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)

    lines.append(
        f"[END] success={str(success).lower()} steps={step} "
        f"score={score:.2f} rewards={rewards_str}"
    )

    return {
        "task_id": task_id,
        "lines": lines,
        "grade": grade_result,
        "success": success,
    }


def main():
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        print("WARNING: OPENAI_API_KEY not set. Using fallback tone detection.")

    client = OpenAI(api_key=api_key) if api_key else None

    results = []
    for task_id in ["easy", "medium", "hard"]:
        print(f"\n{'='*50}")
        if client:
            result = run_task(task_id, client)
        else:
            # No API key: run with deterministic fallback (no LLM calls)
            result = run_task_no_llm(task_id)

        for line in result["lines"]:
            print(line)
        results.append(result)

    print(f"\n{'='*50}")
    print("SUMMARY")
    for r in results:
        g = r["grade"]
        print(f"  {r['task_id']:8s} | score={g['final_score']} | label={g['label']} | steps={g['steps']}")


def run_task_no_llm(task_id: str) -> dict:
    """Deterministic fallback when no OpenAI key is available."""
    task = TASKS[task_id]
    env = SupportEnv(task)
    obs = env.reset()

    workflow = task.get("expected_workflow", ["reply"])
    rewards = []
    step = 0
    done = False
    lines = []

    lines.append(f"[START] task={task_id} env=support model=deterministic-fallback")

    wi = 0
    while not done and step < task.get("max_steps", 10):
        step += 1
        action_type = workflow[wi] if wi < len(workflow) else "reply"
        wi += 1

        action = Action(action_type=action_type, content="")
        obs, reward, done, info = env.step(action)
        rewards.append(reward)

        error_val = info.get("error") or "null"
        lines.append(
            f"[STEP] step={step} action={action_type} "
            f"reward={reward:.2f} done={str(done).lower()} error={error_val}"
        )

    final_obs = env.state()
    grade_result = grade(
        task=task,
        action_history=env._action_history,
        total_reward=env.total_reward(),
        final_state=final_obs.current_state,
        step_count=final_obs.step_count,
        intent_detected=final_obs.intent,
        tone=final_obs.sentiment,
    )

    success = grade_result["label"] in ("full", "partial")
    score = grade_result["final_score"]
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)

    lines.append(
        f"[END] success={str(success).lower()} steps={step} "
        f"score={score:.2f} rewards={rewards_str}"
    )

    return {"task_id": task_id, "lines": lines, "grade": grade_result, "success": success}


if __name__ == "__main__":
    main()
