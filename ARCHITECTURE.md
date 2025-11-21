# Hobbs Agent - Complete Architecture Documentation

## Overview

**Hobbs** is a farm management agent designed to operate as part of a multi-agent ecosystem. It handles sensor data ingestion, weather prediction, intruder detection via camera feeds, irrigation valve control, and adaptive learning—all while coordinating with other specialized agents in the system.

**Version:** 0.10.0
**Language:** Python 3.11+
**Framework:** FastAPI
**Storage:** File-based (JSONL indexes, JSON state files)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HOBBS AGENT                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Sensors    │  │   Weather    │  │   Camera     │  │   Valves     │    │
│  │   Pipeline   │  │   Pipeline   │  │   Pipeline   │  │   Control    │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                 │                 │             │
│         ▼                 ▼                 ▼                 ▼             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      AUTOMATION ENGINE                               │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │   │
│  │  │ Rule Engine │  │  Schedule   │  │  Anomaly    │                  │   │
│  │  │             │  │  Engine     │  │  Detection  │                  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│         ┌──────────────────────────┼──────────────────────────┐            │
│         ▼                          ▼                          ▼            │
│  ┌─────────────┐           ┌─────────────┐           ┌─────────────┐       │
│  │   Memory    │           │  Learning   │           │   Vision    │       │
│  │   Manager   │◄─────────►│   Engine    │           │Intelligence │       │
│  └─────────────┘           └─────────────┘           └─────────────┘       │
│         │                          │                          │            │
│         └──────────────────────────┼──────────────────────────┘            │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      INTEGRATION LAYER                               │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │   │
│  │  │Congress │ │  Aegis  │ │  Argus  │ │   Sky   │ │ Apollo  │       │   │
│  │  │ Client  │ │ Adapter │ │ Client  │ │ Client  │ │ Client  │       │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                                     ▼
                    ┌────────────────────────────────┐
                    │     OTHER AGENTS               │
                    │  Congress │ Aegis │ Argus     │
                    │  Sky │ Apollo │ Aero │ etc.   │
                    └────────────────────────────────┘
```

---

## Core Capabilities

### 1. Sensor Data Pipeline (Phase 2)
- **Endpoint:** `POST /sensor_ingest`
- **Function:** Ingests sensor readings (moisture, temperature, pH, etc.)
- **Storage:** Daily files in `data/sensors/YYYY-MM-DD/`
- **Indexing:** JSONL index for fast retrieval
- **Events:** Emits `hobbs.sensor_trigger` to Congress

### 2. Weather Prediction (Phase 3)
- **Endpoint:** `POST /predict_weather`
- **Function:** Fetches forecasts from Open-Meteo API with offline fallback
- **Features:**
  - Remote API integration
  - Heuristic fallback when offline
  - Forecast caching
- **Storage:** Daily files in `data/weather/YYYY-MM-DD/`

### 3. Intruder Detection (Phases 4 & 9)
- **Endpoint:** `POST /detect_intruder`
- **Function:** Analyzes camera images for security threats
- **Vision Pipeline:**
  ```
  Image → YOLO Detection → OCR Extraction → Trajectory Tracking → Suspicion Scoring
  ```
- **Risk Levels:** low, medium, high, critical
- **Scoring Factors:**
  | Factor | Score |
  |--------|-------|
  | Human detected | +0.5 |
  | Night time (22:00-05:00) | +0.3 |
  | Moving toward house | +0.2 |
  | Repeated presence (24h) | +0.25 |
  | Multiple people | +0.4 |
  | Text/plate detected | +0.15 |

### 4. Valve Control (Phase 5)
- **Endpoint:** `POST /control_valve`
- **Actions:** open, close, toggle, set (0.0-1.0)
- **Safety:** All commands verified through Aegis before execution
- **State:** Shadow state persisted to disk
- **History:** Full audit trail in JSONL

### 5. Automation Engine (Phase 6)
- **Rule-based triggers:** Sensor thresholds, events
- **Scheduled tasks:** Time-based automation
- **Anomaly detection:** Statistical z-score based
- **Configuration:** JSON rule files

### 6. RAG Memory System (Phase 7)
- **Endpoint:** `POST /memory_query`
- **Function:** Unified long-term memory across all subsystems
- **Capabilities:**
  - Keyword search
  - Time-range filtering
  - Source/tag filtering
  - Intruder statistics aggregation
  - Sensor trend analysis

### 7. Adaptive Learning (Phase 8)
- **Endpoint:** `GET/POST /learning_report`
- **Computes:**
  - Sensor baselines (mean, std dev, trends)
  - Intruder patterns (peak hours, hotspot cameras)
  - Weather-sensor correlations
  - Valve usage patterns
- **Generates:** Rule refinement suggestions
- **Triggers:** Every 50 events or on-demand

### 8. Vision Intelligence (Phase 9)
- **YOLO Adapter:** Object detection with graceful degradation
- **OCR Adapter:** Text extraction (pytesseract/easyocr)
- **Trajectory Engine:** Multi-frame movement tracking
- **Suspicion Engine:** Risk scoring with automated alerts

### 9. Multi-Agent Integration (Phase 10)
- **Event Bus:** Centralized event routing
- **Congress Client:** Policy management, heartbeats
- **Argus Client:** Metrics collection and publishing
- **Sky Client:** Summary reporting to orchestrator
- **Apollo Client:** Economic event notifications
- **Aegis Adapter:** Action verification wrapper

---

## File Structure

```
/Hobbs/
├── app.py                      # FastAPI application entry point
├── run_hobbs.py                # Daemon script with heartbeat loop
├── README.md                   # User-facing documentation
├── ARCHITECTURE.md             # This file
│
├── /config/
│   ├── settings.py             # Application configuration
│   ├── automation_rules.json   # Automation rule definitions
│   └── automation_schedule.json # Scheduled task definitions
│
├── /schemas/
│   ├── shared.py               # TaskEnvelope and shared models
│   ├── actuators.py            # Valve command schemas
│   └── memory.py               # Memory event schemas
│
├── /server/
│   ├── /endpoints/             # FastAPI route handlers
│   │   ├── run_task.py
│   │   ├── event.py            # Inter-agent event handling
│   │   ├── status.py           # Health and metrics
│   │   ├── shutdown.py
│   │   ├── sensor_ingest.py
│   │   ├── predict_weather.py
│   │   ├── detect_intruder.py
│   │   ├── control_valve.py
│   │   ├── memory_query.py
│   │   └── learning_report.py
│   │
│   ├── /sensors/
│   │   └── sensor_manager.py   # Sensor data storage and retrieval
│   │
│   ├── /weather/
│   │   └── weather_manager.py  # Weather fetching and caching
│   │
│   ├── /camera/
│   │   ├── camera_manager.py   # Image storage and indexing
│   │   ├── classifier_stub.py  # Legacy classification stub
│   │   └── direction_stub.py   # Legacy direction stub
│   │
│   ├── /actuators/
│   │   ├── valve_controller.py # Valve state management
│   │   └── aegis_client.py     # Direct Aegis verification
│   │
│   ├── /automation/
│   │   ├── automation_engine.py # Main coordinator
│   │   ├── rule_engine.py      # Rule evaluation
│   │   ├── schedule_engine.py  # Scheduled tasks
│   │   └── anomaly_engine.py   # Statistical anomaly detection
│   │
│   ├── /memory/
│   │   ├── memory_manager.py   # Event consolidation
│   │   └── query_engine.py     # Search and aggregation
│   │
│   ├── /learning/
│   │   ├── learning_engine.py  # Baseline computation
│   │   ├── rule_refinement.py  # Suggestion generation
│   │   └── patterns.py         # Statistical utilities
│   │
│   ├── /vision/
│   │   ├── yolo_adapter.py     # YOLO object detection
│   │   ├── ocr_adapter.py      # OCR text extraction
│   │   ├── object_detector.py  # Unified detection pipeline
│   │   ├── trajectory_engine.py # Movement tracking
│   │   └── suspicion_engine.py # Risk scoring
│   │
│   ├── /integration/
│   │   ├── event_bus.py        # Inter-agent event routing
│   │   ├── congress_client.py  # Policy and heartbeat
│   │   ├── argus_client.py     # Metrics publishing
│   │   ├── sky_client.py       # Orchestrator communication
│   │   ├── apollo_client.py    # Economic notifications
│   │   └── aegis_adapter.py    # Action verification
│   │
│   └── /utils/
│       ├── file_ops.py
│       ├── time_ops.py
│       ├── http_ops.py
│       └── image_ops.py
│
├── /data/                      # Runtime data (gitignored)
│   ├── /sensors/               # Sensor readings by date
│   ├── /weather/               # Weather forecasts by date
│   ├── /cameras/               # Camera images by date
│   ├── /actuators/             # Valve state and history
│   ├── /automation/            # Automation execution history
│   ├── /memory/                # Unified event memory
│   ├── /learning/              # Learning cache and counters
│   ├── /vision/                # Trajectory and suspicion history
│   └── /index/                 # JSONL indexes
│
└── /tests/
    ├── test_endpoints.py
    ├── test_sensor_ingest.py
    ├── test_weather.py
    ├── test_intruder_detection.py
    ├── test_control_valve.py
    ├── test_automation.py
    ├── test_memory.py
    ├── test_learning.py
    ├── test_vision.py
    └── test_integration.py
```

---

## API Reference

### Mandatory Endpoints (Required by Ecosystem)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/run_task` | POST | Execute arbitrary tasks via TaskEnvelope |
| `/event` | POST | Receive inter-agent events |
| `/status` | GET | Health check with comprehensive metrics |
| `/shutdown` | POST | Graceful shutdown |

### Hobbs-Specific Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sensor_ingest` | POST | Ingest sensor data |
| `/predict_weather` | POST | Get weather forecast |
| `/detect_intruder` | POST | Analyze camera image |
| `/control_valve` | POST | Control irrigation valve |
| `/memory_query` | POST | Query long-term memory |
| `/learning_report` | GET/POST | Get learning insights |

### TaskEnvelope Schema

All POST endpoints accept the standard TaskEnvelope:

```json
{
  "task_id": "unique-id",
  "source": "requesting-agent",
  "target": "hobbs",
  "type": "task-type",
  "payload": { ... },
  "timestamp": "2025-01-01T00:00:00Z"
}
```

---

## Data Flow Examples

### Sensor Ingest Flow
```
1. POST /sensor_ingest with sensor data
2. Validate payload
3. Store to data/sensors/YYYY-MM-DD/sensor_XXX.json
4. Append to index/sensor_index.jsonl
5. Emit event to Congress
6. Check automation rules
7. Update memory manager
8. Increment learning counter
9. Return success response
```

### Intruder Detection Flow
```
1. POST /detect_intruder with image
2. Decode image (base64 or fetch URL)
3. YOLO detection → objects with bounding boxes
4. OCR extraction → text found in image
5. Update trajectory tracking (multi-frame)
6. Calculate suspicion score
7. Determine risk level
8. If high risk: trigger automation alert
9. Store to camera index with vision metadata
10. Emit event to Congress
11. Return comprehensive response
```

### Learning Cycle Flow
```
1. Trigger: 50 events accumulated OR manual request
2. Load 30 days of memory events
3. Compute sensor baselines (mean, std_dev, trends)
4. Analyze intruder patterns (peak hours, hotspots)
5. Calculate weather-sensor correlations
6. Track valve usage patterns
7. Generate rule suggestions
8. Save to learning cache
9. Emit learning.update to Congress
10. Reset event counter
```

---

## Inter-Agent Communication

### Event Types Handled

| Event Type | Source | Action |
|------------|--------|--------|
| `weather.alert` | Congress/Sky | Trigger weather automation |
| `security.alert` | Aegis | Process security event |
| `farm.sensor.update` | External | Ingest sensor data |
| `sky.command` | Sky | Execute orchestrator command |
| `hobbs.memory.rebuild` | Any | Rebuild memory index |
| `learning.trigger` | Congress | Run learning cycle |
| `congress.policy.update` | Congress | Apply new policies |

### Events Emitted

| Event | Destination | Trigger |
|-------|-------------|---------|
| `hobbs.sensor_trigger` | Congress | Sensor ingested |
| `hobbs.weather.update` | Congress | Weather fetched |
| `hobbs.intruder_detected` | Congress | Intruder found |
| `hobbs.valve_change` | Congress | Valve state changed |
| `hobbs.learning.update` | Congress | Learning cycle complete |

### File-Based Integration Paths

```
Congress:
  ~/Desktop/Engineering/Congress/memory/hobbs_registration.json
  ~/Desktop/Engineering/Congress/memory/hobbs_policy.json
  ~/Desktop/Engineering/Congress/memory/hobbs_heartbeat.log
  ~/Desktop/Engineering/Congress/memory/hobbs_events.log

Argus:
  ~/Desktop/Engineering/Argus/metrics/hobbs_metrics.jsonl

Sky:
  ~/Desktop/Engineering/Sky/memory/hobbs_summaries.jsonl

Apollo:
  ~/Desktop/Engineering/Apollo/memory/hobbs_econ_relevant.jsonl

Aegis:
  ~/Desktop/Engineering/Aegis/requests/hobbs_verify.json (future)
```

---

## Running Hobbs

### Development Mode
```bash
# Install dependencies
pip install fastapi uvicorn pydantic pytest httpx

# Run server with auto-reload
uvicorn app:app --host 0.0.0.0 --port 5055 --reload
```

### Production Mode
```bash
# Run daemon with server and heartbeat
python run_hobbs.py --with-server --port 5055

# Or run server separately
uvicorn app:app --host 0.0.0.0 --port 5055 &
python run_hobbs.py --heartbeat-interval 60 --metrics-interval 300
```

### Testing
```bash
# Run all tests
pytest tests/ -v

# Run specific phase tests
pytest tests/test_integration.py -v  # Phase 10
pytest tests/test_vision.py -v       # Phase 9
pytest tests/test_learning.py -v     # Phase 8
```

---

## Current Limitations

### Technical Limitations

1. **File-Based Storage**
   - No database backend
   - Linear scan for queries (O(n))
   - No transactions or ACID guarantees
   - Concurrent write issues possible

2. **Vision System**
   - YOLO/OCR require optional dependencies
   - Graceful fallback returns empty results
   - No GPU acceleration configured
   - Single-frame analysis (trajectory needs history)

3. **Integration**
   - File-based communication only (no HTTP/gRPC)
   - No authentication between agents
   - No encryption of inter-agent data
   - Polling-based, not event-driven

4. **Learning**
   - Statistical only (no ML models)
   - No online learning (batch only)
   - Fixed 30-day analysis window
   - Suggestions require manual review

### Functional Limitations

1. **Weather**
   - Single provider (Open-Meteo)
   - No severe weather alerts
   - Offline heuristics are basic

2. **Valve Control**
   - Aegis verification is stubbed
   - No hardware integration
   - No flow rate measurement

3. **Memory**
   - No semantic search
   - No vector embeddings
   - Basic keyword matching only

---

## Future Work

### Short Term (Next Phases)

1. **Real Aegis Integration**
   - HTTP client for Aegis verification
   - Proper safety constraint checking
   - Denial logging and alerts

2. **HTTP Inter-Agent Communication**
   - Replace file-based stubs with HTTP clients
   - Add authentication (JWT/API keys)
   - Implement retry logic with backoff

3. **Database Backend**
   - SQLite or PostgreSQL for indexes
   - Proper query optimization
   - Transaction support

### Medium Term

1. **Enhanced Vision**
   - GPU acceleration for YOLO
   - Face recognition (with privacy controls)
   - License plate database lookup
   - Real-time video stream processing

2. **ML-Based Learning**
   - Time-series forecasting for sensors
   - Anomaly detection with autoencoders
   - Reinforcement learning for automation

3. **Distributed Operation**
   - Multiple Hobbs instances
   - Load balancing
   - Shared state coordination

### Long Term

1. **Full Ecosystem Integration**
   - Real-time event streaming (Kafka/Redis)
   - Service mesh deployment
   - Kubernetes orchestration

2. **Advanced Automation**
   - Complex event processing
   - Multi-agent coordination
   - Predictive maintenance

3. **User Interface**
   - Web dashboard
   - Mobile app
   - Voice control integration

---

## Test Coverage

| Test File | Tests | Coverage |
|-----------|-------|----------|
| test_endpoints.py | 20 | Core API |
| test_sensor_ingest.py | 15 | Sensor pipeline |
| test_weather.py | 12 | Weather system |
| test_intruder_detection.py | 18 | Camera/detection |
| test_control_valve.py | 14 | Valve control |
| test_automation.py | 16 | Automation engine |
| test_memory.py | 20 | Memory/query |
| test_learning.py | 18 | Learning engine |
| test_vision.py | 23 | Vision pipeline |
| test_integration.py | 30 | Multi-agent |

**Total: 186+ tests**

---

## Dependencies

### Required
- Python 3.11+
- fastapi
- uvicorn
- pydantic
- httpx
- pytest

### Optional (Vision)
- ultralytics (YOLO)
- pytesseract / easyocr (OCR)
- Pillow (image processing)
- numpy

### Optional (Metrics)
- psutil (CPU/memory metrics)

---

## Configuration

### Environment Variables
None required - all configuration in `config/settings.py`

### Key Settings
```python
AGENT_NAME = "hobbs"
VERSION = "0.10.0"
PORT = 5055
LOG_LEVEL = "INFO"

# Paths
DATA_DIR = ~/Desktop/Engineering/Hobbs/data
LOG_DIR = ~/Desktop/Engineering/Hobbs/logs

# Intervals (daemon mode)
HEARTBEAT_INTERVAL = 60      # seconds
METRICS_INTERVAL = 300       # seconds
LEARNING_INTERVAL = 1800     # seconds
```

---

## Contributing

1. Follow existing code patterns
2. Add tests for new features
3. Update documentation
4. Run full test suite before commits

---

## License

Internal use only - Part of the multi-agent ecosystem.

---

*Last Updated: 2025-11-21*
*Version: 0.10.0*
*Phase: 10 - Full Multi-Agent Integration*
