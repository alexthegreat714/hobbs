"""
Control Valve endpoint for the Hobbs Agent.

Handles valve control requests with Aegis verification,
state management, and history logging.
"""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from schemas.shared import TaskEnvelope
from schemas.actuators import ValveCommandPayload, VALID_ACTIONS, is_valid_action
from config.settings import log_event
from server.actuators.aegis_client import request_verification
from server.actuators.valve_controller import valve_controller


router = APIRouter()


def validate_valve_payload(payload: Dict[str, Any]) -> ValveCommandPayload:
    """
    Validate that the payload contains required valve command fields.

    Args:
        payload: The payload dictionary from TaskEnvelope

    Returns:
        Validated ValveCommandPayload

    Raises:
        HTTPException: If validation fails
    """
    try:
        validated = ValveCommandPayload(**payload)

        # Check action is valid
        if not is_valid_action(validated.action):
            raise ValueError(
                f"Invalid action '{validated.action}'. "
                f"Must be one of: {VALID_ACTIONS}"
            )

        # If action is 'set', value should be provided
        if validated.action.lower() == "set" and validated.value is None:
            # Default to 0.5 if not provided
            validated.value = 0.5

        return validated

    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid valve command payload: {str(e)}. "
                   f"Required: valve_id, action ({VALID_ACTIONS})"
        )


@router.post("/control_valve")
async def control_valve(task: TaskEnvelope) -> dict:
    """
    Receive and process a valve control request.

    Workflow:
    1. Validate ValveCommandPayload from payload
    2. Request verification from Aegis
    3. If denied: log denial, record in history, return error
    4. If verified: apply command, emit event, return success

    Args:
        task: The TaskEnvelope containing valve control details

    Payload must contain:
        - valve_id: str - Valve identifier
        - action: str - "open", "close", "toggle", or "set"
        - value: float (optional) - 0.0-1.0 for 'set' action
        - reason: str (optional) - Reason for command
        - metadata: dict (optional) - Additional metadata

    Returns:
        JSON response:
        {
            "ok": true,
            "valve_id": "...",
            "state": "open|closed|partial",
            "value": float,
            "verified": true
        }

    Raises:
        HTTPException 422: If payload validation fails
        HTTPException 403: If Aegis verification fails
    """
    # Log the incoming request
    log_event("control_valve", task.model_dump())

    # Validate payload
    valve_cmd = validate_valve_payload(task.payload)

    # Prepare command for Aegis verification
    aegis_command = {
        "valve_id": valve_cmd.valve_id,
        "action": valve_cmd.action,
        "value": valve_cmd.value,
        "reason": valve_cmd.reason,
        "source_task_id": task.task_id,
        "source_agent": task.source,
    }

    # Request verification from Aegis
    aegis_result = request_verification(aegis_command)

    # Check verification result
    if not aegis_result.get("verified", False):
        # Record denial in history
        valve_controller.record_denial(
            valve_cmd=valve_cmd,
            aegis_token=aegis_result,
            source_task_id=task.task_id,
            source_agent=task.source,
        )

        raise HTTPException(
            status_code=403,
            detail={
                "ok": False,
                "error": "Aegis verification failed",
                "valve_id": valve_cmd.valve_id,
                "reason": aegis_result.get("details", {}).get("reason", "Unknown"),
            }
        )

    # Apply the command
    result = valve_controller.apply_command(
        valve_cmd=valve_cmd,
        aegis_token=aegis_result,
        source_task_id=task.task_id,
        source_agent=task.source,
    )

    if not result.get("ok", False):
        raise HTTPException(
            status_code=400,
            detail=result
        )

    return result
