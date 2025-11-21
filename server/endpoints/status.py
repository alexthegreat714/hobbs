"""
Status endpoint for the Hobbs Agent.

Provides health check and status information including sensor and weather statistics.
"""

from fastapi import APIRouter
from config.settings import settings, log_event
from server.sensors.sensor_manager import sensor_manager
from server.weather.weather_manager import weather_manager

router = APIRouter()


@router.get("/status")
async def get_status() -> dict:
    """
    Get the current status of the Hobbs agent.

    Returns:
        Status information including:
        - agent name and version
        - sensors_today: number of sensor files for current date
        - index_size: number of entries in sensor_index.jsonl
        - weather_forecasts_today: number of weather files for current date
        - weather_index_size: number of entries in weather_index.jsonl
    """
    log_event("status", {"action": "status_check"})

    return {
        "status": "ok",
        "agent": settings.AGENT_NAME,
        "version": settings.VERSION,
        "sensors_today": sensor_manager.get_sensors_today_count(),
        "index_size": sensor_manager.get_index_size(),
        "weather_forecasts_today": weather_manager.get_forecasts_today_count(),
        "weather_index_size": weather_manager.get_index_size(),
    }
