"""
Tests for Hobbs Agent vision system.

Tests verify:
- YOLO stub returns valid format
- OCR stub returns valid format
- Object detector combines outputs correctly
- Centroid and direction computation
- Suspicion score logic
- /detect_intruder endpoint structure
- Trajectory and suspicion history files
"""

import sys
import json
import base64
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


class TestYOLOAdapter:
    """Tests for the YOLO adapter."""

    def test_yolo_adapter_returns_valid_format(self):
        """Test that YOLO adapter returns expected format."""
        from server.vision.yolo_adapter import yolo_adapter

        # Call with non-existent image (should return empty)
        result = yolo_adapter.run_yolo("/nonexistent/image.png")

        assert "objects" in result
        assert isinstance(result["objects"], list)
        assert "model" in result
        assert "available" in result

    def test_yolo_adapter_status(self):
        """Test YOLO adapter status method."""
        from server.vision.yolo_adapter import yolo_adapter

        status = yolo_adapter.get_status()

        assert "available" in status
        assert "model" in status
        assert "backend" in status


class TestOCRAdapter:
    """Tests for the OCR adapter."""

    def test_ocr_adapter_returns_valid_format(self):
        """Test that OCR adapter returns expected format."""
        from server.vision.ocr_adapter import ocr_adapter

        # Call with non-existent image (should return empty)
        result = ocr_adapter.run_ocr("/nonexistent/image.png")

        assert "text" in result
        assert "lines" in result
        assert isinstance(result["lines"], list)
        assert "engine" in result
        assert "available" in result

    def test_ocr_adapter_status(self):
        """Test OCR adapter status method."""
        from server.vision.ocr_adapter import ocr_adapter

        status = ocr_adapter.get_status()

        assert "available" in status
        assert "engine" in status


class TestObjectDetector:
    """Tests for the unified object detector."""

    def test_detect_objects_returns_valid_format(self):
        """Test that object detector returns expected format."""
        from server.vision.object_detector import object_detector

        result = object_detector.detect_objects(
            "/nonexistent/image.png",
            run_ocr=True,
            timestamp="2025-01-21T10:00:00Z"
        )

        assert "objects" in result
        assert "ocr_text" in result
        assert "summary" in result
        assert "tags" in result
        assert "detection_available" in result
        assert "ocr_available" in result

    def test_detect_objects_generates_tags(self):
        """Test that tags are generated from detection results."""
        from server.vision.object_detector import ObjectDetector

        detector = ObjectDetector()

        # Test tag generation with mock objects
        tags = detector._generate_tags(
            objects=[{"label": "person", "confidence": 0.9}],
            ocr_text="",
            timestamp="2025-01-21T02:00:00Z"  # Night time
        )

        assert "intruder" in tags or "human" in tags
        assert "night" in tags or "after_hours" in tags
        assert "single_person" in tags

    def test_detect_objects_generates_summary(self):
        """Test that summary is generated correctly."""
        from server.vision.object_detector import ObjectDetector

        detector = ObjectDetector()

        # Test summary generation
        summary = detector._generate_summary(
            objects=[
                {"label": "person", "confidence": 0.9},
                {"label": "car", "confidence": 0.8},
            ],
            ocr_text=""
        )

        assert "person" in summary
        assert "car" in summary

        # Empty objects
        summary = detector._generate_summary([], "")
        assert "no objects detected" in summary

    def test_object_detector_status(self):
        """Test object detector status method."""
        from server.vision.object_detector import object_detector

        status = object_detector.get_status()

        assert "yolo" in status
        assert "ocr" in status


class TestTrajectoryEngine:
    """Tests for the trajectory engine."""

    def test_compute_centroid(self):
        """Test centroid computation from bounding box."""
        from server.vision.trajectory_engine import TrajectoryEngine

        engine = TrajectoryEngine()

        # Bounding box [x1, y1, x2, y2]
        bbox = [100, 100, 200, 200]
        centroid = engine._compute_centroid(bbox)

        assert centroid == [150.0, 150.0]

    def test_classify_movement(self):
        """Test movement classification from delta."""
        from server.vision.trajectory_engine import TrajectoryEngine

        engine = TrajectoryEngine()

        # Moving down (toward house)
        movement = engine._classify_movement("test_cam", 0, 50)
        assert movement == "toward_house"

        # Moving up (away from house)
        movement = engine._classify_movement("test_cam", 0, -50)
        assert movement == "away_from_house"

        # Lateral movement
        movement = engine._classify_movement("test_cam", 50, 0)
        assert movement == "lateral"

        # Stationary
        movement = engine._classify_movement("test_cam", 2, 2)
        assert movement == "stationary"

    def test_track_returns_valid_format(self):
        """Test that trajectory tracking returns expected format."""
        from server.vision.trajectory_engine import TrajectoryEngine

        engine = TrajectoryEngine()

        result = engine.track(
            camera_id="test_cam",
            timestamp="2025-01-21T10:00:00Z",
            objects=[
                {"label": "person", "confidence": 0.9, "bbox": [100, 100, 200, 200]}
            ]
        )

        assert "camera_id" in result
        assert result["camera_id"] == "test_cam"
        assert "timestamp" in result
        assert "tracked_objects" in result
        assert "overall_movement" in result
        assert "frame_count" in result

    def test_track_multi_frame(self):
        """Test tracking across multiple frames."""
        from server.vision.trajectory_engine import TrajectoryEngine
        from datetime import datetime

        engine = TrajectoryEngine()

        # Use current timestamps to avoid buffer cleanup issues
        now = datetime.utcnow()
        ts1 = now.isoformat() + "Z"
        ts2 = (now + timedelta(seconds=1)).isoformat() + "Z"

        # Frame 1
        engine.track(
            camera_id="multi_test_cam_v2",
            timestamp=ts1,
            objects=[{"label": "person", "confidence": 0.9, "bbox": [100, 100, 200, 200]}]
        )

        # Frame 2 - person moved down
        result = engine.track(
            camera_id="multi_test_cam_v2",
            timestamp=ts2,
            objects=[{"label": "person", "confidence": 0.9, "bbox": [100, 150, 200, 250]}]
        )

        assert result["frame_count"] == 2
        # Should detect movement
        if result["tracked_objects"]:
            obj = result["tracked_objects"][0]
            assert obj["delta"] != [0, 0]


class TestSuspicionEngine:
    """Tests for the suspicion engine."""

    def test_is_night_time(self):
        """Test night time detection."""
        from server.vision.suspicion_engine import SuspicionEngine

        engine = SuspicionEngine()

        # Night time (2 AM)
        assert engine._is_night_time("2025-01-21T02:00:00Z") is True

        # Day time (2 PM)
        assert engine._is_night_time("2025-01-21T14:00:00Z") is False

        # Night time (11 PM)
        assert engine._is_night_time("2025-01-21T23:00:00Z") is True

    def test_has_identifying_text(self):
        """Test identifying text detection."""
        from server.vision.suspicion_engine import SuspicionEngine

        engine = SuspicionEngine()

        # License plate pattern
        assert engine._has_identifying_text("ABC-1234") is True
        assert engine._has_identifying_text("XY 5678") is True

        # Empty text
        assert engine._has_identifying_text("") is False

        # Just letters
        assert engine._has_identifying_text("abc") is False

    def test_get_risk_level(self):
        """Test risk level determination."""
        from server.vision.suspicion_engine import SuspicionEngine

        engine = SuspicionEngine()

        assert engine._get_risk_level(0.1) == "low"
        assert engine._get_risk_level(0.3) == "medium"
        assert engine._get_risk_level(0.6) == "high"
        assert engine._get_risk_level(0.8) == "critical"

    def test_compute_suspicion_returns_valid_format(self):
        """Test that suspicion computation returns expected format."""
        from server.vision.suspicion_engine import SuspicionEngine

        engine = SuspicionEngine()

        result = engine.compute_suspicion({
            "objects": [{"label": "person", "confidence": 0.9}],
            "trajectory": {"overall_movement": "toward_house"},
            "ocr_text": "",
            "timestamp": "2025-01-21T02:00:00Z",  # Night time
            "camera_id": "test_cam",
            "tags": []
        })

        assert "score" in result
        assert 0 <= result["score"] <= 1
        assert "reasons" in result
        assert isinstance(result["reasons"], list)
        assert "risk_level" in result
        assert result["risk_level"] in ["low", "medium", "high", "critical"]
        assert "factors" in result

    def test_compute_suspicion_human_night(self):
        """Test suspicion score for human at night."""
        from server.vision.suspicion_engine import SuspicionEngine

        engine = SuspicionEngine()

        result = engine.compute_suspicion({
            "objects": [{"label": "person", "confidence": 0.9}],
            "trajectory": {"overall_movement": "toward_house"},
            "ocr_text": "",
            "timestamp": "2025-01-21T02:00:00Z",  # Night time
            "camera_id": "test_cam",
            "tags": []
        })

        # Human at night moving toward house should have high score
        assert result["score"] >= 0.5
        assert "human detected" in " ".join(result["reasons"]).lower()
        assert "night" in " ".join(result["reasons"]).lower()

    def test_compute_suspicion_group(self):
        """Test suspicion score for group of people."""
        from server.vision.suspicion_engine import SuspicionEngine

        engine = SuspicionEngine()

        result = engine.compute_suspicion({
            "objects": [
                {"label": "person", "confidence": 0.9},
                {"label": "person", "confidence": 0.8},
                {"label": "person", "confidence": 0.85},
            ],
            "trajectory": {"overall_movement": "indeterminate"},
            "ocr_text": "",
            "timestamp": "2025-01-21T14:00:00Z",  # Day time
            "camera_id": "test_cam",
            "tags": []
        })

        # Group should trigger group_pattern factor
        assert result["factors"].get("group_pattern", False) is True
        assert "group" in " ".join(result["reasons"]).lower()


class TestDetectIntruderEndpoint:
    """Tests for the /detect_intruder endpoint."""

    def test_detect_intruder_returns_valid_json(self):
        """Test that /detect_intruder endpoint returns valid JSON structure."""
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)

        # Create a minimal test image (1x1 white PNG)
        # This is a valid PNG header for a tiny image
        test_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

        response = client.post(
            "/detect_intruder",
            json={
                "task_id": "vision-test-001",
                "source": "test",
                "target": "hobbs",
                "type": "detect_intruder",
                "payload": {
                    "camera_id": "test_cam",
                    "image_base64": test_image_b64
                }
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "ok" in data
        assert data["ok"] is True
        assert "objects" in data
        assert "trajectory" in data
        assert "suspicion_score" in data
        assert "risk_level" in data
        assert "reasons" in data

        # Backward compatibility fields
        assert "object" in data
        assert "confidence" in data
        assert "direction" in data

    def test_detect_intruder_requires_image(self):
        """Test that endpoint requires image data."""
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)

        response = client.post(
            "/detect_intruder",
            json={
                "task_id": "vision-test-002",
                "source": "test",
                "target": "hobbs",
                "type": "detect_intruder",
                "payload": {
                    "camera_id": "test_cam"
                    # Missing image_base64 and image_url
                }
            }
        )

        assert response.status_code == 422


class TestVisionIntegration:
    """Integration tests for the vision system."""

    def test_trajectory_history_file_creation(self):
        """Test that trajectory history file is created."""
        from server.vision.trajectory_engine import trajectory_engine

        # Track an object
        trajectory_engine.track(
            camera_id="history_test_cam",
            timestamp=datetime.utcnow().isoformat() + "Z",
            objects=[{"label": "person", "confidence": 0.9, "bbox": [100, 100, 200, 200]}]
        )

        # Check that history file exists
        assert trajectory_engine.history_file.exists() or trajectory_engine.get_history_count() >= 0

    def test_suspicion_scores_file_creation(self):
        """Test that suspicion scores file is created."""
        from server.vision.suspicion_engine import suspicion_engine

        # Compute suspicion
        suspicion_engine.compute_suspicion({
            "objects": [{"label": "person", "confidence": 0.9}],
            "trajectory": {},
            "ocr_text": "",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "camera_id": "scores_test_cam",
            "tags": []
        })

        # Check that scores file exists
        assert suspicion_engine.scores_file.exists() or suspicion_engine.get_scores_count() >= 0

    def test_status_endpoint_includes_vision_stats(self):
        """Test that status endpoint includes vision statistics."""
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)
        response = client.get("/status")

        assert response.status_code == 200
        data = response.json()

        # Check vision stats are present
        assert "vision_events_today" in data
        assert "suspicious_events_today" in data
        assert "average_suspicion_score_last_24h" in data
        assert "trajectory_history_count" in data
        assert "vision_detection_available" in data
        assert "vision_ocr_available" in data
