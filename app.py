"""
Hobbs Agent - FastAPI Server

Phase 1: Baseline skeleton with mandatory endpoints, registration, and logging.
No real business logic implemented yet.
"""

import json
import sys
from datetime import datetime
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings, logger
from server.endpoints import (
    run_task_router,
    event_router,
    status_router,
    shutdown_router,
    sensor_ingest_router,
    predict_weather_router,
    detect_intruder_router,
    control_valve_router,
    memory_query_router,
)


def register_with_congress() -> None:
    """
    Register the Hobbs agent with Congress by writing a registration file.

    Creates a JSON file at the Congress memory directory containing:
    - agent name
    - version
    - capabilities
    - registration timestamp
    """
    # Ensure the Congress memory directory exists
    settings.CONGRESS_MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    registration_data = {
        "agent": settings.AGENT_NAME,
        "version": settings.VERSION,
        "capabilities": settings.CAPABILITIES,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    with open(settings.REGISTRATION_FILE, "w") as f:
        json.dump(registration_data, f, indent=2)

    logger.info(f"Registered with Congress: {settings.REGISTRATION_FILE}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting Hobbs Agent v{settings.VERSION}")
    register_with_congress()
    yield
    # Shutdown
    logger.info("Shutting down Hobbs Agent")


# Initialize FastAPI application
app = FastAPI(
    title="Hobbs Agent",
    description="Farm management agent for sensor data, weather prediction, intruder detection, and valve control",
    version=settings.VERSION,
    lifespan=lifespan,
)

# Mount endpoint routers
app.include_router(run_task_router)
app.include_router(event_router)
app.include_router(status_router)
app.include_router(shutdown_router)
app.include_router(sensor_ingest_router)
app.include_router(predict_weather_router)
app.include_router(detect_intruder_router)
app.include_router(control_valve_router)
app.include_router(memory_query_router)


@app.get("/")
async def root():
    """Root endpoint providing basic agent info."""
    return {
        "agent": settings.AGENT_NAME,
        "version": settings.VERSION,
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
