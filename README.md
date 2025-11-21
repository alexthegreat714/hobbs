# Hobbs Agent (Phase 3)

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

## Endpoints

### Mandatory Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/run_task` | POST | Execute a task |
| `/event` | POST | Receive event notifications |
| `/status` | GET | Health check and status (includes sensor + weather stats) |
| `/shutdown` | POST | Graceful shutdown |

### Hobbs-Specific Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sensor_ingest` | POST | Ingest and store sensor data |
| `/predict_weather` | POST | Weather prediction (remote + offline fallback) |
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

## Testing Weather Prediction

Send test weather request via curl:

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

Expected response:
```json
{
  "ok": true,
  "forecast": [
    {
      "time": "2025-11-21T00:00",
      "temperature": 20.5,
      "temperature_unit": "°C",
      "precipitation_probability": 10,
      "wind_speed": 5.0,
      "wind_unit": "km/h"
    },
    ...
  ],
  "confidence": 0.85,
  "source": "remote",
  "location": {"lat": 34.73, "lon": -86.58}
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
            sensor_ingest.py        # Phase 2: Full sensor ingestion
            predict_weather.py      # Phase 3: Weather prediction
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
        weather/                    # Phase 3: Weather management
            __init__.py
            weather_manager.py      # Weather fetching and caching
        utils/                      # Utility functions
            __init__.py
            file_ops.py             # File system operations
            time_ops.py             # Timestamp utilities
            http_ops.py             # Phase 3: HTTP request utilities
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
            /YYYY-MM-DD/
                sensor_type_TIMESTAMP.json
        /weather/                   # Phase 3: Weather forecast storage
            /YYYY-MM-DD/
                weather_TIMESTAMP.json
        /index/                     # Index files
            sensor_index.jsonl      # Time-series sensor index
            weather_index.jsonl     # Phase 3: Weather forecast index
    /tests/
        __init__.py
        test_endpoints.py           # Endpoint tests
        test_sensor_ingest.py       # Phase 2: Sensor ingest tests
        test_weather.py             # Phase 3: Weather tests
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

## Weather Payload Schema

The `/predict_weather` endpoint accepts an optional payload:

```json
{
    "location": {
        "lat": "float (-90 to 90)",
        "lon": "float (-180 to 180)"
    }
}
```

If no location is provided, defaults to Huntsville, AL (34.73, -86.58).

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

## Weather Index Format

Located at: `~/Desktop/Engineering/Hobbs/data/index/weather_index.jsonl`

Each line contains:
```json
{
  "timestamp": "ISO8601",
  "source": "remote or offline",
  "forecast_path": "relative/path/to/file",
  "confidence": "float (0.0-1.0)"
}
```

## Weather Forecast Storage

Weather forecasts are stored at: `~/Desktop/Engineering/Hobbs/data/weather/YYYY-MM-DD/`

Each forecast is saved as a JSON file:
```
weather_YYYYMMDD_HHMMSS.json
```

File contents:
```json
{
  "source": "remote or offline",
  "fetched_at": "ISO8601",
  "location": {"lat": float, "lon": float},
  "hourly": {
    "time": ["..."],
    "temperature_2m": [...],
    "precipitation_probability": [...],
    "wind_speed_10m": [...]
  },
  "hourly_units": {...}
}
```

## Weather Prediction Logic

1. **Remote Fetch**: Attempts to fetch from Open-Meteo API
   - Confidence: 0.85
   - Returns 3-day hourly forecast

2. **Offline Fallback**: If remote fails, generates heuristic estimate
   - Confidence: 0.4
   - Temperature: varies based on time of day
   - Precipitation: ~15% chance
   - Wind: 3-8 mph

## Sensor Data Storage

Sensor data is stored at: `~/Desktop/Engineering/Hobbs/data/sensors/YYYY-MM-DD/`

Each sensor reading is saved as a JSON file:
```
sensor_type_YYYYMMDD_HHMMSS.json
```

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
  "version": "0.3.0",
  "sensors_today": 5,
  "index_size": 42,
  "weather_forecasts_today": 3,
  "weather_index_size": 10
}
```

- `sensors_today`: Number of sensor files created today
- `index_size`: Total entries in sensor_index.jsonl
- `weather_forecasts_today`: Number of weather files created today
- `weather_index_size`: Total entries in weather_index.jsonl

## Version

- Current: 0.3.0
- Phase: 3 (Weather Layer + Local Prediction Engine)
