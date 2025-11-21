"""
Rule Engine for Hobbs Agent automation.

Evaluates rules against sensor data and weather conditions
to trigger automated actions.
"""

import json
import operator
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime

from config.settings import settings, logger


# Operator mapping for rule evaluation
OPERATORS = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}


class RuleEngine:
    """
    Evaluates automation rules against sensor data and conditions.

    Rules are loaded from config/automation_rules.json and evaluated
    when sensor data is received or on scheduled checks.
    """

    def __init__(self):
        """Initialize the rule engine."""
        self.rules_path = settings.BASE_DIR / "config" / "automation_rules.json"
        self.rules: List[Dict[str, Any]] = []
        self._load_rules()

    def _load_rules(self) -> None:
        """Load rules from the configuration file."""
        try:
            if self.rules_path.exists():
                with open(self.rules_path, "r") as f:
                    config = json.load(f)
                    self.rules = config.get("rules", [])
                logger.info(f"Loaded {len(self.rules)} automation rules")
            else:
                logger.warning(f"Rules file not found: {self.rules_path}")
                self.rules = []
        except Exception as e:
            logger.error(f"Failed to load rules: {e}")
            self.rules = []

    def reload_rules(self) -> int:
        """
        Reload rules from configuration file.

        Returns:
            Number of rules loaded
        """
        self._load_rules()
        return len(self.rules)

    def get_rules(self) -> List[Dict[str, Any]]:
        """Get all loaded rules."""
        return self.rules.copy()

    def get_rule_by_id(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific rule by ID."""
        for rule in self.rules:
            if rule.get("id") == rule_id:
                return rule.copy()
        return None

    def evaluate_sensor_rules(
        self,
        sensor_type: str,
        sensor_value: float,
        weather_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluate rules triggered by sensor data.

        Args:
            sensor_type: Type of sensor (e.g., "moisture", "temperature")
            sensor_value: Current sensor reading
            weather_context: Optional weather data for condition checks

        Returns:
            List of triggered actions
        """
        triggered_actions = []

        for rule in self.rules:
            trigger = rule.get("trigger", {})

            # Check if rule applies to this sensor type
            if trigger.get("sensor_type") != sensor_type:
                continue

            # Evaluate the trigger condition
            op_str = trigger.get("operator")
            threshold = trigger.get("value")

            if op_str not in OPERATORS or threshold is None:
                continue

            op_func = OPERATORS[op_str]
            if not op_func(sensor_value, threshold):
                continue

            # Check additional conditions (e.g., weather)
            condition = rule.get("condition", {})
            if not self._check_conditions(condition, weather_context):
                continue

            # Rule triggered - collect action
            action = rule.get("action", {})
            if action:
                triggered_actions.append({
                    "rule_id": rule.get("id"),
                    "action": action,
                    "trigger_context": {
                        "sensor_type": sensor_type,
                        "sensor_value": sensor_value,
                        "operator": op_str,
                        "threshold": threshold,
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                })

        return triggered_actions

    def evaluate_event_rules(
        self,
        event_type: str,
        event_payload: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluate rules triggered by events.

        Args:
            event_type: Type of event (e.g., "hobbs.weather.alert")
            event_payload: Optional event payload data

        Returns:
            List of triggered actions
        """
        triggered_actions = []

        for rule in self.rules:
            trigger = rule.get("trigger", {})

            # Check if rule is triggered by this event
            if trigger.get("event") != event_type:
                continue

            # Event rules don't have value comparisons, just event matching
            action = rule.get("action", {})
            if action:
                triggered_actions.append({
                    "rule_id": rule.get("id"),
                    "action": action,
                    "trigger_context": {
                        "event": event_type,
                        "payload": event_payload,
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                })

        return triggered_actions

    def _check_conditions(
        self,
        condition: Dict[str, Any],
        weather_context: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Check if additional conditions are met.

        Args:
            condition: Condition specification from rule
            weather_context: Current weather data

        Returns:
            True if all conditions are met
        """
        if not condition:
            return True

        # Check weather condition
        weather_cond = condition.get("weather")
        if weather_cond:
            if not self._check_weather_condition(weather_cond, weather_context):
                return False

        return True

    def _check_weather_condition(
        self,
        weather_cond: str,
        weather_context: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Check a weather-based condition.

        Args:
            weather_cond: Condition string (e.g., "no_freeze_soon")
            weather_context: Current weather data

        Returns:
            True if condition is met
        """
        if weather_context is None:
            # No weather data - assume condition is met
            # (fail open for automation)
            return True

        if weather_cond == "no_freeze_soon":
            # Check if any forecast shows freezing
            forecasts = weather_context.get("forecasts", [])
            for forecast in forecasts[:24]:  # Check next 24 hours
                temp = forecast.get("temperature_2m")
                if temp is not None and temp <= 0:
                    return False
            return True

        if weather_cond == "no_rain_soon":
            forecasts = weather_context.get("forecasts", [])
            for forecast in forecasts[:6]:  # Check next 6 hours
                precip = forecast.get("precipitation", 0)
                if precip > 0:
                    return False
            return True

        # Unknown condition - default to True
        return True


# Singleton instance
rule_engine = RuleEngine()
