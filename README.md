---
title: TechmasterMeta
emoji: "🤖"
colorFrom: "orange"
colorTo: "yellow"
sdk: "docker"
app_file: "Dockerfile"
pinned: false
---

# SupportAI-Env

A production-grade OpenEnv environment for evaluating AI agents on customer support workflows.

## Architecture

Hybrid system: deterministic keyword intent detection + LLM tone detection (OpenAI).

## Quick Start

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=your_key   # optional, fallback works without it
uvicorn main:app --host 0.0.0.0 --port 7860
```

Open http://localhost:7860 for the GUI.

## API

| Endpoint | Method | Description |
|---|---|---|
| `/reset` | POST | Start new episode |
| `/step` | POST | Send agent action |
| `/state` | GET | Get current state |

## Run Inference

```bash
python inference.py
```

## Docker

```bash
docker build -t supportai-env .
docker run -p 7860:7860 -e OPENAI_API_KEY=your_key supportai-env
```

## Tasks

| Task | Difficulty | Scenario |
|---|---|---|
| easy | Easy | Order tracking |
| medium | Medium | Refund workflow |
| hard | Hard | Multi-intent + angry customer |
