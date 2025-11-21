"""
File operations utility for the Hobbs Agent.

Provides functions for file system operations including
folder creation, JSON writing, and JSONL appending.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, Union


# Base data directory
DATA_DIR = Path.home() / "Desktop" / "Engineering" / "Hobbs" / "data"


def ensure_folder(path: Union[str, Path]) -> Path:
    """
    Ensure a folder exists, creating it if necessary.

    Args:
        path: The folder path to ensure exists

    Returns:
        Path object of the ensured folder
    """
    folder = Path(path)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def write_json(filepath: Union[str, Path], data: Dict[str, Any]) -> Path:
    """
    Write data to a JSON file.

    Args:
        filepath: The file path to write to
        data: The dictionary data to serialize as JSON

    Returns:
        Path object of the written file
    """
    file_path = Path(filepath)
    ensure_folder(file_path.parent)

    with open(file_path, "w") as f:
        json.dump(data, f, indent=2, default=str)

    return file_path


def append_jsonl(filepath: Union[str, Path], data: Dict[str, Any]) -> Path:
    """
    Append a JSON object as a line to a JSONL file.

    Args:
        filepath: The JSONL file path to append to
        data: The dictionary data to append as a JSON line

    Returns:
        Path object of the file
    """
    file_path = Path(filepath)
    ensure_folder(file_path.parent)

    with open(file_path, "a") as f:
        f.write(json.dumps(data, default=str) + "\n")

    return file_path


def safe_filename(sensor_type: str, timestamp: str) -> str:
    """
    Generate a safe filename from sensor type and timestamp.

    Replaces any unsafe characters with underscores.

    Args:
        sensor_type: The type of sensor (e.g., "moisture", "temperature")
        timestamp: The timestamp string (e.g., "20250121_153045")

    Returns:
        A safe filename string (without extension)
    """
    # Replace any non-alphanumeric characters (except underscore and hyphen) with underscore
    safe_type = re.sub(r"[^a-zA-Z0-9_-]", "_", sensor_type)
    safe_timestamp = re.sub(r"[^a-zA-Z0-9_-]", "_", timestamp)

    return f"{safe_type}_{safe_timestamp}"


def get_data_dir() -> Path:
    """
    Get the base data directory path.

    Returns:
        Path to ~/Desktop/Engineering/Hobbs/data/
    """
    return DATA_DIR


def get_sensors_dir() -> Path:
    """
    Get the sensors data directory path.

    Returns:
        Path to ~/Desktop/Engineering/Hobbs/data/sensors/
    """
    return DATA_DIR / "sensors"


def get_index_dir() -> Path:
    """
    Get the index directory path.

    Returns:
        Path to ~/Desktop/Engineering/Hobbs/data/index/
    """
    return DATA_DIR / "index"


def get_sensor_index_path() -> Path:
    """
    Get the sensor index file path.

    Returns:
        Path to ~/Desktop/Engineering/Hobbs/data/index/sensor_index.jsonl
    """
    return DATA_DIR / "index" / "sensor_index.jsonl"


def count_jsonl_entries(filepath: Union[str, Path]) -> int:
    """
    Count the number of entries in a JSONL file.

    Args:
        filepath: Path to the JSONL file

    Returns:
        Number of lines (entries) in the file
    """
    file_path = Path(filepath)
    if not file_path.exists():
        return 0

    with open(file_path, "r") as f:
        return sum(1 for line in f if line.strip())


def count_files_in_folder(folder: Union[str, Path], pattern: str = "*.json") -> int:
    """
    Count files matching a pattern in a folder.

    Args:
        folder: The folder to search
        pattern: Glob pattern for files to count

    Returns:
        Number of matching files
    """
    folder_path = Path(folder)
    if not folder_path.exists():
        return 0

    return len(list(folder_path.glob(pattern)))
