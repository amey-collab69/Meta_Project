"""
Task 1 — Order Tracking (Easy)
Single-step or two-step resolution.
"""

TASK = {
    "id": "easy",
    "name": "Order Tracking",
    "difficulty": "easy",
    "initial_message": "Where is my order?",
    "expected_intent": "delivery_issue",
    "expected_workflow": ["ask_details", "reply"],
    "max_steps": 4,
    "success_condition": "RESOLUTION",
    "description": (
        "Customer asks about order status. "
        "Agent should ask for order details then reply with tracking info."
    ),
    "scoring": {
        "full_score": 0.95,
        "partial_score": 0.60,
        "fail_score": 0.15,
    },
}
