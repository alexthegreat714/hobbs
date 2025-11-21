# Hobbs Agent (Phase 4)

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

### Phase 3 (Weather Layer + Local Prediction Engine)
- Fully functional `/predict_weather` endpoint
- Remote weather fetching (Open-Meteo API)
- Offline heuristic prediction fallback
- Weather forecast caching and storage
- Weather index file (JSONL)
- Weather event emitters to Congress
- Structured forecast data for later phases

### Phase 4 (Camera & Intruder Detection Framework)
- Fully functional `/detect_intruder` endpoint
- Camera image ingestion (base64 or URL)
- Stubbed ML object classification (human/animal/vehicle/unknown)
- Stubbed direction estimation (toward/away/indeterminate)
- Camera image storage by camera ID
- Camera index file (JSONL)
- Intruder event emitters to Congress
- Ready for YOLOv8 integration in later phases

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

## Testing Weather Prediction

```bash
curl -X POST http://localhost:5055/predict_weather \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test_weather",
    "source": "test",
    "target": "hobbs",
    "type": "weather",
    "payload": {
      "location": {"lat": 34.73, "lon": -86.58}
    },
    "timestamp": "2025-11-21T00:00:00Z"
  }'
```

## Testing Intruder Detection

Send test intruder detection with base64 image:

```bash
# First, encode an image to base64
IMAGE_BASE64=$(base64 -w0 /path/to/image.png)

curl -X POST http://localhost:5055/detect_intruder \
  -H "Content-Type: application/json" \
  -d "{
    \"task_id\": \"test_intruder\",
    \"source\": \"test\",
    \"target\": \"hobbs\",
    \"type\": \"intruder\",
    \"payload\": {
      \"camera_id\": \"woods_cam\",
      \"image_base64\": \"${IMAGE_BASE64}\",
      \"metadata\": {\"test\": true}
    },
    \"timestamp\": \"2025-11-21T00:00:00Z\"
  }"
```

Expected response:
```json
{
  "ok": true,
  "object": "unknown",
  "confidence": 0.15,
  "direction": "indeterminate",
  "dir_confidence": 0.10
}
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
            sensor_ingest.py
            predict_weather.py
            detect_intruder.py      # Phase 4: Intruder detection
            control_valve.py
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
        camera/                     # Phase 4: Camera management
            __init__.py
            camera_manager.py       # Camera storage and indexing
            classifier_stub.py      # Stubbed object classification
            direction_stub.py       # Stubbed direction estimation
        utils/
            __init__.py
            file_ops.py
            time_ops.py
            http_ops.py
            image_ops.py            # Phase 4: Image utilities
    /schemas/
        __init__.py
        shared.py
    /config/
        __init__.py
        settings.py
    /policies/
        __init__.py
        hobbs_policies.json
    /logs/
        .gitkeep
    /data/
        .gitkeep
        /sensors/
            /YYYY-MM-DD/
        /weather/
            /YYYY-MM-DD/
        /cameras/                   # Phase 4: Camera image storage
            /woods_cam/
            /driveway_cam/
            /barn_cam/
        /index/
            sensor_index.jsonl
            weather_index.jsonl
            camera_index.jsonl      # Phase 4: Camera event index
    /tests/
        __init__.py
        test_endpoints.py
        test_sensor_ingest.py
        test_weather.py
        test_intruder_detection.py  # Phase 4: Intruder detection tests
```

## Intruder Detection Payload Schema

The `/detect_intruder` endpoint requires:

```json
{
    "camera_id": "string (required)",
    "image_base64": "string (optional, base64 encoded)",
    "image_url": "string (optional, URL to download)",
    "metadata": "object (optional)"
}
```

Must provide either `image_base64` or `image_url`.

## Camera Index Format

Located at: `~/Desktop/Engineering/Hobbs/data/index/camera_index.jsonl`

Each line contains:
```json
{
  "timestamp": "ISO8601",
  "camera_id": "string",
  "object": "human|animal|vehicle|unknown",
  "obj_conf": "float (0.0-1.0)",
  "direction": "toward_house|away_from_house|indeterminate",
  "dir_conf": "float (0.0-1.0)",
  "image_path": "relative/path/to/image.png"
}
```

## Camera Image Storage

Camera images are stored at: `~/Desktop/Engineering/Hobbs/data/cameras/<camera_id>/`

Each image is saved as:
```
YYYYMMDD_HHMMSS.png
```

## Classification Logic (Stub)

Current stubbed classification:
- If filename contains "test_human" → returns "human" (conf: 0.85)
- If filename contains "test_animal" → returns "animal" (conf: 0.80)
- If filename contains "test_vehicle" → returns "vehicle" (conf: 0.82)
- Otherwise → returns "unknown" (conf: 0.15)

Future phases will integrate YOLOv8 for real classification.

## Direction Logic (Stub)

Current stubbed direction estimation:
- Always returns "indeterminate" (conf: 0.10)

Future phases will implement geometric direction inference based on camera position.

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

## Status Response

The `/status` endpoint returns:
```json
{
  "status": "ok",
  "agent": "hobbs",
  "version": "0.4.0",
  "sensors_today": 5,
  "index_size": 42,
  "weather_forecasts_today": 3,
  "weather_index_size": 10,
  "camera_events_today": 2,
  "camera_index_size": 15
}
```

- `sensors_today`: Number of sensor files created today
- `index_size`: Total entries in sensor_index.jsonl
- `weather_forecasts_today`: Number of weather files created today
- `weather_index_size`: Total entries in weather_index.jsonl
- `camera_events_today`: Number of camera images captured today
- `camera_index_size`: Total entries in camera_index.jsonl

## Version

- Current: 0.4.0
- Phase: 4 (Camera & Intruder Detection Framework)
