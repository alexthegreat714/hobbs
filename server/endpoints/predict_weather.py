"""
Predict Weather endpoint for the Hobbs Agent.

Handles weather prediction requests.
"""

from fastapi import APIRouter
from schemas.shared import TaskEnvelope
from config.settings import log_event

router = APIRouter()


@router.post("/predict_weather")
async def predict_weather(task: TaskEnvelope) -> dict:
    """
    Receive and acknowledge a weather prediction request.

    Args:
        task: The TaskEnvelope containing prediction request details

    Returns:
        Acknowledgment response
    """
    log_event("predict_weather", task.model_dump())

    return {
        "ok": True,
        "received": "predict_weather"
    }
