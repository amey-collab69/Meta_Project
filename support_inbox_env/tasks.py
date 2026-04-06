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
            account_region="india",
            recent_orders=["monthly-plan-renewal"],
        ),
        expected_intent="billing",
        expected_priority="normal",
        expected_team="billing",
        expected_status_flow=["open", "investigating"],
        required_reply_keywords=["refund", "duplicate", "confirm"],
        final_action="resolve",
        resolution_value="refund_started",
        required_internal_note_keywords=["duplicate", "charge"],
        required_refund_amount="19.99",
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
            account_region="us",
            recent_orders=["enterprise-annual-contract", "priority-support-addon"],
        ),
        expected_intent="technical",
        expected_priority="urgent",
        expected_team="engineering",
        expected_status_flow=["open", "investigating"],
        required_reply_keywords=["incident", "engineering", "urgent"],
        final_action="escalate",
        resolution_value="sev1_incident",
        escalation_note_keywords=["production", "500", "enterprise"],
        required_internal_note_keywords=["sev1", "api", "outage"],
        policy_flags=["do_not_resolve_enterprise_outage"],
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
            account_region="eu",
            recent_orders=["business-plan", "audit-log-export"],
        ),
        expected_intent="compliance",
        expected_priority="high",
        expected_team="legal",
        expected_status_flow=["open", "pending_verification"],
        required_reply_keywords=["verify", "identity", "deletion"],
        final_action="escalate",
        resolution_value="privacy_review",
        escalation_note_keywords=["privacy", "legal", "verification"],
        required_internal_note_keywords=["gdpr", "identity", "deletion"],
        required_more_info_keywords=["government", "id", "verify"],
        policy_flags=["identity_verification_required"],
    ),
    TaskSpec(
        task_id="hard_finance_chargeback_risk",
        title="Possible chargeback and fraud escalation",
        difficulty=Difficulty.HARD,
        description=(
            "Handle a possible card fraud and chargeback report. The agent should classify it as billing/fraud, "
            "set urgent priority, route to risk, leave an internal fraud note, request verification from the customer, "
            "and escalate rather than auto-refunding."
        ),
        ticket=Ticket(
            ticket_id="TCK-4021",
            customer_name="Rohan Mehta",
            customer_tier="standard",
            subject="Card charged for plan I never purchased",
            body=(
                "I just saw a card charge from your company for a purchase I did not make. "
                "Please reverse it and investigate immediately because I think this may be fraud."
            ),
            sentiment="alarmed",
            account_region="singapore",
            recent_orders=[],
        ),
        expected_intent="billing",
        expected_priority="urgent",
        expected_team="risk",
        expected_status_flow=["open", "investigating"],
        required_reply_keywords=["verify", "card", "investigate"],
        final_action="escalate",
        resolution_value="fraud_review",
        escalation_note_keywords=["fraud", "chargeback", "card"],
        required_internal_note_keywords=["fraud", "unauthorized", "chargeback"],
        required_more_info_keywords=["last", "four", "verify"],
        policy_flags=["do_not_auto_refund_possible_fraud"],
    ),
]


TASK_LOOKUP = {task.task_id: task for task in TASKS}
