"""
Anomaly Detection Engine for Hobbs Agent automation.

Phase 8: Enhanced with statistical anomaly detection based on
learned baselines and patterns.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

from config.settings import logger
from server.learning.patterns import z_score, mean, std_dev


class AnomalyEngine:
    """
    Detects anomalies in sensor data and system behavior.

    Uses learned baselines to detect statistical anomalies:
    - Sensor values outside 3 standard deviations
    - Weather changes exceeding thresholds
    - Intruder events at unusual times
    """

    # Anomaly thresholds
    SENSOR_Z_THRESHOLD = 3.0  # Standard deviations for sensor anomaly
    WEATHER_TEMP_CHANGE_THRESHOLD = 10.0  # Degrees for sudden change
    INTRUDER_UNUSUAL_THRESHOLD = 0.1  # 10% of total for "unusual" hour

    def __init__(self):
        """Initialize the anomaly engine."""
        self._enabled = True  # Now enabled by default
        self._detection_count = 0
        self._anomaly_count = 0
        self._baselines: Dict[str, Any] = {}
        self._intruder_histogram: Dict[str, int] = {}

        self.data_base = Path.home() / "Desktop" / "Engineering" / "Hobbs" / "data"
        self.learning_cache = self.data_base / "learning" / "learning_cache.json"

        self._load_baselines()
        logger.info("AnomalyEngine initialized (Phase 8 - statistical detection)")

    def _load_baselines(self) -> None:
        """Load learned baselines from learning cache."""
        if not self.learning_cache.exists():
            return

        try:
            with open(self.learning_cache, "r") as f:
                cache = json.load(f)
                self._baselines = cache.get("sensor_baselines", {})

                # Extract intruder histogram
                intruder_patterns = cache.get("intruder_patterns", {})
                self._intruder_histogram = intruder_patterns.get("by_hour", {})

            logger.info(f"Loaded baselines for {len(self._baselines)} sensor types")
        except Exception as e:
            logger.error(f"Failed to load baselines: {e}")

    def reload_baselines(self) -> None:
        """Reload baselines from cache."""
        self._load_baselines()

    def is_enabled(self) -> bool:
        """Check if anomaly detection is enabled."""
        return self._enabled

    def enable(self) -> None:
        """Enable anomaly detection."""
        self._enabled = True
        logger.info("AnomalyEngine enabled")

    def disable(self) -> None:
        """Disable anomaly detection."""
        self._enabled = False
        logger.info("AnomalyEngine disabled")

    def check_sensor_anomaly(
        self,
        sensor_id: str,
        sensor_type: str,
        value: float,
        historical_values: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Check if a sensor reading is anomalous.

        Uses z-score against learned baseline or provided historical values.
        Value > mean + 3*std_dev or < mean - 3*std_dev → anomaly

        Args:
            sensor_id: Identifier of the sensor
            sensor_type: Type of sensor
            value: Current sensor reading
            historical_values: Recent historical values for comparison

        Returns:
            Anomaly detection result
        """
        self._detection_count += 1

        if not self._enabled:
            return self._no_anomaly_result(sensor_id, sensor_type, value, "disabled")

        # Get baseline for this sensor type
        baseline = self._baselines.get(sensor_type, {})
        baseline_mean = baseline.get("avg")
        baseline_std = baseline.get("std_dev")

        # Fall back to historical values if no baseline
        if baseline_mean is None and historical_values:
            baseline_mean = mean(historical_values)
            baseline_std = std_dev(historical_values)

        # Can't detect anomaly without baseline
        if baseline_mean is None or baseline_std is None:
            return self._no_anomaly_result(
                sensor_id, sensor_type, value,
                "no baseline available"
            )

        # Calculate z-score
        z = z_score(value, baseline_mean, baseline_std)
        abs_z = abs(z)

        is_anomaly = abs_z > self.SENSOR_Z_THRESHOLD

        if is_anomaly:
            self._anomaly_count += 1
            anomaly_type = "high_value" if z > 0 else "low_value"
            return {
                "anomaly": True,
                "score": min(abs_z / 5.0, 1.0),  # Normalize to 0-1
                "reason": f"Value {value} is {abs_z:.2f} standard deviations from mean ({baseline_mean:.3f})",
                "anomaly_type": anomaly_type,
                "z_score": round(z, 3),
                "baseline_mean": round(baseline_mean, 3),
                "baseline_std": round(baseline_std, 3),
                "sensor_id": sensor_id,
                "sensor_type": sensor_type,
                "value": value,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

        return self._no_anomaly_result(sensor_id, sensor_type, value, "within normal range")

    def check_weather_anomaly(
        self,
        current_temp: float,
        previous_temp: Optional[float] = None,
        forecast_temps: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Check for weather anomalies.

        Detects sudden temperature changes exceeding threshold.

        Args:
            current_temp: Current temperature
            previous_temp: Previous temperature reading
            forecast_temps: List of forecast temperatures

        Returns:
            Anomaly detection result
        """
        self._detection_count += 1

        if not self._enabled:
            return {
                "anomaly": False,
                "score": 0.0,
                "reason": "detection disabled",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

        # Check for sudden temperature change
        if previous_temp is not None:
            temp_change = abs(current_temp - previous_temp)
            if temp_change > self.WEATHER_TEMP_CHANGE_THRESHOLD:
                self._anomaly_count += 1
                return {
                    "anomaly": True,
                    "score": min(temp_change / 20.0, 1.0),
                    "reason": f"Sudden temperature change of {temp_change:.1f}°C detected",
                    "anomaly_type": "sudden_temp_change",
                    "current_temp": current_temp,
                    "previous_temp": previous_temp,
                    "change": temp_change,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }

        # Check for extreme forecast temperatures
        if forecast_temps:
            forecast_min = min(forecast_temps)
            forecast_max = max(forecast_temps)
            forecast_range = forecast_max - forecast_min

            if forecast_range > 20:  # Large temperature swing forecasted
                self._anomaly_count += 1
                return {
                    "anomaly": True,
                    "score": min(forecast_range / 40.0, 1.0),
                    "reason": f"Large temperature swing forecasted: {forecast_range:.1f}°C",
                    "anomaly_type": "extreme_forecast",
                    "forecast_min": forecast_min,
                    "forecast_max": forecast_max,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }

        return {
            "anomaly": False,
            "score": 0.0,
            "reason": "weather within normal parameters",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    def check_intruder_anomaly(
        self,
        camera_id: str,
        detection_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Check if intruder detection is at an unusual time.

        Based on learned hourly histogram of intruder activity.

        Args:
            camera_id: Camera that detected the intruder
            detection_time: Time of detection (defaults to now)

        Returns:
            Anomaly detection result
        """
        self._detection_count += 1

        if not self._enabled:
            return {
                "anomaly": False,
                "score": 0.0,
                "reason": "detection disabled",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

        if detection_time is None:
            detection_time = datetime.utcnow()

        hour = detection_time.strftime("%H")

        # Check against histogram
        if not self._intruder_histogram:
            return {
                "anomaly": False,
                "score": 0.0,
                "reason": "no intruder baseline available",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

        total_intruders = sum(self._intruder_histogram.values())
        hour_count = self._intruder_histogram.get(hour, 0)

        if total_intruders == 0:
            return {
                "anomaly": False,
                "score": 0.0,
                "reason": "no intruder history",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

        # Hour is unusual if it has < 10% of typical activity
        hour_ratio = hour_count / total_intruders

        if hour_ratio < self.INTRUDER_UNUSUAL_THRESHOLD:
            self._anomaly_count += 1
            return {
                "anomaly": True,
                "score": 1.0 - hour_ratio,
                "reason": f"Intruder detected at unusual hour {hour}:00 (only {hour_ratio*100:.1f}% of historical activity)",
                "anomaly_type": "unusual_time",
                "camera_id": camera_id,
                "hour": hour,
                "hour_ratio": round(hour_ratio, 4),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

        return {
            "anomaly": False,
            "score": 0.0,
            "reason": f"Intruder at typical hour {hour}:00",
            "camera_id": camera_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    def check_pattern_anomaly(
        self,
        pattern_type: str,
        data_points: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check for anomalous patterns in time-series data.

        Args:
            pattern_type: Type of pattern to check
            data_points: List of data points with timestamps

        Returns:
            Anomaly detection result
        """
        self._detection_count += 1

        if not self._enabled or len(data_points) < 3:
            return {
                "anomaly": False,
                "score": 0.0,
                "reason": "insufficient data for pattern analysis",
                "pattern_type": pattern_type,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

        # Extract values from data points
        values = []
        for dp in data_points:
            v = dp.get("value")
            if isinstance(v, (int, float)):
                values.append(float(v))

        if len(values) < 3:
            return {
                "anomaly": False,
                "score": 0.0,
                "reason": "insufficient numeric values",
                "pattern_type": pattern_type,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

        # Check for sudden spike in last value
        last_value = values[-1]
        prev_mean = mean(values[:-1])
        prev_std = std_dev(values[:-1])

        if prev_std > 0:
            z = z_score(last_value, prev_mean, prev_std)
            if abs(z) > 3:
                self._anomaly_count += 1
                return {
                    "anomaly": True,
                    "score": min(abs(z) / 5.0, 1.0),
                    "reason": f"Sudden spike detected in {pattern_type}: {abs(z):.2f} std devs from recent mean",
                    "anomaly_type": "pattern_spike",
                    "pattern_type": pattern_type,
                    "z_score": round(z, 3),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }

        return {
            "anomaly": False,
            "score": 0.0,
            "reason": "pattern within normal variation",
            "pattern_type": pattern_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    def check_system_anomaly(
        self,
        system_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check for anomalies in overall system state.

        Args:
            system_state: Current system state dictionary

        Returns:
            Anomaly detection result
        """
        self._detection_count += 1

        if not self._enabled:
            return {
                "anomaly": False,
                "score": 0.0,
                "reason": "detection disabled",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

        # Check for unusual valve states
        valves_open = system_state.get("valves_open", 0)
        total_valves = system_state.get("total_valves", 0)

        if total_valves > 0 and valves_open == total_valves:
            self._anomaly_count += 1
            return {
                "anomaly": True,
                "score": 0.7,
                "reason": f"All {total_valves} valves are open simultaneously",
                "anomaly_type": "all_valves_open",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

        return {
            "anomaly": False,
            "score": 0.0,
            "reason": "system state normal",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    def _no_anomaly_result(
        self,
        sensor_id: str,
        sensor_type: str,
        value: float,
        reason: str
    ) -> Dict[str, Any]:
        """Create a no-anomaly result."""
        return {
            "anomaly": False,
            "score": 0.0,
            "reason": reason,
            "sensor_id": sensor_id,
            "sensor_type": sensor_type,
            "value": value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get anomaly engine statistics."""
        return {
            "enabled": self._enabled,
            "detection_count": self._detection_count,
            "anomaly_count": self._anomaly_count,
            "baselines_loaded": len(self._baselines),
            "intruder_hours_tracked": len(self._intruder_histogram),
            "stub": False,  # No longer a stub
        }


# Singleton instance
anomaly_engine = AnomalyEngine()
