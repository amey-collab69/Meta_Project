"""
Task 3 — Multi-Issue Complaint (Hard)
Multi-intent (delivery + product) + angry customer tone.
"""

TASK = {
    "id": "hard",
    "name": "Multi-Issue Complaint",
    "difficulty": "hard",
    "initial_message": "This is the worst service! My order is late and the product is damaged!",
    "expected_intent": "complaint",
    "multi_intent": ["complaint", "delivery_issue", "product_issue"],
    "expected_workflow": ["reply", "ask_details", "refund", "reply"],
    "max_steps": 8,
    "success_condition": "END",
    "requires_tone_handling": True,
    "description": (
        "Angry customer with multiple issues: late delivery + damaged product. "
        "Agent must detect tone, acknowledge emotion, collect details, and resolve both issues."
    ),
    "scoring": {
        "full_score": 1.0,
        "partial_score": 0.6,
        "fail_score": 0.0,
    },
}
