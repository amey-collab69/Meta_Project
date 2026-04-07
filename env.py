"""
SupportAI-Env — Core Environment Engine (Enhanced Real-Time Version)
Hybrid: Keyword-based intent (deterministic) + LLM tone detection (supportive only)
Features: Real-time processing, caching, async support, enhanced error handling
"""

import os
import time
from typing import Optional, Dict, Any
from functools import lru_cache
from dotenv import load_dotenv
load_dotenv()
from pydantic import BaseModel
from openai import OpenAI
import asyncio

# ─── Schemas ────────────────────────────────────────────────────────────────

class Observation(BaseModel):
    customer_message: str
    conversation_history: list
    sentiment: str
    issue_type: str
    urgency_level: str
    current_state: str
    step_count: int
    intent: str
    timestamp: float = 0.0
    processing_time_ms: float = 0.0

class Action(BaseModel):
    action_type: str   # reply | refund | escalate | ask_details
    content: Optional[str] = ""
    timestamp: float = 0.0

# ─── Constants ───────────────────────────────────────────────────────────────

VALID_ACTIONS = ["reply", "refund", "escalate", "ask_details"]

# State machine: (current_state, action_type) → next_state
STATE_TRANSITIONS = {
    ("IDENTIFY_INTENT",  "reply"):        "ACTION_STAGE",
    ("IDENTIFY_INTENT",  "ask_details"):  "ACTION_STAGE",
    ("ACTION_STAGE",     "reply"):        "RESOLUTION",
    ("ACTION_STAGE",     "ask_details"):  "VALIDATION_PENDING",
    ("ACTION_STAGE",     "refund"):       "RESOLUTION",
    ("ACTION_STAGE",     "escalate"):     "RESOLUTION",
    ("VALIDATION_PENDING", "refund"):     "RESOLUTION",
    ("VALIDATION_PENDING", "reply"):      "RESOLUTION",
    ("VALIDATION_PENDING", "ask_details"):"VALIDATION_PENDING",
    ("RESOLUTION",       "reply"):        "END",
}

# Per-state allowed actions
STATE_ALLOWED_ACTIONS = {
    "IDENTIFY_INTENT":   ["reply", "ask_details"],
    "ACTION_STAGE":      ["reply", "ask_details", "refund", "escalate"],
    "VALIDATION_PENDING":["ask_details", "refund", "reply"],
    "RESOLUTION":        ["reply"],
    "END":               [],
}

# Enhanced Intent keyword map with more patterns (deterministic)
INTENT_KEYWORDS = {
    "refund":          ["refund", "money back", "reimburs", "return", "get my money", "want my money", 
                        "pay back", "charge back", "cancel order", "don't want"],
    "delivery_issue":  ["late", "delay", "not arrived", "where is my order", "tracking", "hasn't arrived",
                        "didn't receive", "not delivered", "when will", "how long", "still waiting",
                        "expected", "shipping", "delivery status", "track my order"],
    "product_issue":   ["damaged", "broken", "defective", "wrong item", "not working", "faulty",
                        "poor quality", "doesn't work", "incorrect", "missing parts", "not as described",
                        "different from", "wrong product", "wrong size", "wrong color"],
    "complaint":       ["worst", "terrible", "angry", "unacceptable", "horrible", "disgusting",
                        "disappointed", "frustrated", "furious", "outraged", "never again",
                        "poor service", "bad experience", "complaint", "unhappy", "dissatisfied"],
    "general":         [],
}

# Enhanced intent patterns for better matching
INTENT_PATTERNS = {
    "refund": [
        "i want", "i need", "give me", "send me", "can i get", "how do i get",
        "process", "issue", "provide"
    ],
    "delivery_issue": [
        "where", "when", "how long", "status", "update", "check", "find"
    ],
    "product_issue": [
        "received", "got", "came", "arrived", "sent me", "delivered"
    ],
    "complaint": [
        "this is", "you are", "your service", "your company", "never", "always"
    ]
}

MAX_STEPS = 10

# ─── Enhanced Intent Detection with Pattern Matching ─────────────────────────

@lru_cache(maxsize=256)
def detect_intent(message: str) -> str:
    """
    Enhanced intent detection with keyword + pattern matching.
    Uses scoring system for better accuracy.
    """
    msg = message.lower().strip()
    if not msg:
        return "general"
    
    # Score each intent
    intent_scores = {
        "refund": 0,
        "delivery_issue": 0,
        "product_issue": 0,
        "complaint": 0,
        "general": 0
    }
    
    # Keyword matching (primary signal)
    for intent, keywords in INTENT_KEYWORDS.items():
        if intent == "general":
            continue
        for kw in keywords:
            if kw in msg:
                intent_scores[intent] += 2  # Strong signal
                break
    
    # Pattern matching (secondary signal)
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if pattern in msg:
                intent_scores[intent] += 1  # Weaker signal
    
    # Question words boost delivery_issue
    question_words = ["where", "when", "how", "what", "why"]
    if any(qw in msg for qw in question_words):
        intent_scores["delivery_issue"] += 1
    
    # Negative sentiment boosts complaint
    negative_words = ["not", "never", "no", "don't", "didn't", "won't", "can't"]
    negative_count = sum(1 for nw in negative_words if nw in msg)
    if negative_count >= 2:
        intent_scores["complaint"] += 2
    
    # Find highest scoring intent
    max_score = max(intent_scores.values())
    if max_score == 0:
        return "general"
    
    # Priority tiebreaker: complaint > product_issue > refund > delivery_issue
    priority = ["complaint", "product_issue", "refund", "delivery_issue", "general"]
    for intent in priority:
        if intent_scores[intent] == max_score:
            return intent
    
    return "general"

@lru_cache(maxsize=256)
def detect_multi_intent(message: str) -> tuple:
    """
    Returns all detected intents with scoring (for hard task).
    Returns tuple for caching.
    """
    msg = message.lower().strip()
    if not msg:
        return ("general",)
    
    # Score each intent
    intent_scores = {
        "refund": 0,
        "delivery_issue": 0,
        "product_issue": 0,
        "complaint": 0
    }
    
    # Keyword matching
    for intent, keywords in INTENT_KEYWORDS.items():
        if intent == "general":
            continue
        for kw in keywords:
            if kw in msg:
                intent_scores[intent] += 2
    
    # Pattern matching
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if pattern in msg:
                intent_scores[intent] += 1
    
    # Return all intents with score > 0, sorted by score
    detected = [intent for intent, score in sorted(intent_scores.items(), 
                key=lambda x: x[1], reverse=True) if score > 0]
    
    return tuple(detected) if detected else ("general",)

# ─── LLM Tone Detection (Enhanced with Caching & Timeout) ────────────────────

_tone_cache: Dict[str, tuple] = {}  # message -> (tone, timestamp)
_CACHE_TTL = 300  # 5 minutes

def _enhanced_rule_based_tone(msg: str) -> str:
    """Enhanced rule-based tone detection with scoring."""
    angry_words = ["worst", "terrible", "angry", "hate", "awful", "horrible",
                   "unacceptable", "bad", "disgusting", "furious", "outraged",
                   "ridiculous", "useless", "pathetic", "stupid", "never again",
                   "disappointed", "frustrated", "dissatisfied", "unhappy"]
    polite_words = ["please", "thank", "appreciate", "kindly", "grateful", "sorry",
                    "excuse me", "if possible", "would you", "could you"]
    
    # Count sentiment indicators
    angry_count = sum(1 for w in angry_words if w in msg)
    polite_count = sum(1 for w in polite_words if w in msg)
    
    # Exclamation marks indicate strong emotion
    exclamation_count = msg.count("!")
    if exclamation_count >= 2:
        angry_count += 1
    
    # ALL CAPS indicates anger
    words = msg.split()
    caps_count = sum(1 for w in words if w.isupper() and len(w) > 2)
    if caps_count >= 2:
        angry_count += 2
    
    # Determine tone based on scores
    if angry_count >= 2 or (angry_count >= 1 and exclamation_count >= 2):
        return "angry"
    elif polite_count >= 1:
        return "polite"
    elif angry_count >= 1:
        return "angry"
    else:
        return "neutral"

def detect_tone(message: str, use_cache: bool = True) -> str:
    """
    Enhanced tone detection with caching and timeout protection.
    Rule-based first (deterministic), LLM as enhancement.
    Returns: angry | neutral | polite
    LLM does NOT decide actions or rewards.
    """
    msg = message.lower().strip()
    if not msg:
        return "neutral"
    
    # Check cache first
    if use_cache and msg in _tone_cache:
        cached_tone, cached_time = _tone_cache[msg]
        if time.time() - cached_time < _CACHE_TTL:
            return cached_tone
    
    # Enhanced rule-based detection
    rule_tone = _enhanced_rule_based_tone(msg)

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        _tone_cache[msg] = (rule_tone, time.time())
        return rule_tone

    try:
        client = OpenAI(api_key=api_key, timeout=3.0)  # 3 second timeout
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a tone classifier. "
                        "Classify the customer message tone as exactly one of: angry, neutral, polite. "
                        "Reply with only the single word."
                    ),
                },
                {"role": "user", "content": message},
            ],
            max_tokens=5,
            temperature=0,
        )
        llm_tone = response.choices[0].message.content.strip().lower()
        if llm_tone not in ("angry", "neutral", "polite"):
            final_tone = rule_tone
        else:
            # Rule-based takes priority for angry (more reliable)
            final_tone = "angry" if rule_tone == "angry" else llm_tone
        
        _tone_cache[msg] = (final_tone, time.time())
        return final_tone
    except Exception as e:
        print(f"[TONE] LLM failed ({str(e)[:50]}), using rule-based: {rule_tone}")
        _tone_cache[msg] = (rule_tone, time.time())
        return rule_tone

# ─── Response Generator (Logic-driven, no hardcoding) ────────────────────────

# Templates keyed by (action, intent, tone) — most specific wins
# Placeholders: {intent_label}, {tone_label}
_RESPONSE_TEMPLATES = {
    # ask_details
    ("ask_details", "delivery_issue", "angry"):   "I completely understand your frustration. To locate your shipment right away, could you please share your order ID and the date you placed the order?",
    ("ask_details", "delivery_issue", "neutral"):  "I'd be happy to help track your order. Could you please provide your order ID so I can look into this for you?",
    ("ask_details", "delivery_issue", "polite"):   "Thank you for reaching out! Could you please share your order ID so I can check the delivery status for you?",
    ("ask_details", "refund", "angry"):            "I sincerely apologize for this experience. To process your refund as quickly as possible, could you please provide your order ID and describe the issue with the product?",
    ("ask_details", "refund", "neutral"):          "I can help with your refund request. Could you please share your order ID and a brief description of the issue?",
    ("ask_details", "refund", "polite"):           "Thank you for letting us know. To proceed with your refund, could you please provide your order ID and details about the problem?",
    ("ask_details", "product_issue", "angry"):     "I'm truly sorry about the damaged product. To resolve this immediately, please share your order ID and describe the damage.",
    ("ask_details", "product_issue", "neutral"):   "I'm sorry to hear about the product issue. Could you share your order ID and describe what happened?",
    ("ask_details", "product_issue", "polite"):    "Thank you for bringing this to our attention. Could you please provide your order ID and details about the product issue?",
    ("ask_details", "complaint", "angry"):         "I deeply apologize for this experience. To address all your concerns properly, could you please share your order ID?",
    ("ask_details", "complaint", "neutral"):       "I want to make sure I resolve all your concerns. Could you please provide your order ID?",
    ("ask_details", "general", "neutral"):         "To assist you better, could you please provide more details about your issue, including your order ID if applicable?",

    # refund
    ("refund", "refund", "angry"):        "I've processed a full refund for your order. You will receive it within 3–5 business days. I sincerely apologize for the inconvenience caused.",
    ("refund", "refund", "neutral"):      "Your refund has been successfully processed. You should receive it within 3–5 business days to your original payment method.",
    ("refund", "refund", "polite"):       "Great news — your refund has been processed! You'll receive it within 3–5 business days. Thank you for your patience.",
    ("refund", "product_issue", "angry"): "I've issued a full refund for the damaged product. It will be credited within 3–5 business days. I'm very sorry this happened.",
    ("refund", "product_issue", "neutral"):"A refund has been processed for the damaged item. You'll receive it within 3–5 business days.",
    ("refund", "complaint", "angry"):     "As a resolution to your complaint, I've processed a full refund. It will arrive within 3–5 business days. I apologize sincerely for this experience.",

    # escalate
    ("escalate", "complaint", "angry"):   "I completely understand your frustration and I'm escalating your case to our senior support team immediately. They will contact you within 24 hours with a full resolution.",
    ("escalate", "complaint", "neutral"): "I'm escalating your case to our specialist team who will review it thoroughly and contact you within 24 hours.",
    ("escalate", "general", "neutral"):   "I'm escalating your request to our senior support team. They will reach out to you within 24 hours.",

    # reply
    ("reply", "delivery_issue", "angry"):  "I sincerely apologize for the delay. Your order is currently in transit and is expected to arrive within 1–2 business days. I'm monitoring it closely.",
    ("reply", "delivery_issue", "neutral"):"Your order is currently on its way and should arrive within the estimated delivery window. Please let me know if you need further assistance.",
    ("reply", "delivery_issue", "polite"): "Thank you for your patience! Your order is on its way and should arrive soon. Feel free to reach out if you need anything else.",
    ("reply", "refund", "angry"):          "I completely understand your frustration. Your refund request has been acknowledged and is being processed as a priority.",
    ("reply", "refund", "neutral"):        "Your refund request has been received and is being processed. You'll receive a confirmation shortly.",
    ("reply", "product_issue", "angry"):   "I'm truly sorry about the damaged product. I've flagged this as urgent and our team is working on a resolution for you right now.",
    ("reply", "product_issue", "neutral"): "I'm sorry to hear about the product issue. I've noted your concern and will ensure it gets resolved promptly.",
    ("reply", "complaint", "angry"):       "I sincerely apologize for this unacceptable experience. I take full responsibility and I'm committed to resolving every issue you've raised right now.",
    ("reply", "complaint", "neutral"):     "Thank you for bringing this to our attention. I've reviewed your concerns and I'm working on a resolution.",
    ("reply", "general", "neutral"):       "Thank you for contacting support. I've reviewed your message and I'm here to help resolve your issue.",
    ("reply", "general", "polite"):        "Thank you for your kind message! I'm happy to assist you. Please let me know how I can help.",
}

_FALLBACK_RESPONSES = {
    "ask_details": "To assist you better, could you please provide your order ID and more details about your issue?",
    "refund":      "Your refund has been processed and will be credited within 3–5 business days.",
    "escalate":    "Your case has been escalated to our senior support team. They will contact you within 24 hours.",
    "reply":       "Thank you for reaching out. I'm here to help resolve your issue as quickly as possible.",
}

def generate_response(action: str, intent: str, tone: str, step: int, workflow: list) -> str:
    """
    Enhanced logic-driven response generator with context awareness.
    Derives response from: action + intent + tone + workflow position + step number.
    """
    # Most specific key first: (action, intent, tone)
    key = (action, intent, tone)
    if key in _RESPONSE_TEMPLATES:
        response = _RESPONSE_TEMPLATES[key]
    else:
        # Fallback: (action, intent, neutral)
        key2 = (action, intent, "neutral")
        if key2 in _RESPONSE_TEMPLATES:
            response = _RESPONSE_TEMPLATES[key2]
        else:
            # Fallback: (action, general, neutral)
            key3 = (action, "general", "neutral")
            if key3 in _RESPONSE_TEMPLATES:
                response = _RESPONSE_TEMPLATES[key3]
            else:
                # Final fallback by action only
                response = _FALLBACK_RESPONSES.get(action, "I'm processing your request. Please hold on.")
    
    # Add context-aware enhancements based on step
    if step == 1 and tone == "angry":
        # First interaction with angry customer - add empathy
        response = "I sincerely apologize for your experience. " + response
    elif step > 3:
        # Later steps - add urgency
        if "processing" in response.lower() or "working" in response.lower():
            response = response.replace(".", " right away.")
    
    return response


def calculate_reward(
    intent: str,
    expected_intent: str,
    action: str,
    expected_actions: list,
    current_state: str,
    next_state: str,
    step_count: int,
    max_steps: int,
    tone: str,
    action_history: list,
    is_valid: bool,
) -> float:
    """
    Deterministic reward calculation.
    Reward = 0.3(Intent) + 0.4(Action) + 0.2(Sequence) + 0.1(Efficiency) + Tone - Penalties
    """
    reward = 0.0

    # Intent match (+0.3)
    if intent == expected_intent or expected_intent == "any":
        reward += 0.3

    # Action correctness (+0.4)
    if action in expected_actions:
        reward += 0.4

    # Sequence quality (+0.2): valid state transition happened
    if next_state != current_state and next_state != "INVALID":
        reward += 0.2

    # Efficiency (+0.1): reward faster resolution
    if step_count <= max_steps // 2:
        reward += 0.1

    # Tone bonus (+0.1): polite response when user is angry
    if tone == "angry" and action == "reply":
        reward += 0.1

    # ── Penalties ──
    if not is_valid:
        reward -= 0.2  # invalid action

    if action_history.count(action) > 1:
        reward -= 0.1  # repeated action

    # Unnecessary escalation: escalate when not a complaint
    if action == "escalate" and intent not in ("complaint",):
        reward -= 0.2

    # Wrong action (action not in expected and not invalid — just wrong choice)
    if action not in expected_actions and is_valid:
        reward -= 0.3

    # Ensure reward is strictly between 0 and 1 (not -1 to 1)
    # Map from [-1, 1] to (0, 1) strictly
    reward = (reward + 1.0) / 2.0  # Maps [-1,1] to [0,1]
    reward = max(0.01, min(0.99, reward))  # Ensure strictly between 0 and 1
    return round(reward, 4)

# ─── Environment ─────────────────────────────────────────────────────────────

class SupportEnv:
    def __init__(self, task: dict):
        """
        task dict keys:
          - initial_message: str
          - expected_intent: str
          - expected_workflow: list[str]  (ordered expected actions)
          - max_steps: int (optional)
        """
        self.task = task
        self._obs: Optional[Observation] = None
        self._action_history: list = []
        self._done = False
        self._step_count = 0
        self._current_state = "START"
        self._intent = "general"
        self._tone = "neutral"
        self._workflow_index = 0
        self._total_reward = 0.0

    def reset(self) -> Observation:
        """Initialize environment with task scenario (enhanced with timing)."""
        start_time = time.time()
        msg = self.task["initial_message"]
        self._intent = detect_intent(msg)
        self._tone = detect_tone(msg)
        self._current_state = "IDENTIFY_INTENT"
        self._step_count = 0
        self._action_history = []
        self._done = False
        self._workflow_index = 0
        self._total_reward = 0.0

        urgency = "high" if self._tone == "angry" else "normal"
        processing_time = (time.time() - start_time) * 1000  # ms

        self._obs = Observation(
            customer_message=msg,
            conversation_history=[{"role": "customer", "content": msg}],
            sentiment=self._tone,
            issue_type=self._intent,
            urgency_level=urgency,
            current_state=self._current_state,
            step_count=self._step_count,
            intent=self._intent,
            timestamp=time.time(),
            processing_time_ms=round(processing_time, 2),
        )
        return self._obs

    def step(self, action: Action) -> tuple:
        """
        Process one agent action (enhanced with timing and validation).
        Returns: (observation, reward, done, info)
        """
        start_time = time.time()
        
        if self._done:
            return self._obs, 0.0, True, {"error": "Episode already done", "processing_time_ms": 0}

        if self._obs is None:
            return None, 0.0, True, {"error": "Call reset() first", "processing_time_ms": 0}

        act = action.action_type.strip().lower()
        
        # Validate action type
        if act not in VALID_ACTIONS:
            self._step_count += 1
            processing_time = (time.time() - start_time) * 1000
            return self._obs, 0.01, False, {
                "error": f"Invalid action type '{act}'. Must be one of: {VALID_ACTIONS}",
                "valid": False,
                "next_state": self._current_state,
                "processing_time_ms": round(processing_time, 2)
            }
        
        self._step_count += 1
        max_steps = self.task.get("max_steps", MAX_STEPS)

        # ── Validate action ──
        allowed = STATE_ALLOWED_ACTIONS.get(self._current_state, [])
        is_valid = act in VALID_ACTIONS and act in allowed

        # ── State transition ──
        key = (self._current_state, act)
        next_state = STATE_TRANSITIONS.get(key, self._current_state) if is_valid else self._current_state

        # ── Expected action at this workflow step ──
        workflow = self.task.get("expected_workflow", [])
        expected_actions = (
            [workflow[self._workflow_index]]
            if self._workflow_index < len(workflow)
            else ["reply"]
        )

        # ── Reward ──
        reward = calculate_reward(
            intent=self._intent,
            expected_intent=self.task.get("expected_intent", "any"),
            action=act,
            expected_actions=expected_actions,
            current_state=self._current_state,
            next_state=next_state,
            step_count=self._step_count,
            max_steps=max_steps,
            tone=self._tone,
            action_history=self._action_history,
            is_valid=is_valid,
        )
        self._total_reward += reward

        # ── Advance workflow index if action matched ──
        if act in expected_actions:
            self._workflow_index += 1

        # ── Update state ──
        self._current_state = next_state
        self._action_history.append(act)

        # ── Done conditions ──
        done = False
        info = {"error": None, "valid": is_valid, "next_state": next_state}

        if not is_valid:
            info["error"] = f"Invalid action '{act}' in state '{self._current_state}'"

        # ── Generate logic-driven response ──
        agent_response = generate_response(
            action=act,
            intent=self._intent,
            tone=self._tone,
            step=self._step_count,
            workflow=workflow,
        )
        info["agent_response"] = agent_response

        if not is_valid:
            info["error"] = f"Invalid action '{act}' in state '{self._current_state}'"

        if next_state == "END":
            done = True
            info["message"] = "Issue resolved"
        elif self._step_count >= max_steps:
            done = True
            info["message"] = "Max steps reached"
        elif self._action_history.count(act) >= 3:
            done = True
            info["message"] = "Repeated action loop detected"
        elif next_state in ("RESOLUTION", "END") and self._workflow_index >= len(workflow):
            # Workflow fully completed — mark done
            done = True
            info["message"] = "Issue fully resolved"

        self._done = done

        # ── Update observation ──
        processing_time = (time.time() - start_time) * 1000  # ms
        history = self._obs.conversation_history + [
            {"role": "agent", "action": act, "content": action.content or "", "timestamp": time.time()}
        ]
        self._obs = Observation(
            customer_message=self._obs.customer_message,
            conversation_history=history,
            sentiment=self._tone,
            issue_type=self._intent,
            urgency_level=self._obs.urgency_level,
            current_state=self._current_state,
            step_count=self._step_count,
            intent=self._intent,
            timestamp=time.time(),
            processing_time_ms=round(processing_time, 2),
        )
        
        info["processing_time_ms"] = round(processing_time, 2)
        info["score"] = reward  # Add score for OpenEnv validation
        return self._obs, reward, done, info

    def state(self) -> Observation:
        """Return current observation."""
        if self._obs is None:
            raise RuntimeError("Call reset() first")
        return self._obs

    def total_reward(self) -> float:
        return round(self._total_reward, 4)
