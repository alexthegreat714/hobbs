"""
Tests for Hobbs Agent integration module.

Tests verify:
- Event bus routing and handling
- Congress client policy management
- Argus client metrics collection
- Sky client summary sending
- Apollo client notifications
- Aegis adapter verification
- /event endpoint event routing
- Status endpoint integration metrics
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


class TestEventBus:
    """Tests for the event bus."""

    def test_event_bus_initialization(self):
        """Test that event bus initializes correctly."""
        from server.integration.event_bus import event_bus

        assert event_bus is not None
        assert hasattr(event_bus, "publish_event")
        assert hasattr(event_bus, "handle_incoming_event")

    def test_publish_event(self):
        """Test event publishing."""
        from server.integration.event_bus import event_bus

        event = {
            "type": "test.event",
            "payload": {"test": "data"},
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        result = event_bus.publish_event(event)
        assert result is True

    def test_handle_incoming_event_weather_alert(self):
        """Test handling weather alert event."""
        from server.integration.event_bus import event_bus
        from schemas.shared import TaskEnvelope

        envelope = TaskEnvelope(
            task_id="test-weather-001",
            source="test",
            target="hobbs",
            type="weather.alert",
            payload={
                "condition": "frost_warning",
                "severity": "high"
            }
        )

        result = event_bus.handle_incoming_event(envelope)

        assert result["handled"] is True
        assert result["event_type"] == "weather.alert"

    def test_handle_incoming_event_learning_trigger(self):
        """Test handling learning trigger event."""
        from server.integration.event_bus import event_bus
        from schemas.shared import TaskEnvelope

        envelope = TaskEnvelope(
            task_id="test-learning-001",
            source="test",
            target="hobbs",
            type="learning.trigger",
            payload={}
        )

        result = event_bus.handle_incoming_event(envelope)

        assert result["handled"] is True
        assert result["event_type"] == "learning.trigger"


class TestCongressClient:
    """Tests for the Congress client."""

    def test_congress_client_initialization(self):
        """Test that Congress client initializes correctly."""
        from server.integration.congress_client import congress_client

        assert congress_client is not None
        assert hasattr(congress_client, "load_policies")
        assert hasattr(congress_client, "send_heartbeat")

    def test_load_policies(self):
        """Test policy loading."""
        from server.integration.congress_client import congress_client

        policies = congress_client.load_policies()

        assert isinstance(policies, dict)
        assert "permissions" in policies
        assert "limits" in policies

    def test_apply_policies(self):
        """Test policy application."""
        from server.integration.congress_client import congress_client

        test_policies = {
            "version": "test",
            "permissions": {"test_action": True},
            "limits": {"test_limit": 100}
        }

        result = congress_client.apply_policies(test_policies)
        assert result is True

        # Check permission
        assert congress_client.check_permission("test_action") is True

    def test_check_permission(self):
        """Test permission checking."""
        from server.integration.congress_client import congress_client

        # Load default policies
        policies = congress_client.load_policies()
        congress_client.apply_policies(policies)

        # Default policies should allow valve_control
        assert congress_client.check_permission("valve_control") is True

    def test_send_heartbeat(self):
        """Test heartbeat sending."""
        from server.integration.congress_client import congress_client

        result = congress_client.send_heartbeat()
        assert result is True

        # Should have last heartbeat set
        last_hb = congress_client.last_heartbeat
        assert last_hb is not None

    def test_policies_loaded_property(self):
        """Test policies_loaded property."""
        from server.integration.congress_client import CongressClient

        client = CongressClient()

        # Initially no policies
        assert client.policies_loaded is False

        # Load and apply
        policies = client.load_policies()
        client.apply_policies(policies)
        assert client.policies_loaded is True


class TestArgusClient:
    """Tests for the Argus client."""

    def test_argus_client_initialization(self):
        """Test that Argus client initializes correctly."""
        from server.integration.argus_client import argus_client

        assert argus_client is not None
        assert hasattr(argus_client, "collect_metrics")
        assert hasattr(argus_client, "publish_metrics")

    def test_collect_metrics(self):
        """Test metrics collection."""
        from server.integration.argus_client import argus_client

        metrics = argus_client.collect_metrics()

        assert isinstance(metrics, dict)
        assert "timestamp" in metrics
        assert "agent" in metrics
        assert "cpu_usage" in metrics
        assert "mem_usage" in metrics
        assert "events_today" in metrics
        assert "health_status" in metrics

    def test_publish_metrics(self):
        """Test metrics publishing."""
        from server.integration.argus_client import argus_client

        metrics = argus_client.collect_metrics()
        result = argus_client.publish_metrics(metrics)

        assert result is True

    def test_last_metrics_property(self):
        """Test last_metrics property."""
        from server.integration.argus_client import argus_client

        # Collect metrics first
        argus_client.collect_metrics()

        last = argus_client.last_metrics
        assert isinstance(last, dict)
        assert "timestamp" in last


class TestSkyClient:
    """Tests for the Sky client."""

    def test_sky_client_initialization(self):
        """Test that Sky client initializes correctly."""
        from server.integration.sky_client import sky_client

        assert sky_client is not None
        assert hasattr(sky_client, "send_summary")
        assert hasattr(sky_client, "send_status_update")

    def test_send_summary(self):
        """Test summary sending."""
        from server.integration.sky_client import sky_client

        summary = {
            "type": "test_summary",
            "data": {"test": "value"}
        }

        result = sky_client.send_summary(summary)
        assert result is True

    def test_send_status_update(self):
        """Test status update sending."""
        from server.integration.sky_client import sky_client

        status = {"status": "healthy", "events": 10}
        result = sky_client.send_status_update(status)

        assert result is True


class TestApolloClient:
    """Tests for the Apollo client."""

    def test_apollo_client_initialization(self):
        """Test that Apollo client initializes correctly."""
        from server.integration.apollo_client import apollo_client

        assert apollo_client is not None
        assert hasattr(apollo_client, "notify_event")
        assert hasattr(apollo_client, "send_alert")

    def test_notify_event(self):
        """Test event notification."""
        from server.integration.apollo_client import apollo_client

        event = {
            "type": "test.event",
            "severity": "info",
            "message": "Test event"
        }

        result = apollo_client.notify_event(event)
        assert result is True

    def test_send_alert(self):
        """Test alert sending."""
        from server.integration.apollo_client import apollo_client

        result = apollo_client.send_alert(
            alert_type="security",
            message="Test alert",
            severity="high"
        )

        assert result is True


class TestAegisAdapter:
    """Tests for the Aegis adapter."""

    def test_aegis_adapter_initialization(self):
        """Test that Aegis adapter initializes correctly."""
        from server.integration.aegis_adapter import aegis_adapter

        assert aegis_adapter is not None
        assert hasattr(aegis_adapter, "verify_action")
        assert hasattr(aegis_adapter, "verify_valve_command")

    def test_verify_action_basic(self):
        """Test basic action verification."""
        from server.integration.aegis_adapter import aegis_adapter

        result = aegis_adapter.verify_action(
            action_type="sensor_read",
            payload={"sensor_id": "test_sensor"}
        )

        assert "verified" in result
        assert result["verified"] is True

    def test_verify_valve_command(self):
        """Test valve command verification."""
        from server.integration.aegis_adapter import aegis_adapter

        result = aegis_adapter.verify_valve_command(
            valve_id="test_valve",
            action="open"
        )

        assert "verified" in result
        # Result depends on whether Aegis integration is available
        assert isinstance(result["verified"], bool)


class TestEventEndpoint:
    """Tests for the /event endpoint with integration."""

    def test_event_endpoint_returns_valid_json(self):
        """Test that /event endpoint returns valid JSON structure."""
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)

        response = client.post(
            "/event",
            json={
                "task_id": "integration-test-001",
                "source": "test",
                "target": "hobbs",
                "type": "weather.alert",
                "payload": {
                    "condition": "rain_expected",
                    "severity": "medium"
                }
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "ok" in data
        assert data["ok"] is True
        assert "handled" in data
        assert data["handled"] is True

    def test_event_endpoint_handles_learning_trigger(self):
        """Test that /event endpoint handles learning.trigger."""
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)

        response = client.post(
            "/event",
            json={
                "task_id": "integration-test-002",
                "source": "congress",
                "target": "hobbs",
                "type": "learning.trigger",
                "payload": {}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    def test_event_endpoint_handles_policy_update(self):
        """Test that /event endpoint handles congress.policy.update."""
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)

        response = client.post(
            "/event",
            json={
                "task_id": "integration-test-003",
                "source": "congress",
                "target": "hobbs",
                "type": "congress.policy.update",
                "payload": {
                    "policies": {
                        "permissions": {"test": True}
                    }
                }
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True


class TestStatusEndpointIntegration:
    """Tests for the /status endpoint with integration metrics."""

    def test_status_endpoint_includes_integration_stats(self):
        """Test that status endpoint includes integration statistics."""
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)
        response = client.get("/status")

        assert response.status_code == 200
        data = response.json()

        # Check integration stats are present
        assert "policies_loaded" in data
        assert "last_heartbeat" in data
        assert "last_learning_cycle" in data
        assert "metrics_snapshot" in data

        # Validate types
        assert isinstance(data["policies_loaded"], bool)
        assert isinstance(data["metrics_snapshot"], (dict, type(None)))


class TestIntegrationModuleImports:
    """Tests for module imports and exports."""

    def test_integration_init_exports(self):
        """Test that integration __init__ exports all components."""
        from server.integration import (
            event_bus,
            congress_client,
            argus_client,
            sky_client,
            apollo_client,
            aegis_adapter,
        )

        assert event_bus is not None
        assert congress_client is not None
        assert argus_client is not None
        assert sky_client is not None
        assert apollo_client is not None
        assert aegis_adapter is not None


class TestRunHobbsScript:
    """Tests for the run_hobbs.py script."""

    def test_run_hobbs_imports(self):
        """Test that run_hobbs.py can be imported."""
        import run_hobbs

        assert hasattr(run_hobbs, "run_heartbeat_loop")
        assert hasattr(run_hobbs, "run_server")
        assert hasattr(run_hobbs, "main")

    def test_run_hobbs_single_tick(self):
        """Test run_hobbs in single-tick mode."""
        from run_hobbs import run_heartbeat_loop

        # Run a single tick - should complete without error
        run_heartbeat_loop(
            heartbeat_interval=1,
            metrics_interval=1,
            learning_interval=1,
            single_tick=True
        )

        # If we get here without exception, test passes
        assert True
