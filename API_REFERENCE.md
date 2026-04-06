"""
SupportAI-Env v3.0 — API Quick Reference Guide
Complete endpoint documentation with examples
"""

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

## 1. Register New User
POST /auth/register
Content-Type: application/json

{
    "username": "alice",
    "email": "alice@example.com",
    "password": "SecurePass123"
}

Response:
{
    "access_token": "eyJ1c2VyX...",
    "token_type": "bearer",
    "username": "alice"
}


## 2. Login User
POST /auth/login
Content-Type: application/json

{
    "username": "alice",
    "password": "SecurePass123"
}

Response:
{
    "access_token": "eyJ1c2VyX...",
    "token_type": "bearer",
    "username": "alice"
}


# ============================================================================
# SESSION ENDPOINTS
# ============================================================================

## 3. Start New Session (Anonymous or Authenticated)
POST /reset
Content-Type: application/json
Authorization: Bearer <token> (optional)

{
    "task_id": "easy",  # easy, medium, hard
    "session_id": "custom-id-optional"
}

Response:
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "task": "easy",
    "observation": {
        "customer_message": "...",
        "conversation_history": [],
        "sentiment": "neutral",
        "issue_type": "...",
        "current_state": "IDENTIFY_INTENT",
        ...
    },
    "processing_time_ms": 12.5,
    "type": "reset"
}


## 4. Start Custom Scenario
POST /custom_reset
Content-Type: application/json

{
    "message": "I want a refund because the item arrived damaged!"
}

Response:
{
    "session_id": "...",
    "task": "custom",
    "observation": {...},
    "processing_time_ms": 15.2,
    "type": "custom_reset"
}


## 5. Execute Action Step
POST /step
Content-Type: application/json

{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "action_type": "ask_details",  # reply, ask_details, refund, escalate
    "content": "Could you please provide your order number?"
}

Response:
{
    "session_id": "...",
    "observation": {...},
    "reward": 0.75,
    "done": false,
    "info": {"valid": true, "error": null},
    "api_processing_time_ms": 18.3
}

When done=true, response includes:
{
    ...
    "done": true,
    "grade": {
        "raw_score": 0.82,
        "final_score": 0.82,
        "label": "good",
        "breakdown": {
            "intent_detection": {
                "score": 1.0,
                "weight": 0.2,
                "contribution": 0.2
            },
            ...
        },
        "feedback": {
            "overall": "Good work! You demonstrated solid customer support skills.",
            "strengths": ["Strong performance in tone_appropriate"],
            "improvements": ["Focus on resolution_speed"],
            "tips": ["Consider asking for more details..."]
        },
        ...
    }
}


## 6. Get Current State
GET /state?session_id=550e8400-e29b-41d4-a716-446655440000

Response:
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "observation": {...},
    "done": false,
    "total_reward": 2.45,
    "session_age_seconds": 145.2,
    "last_activity_seconds_ago": 12.3
}


## 7. List Active Sessions
GET /sessions

Response:
{
    "active_sessions": 3,
    "sessions": [
        {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "task": "easy",
            "done": false,
            "age_seconds": 145.2,
            "last_activity_seconds_ago": 12.3
        },
        ...
    ]
}


## 8. Delete Session
DELETE /session/550e8400-e29b-41d4-a716-446655440000

Response:
{
    "status": "deleted",
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
}


# ============================================================================
# ANALYTICS ENDPOINTS (Authenticated)
# ============================================================================

## 9. Get User Analytics
GET /analytics/user
Authorization: Bearer <token>

Response:
{
    "user_id": "user-uuid",
    "total_sessions": 25,
    "completed_sessions": 23,
    "completion_rate": 92.0,
    "avg_score": 0.7841,
    "median_score": 0.81,
    "std_dev_score": 0.118,
    "avg_steps": 5.2,
    "best_score": 0.95,
    "worst_score": 0.32,
    "task_distribution": {
        "easy": 10,
        "medium": 8,
        "hard": 5
    },
    "grade_distribution": {
        "excellent": 8,
        "good": 10,
        "acceptable": 5
    },
    "trend": "improving",
    "improvement": {
        "percentage": 12.5,
        "direction": "up"
    }
}


## 10. Get Task Analytics
GET /analytics/task/easy

Response:
{
    "task_id": "easy",
    "total_attempts": 342,
    "success_rate": 78.4,
    "avg_score": 0.692,
    "median_score": 0.71,
    "std_dev": 0.156,
    "avg_steps": 4.8,
    "difficulty_level": "easy",
    "grade_distribution": {
        "full": 156,
        "partial": 112,
        "fail": 74
    }
}


## 11. Get Global Leaderboard
GET /analytics/leaderboard?limit=50

Response:
{
    "leaderboard": [
        {
            "rank": 1,
            "user_id": "uuid1",
            "username": "alice",
            "avg_score": 0.92,
            "total_sessions": 45,
            "last_updated": "2026-04-07T15:30:00"
        },
        {
            "rank": 2,
            "user_id": "uuid2",
            "username": "bob",
            "avg_score": 0.88,
            "total_sessions": 38,
            "last_updated": "2026-04-07T15:29:00"
        },
        ...
    ],
    "total": 127
}


# ============================================================================
# EXPORT ENDPOINTS (Authenticated)
# ============================================================================

## 12. Export User Report
POST /export/report
Authorization: Bearer <token>
Content-Type: application/json

{
    "format": "json",  # json or csv
    "include_sessions": true
}

Response (JSON format):
{
    "generated_at": "2026-04-07T15:45:00",
    "user_id": "...",
    "username": "alice",
    "analysis": {
        "user_id": "...",
        "total_sessions": 25,
        ...
    },
    "sessions": [
        {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "task_id": "easy",
            "duration_seconds": 145.2,
            "step_count": 4,
            "final_score": 0.85,
            "grade_label": "good",
            ...
        },
        ...
    ]
}


## 13. Get Session History
GET /export/sessions?limit=100
Authorization: Bearer <token>

Response:
{
    "user_id": "...",
    "total_sessions": 25,
    "sessions": [
        {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "task_id": "easy",
            "status": "completed",
            "final_score": 0.85,
            "grade_label": "good",
            "step_count": 4,
            "created_at": "2026-04-07T15:00:00"
        },
        ...
    ]
}


# ============================================================================
# GRADING ENDPOINTS
# ============================================================================

## 14. Batch Grade Sessions
POST /grade/batch
Content-Type: application/json

{
    "sessions": [
        {
            "task": {"id": "easy", "max_steps": 8},
            "action_history": ["ask_details", "reply"],
            "total_reward": 1.5,
            "final_state": "RESOLUTION",
            "step_count": 2,
            "intent_detected": "general",
            "tone": "neutral"
        },
        ...
    ]
}

Response:
{
    "total_graded": 5,
    "grades": [
        {
            "raw_score": 0.82,
            "final_score": 0.82,
            "label": "good",
            "breakdown": {...},
            "feedback": {...},
            ...
        },
        ...
    ],
    "statistics": {
        "mean_score": 0.776,
        "median_score": 0.81,
        "std_dev": 0.087,
        "min_score": 0.62,
        "max_score": 0.94
    },
    "grade_distribution": {
        "excellent": 1,
        "good": 3,
        "acceptable": 1
    },
    "pass_rate": 80.0
}


# ============================================================================
# MONITORING ENDPOINTS
# ============================================================================

## 15. Health Check
GET /health

Response:
{
    "status": "healthy",
    "uptime_seconds": 3600.5,
    "active_sessions": 12,
    "total_sessions": 287
}


## 16. Get System Metrics
GET /metrics

Response:
{
    "total_sessions": 287,
    "total_steps": 1542,
    "total_resets": 287,
    "avg_response_time_ms": 24.7,
    "active_sessions": 12,
    "task_counts": {
        "easy": 145,
        "medium": 98,
        "hard": 44
    },
    "uptime_seconds": 3600.5
}


## 17. Get System Info
GET /system/info

Response:
{
    "timestamp": "2026-04-07T15:45:00",
    "uptime_seconds": 3600.5,
    "uptime_formatted": "1h 0m",
    "memory": {
        "active_sessions": 12,
        "active_tokens": 8,
        "rate_limit_buckets": 45
    },
    "metrics": {
        "total_sessions": 287,
        "total_steps": 1542,
        "avg_response_time_ms": 24.7
    }
}


## 18. Get Task Catalog
GET /task_catalog

Response:
{
    "tasks": [
        {
            "id": "easy",
            "name": "Order Status",
            "difficulty": "easy",
            "initial_message": "Hi, could you tell me about my order status?",
            "expected_intent": "general",
            "expected_workflow": ["ask_details", "reply"],
            ...
        },
        ...
    ],
    "supported_actions": ["reply", "ask_details", "refund", "escalate"]
}


## 19. Get API Info
GET /api/info

Response:
{
    "title": "SupportAI-Env Advanced API",
    "version": "3.0.0",
    "description": "Customer Support AI Training Platform",
    "endpoints": {
        "authentication": [...],
        "sessions": [...],
        "analytics": [...],
        ...
    },
    "features": [
        "Persistent database storage",
        "User authentication & authorization",
        ...
    ]
}


# ============================================================================
# WEBSOCKET ENDPOINT
# ============================================================================

## 20. WebSocket Real-Time Updates
WS /ws/550e8400-e29b-41d4-a716-446655440000

Connection:
const ws = new WebSocket("ws://localhost:7860/ws/session-id");

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // Receive real-time updates
    console.log("Update:", data);
};

Receives messages on:
- POST /reset
- POST /step
- POST /custom_reset


# ============================================================================
# COMMON USAGE WORKFLOWS
# ============================================================================

### Workflow 1: Authenticated User Session
1. POST /auth/register → Get token
2. POST /reset (with auth) → Get session_id
3. POST /step → Execute actions (repeat)
4. GET /analytics/user → View performance
5. POST /export/report → Get data

### Workflow 2: Anonymous Training
1. POST /reset → Get session_id
2. POST /step → Execute actions (repeat)
3. Response includes grade when done=true

### Workflow 3: Batch Assessment
1. Create session data structure for multiple sessions
2. POST /grade/batch → Get aggregate results
3. Analyze statistics and grade distribution

### Workflow 4: Competitive Leaderboard
1. POST /auth/register (multiple users)
2. Each user: Complete multiple tasks
3. GET /analytics/leaderboard → Check rankings
4. System automatically updates rankings

# ============================================================================
# ERROR CODES
# ============================================================================

200 OK - Success
201 Created - Resource created
400 Bad Request - Invalid input
401 Unauthorized - Missing/invalid token
404 Not Found - Session/resource not found
409 Conflict - User exists
429 Too Many Requests - Rate limit exceeded
500 Internal Server Error - Server issue

# ============================================================================
# RATE LIMITING
# ============================================================================

Default: 60 requests per minute per client
Token bucket algorithm with burst support

Headers returned:
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 60

When limit exceeded: 429 response

# ============================================================================
# AUTHENTICATION
# ============================================================================

Include token in Authorization header:
Authorization: Bearer eyJ1c2VyX...

Token format: JWT-like with:
- user_id
- username
- iat (issued at)
- exp (expiration)
- jti (JWT ID for revocation)

Default expiration: 24 hours
