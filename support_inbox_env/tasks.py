from support_inbox_env.models import Difficulty, TaskSpec, Ticket


TASKS = [
    TaskSpec(
        task_id="easy_billing_refund",
        title="Duplicate charge refund request",
        difficulty=Difficulty.EASY,
        description=(
            "Handle a duplicate-charge refund request. The agent should classify the issue, "
            "set an appropriate priority, route it to billing, send a helpful response, and resolve."
        ),
        ticket=Ticket(
            ticket_id="TCK-1001",
            customer_name="Maya Patel",
            customer_tier="standard",
            subject="Charged twice for the same subscription",
            body=(
                "Hi team, I was billed twice this morning for my monthly plan. "
                "Please refund the extra charge and confirm when it is fixed."
            ),
            sentiment="frustrated",
        ),
        expected_intent="billing",
        expected_priority="normal",
        expected_team="billing",
        required_reply_keywords=["refund", "duplicate", "confirm"],
        final_action="resolve",
        resolution_value="refund_started",
    ),
    TaskSpec(
        task_id="medium_outage_enterprise",
        title="Enterprise production outage",
        difficulty=Difficulty.MEDIUM,
        description=(
            "Handle an enterprise production outage report. The agent should mark it urgent, "
            "route it to engineering, acknowledge the severity, and escalate."
        ),
        ticket=Ticket(
            ticket_id="TCK-2007",
            customer_name="Jordan Lee",
            customer_tier="enterprise",
            subject="Production API is returning 500 errors for all traffic",
            body=(
                "Our production integration is fully down and every request to your API is failing "
                "with 500 responses. This is impacting customer traffic right now. Please escalate immediately."
            ),
            sentiment="urgent",
        ),
        expected_intent="technical",
        expected_priority="urgent",
        expected_team="engineering",
        required_reply_keywords=["incident", "engineering", "urgent"],
        final_action="escalate",
        resolution_value="sev1_incident",
        escalation_note_keywords=["production", "500", "enterprise"],
    ),
    TaskSpec(
        task_id="hard_compliance_data_deletion",
        title="Sensitive data deletion request",
        difficulty=Difficulty.HARD,
        description=(
            "Handle a sensitive account deletion and data erasure request. The agent should route "
            "the request to legal/compliance, set high priority, request identity verification in the reply, "
            "and escalate for secure processing."
        ),
        ticket=Ticket(
            ticket_id="TCK-3014",
            customer_name="Anika Sharma",
            customer_tier="business",
            subject="Delete my account data under privacy law request",
            body=(
                "I want all of my personal data deleted from your systems as soon as possible. "
                "Please confirm the legal process and ensure no further processing happens without my consent."
            ),
            sentiment="serious",
        ),
        expected_intent="compliance",
        expected_priority="high",
        expected_team="legal",
        required_reply_keywords=["verify", "identity", "deletion"],
        final_action="escalate",
        resolution_value="privacy_review",
        escalation_note_keywords=["privacy", "legal", "verification"],
    ),
]


TASK_LOOKUP = {task.task_id: task for task in TASKS}
