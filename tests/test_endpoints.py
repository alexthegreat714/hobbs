"""
Tests for Hobbs Agent endpoints.

Tests verify:
- Endpoints return 200 status codes
- Endpoints return expected response keys
- Invalid TaskEnvelope returns 422
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def valid_task_envelope():
    """Create a valid TaskEnvelope payload."""
    return {
        "task_id": "test-task-001",
        "source": "test-source",
        "target": "hobbs",
        "type": "test",
        "payload": {"data": "test"},
        "timestamp": "2024-01-15T10:30:00Z"
    }


@pytest.fixture
def invalid_task_envelope():
    """Create an invalid TaskEnvelope payload (missing required fields)."""
    return {
        "task_id": "test-task-001"
        # Missing required fields: source, target, type
    }


class TestStatusEndpoint:
    """Tests for the /status endpoint."""

    def test_status_returns_200(self, client):
        """Test that /status returns 200 OK."""
        response = client.get("/status")
        assert response.status_code == 200

    def test_status_returns_expected_keys(self, client):
        """Test that /status returns expected keys."""
        response = client.get("/status")
        data = response.json()
        assert "status" in data
        assert "agent" in data
        assert "version" in data
        assert data["status"] == "ok"
        assert data["agent"] == "hobbs"


class TestRunTaskEndpoint:
    """Tests for the /run_task endpoint."""

    def test_run_task_returns_200(self, client, valid_task_envelope):
        """Test that /run_task returns 200 OK with valid input."""
        response = client.post("/run_task", json=valid_task_envelope)
        assert response.status_code == 200

    def test_run_task_returns_expected_keys(self, client, valid_task_envelope):
        """Test that /run_task returns expected keys."""
        response = client.post("/run_task", json=valid_task_envelope)
        data = response.json()
        assert "ok" in data
        assert "message" in data
        assert "task_id" in data
        assert data["ok"] is True

    def test_run_task_invalid_envelope_returns_422(self, client, invalid_task_envelope):
        """Test that /run_task returns 422 with invalid input."""
        response = client.post("/run_task", json=invalid_task_envelope)
        assert response.status_code == 422


class TestEventEndpoint:
    """Tests for the /event endpoint."""

    def test_event_returns_200(self, client, valid_task_envelope):
        """Test that /event returns 200 OK with valid input."""
        response = client.post("/event", json=valid_task_envelope)
        assert response.status_code == 200

    def test_event_returns_expected_keys(self, client, valid_task_envelope):
        """Test that /event returns expected keys."""
        response = client.post("/event", json=valid_task_envelope)
        data = response.json()
        assert "ok" in data
        assert "message" in data
        assert "task_id" in data

    def test_event_invalid_envelope_returns_422(self, client, invalid_task_envelope):
        """Test that /event returns 422 with invalid input."""
        response = client.post("/event", json=invalid_task_envelope)
        assert response.status_code == 422


class TestShutdownEndpoint:
    """Tests for the /shutdown endpoint."""

    def test_shutdown_returns_200(self, client, valid_task_envelope):
        """Test that /shutdown returns 200 OK with valid input."""
        response = client.post("/shutdown", json=valid_task_envelope)
        assert response.status_code == 200

    def test_shutdown_returns_expected_keys(self, client, valid_task_envelope):
        """Test that /shutdown returns expected keys."""
        response = client.post("/shutdown", json=valid_task_envelope)
        data = response.json()
        assert "ok" in data
        assert data["ok"] is True

    def test_shutdown_invalid_envelope_returns_422(self, client, invalid_task_envelope):
        """Test that /shutdown returns 422 with invalid input."""
        response = client.post("/shutdown", json=invalid_task_envelope)
        assert response.status_code == 422


class TestSensorIngestEndpoint:
    """Tests for the /sensor_ingest endpoint."""

    def test_sensor_ingest_returns_200(self, client, valid_task_envelope):
        """Test that /sensor_ingest returns 200 OK with valid input."""
        response = client.post("/sensor_ingest", json=valid_task_envelope)
        assert response.status_code == 200

    def test_sensor_ingest_returns_expected_keys(self, client, valid_task_envelope):
        """Test that /sensor_ingest returns expected keys."""
        response = client.post("/sensor_ingest", json=valid_task_envelope)
        data = response.json()
        assert "ok" in data
        assert "received" in data
        assert data["received"] == "sensor_ingest"

    def test_sensor_ingest_invalid_envelope_returns_422(self, client, invalid_task_envelope):
        """Test that /sensor_ingest returns 422 with invalid input."""
        response = client.post("/sensor_ingest", json=invalid_task_envelope)
        assert response.status_code == 422


class TestPredictWeatherEndpoint:
    """Tests for the /predict_weather endpoint."""

    def test_predict_weather_returns_200(self, client, valid_task_envelope):
        """Test that /predict_weather returns 200 OK with valid input."""
        response = client.post("/predict_weather", json=valid_task_envelope)
        assert response.status_code == 200

    def test_predict_weather_returns_expected_keys(self, client, valid_task_envelope):
        """Test that /predict_weather returns expected keys."""
        response = client.post("/predict_weather", json=valid_task_envelope)
        data = response.json()
        assert "ok" in data
        assert "received" in data
        assert data["received"] == "predict_weather"

    def test_predict_weather_invalid_envelope_returns_422(self, client, invalid_task_envelope):
        """Test that /predict_weather returns 422 with invalid input."""
        response = client.post("/predict_weather", json=invalid_task_envelope)
        assert response.status_code == 422


class TestDetectIntruderEndpoint:
    """Tests for the /detect_intruder endpoint."""

    def test_detect_intruder_returns_200(self, client, valid_task_envelope):
        """Test that /detect_intruder returns 200 OK with valid input."""
        response = client.post("/detect_intruder", json=valid_task_envelope)
        assert response.status_code == 200

    def test_detect_intruder_returns_expected_keys(self, client, valid_task_envelope):
        """Test that /detect_intruder returns expected keys."""
        response = client.post("/detect_intruder", json=valid_task_envelope)
        data = response.json()
        assert "ok" in data
        assert "received" in data
        assert data["received"] == "detect_intruder"

    def test_detect_intruder_invalid_envelope_returns_422(self, client, invalid_task_envelope):
        """Test that /detect_intruder returns 422 with invalid input."""
        response = client.post("/detect_intruder", json=invalid_task_envelope)
        assert response.status_code == 422


class TestControlValveEndpoint:
    """Tests for the /control_valve endpoint."""

    def test_control_valve_returns_200(self, client, valid_task_envelope):
        """Test that /control_valve returns 200 OK with valid input."""
        response = client.post("/control_valve", json=valid_task_envelope)
        assert response.status_code == 200

    def test_control_valve_returns_expected_keys(self, client, valid_task_envelope):
        """Test that /control_valve returns expected keys."""
        response = client.post("/control_valve", json=valid_task_envelope)
        data = response.json()
        assert "ok" in data
        assert "received" in data
        assert data["received"] == "control_valve"

    def test_control_valve_invalid_envelope_returns_422(self, client, invalid_task_envelope):
        """Test that /control_valve returns 422 with invalid input."""
        response = client.post("/control_valve", json=invalid_task_envelope)
        assert response.status_code == 422


class TestRootEndpoint:
    """Tests for the root / endpoint."""

    def test_root_returns_200(self, client):
        """Test that / returns 200 OK."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_returns_expected_keys(self, client):
        """Test that / returns expected keys."""
        response = client.get("/")
        data = response.json()
        assert "agent" in data
        assert "version" in data
        assert "status" in data
