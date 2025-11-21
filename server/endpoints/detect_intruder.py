"""
Detect Intruder endpoint for the Hobbs Agent.

Handles camera image ingestion and intruder detection with
full vision intelligence including object detection, trajectory
tracking, and suspiciousness scoring.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from schemas.shared import TaskEnvelope
from config.settings import log_event
from server.camera.camera_manager import camera_manager
from server.vision.object_detector import object_detector
from server.vision.trajectory_engine import trajectory_engine
from server.vision.suspicion_engine import suspicion_engine
from server.automation.automation_engine import automation_engine
from server.learning.learning_engine import learning_engine
from server.utils.time_ops import now_iso


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
    1. Save raw image to camera folder
    2. Run object detection (YOLO + OCR)
    3. Run trajectory tracking
    4. Compute suspiciousness score
    5. Update camera_index.jsonl with enriched metadata
    6. Emit event to Congress
    7. Check for security alerts
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
            "objects": [...],
            "ocr_text": "...",
            "trajectory": {...},
            "suspicion_score": float,
            "reasons": [...],
            "risk_level": "low|medium|high|critical"
        }

    Raises:
        HTTPException 422: If payload validation fails
    """
    # Log the incoming request
    log_event("detect_intruder", task.model_dump())

    # Validate payload
    intruder_data = validate_intruder_payload(task.payload)
    timestamp = now_iso()

    # Step 1: Save the image
    image_path = camera_manager.save_image(
        camera_id=intruder_data.camera_id,
        image_data=intruder_data.image_base64,
        image_url=intruder_data.image_url,
    )

    if not image_path:
        raise HTTPException(
            status_code=500,
            detail="Failed to save image"
        )

    # Step 2: Run object detection (YOLO + OCR)
    detection_result = object_detector.detect_objects(
        str(image_path),
        run_ocr=True,
        timestamp=timestamp
    )

    # Step 3: Run trajectory tracking
    trajectory_result = trajectory_engine.track(
        camera_id=intruder_data.camera_id,
        timestamp=timestamp,
        objects=detection_result.get("objects", [])
    )

    # Step 4: Compute suspiciousness score
    suspicion_event = {
        "objects": detection_result.get("objects", []),
        "trajectory": trajectory_result,
        "ocr_text": detection_result.get("ocr_text", ""),
        "timestamp": timestamp,
        "camera_id": intruder_data.camera_id,
        "tags": detection_result.get("tags", [])
    }
    suspicion_result = suspicion_engine.compute_suspicion(suspicion_event)

    # Step 5: Build enriched index entry
    from pathlib import Path
    DATA_DIR = Path.home() / "Desktop" / "Engineering" / "Hobbs" / "data"
    relative_path = str(image_path.relative_to(DATA_DIR))

    # Determine primary object (for backward compatibility)
    objects = detection_result.get("objects", [])
    primary_object = "unknown"
    primary_confidence = 0.0
    if objects:
        # Get highest confidence object
        best = max(objects, key=lambda x: x.get("confidence", 0))
        primary_object = best.get("label", "unknown")
        primary_confidence = best.get("confidence", 0.0)

    index_entry = {
        "timestamp": timestamp,
        "camera_id": intruder_data.camera_id,
        "object": primary_object,
        "obj_conf": primary_confidence,
        "direction": trajectory_result.get("overall_movement", "indeterminate"),
        "dir_conf": 0.5,  # Default confidence
        "image_path": relative_path,
        # Enriched fields
        "objects": objects,
        "bounding_boxes": [o.get("bbox") for o in objects if "bbox" in o],
        "ocr_text": detection_result.get("ocr_text", ""),
        "tags": detection_result.get("tags", []),
        "suspicion_score": suspicion_result.get("score", 0.0),
        "risk_level": suspicion_result.get("risk_level", "low"),
        "movement_label": trajectory_result.get("overall_movement", "indeterminate"),
    }

    # Add user metadata if provided
    if intruder_data.metadata:
        index_entry["metadata"] = intruder_data.metadata

    # Append to index
    camera_manager.append_index(index_entry)

    # Step 6: Emit event to Congress
    _emit_intruder_event(
        camera_id=intruder_data.camera_id,
        objects=objects,
        suspicion_score=suspicion_result.get("score", 0.0),
        risk_level=suspicion_result.get("risk_level", "low"),
        image_path=image_path,
        timestamp=timestamp
    )

    # Step 7: Check for security alerts
    alert_triggered = False
    if suspicion_result.get("score", 0) >= 0.75:
        # High suspicion - trigger security alert via automation
        automation_engine.process_event(
            event_type="hobbs.security.alert",
            event_payload={
                "camera_id": intruder_data.camera_id,
                "suspicion_score": suspicion_result.get("score"),
                "risk_level": suspicion_result.get("risk_level"),
                "reasons": suspicion_result.get("reasons", []),
                "objects": [o.get("label") for o in objects],
            }
        )
        alert_triggered = True

    # Increment event counter for learning
    learning_engine.increment_event_counter()
    learning_triggered = False
    if learning_engine.should_run_learning_cycle(threshold=50):
        learning_engine.run_full_learning_cycle()
        learning_engine.reset_event_counter()
        learning_triggered = True

    # Build response
    return {
        "ok": True,
        "objects": objects,
        "ocr_text": detection_result.get("ocr_text", ""),
        "summary": detection_result.get("summary", ""),
        "tags": detection_result.get("tags", []),
        "trajectory": {
            "overall_movement": trajectory_result.get("overall_movement"),
            "tracked_objects": trajectory_result.get("tracked_objects", []),
            "frame_count": trajectory_result.get("frame_count", 1)
        },
        "suspicion_score": suspicion_result.get("score", 0.0),
        "risk_level": suspicion_result.get("risk_level", "low"),
        "reasons": suspicion_result.get("reasons", []),
        "alert_triggered": alert_triggered,
        "learning_cycle_triggered": learning_triggered,
        # Backward compatibility
        "object": primary_object,
        "confidence": primary_confidence,
        "direction": trajectory_result.get("overall_movement", "indeterminate"),
        "dir_confidence": 0.5,
    }


def _emit_intruder_event(
    camera_id: str,
    objects: list,
    suspicion_score: float,
    risk_level: str,
    image_path,
    timestamp: str
) -> None:
    """
    Emit an intruder detection event to Congress.
    """
    from pathlib import Path
    from server.utils.file_ops import ensure_folder

    CONGRESS_EVENTS_LOG = Path.home() / "Desktop" / "Engineering" / "Congress" / "memory" / "hobbs_events.log"
    ensure_folder(CONGRESS_EVENTS_LOG.parent)

    # Build object summary
    obj_labels = [o.get("label", "unknown") for o in objects]
    obj_summary = ",".join(obj_labels) if obj_labels else "none"

    event_line = (
        f"{timestamp} hobbs.intruder.detected "
        f"camera={camera_id} objects={obj_summary} "
        f"suspicion={suspicion_score:.2f} risk={risk_level} "
        f"image={image_path}\n"
    )

    with open(CONGRESS_EVENTS_LOG, "a") as f:
        f.write(event_line)
