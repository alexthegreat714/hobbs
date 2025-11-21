"""
Run Task endpoint for the Hobbs Agent.

Handles incoming task execution requests.
"""

from fastapi import APIRouter
from schemas.shared import TaskEnvelope
from config.settings import log_event

router = APIRouter()


@router.post("/run_task")
async def run_task(task: TaskEnvelope) -> dict:
    """
    Receive and acknowledge a task execution request.

    Args:
        task: The TaskEnvelope containing task details

    Returns:
        Acknowledgment response with task_id
    """
    log_event("run_task", task.model_dump())

    return {
        "ok": True,
        "message": "task received",
        "task_id": task.task_id
    }
