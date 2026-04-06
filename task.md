# 🎯 Task Design — SupportAI-Env (Final Hybrid Version)

---

# 🧠 1. Task Philosophy

Tasks are designed to:

* replicate real-world customer support workflows
* evaluate agent reasoning and decision-making
* test multi-step execution capability
* incorporate emotional and contextual understanding

---

## 🔥 Key Design Principle

Each task integrates:

```text id="task_core"
Intent Detection (Keyword) + Tone Awareness (LLM) + State Machine + Reward Logic
```

---

# 🟢 2. Task 1: Order Tracking (Easy)

## 📌 Scenario

Customer:

> "Where is my order?"

---

## 🎯 Objective

* correctly identify tracking intent
* provide accurate response OR request missing details

---

## 🔁 Expected Workflow

```text id="easy_flow"
Step 1 → detect intent (tracking)  
Step 2 → reply with tracking info OR ask_details  
Step 3 → resolve  
```

---

## ⚙️ Allowed Actions

* reply
* ask_details

---

## ❌ Invalid Actions

* refund
* escalate

---

## 🧪 Evaluation Criteria

| Condition                        | Score |
| -------------------------------- | ----- |
| correct response                 | 1.0   |
| partial (asks details correctly) | 0.5   |
| incorrect action                 | 0.0   |

---

## 🧠 Notes

* single-step or two-step resolution
* no emotional complexity
* tests basic intent recognition

---

# 🟡 3. Task 2: Refund Processing (Medium)

## 📌 Scenario

Customer:

> "I received a damaged product, I want a refund"

---

## 🎯 Objective

* validate request
* collect required details
* process refund correctly

---

## 🔁 Expected Workflow

```text id="medium_flow"
Step 1 → detect intent (refund)  
Step 2 → ask_details  
Step 3 → validate information  
Step 4 → issue refund  
```

---

## ⚙️ Allowed Actions

* ask_details
* refund
* reply

---

## ❌ Invalid Actions

* immediate refund without validation
* unrelated replies

---

## 🧪 Evaluation Criteria

| Condition                     | Score |
| ----------------------------- | ----- |
| correct sequence (multi-step) | 1.0   |
| partial workflow              | 0.5   |
| incorrect action              | 0.0   |

---

## 🧠 Notes

* requires multi-step reasoning
* tests sequence correctness
* introduces workflow dependency

---
Initial State: REFUND_REQUEST
Intermediate State: VALIDATION_PENDING
Final State: RESOLVED

# 🔴 4. Task 3: Multi-Issue Complaint (Hard)

## 📌 Scenario

Customer:

> "This is the worst service! My order is late and the product is damaged!"

---

## 🎯 Objective

* detect multiple intents (delivery + product issue)
* handle emotional tone (angry customer)
* resolve issues efficiently
* maintain polite and empathetic response

---

## 🔁 Expected Workflow

```text id="hard_flow"
Step 1 → detect multiple intents  
Step 2 → detect tone (angry via LLM)  
Step 3 → acknowledge emotion  
Step 4 → ask_details OR resolve issues  
Step 5 → provide solution (refund / update)  
Step 6 → finalize resolution  
```

---

## ⚙️ Allowed Actions

* reply
* ask_details
* refund
* escalate

---

## ❌ Invalid Actions

* ignoring emotional tone
* incomplete resolution
* random or unrelated responses

---

## 🧪 Evaluation Criteria

| Condition                     | Score |
| ----------------------------- | ----- |
| full resolution + proper tone | 1.0   |
| partial resolution            | 0.6   |
| poor handling                 | 0.0   |

---

## 🧠 Tone Requirement (Hybrid Logic 🔥)

* tone must be detected using LLM
* response must be polite when user is angry

---

## 🧠 Notes

* highest complexity task
* tests:

  * multi-intent reasoning
  * emotional intelligence
  * multi-step workflow

---

# 📊 5. Difficulty Scaling

| Task   | Complexity | Key Skill           |
| ------ | ---------- | ------------------- |
| Easy   | low        | intent recognition  |
| Medium | moderate   | multi-step workflow |
| Hard   | high       | multi-intent + tone |

---

# 🧠 6. Evaluation Dimensions (Detailed)

Each task is evaluated on:

* intent recognition (keyword-based)
* action correctness
* sequence validity
* tone appropriateness (LLM-assisted)
* efficiency (steps taken)

---

# 🧮 7. Scoring Logic (Aligned with Reward System)

```text id="score_logic"
Score ∝ Intent + Action + Sequence + Tone + Efficiency
```

---

# 🔥 8. Design Principles

✔ Realism — mirrors actual support workflows
✔ Determinism — predictable and reproducible
✔ Progressive Difficulty — easy → hard
✔ Interpretability — clear grading logic
✔ Hybrid Intelligence — keyword + tone

---

# 🏆 9. Key Differentiators

* multi-intent task handling
* tone-aware evaluation
* structured workflows
* deterministic grading system

---
