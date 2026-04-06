---
title: TechmasterMeta
emoji: "🚀"
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Support Inbox OpenEnv

`support-inbox-openenv` is a real-world OpenEnv environment where an agent learns to triage customer support tickets. The agent must inspect a ticket, classify the issue, assign a priority, route it to the correct team, and choose whether to resolve or escalate the case with a helpful reply.

The environment is deterministic and designed for hackathon-style evaluation:

- 3 built-in tasks with easy, medium, and hard difficulty
- Typed observation, action, reward, and response models
- Partial-progress rewards across a full trajectory
- Deterministic graders that return scores in the `0.0` to `1.0` range
- FastAPI server with `reset()`, `step()`, and `state()` endpoints
- Root-level `inference.py` that uses the OpenAI client with OpenAI-compatible APIs
- Dockerfile ready for Hugging Face Spaces

## Environment Concept

This environment simulates a support operations workflow that humans perform every day:

1. Read an inbound customer ticket.
2. Identify the intent.
3. Set an appropriate priority.
4. Route the case to the right team.
5. Draft a response.
6. Resolve or escalate the issue.

This makes the environment more realistic than a toy classification benchmark because the agent must produce a correct sequence of actions and avoid unsafe final decisions.

## Action Space

The action model is `SupportAction` with the following fields:

- `action_type`: one of `classify_intent`, `set_priority`, `assign_team`, `draft_reply`, `resolve`, `escalate`
- `value`: primary action value, such as `billing`, `urgent`, or `engineering`
- `message`: optional free-text response or escalation note

Example:

```json
{
  "action_type": "assign_team",
  "value": "billing"
}
```

## Observation Space

The observation model is `SupportObservation` and includes:

- task metadata
- the current ticket
- current progress checklist
- history of previous actions
- remaining turn budget
- available actions

## Reward Design

The reward model is `SupportReward` with:

- `value`: normalized step reward in `0.0` to `1.0`
- `components`: per-criterion completion information
- `reasoning`: short explanation of what changed this step

Rewards are based on incremental progress toward the task rubric:

- correct intent classification
- correct priority
- correct team assignment
- useful reply quality
- correct final disposition

Repeated or conflicting actions reduce incremental reward.

## Tasks

### `easy_billing_refund`

- Difficulty: easy
- Scenario: customer requests a duplicate charge refund
- Goal: classify as billing, route to billing, set normal priority, send a refund-oriented reply, resolve correctly

### `medium_outage_enterprise`

- Difficulty: medium
- Scenario: enterprise customer reports a production outage
- Goal: classify as technical, assign urgent priority, route to engineering, send a careful incident reply, escalate instead of resolving

### `hard_compliance_data_deletion`

- Difficulty: hard
- Scenario: customer requests data deletion with legal sensitivity
- Goal: classify as compliance, assign high priority, route to legal, include identity-verification language in the reply, escalate for secure handling

## Project Layout

```text
.
├── Dockerfile
├── inference.py
├── openenv.yaml
├── requirements.txt
├── server/
│   ├── __init__.py
│   └── app.py
└── support_inbox_env/
    ├── __init__.py
    ├── client.py
    ├── environment.py
    ├── graders.py
    ├── models.py
    └── tasks.py
```

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

## API Usage

Reset the environment:

```bash
curl -X POST http://127.0.0.1:7860/reset
```

Take a step:

```bash
curl -X POST http://127.0.0.1:7860/step \
  -H "Content-Type: application/json" \
  -d '{"action_type":"classify_intent","value":"billing"}'
```

Inspect state:

```bash
curl http://127.0.0.1:7860/state
```

## Inference Script

The root `inference.py` script uses the OpenAI Python client against any OpenAI-compatible endpoint.

Expected environment variables:

- `API_BASE_URL`
- `MODEL_NAME`
- `HF_TOKEN`

Run:

```bash
API_BASE_URL="https://your-openai-compatible-endpoint/v1" \
MODEL_NAME="your-model" \
HF_TOKEN="your-token" \
python3 inference.py
```

The script emits structured logs with `[START]`, `[STEP]`, and `[END]` tags for each task and prints a final average score.

## Docker

Build and run:

```bash
docker build -t support-inbox-openenv .
docker run -p 7860:7860 support-inbox-openenv
```

## Baseline Notes

Because baseline scores depend on the selected external model endpoint, exact scores will vary. The included prompt and deterministic fallback parser are designed to produce stable action sequences when run with a temperature-minimized OpenAI-compatible model.

## Submission Checklist

- `openenv.yaml` present
- FastAPI app exposes `reset`, `step`, and `state`
- 3 deterministic tasks with graders
- `inference.py` at repo root
- Dockerfile builds the environment
- README documents setup, tasks, and action/observation spaces
