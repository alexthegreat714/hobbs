"""
Memory schema definitions for Hobbs Agent.

Defines the unified event memory format used for RAG memory
and pattern learning.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MemoryEvent(BaseModel):
    """
    Unified event memory format.

    All memory JSONL files store line-delimited MemoryEvent objects.
    """
    event_id: str = Field(..., description="Unique event identifier")
    timestamp: str = Field(..., description="ISO8601 timestamp")
    source: str = Field(..., description="Event source: sensor, weather, camera, valve, automation")
    subtype: str = Field(..., description="Event subtype: moisture, forecast, intruder, valve_change, etc.")
    summary: str = Field(..., description="Short human-readable description")
    tags: List[str] = Field(default_factory=list, description="Searchable tags")
    raw_path: Optional[str] = Field(None, description="Pointer to original JSON or image path")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Freeform metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "evt_sensor_20250121_001",
                "timestamp": "2025-01-21T15:30:00Z",
                "source": "sensor",
                "subtype": "moisture",
                "summary": "Sensor moisture=0.18 at 2025-01-21T15:30:00Z",
                "tags": ["moisture", "low_reading"],
                "raw_path": "/data/sensors/2025-01-21/sensor_001.json",
                "metadata": {"value": 0.18, "unit": "ratio"}
            }
        }


class MemoryQueryPayload(BaseModel):
    """Payload for memory query requests."""
    query: Optional[str] = Field(None, description="Text search query")
    source_filter: Optional[List[str]] = Field(None, description="Filter by source types")
    subtype_filter: Optional[List[str]] = Field(None, description="Filter by subtypes")
    tags: Optional[List[str]] = Field(None, description="Filter by tags (all must match)")
    start_time: Optional[str] = Field(None, description="Start of time range (ISO8601)")
    end_time: Optional[str] = Field(None, description="End of time range (ISO8601)")
    limit: int = Field(50, description="Maximum results to return", ge=1, le=1000)
    mode: Optional[str] = Field(None, description="Special mode: 'intruder_stats'")
    days: Optional[int] = Field(30, description="Days for stats calculation")


class IntruderStats(BaseModel):
    """Statistics about intruder detections."""
    total_intruders: int
    by_camera: Dict[str, int]
    by_hour: Dict[str, int]
    last_seen: Optional[str]
