"""
Shared data models for the Hobbs Agent.

This module defines the TaskEnvelope schema used by all endpoints.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any
from datetime import datetime


class TaskEnvelope(BaseModel):
    """
    Standard task envelope used for communication between agents.

    This schema is reused by all endpoints for consistent message formatting.
    """
    task_id: str = Field(..., description="Unique identifier for the task")
    source: str = Field(..., description="Source agent or system that sent the task")
    target: str = Field(..., description="Target agent or system to receive the task")
    type: str = Field(..., description="Type of task being requested")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Task-specific data payload")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="ISO8601 timestamp of when the task was created"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task-001",
                "source": "congress",
                "target": "hobbs",
                "type": "sensor_ingest",
                "payload": {"sensor_id": "temp-01", "value": 23.5},
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }
