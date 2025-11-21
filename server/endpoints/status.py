"""
Status endpoint for the Hobbs Agent.

Provides health check and status information including sensor, weather, camera, and valve statistics.
"""

from fastapi import APIRouter
from config.settings import settings, log_event
from server.sensors.sensor_manager import sensor_manager
from server.weather.weather_manager import weather_manager
from server.camera.camera_manager import camera_manager
from server.actuators.valve_controller import valve_controller
from server.automation.automation_engine import automation_engine
from server.memory.memory_manager import memory_manager
from server.learning.learning_engine import learning_engine
from server.vision.trajectory_engine import trajectory_engine
from server.vision.suspicion_engine import suspicion_engine
from server.vision.object_detector import object_detector

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
        - camera_events_today: number of camera images for current date
        - camera_index_size: number of entries in camera_index.jsonl
        - valves_known: number of valves in state
        - valve_events_count: number of entries in valve_history.jsonl
    """
    log_event("status", {"action": "status_check"})

    # Get automation stats
    automation_stats = automation_engine.get_stats()

    return {
        "status": "ok",
        "agent": settings.AGENT_NAME,
        "version": settings.VERSION,
        "sensors_today": sensor_manager.get_sensors_today_count(),
        "index_size": sensor_manager.get_index_size(),
        "weather_forecasts_today": weather_manager.get_forecasts_today_count(),
        "weather_index_size": weather_manager.get_index_size(),
        "camera_events_today": camera_manager.get_camera_events_today_count(),
        "camera_index_size": camera_manager.get_index_size(),
        "valves_known": valve_controller.get_valves_count(),
        "valve_events_count": valve_controller.get_history_count(),
        "automation_rules": automation_stats.get("rules_loaded", 0),
        "automation_schedules": automation_stats.get("schedules_loaded", 0),
        "automation_history_count": automation_stats.get("history_count", 0),
        "memory_events_count": memory_manager.get_events_count(),
        "intruder_events_count": memory_manager.get_intruders_count(),
        "weather_summary_count": memory_manager.get_weather_summary_count(),
        "learning_cache_exists": learning_engine.cache_file.exists(),
        "learning_events_until_cycle": learning_engine.get_events_until_cycle(threshold=50),
        # Vision stats
        "vision_events_today": camera_manager.get_camera_events_today_count(),
        "suspicious_events_today": suspicion_engine.get_suspicious_count_today(),
        "average_suspicion_score_last_24h": suspicion_engine.get_average_score_last_24h(),
        "trajectory_history_count": trajectory_engine.get_history_count(),
        "vision_detection_available": object_detector.yolo.available,
        "vision_ocr_available": object_detector.ocr.available,
    }
