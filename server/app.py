from __future__ import annotations

from typing import Optional

from fastapi import FastAPI

from support_inbox_env.environment import SupportInboxEnvironment
from support_inbox_env.models import (
    EnvironmentState,
    ResetRequest,
    StepRequest,
    StepResponse,
    SupportObservation,
)

app = FastAPI(
    title="Support Inbox OpenEnv",
    version="0.1.0",
    description="A deterministic OpenEnv-compatible customer support triage environment.",
)

ENVIRONMENT = SupportInboxEnvironment()


@app.get("/")
def root() -> dict:
    return {
        "name": "support-inbox-openenv",
        "status": "ok",
        "available_endpoints": ["/reset", "/step", "/state", "/tasks"],
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/tasks")
def tasks() -> dict:
    return {"tasks": ENVIRONMENT.list_tasks()}


@app.post("/reset", response_model=SupportObservation)
def reset(request: Optional[ResetRequest] = None) -> SupportObservation:
    task_id = request.task_id if request else None
    return ENVIRONMENT.reset(task_id=task_id)


@app.post("/step", response_model=StepResponse)
def step(request: StepRequest) -> StepResponse:
    return ENVIRONMENT.step(request.action)


@app.get("/state", response_model=EnvironmentState)
def state() -> EnvironmentState:
    return ENVIRONMENT.state()
