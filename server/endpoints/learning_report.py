"""
Learning Report endpoint for the Hobbs Agent.

Provides access to learning insights, baselines, and recommendations.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter

from schemas.shared import TaskEnvelope
from config.settings import log_event
from server.learning.learning_engine import learning_engine
from server.learning.rule_refinement import rule_refinement


router = APIRouter()


@router.get("/learning_report")
async def get_learning_report() -> dict:
    """
    Get the current learning report.

    Returns cached learning data and recent recommendations.

    Returns:
        {
            "ok": true,
            "learning": {...},
            "recommendations": [...]
        }
    """
    log_event("learning_report", {"action": "get_report"})

    # Load cached learning data
    learning_data = learning_engine.load_cache()

    # Load recent recommendations
    recommendations = rule_refinement.load_recommendations(limit=5)

    # Flatten recommendations to just the suggestions
    all_suggestions = []
    for rec in recommendations:
        all_suggestions.extend(rec.get("suggestions", []))

    return {
        "ok": True,
        "learning": learning_data,
        "recommendations": all_suggestions[-10:],  # Last 10 suggestions
        "recommendations_count": len(all_suggestions),
    }


@router.post("/learning_report")
async def post_learning_report(task: TaskEnvelope) -> dict:
    """
    Request a learning report or trigger a learning cycle.

    Payload options:
        - action: "get" (default) - Return cached report
        - action: "refresh" - Run new learning cycle and return results

    Args:
        task: TaskEnvelope with optional action in payload

    Returns:
        Learning report with baselines and recommendations
    """
    log_event("learning_report", task.model_dump())

    action = task.payload.get("action", "get")

    if action == "refresh":
        # Run full learning cycle
        result = learning_engine.run_full_learning_cycle()
        return {
            "ok": True,
            "action": "refresh",
            "learning": result.get("learning", {}),
            "recommendations": result.get("recommendations", []),
        }

    # Default: get cached report
    learning_data = learning_engine.load_cache()
    recommendations = rule_refinement.load_recommendations(limit=5)

    all_suggestions = []
    for rec in recommendations:
        all_suggestions.extend(rec.get("suggestions", []))

    return {
        "ok": True,
        "action": "get",
        "learning": learning_data,
        "recommendations": all_suggestions[-10:],
    }
