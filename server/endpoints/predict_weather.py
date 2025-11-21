"""
Predict Weather endpoint for the Hobbs Agent.

Handles weather prediction requests with remote fetching and offline fallback.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from schemas.shared import TaskEnvelope
from config.settings import log_event
from server.weather.weather_manager import weather_manager


router = APIRouter()


class LocationPayload(BaseModel):
    """Location coordinates for weather prediction."""
    lat: float = Field(..., description="Latitude", ge=-90, le=90)
    lon: float = Field(..., description="Longitude", ge=-180, le=180)


class WeatherPayload(BaseModel):
    """Optional payload structure for weather prediction."""
    location: Optional[LocationPayload] = Field(
        None, description="Location coordinates (lat/lon)"
    )


def extract_location(payload: Dict[str, Any]) -> Optional[Dict[str, float]]:
    """
    Extract location from payload if present.

    Args:
        payload: The payload dictionary from TaskEnvelope

    Returns:
        Dict with lat/lon or None if not provided
    """
    if not payload:
        return None

    location = payload.get("location")
    if not location:
        return None

    if isinstance(location, dict) and "lat" in location and "lon" in location:
        return {
            "lat": float(location["lat"]),
            "lon": float(location["lon"]),
        }

    return None


def format_forecast_response(
    forecast: Dict[str, Any], confidence: float
) -> List[Dict[str, Any]]:
    """
    Format forecast data into a simplified list for response.

    Args:
        forecast: Raw forecast data from weather manager
        confidence: Confidence score

    Returns:
        List of hourly forecast entries
    """
    hourly = forecast.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    precip = hourly.get("precipitation_probability", [])
    wind = hourly.get("wind_speed_10m", [])

    units = forecast.get("hourly_units", {})

    result = []
    for i in range(min(len(times), 24)):  # Limit to 24 hours
        entry = {
            "time": times[i] if i < len(times) else None,
            "temperature": temps[i] if i < len(temps) else None,
            "temperature_unit": units.get("temperature_2m", "°C"),
            "precipitation_probability": precip[i] if i < len(precip) else None,
            "wind_speed": wind[i] if i < len(wind) else None,
            "wind_unit": units.get("wind_speed_10m", "km/h"),
        }
        result.append(entry)

    return result


@router.post("/predict_weather")
async def predict_weather(task: TaskEnvelope) -> dict:
    """
    Receive and process a weather prediction request.

    Workflow:
    1. Extract location from payload (or use default)
    2. Fetch forecast (remote first, offline fallback)
    3. Store forecast JSON to weather folder
    4. Update weather_index.jsonl
    5. Emit event to Congress
    6. Log to hobbs.log
    7. Return forecast with confidence

    Args:
        task: The TaskEnvelope containing prediction request details

    Payload may contain:
        - location: { "lat": float, "lon": float } (optional)

    Returns:
        JSON response:
        {
            "ok": true,
            "forecast": [...],
            "confidence": float,
            "source": "remote" or "offline"
        }
    """
    # Log the incoming request
    log_event("predict_weather", task.model_dump())

    # Extract location from payload
    location = extract_location(task.payload)

    # Get forecast from weather manager
    forecast, confidence, source = weather_manager.get_forecast(location)

    # Format forecast for response
    forecast_list = format_forecast_response(forecast, confidence)

    return {
        "ok": True,
        "forecast": forecast_list,
        "confidence": confidence,
        "source": source,
        "location": forecast.get("location", {}),
    }
