# 🧠 Design Document — SupportAI-Env (Advanced Hybrid Architecture with GUI)

---

# 🚀 1. System Overview

SupportAI-Env is a **real-world simulation environment** designed for evaluating AI agents on customer support workflows. The system follows the OpenEnv paradigm and supports:

1. Programmatic interaction via API (`/reset`, `/step`)
2. Human interaction via GUI (web interface)

---

## 🧠 Core Innovation (Hybrid Logic 🔥)

The system uses a **Hybrid Decision Engine**:

```text
Keyword-Based Logic (Deterministic) + LLM (Tone & Ambiguity)
```

* Keywords → intent detection (deterministic)
* LLM → tone detection (supportive, not controlling)

👉 Ensures:
✔ deterministic grading
✔ real-world intelligence
✔ judge-friendly design

---

# 🧩 2. Technology Stack

* Python — environment logic & orchestration
* FastAPI — REST API + GUI serving
* Pydantic — strongly typed schemas
* OpenAI API — tone detection & inference
* Docker — reproducible runtime
* Hugging Face Spaces — deployment layer

---

# 🏗️ 3. High-Level Architecture

```text
        ┌──────────────┐
        │     GUI      │
        └──────┬───────┘
               │
        ┌──────▼───────┐
        │   FastAPI    │
        └──────┬───────┘
               │
        ┌──────▼────────────┐
        │ Hybrid Engine      │
        │ (Keyword + LLM)    │
        └──────┬────────────┘
               │
        ┌──────▼────────────┐
        │ State Machine      │
        └──────┬────────────┘
               │
        ┌──────▼───────┐
        │ Reward Engine │
        └──────────────┘
```

---

# 🔁 4. Execution Flow (Detailed)

```text
RESET → INITIAL STATE  
↓  
KEYWORD INTENT DETECTION  
↓  
LLM TONE DETECTION  
↓  
ACTION INPUT  
↓  
STATE VALIDATION  
↓  
STATE TRANSITION  
↓  
REWARD CALCULATION  
↓  
DONE CHECK  
↓  
NEXT STEP / TERMINATE
```

---

# 🧠 5. State (Observation Model)

```python
class Observation(BaseModel):
    customer_message: str
    conversation_history: list
    sentiment: str
    issue_type: str
    urgency_level: str
```

---

## 🔍 Additional Internal State

* `current_state` → tracks workflow stage
* `step_count` → limits episode length
* `intent` → derived from keyword engine

---

# ⚡ 6. Hybrid Intent & Tone Detection

## 🔹 Keyword-Based Intent (Deterministic)

```text
"refund" → refund  
"late" → delivery_issue  
"damaged" → product_issue  
```

---

## 🔹 LLM-Based Tone Detection (Controlled)

```text
Input → LLM → Output:
- angry
- neutral
- polite
```

⚠️ LLM is NOT used for:

* decision making
* reward calculation

👉 Only used to enhance realism (tone awareness)

---

# 🔁 7. State Machine Design (CRITICAL)

## State Transition Model:

```text
START → IDENTIFY_INTENT → ACTION_STAGE → RESOLUTION → END
```

---

## Example Transitions:

```text
DELIVERY_ISSUE + reply → RESOLVED  
DELIVERY_ISSUE + refund → INVALID  
REFUND_REQUEST + ask_details → VALID_PROGRESS  
```

---

# ⚙️ 8. Action Validity Rules

| State     | Allowed Actions     | Invalid Actions |
| --------- | ------------------- | --------------- |
| tracking  | reply, ask_details  | refund          |
| refund    | ask_details, refund | random reply    |
| complaint | reply, escalate     | ignore          |

---

# 🧮 9. Reward Function (Advanced)

## Final Formula:

```text
Reward = 0.3(Intent Match)
       + 0.4(Action Correctness)
       + 0.2(Sequence Quality)
       + 0.1(Efficiency)
       + Tone Bonus
       - Penalties
```

---

## ✅ Positive Rewards

| Component                   | Score |
| --------------------------- | ----- |
| Intent correct              | +0.3  |
| Correct action              | +0.4  |
| Proper sequence             | +0.2  |
| Fast resolution             | +0.1  |
| Polite tone (if angry user) | +0.1  |

---

## ❌ Penalties

| Scenario               | Penalty |
| ---------------------- | ------- |
| Wrong action           | -0.3    |
| Invalid action         | -0.2    |
| Repeated action        | -0.1    |
| Unnecessary escalation | -0.2    |

---

# 🔄 10. Episode Termination Logic

Episode ends when:

* issue resolved
* max steps reached
* repeated invalid loop detected

---

# 🧪 11. Grader System

```text
Agent Actions → Rule Evaluation → Score (0.0–1.0)
```

---

## Evaluation Criteria:

* intent correctness
* action validity
* sequence completion
* tone appropriateness
* efficiency

---

# 🌐 12. API Layer (FastAPI)

| Endpoint    | Function               |
| ----------- | ---------------------- |
| POST /reset | initialize environment |
| POST /step  | process action         |
| GET /state  | fetch state            |

---

# 🎨 13. GUI Layer (Enhanced UX 🔥)

## Features:

* chat-style interface
* action buttons
* reward display
* conversation history

---

## Interaction Flow:

```text
User → GUI → API → Env → Response → GUI Update
```

---

## Purpose:

✔ makes system easy to test
✔ improves judge experience
✔ adds product-level feel

---

# 🤖 14. Inference Engine

* uses OpenAI API
* generates baseline performance
* logs structured output

```text
[START]
[STEP]
[END]
```

---

# 🐳 15. Deployment Architecture

```text
Code → Docker Build → Container → HF Space Deploy
```

---

# 🧠 16. Design Strengths (Winning Factors)

✔ Hybrid deterministic + intelligent system
✔ Real-world workflow simulation
✔ Strong reward engineering
✔ Multi-step reasoning support
✔ Dual interaction (API + GUI)
✔ Fully OpenEnv compliant

---

# 🏆 17. Key Differentiators

* Hybrid keyword + LLM architecture
* Tone-aware reward system
* State-machine driven logic
* Judge-friendly GUI
* Deterministic grading system

---
