"""
Task Router for the Hobbs Agent.

Routes incoming tasks to appropriate handlers.
"""

from schemas.shared import TaskEnvelope
from config.settings import logger


def route_task(task: TaskEnvelope) -> dict:
    """
    Route a task to the appropriate handler based on task type.

    This is a placeholder for future task routing logic.

    Args:
        task: The TaskEnvelope to route

    Returns:
        Result of task routing
    """
    logger.info(f"Routing task {task.task_id} of type {task.type}")

    # Placeholder: No real routing logic yet
    return {
        "routed": True,
        "task_id": task.task_id,
        "type": task.type
    }
