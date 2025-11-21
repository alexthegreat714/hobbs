"""
Sensor Manager for the Hobbs Agent.

Responsible for:
- Preparing folder for today's sensor data
- Writing sensor JSON files
- Updating sensor_index.jsonl
- Emitting sensor events to Congress
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union

from server.utils.file_ops import (
    ensure_folder,
    write_json,
    append_jsonl,
    safe_filename,
    get_sensors_dir,
    get_sensor_index_path,
    count_files_in_folder,
    count_jsonl_entries,
)
from server.utils.time_ops import now_iso, today_str, timestamp_str
from config.settings import logger


# Congress event log location
CONGRESS_EVENTS_LOG = Path.home() / "Desktop" / "Engineering" / "Congress" / "memory" / "hobbs_events.log"


class SensorManager:
    """
    Manages sensor data storage and indexing.
    """

    def __init__(self):
        """Initialize the sensor manager."""
        self.sensors_dir = get_sensors_dir()
        self.index_path = get_sensor_index_path()

    def get_today_folder(self) -> Path:
        """
        Get the folder path for today's sensor data.

        Returns:
            Path to ~/Desktop/Engineering/Hobbs/data/sensors/YYYY-MM-DD/
        """
        today = today_str()
        folder = self.sensors_dir / today
        ensure_folder(folder)
        return folder

    def store_sensor_data(
        self,
        sensor_type: str,
        value: Union[float, Dict[str, Any]],
        unit: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Store sensor data to file and update index.

        Args:
            sensor_type: Type of sensor (e.g., "moisture", "temperature")
            value: Sensor value (float or dict)
            unit: Unit of measurement (optional)
            metadata: Additional metadata (optional)
            task_id: Associated task ID (optional)

        Returns:
            Dictionary with storage result including file path
        """
        timestamp = now_iso()
        ts_filename = timestamp_str()

        # Prepare sensor data payload
        sensor_data = {
            "timestamp": timestamp,
            "sensor_type": sensor_type,
            "value": value,
            "unit": unit,
            "metadata": metadata or {},
            "task_id": task_id,
        }

        # Generate filename and path
        filename = safe_filename(sensor_type, ts_filename) + ".json"
        today_folder = self.get_today_folder()
        filepath = today_folder / filename

        # Write sensor JSON file
        write_json(filepath, sensor_data)
        logger.info(f"Stored sensor data: {filepath}")

        # Calculate relative path from data folder
        relative_path = str(filepath.relative_to(self.sensors_dir.parent))

        # Create index entry
        index_entry = {
            "timestamp": timestamp,
            "sensor_type": sensor_type,
            "value": value,
            "unit": unit,
            "path": relative_path,
        }

        # Append to sensor index
        append_jsonl(self.index_path, index_entry)
        logger.info(f"Updated sensor index: {self.index_path}")

        # Emit sensor trigger event to Congress
        self._emit_sensor_event(sensor_type, value, timestamp)

        return {
            "stored": True,
            "path": str(filepath),
            "relative_path": relative_path,
            "timestamp": timestamp,
        }

    def _emit_sensor_event(
        self,
        sensor_type: str,
        value: Union[float, Dict[str, Any]],
        timestamp: str,
    ) -> None:
        """
        Emit a stubbed sensor trigger event to Congress.

        Writes to ~/Desktop/Engineering/Congress/memory/hobbs_events.log

        Args:
            sensor_type: Type of sensor
            value: Sensor value
            timestamp: Event timestamp
        """
        # Ensure Congress memory directory exists
        ensure_folder(CONGRESS_EVENTS_LOG.parent)

        event_line = f"{timestamp} hobbs.sensor_trigger sensor_type={sensor_type} value={value}\n"

        with open(CONGRESS_EVENTS_LOG, "a") as f:
            f.write(event_line)

        logger.info(f"Emitted sensor event to Congress: hobbs.sensor_trigger")

    def get_sensors_today_count(self) -> int:
        """
        Get the count of sensor files for today.

        Returns:
            Number of sensor JSON files in today's folder
        """
        today_folder = self.sensors_dir / today_str()
        return count_files_in_folder(today_folder, "*.json")

    def get_index_size(self) -> int:
        """
        Get the number of entries in the sensor index.

        Returns:
            Number of entries in sensor_index.jsonl
        """
        return count_jsonl_entries(self.index_path)


# Singleton instance
sensor_manager = SensorManager()
