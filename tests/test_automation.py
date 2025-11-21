"""
Tests for Hobbs Agent automation engine.

Tests verify:
- Rule engine loads rules and evaluates correctly
- Schedule engine loads schedules and tracks execution
- Anomaly engine stub returns expected format
- Automation engine coordinates components correctly
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


class TestRuleEngine:
    """Tests for the rule engine."""

    def test_rule_engine_loads_rules(self):
        """Test that rule engine loads rules from config."""
        from server.automation.rule_engine import rule_engine
        rules = rule_engine.get_rules()
        assert isinstance(rules, list)
        assert len(rules) > 0

    def test_rule_engine_get_rule_by_id(self):
        """Test getting a specific rule by ID."""
        from server.automation.rule_engine import rule_engine
        rule = rule_engine.get_rule_by_id("irrigation_moisture_low")
        assert rule is not None
        assert rule["id"] == "irrigation_moisture_low"

    def test_rule_engine_get_nonexistent_rule(self):
        """Test getting a nonexistent rule returns None."""
        from server.automation.rule_engine import rule_engine
        rule = rule_engine.get_rule_by_id("nonexistent_rule")
        assert rule is None

    def test_rule_engine_evaluate_sensor_triggers(self):
        """Test that sensor rules are evaluated correctly."""
        from server.automation.rule_engine import rule_engine

        # Test moisture below threshold - should trigger
        actions = rule_engine.evaluate_sensor_rules(
            sensor_type="moisture",
            sensor_value=0.10,  # Below 0.15 threshold
            weather_context=None
        )
        assert len(actions) >= 1
        assert any(a["rule_id"] == "irrigation_moisture_low" for a in actions)

    def test_rule_engine_no_trigger_above_threshold(self):
        """Test that rules don't trigger when threshold not met."""
        from server.automation.rule_engine import rule_engine

        # Test moisture above threshold - should not trigger
        actions = rule_engine.evaluate_sensor_rules(
            sensor_type="moisture",
            sensor_value=0.50,  # Above 0.15 threshold
            weather_context=None
        )
        # Should not trigger irrigation_moisture_low
        assert not any(a["rule_id"] == "irrigation_moisture_low" for a in actions)

    def test_rule_engine_evaluate_event_rules(self):
        """Test that event-based rules are evaluated."""
        from server.automation.rule_engine import rule_engine

        actions = rule_engine.evaluate_event_rules(
            event_type="hobbs.weather.alert",
            event_payload={"type": "freeze_warning"}
        )
        assert len(actions) >= 1
        assert any(a["rule_id"] == "close_irrigation_after_weather_alert" for a in actions)

    def test_rule_engine_reload_rules(self):
        """Test that rules can be reloaded."""
        from server.automation.rule_engine import rule_engine
        count = rule_engine.reload_rules()
        assert count > 0


class TestScheduleEngine:
    """Tests for the schedule engine."""

    def test_schedule_engine_loads_schedule(self):
        """Test that schedule engine loads schedule from config."""
        from server.automation.schedule_engine import schedule_engine
        schedule = schedule_engine.get_schedule()
        assert isinstance(schedule, list)
        assert len(schedule) > 0

    def test_schedule_engine_get_schedule_by_id(self):
        """Test getting a specific schedule by ID."""
        from server.automation.schedule_engine import schedule_engine
        item = schedule_engine.get_schedule_by_id("midday_irrigation_check")
        assert item is not None
        assert item["id"] == "midday_irrigation_check"
        assert item["time"] == "12:00"

    def test_schedule_engine_get_due_tasks(self):
        """Test getting due tasks at a specific time."""
        from server.automation.schedule_engine import schedule_engine

        # Reset schedule tracking
        schedule_engine.reset_schedule()

        # Check at 14:00 - midday task should be due
        test_time = datetime(2024, 1, 15, 14, 0, 0)
        due_tasks = schedule_engine.get_due_tasks(test_time)

        # Midday (12:00) task should be due at 14:00
        assert any(t["schedule_id"] == "midday_irrigation_check" for t in due_tasks)

    def test_schedule_engine_mark_executed(self):
        """Test marking a schedule as executed."""
        from server.automation.schedule_engine import schedule_engine

        schedule_engine.reset_schedule()

        # First check - should find due tasks
        test_time = datetime(2024, 1, 15, 14, 0, 0)
        due_tasks_1 = schedule_engine.get_due_tasks(test_time)
        midday_due = any(t["schedule_id"] == "midday_irrigation_check" for t in due_tasks_1)

        if midday_due:
            # Mark as executed
            schedule_engine.mark_executed("midday_irrigation_check", test_time)

            # Check again - should not be due anymore today
            due_tasks_2 = schedule_engine.get_due_tasks(test_time)
            assert not any(t["schedule_id"] == "midday_irrigation_check" for t in due_tasks_2)

    def test_schedule_engine_reload_schedule(self):
        """Test that schedule can be reloaded."""
        from server.automation.schedule_engine import schedule_engine
        count = schedule_engine.reload_schedule()
        assert count > 0


class TestAnomalyEngine:
    """Tests for the anomaly detection engine stub."""

    def test_anomaly_engine_check_sensor(self):
        """Test sensor anomaly check returns expected format."""
        from server.automation.anomaly_engine import anomaly_engine

        result = anomaly_engine.check_sensor_anomaly(
            sensor_id="sensor-001",
            sensor_type="moisture",
            value=0.45
        )

        assert "is_anomaly" in result
        assert "confidence" in result
        assert "anomaly_type" in result
        assert "details" in result
        assert result["is_anomaly"] is False  # Stub always returns False
        assert result["details"]["stub"] is True

    def test_anomaly_engine_check_pattern(self):
        """Test pattern anomaly check returns expected format."""
        from server.automation.anomaly_engine import anomaly_engine

        result = anomaly_engine.check_pattern_anomaly(
            pattern_type="sensor_drift",
            data_points=[{"value": 0.1}, {"value": 0.2}]
        )

        assert "is_anomaly" in result
        assert result["is_anomaly"] is False
        assert result["details"]["stub"] is True

    def test_anomaly_engine_check_system(self):
        """Test system anomaly check returns expected format."""
        from server.automation.anomaly_engine import anomaly_engine

        result = anomaly_engine.check_system_anomaly({
            "valves_open": 2,
            "sensors_active": 5
        })

        assert "is_anomaly" in result
        assert result["is_anomaly"] is False

    def test_anomaly_engine_enable_disable(self):
        """Test enabling and disabling anomaly detection."""
        from server.automation.anomaly_engine import anomaly_engine

        anomaly_engine.disable()
        assert anomaly_engine.is_enabled() is False

        anomaly_engine.enable()
        assert anomaly_engine.is_enabled() is True

        # Cleanup - disable again
        anomaly_engine.disable()

    def test_anomaly_engine_stats(self):
        """Test getting anomaly engine stats."""
        from server.automation.anomaly_engine import anomaly_engine

        stats = anomaly_engine.get_stats()
        assert "enabled" in stats
        assert "detection_count" in stats
        assert "stub" in stats
        assert stats["stub"] is True


class TestAutomationEngine:
    """Tests for the main automation engine."""

    def test_automation_engine_process_sensor_data(self):
        """Test processing sensor data through automation."""
        from server.automation.automation_engine import automation_engine

        result = automation_engine.process_sensor_data(
            sensor_id="test-sensor-001",
            sensor_type="moisture",
            value=0.10  # Should trigger irrigation rule
        )

        assert "sensor_id" in result
        assert "sensor_type" in result
        assert "triggered_actions" in result
        assert "anomaly_check" in result
        assert "timestamp" in result

    def test_automation_engine_process_event(self):
        """Test processing event through automation."""
        from server.automation.automation_engine import automation_engine

        result = automation_engine.process_event(
            event_type="hobbs.weather.alert",
            event_payload={"type": "freeze_warning"}
        )

        assert "event_type" in result
        assert "triggered_actions" in result
        assert "timestamp" in result

    def test_automation_engine_process_weather_update(self):
        """Test processing weather update through automation."""
        from server.automation.automation_engine import automation_engine

        result = automation_engine.process_weather_update({
            "forecasts": [
                {"time": "2024-01-15T12:00", "temperature_2m": 15.0, "precipitation": 0},
                {"time": "2024-01-15T13:00", "temperature_2m": 16.0, "precipitation": 0},
            ]
        })

        assert "weather_processed" in result
        assert "alerts" in result
        assert "triggered_actions" in result
        assert result["weather_processed"] is True

    def test_automation_engine_weather_freeze_alert(self):
        """Test that freezing weather triggers alerts."""
        from server.automation.automation_engine import automation_engine

        result = automation_engine.process_weather_update({
            "forecasts": [
                {"time": "2024-01-15T12:00", "temperature_2m": -5.0, "precipitation": 0},
            ]
        })

        assert len(result["alerts"]) > 0
        assert any(a["type"] == "freeze_warning" for a in result["alerts"])

    def test_automation_engine_run_scheduled_check(self):
        """Test running scheduled automation check."""
        from server.automation.automation_engine import automation_engine
        from server.automation.schedule_engine import schedule_engine

        # Reset schedule
        schedule_engine.reset_schedule()

        # Run at a time when tasks are due
        test_time = datetime(2024, 1, 15, 14, 0, 0)
        result = automation_engine.run_scheduled_check(test_time)

        assert "checked_at" in result
        assert "due_tasks" in result
        assert "executed_tasks" in result

    def test_automation_engine_get_stats(self):
        """Test getting automation stats."""
        from server.automation.automation_engine import automation_engine

        stats = automation_engine.get_stats()

        assert "rules_loaded" in stats
        assert "schedules_loaded" in stats
        assert "anomaly_detection_enabled" in stats
        assert "action_count" in stats
        assert stats["rules_loaded"] > 0
        assert stats["schedules_loaded"] > 0

    def test_automation_engine_reload_config(self):
        """Test reloading automation configuration."""
        from server.automation.automation_engine import automation_engine

        result = automation_engine.reload_config()

        assert "rules" in result
        assert "schedules" in result
        assert result["rules"] > 0
        assert result["schedules"] > 0

    def test_automation_engine_get_history(self):
        """Test getting automation history."""
        from server.automation.automation_engine import automation_engine

        history = automation_engine.get_history(limit=10)
        assert isinstance(history, list)
