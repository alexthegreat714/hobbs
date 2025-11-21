"""
Event Router for the Hobbs Agent.

Routes incoming events to appropriate handlers.
"""

from schemas.shared import TaskEnvelope
from config.settings import logger


def route_event(event: TaskEnvelope) -> dict:
    """
    Route an event to the appropriate handler based on event type.

    This is a placeholder for future event routing logic.

    Args:
        event: The TaskEnvelope containing event data

    Returns:
        Result of event routing
    """
    logger.info(f"Routing event {event.task_id} of type {event.type}")

    # Placeholder: No real routing logic yet
    return {
        "routed": True,
        "task_id": event.task_id,
        "type": event.type
    }
