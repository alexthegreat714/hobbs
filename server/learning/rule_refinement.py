"""
Rule Refinement Engine for Hobbs Agent.

Proposes improvements to automation rules based on learned patterns.
"""

import json
from typing import Any, Dict, List
from datetime import datetime
from pathlib import Path

from config.settings import logger


class RuleRefinement:
    """
    Rule refinement engine that suggests automation improvements.

    Analyzes learning reports to propose:
    - Threshold adjustments
    - New rules based on observed patterns
    - Schedule optimizations
    """

    def __init__(self):
        """Initialize the rule refinement engine."""
        self.data_base = Path.home() / "Desktop" / "Engineering" / "Hobbs" / "data"
        self.learning_dir = self.data_base / "learning"
        self.recommendations_file = self.learning_dir / "recommendations.jsonl"
        self._ensure_paths()

    def _ensure_paths(self) -> None:
        """Ensure required directories exist."""
        self.learning_dir.mkdir(parents=True, exist_ok=True)

    def generate_rule_suggestions(self, learning_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate rule suggestions based on learning report.

        Args:
            learning_report: Output from learning_engine.run_full_learning_cycle()

        Returns:
            Dictionary with suggestions list
        """
        suggestions = []

        # A. Check sensor baseline variance
        sensor_suggestions = self._suggest_threshold_adjustments(
            learning_report.get("sensor_baselines", {})
        )
        suggestions.extend(sensor_suggestions)

        # B. Check intruder patterns for scheduling
        intruder_suggestions = self._suggest_alert_schedules(
            learning_report.get("intruder_patterns", {})
        )
        suggestions.extend(intruder_suggestions)

        # C. Check for frequently paired events
        valve_suggestions = self._suggest_automation_rules(
            learning_report.get("valve_patterns", {}),
            learning_report.get("sensor_baselines", {})
        )
        suggestions.extend(valve_suggestions)

        # D. Check weather correlation for combined rules
        weather_suggestions = self._suggest_weather_rules(
            learning_report.get("weather_sensor_correlation", {})
        )
        suggestions.extend(weather_suggestions)

        # Save suggestions to file
        result = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "suggestions": suggestions,
            "count": len(suggestions),
        }

        self._save_suggestions(result)

        return result

    def _suggest_threshold_adjustments(self, sensor_baselines: Dict[str, Any]) -> List[Dict]:
        """
        Suggest threshold adjustments based on sensor variance.

        High variance suggests thresholds may need tightening.
        """
        suggestions = []

        for sensor_type, stats in sensor_baselines.items():
            if stats.get("variance_level") == "high":
                avg = stats.get("avg", 0)
                std = stats.get("std_dev", 0)

                # Suggest new threshold at mean - 1 std
                new_threshold = round(avg - std, 3)
                if new_threshold > 0:
                    suggestions.append({
                        "id": f"suggest_adjust_{sensor_type}_threshold",
                        "type": "threshold_adjustment",
                        "priority": "medium",
                        "description": (
                            f"Sensor '{sensor_type}' has high variance (std={std:.3f}). "
                            f"Suggested new threshold: {new_threshold}"
                        ),
                        "proposed_rule": {
                            "id": f"{sensor_type}_adjusted_threshold",
                            "trigger": {
                                "sensor_type": sensor_type,
                                "operator": "<",
                                "value": new_threshold
                            },
                            "action": {
                                "note": "Adjust existing rule threshold"
                            }
                        },
                        "confidence": 0.7,
                    })

        return suggestions

    def _suggest_alert_schedules(self, intruder_patterns: Dict[str, Any]) -> List[Dict]:
        """
        Suggest high-alert windows based on intruder patterns.

        If intruders consistently appear at certain hours, suggest scheduled alerts.
        """
        suggestions = []
        peak_hours = intruder_patterns.get("peak_hours", [])
        total_intruders = intruder_patterns.get("total_intruders", 0)

        if total_intruders >= 5 and len(peak_hours) >= 1:
            # Format peak hours for display
            hour_ranges = []
            for h in peak_hours[:3]:
                hour_int = int(h)
                hour_ranges.append(f"{hour_int:02d}:00-{(hour_int+1)%24:02d}:00")

            suggestions.append({
                "id": "suggest_intruder_alert_schedule",
                "type": "schedule_addition",
                "priority": "high",
                "description": (
                    f"Intruder activity concentrates at hours: {', '.join(hour_ranges)}. "
                    f"Suggested: Enable high-alert mode during these windows."
                ),
                "proposed_rule": {
                    "id": "high_alert_window",
                    "schedule": [{"time": f"{h}:00"} for h in peak_hours],
                    "action": {
                        "mode": "high_alert",
                        "cameras": intruder_patterns.get("hotspot_cameras", [])
                    }
                },
                "confidence": 0.8 if total_intruders >= 10 else 0.6,
            })

        return suggestions

    def _suggest_automation_rules(
        self,
        valve_patterns: Dict[str, Any],
        sensor_baselines: Dict[str, Any]
    ) -> List[Dict]:
        """
        Suggest automation rules based on observed patterns.

        If moisture-low → irrigation-open happens frequently,
        suggest formalizing into an automation rule.
        """
        suggestions = []

        # Check if valve automation ratio is low but patterns suggest it should be higher
        auto_ratio = valve_patterns.get("automation_ratio", 0)
        total_actions = valve_patterns.get("total_actions", 0)

        if total_actions >= 10 and auto_ratio < 0.5:
            # Many manual actions - suggest more automation
            per_valve = valve_patterns.get("per_valve", {})

            for valve_id, stats in per_valve.items():
                if stats.get("total_actions", 0) >= 5:
                    if "irrigation" in valve_id.lower():
                        # Check if moisture sensor exists
                        if "moisture" in sensor_baselines:
                            moisture_stats = sensor_baselines["moisture"]
                            threshold = round(moisture_stats.get("avg", 0.15) - moisture_stats.get("std_dev", 0.05), 3)

                            suggestions.append({
                                "id": f"suggest_automate_{valve_id}",
                                "type": "new_automation_rule",
                                "priority": "medium",
                                "description": (
                                    f"Valve '{valve_id}' has many manual actions. "
                                    f"Suggested: Automate based on moisture sensor (threshold: {threshold})"
                                ),
                                "proposed_rule": {
                                    "id": f"auto_{valve_id}_moisture",
                                    "trigger": {
                                        "sensor_type": "moisture",
                                        "operator": "<",
                                        "value": threshold
                                    },
                                    "action": {
                                        "valve_id": valve_id,
                                        "command": "open",
                                        "value": 1.0
                                    }
                                },
                                "confidence": 0.65,
                            })

        return suggestions

    def _suggest_weather_rules(self, weather_correlation: Dict[str, Any]) -> List[Dict]:
        """
        Suggest combined weather-irrigation rules based on correlation.

        Strong negative correlation between temp and moisture
        suggests irrigation should increase with temperature.
        """
        suggestions = []
        corr = weather_correlation.get("correlation", 0)
        sample_size = weather_correlation.get("sample_size", 0)

        if sample_size >= 5:
            if corr < -0.5:
                # Negative correlation: higher temp = lower moisture
                suggestions.append({
                    "id": "suggest_weather_irrigation_rule",
                    "type": "combined_rule",
                    "priority": "medium",
                    "description": (
                        f"Strong negative correlation ({corr:.2f}) between temperature and moisture. "
                        f"Suggested: Increase irrigation during hot weather."
                    ),
                    "proposed_rule": {
                        "id": "hot_weather_irrigation",
                        "trigger": {
                            "event": "hobbs.weather.high_temp",
                            "temperature_threshold": 30
                        },
                        "condition": {
                            "moisture": {"operator": "<", "value": 0.3}
                        },
                        "action": {
                            "valve_id": "main_irrigation",
                            "command": "open"
                        }
                    },
                    "confidence": 0.7,
                })

        return suggestions

    def _save_suggestions(self, result: Dict[str, Any]) -> None:
        """Append suggestions to recommendations file."""
        try:
            with open(self.recommendations_file, "a") as f:
                f.write(json.dumps(result) + "\n")
        except Exception as e:
            logger.error(f"Failed to save recommendations: {e}")

    def load_recommendations(self, limit: int = 10) -> List[Dict]:
        """
        Load recent recommendations.

        Args:
            limit: Maximum number of recommendation sets to return

        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        if not self.recommendations_file.exists():
            return recommendations

        try:
            with open(self.recommendations_file, "r") as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    if line.strip():
                        recommendations.append(json.loads(line))
        except Exception as e:
            logger.error(f"Failed to load recommendations: {e}")

        return recommendations


# Singleton instance
rule_refinement = RuleRefinement()
