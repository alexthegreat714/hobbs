"""
Run Task endpoint for the Hobbs Agent.

Handles incoming task execution requests.
"""

from fastapi import APIRouter
from schemas.shared import TaskEnvelope
from config.settings import log_event
from server.memory.memory_manager import memory_manager

router = APIRouter()


@router.post("/run_task")
async def run_task(task: TaskEnvelope) -> dict:
    """
    Receive and acknowledge a task execution request.

    Handles special task types:
    - memory_rebuild: Triggers full memory rebuild from logs

    Args:
        task: The TaskEnvelope containing task details

    Returns:
        Acknowledgment response with task_id
    """
    log_event("run_task", task.model_dump())

    # Check for memory rebuild task
    if task.type == "memory_rebuild":
        target = task.payload.get("target", "")
        if target == "hobbs.memory":
            counts = memory_manager.rebuild_full_memory()
            return {
                "ok": True,
                "message": "memory rebuild complete",
                "task_id": task.task_id,
                "counts": counts,
            }

    return {
        "ok": True,
        "message": "task received",
        "task_id": task.task_id
    }
