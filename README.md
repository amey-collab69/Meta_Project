---
title: SupportAI-Env
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
app_file: main.py
pinned: false
---

# 🚀 SupportAI-Env

Production-grade OpenEnv environment for customer support AI training with real-time dashboard, advanced grading, and multi-task workflows.

## Features

- **Multi-Task Training**: Easy, Medium, and Hard difficulty levels
- **Real-Time Dashboard**: Live metrics, conversation tracking, and visual workflow timeline
- **Advanced Grading**: Weighted scoring with detailed feedback
- **Database Persistence**: SQLite-based session and user management
- **Authentication**: Token-based user authentication and rate limiting
- **Analytics**: Performance trends, leaderboards, and data export
- **WebSocket Updates**: Real-time state synchronization
- **Custom Scenarios**: Dynamic task generation from user input

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start server
python start_server.py

# Access dashboard
http://localhost:7860
```

## API Endpoints

### Core Endpoints
- `POST /reset` - Start new session
- `POST /step` - Execute action
- `GET /state` - Get current state
- `POST /custom_reset` - Custom scenario

### Authentication
- `POST /auth/register` - Register user
- `POST /auth/login` - Login user

### Analytics
- `GET /analytics/user` - User performance
- `GET /analytics/task/{id}` - Task statistics
- `GET /analytics/leaderboard` - Global rankings

### Monitoring
- `GET /health` - Health check
- `GET /metrics` - System metrics
- `GET /docs` - API documentation

## Task Levels

| Level | Scenario | Max Steps | Description |
|-------|----------|-----------|-------------|
| Easy | Order Status | 4 | Simple inquiry with neutral tone |
| Medium | Refund Processing | 6 | Multi-step workflow with complaints |
| Hard | Multi-Issue Complaint | 8 | Complex angry customer scenario |

## Action Space

- `reply` - Send response to customer
- `ask_details` - Request more information
- `refund` - Process refund
- `escalate` - Escalate to supervisor

## Deployment

### Docker
```bash
docker build -t supportai-env .
docker run -p 7860:7860 supportai-env
```

### Hugging Face Spaces
This project is configured for deployment on Hugging Face Spaces with Docker runtime.

## Tech Stack

- **Backend**: FastAPI + Uvicorn
- **Database**: SQLite with thread-safe operations
- **AI**: OpenAI GPT for tone detection
- **Frontend**: Vanilla JavaScript with WebSocket
- **Deployment**: Docker + Hugging Face Spaces

## OpenEnv Compliance

This environment follows OpenEnv standards:
- Structured API endpoints (`/reset`, `/step`, `/state`)
- Deterministic grading system
- Reproducible results
- Standard observation/action/reward interface

## License

MIT

---

**Version 3.0.0** | Built for AI trainers and researchers
