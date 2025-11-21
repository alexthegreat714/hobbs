"""
YOLO Adapter for Hobbs Agent Vision System.

Provides object detection using YOLO models with graceful fallback
when models are not available.
"""

import json
from typing import Any, Dict, List, Optional
from pathlib import Path

from config.settings import logger


# Try to import ultralytics YOLO
YOLO_AVAILABLE = False
YOLO_MODEL = None

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
    logger.info("YOLO (ultralytics) is available")
except ImportError:
    logger.warning("ultralytics not installed - YOLO detection will return empty results")


class YOLOAdapter:
    """
    YOLO object detection adapter.

    Supports:
    A) Local Python YOLO (ultralytics)
    B) Fallback mode returning empty results when not available
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the YOLO adapter.

        Args:
            model_path: Path to YOLO model weights (default: yolov8n.pt)
        """
        self.model = None
        self.model_path = model_path or "yolov8n.pt"
        self.available = False

        if YOLO_AVAILABLE:
            try:
                self.model = YOLO(self.model_path)
                self.available = True
                logger.info(f"YOLO model loaded: {self.model_path}")
            except Exception as e:
                logger.warning(f"Failed to load YOLO model: {e}")
                self.available = False

    def run_yolo(self, image_path: str) -> Dict[str, Any]:
        """
        Run YOLO object detection on an image.

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary with detected objects:
            {
                "objects": [
                    {
                        "label": "person",
                        "confidence": 0.92,
                        "bbox": [x1, y1, x2, y2]
                    },
                    ...
                ],
                "model": "yolov8n" or "none",
                "available": bool
            }
        """
        result = {
            "objects": [],
            "model": "none",
            "available": self.available
        }

        if not self.available or self.model is None:
            logger.debug("YOLO not available, returning empty objects list")
            return result

        try:
            # Verify image exists
            if not Path(image_path).exists():
                logger.warning(f"Image not found: {image_path}")
                return result

            # Run inference
            results = self.model(image_path, verbose=False)

            result["model"] = self.model_path

            # Parse results
            for r in results:
                boxes = r.boxes
                if boxes is not None:
                    for box in boxes:
                        # Get bounding box coordinates
                        xyxy = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                        conf = float(box.conf[0])
                        cls = int(box.cls[0])
                        label = r.names[cls]

                        result["objects"].append({
                            "label": label,
                            "confidence": round(conf, 3),
                            "bbox": [round(c, 2) for c in xyxy]
                        })

            logger.info(f"YOLO detected {len(result['objects'])} objects in {image_path}")

        except Exception as e:
            logger.error(f"YOLO inference failed: {e}")

        return result

    def get_status(self) -> Dict[str, Any]:
        """Get adapter status."""
        return {
            "available": self.available,
            "model": self.model_path if self.available else None,
            "backend": "ultralytics" if YOLO_AVAILABLE else None
        }


# Singleton instance
yolo_adapter = YOLOAdapter()
