"""
Memory Query endpoint for the Hobbs Agent.

Provides HTTP API for Sky/Congress to query long-term memory,
search events, and get pattern statistics.
"""

from typing import Any, Dict, List

from fastapi import APIRouter

from schemas.shared import TaskEnvelope
from schemas.memory import MemoryQueryPayload, MemoryEvent
from config.settings import log_event
from server.memory.query_engine import query_engine


router = APIRouter()


def parse_query_payload(payload: Dict[str, Any]) -> MemoryQueryPayload:
    """
    Parse and validate query payload.

    Args:
        payload: Raw payload dictionary

    Returns:
        Validated MemoryQueryPayload
    """
    return MemoryQueryPayload(**payload)


@router.post("/memory_query")
async def memory_query(task: TaskEnvelope) -> dict:
    """
    Query the long-term memory.

    Accepts a TaskEnvelope with query parameters and returns
    matching memory events or statistics.

    Args:
        task: TaskEnvelope with query payload

    Payload fields:
        - query: str (optional) - Text search in summary
        - source_filter: list[str] (optional) - Filter by sources
        - subtype_filter: list[str] (optional) - Filter by subtypes
        - tags: list[str] (optional) - Filter by tags (all must match)
        - start_time: str (optional) - Start of time range
        - end_time: str (optional) - End of time range
        - limit: int (default 50) - Maximum results
        - mode: str (optional) - "intruder_stats" for statistics mode
        - days: int (default 30) - Days for stats calculation

    Returns:
        For normal queries:
        {
            "ok": true,
            "results": [MemoryEvent, ...]
        }

        For mode="intruder_stats":
        {
            "ok": true,
            "stats": {
                "total_intruders": int,
                "by_camera": {...},
                "by_hour": {...},
                "last_seen": str or null
            }
        }
    """
    # Log the incoming request
    log_event("memory_query", task.model_dump())

    # Parse query payload
    query_params = parse_query_payload(task.payload)

    # Check for special modes
    if query_params.mode == "intruder_stats":
        days = query_params.days or 30
        stats = query_engine.get_intruder_stats(days=days)
        return {
            "ok": True,
            "stats": stats.model_dump(),
        }

    # Normal search query
    results = query_engine.search_memory(
        text_query=query_params.query,
        source_filter=query_params.source_filter,
        subtype_filter=query_params.subtype_filter,
        start_time=query_params.start_time,
        end_time=query_params.end_time,
        tag_filter=query_params.tags,
        limit=query_params.limit,
    )

    return {
        "ok": True,
        "results": [event.model_dump() for event in results],
        "count": len(results),
    }
