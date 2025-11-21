"""
Configuration and logging settings for the Hobbs Agent.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path


class Settings:
    """Application settings for Hobbs Agent."""

    AGENT_NAME: str = "hobbs"
    VERSION: str = "0.2.0"

    # Capabilities exposed by this agent
    CAPABILITIES: list = [
        "sensor_ingest",
        "predict_weather",
        "detect_intruder",
        "control_valve"
    ]

    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent
    LOG_DIR: Path = Path.home() / "Desktop" / "Engineering" / "Hobbs" / "logs"
    LOG_FILE: Path = LOG_DIR / "hobbs.log"

    # Congress registration path
    CONGRESS_MEMORY_DIR: Path = Path.home() / "Desktop" / "Engineering" / "Congress" / "memory"
    REGISTRATION_FILE: Path = CONGRESS_MEMORY_DIR / "hobbs_registration.json"


settings = Settings()


def setup_logging() -> logging.Logger:
    """Set up the logging infrastructure."""
    # Ensure log directory exists
    settings.LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Create logger
    logger = logging.getLogger("hobbs")
    logger.setLevel(logging.INFO)

    # File handler
    file_handler = logging.FileHandler(settings.LOG_FILE)
    file_handler.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


# Initialize logger
logger = setup_logging()


def log_event(endpoint_name: str, payload: dict) -> None:
    """
    Log an event to the Hobbs log file.

    Format: <TIMESTAMP> ENDPOINT: <ENDPOINT_NAME> PAYLOAD: <JSON>

    Args:
        endpoint_name: Name of the endpoint that received the request
        payload: The payload data to log
    """
    payload_json = json.dumps(payload, default=str)
    logger.info(f"ENDPOINT: {endpoint_name} PAYLOAD: {payload_json}")
