"""
Classifier stub for the Hobbs Agent.

This is a placeholder for future YOLOv8 integration.
Currently returns stubbed classification results based on filename patterns.
"""

from pathlib import Path
from typing import Dict, Any

from config.settings import logger


# Valid object types
OBJECT_TYPES = ["human", "animal", "vehicle", "unknown"]


def classify(image_path: str) -> Dict[str, Any]:
    """
    Classify an object in an image (STUB).

    This is a placeholder for future ML model integration.
    Currently uses filename patterns to determine classification:
    - If filename contains "test_human" → returns "human"
    - If filename contains "test_animal" → returns "animal"
    - If filename contains "test_vehicle" → returns "vehicle"
    - Otherwise → returns "unknown"

    Args:
        image_path: Path to the image file

    Returns:
        Dict with:
            - object: str ("human", "animal", "vehicle", or "unknown")
            - confidence: float (0.0-1.0)
    """
    logger.info(f"Classifying image (stub): {image_path}")

    path = Path(image_path)
    filename = path.stem.lower()

    # Check filename for test patterns
    if "test_human" in filename:
        result = {
            "object": "human",
            "confidence": 0.85,
        }
    elif "test_animal" in filename:
        result = {
            "object": "animal",
            "confidence": 0.80,
        }
    elif "test_vehicle" in filename:
        result = {
            "object": "vehicle",
            "confidence": 0.82,
        }
    else:
        # Default unknown classification
        result = {
            "object": "unknown",
            "confidence": 0.15,
        }

    logger.info(f"Classification result (stub): {result}")
    return result


def get_supported_objects() -> list:
    """
    Get list of supported object types.

    Returns:
        List of object type strings
    """
    return OBJECT_TYPES.copy()
