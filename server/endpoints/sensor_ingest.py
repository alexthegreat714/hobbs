"""
Sensor Ingest endpoint for the Hobbs Agent.

Handles incoming sensor data ingestion requests.
"""

from fastapi import APIRouter
from schemas.shared import TaskEnvelope
from config.settings import log_event

router = APIRouter()


@router.post("/sensor_ingest")
async def sensor_ingest(task: TaskEnvelope) -> dict:
    """
    Receive and acknowledge a sensor data ingestion request.

    Args:
        task: The TaskEnvelope containing sensor data

    Returns:
        Acknowledgment response
    """
    log_event("sensor_ingest", task.model_dump())

    return {
        "ok": True,
        "received": "sensor_ingest"
    }
