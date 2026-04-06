from __future__ import annotations

from typing import Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

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


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return """
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Support Inbox OpenEnv</title>
        <style>
          body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
          }
          .wrap {
            max-width: 760px;
            margin: 48px auto;
            padding: 24px;
          }
          .card {
            background: #111827;
            border: 1px solid #334155;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 12px 36px rgba(0, 0, 0, 0.28);
          }
          h1 {
            margin-top: 0;
            font-size: 2rem;
          }
          p, li {
            line-height: 1.6;
          }
          code {
            background: #1e293b;
            padding: 2px 6px;
            border-radius: 6px;
          }
          ul {
            padding-left: 20px;
          }
        </style>
      </head>
      <body>
        <div class="wrap">
          <div class="card">
            <h1>Support Inbox OpenEnv</h1>
            <p>The Docker Space is running successfully.</p>
            <p>This environment exposes the OpenEnv-style API endpoints:</p>
            <ul>
              <li><code>GET /health</code></li>
              <li><code>GET /tasks</code></li>
              <li><code>POST /reset</code></li>
              <li><code>POST /step</code></li>
              <li><code>GET /state</code></li>
            </ul>
            <p>Use the API directly for evaluation and the root page as a health check.</p>
          </div>
        </div>
      </body>
    </html>
    """


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


def main() -> None:
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
