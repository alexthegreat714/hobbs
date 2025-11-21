"""
Memory Manager for Hobbs Agent.

Builds and maintains unified event memory from existing logs.
Normalizes sensor, weather, camera, valve, and automation data
into searchable MemoryEvent records.
"""

import json
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

from config.settings import settings, logger
from schemas.memory import MemoryEvent


class MemoryManager:
    """
    Manages long-term memory storage and consolidation.

    Builds MemoryEvent records from raw logs and maintains
    unified JSONL memory files.
    """

    def __init__(self):
        """Initialize the memory manager."""
        self.data_base = Path.home() / "Desktop" / "Engineering" / "Hobbs" / "data"
        self.memory_dir = self.data_base / "memory"
        self.index_dir = self.data_base / "index"
        self.actuator_dir = self.data_base / "actuators"
        self.automation_dir = self.data_base / "automation"

        # Memory files
        self.events_file = self.memory_dir / "events.jsonl"
        self.intruders_file = self.memory_dir / "intruders.jsonl"
        self.weather_summary_file = self.memory_dir / "weather_summary.jsonl"
        self.sensor_summary_file = self.memory_dir / "sensor_summary.jsonl"

        self._ensure_paths()
        logger.info("MemoryManager initialized")

    def _ensure_paths(self) -> None:
        """Ensure required directories exist."""
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def _generate_event_id(self, source: str) -> str:
        """Generate a unique event ID."""
        short_uuid = str(uuid.uuid4())[:8]
        return f"evt_{source}_{short_uuid}"

    def append_memory_event(self, event: MemoryEvent, target_file: Path) -> None:
        """
        Append a MemoryEvent to a target JSONL file.

        Args:
            event: The MemoryEvent to append
            target_file: Path to the target JSONL file
        """
        try:
            with open(target_file, "a") as f:
                f.write(event.model_dump_json() + "\n")
        except Exception as e:
            logger.error(f"Failed to append memory event: {e}")

    def build_from_sensors(self) -> List[MemoryEvent]:
        """
        Build MemoryEvents from sensor_index.jsonl.

        Returns:
            List of created MemoryEvents
        """
        events = []
        sensor_index = self.index_dir / "sensor_index.jsonl"

        if not sensor_index.exists():
            logger.warning("sensor_index.jsonl not found")
            return events

        try:
            with open(sensor_index, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        event = MemoryEvent(
                            event_id=self._generate_event_id("sensor"),
                            timestamp=entry.get("timestamp", datetime.utcnow().isoformat() + "Z"),
                            source="sensor",
                            subtype=entry.get("sensor_type", "unknown"),
                            summary=f"Sensor {entry.get('sensor_type', 'unknown')}={entry.get('value', 'N/A')} at {entry.get('timestamp', 'unknown')}",
                            tags=[entry.get("sensor_type", "sensor")],
                            raw_path=entry.get("file_path"),
                            metadata={
                                "value": entry.get("value"),
                                "unit": entry.get("unit"),
                                "task_id": entry.get("task_id"),
                            }
                        )
                        events.append(event)
                    except Exception as e:
                        logger.warning(f"Failed to parse sensor entry: {e}")
        except Exception as e:
            logger.error(f"Failed to read sensor_index.jsonl: {e}")

        return events

    def build_from_weather(self) -> List[MemoryEvent]:
        """
        Build MemoryEvents from weather_index.jsonl.

        Returns:
            List of created MemoryEvents
        """
        events = []
        weather_index = self.index_dir / "weather_index.jsonl"

        if not weather_index.exists():
            logger.warning("weather_index.jsonl not found")
            return events

        try:
            with open(weather_index, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        source_type = entry.get("source", "unknown")
                        event = MemoryEvent(
                            event_id=self._generate_event_id("weather"),
                            timestamp=entry.get("timestamp", datetime.utcnow().isoformat() + "Z"),
                            source="weather",
                            subtype="forecast",
                            summary=f"Weather forecast updated (source={source_type})",
                            tags=["weather", source_type],
                            raw_path=entry.get("file_path"),
                            metadata={
                                "source": source_type,
                                "location": entry.get("location", {}),
                                "confidence": entry.get("confidence"),
                            }
                        )
                        events.append(event)
                    except Exception as e:
                        logger.warning(f"Failed to parse weather entry: {e}")
        except Exception as e:
            logger.error(f"Failed to read weather_index.jsonl: {e}")

        return events

    def build_from_camera(self) -> List[MemoryEvent]:
        """
        Build MemoryEvents from camera_index.jsonl.

        Returns:
            List of created MemoryEvents
        """
        events = []
        camera_index = self.index_dir / "camera_index.jsonl"

        if not camera_index.exists():
            logger.warning("camera_index.jsonl not found")
            return events

        try:
            with open(camera_index, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        camera_id = entry.get("camera_id", "unknown")
                        object_type = entry.get("object_detected", "unknown")
                        confidence = entry.get("confidence", 0)

                        # Determine if this is an intruder event
                        is_intruder = entry.get("intruder_detected", False)
                        subtype = "intruder" if is_intruder else "camera_event"

                        tags = [camera_id, object_type]
                        if is_intruder:
                            tags.append("intruder")

                        # Add direction if available
                        direction = entry.get("direction")
                        if direction:
                            tags.append(direction)

                        event = MemoryEvent(
                            event_id=self._generate_event_id("camera"),
                            timestamp=entry.get("timestamp", datetime.utcnow().isoformat() + "Z"),
                            source="camera",
                            subtype=subtype,
                            summary=f"Camera {camera_id}: {object_type} detected (confidence={confidence:.2f})",
                            tags=tags,
                            raw_path=entry.get("image_path"),
                            metadata={
                                "camera_id": camera_id,
                                "object_detected": object_type,
                                "confidence": confidence,
                                "intruder_detected": is_intruder,
                                "direction": direction,
                                "task_id": entry.get("task_id"),
                            }
                        )
                        events.append(event)
                    except Exception as e:
                        logger.warning(f"Failed to parse camera entry: {e}")
        except Exception as e:
            logger.error(f"Failed to read camera_index.jsonl: {e}")

        return events

    def build_from_valves(self) -> List[MemoryEvent]:
        """
        Build MemoryEvents from valve_history.jsonl.

        Returns:
            List of created MemoryEvents
        """
        events = []
        valve_history = self.actuator_dir / "valve_history.jsonl"

        if not valve_history.exists():
            logger.warning("valve_history.jsonl not found")
            return events

        try:
            with open(valve_history, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        valve_id = entry.get("valve_id", "unknown")
                        action = entry.get("action", "unknown")
                        value = entry.get("value")
                        new_state = entry.get("new_state", "unknown")

                        value_str = f" value={value}" if value is not None else ""
                        event = MemoryEvent(
                            event_id=self._generate_event_id("valve"),
                            timestamp=entry.get("timestamp", datetime.utcnow().isoformat() + "Z"),
                            source="valve",
                            subtype="valve_change",
                            summary=f"Valve {valve_id}: {action}{value_str} -> {new_state}",
                            tags=[valve_id, action, new_state],
                            raw_path=None,
                            metadata={
                                "valve_id": valve_id,
                                "action": action,
                                "value": value,
                                "previous_state": entry.get("previous_state"),
                                "new_state": new_state,
                                "reason": entry.get("reason"),
                                "aegis_verified": entry.get("aegis_verified"),
                                "source_agent": entry.get("source_agent"),
                            }
                        )
                        events.append(event)
                    except Exception as e:
                        logger.warning(f"Failed to parse valve entry: {e}")
        except Exception as e:
            logger.error(f"Failed to read valve_history.jsonl: {e}")

        return events

    def build_from_automation(self) -> List[MemoryEvent]:
        """
        Build MemoryEvents from automation_history.jsonl.

        Returns:
            List of created MemoryEvents
        """
        events = []
        automation_history = self.automation_dir / "automation_history.jsonl"

        if not automation_history.exists():
            logger.warning("automation_history.jsonl not found")
            return events

        try:
            with open(automation_history, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        trigger_type = entry.get("trigger_type", "unknown")
                        action_data = entry.get("action", {})
                        rule_id = action_data.get("rule_id", "unknown")

                        event = MemoryEvent(
                            event_id=self._generate_event_id("automation"),
                            timestamp=entry.get("timestamp", datetime.utcnow().isoformat() + "Z"),
                            source="automation",
                            subtype="rule_fire",
                            summary=f"Automation rule '{rule_id}' fired ({trigger_type})",
                            tags=["automation", trigger_type, rule_id],
                            raw_path=None,
                            metadata={
                                "trigger_type": trigger_type,
                                "rule_id": rule_id,
                                "action": action_data.get("action", {}),
                                "trigger_context": action_data.get("trigger_context", {}),
                            }
                        )
                        events.append(event)
                    except Exception as e:
                        logger.warning(f"Failed to parse automation entry: {e}")
        except Exception as e:
            logger.error(f"Failed to read automation_history.jsonl: {e}")

        return events

    def rebuild_full_memory(self) -> Dict[str, int]:
        """
        Clear and rebuild all memory files from raw logs.

        Returns:
            Dictionary with counts of events per source
        """
        logger.info("Starting full memory rebuild...")

        # Clear existing memory files
        for f in [self.events_file, self.intruders_file,
                  self.weather_summary_file, self.sensor_summary_file]:
            if f.exists():
                f.unlink()
            f.touch()

        counts = {
            "sensor": 0,
            "weather": 0,
            "camera": 0,
            "valve": 0,
            "automation": 0,
            "total": 0,
        }

        # Build from all sources
        all_events = []

        # Sensors
        sensor_events = self.build_from_sensors()
        counts["sensor"] = len(sensor_events)
        all_events.extend(sensor_events)
        for event in sensor_events:
            self.append_memory_event(event, self.sensor_summary_file)

        # Weather
        weather_events = self.build_from_weather()
        counts["weather"] = len(weather_events)
        all_events.extend(weather_events)
        for event in weather_events:
            self.append_memory_event(event, self.weather_summary_file)

        # Camera
        camera_events = self.build_from_camera()
        counts["camera"] = len(camera_events)
        all_events.extend(camera_events)
        for event in camera_events:
            if event.subtype == "intruder":
                self.append_memory_event(event, self.intruders_file)

        # Valves
        valve_events = self.build_from_valves()
        counts["valve"] = len(valve_events)
        all_events.extend(valve_events)

        # Automation
        automation_events = self.build_from_automation()
        counts["automation"] = len(automation_events)
        all_events.extend(automation_events)

        # Write all events to global events file
        for event in all_events:
            self.append_memory_event(event, self.events_file)

        counts["total"] = len(all_events)
        logger.info(f"Memory rebuild complete: {counts}")

        return counts

    def incremental_update(self) -> Dict[str, int]:
        """
        Incrementally update memory from new log entries.

        STUB: Currently just calls rebuild_full_memory().
        Future implementation will track last processed entries.

        Returns:
            Dictionary with counts of new events
        """
        # For now, just rebuild everything
        return self.rebuild_full_memory()

    def get_events_count(self) -> int:
        """Get the number of events in events.jsonl."""
        try:
            if self.events_file.exists():
                with open(self.events_file, "r") as f:
                    return sum(1 for line in f if line.strip())
        except Exception:
            pass
        return 0

    def get_intruders_count(self) -> int:
        """Get the number of events in intruders.jsonl."""
        try:
            if self.intruders_file.exists():
                with open(self.intruders_file, "r") as f:
                    return sum(1 for line in f if line.strip())
        except Exception:
            pass
        return 0

    def get_weather_summary_count(self) -> int:
        """Get the number of events in weather_summary.jsonl."""
        try:
            if self.weather_summary_file.exists():
                with open(self.weather_summary_file, "r") as f:
                    return sum(1 for line in f if line.strip())
        except Exception:
            pass
        return 0


# Singleton instance
memory_manager = MemoryManager()
