"""
Status endpoint for the Hobbs Agent.

Provides health check and status information.
"""

from fastapi import APIRouter
from config.settings import settings, log_event

router = APIRouter()


@router.get("/status")
async def get_status() -> dict:
    """
    Get the current status of the Hobbs agent.

    Returns:
        Status information including agent name and version
    """
    log_event("status", {"action": "status_check"})

    return {
        "status": "ok",
        "agent": settings.AGENT_NAME,
        "version": settings.VERSION
    }
