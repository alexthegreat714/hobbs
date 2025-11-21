"""
Learning Engine for Hobbs Agent.

Provides adaptive learning capabilities including:
- Rolling averages and baselines
- Trend detection
- Seasonality patterns
- Event frequency analysis
- Transition probabilities
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

from config.settings import settings, logger
from schemas.memory import MemoryEvent
from server.learning.patterns import (
    mean,
    std_dev,
    correlation,
    detect_peak_hours,
    compute_statistics,
    detect_trend,
)


class LearningEngine:
    """
    Adaptive learning engine for Hobbs Agent.

    Analyzes historical data to compute baselines, detect patterns,
    and provide insights for rule refinement.
    """

    def __init__(self):
        """Initialize the learning engine."""
        self.data_base = Path.home() / "Desktop" / "Engineering" / "Hobbs" / "data"
        self.memory_dir = self.data_base / "memory"
        self.learning_dir = self.data_base / "learning"
        self.index_dir = self.data_base / "index"

        self.cache_file = self.learning_dir / "learning_cache.json"
        self.counter_file = self.learning_dir / "event_counter.json"
        self.events_file = self.memory_dir / "events.jsonl"

        self._last_learning_cycle = None

        self._ensure_paths()
        logger.info("LearningEngine initialized")

    def _ensure_paths(self) -> None:
        """Ensure required directories exist."""
        self.learning_dir.mkdir(parents=True, exist_ok=True)

    def load_memory_events(self, days: int = 30) -> List[MemoryEvent]:
        """
        Load memory events from the events file.

        Args:
            days: Number of days of history to load

        Returns:
            List of MemoryEvent objects
        """
        events = []
        cutoff = datetime.utcnow() - timedelta(days=days)

        if not self.events_file.exists():
            return events

        try:
            with open(self.events_file, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        event = MemoryEvent(**data)

                        # Parse timestamp and filter by date
                        try:
                            ts = event.timestamp.replace("Z", "+00:00")
                            event_dt = datetime.fromisoformat(ts.replace("Z", ""))
                            if event_dt.replace(tzinfo=None) >= cutoff:
                                events.append(event)
                        except Exception:
                            events.append(event)  # Include if can't parse date

                    except Exception as e:
                        logger.warning(f"Failed to parse memory event: {e}")
        except Exception as e:
            logger.error(f"Failed to load memory events: {e}")

        return events

    def compute_sensor_baselines(self, events: Optional[List[MemoryEvent]] = None) -> Dict[str, Any]:
        """
        Compute baseline statistics for each sensor type.

        Args:
            events: Memory events (loads from file if not provided)

        Returns:
            Dictionary with baseline stats per sensor type
        """
        if events is None:
            events = self.load_memory_events()

        # Group sensor events by type
        sensor_values: Dict[str, List[float]] = defaultdict(list)

        for event in events:
            if event.source != "sensor":
                continue

            value = event.metadata.get("value")
            if isinstance(value, (int, float)):
                sensor_values[event.subtype].append(float(value))

        # Compute statistics per sensor type
        baselines = {}
        for sensor_type, values in sensor_values.items():
            if not values:
                continue

            stats = compute_statistics(values)
            stats["trend"] = detect_trend(values)
            stats["variance_level"] = "high" if stats["std_dev"] > stats["avg"] * 0.5 else "normal"
            baselines[sensor_type] = stats

        return baselines

    def compute_intruder_patterns(self, events: Optional[List[MemoryEvent]] = None) -> Dict[str, Any]:
        """
        Compute intruder detection patterns.

        Args:
            events: Memory events (loads from file if not provided)

        Returns:
            Dictionary with intruder patterns
        """
        if events is None:
            events = self.load_memory_events()

        # Track intruder events
        hourly_counts: Dict[str, int] = defaultdict(int)
        camera_counts: Dict[str, int] = defaultdict(int)
        object_counts: Dict[str, int] = defaultdict(int)
        total_intruders = 0

        for event in events:
            if event.source != "camera" or event.subtype != "intruder":
                continue

            total_intruders += 1

            # Extract hour
            try:
                ts = event.timestamp.replace("Z", "")
                dt = datetime.fromisoformat(ts)
                hour = dt.strftime("%H")
                hourly_counts[hour] += 1
            except Exception:
                pass

            # Extract camera
            camera_id = event.metadata.get("camera_id", "unknown")
            camera_counts[camera_id] += 1

            # Extract object type
            obj_type = event.metadata.get("object_detected", "unknown")
            object_counts[obj_type] += 1

        # Detect peak hours
        peak_hours = detect_peak_hours(dict(hourly_counts), top_n=3)

        # Determine hotspot cameras
        sorted_cameras = sorted(camera_counts.items(), key=lambda x: x[1], reverse=True)
        hotspot_cameras = [c for c, _ in sorted_cameras[:3]]

        return {
            "total_intruders": total_intruders,
            "by_hour": dict(hourly_counts),
            "by_camera": dict(camera_counts),
            "by_object": dict(object_counts),
            "peak_hours": peak_hours,
            "hotspot_cameras": hotspot_cameras,
        }

    def compute_weather_effects_on_sensors(
        self,
        events: Optional[List[MemoryEvent]] = None
    ) -> Dict[str, Any]:
        """
        Compute correlation between weather and sensor readings.

        Args:
            events: Memory events (loads from file if not provided)

        Returns:
            Dictionary with weather-sensor correlations
        """
        if events is None:
            events = self.load_memory_events()

        # Collect weather temperatures and moisture readings
        # Simplified: group by date and correlate daily averages
        daily_temps: Dict[str, List[float]] = defaultdict(list)
        daily_moisture: Dict[str, List[float]] = defaultdict(list)

        for event in events:
            try:
                ts = event.timestamp.replace("Z", "")
                dt = datetime.fromisoformat(ts)
                date_key = dt.strftime("%Y-%m-%d")

                if event.source == "weather":
                    # Try to extract temperature from metadata
                    temp = event.metadata.get("temperature")
                    if isinstance(temp, (int, float)):
                        daily_temps[date_key].append(float(temp))

                elif event.source == "sensor" and event.subtype == "moisture":
                    value = event.metadata.get("value")
                    if isinstance(value, (int, float)):
                        daily_moisture[date_key].append(float(value))

            except Exception:
                pass

        # Compute daily averages
        common_dates = set(daily_temps.keys()) & set(daily_moisture.keys())

        if len(common_dates) < 3:
            return {
                "correlation": 0.0,
                "sample_size": len(common_dates),
                "note": "Insufficient data for correlation"
            }

        sorted_dates = sorted(common_dates)
        temp_avgs = [mean(daily_temps[d]) for d in sorted_dates]
        moisture_avgs = [mean(daily_moisture[d]) for d in sorted_dates]

        corr = correlation(temp_avgs, moisture_avgs)

        return {
            "correlation": round(corr, 4),
            "sample_size": len(common_dates),
            "interpretation": (
                "strong positive" if corr > 0.7 else
                "moderate positive" if corr > 0.3 else
                "weak/none" if corr > -0.3 else
                "moderate negative" if corr > -0.7 else
                "strong negative"
            )
        }

    def compute_valve_usage_patterns(
        self,
        events: Optional[List[MemoryEvent]] = None
    ) -> Dict[str, Any]:
        """
        Compute valve usage patterns.

        Args:
            events: Memory events (loads from file if not provided)

        Returns:
            Dictionary with valve usage patterns
        """
        if events is None:
            events = self.load_memory_events()

        valve_events: Dict[str, List[Dict]] = defaultdict(list)
        total_actions = 0
        automation_driven = 0
        manual_driven = 0

        for event in events:
            if event.source != "valve":
                continue

            total_actions += 1
            valve_id = event.metadata.get("valve_id", "unknown")

            # Determine if automation-driven
            source_agent = event.metadata.get("source_agent", "")
            if "automation" in source_agent.lower() or "hobbs" in source_agent.lower():
                automation_driven += 1
            else:
                manual_driven += 1

            valve_events[valve_id].append({
                "timestamp": event.timestamp,
                "action": event.metadata.get("action"),
                "new_state": event.metadata.get("new_state"),
            })

        # Compute per-valve stats
        per_valve = {}
        for valve_id, events_list in valve_events.items():
            open_count = sum(1 for e in events_list if e.get("new_state") == "open")
            close_count = sum(1 for e in events_list if e.get("new_state") == "closed")
            per_valve[valve_id] = {
                "total_actions": len(events_list),
                "open_count": open_count,
                "close_count": close_count,
            }

        return {
            "total_actions": total_actions,
            "automation_driven": automation_driven,
            "manual_driven": manual_driven,
            "automation_ratio": automation_driven / total_actions if total_actions > 0 else 0,
            "per_valve": per_valve,
        }

    def run_full_learning_cycle(self) -> Dict[str, Any]:
        """
        Run a complete learning cycle.

        Steps:
        1. Load memory events
        2. Compute all statistics
        3. Write learning cache
        4. Generate rule suggestions
        5. Emit event to Congress

        Returns:
            Complete learning report
        """
        logger.info("Starting full learning cycle...")
        self._last_learning_cycle = datetime.utcnow().isoformat() + "Z"

        # Load events
        events = self.load_memory_events(days=30)

        # Compute all patterns
        sensor_baselines = self.compute_sensor_baselines(events)
        intruder_patterns = self.compute_intruder_patterns(events)
        weather_correlation = self.compute_weather_effects_on_sensors(events)
        valve_patterns = self.compute_valve_usage_patterns(events)

        # Build learning report
        learning_report = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "events_analyzed": len(events),
            "sensor_baselines": sensor_baselines,
            "intruder_patterns": intruder_patterns,
            "weather_sensor_correlation": weather_correlation,
            "valve_patterns": valve_patterns,
        }

        # Save to cache
        self._save_cache(learning_report)

        # Generate rule suggestions
        from server.learning.rule_refinement import rule_refinement
        suggestions = rule_refinement.generate_rule_suggestions(learning_report)

        # Emit event to Congress
        self._emit_learning_event()

        logger.info(f"Learning cycle complete: {len(events)} events analyzed")

        return {
            "learning": learning_report,
            "recommendations": suggestions.get("suggestions", []),
        }

    def _save_cache(self, report: Dict[str, Any]) -> None:
        """Save learning report to cache file."""
        try:
            with open(self.cache_file, "w") as f:
                json.dump(report, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save learning cache: {e}")

    def load_cache(self) -> Dict[str, Any]:
        """Load learning report from cache file."""
        if not self.cache_file.exists():
            return {}
        try:
            with open(self.cache_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load learning cache: {e}")
            return {}

    def _emit_learning_event(self) -> None:
        """Emit learning update event to Congress."""
        try:
            congress_memory = Path.home() / "Desktop" / "Engineering" / "Congress" / "memory"
            congress_memory.mkdir(parents=True, exist_ok=True)
            events_file = congress_memory / "hobbs_events.log"

            timestamp = datetime.utcnow().isoformat() + "Z"
            event_line = f"{timestamp} hobbs.learning.update CYCLE_COMPLETE\n"

            with open(events_file, "a") as f:
                f.write(event_line)
        except Exception as e:
            logger.error(f"Failed to emit learning event: {e}")

    def increment_event_counter(self) -> int:
        """
        Increment the event counter and return the new value.

        Returns:
            Current counter value after increment
        """
        counter = 0
        try:
            if self.counter_file.exists():
                with open(self.counter_file, "r") as f:
                    data = json.load(f)
                    counter = data.get("count", 0)
        except Exception:
            pass

        counter += 1

        try:
            with open(self.counter_file, "w") as f:
                json.dump({"count": counter, "last_update": datetime.utcnow().isoformat() + "Z"}, f)
        except Exception as e:
            logger.error(f"Failed to update event counter: {e}")

        return counter

    def should_run_learning_cycle(self, threshold: int = 50) -> bool:
        """
        Check if learning cycle should run based on event count.

        Args:
            threshold: Number of events between learning cycles

        Returns:
            True if cycle should run
        """
        try:
            if self.counter_file.exists():
                with open(self.counter_file, "r") as f:
                    data = json.load(f)
                    count = data.get("count", 0)
                    return count >= threshold
        except Exception:
            pass
        return False

    def reset_event_counter(self) -> None:
        """Reset the event counter to zero."""
        try:
            with open(self.counter_file, "w") as f:
                json.dump({"count": 0, "last_update": datetime.utcnow().isoformat() + "Z"}, f)
        except Exception as e:
            logger.error(f"Failed to reset event counter: {e}")

    def get_events_until_cycle(self, threshold: int = 50) -> int:
        """
        Get the number of events until next learning cycle.

        Args:
            threshold: Number of events between learning cycles

        Returns:
            Number of events remaining until next cycle
        """
        try:
            if self.counter_file.exists():
                with open(self.counter_file, "r") as f:
                    data = json.load(f)
                    count = data.get("count", 0)
                    return max(0, threshold - count)
        except Exception:
            pass
        return threshold

    @property
    def last_learning_cycle(self) -> Optional[str]:
        """Get timestamp of last learning cycle."""
        if self._last_learning_cycle:
            return self._last_learning_cycle

        # Try to read from cache file
        cache = self.load_cache()
        return cache.get("timestamp")


# Singleton instance
learning_engine = LearningEngine()
