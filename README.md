# Hobbs Agent (Phase 1)

Farm management agent implementing the Blank Slate Agent Ecosystem Contract.

## Features

- Implements agent skeleton
- Exposes required endpoints
- Registers with Congress
- Provides logging system
- Includes shared schema for tasks
- No real logic yet

## Endpoints

### Mandatory Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/run_task` | POST | Execute a task |
| `/event` | POST | Receive event notifications |
| `/status` | GET | Health check and status |
| `/shutdown` | POST | Graceful shutdown |

### Hobbs-Specific Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sensor_ingest` | POST | Ingest sensor data |
| `/predict_weather` | POST | Weather prediction requests |
| `/detect_intruder` | POST | Intruder detection requests |
| `/control_valve` | POST | Valve control requests |

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn pydantic pytest httpx
```

## Running the Server

```bash
# Run with uvicorn
uvicorn app:app --host 0.0.0.0 --port 8001 --reload

# Or run directly
python app.py
```

## Running Tests

```bash
pytest tests/ -v
```

## Project Structure

```
/Hobbs/
    README.md
    app.py                      # FastAPI application
    /server/
        __init__.py
        endpoints/              # API endpoint routers
            __init__.py
            run_task.py
            event.py
            status.py
            shutdown.py
            sensor_ingest.py
            predict_weather.py
            detect_intruder.py
            control_valve.py
        tasks/
            __init__.py
            task_router.py      # Task routing logic
        events/
            __init__.py
            event_router.py     # Event routing logic
    /schemas/
        __init__.py
        shared.py               # TaskEnvelope model
    /config/
        __init__.py
        settings.py             # Configuration and logging
    /policies/
        __init__.py
        hobbs_policies.json     # Policy definitions
    /logs/
        .gitkeep
    /data/
        .gitkeep
    /tests/
        test_endpoints.py       # Endpoint tests
```

## TaskEnvelope Schema

All endpoints accept a `TaskEnvelope` with the following fields:

```json
{
    "task_id": "string",
    "source": "string",
    "target": "string",
    "type": "string",
    "payload": {},
    "timestamp": "ISO8601 string"
}
```

## Congress Registration

On startup, the agent registers with Congress by writing to:
`~/Desktop/Engineering/Congress/memory/hobbs_registration.json`

## Logging

All endpoint calls are logged to:
`~/Desktop/Engineering/Hobbs/logs/hobbs.log`

Format: `<TIMESTAMP> ENDPOINT: <ENDPOINT_NAME> PAYLOAD: <JSON>`

## Version

- Current: 0.1.0
- Phase: 1 (Skeleton)
