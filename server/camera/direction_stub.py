"""
Direction estimation stub for the Hobbs Agent.

This is a placeholder for future geometric direction inference.
Currently returns stubbed direction estimation results.
"""

from typing import Dict, Any

from config.settings import logger


# Valid direction types
DIRECTION_TYPES = ["toward_house", "away_from_house", "indeterminate"]


def estimate_direction(camera_id: str) -> Dict[str, Any]:
    """
    Estimate the direction of movement (STUB).

    This is scaffolding for later geometric direction inference.
    Currently always returns "indeterminate" with low confidence.

    In future phases, this will:
    - Use camera position metadata
    - Analyze motion vectors
    - Calculate relative direction to house/barn

    Args:
        camera_id: The camera identifier

    Returns:
        Dict with:
            - direction: str ("toward_house", "away_from_house", or "indeterminate")
            - confidence: float (0.0-1.0)
    """
    logger.info(f"Estimating direction for camera (stub): {camera_id}")

    # Always return indeterminate with low confidence
    # This is placeholder logic for future implementation
    result = {
        "direction": "indeterminate",
        "confidence": 0.10,
    }

    logger.info(f"Direction result (stub): {result}")
    return result


def get_supported_directions() -> list:
    """
    Get list of supported direction types.

    Returns:
        List of direction type strings
    """
    return DIRECTION_TYPES.copy()
