from __future__ import annotations

from typing import Optional

import httpx

from support_inbox_env.models import EnvironmentState, StepResponse, SupportAction, SupportObservation


class SupportInboxClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=30.0)

    def reset(self, task_id: Optional[str] = None) -> SupportObservation:
        payload = {"task_id": task_id} if task_id else {}
        response = self._client.post(f"{self.base_url}/reset", json=payload)
        response.raise_for_status()
        return SupportObservation.model_validate(response.json())

    def step(self, action: SupportAction) -> StepResponse:
        response = self._client.post(f"{self.base_url}/step", json={"action": action.model_dump()})
        response.raise_for_status()
        return StepResponse.model_validate(response.json())

    def state(self) -> EnvironmentState:
        response = self._client.get(f"{self.base_url}/state")
        response.raise_for_status()
        return EnvironmentState.model_validate(response.json())
