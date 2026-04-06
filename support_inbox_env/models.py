from __future__ import annotations

from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ActionType(str, Enum):
    CLASSIFY_INTENT = "classify_intent"
    SET_PRIORITY = "set_priority"
    ASSIGN_TEAM = "assign_team"
    ADD_INTERNAL_NOTE = "add_internal_note"
    REQUEST_MORE_INFO = "request_more_info"
    CHANGE_STATUS = "change_status"
    DRAFT_REPLY = "draft_reply"
    APPLY_REFUND = "apply_refund"
    RESOLVE = "resolve"
    ESCALATE = "escalate"


class Ticket(BaseModel):
    ticket_id: str
    customer_name: str
    customer_tier: str
    subject: str
    body: str
    sentiment: str
    account_region: str = "global"
    recent_orders: List[str] = Field(default_factory=list)


class TaskSpec(BaseModel):
    task_id: str
    title: str
    difficulty: Difficulty
    description: str
    ticket: Ticket
    expected_intent: str
    expected_priority: str
    expected_team: str
    expected_status_flow: List[str] = Field(default_factory=list)
    required_reply_keywords: List[str]
    final_action: Literal["resolve", "escalate"]
    resolution_value: str
    escalation_note_keywords: List[str] = Field(default_factory=list)
    required_internal_note_keywords: List[str] = Field(default_factory=list)
    required_more_info_keywords: List[str] = Field(default_factory=list)
    required_refund_amount: Optional[str] = None
    policy_flags: List[str] = Field(default_factory=list)
    max_turns: int = 8


class SupportAction(BaseModel):
    action_type: ActionType
    value: str = ""
    message: str = ""


class ActionRecord(BaseModel):
    step_index: int
    action_type: ActionType
    value: str = ""
    message: str = ""


class ProgressChecklist(BaseModel):
    intent_done: bool = False
    priority_done: bool = False
    team_done: bool = False
    note_done: bool = False
    status_flow_done: bool = False
    reply_done: bool = False
    policy_done: bool = False
    final_action_done: bool = False


class SupportObservation(BaseModel):
    task_id: str
    title: str
    difficulty: Difficulty
    objective: str
    ticket: Ticket
    checklist: ProgressChecklist
    action_history: List[ActionRecord]
    internal_notes: List[str]
    status_history: List[str]
    current_status: str
    remaining_turns: int
    available_actions: List[ActionType]
    guidance: str


class SupportReward(BaseModel):
    value: float = Field(ge=0.0, le=1.0)
    components: Dict[str, float]
    reasoning: str


class StepResponse(BaseModel):
    observation: SupportObservation
    reward: SupportReward
    done: bool
    info: Dict[str, object]


class EnvironmentState(BaseModel):
    active_task_id: Optional[str] = None
    observation: Optional[SupportObservation] = None
    done: bool = False
    cumulative_score: float = 0.0
    grader_score: float = 0.0


class ResetRequest(BaseModel):
    task_id: Optional[str] = None


class StepRequest(BaseModel):
    action: SupportAction
