"""
Shutdown endpoint for the Hobbs Agent.

Handles graceful shutdown requests.
"""

from fastapi import APIRouter
from schemas.shared import TaskEnvelope
from config.settings import log_event

router = APIRouter()


@router.post("/shutdown")
async def shutdown(task: TaskEnvelope) -> dict:
    """
    Handle a shutdown request.

    Args:
        task: The TaskEnvelope containing shutdown request details

    Returns:
        Acknowledgment of shutdown request
    """
    log_event("shutdown", task.model_dump())

    return {
        "ok": True
    }
