"""
Event endpoint for the Hobbs Agent.

Handles incoming event notifications.
"""

from fastapi import APIRouter
from schemas.shared import TaskEnvelope
from config.settings import log_event

router = APIRouter()


@router.post("/event")
async def receive_event(task: TaskEnvelope) -> dict:
    """
    Receive and acknowledge an event notification.

    Args:
        task: The TaskEnvelope containing event details

    Returns:
        Acknowledgment response with task_id
    """
    log_event("event", task.model_dump())

    return {
        "ok": True,
        "message": "event received",
        "task_id": task.task_id
    }
