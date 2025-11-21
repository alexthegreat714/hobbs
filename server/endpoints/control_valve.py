"""
Control Valve endpoint for the Hobbs Agent.

Handles valve control requests.
"""

from fastapi import APIRouter
from schemas.shared import TaskEnvelope
from config.settings import log_event

router = APIRouter()


@router.post("/control_valve")
async def control_valve(task: TaskEnvelope) -> dict:
    """
    Receive and acknowledge a valve control request.

    Args:
        task: The TaskEnvelope containing valve control details

    Returns:
        Acknowledgment response
    """
    log_event("control_valve", task.model_dump())

    return {
        "ok": True,
        "received": "control_valve"
    }
