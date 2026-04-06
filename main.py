"""
SupportAI-Env — FastAPI Server (Enhanced Real-Time Version)
Endpoints: POST /reset, POST /step, GET /state, GET /health, GET /metrics
Serves GUI at GET /
Features: Real-time updates, session management, metrics tracking, health checks
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List
import uuid
import time
import asyncio
from collections import defaultdict

from env import SupportEnv, Action
from tasks import TASKS
from grader import grade

app = FastAPI(title="SupportAI-Env", version="2.0.0", description="Enhanced Real-Time Customer Support AI Environment")

# Add CORS middleware for better API access
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

@app.post("/reset")
def reset(req: ResetRequest):
    start_time = time.time()
    task_id = req.task_id
    if task_id not in TASKS:
        raise HTTPException(status_code=400, detail=f"Unknown task_id '{task_id}'. Choose: easy, medium, hard")
    session_id = req.session_id or str(uuid.uuid4())
    task = TASKS[task_id]
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
    _update_metrics("reset", task_id)
    
    return {
        "session_id": session_id,
        "task": task_id,
        "observation": obs.model_dump(),
        "processing_time_ms": round(duration_ms, 2)
    }

@app.post("/custom_reset")
def custom_reset(req: CustomResetRequest):
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
    
    return {
        "session_id": session_id,
        "task": "custom",
        "observation": obs.model_dump(),
        "processing_time_ms": round(duration_ms, 2)
    }

@app.post("/step")
def step(req: StepRequest):
    start_time = time.time()
    
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

    print(f"[ACTION] {req.action_type} | reward={reward} | state={obs.current_state} | valid={info.get('valid')} | time={info.get('processing_time_ms', 0)}ms")

    result = {
        "session_id": req.session_id,
        "observation": obs.model_dump(),
        "reward": reward,
        "done": done,
        "info": info,
    }
    
    if done:
        grade_result = grade(
            task=session["task"],
            action_history=env._action_history,
            total_reward=env.total_reward(),
            final_state=obs.current_state,
            step_count=obs.step_count,
            intent_detected=obs.intent,
            tone=obs.sentiment,
        )
        result["grade"] = grade_result
        print(f"[GRADE] {grade_result}")
    
    duration_ms = (time.time() - start_time) * 1000
    _track_response_time(duration_ms)
    _update_metrics("step")
    result["api_processing_time_ms"] = round(duration_ms, 2)
    
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

# ─── GUI ──────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def gui():
    return HTMLResponse(content=GUI_HTML)

GUI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>SupportAI-Env</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:#0f1117;color:#e0e0e0;height:100vh;display:flex;flex-direction:column}
header{background:#1a1d27;padding:12px 20px;display:flex;align-items:center;gap:10px;border-bottom:1px solid #2a2d3a}
header h1{font-size:1.1rem;color:#7c83fd}
.badge{font-size:0.7rem;background:#2a2d3a;padding:2px 8px;border-radius:10px;color:#aaa}
.layout{display:flex;flex:1;overflow:hidden}

/* Sidebar */
.sidebar{width:200px;background:#1a1d27;padding:14px;border-right:1px solid #2a2d3a;display:flex;flex-direction:column;gap:10px}
.sidebar h3{font-size:0.7rem;color:#666;text-transform:uppercase;letter-spacing:1px}
.task-btn{background:#2a2d3a;border:1px solid #3a3d4a;color:#bbb;padding:8px 10px;border-radius:8px;cursor:pointer;font-size:0.8rem;text-align:left;width:100%}
.task-btn.active,.task-btn:hover{background:#7c83fd22;border-color:#7c83fd;color:#7c83fd}
.reward-panel{margin-top:auto;background:#2a2d3a;border-radius:8px;padding:10px}
.reward-panel .rlabel{font-size:0.65rem;color:#888}
.reward-panel .rval{font-size:1.5rem;font-weight:bold;color:#7c83fd}
.reward-panel .rsub{font-size:0.7rem;color:#aaa;margin-top:3px}

/* Main chat */
.chat{flex:1;display:flex;flex-direction:column;overflow:hidden}
.guide-bar{background:#1e2030;border-bottom:1px solid #2a2d3a;padding:8px 16px;font-size:0.8rem;color:#a0a8ff;display:flex;align-items:center;gap:8px}
.guide-bar .step-indicator{background:#7c83fd;color:#fff;border-radius:12px;padding:2px 8px;font-size:0.7rem;font-weight:bold}
.messages{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px}

/* Message bubbles */
.msg{max-width:75%;padding:10px 14px;border-radius:12px;font-size:0.88rem;line-height:1.5}
.msg.customer{background:#2a2d3a;align-self:flex-start;border-bottom-left-radius:3px;border-left:3px solid #555}
.msg.agent{background:#1a2e3a;border:1px solid #2a5a6a;align-self:flex-end;border-bottom-right-radius:3px;color:#a0d4ff;border-right:3px solid #7c83fd}
.msg.system{background:#1a1d27;border:1px solid #3a3d4a;align-self:center;color:#aaa;font-size:0.78rem;max-width:90%;text-align:center;border-radius:8px}
.msg.success{background:#1e3a1e;border:1px solid #2a6a2a;color:#6fcf97;align-self:center;text-align:center;max-width:90%}
.msg.error-msg{background:#3a1e1e;border:1px solid #6a2a2a;color:#ff8080;align-self:center;text-align:center;max-width:90%}
.msg .meta{font-size:0.68rem;color:#666;margin-top:4px}
.msg .reward-badge{display:inline-block;padding:1px 6px;border-radius:8px;font-size:0.7rem;font-weight:bold;margin-left:6px}
.reward-badge.pos{background:#1e4a1e;color:#6fcf97}
.reward-badge.neg{background:#4a1e1e;color:#ff8080}

/* Action area */
.action-area{padding:14px 16px;background:#1a1d27;border-top:1px solid #2a2d3a}
.action-area h4{font-size:0.7rem;color:#666;text-transform:uppercase;margin-bottom:8px}
.input-row{display:flex;gap:8px;margin-bottom:10px}
#msg-input{flex:1;background:#2a2d3a;border:1px solid #3a3d4a;color:#e0e0e0;padding:8px 12px;border-radius:8px;font-size:0.85rem}
#msg-input:focus{outline:none;border-color:#7c83fd}
.btn-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.act-btn{background:#2a2d3a;border:1px solid #3a3d4a;color:#ccc;padding:10px 6px;border-radius:8px;cursor:pointer;font-size:0.82rem;transition:all 0.15s}
.act-btn:hover:not(:disabled){background:#7c83fd22;border-color:#7c83fd;color:#7c83fd}
.act-btn:disabled{opacity:0.35;cursor:not-allowed}
.act-btn.highlight{border-color:#7c83fd;color:#7c83fd;box-shadow:0 0 8px #7c83fd44}

/* State bar */
.state-bar{padding:6px 16px;background:#12141e;border-top:1px solid #2a2d3a;font-size:0.72rem;color:#666;display:flex;gap:16px;flex-wrap:wrap}
.state-bar .sv{color:#aaa}
.state-bar .sv.hi{color:#7c83fd;font-weight:bold}
</style>
</head>
<body>
<header>
  <h1>🤖 SupportAI-Env</h1>
  <span class="badge">OpenEnv v2.0</span>
  <span class="badge" id="session-badge">No session</span>
  <span class="badge" id="task-badge">—</span>
  <span class="badge" id="perf-badge" style="background:#1e4a1e;color:#6fcf97">⚡ 0ms</span>
  <span class="badge" id="status-badge" style="background:#1e4a1e;color:#6fcf97">● Online</span>
</header>

<div class="layout">
  <div class="sidebar">
    <h3>Select Task</h3>
    <button class="task-btn active" onclick="startTask('easy',this)">🟢 Easy<br/><small style="color:#888">Order Tracking</small></button>
    <button class="task-btn" onclick="startTask('medium',this)">🟡 Medium<br/><small style="color:#888">Refund Workflow</small></button>
    <button class="task-btn" onclick="startTask('hard',this)">🔴 Hard<br/><small style="color:#888">Multi-Intent</small></button>
    <button class="task-btn" id="custom-tab-btn" onclick="showCustomTab(this)">✏️ Custom<br/><small style="color:#888">Your Problem</small></button>
    <div id="custom-input-area" style="display:none;flex-direction:column;gap:6px;margin-top:4px">
      <textarea id="custom-msg" rows="4" placeholder="Type your customer problem here..." style="background:#2a2d3a;border:1px solid #3a3d4a;color:#e0e0e0;padding:8px;border-radius:8px;font-size:0.8rem;resize:vertical;width:100%"></textarea>
      <button onclick="startCustomTask()" style="background:#7c83fd;border:none;color:#fff;padding:8px;border-radius:8px;cursor:pointer;font-size:0.82rem;font-weight:bold">▶ Start Chat</button>
    </div>
    <div class="reward-panel">
      <div class="rlabel">Total Reward</div>
      <div class="rval" id="total-reward">—</div>
      <div class="rsub" id="step-info">Steps: 0</div>
      <div class="rsub" id="score-info" style="color:#7c83fd;margin-top:4px"></div>
    </div>
  </div>

  <div class="chat">
    <div class="guide-bar" id="guide-bar">
      <span class="step-indicator" id="step-num">—</span>
      <span id="guide-text">Select a task from the left to begin</span>
    </div>

    <div class="messages" id="messages">
      <div class="msg system">👈 Select a task on the left to start. Then follow the guided steps.</div>
    </div>

    <div class="action-area">
      <h4>Your Action</h4>
      <div class="input-row">
        <input id="msg-input" type="text" placeholder="Type your reply message here (required for Reply)..." />
      </div>
      <div class="btn-grid">
        <button class="act-btn" id="btn-reply" onclick="sendAction('reply')" disabled>💬 Reply</button>
        <button class="act-btn" id="btn-ask" onclick="sendAction('ask_details')" disabled>🔍 Ask Details</button>
        <button class="act-btn" id="btn-refund" onclick="sendAction('refund')" disabled>💰 Refund</button>
        <button class="act-btn" id="btn-escalate" onclick="sendAction('escalate')" disabled>🚨 Escalate</button>
      </div>
    </div>

    <div class="state-bar">
      <div>State: <span class="sv hi" id="s-state">—</span></div>
      <div>Intent: <span class="sv" id="s-intent">—</span></div>
      <div>Tone: <span class="sv" id="s-tone">—</span></div>
      <div>Step: <span class="sv" id="s-step">0</span></div>
      <div>Done: <span class="sv" id="s-done">No</span></div>
    </div>
  </div>
</div>

<script>
let sessionId = null;
let isDone = false;
let stepNum = 0;

// Guided instructions per task
const GUIDES = {
  easy: [
    "Step 1: Click 'Ask Details' to request the order number",
    "Step 2: Click 'Reply' with tracking information to resolve",
    "✅ Task complete!"
  ],
  medium: [
    "Step 1: Click 'Ask Details' to collect refund information",
    "Step 2: Click 'Ask Details' again to validate the claim",
    "Step 3: Click 'Refund' to process the refund",
    "✅ Task complete!"
  ],
  hard: [
    "Step 1: Click 'Reply' to acknowledge the angry customer",
    "Step 2: Click 'Ask Details' to gather issue information",
    "Step 3: Click 'Refund' to resolve the product issue",
    "Step 4: Click 'Reply' to finalize and close",
    "✅ Task complete!"
  ]
};

let currentTask = 'easy';

function showCustomTab(btn) {
  document.querySelectorAll('.task-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const area = document.getElementById('custom-input-area');
  area.style.display = area.style.display === 'none' ? 'flex' : 'none';
}

async function startCustomTask() {
  const msg = document.getElementById('custom-msg').value.trim();
  if (!msg) {
    alert('Please type your problem first.');
    return;
  }
  document.getElementById('custom-input-area').style.display = 'none';
  currentTask = 'custom';
  stepNum = 0;
  isDone = false;

  try {
    const startTime = performance.now();
    const res = await fetch('/custom_reset', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({message: msg})
    });
    const data = await res.json();
    const duration = Math.round(performance.now() - startTime);
    updatePerfBadge(duration);
    
    sessionId = data.session_id;

    document.getElementById('messages').innerHTML = '';
    document.getElementById('total-reward').textContent = '0.0000';
    document.getElementById('step-info').textContent = 'Steps: 0';
    document.getElementById('score-info').textContent = '';
    document.getElementById('session-badge').textContent = 'ID: ' + sessionId.slice(0,8);
    document.getElementById('task-badge').textContent = 'CUSTOM';
    document.getElementById('msg-input').value = '';
    setButtons(false);

    const obs = data.observation;
    addMsg('customer', '🧑 Customer: ' + obs.customer_message,
      'Intent: ' + obs.intent + ' | Tone: ' + obs.sentiment + ' | Urgency: ' + obs.urgency_level + ' | Processed in ' + (data.processing_time_ms || 0) + 'ms');
    updateStateBar(obs, false);
    document.getElementById('guide-text').textContent = 'Custom problem loaded — use the action buttons to respond';
    document.getElementById('step-num').textContent = 'Step 1';
  } catch(e) {
    addMsg('error-msg', '❌ Failed to start custom session.');
    updateStatusBadge(false);
  }
}

async function startTask(taskId, btn) {
  document.querySelectorAll('.task-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentTask = taskId;
  stepNum = 0;
  isDone = false;

  try {
    const startTime = performance.now();
    const res = await fetch('/reset', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({task_id: taskId})
    });
    const data = await res.json();
    const duration = Math.round(performance.now() - startTime);
    updatePerfBadge(duration);
    
    sessionId = data.session_id;

    // Reset UI
    document.getElementById('messages').innerHTML = '';
    document.getElementById('total-reward').textContent = '0.0000';
    document.getElementById('step-info').textContent = 'Steps: 0';
    document.getElementById('score-info').textContent = '';
    document.getElementById('session-badge').textContent = 'ID: ' + sessionId.slice(0,8);
    document.getElementById('task-badge').textContent = taskId.toUpperCase();
    document.getElementById('msg-input').value = '';
    setButtons(false);
    updateGuide();

    const obs = data.observation;
    addMsg('customer', '🧑 Customer: ' + obs.customer_message,
      'Intent: ' + obs.intent + ' | Tone: ' + obs.sentiment + ' | Urgency: ' + obs.urgency_level + ' | Processed in ' + (data.processing_time_ms || 0) + 'ms');
    updateStateBar(obs, false);
    addMsg('system', '👆 Follow the guide above. Use the action buttons below.');
  } catch(e) {
    addMsg('error-msg', '❌ Failed to connect to server. Make sure the server is running.');
    updateStatusBadge(false);
  }
}

async function sendAction(actionType) {
  if (!sessionId || isDone) return;

  const inputEl = document.getElementById('msg-input');
  const content = inputEl.value.trim();

  console.log("Sending:", actionType, content);

  // Require content for reply
  if (actionType === 'reply' && !content) {
    addMsg('error-msg', '⚠️ Please enter a message in the input box before clicking Reply.');
    inputEl.focus();
    return;
  }

  setButtons(true); // disable during request

  try {
    const startTime = performance.now();
    const payload = {session_id: sessionId, action_type: actionType, content: content};
    console.log("Payload:", JSON.stringify(payload));
    const res = await fetch('/step', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    const duration = Math.round(performance.now() - startTime);
    updatePerfBadge(duration);

    if (!res.ok) {
      const err = await res.json();
      addMsg('error-msg', '❌ Error: ' + (err.detail || 'Unknown error'));
      setButtons(false);
      return;
    }

    const data = await res.json();
    inputEl.value = '';  // clear input after successful send

    const obs = data.observation;
    const reward = data.reward;
    const done = data.done;
    const info = data.info;
    const isValid = info.valid;
    const agentResponse = info.agent_response || '';
    const procTime = obs.processing_time_ms || 0;

    const rewardClass = reward >= 0 ? 'pos' : 'neg';
    const rewardSign = reward >= 0 ? '+' : '';
    const validIcon = isValid ? '✅' : '❌';

    // Show agent response as chat bubble
    if (actionType === 'reply' && content) {
      // User typed a reply — show their text
      addMsg('agent', '🧑‍💼 You replied: ' + content,
        validIcon + ' REPLY | Reward: <span class="reward-badge ' + rewardClass + '">' + rewardSign + reward.toFixed(4) + '</span> | → ' + info.next_state + ' | ' + procTime + 'ms');
    } else {
      // Show logic-driven response from backend
      addMsg('agent', '🤖 Support: ' + agentResponse,
        validIcon + ' ' + actionType.toUpperCase() + ' | Reward: <span class="reward-badge ' + rewardClass + '">' + rewardSign + reward.toFixed(4) + '</span> | → ' + info.next_state + ' | ' + procTime + 'ms');
    }

    if (!isValid) {
      addMsg('error-msg', '❌ Invalid action in current state. Try a different action.');
    }

    if (info.error && isValid) {
      addMsg('error-msg', '⚠️ ' + info.error);
    }

    // Update reward display
    const stateRes = await fetch('/state?session_id=' + sessionId);
    const stateData = await stateRes.json();
    document.getElementById('total-reward').textContent = stateData.total_reward.toFixed(4);
    document.getElementById('step-info').textContent = 'Steps: ' + obs.step_count;

    updateStateBar(obs, done);
    stepNum++;
    updateGuide();

    if (done) {
      isDone = true;
      const endMsg = info.message || 'Episode ended';
      addMsg('success', '🏁 ' + endMsg);

      if (data.grade) {
        const g = data.grade;
        const emoji = g.label === 'full' ? '🏆' : g.label === 'partial' ? '⚡' : '❌';
        addMsg('success',
          emoji + ' Grade: ' + g.label.toUpperCase() +
          ' | Score: ' + g.final_score +
          ' | Raw: ' + g.raw_score +
          ' | Total Reward: ' + g.total_reward
        );
        document.getElementById('score-info').textContent = emoji + ' Score: ' + g.final_score + ' (' + g.label + ')';
      }

      document.getElementById('guide-text').textContent = GUIDES[currentTask][GUIDES[currentTask].length - 1];
      document.getElementById('step-num').textContent = 'DONE';
    } else {
      setButtons(false);
    }
  } catch(e) {
    addMsg('error-msg', '❌ Network error. Is the server running?');
    inputEl.value = '';
    setButtons(false);
    updateStatusBadge(false);
  }
}

function updateGuide() {
  const guides = GUIDES[currentTask] || [];
  const idx = Math.min(stepNum, guides.length - 2);
  const text = guides[idx] || 'Follow the workflow';
  document.getElementById('guide-text').textContent = text;
  document.getElementById('step-num').textContent = 'Step ' + (idx + 1);

  // Highlight suggested button
  document.querySelectorAll('.act-btn').forEach(b => b.classList.remove('highlight'));
  if (text.includes('Reply')) document.getElementById('btn-reply').classList.add('highlight');
  else if (text.includes('Ask Details')) document.getElementById('btn-ask').classList.add('highlight');
  else if (text.includes('Refund')) document.getElementById('btn-refund').classList.add('highlight');
  else if (text.includes('Escalate')) document.getElementById('btn-escalate').classList.add('highlight');
}

function addMsg(type, text, meta) {
  const div = document.createElement('div');
  div.className = 'msg ' + type;
  div.innerHTML = '<div>' + text + '</div>' + (meta ? '<div class="meta">' + meta + '</div>' : '');
  const box = document.getElementById('messages');
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function updateStateBar(obs, done) {
  document.getElementById('s-state').textContent = obs.current_state;
  document.getElementById('s-intent').textContent = obs.intent;
  document.getElementById('s-tone').textContent = obs.sentiment;
  document.getElementById('s-step').textContent = obs.step_count;
  document.getElementById('s-done').textContent = done ? 'Yes ✅' : 'No';
}

function setButtons(disabled) {
  ['btn-reply','btn-ask','btn-refund','btn-escalate'].forEach(id => {
    document.getElementById(id).disabled = disabled;
  });
}

function updatePerfBadge(durationMs) {
  const badge = document.getElementById('perf-badge');
  badge.textContent = '⚡ ' + durationMs + 'ms';
  if (durationMs < 100) {
    badge.style.background = '#1e4a1e';
    badge.style.color = '#6fcf97';
  } else if (durationMs < 500) {
    badge.style.background = '#4a3a1e';
    badge.style.color = '#f0c674';
  } else {
    badge.style.background = '#4a1e1e';
    badge.style.color = '#ff8080';
  }
}

function updateStatusBadge(online) {
  const badge = document.getElementById('status-badge');
  if (online) {
    badge.textContent = '● Online';
    badge.style.background = '#1e4a1e';
    badge.style.color = '#6fcf97';
  } else {
    badge.textContent = '● Offline';
    badge.style.background = '#4a1e1e';
    badge.style.color = '#ff8080';
  }
}

// Auto-start easy task on load
window.onload = () => {
  const btn = document.querySelector('.task-btn.active');
  if (btn) startTask('easy', btn);
  
  // Check server health periodically
  setInterval(async () => {
    try {
      const res = await fetch('/health');
      if (res.ok) {
        updateStatusBadge(true);
      } else {
        updateStatusBadge(false);
      }
    } catch(e) {
      updateStatusBadge(false);
    }
  }, 10000); // Check every 10 seconds
};
</script>
</body>
</html>
"""
