# 🚀 SupportAI-Env v3.0 — Getting Started Guide

## ✨ What's New in v3.0

Your project has been **significantly enhanced** with enterprise-grade features:

### Core Improvements
- ✅ **Persistent Database** - SQLite storage for sessions, users, analytics
- ✅ **User Authentication** - Secure registration & token-based login
- ✅ **Advanced Analytics** - Performance trends, statistics, insights
- ✅ **Better Grading** - Weighted rubrics, detailed feedback, batch processing
- ✅ **Rate Limiting** - Protect API from abuse
- ✅ **Security** - Password hashing, token management, input validation
- ✅ **Data Export** - JSON/CSV reports for analysis
- ✅ **Global Leaderboards** - Competitive rankings
- ✅ **Zero New Dependencies** - Uses only Python stdlib

---

## 🚀 Quick Start

### 1. Start the Server
```bash
cd c:\Meta_Project-main
python start_server.py
```

Server launches at **http://localhost:7860**

### 2. Try It Out

#### Option A: Web Dashboard (Same as Before)
Open http://localhost:7860 in your browser. All original features still work!

#### Option B: Use New Authentication Features

**Register New User:**
```bash
curl -X POST http://localhost:7860/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "email": "alice@example.com",
    "password": "Secure123!"
  }'
```

**Response:**
```json
{
  "access_token": "eyJ1c2VyX...",
  "token_type": "bearer",
  "username": "alice"
}
```

**Save the token and use it for authenticated requests:**
```bash
TOKEN="eyJ1c2VyX..."

# Start authenticated session
curl -X POST http://localhost:7860/reset \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task_id": "medium"}'
```

### 3. View Your Analytics

```bash
TOKEN="your-token-here"

# Get your performance data
curl -X GET http://localhost:7860/analytics/user \
  -H "Authorization: Bearer $TOKEN"
```

### 4. Export Your Data

```bash
# Get JSON report
curl -X POST http://localhost:7860/export/report \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"format": "json", "include_sessions": true}'
```

---

## 📚 New Files Added

### Core Modules
| File | Purpose |
|------|---------|
| `database.py` | Persistent storage (SQLite, sessions, users, analytics, leaderboards) |
| `analytics.py` | Advanced analytics, insights, data export |
| `security.py` | Authentication, password hashing, rate limiting, input validation |
| `advanced_grader.py` | Weighted grading with custom rubrics and detailed feedback |

### Documentation
| File | Purpose |
|------|---------|
| `IMPROVEMENTS.md` | Detailed list of all improvements and features |
| `API_REFERENCE.md` | Complete API endpoint reference with examples |
| `GETTING_STARTED.md` | This file - Quick start guide |

---

## 🎯 Key Features Explained

### 1. User Registration & Authentication
- Create user accounts with username, email, password
- Passwords hashed with PBKDF2-HMAC-SHA256
- JWT-like tokens valid for 24 hours
- Token-based API authentication

**Use Case**: Multi-user training platform, user progress tracking

### 2. Persistent Session Storage
- All sessions saved to database
- Track history per user
- Export session data anytime
- Resume progress across sessions

**Use Case**: Corporate training, performance reviews, long-term learning

### 3. Advanced Analytics
- User performance trends (improving/stable/declining)
- Statistical analysis (mean, median, std dev)
- Task difficulty ratings
- Grade distributions
- Leaderboard rankings

**Use Case**: Track learning progress, identify weak areas, motivate with leaderboards

### 4. Enhanced Grading System
- Custom rubrics for each task level
- Weighted scoring (not just binary)
- Detailed feedback on strengths/improvements
- Batch grading for multiple sessions
- Auto-generated tips for improvement

**Use Case**: Detailed performance feedback, fair evaluation, learning guidance

### 5. Security & Rate Limiting
- Password strength validation
- Token revocation
- Rate limits (60 req/min per client)
- Input sanitization
- CORS protection

**Use Case**: Secure API access, prevent abuse, enterprise deployment

### 6. Data Export
- JSON format for import to other tools
- CSV format for spreadsheet analysis
- Full session history export
- Performance reports

**Use Case**: Analytics in Excel, integration with other systems, compliance reports

---

## 📊 Database Schema

The system automatically creates these tables:

```
sessions
├── session_id (unique identifier)
├── user_id (optional, for authenticated users)
├── task_id (easy/medium/hard/custom)
├── status (active/completed/failed)
├── final_score, grade_label, step_count
├── action_history, state_history (JSON)
└── timestamps

users
├── user_id (unique identifier)
├── username (unique)
├── email
├── password_hash (PBKDF2)
├── avg_score, total_sessions
└── auth fields (created_at, last_login)

analytics
├── record_id
├── user_id, task_id (optional)
├── metric_name, metric_value
└── timestamp

leaderboard
├── rank
├── user_id, username
├── avg_score, total_sessions
└── last_updated
```

Location: **c:\Meta_Project-main\supportai.db** (SQLite)

---

## 🔄 Backward Compatibility

✅ **All existing features still work:**
- Original dashboard at http://localhost:7860
- POST /reset, POST /step, GET /state
- Real-time WebSocket updates
- Task catalog and custom scenarios
- Anonymous usage (no registration required)

**No breaking changes** - Existing code continues to work as-is.

---

## 🎓 Using Advanced Features

### Scenario 1: Personal Learning
1. Start session anonymously: `POST /reset`
2. Execute actions: `POST /step` (repeat)
3. Get instant feedback with advanced grader
4. No database needed - stateless usage

### Scenario 2:  Individual Progress Tracking
1. Register account: `POST /auth/register`
2. Start authenticated session: `POST /reset` (with token)
3. Build up session history in database
4. View trends: `GET /analytics/user`
5. Export progress: `POST /export/report`

### Scenario 3: Team/Class Leaderboard
1. Batch register 20 users
2. Each completes multiple tasks (authenticated sessions)
3. Analytics automatically tracks scores
4. Leaderboard updates: `GET /analytics/leaderboard`
5. Motivate with friendly competition

### Scenario 4: Automated Assessment
1. Prepare session data for 50 students
2. Batch grade all: `POST /grade/batch`
3. Get aggregate statistics (mean, median, distribution)
4. Identify struggling students, celebrate high performers

---

## 📈 API Workflow Examples

### Quick Anonymous Test
```python
import requests
import json

# Start session
r = requests.post("http://localhost:7860/reset",
                  json={"task_id": "easy"})
session = r.json()
session_id = session["session_id"]
print(f"Session started: {session_id}")

# Take action
r = requests.post("http://localhost:7860/step",
                  json={
                      "session_id": session_id,
                      "action_type": "ask_details",
                      "content": "What is your order number?"
                  })
result = r.json()
print(f"Reward: {result['reward']}")
print(f"Done: {result['done']}")

if result['done']:
    grade = result.get('grade', {})
    print(f"Grade: {grade.get('label')}")
    print(f"Score: {grade.get('final_score')}")
    print(f"Feedback: {grade.get('feedback', {}).get('overall')}")
```

### Authenticated User Flow
```python
import requests

# Register
r = requests.post("http://localhost:7860/auth/register",
                  json={
                      "username": "alice",
                      "password": "SecurePass123"
                  })
token = r.json()["access_token"]
print(f"Token: {token}")

# Start session
headers = {"Authorization": f"Bearer {token}"}
r = requests.post("http://localhost:7860/reset",
                  json={"task_id": "medium"},
                  headers=headers)
session_id = r.json()["session_id"]

# ... complete session ...

# Get analytics
r = requests.get("http://localhost:7860/analytics/user",
                 headers=headers)
analytics = r.json()
print(f"Avg Score: {analytics['avg_score']}")
print(f"Trend: {analytics['trend']}")
```

---

## 🛠️ Configuration

Default settings (can be modified in source code):

```python
# database.py
db_path = "supportai.db"

# security.py
rate_limit: 60 requests/minute, burst_size: 100
token_expiry: 24 hours
password_min_length: 8

# advanced_grader.py
Easy threshold: 0.85 excellent, 0.65 good, 0.40 acceptable
Medium threshold: 0.85 excellent, 0.65 good, 0.40 acceptable
Hard threshold: 0.85 excellent, 0.65 good, 0.40 acceptable
```

---

## 📊 Monitoring

### Health Check
```bash
curl http://localhost:7860/health
```

### System Metrics
```bash
curl http://localhost:7860/metrics
```

### Detailed System Info
```bash
curl http://localhost:7860/system/info
```

### API Information
```bash
curl http://localhost:7860/api/info
```

---

## 🐛 Troubleshooting

### Issue: Database locked
**Solution**: Delete `supportai.db` and restart server
```bash
rm supportai.db
python start_server.py
```

### Issue: Token expired
**Solution**: Login again to get a new token
```bash
curl -X POST http://localhost:7860/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "YourPassword123"}'
```

### Issue: Rate limit exceeded
**Solution**: Wait 1 minute before making requests again
Or adjust rate limit in `security.py`

### Issue: Unicode characters in output (Windows)
**Solution**: This is expected on Windows. The API JSON will display correctly in tools.

---

## 📚 Documentation Files

1. **README.md** - Original project info (unchanged)
2. **IMPROVEMENTS.md** - Detailed v3.0 enhancements
3. **API_REFERENCE.md** - Complete API endpoint docs
4. **GETTING_STARTED.md** - This file
5. **requirements.txt** - Python dependencies (unchanged)

---

## 🎯 Next Steps

1. **Start the server**: `python start_server.py`
2. **Open dashboard**: http://localhost:7860
3. **Try authentication**: Register & login
4. **Create sessions**: Start an authenticated session
5. **View analytics**: Check your performance metrics
6. **Export data**: Download your session history
7. **Read docs**: Check API_REFERENCE.md for all endpoints

---

## 💡 Pro Tips

1. **Development**: Use anonymous sessions for quick testing
2. **Production**: Use authentication for multi-user deployments
3. **Analysis**: Batch grade multiple sessions for aggregate stats
4. **Integration**: Export JSON for use in external tools
5. **Monitoring**: Use /system/info to monitor server health
6. **Security**: Use HTTPS in production (add reverse proxy)

---

## 🎉 Summary

Your SupportAI-Env has been transformed from a basic training tool into an **enterprise-ready platform** with:

- ✅ Persistent data storage
- ✅ Multi-user support  
- ✅ Advanced analytics
- ✅ Professional grading
- ✅ Security & rate limiting
- ✅ Data export capabilities
- ✅ Global leaderboards

**All while maintaining 100% backward compatibility** with existing features!

**Enjoy your enhanced platform!** 🚀
