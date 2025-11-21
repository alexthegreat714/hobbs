"""
Detect Intruder endpoint for the Hobbs Agent.

Handles camera image ingestion and intruder detection with
stubbed classification and direction estimation.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from schemas.shared import TaskEnvelope
from config.settings import log_event
from server.camera.camera_manager import camera_manager


router = APIRouter()


class IntruderPayload(BaseModel):
    """
    Expected payload structure for intruder detection.
    """
    camera_id: str = Field(..., description="Camera identifier (e.g., 'woods_cam')")
    image_base64: Optional[str] = Field(None, description="Base64 encoded image data")
    image_url: Optional[str] = Field(None, description="URL to download image from")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )


def validate_intruder_payload(payload: Dict[str, Any]) -> IntruderPayload:
    """
    Validate that the payload contains required intruder detection fields.

    Args:
        payload: The payload dictionary from TaskEnvelope

    Returns:
        Validated IntruderPayload

    Raises:
        HTTPException: If validation fails
    """
    try:
        validated = IntruderPayload(**payload)

        # Must have either image_base64 or image_url
        if not validated.image_base64 and not validated.image_url:
            raise ValueError("Must provide either 'image_base64' or 'image_url'")

        return validated

    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid intruder detection payload: {str(e)}. "
                   f"Required: camera_id + (image_base64 or image_url)"
        )


@router.post("/detect_intruder")
async def detect_intruder(task: TaskEnvelope) -> dict:
    """
    Receive and process an intruder detection request.

    Workflow:
    1. Decode/download the image
    2. Save image to camera folder
    3. Classify the object (stub)
    4. Estimate direction (stub)
    5. Update camera_index.jsonl
    6. Emit event to Congress
    7. Log to hobbs.log
    8. Return detection result

    Args:
        task: The TaskEnvelope containing detection request details

    Payload must contain:
        - camera_id: str - Camera identifier
        - image_base64: str (optional) - Base64 encoded image
        - image_url: str (optional) - URL to download image
        - metadata: dict (optional) - Additional metadata

    Returns:
        JSON response:
        {
            "ok": true,
            "object": "human|animal|vehicle|unknown",
            "confidence": float,
            "direction": "toward_house|away_from_house|indeterminate",
            "dir_confidence": float
        }

    Raises:
        HTTPException 422: If payload validation fails
    """
    # Log the incoming request
    log_event("detect_intruder", task.model_dump())

    # Validate payload
    intruder_data = validate_intruder_payload(task.payload)

    # Process detection using camera manager
    result, image_path = camera_manager.process_detection(
        camera_id=intruder_data.camera_id,
        image_data=intruder_data.image_base64,
        image_url=intruder_data.image_url,
        metadata=intruder_data.metadata,
    )

    if not result["ok"]:
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to process detection")
        )

    return result
