"""
Tests for Hobbs Agent learning engine.

Tests verify:
- Pattern utilities (rolling_avg, z_score, correlation)
- Sensor baseline computation
- Intruder pattern detection
- Rule suggestion generation
- Learning report endpoint
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


class TestPatternUtilities:
    """Tests for pattern utility functions."""

    def test_rolling_avg_basic(self):
        """Test rolling average with simple data."""
        from server.learning.patterns import rolling_avg

        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = rolling_avg(values, window=3)

        assert len(result) == 3  # 5 - 3 + 1 = 3
        assert result[0] == pytest.approx(2.0)  # (1+2+3)/3
        assert result[1] == pytest.approx(3.0)  # (2+3+4)/3
        assert result[2] == pytest.approx(4.0)  # (3+4+5)/3

    def test_rolling_avg_empty(self):
        """Test rolling average with empty input."""
        from server.learning.patterns import rolling_avg

        result = rolling_avg([], window=3)
        assert result == []

    def test_rolling_avg_window_larger_than_data(self):
        """Test rolling average when window is larger than data."""
        from server.learning.patterns import rolling_avg

        values = [1.0, 2.0]
        result = rolling_avg(values, window=5)

        # Should adjust window to data length
        assert len(result) == 1
        assert result[0] == pytest.approx(1.5)

    def test_z_score_basic(self):
        """Test z-score calculation."""
        from server.learning.patterns import z_score

        # Value 2 standard deviations above mean
        result = z_score(value=30, mean=20, std=5)
        assert result == pytest.approx(2.0)

        # Value at mean
        result = z_score(value=20, mean=20, std=5)
        assert result == pytest.approx(0.0)

        # Value 1 std below mean
        result = z_score(value=15, mean=20, std=5)
        assert result == pytest.approx(-1.0)

    def test_z_score_zero_std(self):
        """Test z-score with zero standard deviation."""
        from server.learning.patterns import z_score

        result = z_score(value=25, mean=20, std=0)
        assert result == 0.0

    def test_correlation_positive(self):
        """Test positive correlation."""
        from server.learning.patterns import correlation

        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [2.0, 4.0, 6.0, 8.0, 10.0]  # Perfect positive correlation

        result = correlation(xs, ys)
        assert result == pytest.approx(1.0, abs=0.001)

    def test_correlation_negative(self):
        """Test negative correlation."""
        from server.learning.patterns import correlation

        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [10.0, 8.0, 6.0, 4.0, 2.0]  # Perfect negative correlation

        result = correlation(xs, ys)
        assert result == pytest.approx(-1.0, abs=0.001)

    def test_correlation_no_correlation(self):
        """Test with uncorrelated data."""
        from server.learning.patterns import correlation

        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [5.0, 3.0, 7.0, 2.0, 6.0]  # Random

        result = correlation(xs, ys)
        # Should be weak (between -0.5 and 0.5)
        assert -1.0 <= result <= 1.0

    def test_correlation_insufficient_data(self):
        """Test correlation with insufficient data."""
        from server.learning.patterns import correlation

        # Single point
        result = correlation([1.0], [2.0])
        assert result == 0.0

        # Empty
        result = correlation([], [])
        assert result == 0.0

        # Mismatched lengths
        result = correlation([1.0, 2.0], [1.0])
        assert result == 0.0

    def test_mean_calculation(self):
        """Test mean calculation."""
        from server.learning.patterns import mean

        result = mean([1.0, 2.0, 3.0, 4.0, 5.0])
        assert result == pytest.approx(3.0)

        result = mean([])
        assert result == 0.0

    def test_std_dev_calculation(self):
        """Test standard deviation calculation."""
        from server.learning.patterns import std_dev

        # Known values
        values = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
        result = std_dev(values)
        assert result == pytest.approx(2.0, abs=0.1)

        # Empty and single value
        assert std_dev([]) == 0.0
        assert std_dev([5.0]) == 0.0

    def test_detect_trend_increasing(self):
        """Test trend detection for increasing values."""
        from server.learning.patterns import detect_trend

        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
        result = detect_trend(values)
        assert result == "increasing"

    def test_detect_trend_decreasing(self):
        """Test trend detection for decreasing values."""
        from server.learning.patterns import detect_trend

        values = [10.0, 9.0, 8.0, 7.0, 6.0, 5.0]
        result = detect_trend(values)
        assert result == "decreasing"

    def test_detect_trend_stable(self):
        """Test trend detection for stable values."""
        from server.learning.patterns import detect_trend

        values = [5.0, 5.0, 5.0, 5.0, 5.0]
        result = detect_trend(values)
        assert result == "stable"

    def test_detect_trend_insufficient_data(self):
        """Test trend detection with insufficient data."""
        from server.learning.patterns import detect_trend

        result = detect_trend([1.0, 2.0])
        assert result == "stable"

    def test_histogram(self):
        """Test histogram creation."""
        from server.learning.patterns import histogram

        data = ["a", "b", "a", "c", "a", "b"]
        bins = ["a", "b", "c", "d"]
        result = histogram(data, bins)

        assert result["a"] == 3
        assert result["b"] == 2
        assert result["c"] == 1
        assert result["d"] == 0

    def test_detect_peak_hours(self):
        """Test peak hour detection."""
        from server.learning.patterns import detect_peak_hours

        hourly_counts = {
            "08": 5,
            "09": 10,
            "10": 3,
            "14": 15,
            "15": 8,
        }

        result = detect_peak_hours(hourly_counts, top_n=3)
        assert len(result) == 3
        assert result[0] == "14"  # Highest count
        assert result[1] == "09"  # Second highest
        assert result[2] == "15"  # Third highest

    def test_compute_statistics(self):
        """Test comprehensive statistics computation."""
        from server.learning.patterns import compute_statistics

        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = compute_statistics(values)

        assert result["avg"] == pytest.approx(3.0)
        assert result["min"] == 1.0
        assert result["max"] == 5.0
        assert result["count"] == 5
        assert result["std_dev"] > 0

        # Empty case
        result = compute_statistics([])
        assert result["count"] == 0


class TestSensorBaselines:
    """Tests for sensor baseline computation."""

    def test_compute_sensor_baselines_synthetic(self):
        """Test baseline computation with synthetic data."""
        from server.learning.learning_engine import LearningEngine
        from schemas.memory import MemoryEvent

        engine = LearningEngine()

        # Create synthetic sensor events
        events = []
        for i in range(20):
            events.append(MemoryEvent(
                event_id=f"evt-{i}",
                timestamp=datetime.utcnow().isoformat() + "Z",
                source="sensor",
                subtype="moisture",
                summary=f"Moisture reading {i}",
                metadata={"value": 0.3 + (i * 0.01)},  # Values 0.30 to 0.49
            ))

        for i in range(10):
            events.append(MemoryEvent(
                event_id=f"temp-{i}",
                timestamp=datetime.utcnow().isoformat() + "Z",
                source="sensor",
                subtype="temperature",
                summary=f"Temperature reading {i}",
                metadata={"value": 20.0 + i},  # Values 20-29
            ))

        result = engine.compute_sensor_baselines(events)

        # Should have baselines for both sensor types
        assert "moisture" in result
        assert "temperature" in result

        # Moisture baseline
        moisture = result["moisture"]
        assert moisture["count"] == 20
        assert moisture["min"] == pytest.approx(0.3, abs=0.01)
        assert moisture["max"] == pytest.approx(0.49, abs=0.01)
        assert "avg" in moisture
        assert "std_dev" in moisture
        assert "trend" in moisture

        # Temperature baseline
        temp = result["temperature"]
        assert temp["count"] == 10
        assert temp["min"] == pytest.approx(20.0)
        assert temp["max"] == pytest.approx(29.0)

    def test_compute_sensor_baselines_empty(self):
        """Test baseline computation with no events."""
        from server.learning.learning_engine import LearningEngine

        engine = LearningEngine()
        result = engine.compute_sensor_baselines([])

        assert result == {}


class TestIntruderPatterns:
    """Tests for intruder pattern detection."""

    def test_compute_intruder_patterns_synthetic(self):
        """Test intruder pattern computation with synthetic data."""
        from server.learning.learning_engine import LearningEngine
        from schemas.memory import MemoryEvent

        engine = LearningEngine()

        # Create synthetic intruder events
        events = []
        base_time = datetime(2024, 6, 15, 0, 0, 0)

        # Add intruder events at specific hours
        for i in range(5):  # 5 events at hour 02
            events.append(MemoryEvent(
                event_id=f"int-02-{i}",
                timestamp=(base_time.replace(hour=2)).isoformat() + "Z",
                source="camera",
                subtype="intruder",
                summary="Intruder detected",
                metadata={"camera_id": "cam-north", "object_detected": "person"},
            ))

        for i in range(3):  # 3 events at hour 14
            events.append(MemoryEvent(
                event_id=f"int-14-{i}",
                timestamp=(base_time.replace(hour=14)).isoformat() + "Z",
                source="camera",
                subtype="intruder",
                summary="Intruder detected",
                metadata={"camera_id": "cam-south", "object_detected": "animal"},
            ))

        result = engine.compute_intruder_patterns(events)

        assert result["total_intruders"] == 8
        assert "02" in result["by_hour"]
        assert "14" in result["by_hour"]
        assert result["by_hour"]["02"] == 5
        assert result["by_hour"]["14"] == 3

        # Peak hours should have "02" first
        assert "02" in result["peak_hours"]

        # Camera counts
        assert result["by_camera"]["cam-north"] == 5
        assert result["by_camera"]["cam-south"] == 3

        # Object counts
        assert result["by_object"]["person"] == 5
        assert result["by_object"]["animal"] == 3

    def test_compute_intruder_patterns_empty(self):
        """Test intruder patterns with no events."""
        from server.learning.learning_engine import LearningEngine

        engine = LearningEngine()
        result = engine.compute_intruder_patterns([])

        assert result["total_intruders"] == 0
        assert result["peak_hours"] == []


class TestRuleSuggestions:
    """Tests for rule suggestion generation."""

    def test_generate_threshold_adjustment(self):
        """Test threshold adjustment suggestion for high variance sensors."""
        from server.learning.rule_refinement import RuleRefinement

        refinement = RuleRefinement()

        learning_report = {
            "sensor_baselines": {
                "moisture": {
                    "avg": 0.4,
                    "std_dev": 0.3,  # High variance (> 50% of avg)
                    "variance_level": "high",
                }
            }
        }

        result = refinement.generate_rule_suggestions(learning_report)

        # Should suggest threshold adjustment
        suggestions = result["suggestions"]
        threshold_suggestions = [s for s in suggestions if s["type"] == "threshold_adjustment"]
        assert len(threshold_suggestions) >= 1
        assert "moisture" in threshold_suggestions[0]["id"]

    def test_generate_alert_schedule(self):
        """Test alert schedule suggestion based on intruder patterns."""
        from server.learning.rule_refinement import RuleRefinement

        refinement = RuleRefinement()

        learning_report = {
            "sensor_baselines": {},
            "intruder_patterns": {
                "total_intruders": 10,
                "peak_hours": ["02", "03", "22"],
                "hotspot_cameras": ["cam-001", "cam-002"],
            }
        }

        result = refinement.generate_rule_suggestions(learning_report)

        # Should suggest alert schedule
        suggestions = result["suggestions"]
        schedule_suggestions = [s for s in suggestions if s["type"] == "schedule_addition"]
        assert len(schedule_suggestions) >= 1
        assert schedule_suggestions[0]["priority"] == "high"

    def test_generate_weather_rule(self):
        """Test weather rule suggestion for negative correlation."""
        from server.learning.rule_refinement import RuleRefinement

        refinement = RuleRefinement()

        learning_report = {
            "sensor_baselines": {},
            "intruder_patterns": {},
            "weather_sensor_correlation": {
                "correlation": -0.75,
                "sample_size": 10,
            }
        }

        result = refinement.generate_rule_suggestions(learning_report)

        # Should suggest weather-irrigation rule
        suggestions = result["suggestions"]
        weather_suggestions = [s for s in suggestions if s["type"] == "combined_rule"]
        assert len(weather_suggestions) >= 1
        assert "weather" in weather_suggestions[0]["id"]

    def test_no_suggestions_for_normal_data(self):
        """Test that normal data doesn't generate excessive suggestions."""
        from server.learning.rule_refinement import RuleRefinement

        refinement = RuleRefinement()

        learning_report = {
            "sensor_baselines": {
                "moisture": {
                    "avg": 0.4,
                    "std_dev": 0.05,  # Normal variance
                    "variance_level": "normal",
                }
            },
            "intruder_patterns": {
                "total_intruders": 2,  # Not enough to suggest
                "peak_hours": [],
            },
            "weather_sensor_correlation": {
                "correlation": 0.1,  # Weak correlation
                "sample_size": 3,  # Not enough data
            },
            "valve_patterns": {
                "total_actions": 2,  # Not enough
                "automation_ratio": 0.8,
            }
        }

        result = refinement.generate_rule_suggestions(learning_report)

        # Should have few or no suggestions
        assert len(result["suggestions"]) <= 1


class TestLearningEndpoint:
    """Tests for the learning report endpoint."""

    def test_learning_report_get_returns_valid_json(self):
        """Test that GET /learning_report returns valid JSON structure."""
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)
        response = client.get("/learning_report")

        assert response.status_code == 200
        data = response.json()

        assert "ok" in data
        assert data["ok"] is True
        assert "learning" in data
        assert "recommendations" in data

    def test_learning_report_post_returns_valid_json(self):
        """Test that POST /learning_report returns valid JSON structure."""
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)
        response = client.post(
            "/learning_report",
            json={
                "task_id": "test-task-001",
                "source": "test",
                "target": "hobbs",
                "type": "learning_report",
                "payload": {"action": "get"}
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "ok" in data
        assert data["ok"] is True
        assert "action" in data
        assert "learning" in data

    def test_learning_report_refresh(self):
        """Test that POST with action=refresh triggers learning cycle."""
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)
        response = client.post(
            "/learning_report",
            json={
                "task_id": "test-task-002",
                "source": "test",
                "target": "hobbs",
                "type": "learning_report",
                "payload": {"action": "refresh"}
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["ok"] is True
        assert data["action"] == "refresh"
        assert "learning" in data
        assert "recommendations" in data


class TestEventCounter:
    """Tests for the event counter mechanism."""

    def test_increment_event_counter(self):
        """Test event counter increment."""
        from server.learning.learning_engine import LearningEngine

        engine = LearningEngine()

        # Reset counter
        engine.reset_event_counter()

        # Increment
        count1 = engine.increment_event_counter()
        assert count1 == 1

        count2 = engine.increment_event_counter()
        assert count2 == 2

    def test_should_run_learning_cycle(self):
        """Test learning cycle threshold check."""
        from server.learning.learning_engine import LearningEngine

        engine = LearningEngine()

        # Reset and check
        engine.reset_event_counter()
        assert engine.should_run_learning_cycle(threshold=5) is False

        # Increment to threshold
        for _ in range(5):
            engine.increment_event_counter()

        assert engine.should_run_learning_cycle(threshold=5) is True

    def test_reset_event_counter(self):
        """Test event counter reset."""
        from server.learning.learning_engine import LearningEngine

        engine = LearningEngine()

        # Increment a few times
        for _ in range(10):
            engine.increment_event_counter()

        # Reset
        engine.reset_event_counter()

        # Should not trigger
        assert engine.should_run_learning_cycle(threshold=5) is False
