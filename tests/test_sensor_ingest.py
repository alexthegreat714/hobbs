"""
Tests for Hobbs Agent sensor ingest functionality.

Tests verify:
- Valid sensor ingest creates JSON file
- Index entry is appended
- Correct HTTP 200 response
- Invalid payloads return appropriate errors
"""

import sys
import json
import shutil
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from app import app
from server.utils.file_ops import get_sensors_dir, get_sensor_index_path
from server.utils.time_ops import today_str


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def valid_sensor_envelope():
    """Create a valid TaskEnvelope with sensor payload."""
    return {
        "task_id": "test-sensor-001",
        "source": "test-source",
        "target": "hobbs",
        "type": "sensor",
        "payload": {
            "sensor_type": "moisture",
            "value": 0.18,
            "unit": "fraction",
            "metadata": {"location": "field-1"}
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@pytest.fixture
def valid_sensor_envelope_dict_value():
    """Create a valid TaskEnvelope with dict value in sensor payload."""
    return {
        "task_id": "test-sensor-002",
        "source": "test-source",
        "target": "hobbs",
        "type": "sensor",
        "payload": {
            "sensor_type": "gps",
            "value": {"lat": 40.7128, "lng": -74.0060},
            "unit": None,
            "metadata": {}
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@pytest.fixture
def invalid_sensor_payload_envelope():
    """Create a TaskEnvelope with invalid sensor payload (missing required fields)."""
    return {
        "task_id": "test-sensor-003",
        "source": "test-source",
        "target": "hobbs",
        "type": "sensor",
        "payload": {
            "sensor_type": "temperature"
            # Missing 'value' field
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@pytest.fixture
def cleanup_test_data():
    """Fixture to clean up test data after tests."""
    yield
    # Cleanup: Remove today's sensor folder if it exists
    today_folder = get_sensors_dir() / today_str()
    if today_folder.exists():
        shutil.rmtree(today_folder)

    # Clear the sensor index file
    index_path = get_sensor_index_path()
    if index_path.exists():
        index_path.write_text("")


class TestSensorIngestEndpoint:
    """Tests for the /sensor_ingest endpoint."""

    def test_sensor_ingest_returns_200(self, client, valid_sensor_envelope, cleanup_test_data):
        """Test that /sensor_ingest returns 200 OK with valid input."""
        response = client.post("/sensor_ingest", json=valid_sensor_envelope)
        assert response.status_code == 200

    def test_sensor_ingest_returns_ok_and_stored(self, client, valid_sensor_envelope, cleanup_test_data):
        """Test that /sensor_ingest returns ok and stored flags."""
        response = client.post("/sensor_ingest", json=valid_sensor_envelope)
        data = response.json()
        assert "ok" in data
        assert "stored" in data
        assert data["ok"] is True
        assert data["stored"] is True

    def test_sensor_ingest_creates_json_file(self, client, valid_sensor_envelope, cleanup_test_data):
        """Test that /sensor_ingest creates a JSON file in the correct location."""
        response = client.post("/sensor_ingest", json=valid_sensor_envelope)
        assert response.status_code == 200

        # Check that a file was created in today's folder
        today_folder = get_sensors_dir() / today_str()
        assert today_folder.exists(), f"Today's folder should exist: {today_folder}"

        json_files = list(today_folder.glob("moisture_*.json"))
        assert len(json_files) >= 1, "At least one moisture sensor JSON file should exist"

        # Verify the file contains valid JSON with expected fields
        with open(json_files[0], "r") as f:
            stored_data = json.load(f)

        assert "timestamp" in stored_data
        assert "sensor_type" in stored_data
        assert stored_data["sensor_type"] == "moisture"
        assert "value" in stored_data
        assert stored_data["value"] == 0.18

    def test_sensor_ingest_appends_to_index(self, client, valid_sensor_envelope, cleanup_test_data):
        """Test that /sensor_ingest appends an entry to the sensor index."""
        # Clear index first
        index_path = get_sensor_index_path()
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text("")

        response = client.post("/sensor_ingest", json=valid_sensor_envelope)
        assert response.status_code == 200

        # Check that an entry was appended to the index
        assert index_path.exists(), f"Index file should exist: {index_path}"

        with open(index_path, "r") as f:
            lines = [line.strip() for line in f if line.strip()]

        assert len(lines) >= 1, "At least one index entry should exist"

        # Parse the last entry
        entry = json.loads(lines[-1])
        assert "timestamp" in entry
        assert "sensor_type" in entry
        assert entry["sensor_type"] == "moisture"
        assert "value" in entry
        assert "path" in entry

    def test_sensor_ingest_with_dict_value(self, client, valid_sensor_envelope_dict_value, cleanup_test_data):
        """Test that /sensor_ingest handles dict values correctly."""
        response = client.post("/sensor_ingest", json=valid_sensor_envelope_dict_value)
        assert response.status_code == 200

        data = response.json()
        assert data["ok"] is True
        assert data["stored"] is True

    def test_sensor_ingest_invalid_payload_returns_422(self, client, invalid_sensor_payload_envelope):
        """Test that /sensor_ingest returns 422 with invalid sensor payload."""
        response = client.post("/sensor_ingest", json=invalid_sensor_payload_envelope)
        assert response.status_code == 422

    def test_sensor_ingest_missing_task_envelope_fields_returns_422(self, client):
        """Test that /sensor_ingest returns 422 when TaskEnvelope fields are missing."""
        invalid_envelope = {
            "task_id": "test-001"
            # Missing required fields
        }
        response = client.post("/sensor_ingest", json=invalid_envelope)
        assert response.status_code == 422


class TestStatusWithSensorStats:
    """Tests for /status endpoint with sensor statistics."""

    def test_status_includes_sensor_stats(self, client):
        """Test that /status includes sensors_today and index_size."""
        response = client.get("/status")
        assert response.status_code == 200

        data = response.json()
        assert "sensors_today" in data
        assert "index_size" in data
        assert isinstance(data["sensors_today"], int)
        assert isinstance(data["index_size"], int)
