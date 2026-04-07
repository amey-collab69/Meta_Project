"""
SupportAI-Env — FastAPI Server (Advanced Production Version 3.0)
Features: Database persistence, authentication, analytics, advanced grading,
rate limiting, security, batch processing, and real-time WebSocket updates
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, Header
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List
import uuid
import time
import asyncio
import json
from collections import defaultdict
import logging
from datetime import datetime

from env import SupportEnv, Action
from tasks import TASKS
from grader import grade
from database import db, SessionRecord
from analytics import analytics, exporter
from security import security, rate_limiter, validator
from advanced_grader import grader, batch_grader

# ─── Logging Setup ──────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SupportAI-Env",
    version="3.0.0",
    description="Advanced Customer Support AI Training Platform with Database, Analytics, and Security"
)

# ─── Middleware ───────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_sessions: Dict[str, Dict] = {}
_metrics: Dict[str, any] = {
    "total_sessions": 0,
    "total_steps": 0,
    "total_resets": 0,
    "avg_response_time_ms": 0.0,
    "active_sessions": 0,
    "task_counts": defaultdict(int),
    "start_time": time.time(),
}
_response_times: List[float] = []

# WebSocket connections for real-time updates
_active_connections: Dict[str, WebSocket] = {}

# ─── Schemas ─────────────────────────────────────────────────────────────────

class ResetRequest(BaseModel):
    task_id: str = "easy"
    session_id: Optional[str] = None

class CustomResetRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class StepRequest(BaseModel):
    session_id: str
    action_type: str
    content: Optional[str] = ""

class HealthResponse(BaseModel):
    status: str
    uptime_seconds: float
    active_sessions: int
    total_sessions: int

class MetricsResponse(BaseModel):
    total_sessions: int
    total_steps: int
    total_resets: int
    avg_response_time_ms: float
    active_sessions: int
    task_counts: Dict[str, int]
    uptime_seconds: float

# ─── Authentication Schemas ──────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    email: Optional[str] = None
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str

# ─── Export Schemas ─────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    format: str = "json"  # json, csv
    include_sessions: bool = True

# ─── Helper Functions ────────────────────────────────────────────────────────

def _track_response_time(duration_ms: float):
    """Track response time for metrics."""
    _response_times.append(duration_ms)
    if len(_response_times) > 1000:  # Keep last 1000 measurements
        _response_times.pop(0)
    _metrics["avg_response_time_ms"] = sum(_response_times) / len(_response_times)

def _update_metrics(action: str, task_id: Optional[str] = None):
    """Update system metrics."""
    if action == "reset":
        _metrics["total_resets"] += 1
        _metrics["total_sessions"] += 1
        if task_id:
            _metrics["task_counts"][task_id] += 1
    elif action == "step":
        _metrics["total_steps"] += 1
    _metrics["active_sessions"] = len(_sessions)

async def _broadcast_update(session_id: str, data: dict):
    """Broadcast update to connected WebSocket clients."""
    if session_id in _active_connections:
        try:
            await _active_connections[session_id].send_json(data)
        except:
            pass  # Connection closed

# ─── API Endpoints ────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint for monitoring."""
    uptime = time.time() - _metrics["start_time"]
    return HealthResponse(
        status="healthy",
        uptime_seconds=round(uptime, 2),
        active_sessions=len(_sessions),
        total_sessions=_metrics["total_sessions"]
    )

@app.get("/metrics", response_model=MetricsResponse)
def get_metrics():
    """Get system metrics."""
    uptime = time.time() - _metrics["start_time"]
    return MetricsResponse(
        total_sessions=_metrics["total_sessions"],
        total_steps=_metrics["total_steps"],
        total_resets=_metrics["total_resets"],
        avg_response_time_ms=round(_metrics["avg_response_time_ms"], 2),
        active_sessions=len(_sessions),
        task_counts=dict(_metrics["task_counts"]),
        uptime_seconds=round(uptime, 2)
    )

# ─── Authentication Endpoints ────────────────────────────────────────────────

@app.post("/auth/register", response_model=TokenResponse)
def register(req: RegisterRequest):
    """Register a new user."""
    # Validate inputs
    username_valid, username_err = validator.validate_username(req.username)
    if not username_valid:
        raise HTTPException(status_code=400, detail=username_err)
    
    if req.email:
        email_valid, email_err = validator.validate_email(req.email)
        if not email_valid:
            raise HTTPException(status_code=400, detail=email_err)
    
    password_valid, password_err = validator.validate_password(req.password)
    if not password_valid:
        raise HTTPException(status_code=400, detail=password_err)
    
    # Check if user already exists
    existing = db.get_user(req.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")
    
    # Create user
    user_id = str(uuid.uuid4())
    password_hash, _ = security.hash_password(req.password)
    
    db.create_user(user_id, req.username, req.email, password_hash)
    
    # Create token
    token = security.create_token(user_id, req.username)
    
    logger.info(f"New user registered: {req.username}")
    
    return TokenResponse(access_token=token, username=req.username)

@app.post("/auth/login", response_model=TokenResponse)
def login(req: LoginRequest):
    """Login user."""
    # Validate username format
    username_valid, _ = validator.validate_username(req.username)
    if not username_valid:
        raise HTTPException(status_code=400, detail="Invalid username")
    
    # Check user exists
    user = db.get_user(req.username)
    if not user or not security.verify_password(req.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create token
    token = security.create_token(user["user_id"], req.username)
    logger.info(f"User logged in: {req.username}")
    
    return TokenResponse(access_token=token, username=req.username)

def verify_token(request: Request) -> str:
    """Helper to verify token and extract user_id."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = auth_header[7:]
    payload = security.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return payload.get("user_id")

# ─── Analytics Endpoints ────────────────────────────────────────────────────

@app.get("/analytics/user")
def get_user_analytics(request: Request):
    """Get analytics for current user."""
    user_id = verify_token(request)
    analysis = analytics.analyze_user(user_id)
    return analysis

@app.get("/analytics/task/{task_id}")
def get_task_analytics(task_id: str):
    """Get analytics for a specific task across all users."""
    report = analytics.task_performance_report(task_id)
    return report

@app.get("/analytics/leaderboard")
def get_leaderboard(limit: int = 50):
    """Get global leaderboard."""
    db.refresh_leaderboard(limit)
    leaderboard = db.get_leaderboard(limit)
    return {"leaderboard": leaderboard, "total": len(leaderboard)}

# ─── Export & Report Endpoints ──────────────────────────────────────────────

@app.post("/export/report")
def export_user_report(req: ExportRequest, request: Request):
    """Export user data as report."""
    user_id = verify_token(request)
    
    report = exporter.generate_report(user_id, include_sessions=req.include_sessions)
    
    if req.format == "csv":
        sessions = report.get("sessions", [])
        csv_data = exporter.to_csv(sessions)
        return {"format": "csv", "data": csv_data}
    else:
        return report

@app.get("/export/sessions")
def list_user_sessions(request: Request, limit: int = 100):
    """Get user's session history."""
    user_id = verify_token(request)
    sessions = db.get_user_sessions(user_id, limit=limit)
    return {
        "user_id": user_id,
        "total_sessions": len(sessions),
        "sessions": [
            {
                "session_id": s["session_id"],
                "task_id": s["task_id"],
                "status": s["status"],
                "final_score": s["final_score"],
                "grade_label": s["grade_label"],
                "step_count": s["step_count"],
                "created_at": s["created_at"]
            }
            for s in sessions
        ]
    }

# ─── Enhanced Reset with Database Persistence ───────────────────────────────

@app.post("/reset")
async def reset(req: Optional[ResetRequest] = None, request: Request = None):
    """Reset a session (optionally authenticated)."""
    start_time = time.time()
    
    # Rate limiting
    client_id = request.client.host if request else "unknown"
    allowed, rate_info = rate_limiter.is_allowed(client_id)
    if not allowed:
        raise HTTPException(status_code=429, detail="Too many requests")
    
    # Get user_id if authenticated
    user_id = None
    if request and request.headers.get("Authorization"):
        try:
            user_id = verify_token(request)
        except:
            pass  # Allow anonymous usage
    
    # Get task_id from request or use default
    task_id = req.task_id if req else "easy"
    session_id = req.session_id if req else None
    
    if task_id not in TASKS:
        raise HTTPException(status_code=400, detail=f"Unknown task_id '{task_id}'. Choose: easy, medium, hard")
    
    session_id = session_id or str(uuid.uuid4())
    task = TASKS[task_id]
    env = SupportEnv(task)
    obs = env.reset()
    
    # Store in database
    db_session = db.create_session(session_id, task_id, user_id)
    
    _sessions[session_id] = {
        "env": env,
        "task": task,
        "done": False,
        "created_at": time.time(),
        "last_activity": time.time(),
        "user_id": user_id,
        "db_session": db_session
    }
    
    duration_ms = (time.time() - start_time) * 1000
    _track_response_time(duration_ms)
    _update_metrics("reset", task_id)
    
    result = {
        "session_id": session_id,
        "task": task_id,
        "observation": obs.model_dump(),
        "processing_time_ms": round(duration_ms, 2),
        "type": "reset"
    }
    
    if user_id:
        logger.info(f"Session {session_id} started by user {user_id}")
    
    await _broadcast_update(session_id, result)
    return result

@app.post("/custom_reset")
async def custom_reset(req: CustomResetRequest):
    """Start a session with a custom user-typed message (enhanced)."""
    start_time = time.time()
    
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    session_id = req.session_id or str(uuid.uuid4())
    
    # Build a dynamic task from the custom message
    from env import detect_intent
    intent = detect_intent(req.message)
    
    # Map intent to closest task workflow
    workflow_map = {
        "delivery_issue": ["ask_details", "reply"],
        "refund":         ["ask_details", "ask_details", "refund"],
        "product_issue":  ["ask_details", "refund"],
        "complaint":      ["reply", "ask_details", "refund", "reply"],
        "general":        ["reply"],
    }
    workflow = workflow_map.get(intent, ["ask_details", "reply"])
    
    task = {
        "id": "custom",
        "name": "Custom Problem",
        "difficulty": "custom",
        "initial_message": req.message.strip(),
        "expected_intent": intent,
        "expected_workflow": workflow,
        "max_steps": max(len(workflow) * 2, 6),
        "success_condition": "RESOLUTION",
        "scoring": {"full_score": 1.0, "partial_score": 0.5, "fail_score": 0.0},
    }
    
    env = SupportEnv(task)
    obs = env.reset()
    _sessions[session_id] = {
        "env": env,
        "task": task,
        "done": False,
        "created_at": time.time(),
        "last_activity": time.time()
    }
    
    duration_ms = (time.time() - start_time) * 1000
    _track_response_time(duration_ms)
    _update_metrics("reset", "custom")
    
    result = {
        "session_id": session_id,
        "task": "custom",
        "observation": obs.model_dump(),
        "processing_time_ms": round(duration_ms, 2),
        "type": "custom_reset"
    }
    await _broadcast_update(session_id, result)
    return result

@app.post("/step")
async def step(req: StepRequest):
    """Execute an action step with advanced grading and database persistence."""
    start_time = time.time()
    
    # Rate limiting
    allowed, rate_info = rate_limiter.is_allowed("step")
    if not allowed:
        raise HTTPException(status_code=429, detail="Too many requests")
    
    session = _sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found. Call /reset first.")
    if session["done"]:
        raise HTTPException(status_code=400, detail="Episode is done. Call /reset to start a new one.")

    env: SupportEnv = session["env"]
    action = Action(action_type=req.action_type, content=req.content or "", timestamp=time.time())
    obs, reward, done, info = env.step(action)
    session["done"] = done
    session["last_activity"] = time.time()

    logger.info(f"Action: {req.action_type} | Reward: {reward} | Done: {done}")

    result = {
        "session_id": req.session_id,
        "observation": obs.model_dump(),
        "reward": reward,
        "done": done,
        "info": info,
    }
    
    if done:
        # Use advanced grader for more detailed feedback
        grade_result = grader.grade_comprehensive(
            task=session["task"],
            action_history=env._action_history,
            total_reward=env.total_reward(),
            final_state=obs.current_state,
            step_count=obs.step_count,
            intent_detected=obs.intent,
            tone=obs.sentiment,
        )
        
        result["grade"] = grade_result
        
        # Persist to database
        user_id = session.get("user_id")
        db.update_session(
            req.session_id,
            status="completed",
            final_score=grade_result.get("final_score", 0.0),
            grade_label=grade_result.get("label", ""),
            step_count=obs.step_count,
            total_reward=env.total_reward(),
            action_history=env._action_history
        )
        
        # Update user stats if authenticated
        if user_id:
            db.update_user_stats(user_id)
        
        logger.info(f"Session {req.session_id} completed with grade: {grade_result.get('label')}")
    
    duration_ms = (time.time() - start_time) * 1000
    _track_response_time(duration_ms)
    _update_metrics("step")
    result["api_processing_time_ms"] = round(duration_ms, 2)
    await _broadcast_update(req.session_id, result)
    
    return result

@app.get("/state")
def get_state(session_id: str):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    env: SupportEnv = session["env"]
    session["last_activity"] = time.time()
    
    return {
        "session_id": session_id,
        "observation": env.state().model_dump(),
        "done": session["done"],
        "total_reward": env.total_reward(),
        "session_age_seconds": round(time.time() - session["created_at"], 2),
        "last_activity_seconds_ago": round(time.time() - session["last_activity"], 2)
    }

@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    """Delete a session to free up resources."""
    if session_id in _sessions:
        del _sessions[session_id]
        return {"status": "deleted", "session_id": session_id}
    raise HTTPException(status_code=404, detail="Session not found.")

@app.get("/sessions")
def list_sessions():
    """List all active sessions."""
    return {
        "active_sessions": len(_sessions),
        "sessions": [
            {
                "session_id": sid,
                "task": s["task"]["id"],
                "done": s["done"],
                "age_seconds": round(time.time() - s["created_at"], 2),
        "last_activity_seconds_ago": round(time.time() - s["last_activity"], 2)
            }
            for sid, s in _sessions.items()
        ]
    }

# ─── Advanced Grading Endpoints ──────────────────────────────────────────────

@app.post("/grade/batch")
def batch_grade(sessions: List[Dict]):
    """Grade multiple sessions at once with aggregate statistics."""
    if not sessions or len(sessions) == 0:
        raise HTTPException(status_code=400, detail="No sessions provided")
    
    # Limit to prevent abuse
    if len(sessions) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 sessions per batch")
    
    result = batch_grader.grade_batch(sessions)
    return result

@app.get("/api/info")
def api_info():
    """Get API information and available endpoints."""
    return {
        "title": "SupportAI-Env Advanced API",
        "version": "3.0.0",
        "description": "Customer Support AI Training Platform",
        "endpoints": {
            "authentication": [
                "POST /auth/register - Register new user",
                "POST /auth/login - Login user"
            ],
            "sessions": [
                "POST /reset - Start new session",
                "POST /custom_reset - Start custom scenario",
                "POST /step - Execute action",
                "GET /state - Get current state",
                "GET /sessions - List active",
                "DELETE /session/{id} - Delete session"
            ],
            "analytics": [
                "GET /analytics/user - User performance",
                "GET /analytics/task/{id} - Task analytics",
                "GET /analytics/leaderboard - Global leaderboard"
            ],
            "export": [
                "POST /export/report - Export user report",
                "GET /export/sessions - Get session history"
            ],
            "grading": [
                "POST /grade/batch - Batch grade sessions"
            ],
            "monitoring": [
                "GET /health - Health status",
                "GET /metrics - System metrics",
                "GET /task_catalog - Available tasks"
            ]
        },
        "features": [
            "Persistent database storage",
            "User authentication & authorization",
            "Advanced analytics & insights",
            "Real-time WebSocket updates",
            "Rate limiting & security",
            "Detailed grading with feedback",
            "Data export (JSON/CSV)",
            "Leaderboards"
        ]
    }

# ─── Health & Monitoring ────────────────────────────────────────────────────

@app.get("/system/info")
def system_info():
    """Get detailed system information."""
    uptime = time.time() - _metrics["start_time"]
    
    # Clean up old rate limit buckets
    rate_limiter.cleanup_old_buckets()
    
    # Clean up expired tokens
    security.cleanup_expired_tokens()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": round(uptime, 2),
        "uptime_formatted": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m",
        "memory": {
            "active_sessions": len(_sessions),
            "active_tokens": len(security.active_tokens),
            "rate_limit_buckets": len(rate_limiter.buckets)
        },
        "metrics": {
            "total_sessions": _metrics["total_sessions"],
            "total_steps": _metrics["total_steps"],
            "avg_response_time_ms": round(_metrics["avg_response_time_ms"], 2)
        }
    }

# ─── WebSocket ────────────────────────────────────────────────────────────
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    _active_connections[session_id] = websocket
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        _active_connections.pop(session_id, None)

def _serialize_task(task: Dict) -> Dict:
    """Return frontend-safe task metadata."""
    return {
        "id": task["id"],
        "name": task["name"],
        "difficulty": task["difficulty"],
        "initial_message": task["initial_message"],
        "expected_intent": task["expected_intent"],
        "expected_workflow": task["expected_workflow"],
        "max_steps": task["max_steps"],
        "success_condition": task["success_condition"],
        "description": task.get("description", ""),
        "multi_intent": task.get("multi_intent", []),
        "requires_tone_handling": task.get("requires_tone_handling", False),
        "scoring": task.get("scoring", {}),
    }

@app.get("/task_catalog")
def task_catalog():
    """Expose task metadata for richer frontend rendering."""
    return {
        "tasks": [_serialize_task(task) for task in TASKS.values()],
        "supported_actions": ["reply", "ask_details", "refund", "escalate"],
    }

# ─── GUI ──────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def gui():
    task_payload = {task_id: _serialize_task(task) for task_id, task in TASKS.items()}
    return HTMLResponse(content=build_gui_html(task_payload))

def build_gui_html(task_payload: Dict[str, Dict]) -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>SupportAI-Env Control Center</title>
<style>
:root{
  --bg:#f4efe7;
  --ink:#1f2937;
  --muted:#6b7280;
  --panel:#fffdf9;
  --panel-strong:#fffaf2;
  --line:rgba(64,48,32,.12);
  --shadow:0 24px 70px rgba(53,33,13,.12);
  --brand:#c56a1a;
  --brand-deep:#8b4513;
  --teal:#17594a;
  --green:#207d52;
  --red:#b85042;
  --gold:#f3b84b;
}
*{box-sizing:border-box}
html,body{margin:0;min-height:100%}
body{
  font-family:Georgia,"Times New Roman",serif;
  color:var(--ink);
  background:
    radial-gradient(circle at top left, rgba(243,184,75,.35), transparent 28%),
    radial-gradient(circle at top right, rgba(23,89,74,.12), transparent 22%),
    linear-gradient(180deg, #f9f4ec 0%, #f2ece2 45%, #efe7db 100%);
}
.shell{max-width:1480px;margin:0 auto;padding:28px 22px 32px}
.hero{
  background:linear-gradient(135deg, rgba(255,250,242,.96), rgba(250,240,225,.94));
  border:1px solid var(--line);
  border-radius:28px;
  box-shadow:var(--shadow);
  padding:28px;
  position:relative;
  overflow:hidden;
}
.hero:before{
  content:"";
  position:absolute;
  inset:auto -8% -35% auto;
  width:360px;height:360px;border-radius:999px;
  background:radial-gradient(circle, rgba(197,106,26,.16), rgba(197,106,26,0));
}
.eyebrow{display:inline-flex;align-items:center;gap:10px;padding:8px 14px;border-radius:999px;background:rgba(197,106,26,.10);color:var(--brand-deep);font:600 12px/1.2 "Trebuchet MS",sans-serif;letter-spacing:.14em;text-transform:uppercase}
.hero-grid{display:grid;grid-template-columns:1.35fr .9fr;gap:22px;margin-top:18px}
.hero h1{margin:0;font-size:clamp(2.4rem,4vw,4.4rem);line-height:.95;letter-spacing:-.04em}
.hero p{margin:14px 0 0;font:500 17px/1.6 "Trebuchet MS",sans-serif;color:#51473d;max-width:66ch}
.status-row,.meta-row,.stat-grid,.task-grid,.content-grid,.mini-grid,.state-grid,.timeline,.actions-grid,.event-list{display:grid;gap:14px}
.status-row{grid-template-columns:repeat(4,minmax(0,1fr));margin-top:22px}
.metric,.panel,.task-card,.action-card,.timeline-card,.msg,.event-card{
  background:rgba(255,253,249,.88);
  border:1px solid var(--line);
  border-radius:22px;
  box-shadow:0 10px 30px rgba(91,66,32,.06);
}
.metric{padding:18px}
.metric .label{font:600 12px/1.2 "Trebuchet MS",sans-serif;color:var(--muted);text-transform:uppercase;letter-spacing:.12em}
.metric .value{margin-top:10px;font-size:2rem}
.metric .sub{margin-top:8px;font:500 13px/1.4 "Trebuchet MS",sans-serif;color:var(--muted)}
.hero-side{display:flex;flex-direction:column;gap:16px}
.stack{display:flex;flex-wrap:wrap;gap:10px}
.badge{display:inline-flex;align-items:center;gap:8px;padding:10px 14px;border-radius:999px;background:#fff7ea;border:1px solid rgba(197,106,26,.16);font:600 12px/1.2 "Trebuchet MS",sans-serif;color:#744315;letter-spacing:.08em;text-transform:uppercase}
.pill-online{background:#edf8f0;color:var(--green);border-color:rgba(32,125,82,.16)}
.pill-warn{background:#fff2df;color:#9b5a15}
.pill-offline{background:#fdeceb;color:var(--red)}
.shell-section{margin-top:24px}
.content-grid{grid-template-columns:1.05fr 1.2fr .9fr;align-items:start}
.panel{padding:20px}
.panel h2,.panel h3{margin:0 0 14px}
.panel h2{font-size:1.4rem}
.panel h3{font-size:1.02rem}
.panel-copy{font:500 14px/1.7 "Trebuchet MS",sans-serif;color:#5c5146}
.task-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
.task-card{padding:18px;cursor:pointer;transition:transform .18s ease, border-color .18s ease, box-shadow .18s ease}
.task-card:hover{transform:translateY(-2px);border-color:rgba(197,106,26,.35)}
.task-card.active{border-color:rgba(197,106,26,.52);box-shadow:0 14px 34px rgba(197,106,26,.12)}
.task-top{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}
.task-name{font-size:1.16rem;margin:2px 0 8px}
.task-chip{padding:6px 10px;border-radius:999px;font:700 11px/1 "Trebuchet MS",sans-serif;letter-spacing:.12em;text-transform:uppercase}
.easy{background:#edf8f0;color:var(--green)}
.medium{background:#fff5e4;color:#9b5a15}
.hard{background:#fdeceb;color:var(--red)}
.task-meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.micro{padding:6px 10px;border-radius:999px;background:#f5efe5;font:600 11px/1 "Trebuchet MS",sans-serif;color:#665748}
.task-desc{font:500 14px/1.6 "Trebuchet MS",sans-serif;color:#54493f}
.feature-list,.workflow-list,.event-list{margin:0;padding:0;list-style:none}
.feature-list li,.workflow-list li,.event-card,.state-item,.rubric-item{font:500 14px/1.55 "Trebuchet MS",sans-serif}
.feature-list li,.rubric-item,.state-item{padding:12px 14px;border-radius:16px;background:var(--panel-strong);border:1px solid rgba(64,48,32,.08)}
.mini-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
.state-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
.state-item strong,.rubric-item strong{display:block;font:700 11px/1.2 "Trebuchet MS",sans-serif;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-bottom:8px}
.workflow-list{display:grid;gap:10px}
.workflow-step{display:flex;gap:12px;align-items:flex-start;padding:12px 14px;border-radius:18px;background:#f8f1e8;border:1px solid rgba(64,48,32,.08)}
.workflow-step.active{background:#fff4dc;border-color:rgba(197,106,26,.28)}
.workflow-step.done{background:#eef8f0;border-color:rgba(32,125,82,.18)}
.step-index{flex:0 0 34px;height:34px;border-radius:999px;background:#fff;border:1px solid rgba(64,48,32,.10);display:grid;place-items:center;font:700 13px/1 "Trebuchet MS",sans-serif}
.step-copy{display:flex;flex-direction:column;gap:4px}
.step-copy span{font-size:15px;color:#2b241f}
.step-copy small{font-size:12px;color:var(--muted);font-family:"Trebuchet MS",sans-serif}
.timeline{grid-template-columns:minmax(0,1fr)}
.timeline-card{padding:18px}
.guide-box{padding:14px 16px;border-radius:18px;background:linear-gradient(135deg,#fff5de,#fff9ef);border:1px solid rgba(197,106,26,.16)}
.guide-label{font:700 11px/1.2 "Trebuchet MS",sans-serif;letter-spacing:.14em;text-transform:uppercase;color:#8b5d24}
.guide-text{margin-top:8px;font:600 15px/1.5 "Trebuchet MS",sans-serif;color:#503f2f}
.messages{display:flex;flex-direction:column;gap:12px;max-height:560px;overflow:auto;padding-right:4px}
.msg{padding:16px 18px}
.msg.customer{border-left:4px solid #8b4513}
.msg.agent{border-left:4px solid var(--teal)}
.msg.system{border-left:4px solid #9b8d7d}
.msg.success{border-left:4px solid var(--green);background:#f0faf4}
.msg.error-msg{border-left:4px solid var(--red);background:#fef2f1}
.msg-head{display:flex;align-items:center;justify-content:space-between;gap:12px}
.msg-role{font:700 11px/1.2 "Trebuchet MS",sans-serif;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.msg-body{margin-top:8px;font-size:1rem;line-height:1.6}
.msg-meta{margin-top:10px;font:600 12px/1.5 "Trebuchet MS",sans-serif;color:#736452}
.actions-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
.action-card{padding:14px;text-align:left;cursor:pointer;transition:border-color .16s ease, transform .16s ease, background .16s ease}
.action-card:hover:not(:disabled){transform:translateY(-2px);border-color:rgba(197,106,26,.34)}
.action-card:disabled{opacity:.45;cursor:not-allowed}
.action-card.active-suggestion{background:#fff2d4;border-color:rgba(197,106,26,.42)}
.action-card strong{display:block;font-size:1rem}
.action-card span{display:block;margin-top:6px;font:500 13px/1.5 "Trebuchet MS",sans-serif;color:#665748}
.composer{margin-top:16px}
.composer textarea,.custom-box textarea{
  width:100%;min-height:110px;resize:vertical;border-radius:18px;padding:14px 16px;
  border:1px solid rgba(64,48,32,.12);background:#fffefb;color:var(--ink);
  font:500 15px/1.55 "Trebuchet MS",sans-serif;
}
.composer textarea:focus,.custom-box textarea:focus{outline:none;border-color:rgba(197,106,26,.44);box-shadow:0 0 0 4px rgba(197,106,26,.08)}
.composer-note{margin-top:10px;font:500 12px/1.5 "Trebuchet MS",sans-serif;color:var(--muted)}
.primary-btn{
  border:none;border-radius:16px;padding:13px 18px;background:linear-gradient(135deg,var(--brand),#df8d36);color:#fff;
  font:700 14px/1 "Trebuchet MS",sans-serif;letter-spacing:.04em;cursor:pointer;box-shadow:0 14px 28px rgba(197,106,26,.22)
}
.secondary-btn{
  border:1px solid rgba(64,48,32,.12);border-radius:16px;padding:12px 16px;background:#fffaf1;color:#513b28;
  font:700 13px/1 "Trebuchet MS",sans-serif;cursor:pointer
}
.btn-row{display:flex;flex-wrap:wrap;gap:10px;margin-top:14px}
.event-list{display:grid;gap:10px;max-height:420px;overflow:auto}
.event-card{padding:12px 14px}
.event-card strong{display:block;font:700 11px/1.2 "Trebuchet MS",sans-serif;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.event-card span{display:block;margin-top:8px;color:#40372f}
.event-card small{display:block;margin-top:6px;color:var(--muted)}
.custom-box{margin-top:16px;padding:16px;border-radius:22px;background:#fff8ef;border:1px dashed rgba(197,106,26,.28)}
.helper{font:500 13px/1.5 "Trebuchet MS",sans-serif;color:var(--muted)}
@media (max-width:1180px){
  .hero-grid,.content-grid{grid-template-columns:1fr}
}
@media (max-width:760px){
  .shell{padding:18px 14px 28px}
  .status-row,.task-grid,.mini-grid,.state-grid,.actions-grid{grid-template-columns:1fr}
  .hero{padding:22px}
  .metric .value{font-size:1.6rem}
}
</style>
</head>
<body>
<div class="shell">
  <section class="hero">
    <div class="eyebrow">SupportAI Env • Advanced Review Lab</div>
    <div class="hero-grid">
      <div>
        <h1>Modern support-agent evaluation, with the workflow details visible.</h1>
        <p>
          Run guided customer-support simulations, inspect intent and tone detection, track reward quality in real time,
          and review each step like a product-grade operations console.
        </p>
        <div class="status-row">
          <div class="metric">
            <div class="label">Session</div>
            <div class="value" id="session-badge">No active run</div>
            <div class="sub" id="task-badge">Choose a benchmark scenario to begin.</div>
          </div>
          <div class="metric">
            <div class="label">Reward</div>
            <div class="value" id="total-reward">0.0000</div>
            <div class="sub" id="step-info">0 steps completed</div>
          </div>
          <div class="metric">
            <div class="label">Latency</div>
            <div class="value" id="perf-badge">0ms</div>
            <div class="sub" id="latency-detail">Awaiting first request</div>
          </div>
          <div class="metric">
            <div class="label">System</div>
            <div class="value" id="status-badge">Online</div>
            <div class="sub" id="uptime-badge">Uptime: --</div>
          </div>
        </div>
      </div>
      <div class="hero-side">
        <div class="panel">
          <h2>Live Bench Summary</h2>
          <div class="mini-grid">
            <div class="rubric-item"><strong>Total Sessions</strong><span id="m-total-sessions">0</span></div>
            <div class="rubric-item"><strong>Active Sessions</strong><span id="m-active-sessions">0</span></div>
            <div class="rubric-item"><strong>Total Steps</strong><span id="m-total-steps">0</span></div>
            <div class="rubric-item"><strong>Avg Response</strong><span id="m-avg-time">0ms</span></div>
          </div>
        </div>
        <div class="panel">
          <h2>Evaluation Focus</h2>
          <ul class="feature-list">
            <li>Deterministic intent detection keeps grading stable and testable.</li>
            <li>Tone awareness adds realism without taking control of rewards or transitions.</li>
            <li>Workflow guidance, rubric detail, and event logging make each run easier to inspect.</li>
          </ul>
        </div>
      </div>
    </div>
  </section>

  <section class="shell-section content-grid">
    <div class="panel">
      <h2>Scenario Library</h2>
      <p class="panel-copy">Each benchmark includes workflow expectations, difficulty, intent targets, and resolution rules. Start from a preset or load your own customer message.</p>
      <div class="task-grid" id="task-grid"></div>
      <div class="custom-box">
        <h3>Custom Scenario</h3>
        <p class="helper">Paste a customer issue and the environment will infer the closest workflow so you can test open-ended responses.</p>
        <textarea id="custom-msg" placeholder="Example: My package is late, the product arrived damaged, and I need a refund."></textarea>
        <div class="btn-row">
          <button class="primary-btn" onclick="startCustomTask()">Start Custom Run</button>
        </div>
      </div>
    </div>

    <div class="timeline">
      <div class="timeline-card">
        <h2 id="detail-title">Scenario Details</h2>
        <p class="panel-copy" id="detail-description">Select a task to inspect its expected handling workflow, scoring, and operational notes.</p>
        <div class="guide-box">
          <div class="guide-label" id="step-num">Ready State</div>
          <div class="guide-text" id="guide-text">Pick a benchmark and the interface will guide the next best action.</div>
        </div>
        <div class="shell-section">
          <h3>Expected Workflow</h3>
          <ul class="workflow-list" id="workflow-list"></ul>
        </div>
        <div class="shell-section">
          <h3>Conversation Stream</h3>
          <div class="messages" id="messages">
            <div class="msg system">
              <div class="msg-head"><div class="msg-role">System</div></div>
              <div class="msg-body">Select a scenario from the library to launch a run. The chat, scoring, and workflow tracker will populate automatically.</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="panel">
      <h2>Run Console</h2>
      <div class="state-grid">
        <div class="state-item"><strong>Current State</strong><span id="s-state">--</span></div>
        <div class="state-item"><strong>Detected Intent</strong><span id="s-intent">--</span></div>
        <div class="state-item"><strong>Customer Tone</strong><span id="s-tone">--</span></div>
        <div class="state-item"><strong>Episode Status</strong><span id="s-done">Not started</span></div>
        <div class="state-item"><strong>Step Count</strong><span id="s-step">0</span></div>
        <div class="state-item"><strong>Grade Snapshot</strong><span id="score-info">No grade yet</span></div>
      </div>

      <div class="shell-section">
        <h3>Action Palette</h3>
        <div class="actions-grid">
          <button class="action-card" id="btn-reply" onclick="sendAction('reply')" disabled>
            <strong>Reply</strong>
            <span>Send a direct support response to acknowledge or close the issue.</span>
          </button>
          <button class="action-card" id="btn-ask" onclick="sendAction('ask_details')" disabled>
            <strong>Ask Details</strong>
            <span>Request the order number, proof, or extra context before resolving.</span>
          </button>
          <button class="action-card" id="btn-refund" onclick="sendAction('refund')" disabled>
            <strong>Refund</strong>
            <span>Process the monetary resolution when the workflow justifies it.</span>
          </button>
          <button class="action-card" id="btn-escalate" onclick="sendAction('escalate')" disabled>
            <strong>Escalate</strong>
            <span>Route the issue onward if the current agent should not own the resolution.</span>
          </button>
        </div>
        <div class="composer">
          <textarea id="msg-input" placeholder="Compose the agent reply here. A typed message is required when you choose Reply."></textarea>
          <div class="composer-note">Tip: use empathetic acknowledgment first for angry customers, then move into details or resolution.</div>
        </div>
      </div>

      <div class="shell-section">
        <h3>Task Brief</h3>
        <ul class="feature-list" id="brief-list"></ul>
      </div>

      <div class="shell-section">
        <h3>Run Events</h3>
        <div class="event-list" id="event-log"></div>
      </div>
    </div>
  </section>
</div>

<script>
const TASK_DATA = __TASK_DATA__;
const ACTION_LABELS = {
  reply: "Reply to the customer with guidance or closure",
  ask_details: "Ask for supporting order or issue details",
  refund: "Issue a refund or reimbursement",
  escalate: "Escalate to a specialized queue"
};

let sessionId = null;
let currentTask = "easy";
let stepNum = 0;
let isDone = false;
let metricsTimer = null;

function titleCase(value) {
  return String(value || "--").replace(/_/g, " ").replace(/\\b\\w/g, c => c.toUpperCase());
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function workflowGuide(task) {
  if (!task || !Array.isArray(task.expected_workflow)) {
    return ["Follow the environment workflow carefully."];
  }
  return task.expected_workflow.map((action, index) => {
    return "Step " + (index + 1) + ": " + ACTION_LABELS[action];
  }).concat(["Run complete: review grade and event log."]);
}

function renderTaskCards() {
  const grid = document.getElementById("task-grid");
  grid.innerHTML = "";
  Object.values(TASK_DATA).forEach((task) => {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "task-card" + (task.id === currentTask ? " active" : "");
    card.onclick = () => startTask(task.id);
    card.innerHTML = `
      <div class="task-top">
        <div>
          <div class="task-name">${escapeHtml(task.name)}</div>
          <div class="task-desc">${escapeHtml(task.description || "Scenario details not provided.")}</div>
        </div>
        <span class="task-chip ${escapeHtml(task.difficulty)}">${escapeHtml(task.difficulty)}</span>
      </div>
      <div class="task-meta">
        <span class="micro">Intent: ${escapeHtml(titleCase(task.expected_intent))}</span>
        <span class="micro">Steps: ${escapeHtml(task.expected_workflow.length)} / max ${escapeHtml(task.max_steps)}</span>
        <span class="micro">Finish: ${escapeHtml(titleCase(task.success_condition))}</span>
      </div>
    `;
    grid.appendChild(card);
  });
}

function renderTaskDetails(taskId) {
  const task = TASK_DATA[taskId];
  const detailTitle = document.getElementById("detail-title");
  const detailDescription = document.getElementById("detail-description");
  const workflowList = document.getElementById("workflow-list");
  const briefList = document.getElementById("brief-list");

  if (!task) return;

  detailTitle.textContent = task.name + " Overview";
  detailDescription.textContent = task.description || "No description available.";
  workflowList.innerHTML = "";
  briefList.innerHTML = "";

  task.expected_workflow.forEach((action, index) => {
    const li = document.createElement("li");
    li.className = "workflow-step" + (index < stepNum ? " done" : index === stepNum && !isDone ? " active" : "");
    li.innerHTML = `
      <div class="step-index">${index + 1}</div>
      <div class="step-copy">
        <span>${escapeHtml(titleCase(action))}</span>
        <small>${escapeHtml(ACTION_LABELS[action] || "Take the appropriate next action.")}</small>
      </div>
    `;
    workflowList.appendChild(li);
  });

  const items = [
    "Initial customer message: " + task.initial_message,
    "Expected intent: " + titleCase(task.expected_intent),
    "Resolution target: " + titleCase(task.success_condition),
    "Scoring rubric: full " + task.scoring.full_score + ", partial " + task.scoring.partial_score + ", fail " + task.scoring.fail_score
  ];

  if (task.multi_intent && task.multi_intent.length) {
    items.push("Multi-intent coverage: " + task.multi_intent.map(titleCase).join(", "));
  }
  if (task.requires_tone_handling) {
    items.push("Tone handling matters here: the agent should acknowledge customer emotion before resolving.");
  }

  items.forEach((copy) => {
    const li = document.createElement("li");
    li.textContent = copy;
    briefList.appendChild(li);
  });
}

function setButtons(disabled) {
  ["btn-reply", "btn-ask", "btn-refund", "btn-escalate"].forEach((id) => {
    document.getElementById(id).disabled = disabled;
    document.getElementById(id).classList.remove("active-suggestion");
  });
}

function setSuggestedAction(action) {
  const mapping = {
    reply: "btn-reply",
    ask_details: "btn-ask",
    refund: "btn-refund",
    escalate: "btn-escalate"
  };
  Object.values(mapping).forEach((id) => document.getElementById(id).classList.remove("active-suggestion"));
  if (mapping[action]) {
    document.getElementById(mapping[action]).classList.add("active-suggestion");
  }
}

function updateGuide() {
  const task = TASK_DATA[currentTask];
  const guide = workflowGuide(task);
  const idx = Math.min(stepNum, Math.max(guide.length - 1, 0));
  const nextAction = task && task.expected_workflow ? task.expected_workflow[Math.min(stepNum, task.expected_workflow.length - 1)] : null;
  document.getElementById("step-num").textContent = isDone ? "Run Complete" : "Guided Step " + (Math.min(stepNum + 1, task.expected_workflow.length || 1));
  document.getElementById("guide-text").textContent = guide[idx] || "Follow the benchmark workflow.";
  if (!isDone && nextAction) {
    setSuggestedAction(nextAction);
  }
  renderTaskDetails(currentTask);
}

function resetRunUi(taskLabel) {
  document.getElementById("messages").innerHTML = "";
  document.getElementById("event-log").innerHTML = "";
  document.getElementById("total-reward").textContent = "0.0000";
  document.getElementById("step-info").textContent = "0 steps completed";
  document.getElementById("score-info").textContent = "No grade yet";
  document.getElementById("session-badge").textContent = "Starting run...";
  document.getElementById("task-badge").textContent = taskLabel;
  document.getElementById("msg-input").value = "";
  setButtons(false);
  addEvent("Session", "Preparing a fresh environment run for " + taskLabel + ".", "Waiting for reset response");
}

function addEvent(title, body, detail) {
  const box = document.getElementById("event-log");
  const div = document.createElement("div");
  div.className = "event-card";
  div.innerHTML = `<strong>${escapeHtml(title)}</strong><span>${escapeHtml(body)}</span>${detail ? `<small>${escapeHtml(detail)}</small>` : ""}`;
  box.prepend(div);
}

function addMsg(type, title, body, meta) {
  const div = document.createElement("div");
  div.className = "msg " + type;
  div.innerHTML = `
    <div class="msg-head">
      <div class="msg-role">${escapeHtml(title)}</div>
    </div>
    <div class="msg-body">${escapeHtml(body)}</div>
    ${meta ? `<div class="msg-meta">${meta}</div>` : ""}
  `;
  const box = document.getElementById("messages");
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function updateStateBar(obs, done) {
  document.getElementById("s-state").textContent = titleCase(obs.current_state);
  document.getElementById("s-intent").textContent = titleCase(obs.intent);
  document.getElementById("s-tone").textContent = titleCase(obs.sentiment);
  document.getElementById("s-step").textContent = obs.step_count;
  document.getElementById("s-done").textContent = done ? "Completed" : "In progress";
}

function updatePerfBadge(durationMs) {
  document.getElementById("perf-badge").textContent = durationMs + "ms";
  document.getElementById("latency-detail").textContent = durationMs < 100 ? "Excellent response time" : durationMs < 500 ? "Stable response time" : "Slow response path";
}

function updateStatusBadge(online, uptime) {
  const badge = document.getElementById("status-badge");
  badge.textContent = online ? "Online" : "Offline";
  badge.className = online ? "badge pill-online" : "badge pill-offline";
  document.getElementById("uptime-badge").textContent = uptime ? "Uptime: " + uptime + "s" : "Uptime: --";
}

async function refreshMetrics() {
  try {
    const [metricsRes, healthRes] = await Promise.all([fetch("/metrics"), fetch("/health")]);
    if (!metricsRes.ok || !healthRes.ok) throw new Error("metrics unavailable");
    const metrics = await metricsRes.json();
    const health = await healthRes.json();
    document.getElementById("m-total-sessions").textContent = metrics.total_sessions;
    document.getElementById("m-active-sessions").textContent = metrics.active_sessions;
    document.getElementById("m-total-steps").textContent = metrics.total_steps;
    document.getElementById("m-avg-time").textContent = metrics.avg_response_time_ms + "ms";
    updateStatusBadge(true, health.uptime_seconds);
  } catch (err) {
    updateStatusBadge(false);
  }
}

async function startTask(taskId) {
  const task = TASK_DATA[taskId];
  currentTask = taskId;
  stepNum = 0;
  isDone = false;
  renderTaskCards();
  renderTaskDetails(taskId);
  resetRunUi(task.name);

  try {
    const started = performance.now();
    const res = await fetch("/reset", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({task_id: taskId})
    });
    const data = await res.json();
    updatePerfBadge(Math.round(performance.now() - started));

    sessionId = data.session_id;
    document.getElementById("session-badge").textContent = "Run " + sessionId.slice(0, 8);
    document.getElementById("task-badge").textContent = task.name + " • " + titleCase(task.difficulty);

    const obs = data.observation;
    addMsg("customer", "Customer", obs.customer_message, "Intent " + titleCase(obs.intent) + " • Tone " + titleCase(obs.sentiment) + " • Urgency " + titleCase(obs.urgency_level));
    addMsg("system", "System", "Scenario initialized. Follow the highlighted workflow step and inspect the event log for deeper detail.", "Reset processed in " + (data.processing_time_ms || 0) + "ms");
    addEvent("Reset complete", "Loaded " + task.name + ".", "Session " + sessionId);
    updateStateBar(obs, false);
    refreshMetrics();
    updateGuide();
  } catch (err) {
    addMsg("error-msg", "System error", "Failed to start the selected benchmark.", "Check whether the FastAPI server is reachable.");
    addEvent("Network issue", "Could not reset the task.", "Server may be offline");
    updateStatusBadge(false);
  }
}

async function startCustomTask() {
  const rawMessage = document.getElementById("custom-msg").value.trim();
  if (!rawMessage) {
    addMsg("error-msg", "Input needed", "Enter a customer problem before starting a custom run.");
    return;
  }

  currentTask = "easy";
  stepNum = 0;
  isDone = false;
  renderTaskCards();
  renderTaskDetails("easy");
  resetRunUi("Custom scenario");

  try {
    const started = performance.now();
    const res = await fetch("/custom_reset", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({message: rawMessage})
    });
    const data = await res.json();
    updatePerfBadge(Math.round(performance.now() - started));

    sessionId = data.session_id;
    document.getElementById("session-badge").textContent = "Run " + sessionId.slice(0, 8);
    document.getElementById("task-badge").textContent = "Custom scenario • adaptive workflow";

    const obs = data.observation;
    addMsg("customer", "Customer", obs.customer_message, "Intent " + titleCase(obs.intent) + " • Tone " + titleCase(obs.sentiment) + " • Urgency " + titleCase(obs.urgency_level));
    addMsg("system", "System", "Custom scenario initialized. The backend mapped your message into a dynamic task flow.", "Reset processed in " + (data.processing_time_ms || 0) + "ms");
    addEvent("Custom run", "Created a session from your own scenario text.", "Detected intent: " + titleCase(obs.intent));
    updateStateBar(obs, false);
    document.getElementById("detail-title").textContent = "Custom Scenario Overview";
    document.getElementById("detail-description").textContent = "This run was generated dynamically from the message you entered. Use the event log and state panel to infer the best next step.";
    document.getElementById("workflow-list").innerHTML = '<li class="workflow-step active"><div class="step-index">1</div><div class="step-copy"><span>Adaptive workflow</span><small>The environment will score your sequence against the inferred support path.</small></div></li>';
    document.getElementById("brief-list").innerHTML = '<li>Custom session uses inferred intent detection and an auto-generated expected workflow.</li>';
    document.getElementById("guide-text").textContent = "Custom scenario active. Start with the action that best acknowledges or clarifies the customer issue.";
    document.getElementById("step-num").textContent = "Adaptive Run";
    refreshMetrics();
  } catch (err) {
    addMsg("error-msg", "System error", "Failed to start the custom scenario.");
    addEvent("Network issue", "Could not initialize the custom run.", "Server may be offline");
    updateStatusBadge(false);
  }
}

async function sendAction(actionType) {
  if (!sessionId || isDone) return;

  const inputEl = document.getElementById("msg-input");
  const content = inputEl.value.trim();
  if (actionType === "reply" && !content) {
    addMsg("error-msg", "Reply required", "Type a support response before sending the Reply action.");
    inputEl.focus();
    return;
  }

  setButtons(true);

  try {
    const started = performance.now();
    const res = await fetch("/step", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({
        session_id: sessionId,
        action_type: actionType,
        content: content
      })
    });
    updatePerfBadge(Math.round(performance.now() - started));

    if (!res.ok) {
      const err = await res.json();
      addMsg("error-msg", "Action rejected", err.detail || "The environment rejected the action.");
      addEvent("Action rejected", titleCase(actionType) + " was not accepted.", err.detail || "Unknown error");
      setButtons(false);
      return;
    }

    const data = await res.json();
    inputEl.value = "";

    const obs = data.observation;
    const reward = data.reward;
    const done = data.done;
    const info = data.info || {};
    const valid = Boolean(info.valid);
    const rewardText = (reward >= 0 ? "+" : "") + reward.toFixed(4);
    const meta = "Reward " + rewardText + " • Next state " + titleCase(info.next_state || obs.current_state) + " • " + (obs.processing_time_ms || 0) + "ms";

    if (actionType === "reply") {
      addMsg("agent", "Agent reply", content, meta);
    } else {
      addMsg("agent", titleCase(actionType), info.agent_response || "Action processed by backend workflow.", meta);
    }

    if (!valid) {
      addMsg("error-msg", "Validation warning", "That action was not valid for the current state.");
    }
    if (info.error && valid) {
      addMsg("error-msg", "Processing note", info.error);
    }

    addEvent(
      titleCase(actionType),
      (valid ? "Accepted" : "Marked invalid") + " with reward " + rewardText + ".",
      "Current state: " + titleCase(obs.current_state)
    );

    const stateRes = await fetch("/state?session_id=" + encodeURIComponent(sessionId));
    const stateData = await stateRes.json();
    document.getElementById("total-reward").textContent = stateData.total_reward.toFixed(4);
    document.getElementById("step-info").textContent = obs.step_count + " steps completed";

    updateStateBar(obs, done);
    stepNum += 1;
    isDone = done;

    if (done) {
      addMsg("success", "Run finished", info.message || "The episode reached a terminal state.");
      addEvent("Run complete", "Episode ended after " + obs.step_count + " steps.", "Final reward: " + stateData.total_reward.toFixed(4));

      if (data.grade) {
        const g = data.grade;
        document.getElementById("score-info").textContent = titleCase(g.label) + " • " + g.final_score;
        addMsg("success", "Grade summary", "Label " + g.label.toUpperCase() + " with final score " + g.final_score + ".", "Raw score " + g.raw_score + " • Total reward " + g.total_reward);
      }
    } else {
      setButtons(false);
    }

    refreshMetrics();
    updateGuide();
  } catch (err) {
    addMsg("error-msg", "Network issue", "Could not send the action to the server.");
    addEvent("Network issue", "Action request failed before completion.", "Server may be offline");
    inputEl.value = "";
    setButtons(false);
    updateStatusBadge(false);
  }
}

window.addEventListener("load", async () => {
  renderTaskCards();
  renderTaskDetails(currentTask);
  await refreshMetrics();
  await startTask("easy");
  metricsTimer = setInterval(refreshMetrics, 10000);
});
</script>
</body>
</html>
""".replace("__TASK_DATA__", json.dumps(task_payload))
