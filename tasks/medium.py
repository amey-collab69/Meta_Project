"""
Task 2 — Refund Processing (Medium)
Multi-step workflow: ask_details → validate → refund
"""

TASK = {
    "id": "medium",
    "name": "Refund Processing",
    "difficulty": "medium",
    "initial_message": "I received a damaged product, I want a refund",
    "expected_intent": "refund",
    "expected_workflow": ["ask_details", "ask_details", "refund"],
    "max_steps": 6,
    "success_condition": "RESOLUTION",
    "initial_state": "REFUND_REQUEST",
    "intermediate_state": "VALIDATION_PENDING",
    "final_state": "RESOLVED",
    "description": (
        "Customer requests refund for damaged product. "
        "Agent must collect details, validate, then process refund."
    ),
    "scoring": {
        "full_score": 0.90,
        "partial_score": 0.55,
        "fail_score": 0.20,
    },
}
