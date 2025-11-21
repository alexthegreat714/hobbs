"""
Event endpoint for the Hobbs Agent.

Handles incoming event notifications from other agents in the ecosystem.
Routes events to appropriate handlers via the event bus.
"""

from fastapi import APIRouter
from schemas.shared import TaskEnvelope
from config.settings import log_event
from server.integration.event_bus import event_bus

router = APIRouter()


# Supported event types
SUPPORTED_EVENTS = [
    "weather.alert",              # From Apollo
    "security.alert",             # From Aegis
    "farm.sensor.update",         # Self or sensor bridges
    "sky.command",                # From Sky
    "hobbs.memory.rebuild",       # From Congress or Sky
    "memory.rebuild",             # Alias
    "learning.trigger",           # Learning cycle trigger
    "congress.policy.update",     # Policy updates from Congress
    "aero.experiment.validation.ready",  # Future use
]


@router.post("/event")
async def receive_event(task: TaskEnvelope) -> dict:
    """
    Receive and process an event notification.

    Routes incoming events to appropriate handlers based on event type.

    Supported event types:
    - weather.alert: Weather alerts from Apollo
    - security.alert: Security alerts from Aegis
    - farm.sensor.update: Sensor update events
    - sky.command: Commands from Sky orchestrator
    - hobbs.memory.rebuild: Memory rebuild requests
    - learning.trigger: Learning cycle triggers
    - congress.policy.update: Policy updates
    - aero.experiment.validation.ready: Experiment validation (future)

    Args:
        task: The TaskEnvelope containing event details

    Returns:
        JSON response:
        {
            "ok": true,
            "handled": true,
            "event_type": str,
            "result": dict
        }
    """
    log_event("event", task.model_dump())

    # Route event through event bus
    result = event_bus.handle_incoming_event(task)

    return {
        "ok": True,
        "handled": result.get("handled", True),
        "event_type": task.type,
        "source": task.source,
        "task_id": task.task_id,
        "result": result.get("result", {})
    }


@router.get("/event/types")
async def get_supported_events() -> dict:
    """
    Get list of supported event types.

    Returns:
        List of event types this endpoint can handle
    """
    return {
        "ok": True,
        "supported_events": SUPPORTED_EVENTS
    }


@router.get("/event/recent")
async def get_recent_events() -> dict:
    """
    Get recent event history.

    Returns:
        List of recently processed events
    """
    recent = event_bus.get_recent_events(limit=20)
    return {
        "ok": True,
        "count": len(recent),
        "events": recent
    }
