"""
Sensor Ingest endpoint for the Hobbs Agent.

Handles incoming sensor data ingestion requests.
Validates payload, stores sensor data, updates index, and emits events.
"""

from typing import Any, Dict, Optional, Union

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from schemas.shared import TaskEnvelope
from config.settings import log_event
from server.sensors.sensor_manager import sensor_manager
from server.automation.automation_engine import automation_engine
from server.learning.learning_engine import learning_engine


router = APIRouter()


class SensorPayload(BaseModel):
    """
    Expected payload structure for sensor ingest.
    """
    sensor_type: str = Field(..., description="Type of sensor (e.g., moisture, temperature)")
    value: Union[float, Dict[str, Any]] = Field(..., description="Sensor value (number or object)")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


def validate_sensor_payload(payload: Dict[str, Any]) -> SensorPayload:
    """
    Validate that the payload contains required sensor fields.

    Args:
        payload: The payload dictionary from TaskEnvelope

    Returns:
        Validated SensorPayload

    Raises:
        HTTPException: If validation fails
    """
    try:
        return SensorPayload(**payload)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid sensor payload: {str(e)}. Required fields: sensor_type, value"
        )


@router.post("/sensor_ingest")
async def sensor_ingest(task: TaskEnvelope) -> dict:
    """
    Receive and process sensor data ingestion request.

    Validates payload, stores sensor data to file, updates index,
    logs the event, and emits a stubbed internal event to Congress.

    Args:
        task: The TaskEnvelope containing sensor data

    Payload must contain:
        - sensor_type: str - Type of sensor
        - value: float or dict - Sensor reading value
        - unit: str (optional) - Unit of measurement
        - metadata: dict (optional) - Additional metadata

    Returns:
        JSON response: { "ok": true, "stored": true }

    Raises:
        HTTPException 422: If payload validation fails
    """
    # Log the incoming request
    log_event("sensor_ingest", task.model_dump())

    # Validate sensor payload
    sensor_data = validate_sensor_payload(task.payload)

    # Store sensor data using sensor manager
    result = sensor_manager.store_sensor_data(
        sensor_type=sensor_data.sensor_type,
        value=sensor_data.value,
        unit=sensor_data.unit,
        metadata=sensor_data.metadata,
        task_id=task.task_id,
    )

    # Process through automation engine for rule evaluation
    automation_result = None
    if isinstance(sensor_data.value, (int, float)):
        automation_result = automation_engine.process_sensor_data(
            sensor_id=task.task_id,
            sensor_type=sensor_data.sensor_type,
            value=float(sensor_data.value),
        )

    # Increment event counter and check if learning cycle should run
    learning_engine.increment_event_counter()
    learning_triggered = False
    if learning_engine.should_run_learning_cycle(threshold=50):
        learning_engine.run_full_learning_cycle()
        learning_engine.reset_event_counter()
        learning_triggered = True

    return {
        "ok": True,
        "stored": result["stored"],
        "automation": {
            "triggered_actions": len(automation_result.get("triggered_actions", [])) if automation_result else 0,
        },
        "learning_cycle_triggered": learning_triggered,
    }
