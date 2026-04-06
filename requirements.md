# 📌 Requirements Document — SupportAI-Env (Final Hybrid Version)

---

# 🎯 1. Objective

Develop a **production-grade OpenEnv environment** that simulates real-world customer support workflows, enabling evaluation of AI agents through structured interactions, deterministic logic, and measurable outcomes.

The system must support both:

* automated evaluation (API-based)
* manual testing (GUI-based)

---

# 🧩 2. Functional Requirements

## 🔹 2.1 Environment Interface (OpenEnv Compliance)

The environment must implement:

* `reset()` → initialize a new scenario
* `step(action)` → process agent action
* `state()` → return current state

All interfaces must use strongly typed schemas via Pydantic

---

## 🔹 2.2 Hybrid Decision System (CRITICAL 🔥)

The system must follow a **hybrid logic architecture**:

### ✅ Deterministic Component:

* keyword-based intent detection
* rule-based state transitions
* deterministic reward calculation

### ✅ LLM Component:

* tone detection (angry / neutral / polite)
* ambiguity resolution (optional)

---

### ❌ Restrictions:

* LLM must NOT be used for:

  * reward calculation
  * action decision
  * grading

---

## 🔹 2.3 Simulation Scope

Environment must simulate realistic customer support workflows:

* order tracking
* refund processing
* complaint handling

System must support:

* conversational context
* multi-step workflows
* decision-based interactions

---

## 🔹 2.4 State & Action Schema

### Observation Model:

```text id="obs_schema"
customer_message: string  
conversation_history: list  
sentiment: string  
issue_type: string  
urgency_level: string  
```

---

### Action Model:

```text id="act_schema"
action_type: enum (reply, refund, escalate, ask_details)  
content: string (optional)  
```

---

## 🔹 2.5 Task System

The environment must include **minimum 3 tasks**:

| Level  | Requirement                        |
| ------ | ---------------------------------- |
| Easy   | single-step resolution             |
| Medium | multi-step workflow                |
| Hard   | multi-intent + emotional reasoning |

---

Each task must:

* have clearly defined objectives
* include expected workflow
* include deterministic grader
* produce score in range **0.0 → 1.0**

---

## 🔹 2.6 State Machine Logic

System must implement structured transitions:

```text id="state_flow"
STATE + ACTION → NEXT STATE
```

---

### Requirements:

* enforce valid action rules
* reject invalid transitions
* maintain deterministic behavior

---

## 🔹 2.7 Reward System (Advanced)

The reward system must provide **dense, multi-factor feedback**.

### Required Components:

* intent accuracy
* action correctness
* sequence quality
* efficiency (steps taken)
* tone awareness

---

### Example Reward Structure:

```text id="reward_structure"
Reward = 0.3(Intent Match)
       + 0.4(Action Correctness)
       + 0.2(Sequence Quality)
       + 0.1(Efficiency)
       + Tone Bonus
       - Penalties
```

---

### Penalties must include:

* invalid actions
* repeated steps
* unnecessary escalation

---

## 🔹 2.8 Inference System

* Must include `inference.py`
* Uses OpenAI API
* Must output structured logs:

```text id="log_format"
[START]
[STEP]
[END]
```

---

## 🔹 2.9 GUI Requirement (IMPORTANT 🔥)

The system must include an interactive GUI for manual testing.

### Features:

* chat-style interface
* action buttons
* reward display
* conversation history

---

### Purpose:

* improve usability
* allow judges to test easily
* demonstrate real-world application

---

# ⚙️ 3. Non-Functional Requirements

## 🔹 3.1 Performance

* runtime < 20 minutes
* optimized for:

  * 2 vCPU
  * 8GB RAM

---

## 🔹 3.2 Deployment

* containerized using Docker
* hosted on Hugging Face Spaces

---

## 🔹 3.3 Reliability

* deterministic outputs (same input → same result)
* reproducible scores
* no runtime failures

---

## 🔹 3.4 Usability

* GUI for non-technical users
* API for automated evaluation
* clear documentation

---

# ❌ 4. Disqualification Conditions

* missing tasks (<3)
* non-deterministic scoring
* invalid reward logic
* broken Docker build
* failed deployment
* incorrect logging format

---

# 📊 5. Evaluation Metrics (JUDGE LEVEL)

The system must support evaluation using:

| Metric            | Description          |
| ----------------- | -------------------- |
| Success Rate      | % of tasks completed |
| Average Reward    | quality of decisions |
| Steps per Episode | efficiency           |
| Error Rate        | robustness           |

---

# 🧠 6. Success Criteria

A successful implementation must demonstrate:

✔ realistic simulation of support workflows
✔ deterministic and reproducible behavior
✔ strong reward engineering
✔ clear task progression (easy → hard)
✔ usability through GUI + API

---

# 🏆 7. Final Requirement Summary

The system must behave like:

👉 a real-world AI evaluation environment

NOT

👉 a simple rule-based demo

---
