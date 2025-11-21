"""
Tests for Hobbs Agent memory system.

Tests verify:
- Memory manager builds events from logs
- Query engine filters and searches correctly
- Memory query endpoint works
- Intruder stats calculation
"""

import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from app import app

from schemas.memory import MemoryEvent, MemoryQueryPayload


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def valid_task_envelope():
    """Create a valid TaskEnvelope payload."""
    return {
        "task_id": "test-memory-001",
        "source": "test-source",
        "target": "hobbs",
        "type": "memory_query",
        "payload": {"query": "test", "limit": 10},
        "timestamp": "2024-01-15T10:30:00Z"
    }


class TestMemoryEvent:
    """Tests for MemoryEvent schema."""

    def test_memory_event_creation(self):
        """Test creating a MemoryEvent."""
        event = MemoryEvent(
            event_id="evt_test_001",
            timestamp="2024-01-15T10:30:00Z",
            source="sensor",
            subtype="moisture",
            summary="Test sensor event",
            tags=["test", "moisture"],
            raw_path="/data/sensors/test.json",
            metadata={"value": 0.5}
        )
        assert event.event_id == "evt_test_001"
        assert event.source == "sensor"
        assert "moisture" in event.tags

    def test_memory_event_defaults(self):
        """Test MemoryEvent default values."""
        event = MemoryEvent(
            event_id="evt_test_002",
            timestamp="2024-01-15T10:30:00Z",
            source="weather",
            subtype="forecast",
            summary="Test weather event",
        )
        assert event.tags == []
        assert event.raw_path is None
        assert event.metadata == {}


class TestMemoryQueryPayload:
    """Tests for MemoryQueryPayload schema."""

    def test_query_payload_defaults(self):
        """Test default values for query payload."""
        payload = MemoryQueryPayload()
        assert payload.query is None
        assert payload.limit == 50
        assert payload.days == 30

    def test_query_payload_with_filters(self):
        """Test query payload with filters."""
        payload = MemoryQueryPayload(
            query="intruder",
            source_filter=["camera"],
            tags=["human"],
            limit=20
        )
        assert payload.query == "intruder"
        assert "camera" in payload.source_filter
        assert payload.limit == 20


class TestMemoryManager:
    """Tests for memory manager."""

    def test_memory_manager_exists(self):
        """Test that memory manager singleton exists."""
        from server.memory.memory_manager import memory_manager
        assert memory_manager is not None

    def test_generate_event_id(self):
        """Test event ID generation."""
        from server.memory.memory_manager import memory_manager
        event_id = memory_manager._generate_event_id("sensor")
        assert event_id.startswith("evt_sensor_")
        assert len(event_id) > 10

    def test_rebuild_full_memory(self):
        """Test full memory rebuild."""
        from server.memory.memory_manager import memory_manager

        # This should run without errors even if no logs exist
        counts = memory_manager.rebuild_full_memory()

        assert "sensor" in counts
        assert "weather" in counts
        assert "camera" in counts
        assert "valve" in counts
        assert "automation" in counts
        assert "total" in counts

    def test_get_events_count(self):
        """Test getting events count."""
        from server.memory.memory_manager import memory_manager
        count = memory_manager.get_events_count()
        assert isinstance(count, int)
        assert count >= 0


class TestQueryEngine:
    """Tests for query engine."""

    def test_query_engine_exists(self):
        """Test that query engine singleton exists."""
        from server.memory.query_engine import query_engine
        assert query_engine is not None

    def test_search_memory_empty(self):
        """Test searching empty memory."""
        from server.memory.query_engine import query_engine

        results = query_engine.search_memory(
            text_query="nonexistent",
            limit=10
        )
        assert isinstance(results, list)

    def test_search_memory_with_source_filter(self):
        """Test searching with source filter."""
        from server.memory.query_engine import query_engine

        results = query_engine.search_memory(
            source_filter=["camera"],
            limit=10
        )
        assert isinstance(results, list)
        # All results should have source="camera"
        for event in results:
            assert event.source == "camera"

    def test_search_memory_with_tag_filter(self):
        """Test searching with tag filter."""
        from server.memory.query_engine import query_engine

        results = query_engine.search_memory(
            tag_filter=["intruder"],
            limit=10
        )
        assert isinstance(results, list)
        # All results should have "intruder" tag
        for event in results:
            assert "intruder" in [t.lower() for t in event.tags]

    def test_get_intruder_stats(self):
        """Test getting intruder statistics."""
        from server.memory.query_engine import query_engine

        stats = query_engine.get_intruder_stats(days=30)

        assert hasattr(stats, "total_intruders")
        assert hasattr(stats, "by_camera")
        assert hasattr(stats, "by_hour")
        assert hasattr(stats, "last_seen")
        assert isinstance(stats.total_intruders, int)
        assert isinstance(stats.by_camera, dict)
        assert isinstance(stats.by_hour, dict)

    def test_get_sensor_trends(self):
        """Test getting sensor trends."""
        from server.memory.query_engine import query_engine

        trends = query_engine.get_sensor_trends("moisture", days=7)

        assert "sensor_type" in trends
        assert "days" in trends
        assert "count" in trends
        assert trends["sensor_type"] == "moisture"
        assert trends["days"] == 7


class TestMemoryQueryEndpoint:
    """Tests for the /memory_query endpoint."""

    def test_memory_query_returns_200(self, client, valid_task_envelope):
        """Test that /memory_query returns 200 OK."""
        response = client.post("/memory_query", json=valid_task_envelope)
        assert response.status_code == 200

    def test_memory_query_returns_results(self, client, valid_task_envelope):
        """Test that /memory_query returns results structure."""
        response = client.post("/memory_query", json=valid_task_envelope)
        data = response.json()

        assert "ok" in data
        assert data["ok"] is True
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_memory_query_with_source_filter(self, client):
        """Test memory query with source filter."""
        envelope = {
            "task_id": "test-mem-002",
            "source": "test",
            "target": "hobbs",
            "type": "memory_query",
            "payload": {
                "source_filter": ["sensor"],
                "limit": 5
            },
            "timestamp": "2024-01-15T10:30:00Z"
        }
        response = client.post("/memory_query", json=envelope)
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_memory_query_intruder_stats_mode(self, client):
        """Test memory query in intruder_stats mode."""
        envelope = {
            "task_id": "test-mem-003",
            "source": "test",
            "target": "hobbs",
            "type": "memory_query",
            "payload": {
                "mode": "intruder_stats",
                "days": 30
            },
            "timestamp": "2024-01-15T10:30:00Z"
        }
        response = client.post("/memory_query", json=envelope)
        assert response.status_code == 200
        data = response.json()

        assert "ok" in data
        assert data["ok"] is True
        assert "stats" in data
        assert "total_intruders" in data["stats"]
        assert "by_camera" in data["stats"]
        assert "by_hour" in data["stats"]

    def test_memory_query_invalid_envelope(self, client):
        """Test that invalid envelope returns 422."""
        invalid = {"task_id": "test-invalid"}
        response = client.post("/memory_query", json=invalid)
        assert response.status_code == 422


class TestRunTaskMemoryRebuild:
    """Tests for memory rebuild via run_task."""

    def test_memory_rebuild_task(self, client):
        """Test triggering memory rebuild via run_task."""
        envelope = {
            "task_id": "test-rebuild-001",
            "source": "test",
            "target": "hobbs",
            "type": "memory_rebuild",
            "payload": {
                "target": "hobbs.memory"
            },
            "timestamp": "2024-01-15T10:30:00Z"
        }
        response = client.post("/run_task", json=envelope)
        assert response.status_code == 200
        data = response.json()

        assert data["ok"] is True
        assert "counts" in data
        assert "total" in data["counts"]


class TestStatusEndpointMemory:
    """Tests for memory stats in status endpoint."""

    def test_status_includes_memory_stats(self, client):
        """Test that /status includes memory statistics."""
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()

        assert "memory_events_count" in data
        assert "intruder_events_count" in data
        assert "weather_summary_count" in data
        assert isinstance(data["memory_events_count"], int)
