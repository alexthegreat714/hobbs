# Hobbs Agent (Phase 2)

Farm management agent implementing the Blank Slate Agent Ecosystem Contract.

## Features

### Phase 1 (Skeleton)
- Implements agent skeleton
- Exposes required endpoints
- Registers with Congress
- Provides logging system
- Includes shared schema for tasks

### Phase 2 (Sensor Pipeline + Data History)
- Fully functional `/sensor_ingest` endpoint
- Sensor file storage system with daily organization
- Time-series event indexing (JSONL)
- Sensor event emitters to Congress (stubbed)
- Query helpers for data retrieval
- Updated `/status` with sensor statistics

## Endpoints

### Mandatory Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/run_task` | POST | Execute a task |
| `/event` | POST | Receive event notifications |
| `/status` | GET | Health check and status (includes sensor stats) |
| `/shutdown` | POST | Graceful shutdown |

### Hobbs-Specific Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sensor_ingest` | POST | Ingest and store sensor data |
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
uvicorn app:app --host 0.0.0.0 --port 5055 --reload

# Or run directly
python app.py
```

## Running Tests

```bash
pytest tests/ -v
```

## Testing Sensor Ingest

Send test sensor data via curl:

```bash
curl -X POST http://localhost:5055/sensor_ingest \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test1",
    "source": "test",
    "target": "hobbs",
    "type": "sensor",
    "payload": {
      "sensor_type": "moisture",
      "value": 0.18,
      "unit": "fraction"
    },
    "timestamp": "2025-11-21T00:00:00Z"
  }'
```

Expected response:
```json
{"ok": true, "stored": true}
```

## Project Structure

```
/Hobbs/
    README.md
    app.py                          # FastAPI application
    /server/
        __init__.py
        endpoints/                  # API endpoint routers
            __init__.py
            run_task.py
            event.py
            status.py
            shutdown.py
            sensor_ingest.py        # Phase 2: Full sensor ingestion
            predict_weather.py
            detect_intruder.py
            control_valve.py
        tasks/
            __init__.py
            task_router.py          # Task routing logic
        events/
            __init__.py
            event_router.py         # Event routing logic
        sensors/                    # Phase 2: Sensor management
            __init__.py
            sensor_manager.py       # Sensor storage and indexing
        utils/                      # Phase 2: Utility functions
            __init__.py
            file_ops.py             # File system operations
            time_ops.py             # Timestamp utilities
    /schemas/
        __init__.py
        shared.py                   # TaskEnvelope model
    /config/
        __init__.py
        settings.py                 # Configuration and logging
    /policies/
        __init__.py
        hobbs_policies.json         # Policy definitions
    /logs/
        .gitkeep
    /data/
        .gitkeep
        /sensors/                   # Phase 2: Sensor data storage
            /YYYY-MM-DD/            # Daily folders
                sensor_type_TIMESTAMP.json
        /index/                     # Phase 2: Index files
            sensor_index.jsonl      # Time-series sensor index
    /tests/
        __init__.py
        test_endpoints.py           # Endpoint tests
        test_sensor_ingest.py       # Phase 2: Sensor ingest tests
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

## Sensor Payload Schema

The `/sensor_ingest` endpoint requires the following payload structure:

```json
{
    "sensor_type": "string (required)",
    "value": "float or object (required)",
    "unit": "string or null (optional)",
    "metadata": "object (optional)"
}
```

## Sensor Index Format

Located at: `~/Desktop/Engineering/Hobbs/data/index/sensor_index.jsonl`

Each line contains:
```json
{
  "timestamp": "ISO8601",
  "sensor_type": "string",
  "value": "number or object",
  "unit": "string or null",
  "path": "relative file path to stored JSON"
}
```

## Sensor Data Storage

Sensor data is stored at: `~/Desktop/Engineering/Hobbs/data/sensors/YYYY-MM-DD/`

Each sensor reading is saved as a JSON file:
```
sensor_type_YYYYMMDD_HHMMSS.json
```

File contents:
```json
{
  "timestamp": "ISO8601",
  "sensor_type": "string",
  "value": "number or object",
  "unit": "string or null",
  "metadata": {},
  "task_id": "string"
}
```

## Congress Integration

### Registration
On startup, the agent registers with Congress by writing to:
`~/Desktop/Engineering/Congress/memory/hobbs_registration.json`

### Event Emission (Phase 2)
Sensor events are emitted to:
`~/Desktop/Engineering/Congress/memory/hobbs_events.log`

Format: `<TIMESTAMP> hobbs.sensor_trigger sensor_type=<TYPE> value=<VALUE>`

## Logging

All endpoint calls are logged to:
`~/Desktop/Engineering/Hobbs/logs/hobbs.log`

Format: `<TIMESTAMP> ENDPOINT: <ENDPOINT_NAME> PAYLOAD: <JSON>`

## Status Response

The `/status` endpoint returns:
```json
{
  "status": "ok",
  "agent": "hobbs",
  "version": "0.2.0",
  "sensors_today": 5,
  "index_size": 42
}
```

- `sensors_today`: Number of sensor files created today
- `index_size`: Total entries in sensor_index.jsonl

## Version

- Current: 0.2.0
- Phase: 2 (Sensor Pipeline + Data History)
