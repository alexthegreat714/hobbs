"""
Detect Intruder endpoint for the Hobbs Agent.

Handles intruder detection requests.
"""

from fastapi import APIRouter
from schemas.shared import TaskEnvelope
from config.settings import log_event

router = APIRouter()


@router.post("/detect_intruder")
async def detect_intruder(task: TaskEnvelope) -> dict:
    """
    Receive and acknowledge an intruder detection request.

    Args:
        task: The TaskEnvelope containing detection request details

    Returns:
        Acknowledgment response
    """
    log_event("detect_intruder", task.model_dump())

    return {
        "ok": True,
        "received": "detect_intruder"
    }
