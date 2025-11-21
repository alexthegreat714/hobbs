# Hobbs Agent (Phase 10)

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

### Phase 7 (RAG Memory & Pattern Insight)
- Unified event memory format (MemoryEvent)
- Memory consolidation from all logs
- Keyword/tag-based retrieval
- Time-based filtering and aggregation
- `/memory_query` endpoint for Sky/Congress
- Intruder statistics and pattern reports
- Sensor trend analysis
- Memory rebuild via `/run_task`

### Phase 8 (Adaptive Learning + Rule Refinement)
- Learning engine with rolling averages and baselines
- Statistical pattern detection (no neural nets/embeddings)
- Sensor baseline computation with trend analysis
- Intruder pattern analysis (peak hours, hotspot cameras)
- Weather-sensor correlation analysis
- Valve usage pattern tracking
- Rule refinement engine with automated suggestions
- Threshold adjustment recommendations
- Alert schedule suggestions based on patterns
- Statistical anomaly detection (z-score based)
- `/learning_report` endpoint (GET/POST)
- Learning cycle triggered every 50 events
- Learning cache and recommendations persistence

### Phase 9 (Full Vision Intelligence)
- YOLO-based object detection (with graceful fallback)
- OCR text extraction (pytesseract/easyocr with fallback)
- Unified object detector combining YOLO + OCR
- Semantic tagging from detected objects
- Multi-frame trajectory tracking
- Movement direction inference (toward/away from house)
- Suspiciousness scoring engine
- Risk level classification (low/medium/high/critical)
- Security alert automation (high suspicion triggers)
- Enriched camera index with vision metadata
- Vision statistics in status endpoint
- Full backward compatibility with Phase 4 response format

### Phase 10 (Full Multi-Agent Integration)
- Event bus for centralized inter-agent event handling
- Congress client for policy management and heartbeats
- Argus client for metrics collection and publishing
- Sky client for sending summaries and status updates
- Apollo client for economic event notifications
- Aegis adapter for high-level action verification
- Upgraded `/event` endpoint with real event routing
- `run_hobbs.py` daemon script for long-lived operation
- Periodic heartbeat to Congress (configurable interval)
- Periodic metrics publishing to Argus
- Policy-based permission checking
- Integration metrics in status endpoint

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
| `/memory_query` | POST | Query long-term memory and get statistics |
| `/learning_report` | GET/POST | Get learning insights and recommendations |

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
        memory/                     # Phase 7: RAG Memory
            __init__.py
            memory_manager.py       # Memory consolidation
            query_engine.py         # Memory search and stats
        learning/                   # Phase 8: Adaptive Learning
            __init__.py
            learning_engine.py      # Baseline and pattern computation
            rule_refinement.py      # Rule suggestion generation
            patterns.py             # Statistical utilities
        integration/                # Phase 10: Multi-Agent Integration
            __init__.py
            event_bus.py            # Centralized event routing
            congress_client.py      # Policy and heartbeat management
            argus_client.py         # Metrics collection and publishing
            sky_client.py           # Sky orchestrator communication
            apollo_client.py        # Apollo economic notifications
            aegis_adapter.py        # Action verification wrapper
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
        memory.py                   # Phase 7: Memory event schema
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
        /memory/                    # Phase 7: Long-term memory
            events.jsonl            # Unified event stream
            intruders.jsonl         # Camera/intruder events
            weather_summary.jsonl   # Weather event summaries
            sensor_summary.jsonl    # Sensor event summaries
        /learning/                  # Phase 8: Learning data
            learning_cache.json     # Cached baselines and patterns
            recommendations.jsonl   # Rule suggestions history
            event_counter.json      # Event counter for learning cycle
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
        test_memory.py              # Phase 7: Memory tests
        test_learning.py            # Phase 8: Learning tests
        test_vision.py              # Phase 9: Vision tests
        test_integration.py         # Phase 10: Integration tests
    run_hobbs.py                    # Phase 10: Daemon entry point
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
  "version": "0.10.0",
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
  "automation_history_count": 12,
  "memory_events_count": 100,
  "intruder_events_count": 15,
  "weather_summary_count": 20,
  "learning_cache_exists": true,
  "learning_events_until_cycle": 35,
  "vision_events_today": 2,
  "suspicious_events_today": 1,
  "trajectory_history_count": 10,
  "vision_detection_available": false,
  "vision_ocr_available": false,
  "policies_loaded": true,
  "last_heartbeat": "2025-11-21T12:00:00Z",
  "last_learning_cycle": "2025-11-21T10:00:00Z",
  "metrics_snapshot": {"health_status": "healthy", "cpu_usage": 15.2}
}
```

- `valves_known`: Number of valves in state file
- `valve_events_count`: Total entries in valve_history.jsonl
- `automation_rules`: Number of loaded automation rules
- `automation_schedules`: Number of scheduled tasks
- `automation_history_count`: Total entries in automation_history.jsonl
- `memory_events_count`: Total entries in events.jsonl
- `intruder_events_count`: Total entries in intruders.jsonl
- `weather_summary_count`: Total entries in weather_summary.jsonl
- `learning_cache_exists`: Whether learning cache file exists
- `learning_events_until_cycle`: Events remaining until next learning cycle
- `vision_events_today`: Camera events processed today
- `suspicious_events_today`: Events with suspicion score >= 0.5
- `trajectory_history_count`: Total trajectory tracking entries
- `vision_detection_available`: Whether YOLO detection is available
- `vision_ocr_available`: Whether OCR engine is available
- `policies_loaded`: Whether Congress policies have been loaded
- `last_heartbeat`: ISO8601 timestamp of last heartbeat sent
- `last_learning_cycle`: ISO8601 timestamp of last learning cycle
- `metrics_snapshot`: Last collected Argus metrics

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

## RAG Memory & Pattern Insight

Hobbs maintains unified long-term memory of:
- Sensor readings
- Weather updates
- Camera/intruder events
- Valve changes
- Automation actions

Memory is stored as JSONL in:
`~/Desktop/Engineering/Hobbs/data/memory/`

### Memory Event Format

Each event follows the unified MemoryEvent schema:

```json
{
  "event_id": "evt_sensor_abc12345",
  "timestamp": "2025-01-21T15:30:00Z",
  "source": "sensor",
  "subtype": "moisture",
  "summary": "Sensor moisture=0.18 at 2025-01-21T15:30:00Z",
  "tags": ["moisture", "low_reading"],
  "raw_path": "/data/sensors/2025-01-21/sensor_001.json",
  "metadata": {"value": 0.18, "unit": "ratio"}
}
```

### Memory Query Endpoint

The `/memory_query` endpoint lets Sky, Aegis, and Congress query memory:

```bash
curl -X POST http://localhost:5055/memory_query \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "mem_test_01",
    "source": "sky",
    "target": "hobbs",
    "type": "memory_query",
    "payload": {
      "query": "intruder",
      "source_filter": ["camera"],
      "limit": 10
    },
    "timestamp": "2025-11-21T00:00:00Z"
  }'
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | string | Text search in summary (case-insensitive) |
| `source_filter` | list | Filter by sources: sensor, weather, camera, valve, automation |
| `subtype_filter` | list | Filter by subtypes: moisture, forecast, intruder, etc. |
| `tags` | list | Filter by tags (all must match) |
| `start_time` | string | Start of time range (ISO8601) |
| `end_time` | string | End of time range (ISO8601) |
| `limit` | int | Maximum results (default 50) |
| `mode` | string | Special mode: "intruder_stats" |
| `days` | int | Days for stats calculation (default 30) |

### Intruder Statistics Mode

Get aggregated intruder statistics:

```bash
curl -X POST http://localhost:5055/memory_query \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "stats_test_01",
    "source": "sky",
    "target": "hobbs",
    "type": "memory_query",
    "payload": {
      "mode": "intruder_stats",
      "days": 30
    },
    "timestamp": "2025-11-21T00:00:00Z"
  }'
```

Response:
```json
{
  "ok": true,
  "stats": {
    "total_intruders": 15,
    "by_camera": {"cam_woods": 8, "cam_driveway": 7},
    "by_hour": {"06": 3, "18": 5, "22": 7},
    "last_seen": "2025-11-20T22:15:00Z"
  }
}
```

### Memory Rebuild

Trigger full memory rebuild via `/run_task`:

```bash
curl -X POST http://localhost:5055/run_task \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "rebuild_01",
    "source": "admin",
    "target": "hobbs",
    "type": "memory_rebuild",
    "payload": {"target": "hobbs.memory"},
    "timestamp": "2025-11-21T00:00:00Z"
  }'
```

## Learning Report Endpoint

The `/learning_report` endpoint provides access to learned patterns and recommendations.

### GET /learning_report

Returns cached learning data and recent recommendations:

```bash
curl http://localhost:5055/learning_report
```

Response:
```json
{
  "ok": true,
  "learning": {
    "timestamp": "2025-11-21T12:00:00Z",
    "events_analyzed": 150,
    "sensor_baselines": {
      "moisture": {"avg": 0.35, "std_dev": 0.08, "trend": "stable"}
    },
    "intruder_patterns": {
      "total_intruders": 12,
      "peak_hours": ["02", "22", "23"]
    }
  },
  "recommendations": [
    {
      "id": "suggest_adjust_moisture_threshold",
      "type": "threshold_adjustment",
      "priority": "medium",
      "description": "Sensor 'moisture' has high variance..."
    }
  ]
}
```

### POST /learning_report

Request a learning report or trigger a learning cycle:

```bash
curl -X POST http://localhost:5055/learning_report \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "learn_01",
    "source": "sky",
    "target": "hobbs",
    "type": "learning_report",
    "payload": {"action": "refresh"},
    "timestamp": "2025-11-21T00:00:00Z"
  }'
```

Payload options:
- `action: "get"` (default) - Return cached report
- `action: "refresh"` - Run new learning cycle and return results

### Learning Cycle

The learning engine analyzes historical data to compute:
- **Sensor Baselines**: Mean, std deviation, trends per sensor type
- **Intruder Patterns**: Peak hours, hotspot cameras, object types
- **Weather Correlation**: Temperature vs. moisture correlation
- **Valve Patterns**: Automation vs. manual ratio, per-valve stats

Learning cycles are triggered:
- Manually via POST with `action: "refresh"`
- Automatically every 50 sensor/weather events

### Rule Suggestions

The rule refinement engine generates suggestions based on patterns:

| Suggestion Type | Trigger | Example |
|-----------------|---------|---------|
| `threshold_adjustment` | High variance sensor | "Adjust moisture threshold to 0.25" |
| `schedule_addition` | Intruder peak hours | "Enable high-alert at 02:00-03:00" |
| `new_automation_rule` | Manual valve patterns | "Automate irrigation based on moisture" |
| `combined_rule` | Weather correlation | "Increase irrigation during hot weather" |

## Vision Intelligence (Phase 9)

The `/detect_intruder` endpoint now provides full vision intelligence.

### Example Request

```bash
curl -X POST http://localhost:5055/detect_intruder \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "intruder_test",
    "source": "sky",
    "target": "hobbs",
    "type": "vision",
    "payload": {
      "camera_id": "woods_cam",
      "image_base64": "<base64 encoded image>"
    },
    "timestamp": "2025-11-21T00:00:00Z"
  }'
```

### Response Format

```json
{
  "ok": true,
  "objects": [
    {"label": "person", "confidence": 0.92, "bbox": [100, 100, 200, 300]}
  ],
  "ocr_text": "ABC-1234",
  "summary": "person detected (text detected)",
  "tags": ["intruder", "human", "night", "has_text"],
  "trajectory": {
    "overall_movement": "toward_house",
    "tracked_objects": [...],
    "frame_count": 3
  },
  "suspicion_score": 0.85,
  "risk_level": "critical",
  "reasons": ["human detected (1)", "night time activity", "moving toward house"],
  "alert_triggered": true,
  "object": "person",
  "confidence": 0.92,
  "direction": "toward_house"
}
```

### Suspicion Scoring

The suspicion engine calculates risk based on:

| Factor | Score | Description |
|--------|-------|-------------|
| Human detected | +0.5 | Person identified in frame |
| Night time | +0.3 | Detection during 22:00-05:00 |
| Toward house | +0.2 | Movement direction toward property |
| Repeated presence | +0.25 | Same type seen within 24 hours |
| Group pattern | +0.4 | Multiple people detected |
| Text/plate detected | +0.15 | OCR found identifying text |
| Vehicle at night | +0.2 | Vehicle during night hours |

Risk levels: low (<0.25), medium (0.25-0.5), high (0.5-0.75), critical (>0.75)

### Vision Components

```
/server/vision/
    yolo_adapter.py      # YOLO object detection wrapper
    ocr_adapter.py       # OCR text extraction wrapper
    object_detector.py   # Unified detection pipeline
    trajectory_engine.py # Multi-frame tracking
    suspicion_engine.py  # Risk scoring engine
```

### Data Files

```
/data/vision/
    trajectory_history.jsonl  # Movement tracking history
    suspicion_scores.jsonl    # Suspicion score history
```

## Multi-Agent Integration (Phase 10)

### Running the Daemon

The `run_hobbs.py` script provides daemon-like operation with heartbeat:

```bash
# Run heartbeat loop only (server started separately)
python run_hobbs.py

# Start server and heartbeat loop together
python run_hobbs.py --with-server

# Run one heartbeat cycle and exit (for testing)
python run_hobbs.py --single-tick

# Custom intervals
python run_hobbs.py --with-server --heartbeat-interval 30 --metrics-interval 120
```

### Event Bus

The event bus handles routing of inter-agent events:

```
Supported Events:
- weather.alert         -> Process weather alerts, trigger automation
- security.alert        -> Handle security alerts from Aegis
- farm.sensor.update    -> Process sensor updates
- sky.command           -> Execute commands from Sky orchestrator
- hobbs.memory.rebuild  -> Trigger memory consolidation
- learning.trigger      -> Trigger learning cycle
- congress.policy.update -> Apply new policies from Congress
```

### Congress Client

Manages policy loading and heartbeat:

```python
from server.integration.congress_client import congress_client

# Load and apply policies
policies = congress_client.load_policies()
congress_client.apply_policies(policies)

# Check permission
if congress_client.check_permission("valve_control"):
    # Perform action
    pass

# Send heartbeat
congress_client.send_heartbeat()
```

### Argus Client

Collects and publishes metrics:

```python
from server.integration.argus_client import argus_client

# Collect metrics
metrics = argus_client.collect_metrics()
# Returns: {cpu_usage, mem_usage, events_today, health_status, ...}

# Publish to Argus
argus_client.publish_metrics(metrics)
```

### Sky and Apollo Clients

File-based communication stubs:

```python
from server.integration.sky_client import sky_client
from server.integration.apollo_client import apollo_client

# Send summary to Sky
sky_client.send_summary({"type": "daily_report", "data": {...}})

# Notify Apollo of economic event
apollo_client.notify_event({"type": "resource_usage", "amount": 100})
```

### Aegis Adapter

High-level wrapper for action verification:

```python
from server.integration.aegis_adapter import aegis_adapter

# Verify any action
result = aegis_adapter.verify_action("valve_control", {"valve_id": "main"})

# Verify valve command specifically
result = aegis_adapter.verify_valve_command("main_irrigation", "open")
```

### Integration File Paths

```
Congress:
  ~/Desktop/Engineering/Congress/memory/hobbs_policy.json     # Policies
  ~/Desktop/Engineering/Congress/memory/hobbs_heartbeat.log   # Heartbeat log
  ~/Desktop/Engineering/Congress/memory/hobbs_events.log      # Event log

Argus:
  ~/Desktop/Engineering/Argus/metrics/hobbs_metrics.jsonl     # Published metrics

Sky:
  ~/Desktop/Engineering/Sky/memory/hobbs_summaries.jsonl      # Summaries sent

Apollo:
  ~/Desktop/Engineering/Apollo/memory/hobbs_econ_relevant.jsonl # Economic events
```

## Version

- Current: 0.10.0
- Phase: 10 (Full Multi-Agent Integration)
