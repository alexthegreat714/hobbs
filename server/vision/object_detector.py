"""
Object Detector for Hobbs Agent Vision System.

Combines YOLO object detection and OCR into a unified detection output
with semantic tagging and summarization.
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime

from config.settings import logger
from server.vision.yolo_adapter import yolo_adapter
from server.vision.ocr_adapter import ocr_adapter


# Object label to tag mappings
LABEL_TO_TAGS = {
    # People
    "person": ["intruder", "human"],
    "man": ["intruder", "human"],
    "woman": ["intruder", "human"],
    "child": ["intruder", "human"],

    # Vehicles
    "car": ["vehicle", "automobile"],
    "truck": ["vehicle", "large_vehicle"],
    "bus": ["vehicle", "large_vehicle"],
    "motorcycle": ["vehicle", "two_wheeler"],
    "bicycle": ["vehicle", "two_wheeler"],

    # Animals
    "dog": ["animal", "pet"],
    "cat": ["animal", "pet"],
    "bird": ["animal", "wildlife"],
    "horse": ["animal", "livestock"],
    "cow": ["animal", "livestock"],
    "sheep": ["animal", "livestock"],
    "bear": ["animal", "wildlife", "dangerous"],
    "deer": ["animal", "wildlife"],

    # Default
    "default": ["unknown_object"]
}


class ObjectDetector:
    """
    Unified object detector combining YOLO and OCR.

    Provides:
    - Object detection with bounding boxes
    - Text extraction via OCR
    - Semantic tagging
    - Summary generation
    """

    def __init__(self):
        """Initialize the object detector."""
        self.yolo = yolo_adapter
        self.ocr = ocr_adapter

    def detect_objects(
        self,
        image_path: str,
        run_ocr: bool = True,
        timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run full object detection pipeline on an image.

        Args:
            image_path: Path to the image file
            run_ocr: Whether to run OCR (default True)
            timestamp: Optional timestamp for time-based tagging

        Returns:
            Unified detection result:
            {
                "objects": [...],
                "ocr_text": "...",
                "summary": "person near woods",
                "tags": ["intruder", "night", "vehicle"],
                "detection_available": bool,
                "ocr_available": bool
            }
        """
        result = {
            "objects": [],
            "ocr_text": "",
            "ocr_lines": [],
            "summary": "no objects detected",
            "tags": [],
            "detection_available": self.yolo.available,
            "ocr_available": self.ocr.available,
            "timestamp": timestamp or datetime.utcnow().isoformat() + "Z"
        }

        # Run YOLO detection
        yolo_result = self.yolo.run_yolo(image_path)
        result["objects"] = yolo_result.get("objects", [])
        result["detection_available"] = yolo_result.get("available", False)

        # Run OCR if requested
        if run_ocr:
            ocr_result = self.ocr.run_ocr(image_path)
            result["ocr_text"] = ocr_result.get("text", "")
            result["ocr_lines"] = ocr_result.get("lines", [])
            result["ocr_available"] = ocr_result.get("available", False)

        # Generate tags from detected objects
        result["tags"] = self._generate_tags(
            result["objects"],
            result["ocr_text"],
            timestamp
        )

        # Generate summary
        result["summary"] = self._generate_summary(
            result["objects"],
            result["ocr_text"]
        )

        return result

    def _generate_tags(
        self,
        objects: List[Dict],
        ocr_text: str,
        timestamp: Optional[str]
    ) -> List[str]:
        """
        Generate semantic tags from detection results.

        Args:
            objects: List of detected objects
            ocr_text: Extracted OCR text
            timestamp: Detection timestamp

        Returns:
            List of unique tags
        """
        tags = set()

        # Tags from detected objects
        for obj in objects:
            label = obj.get("label", "").lower()
            label_tags = LABEL_TO_TAGS.get(label, LABEL_TO_TAGS["default"])
            tags.update(label_tags)

        # Time-based tags
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                hour = dt.hour
                if 22 <= hour or hour < 5:
                    tags.add("night")
                    tags.add("after_hours")
                elif 5 <= hour < 7:
                    tags.add("early_morning")
                elif 18 <= hour < 22:
                    tags.add("evening")
                else:
                    tags.add("daytime")
            except Exception:
                pass

        # OCR-based tags
        if ocr_text:
            text_lower = ocr_text.lower()
            # Check for license plate patterns
            if any(c.isdigit() for c in ocr_text) and len(ocr_text) >= 3:
                tags.add("has_text")
                # Simple license plate heuristic
                import re
                if re.search(r'[A-Z0-9]{2,3}[\s-]?[A-Z0-9]{2,4}', ocr_text.upper()):
                    tags.add("possible_license_plate")

        # Count-based tags
        person_count = sum(1 for o in objects if o.get("label") == "person")
        if person_count > 1:
            tags.add("multiple_people")
            tags.add("group")
        if person_count == 1:
            tags.add("single_person")

        vehicle_count = sum(1 for o in objects if o.get("label") in ["car", "truck", "bus", "motorcycle"])
        if vehicle_count > 0:
            tags.add("has_vehicle")

        return sorted(list(tags))

    def _generate_summary(
        self,
        objects: List[Dict],
        ocr_text: str
    ) -> str:
        """
        Generate a human-readable summary of detection results.

        Args:
            objects: List of detected objects
            ocr_text: Extracted OCR text

        Returns:
            Summary string
        """
        if not objects:
            return "no objects detected"

        # Count objects by type
        counts = {}
        for obj in objects:
            label = obj.get("label", "object")
            counts[label] = counts.get(label, 0) + 1

        # Build summary parts
        parts = []
        for label, count in sorted(counts.items(), key=lambda x: -x[1]):
            if count == 1:
                parts.append(label)
            else:
                parts.append(f"{count} {label}s")

        summary = ", ".join(parts[:3])  # Limit to top 3

        # Add OCR info if present
        if ocr_text and len(ocr_text) <= 50:
            summary += f" (text: '{ocr_text[:30]}')"
        elif ocr_text:
            summary += " (text detected)"

        return summary

    def get_status(self) -> Dict[str, Any]:
        """Get detector status."""
        return {
            "yolo": self.yolo.get_status(),
            "ocr": self.ocr.get_status()
        }


# Singleton instance
object_detector = ObjectDetector()
