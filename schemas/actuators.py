"""
Actuator data models for the Hobbs Agent.

Defines schemas for valve control and other physical actuators.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ValveCommandPayload(BaseModel):
    """
    Payload structure for valve control commands.

    Used by the /control_valve endpoint to receive and validate
    valve control instructions.
    """
    valve_id: str = Field(
        ...,
        description="Unique identifier for the valve (e.g., 'main_irrigation')"
    )
    action: str = Field(
        ...,
        description="Action to perform: 'open', 'close', 'toggle', or 'set'"
    )
    value: Optional[float] = Field(
        None,
        description="Value for 'set' action (0.0-1.0 representing % open)",
        ge=0.0,
        le=1.0
    )
    reason: Optional[str] = Field(
        None,
        description="Reason for the valve command"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata for the command"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "valve_id": "main_irrigation",
                "action": "open",
                "value": 1.0,
                "reason": "scheduled_watering",
                "metadata": {"zone": "north_field"}
            }
        }


# Valid actions for valve commands
VALID_ACTIONS = ["open", "close", "toggle", "set"]


def is_valid_action(action: str) -> bool:
    """
    Check if an action is valid.

    Args:
        action: The action string to validate

    Returns:
        True if valid, False otherwise
    """
    return action.lower() in VALID_ACTIONS
