# AiWorkOS

The place where work gets done inside ChatGPT.

## Backend

Async Python backend for an AI Work Operating System built with FastAPI, the OpenAI Agents SDK, and an MCP server for reusable tools.

## Features

- FastAPI service with health and workflow endpoints
- Agent registry with orchestrator, research, marketing, and coding agents
- Task decomposition and workflow planning
- MCP server exposing backend tools
- SQLite persistence layer with async access
- Modular structure under `backend/`

## Structure

```text
backend/
  agents/
  workflows/
  mcp_server/
  db/
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Set environment variables:

```bash
export OPENAI_API_KEY=your_key
export AIWORKOS_DEFAULT_MODEL=gpt-4.1
```

## Run the API

```bash
uvicorn backend.main:app --reload
```

## Run the MCP Server

```bash
python3 -m backend.mcp_server.server
```

## Example Request

```bash
curl -X POST http://127.0.0.1:8000/api/v1/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Launch a landing page for an AI code review product",
    "context": {
      "audience": "engineering leaders",
      "deadline": "2 weeks"
    }
  }'
```
