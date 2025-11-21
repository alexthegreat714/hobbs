# Hobbs Agent Endpoints Package
from .run_task import router as run_task_router
from .event import router as event_router
from .status import router as status_router
from .shutdown import router as shutdown_router
from .sensor_ingest import router as sensor_ingest_router
from .predict_weather import router as predict_weather_router
from .detect_intruder import router as detect_intruder_router
from .control_valve import router as control_valve_router
from .memory_query import router as memory_query_router

__all__ = [
    "run_task_router",
    "event_router",
    "status_router",
    "shutdown_router",
    "sensor_ingest_router",
    "predict_weather_router",
    "detect_intruder_router",
    "control_valve_router",
    "memory_query_router",
]
