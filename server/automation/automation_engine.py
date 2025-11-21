"""
Automation Engine for Hobbs Agent.

Coordinates rule evaluation, scheduling, and anomaly detection
to drive automated control actions.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

from config.settings import settings, logger
from server.automation.rule_engine import rule_engine
from server.automation.schedule_engine import schedule_engine
from server.automation.anomaly_engine import anomaly_engine


class AutomationEngine:
    """
    Main automation coordinator for Hobbs Agent.

    Integrates rule evaluation, scheduling, and anomaly detection
    to determine and execute automated actions.
    """

    def __init__(self):
        """Initialize the automation engine."""
        self.history_path = Path.home() / "Desktop" / "Engineering" / "Hobbs" / "data" / "automation"
        self.history_file = self.history_path / "automation_history.jsonl"
        self._ensure_paths()
        self._action_count = 0
        logger.info("AutomationEngine initialized")

    def _ensure_paths(self) -> None:
        """Ensure required directories exist."""
        self.history_path.mkdir(parents=True, exist_ok=True)

    def process_sensor_data(
        self,
        sensor_id: str,
        sensor_type: str,
        value: float,
        weather_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process incoming sensor data through automation.

        Args:
            sensor_id: Identifier of the sensor
            sensor_type: Type of sensor (e.g., "moisture", "temperature")
            value: Sensor reading value
            weather_context: Optional current weather data

        Returns:
            Processing result with any triggered actions
        """
        result = {
            "sensor_id": sensor_id,
            "sensor_type": sensor_type,
            "value": value,
            "triggered_actions": [],
            "anomaly_check": None,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        # Check for anomalies (stub)
        anomaly_result = anomaly_engine.check_sensor_anomaly(
            sensor_id=sensor_id,
            sensor_type=sensor_type,
            value=value
        )
        result["anomaly_check"] = anomaly_result

        # Evaluate rules
        triggered_actions = rule_engine.evaluate_sensor_rules(
            sensor_type=sensor_type,
            sensor_value=value,
            weather_context=weather_context
        )

        if triggered_actions:
            result["triggered_actions"] = triggered_actions
            self._record_actions(triggered_actions, "sensor_trigger")

        return result

    def process_event(
        self,
        event_type: str,
        event_payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process an event through automation rules.

        Args:
            event_type: Type of event (e.g., "hobbs.weather.alert")
            event_payload: Optional event data

        Returns:
            Processing result with any triggered actions
        """
        result = {
            "event_type": event_type,
            "triggered_actions": [],
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        # Evaluate event-based rules
        triggered_actions = rule_engine.evaluate_event_rules(
            event_type=event_type,
            event_payload=event_payload
        )

        if triggered_actions:
            result["triggered_actions"] = triggered_actions
            self._record_actions(triggered_actions, "event_trigger")

        return result

    def process_weather_update(
        self,
        weather_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process weather update and check for alerts.

        Args:
            weather_data: Weather forecast data

        Returns:
            Processing result with any triggered actions
        """
        result = {
            "weather_processed": True,
            "alerts": [],
            "triggered_actions": [],
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        # Check for weather alerts
        alerts = self._check_weather_alerts(weather_data)
        result["alerts"] = alerts

        # Process each alert as an event
        for alert in alerts:
            event_result = self.process_event(
                event_type="hobbs.weather.alert",
                event_payload=alert
            )
            result["triggered_actions"].extend(event_result.get("triggered_actions", []))

        return result

    def _check_weather_alerts(self, weather_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check weather data for alert conditions.

        Args:
            weather_data: Weather forecast data

        Returns:
            List of weather alerts
        """
        alerts = []
        forecasts = weather_data.get("forecasts", [])

        for forecast in forecasts[:24]:  # Check next 24 hours
            # Check for freezing
            temp = forecast.get("temperature_2m")
            if temp is not None and temp <= 0:
                alerts.append({
                    "type": "freeze_warning",
                    "temperature": temp,
                    "time": forecast.get("time"),
                    "severity": "high" if temp < -5 else "medium",
                })
                break  # One freeze warning is enough

            # Check for heavy precipitation
            precip = forecast.get("precipitation", 0)
            if precip > 10:  # mm/hour
                alerts.append({
                    "type": "heavy_precipitation",
                    "precipitation": precip,
                    "time": forecast.get("time"),
                    "severity": "medium",
                })

        return alerts

    def run_scheduled_check(self, current_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Run scheduled automation tasks.

        Args:
            current_time: Time to check against (defaults to now)

        Returns:
            Result with executed tasks
        """
        due_tasks = schedule_engine.get_due_tasks(current_time)

        result = {
            "checked_at": datetime.utcnow().isoformat() + "Z",
            "due_tasks": len(due_tasks),
            "executed_tasks": [],
        }

        for task_info in due_tasks:
            schedule_id = task_info.get("schedule_id")
            task = task_info.get("task", {})

            # Execute the task
            execution_result = self._execute_scheduled_task(task)

            # Mark as executed
            schedule_engine.mark_executed(schedule_id)

            result["executed_tasks"].append({
                "schedule_id": schedule_id,
                "task": task,
                "result": execution_result,
            })

        if result["executed_tasks"]:
            self._record_actions(
                [{"schedule": t} for t in result["executed_tasks"]],
                "schedule_trigger"
            )

        return result

    def _execute_scheduled_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a scheduled task.

        Args:
            task: Task definition

        Returns:
            Execution result
        """
        task_type = task.get("type")
        payload = task.get("payload", {})

        if task_type == "automation_check":
            # Run rule evaluation check
            rule_group = payload.get("rule_group", "all")
            return {
                "executed": True,
                "task_type": task_type,
                "rule_group": rule_group,
                "message": f"Automation check completed for rule group: {rule_group}",
            }

        return {
            "executed": False,
            "task_type": task_type,
            "message": f"Unknown task type: {task_type}",
        }

    def _record_actions(self, actions: List[Dict[str, Any]], trigger_type: str) -> None:
        """
        Record triggered actions to history.

        Args:
            actions: List of triggered actions
            trigger_type: Type of trigger (sensor, event, schedule)
        """
        try:
            with open(self.history_file, "a") as f:
                for action in actions:
                    record = {
                        "trigger_type": trigger_type,
                        "action": action,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    }
                    f.write(json.dumps(record) + "\n")
                    self._action_count += 1
        except Exception as e:
            logger.error(f"Failed to record automation action: {e}")

    def get_pending_actions(self) -> List[Dict[str, Any]]:
        """
        Get actions that need to be executed.

        Returns:
            List of pending actions (valve commands, events to emit)
        """
        # For now, actions are processed inline
        # This could be expanded to queue actions for batch processing
        return []

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent automation history.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of recent automation actions
        """
        history = []
        try:
            if self.history_file.exists():
                with open(self.history_file, "r") as f:
                    lines = f.readlines()
                    for line in lines[-limit:]:
                        if line.strip():
                            history.append(json.loads(line))
        except Exception as e:
            logger.error(f"Failed to read automation history: {e}")

        return history

    def get_history_count(self) -> int:
        """Get the number of entries in automation history."""
        try:
            if self.history_file.exists():
                with open(self.history_file, "r") as f:
                    return sum(1 for line in f if line.strip())
        except Exception:
            pass
        return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get automation engine statistics."""
        return {
            "rules_loaded": len(rule_engine.get_rules()),
            "schedules_loaded": len(schedule_engine.get_schedule()),
            "anomaly_detection_enabled": anomaly_engine.is_enabled(),
            "action_count": self._action_count,
            "history_count": self.get_history_count(),
        }

    def reload_config(self) -> Dict[str, int]:
        """
        Reload all automation configuration.

        Returns:
            Count of loaded items per config type
        """
        return {
            "rules": rule_engine.reload_rules(),
            "schedules": schedule_engine.reload_schedule(),
        }


# Singleton instance
automation_engine = AutomationEngine()
