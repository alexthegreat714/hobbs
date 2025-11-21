"""
Status endpoint for the Hobbs Agent.

Provides health check and status information including sensor statistics.
"""

from fastapi import APIRouter
from config.settings import settings, log_event
from server.sensors.sensor_manager import sensor_manager

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
    """
    log_event("status", {"action": "status_check"})

    return {
        "status": "ok",
        "agent": settings.AGENT_NAME,
        "version": settings.VERSION,
        "sensors_today": sensor_manager.get_sensors_today_count(),
        "index_size": sensor_manager.get_index_size(),
    }
