# 🧠 Kiro Full Project Instruction — SupportAI-Env (Complete OpenEnv System)

---

# 🎯 PROJECT GOAL

Build a **complete production-grade OpenEnv environment** named:

👉 **SupportAI-Env**

This environment simulates **real-world customer support workflows** and allows AI agents to interact using:

* reset()
* step()
* state()

---

# 🏗️ SYSTEM OVERVIEW

The system must include:

```text
Environment Engine (env.py)
+ Task System
+ Grader System
+ FastAPI Server (API)
+ GUI Interface
+ Inference Script
+ Docker Setup
```

---

# 🧠 CORE LOGIC REQUIREMENTS

## 🔹 Hybrid Decision System

The system must combine:

### 1. Deterministic Logic (PRIMARY)

* keyword-based intent detection
* rule-based state machine
* deterministic reward calculation

### 2. LLM Support (LIMITED USE)

* tone detection only
* ambiguity resolution (optional)

⚠️ LLM MUST NOT:

* decide actions
* calculate rewards
* affect determinism

---

# 📦 PROJECT STRUCTURE

```text
project/
│
├── env.py
├── main.py
├── inference.py
├── grader.py
├── tasks/
│   ├── easy.py
│   ├── medium.py
│   ├── hard.py
│
├── openenv.yaml
├── requirements.txt
├── Dockerfile
└── README.md
```

---

# 🧩 1. ENVIRONMENT ENGINE (env.py)

Implement:

```python
class SupportEnv:
    def reset(self): ...
    def step(self, action): ...
    def state(self): ...
```

---

## 🔹 Features to include:

### ✅ Intent Detection (Keyword)

```python
if "refund" in msg:
    intent = "refund"
elif "late" in msg:
    intent = "delivery_issue"
```

---

### ✅ Tone Detection (LLM)

* Use OpenAI API
* Output:

  * angry
  * neutral
  * polite

---

### ✅ State Machine

```text
START → IDENTIFY_INTENT → ACTION_STAGE → RESOLVED → END
```

---

### ✅ Action Space

```python
["reply", "refund", "escalate", "ask_details"]
```

---

### ✅ Action Validation

* invalid actions → penalty
* return error in `info`

---

### ✅ Reward System

```text
Reward = Intent + Action + Sequence + Efficiency + Tone - Penalty
```

---

### ✅ Episode Termination

* resolved
* max steps
* loop detection

---

# 🧪 2. TASK SYSTEM

Create 3 tasks:

## 🟢 Easy

* order tracking

## 🟡 Medium

* refund workflow (multi-step)

## 🔴 Hard

* multi-intent + angry customer

---

Each task must define:

* initial state
* expected workflow
* success condition

---

# 🧮 3. GRADER (grader.py)

* deterministic scoring
* output: 0.0 → 1.0

Based on:

* correctness
* sequence
* efficiency

---

# 🌐 4. FASTAPI SERVER (main.py)

Implement:

```text
POST /reset
POST /step
GET /state
```

---

# 🎨 5. GUI (VERY IMPORTANT)

Create simple UI:

### Features:

* chat-style interface
* action buttons
* reward display
* conversation history

---

### Flow:

```text
User → GUI → API → Env → Response → GUI
```

---

# 🤖 6. INFERENCE SCRIPT (inference.py)

Must:

* use OpenAI API
* follow EXACT format:

```text
[START]
[STEP]
[END]
```

---

### Example:

```text
[START] task=refund env=support model=xyz
[STEP] step=1 action=ask_details reward=0.00 done=false error=null
[END] success=true steps=2 score=1.00 rewards=0.00,1.00
```

---

# 🐳 7. DOCKER SETUP

Create Dockerfile:

* install dependencies
* run inference.py

---

# ☁️ 8. DEPLOYMENT

Prepare for:
👉 Hugging Face Spaces

---

# ⚙️ 9. REQUIREMENTS.TXT

Include:

* fastapi
* uvicorn
* openai
* pydantic

---

# 🧠 10. SYSTEM RULES

✔ deterministic outputs
✔ no randomness
✔ reproducible results

---

# ❌ DO NOT DO

❌ no pure LLM system
❌ no random logic
❌ no missing API

---

# 🏆 11. FINAL OUTPUT EXPECTATION

Generate complete working project:

```text
env.py
main.py
inference.py
grader.py
tasks/
Dockerfile
requirements.txt
```

---

# 🚀 FINAL GOAL

Build something that feels like:

👉 real AI evaluation system used in industry

NOT

👉 basic academic project

---
