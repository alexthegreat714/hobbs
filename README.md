# Hobbs Agent (Phase 6)

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
- Sensor event emitters to Congress
- Query helpers for data retrieval

### Phase 3 (Weather Layer + Local Prediction Engine)
- Fully functional `/predict_weather` endpoint
- Remote weather fetching (Open-Meteo API)
- Offline heuristic prediction fallback
- Weather forecast caching and storage
- Weather index file (JSONL)
- Weather event emitters to Congress

### Phase 4 (Camera & Intruder Detection Framework)
- Fully functional `/detect_intruder` endpoint
- Camera image ingestion (base64 or URL)
- Stubbed ML object classification
- Stubbed direction estimation
- Camera image storage and indexing
- Intruder event emitters to Congress

### Phase 5 (Physical Control Layer)
- Fully functional `/control_valve` endpoint
- Aegis verification for all commands (stubbed)
- Local valve state management (shadow state)
- Persistent valve history log
- Valve change event emitters to Congress
- Support for open/close/toggle/set actions
- State persistence across restarts

### Phase 6 (Automation Engine)
- Rule-based automation engine
- Configurable automation rules (JSON)
- Scheduled task execution
- Anomaly detection stub (placeholder for ML)
- Integration with sensor ingest pipeline
- Integration with weather prediction pipeline
- Weather alert detection (freeze, precipitation)
- Automation history logging

## Endpoints

### Mandatory Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/run_task` | POST | Execute a task |
| `/event` | POST | Receive event notifications |
| `/status` | GET | Health check and status (includes all stats) |
| `/shutdown` | POST | Graceful shutdown |

### Hobbs-Specific Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sensor_ingest` | POST | Ingest and store sensor data |
| `/predict_weather` | POST | Weather prediction (remote + offline fallback) |
| `/detect_intruder` | POST | Camera image intruder detection |
| `/control_valve` | POST | Valve control with Aegis verification |

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

## Testing Valve Control

Send valve control command via curl:

```bash
curl -X POST http://localhost:5055/control_valve \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "valve_test_01",
    "source": "sky",
    "target": "hobbs",
    "type": "control",
    "payload": {
      "valve_id": "main_irrigation",
      "action": "open",
      "value": 1.0,
      "reason": "test_open"
    },
    "timestamp": "2025-11-21T00:00:00Z"
  }'
```

Expected response:
```json
{
  "ok": true,
  "valve_id": "main_irrigation",
  "state": "open",
  "value": 1.0,
  "previous_state": "unknown",
  "verified": true
}
```

### Other Valve Actions

**Close valve:**
```bash
curl -X POST http://localhost:5055/control_valve \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "valve_test_02",
    "source": "sky",
    "target": "hobbs",
    "type": "control",
    "payload": {
      "valve_id": "main_irrigation",
      "action": "close",
      "reason": "end_watering"
    },
    "timestamp": "2025-11-21T01:00:00Z"
  }'
```

**Set valve to 50%:**
```bash
curl -X POST http://localhost:5055/control_valve \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "valve_test_03",
    "source": "sky",
    "target": "hobbs",
    "type": "control",
    "payload": {
      "valve_id": "drip_line_1",
      "action": "set",
      "value": 0.5,
      "reason": "partial_flow"
    },
    "timestamp": "2025-11-21T02:00:00Z"
  }'
```

## Project Structure

```
/Hobbs/
    README.md
    app.py
    /server/
        __init__.py
        endpoints/
            __init__.py
            run_task.py
            event.py
            status.py
            shutdown.py
            sensor_ingest.py
            predict_weather.py
            detect_intruder.py
            control_valve.py        # Phase 5: Full valve control
        tasks/
            __init__.py
            task_router.py
        events/
            __init__.py
            event_router.py
        sensors/
            __init__.py
            sensor_manager.py
        weather/
            __init__.py
            weather_manager.py
        camera/
            __init__.py
            camera_manager.py
            classifier_stub.py
            direction_stub.py
        actuators/                  # Phase 5: Actuator control
            __init__.py
            valve_controller.py     # Valve state management
            aegis_client.py         # Aegis verification stub
        automation/                 # Phase 6: Automation engine
            __init__.py
            automation_engine.py    # Main automation coordinator
            rule_engine.py          # Rule evaluation engine
            schedule_engine.py      # Scheduled task engine
            anomaly_engine.py       # Anomaly detection stub
        utils/
            __init__.py
            file_ops.py
            time_ops.py
            http_ops.py
            image_ops.py
    /schemas/
        __init__.py
        shared.py
        actuators.py                # Phase 5: Valve command schema
    /config/
        __init__.py
        settings.py
        automation_rules.json       # Phase 6: Automation rules
        automation_schedule.json    # Phase 6: Scheduled tasks
    /policies/
        __init__.py
        hobbs_policies.json
    /logs/
        .gitkeep
    /data/
        .gitkeep
        /sensors/
        /weather/
        /cameras/
        /actuators/                 # Phase 5: Actuator data
            valve_state.json        # Current valve states
            valve_history.jsonl     # Valve action history
        /automation/                # Phase 6: Automation data
            automation_history.jsonl
        /index/
            sensor_index.jsonl
            weather_index.jsonl
            camera_index.jsonl
    /tests/
        __init__.py
        test_endpoints.py
        test_sensor_ingest.py
        test_weather.py
        test_intruder_detection.py
        test_control_valve.py       # Phase 5: Valve control tests
        test_automation.py          # Phase 6: Automation tests
```

## Valve Control Payload Schema

The `/control_valve` endpoint requires:

```json
{
    "valve_id": "string (required)",
    "action": "open|close|toggle|set (required)",
    "value": "float 0.0-1.0 (optional, for 'set' action)",
    "reason": "string (optional)",
    "metadata": "object (optional)"
}
```

### Actions

| Action | Description | Resulting State |
|--------|-------------|-----------------|
| `open` | Fully open the valve | state: "open", value: 1.0 |
| `close` | Fully close the valve | state: "closed", value: 0.0 |
| `toggle` | Toggle between open/closed | Opposite of current state |
| `set` | Set to specific position | state: "partial", value: 0.0-1.0 |

## Valve State File

Located at: `~/Desktop/Engineering/Hobbs/data/actuators/valve_state.json`

Contains current state of all known valves:
```json
{
  "main_irrigation": {
    "state": "open",
    "value": 1.0,
    "last_update": "2025-01-21T15:30:00Z"
  },
  "drip_line_1": {
    "state": "partial",
    "value": 0.5,
    "last_update": "2025-01-21T16:00:00Z"
  }
}
```

## Valve History Format

Located at: `~/Desktop/Engineering/Hobbs/data/actuators/valve_history.jsonl`

Each line contains:
```json
{
  "timestamp": "ISO8601",
  "valve_id": "string",
  "action": "open|close|toggle|set",
  "value": "float or null",
  "previous_state": "string",
  "new_state": "string",
  "reason": "string or null",
  "aegis_signature": "string",
  "aegis_verified": true,
  "source_task_id": "string",
  "source_agent": "string"
}
```

## Aegis Integration

All valve commands are verified through Aegis before execution.

Current implementation: **Stub** (always returns verified=true)

Future implementation will:
- Make HTTP POST to Aegis /verify endpoint
- Include command details in request
- Wait for Aegis approval before proceeding
- Record denials in history

## Congress Integration

### Registration
On startup, the agent registers with Congress by writing to:
`~/Desktop/Engineering/Congress/memory/hobbs_registration.json`

### Event Emission
Events are emitted to:
`~/Desktop/Engineering/Congress/memory/hobbs_events.log`

Formats:
- Sensor: `<TIMESTAMP> hobbs.sensor_trigger sensor_type=<TYPE> value=<VALUE>`
- Weather: `<TIMESTAMP> hobbs.weather.update FORECAST_SAVED:<PATH>`
- Intruder: `<TIMESTAMP> hobbs.intruder_detected camera=<ID> object=<TYPE> confidence=<CONF> image=<PATH>`
- Valve: `<TIMESTAMP> hobbs.valve_change VALVE:<ID> ACTION:<ACTION> VALUE:<VALUE>`

## Status Response

The `/status` endpoint returns:
```json
{
  "status": "ok",
  "agent": "hobbs",
  "version": "0.6.0",
  "sensors_today": 5,
  "index_size": 42,
  "weather_forecasts_today": 3,
  "weather_index_size": 10,
  "camera_events_today": 2,
  "camera_index_size": 15,
  "valves_known": 3,
  "valve_events_count": 25,
  "automation_rules": 4,
  "automation_schedules": 3,
  "automation_history_count": 12
}
```

- `valves_known`: Number of valves in state file
- `valve_events_count`: Total entries in valve_history.jsonl
- `automation_rules`: Number of loaded automation rules
- `automation_schedules`: Number of scheduled tasks
- `automation_history_count`: Total entries in automation_history.jsonl

## Automation Engine

### Rule Configuration

Rules are defined in `config/automation_rules.json`:

```json
{
  "version": "0.1.0",
  "rules": [
    {
      "id": "irrigation_moisture_low",
      "trigger": {"sensor_type": "moisture", "operator": "<", "value": 0.15},
      "condition": {"weather": "no_freeze_soon"},
      "action": {"valve_id": "main_irrigation", "command": "open", "value": 1.0}
    }
  ]
}
```

### Trigger Types

| Trigger Type | Description | Example |
|--------------|-------------|---------|
| Sensor | Triggers on sensor value | `{"sensor_type": "moisture", "operator": "<", "value": 0.15}` |
| Event | Triggers on event | `{"event": "hobbs.weather.alert"}` |

### Operators

Supported operators: `<`, `<=`, `>`, `>=`, `==`, `!=`

### Conditions

| Condition | Description |
|-----------|-------------|
| `no_freeze_soon` | No freezing temperatures in next 24 hours |
| `no_rain_soon` | No precipitation in next 6 hours |

### Schedule Configuration

Schedules are defined in `config/automation_schedule.json`:

```json
{
  "version": "0.1.0",
  "schedule": [
    {
      "id": "midday_irrigation_check",
      "time": "12:00",
      "task": {"type": "automation_check", "payload": {"rule_group": "irrigation"}}
    }
  ]
}
```

### Anomaly Detection

The anomaly detection engine is currently a **stub** that returns no anomalies for all inputs. Future implementation will include ML-based anomaly detection for:
- Sensor value anomalies
- Pattern anomalies (time-series)
- System state anomalies

### Automation History

Located at: `~/Desktop/Engineering/Hobbs/data/automation/automation_history.jsonl`

Each line contains:
```json
{
  "trigger_type": "sensor_trigger|event_trigger|schedule_trigger",
  "action": {
    "rule_id": "string",
    "action": {...},
    "trigger_context": {...}
  },
  "timestamp": "ISO8601"
}
```

## Version

- Current: 0.6.0
- Phase: 6 (Automation Engine)
