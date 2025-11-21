"""
Tests for Hobbs Agent valve control functionality.

Tests verify:
- Valid open/close commands succeed
- Unknown actions return errors
- Aegis verification is honored
- History entries are appended
- State file is updated
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
from server.actuators.valve_controller import (
    ValveController,
    VALVE_STATE_FILE,
    VALVE_HISTORY_FILE,
    ACTUATORS_DIR,
)
from server.actuators.aegis_client import request_verification
from schemas.actuators import ValveCommandPayload, VALID_ACTIONS, is_valid_action


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def valid_open_envelope():
    """Create a valid TaskEnvelope for valve open command."""
    return {
        "task_id": "test-valve-001",
        "source": "test-source",
        "target": "hobbs",
        "type": "control",
        "payload": {
            "valve_id": "test_valve",
            "action": "open",
            "value": 1.0,
            "reason": "test_open"
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@pytest.fixture
def valid_close_envelope():
    """Create a valid TaskEnvelope for valve close command."""
    return {
        "task_id": "test-valve-002",
        "source": "test-source",
        "target": "hobbs",
        "type": "control",
        "payload": {
            "valve_id": "test_valve",
            "action": "close",
            "reason": "test_close"
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@pytest.fixture
def valid_toggle_envelope():
    """Create a valid TaskEnvelope for valve toggle command."""
    return {
        "task_id": "test-valve-003",
        "source": "test-source",
        "target": "hobbs",
        "type": "control",
        "payload": {
            "valve_id": "test_valve",
            "action": "toggle",
            "reason": "test_toggle"
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@pytest.fixture
def valid_set_envelope():
    """Create a valid TaskEnvelope for valve set command."""
    return {
        "task_id": "test-valve-004",
        "source": "test-source",
        "target": "hobbs",
        "type": "control",
        "payload": {
            "valve_id": "test_valve",
            "action": "set",
            "value": 0.5,
            "reason": "test_partial"
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@pytest.fixture
def invalid_action_envelope():
    """Create an envelope with invalid action."""
    return {
        "task_id": "test-valve-invalid",
        "source": "test-source",
        "target": "hobbs",
        "type": "control",
        "payload": {
            "valve_id": "test_valve",
            "action": "invalid_action",
            "reason": "test_invalid"
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@pytest.fixture
def cleanup_valve_data():
    """Fixture to clean up test valve data after tests."""
    yield
    # Cleanup: Remove valve state and history files
    if VALVE_STATE_FILE.exists():
        VALVE_STATE_FILE.unlink()
    if VALVE_HISTORY_FILE.exists():
        VALVE_HISTORY_FILE.write_text("")


class TestValveCommandPayload:
    """Tests for the ValveCommandPayload schema."""

    def test_valid_payload(self):
        """Test that valid payload is accepted."""
        payload = ValveCommandPayload(
            valve_id="test",
            action="open",
            value=1.0,
            reason="test"
        )
        assert payload.valve_id == "test"
        assert payload.action == "open"

    def test_valid_actions(self):
        """Test that VALID_ACTIONS contains expected values."""
        assert "open" in VALID_ACTIONS
        assert "close" in VALID_ACTIONS
        assert "toggle" in VALID_ACTIONS
        assert "set" in VALID_ACTIONS

    def test_is_valid_action(self):
        """Test is_valid_action function."""
        assert is_valid_action("open") is True
        assert is_valid_action("CLOSE") is True
        assert is_valid_action("invalid") is False


class TestAegisClient:
    """Tests for the Aegis client stub."""

    def test_request_verification_returns_verified(self):
        """Test that stub returns verified=True."""
        command = {
            "valve_id": "test",
            "action": "open",
            "value": 1.0,
            "reason": "test",
            "source_task_id": "task-001",
            "source_agent": "test"
        }
        result = request_verification(command)

        assert "verified" in result
        assert result["verified"] is True
        assert "signature" in result
        assert "details" in result
        assert "timestamp" in result

    def test_request_verification_includes_details(self):
        """Test that verification includes command details."""
        command = {
            "valve_id": "main_irrigation",
            "action": "close",
            "source_agent": "sky"
        }
        result = request_verification(command)

        assert result["details"]["valve_id"] == "main_irrigation"
        assert result["details"]["action"] == "close"
        assert result["details"]["requested_by"] == "sky"


class TestValveController:
    """Tests for the ValveController class."""

    def test_apply_open_command(self, cleanup_valve_data):
        """Test applying an open command."""
        controller = ValveController()
        payload = ValveCommandPayload(
            valve_id="test_valve",
            action="open",
            reason="test"
        )
        aegis_token = {"verified": True, "signature": "test-sig"}

        result = controller.apply_command(
            payload, aegis_token, "task-001", "test"
        )

        assert result["ok"] is True
        assert result["state"] == "open"
        assert result["value"] == 1.0

    def test_apply_close_command(self, cleanup_valve_data):
        """Test applying a close command."""
        controller = ValveController()
        payload = ValveCommandPayload(
            valve_id="test_valve",
            action="close",
            reason="test"
        )
        aegis_token = {"verified": True, "signature": "test-sig"}

        result = controller.apply_command(
            payload, aegis_token, "task-001", "test"
        )

        assert result["ok"] is True
        assert result["state"] == "closed"
        assert result["value"] == 0.0

    def test_apply_set_command(self, cleanup_valve_data):
        """Test applying a set command."""
        controller = ValveController()
        payload = ValveCommandPayload(
            valve_id="test_valve",
            action="set",
            value=0.5,
            reason="test"
        )
        aegis_token = {"verified": True, "signature": "test-sig"}

        result = controller.apply_command(
            payload, aegis_token, "task-001", "test"
        )

        assert result["ok"] is True
        assert result["state"] == "partial"
        assert result["value"] == 0.5

    def test_toggle_changes_state(self, cleanup_valve_data):
        """Test that toggle changes valve state."""
        controller = ValveController()
        aegis_token = {"verified": True, "signature": "test-sig"}

        # First open the valve
        payload_open = ValveCommandPayload(
            valve_id="toggle_test",
            action="open",
            reason="test"
        )
        controller.apply_command(payload_open, aegis_token, "task-001", "test")

        # Now toggle (should close)
        payload_toggle = ValveCommandPayload(
            valve_id="toggle_test",
            action="toggle",
            reason="test"
        )
        result = controller.apply_command(
            payload_toggle, aegis_token, "task-002", "test"
        )

        assert result["state"] == "closed"

    def test_state_persistence(self, cleanup_valve_data):
        """Test that valve state is persisted to disk."""
        controller = ValveController()
        payload = ValveCommandPayload(
            valve_id="persist_test",
            action="open",
            reason="test"
        )
        aegis_token = {"verified": True, "signature": "test-sig"}

        controller.apply_command(payload, aegis_token, "task-001", "test")

        # Check state file exists
        assert VALVE_STATE_FILE.exists()

        # Load and verify
        with open(VALVE_STATE_FILE) as f:
            state = json.load(f)

        assert "persist_test" in state
        assert state["persist_test"]["state"] == "open"


class TestControlValveEndpoint:
    """Tests for the /control_valve endpoint."""

    def test_open_command_returns_200(
        self, client, valid_open_envelope, cleanup_valve_data
    ):
        """Test that open command returns 200 OK."""
        response = client.post("/control_valve", json=valid_open_envelope)
        assert response.status_code == 200

    def test_open_command_returns_expected_keys(
        self, client, valid_open_envelope, cleanup_valve_data
    ):
        """Test that open command returns expected response keys."""
        response = client.post("/control_valve", json=valid_open_envelope)
        data = response.json()

        assert "ok" in data
        assert "valve_id" in data
        assert "state" in data
        assert "value" in data
        assert "verified" in data
        assert data["ok"] is True
        assert data["state"] == "open"

    def test_close_command_returns_200(
        self, client, valid_close_envelope, cleanup_valve_data
    ):
        """Test that close command returns 200 OK."""
        response = client.post("/control_valve", json=valid_close_envelope)
        assert response.status_code == 200

        data = response.json()
        assert data["state"] == "closed"

    def test_set_command_returns_partial_state(
        self, client, valid_set_envelope, cleanup_valve_data
    ):
        """Test that set command returns partial state."""
        response = client.post("/control_valve", json=valid_set_envelope)
        assert response.status_code == 200

        data = response.json()
        assert data["state"] == "partial"
        assert data["value"] == 0.5

    def test_invalid_action_returns_422(
        self, client, invalid_action_envelope, cleanup_valve_data
    ):
        """Test that invalid action returns 422."""
        response = client.post("/control_valve", json=invalid_action_envelope)
        assert response.status_code == 422

    def test_missing_payload_fields_returns_422(self, client):
        """Test that missing payload fields returns 422."""
        envelope = {
            "task_id": "test-001",
            "source": "test",
            "target": "hobbs",
            "type": "control",
            "payload": {
                "valve_id": "test"
                # Missing action
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        response = client.post("/control_valve", json=envelope)
        assert response.status_code == 422

    def test_history_entry_created(
        self, client, valid_open_envelope, cleanup_valve_data
    ):
        """Test that history entry is created."""
        # Clear history first
        VALVE_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        VALVE_HISTORY_FILE.write_text("")

        response = client.post("/control_valve", json=valid_open_envelope)
        assert response.status_code == 200

        # Check history file
        with open(VALVE_HISTORY_FILE) as f:
            lines = [line.strip() for line in f if line.strip()]

        assert len(lines) >= 1

        entry = json.loads(lines[-1])
        assert entry["valve_id"] == "test_valve"
        assert entry["action"] == "open"
        assert "timestamp" in entry
        assert "aegis_signature" in entry


class TestStatusWithValveStats:
    """Tests for /status endpoint with valve statistics."""

    def test_status_includes_valve_stats(self, client):
        """Test that /status includes valve statistics."""
        response = client.get("/status")
        assert response.status_code == 200

        data = response.json()
        assert "valves_known" in data
        assert "valve_events_count" in data
        assert isinstance(data["valves_known"], int)
        assert isinstance(data["valve_events_count"], int)
