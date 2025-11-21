"""
Tests for Hobbs Agent intruder detection functionality.

Tests verify:
- /detect_intruder accepts base64 input
- Image saved correctly
- Index entry created
- Stub classifier returns expected structure
- Correct JSON response
"""

import sys
import json
import base64
import shutil
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from app import app
from server.utils.image_ops import get_cameras_dir, get_camera_index_path
from server.utils.time_ops import today_str
from server.camera.classifier_stub import classify, get_supported_objects
from server.camera.direction_stub import estimate_direction, get_supported_directions


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_image_base64():
    """Create a minimal valid PNG image as base64."""
    # Minimal 1x1 white PNG image
    png_bytes = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,  # 8-bit RGB
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT chunk
        0x54, 0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0xFF,
        0x00, 0x05, 0xFE, 0x02, 0xFE, 0xDC, 0xCC, 0x59,
        0xE7, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,  # IEND chunk
        0x44, 0xAE, 0x42, 0x60, 0x82
    ])
    return base64.b64encode(png_bytes).decode("utf-8")


@pytest.fixture
def valid_intruder_envelope(sample_image_base64):
    """Create a valid TaskEnvelope for intruder detection."""
    return {
        "task_id": "test-intruder-001",
        "source": "test-source",
        "target": "hobbs",
        "type": "intruder",
        "payload": {
            "camera_id": "test_cam",
            "image_base64": sample_image_base64,
            "metadata": {"test": True}
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@pytest.fixture
def intruder_envelope_human(sample_image_base64):
    """Create an envelope that triggers human classification."""
    return {
        "task_id": "test-intruder-human",
        "source": "test-source",
        "target": "hobbs",
        "type": "intruder",
        "payload": {
            "camera_id": "test_human_cam",
            "image_base64": sample_image_base64,
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@pytest.fixture
def invalid_intruder_payload_envelope():
    """Create an envelope with invalid intruder payload (missing image)."""
    return {
        "task_id": "test-intruder-invalid",
        "source": "test-source",
        "target": "hobbs",
        "type": "intruder",
        "payload": {
            "camera_id": "test_cam"
            # Missing image_base64 and image_url
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@pytest.fixture
def cleanup_camera_data():
    """Fixture to clean up test camera data after tests."""
    yield
    # Cleanup: Remove test camera folders
    cameras_dir = get_cameras_dir()
    for test_folder in ["test_cam", "test_human_cam"]:
        folder = cameras_dir / test_folder
        if folder.exists():
            shutil.rmtree(folder)

    # Clear the camera index file
    index_path = get_camera_index_path()
    if index_path.exists():
        index_path.write_text("")


class TestClassifierStub:
    """Tests for the classifier stub."""

    def test_classify_returns_expected_structure(self):
        """Test that classify returns expected dict structure."""
        result = classify("/fake/path/image.png")

        assert "object" in result
        assert "confidence" in result
        assert isinstance(result["object"], str)
        assert isinstance(result["confidence"], float)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_classify_unknown_default(self):
        """Test that classify returns 'unknown' for regular files."""
        result = classify("/fake/path/regular_image.png")

        assert result["object"] == "unknown"
        assert result["confidence"] == 0.15

    def test_classify_human_pattern(self):
        """Test that classify detects 'test_human' pattern."""
        result = classify("/fake/path/test_human_image.png")

        assert result["object"] == "human"
        assert result["confidence"] == 0.85

    def test_classify_animal_pattern(self):
        """Test that classify detects 'test_animal' pattern."""
        result = classify("/fake/path/test_animal_image.png")

        assert result["object"] == "animal"
        assert result["confidence"] == 0.80

    def test_classify_vehicle_pattern(self):
        """Test that classify detects 'test_vehicle' pattern."""
        result = classify("/fake/path/test_vehicle_image.png")

        assert result["object"] == "vehicle"
        assert result["confidence"] == 0.82

    def test_get_supported_objects(self):
        """Test that get_supported_objects returns expected list."""
        objects = get_supported_objects()

        assert "human" in objects
        assert "animal" in objects
        assert "vehicle" in objects
        assert "unknown" in objects


class TestDirectionStub:
    """Tests for the direction stub."""

    def test_estimate_direction_returns_expected_structure(self):
        """Test that estimate_direction returns expected dict structure."""
        result = estimate_direction("any_camera")

        assert "direction" in result
        assert "confidence" in result
        assert isinstance(result["direction"], str)
        assert isinstance(result["confidence"], float)

    def test_estimate_direction_returns_indeterminate(self):
        """Test that estimate_direction always returns indeterminate (stub)."""
        result = estimate_direction("any_camera")

        assert result["direction"] == "indeterminate"
        assert result["confidence"] == 0.10

    def test_get_supported_directions(self):
        """Test that get_supported_directions returns expected list."""
        directions = get_supported_directions()

        assert "toward_house" in directions
        assert "away_from_house" in directions
        assert "indeterminate" in directions


class TestDetectIntruderEndpoint:
    """Tests for the /detect_intruder endpoint."""

    def test_detect_intruder_returns_200(
        self, client, valid_intruder_envelope, cleanup_camera_data
    ):
        """Test that /detect_intruder returns 200 OK with valid input."""
        response = client.post("/detect_intruder", json=valid_intruder_envelope)
        assert response.status_code == 200

    def test_detect_intruder_returns_expected_keys(
        self, client, valid_intruder_envelope, cleanup_camera_data
    ):
        """Test that /detect_intruder returns expected response keys."""
        response = client.post("/detect_intruder", json=valid_intruder_envelope)
        data = response.json()

        assert "ok" in data
        assert "object" in data
        assert "confidence" in data
        assert "direction" in data
        assert "dir_confidence" in data
        assert data["ok"] is True

    def test_detect_intruder_saves_image(
        self, client, valid_intruder_envelope, cleanup_camera_data
    ):
        """Test that /detect_intruder saves image to camera folder."""
        response = client.post("/detect_intruder", json=valid_intruder_envelope)
        assert response.status_code == 200

        # Check that image was saved
        camera_folder = get_cameras_dir() / "test_cam"
        assert camera_folder.exists()

        png_files = list(camera_folder.glob("*.png"))
        assert len(png_files) >= 1

    def test_detect_intruder_creates_index_entry(
        self, client, valid_intruder_envelope, cleanup_camera_data
    ):
        """Test that /detect_intruder creates an index entry."""
        # Clear index first
        index_path = get_camera_index_path()
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text("")

        response = client.post("/detect_intruder", json=valid_intruder_envelope)
        assert response.status_code == 200

        # Check index was updated
        with open(index_path, "r") as f:
            lines = [line.strip() for line in f if line.strip()]

        assert len(lines) >= 1

        entry = json.loads(lines[-1])
        assert "timestamp" in entry
        assert "camera_id" in entry
        assert "object" in entry
        assert "obj_conf" in entry
        assert "direction" in entry
        assert "dir_conf" in entry
        assert "image_path" in entry

    def test_detect_intruder_invalid_payload_returns_422(
        self, client, invalid_intruder_payload_envelope
    ):
        """Test that /detect_intruder returns 422 with invalid payload."""
        response = client.post("/detect_intruder", json=invalid_intruder_payload_envelope)
        assert response.status_code == 422

    def test_detect_intruder_missing_envelope_fields_returns_422(self, client):
        """Test that /detect_intruder returns 422 when TaskEnvelope fields missing."""
        invalid_envelope = {
            "task_id": "test-001"
            # Missing required fields
        }
        response = client.post("/detect_intruder", json=invalid_envelope)
        assert response.status_code == 422


class TestStatusWithCameraStats:
    """Tests for /status endpoint with camera statistics."""

    def test_status_includes_camera_stats(self, client):
        """Test that /status includes camera event statistics."""
        response = client.get("/status")
        assert response.status_code == 200

        data = response.json()
        assert "camera_events_today" in data
        assert "camera_index_size" in data
        assert isinstance(data["camera_events_today"], int)
        assert isinstance(data["camera_index_size"], int)
