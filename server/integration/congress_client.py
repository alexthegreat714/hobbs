"""
Congress Client for Hobbs Agent.

Handles policy management and heartbeat communication with Congress.
"""

import json
from typing import Any, Dict, Optional
from datetime import datetime
from pathlib import Path

from config.settings import settings, logger


# Congress paths
CONGRESS_DIR = Path.home() / "Desktop" / "Engineering" / "Congress" / "memory"
HOBBS_POLICY_FILE = CONGRESS_DIR / "hobbs_policy.json"
HOBBS_HEARTBEAT_LOG = CONGRESS_DIR / "hobbs_heartbeat.log"

# Local paths
HOBBS_DATA_DIR = Path.home() / "Desktop" / "Engineering" / "Hobbs" / "data"
ACTIVE_POLICIES_FILE = HOBBS_DATA_DIR / "policies_active.json"
LOCAL_POLICIES_FILE = Path(__file__).parent.parent.parent / "config" / "hobbs_policies.json"


class CongressClient:
    """
    Client for communicating with Congress.

    Handles:
    - Policy loading and application
    - Heartbeat reporting
    - Registration updates
    """

    def __init__(self):
        """Initialize the Congress client."""
        self._active_policies = {}
        self._last_heartbeat = None
        self._startup_time = datetime.utcnow()
        self._ensure_paths()

    def _ensure_paths(self) -> None:
        """Ensure required directories exist."""
        CONGRESS_DIR.mkdir(parents=True, exist_ok=True)
        HOBBS_DATA_DIR.mkdir(parents=True, exist_ok=True)

    def load_policies(self) -> Dict[str, Any]:
        """
        Load policies for Hobbs.

        Attempts to load from Congress first, then falls back to local config.

        Returns:
            Policy dictionary
        """
        policies = {}

        # Try Congress policy file first
        if HOBBS_POLICY_FILE.exists():
            try:
                with open(HOBBS_POLICY_FILE, "r") as f:
                    policies = json.load(f)
                logger.info(f"Loaded policies from Congress: {HOBBS_POLICY_FILE}")
                return policies
            except Exception as e:
                logger.warning(f"Failed to load Congress policies: {e}")

        # Fall back to local policies
        if LOCAL_POLICIES_FILE.exists():
            try:
                with open(LOCAL_POLICIES_FILE, "r") as f:
                    policies = json.load(f)
                logger.info(f"Loaded local policies: {LOCAL_POLICIES_FILE}")
                return policies
            except Exception as e:
                logger.warning(f"Failed to load local policies: {e}")

        # Return default policies if nothing found
        policies = self._get_default_policies()
        logger.info("Using default policies")
        return policies

    def _get_default_policies(self) -> Dict[str, Any]:
        """Get default policy configuration."""
        return {
            "version": "1.0.0",
            "agent": "hobbs",
            "permissions": {
                "valve_control": True,
                "sensor_ingest": True,
                "weather_fetch": True,
                "intruder_detection": True,
                "memory_rebuild": True,
                "learning_cycle": True
            },
            "limits": {
                "max_valve_commands_per_hour": 100,
                "max_sensor_events_per_minute": 60,
                "max_image_storage_mb": 1000,
                "learning_cycle_interval_minutes": 30
            },
            "alerts": {
                "suspicion_threshold": 0.75,
                "temperature_freeze_threshold": 0,
                "moisture_low_threshold": 0.2
            },
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }

    def apply_policies(self, policies: Dict[str, Any]) -> bool:
        """
        Apply policies to Hobbs.

        Stores active policies in memory and to disk.

        Args:
            policies: Policy dictionary to apply

        Returns:
            True if policies were applied successfully
        """
        try:
            self._active_policies = policies

            # Save to active policies file
            with open(ACTIVE_POLICIES_FILE, "w") as f:
                json.dump(policies, f, indent=2)

            logger.info("Policies applied successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to apply policies: {e}")
            return False

    def get_active_policies(self) -> Dict[str, Any]:
        """Get currently active policies."""
        if not self._active_policies:
            # Try to load from file
            if ACTIVE_POLICIES_FILE.exists():
                try:
                    with open(ACTIVE_POLICIES_FILE, "r") as f:
                        self._active_policies = json.load(f)
                except Exception:
                    pass
        return self._active_policies

    def check_permission(self, action: str) -> bool:
        """
        Check if an action is permitted by current policies.

        Args:
            action: Action name to check

        Returns:
            True if action is permitted
        """
        policies = self.get_active_policies()
        permissions = policies.get("permissions", {})
        return permissions.get(action, True)  # Default to permitted

    def get_limit(self, limit_name: str, default: Any = None) -> Any:
        """
        Get a limit value from current policies.

        Args:
            limit_name: Name of the limit
            default: Default value if not found

        Returns:
            Limit value
        """
        policies = self.get_active_policies()
        limits = policies.get("limits", {})
        return limits.get(limit_name, default)

    def get_alert_threshold(self, threshold_name: str, default: float = 0.0) -> float:
        """
        Get an alert threshold from current policies.

        Args:
            threshold_name: Name of the threshold
            default: Default value if not found

        Returns:
            Threshold value
        """
        policies = self.get_active_policies()
        alerts = policies.get("alerts", {})
        return alerts.get(threshold_name, default)

    def send_heartbeat(self) -> bool:
        """
        Send a heartbeat to Congress.

        Appends a heartbeat line to the Congress heartbeat log.

        Returns:
            True if heartbeat was sent successfully
        """
        try:
            self._ensure_paths()

            timestamp = datetime.utcnow().isoformat() + "Z"
            uptime_hours = (datetime.utcnow() - self._startup_time).total_seconds() / 3600

            heartbeat_line = (
                f"{timestamp} hobbs.heartbeat "
                f"STATUS:ok "
                f"VERSION:{settings.VERSION} "
                f"UPTIME_HOURS:{uptime_hours:.2f}\n"
            )

            with open(HOBBS_HEARTBEAT_LOG, "a") as f:
                f.write(heartbeat_line)

            self._last_heartbeat = timestamp
            logger.debug(f"Heartbeat sent: {timestamp}")
            return True

        except Exception as e:
            logger.error(f"Failed to send heartbeat: {e}")
            return False

    def get_last_heartbeat(self) -> Optional[str]:
        """Get timestamp of last heartbeat."""
        if self._last_heartbeat:
            return self._last_heartbeat

        # Try to read from file
        if HOBBS_HEARTBEAT_LOG.exists():
            try:
                with open(HOBBS_HEARTBEAT_LOG, "r") as f:
                    lines = f.readlines()
                    if lines:
                        last_line = lines[-1].strip()
                        # Extract timestamp (first part before space)
                        return last_line.split()[0] if last_line else None
            except Exception:
                pass
        return None

    @property
    def policies_loaded(self) -> bool:
        """Check if policies have been loaded."""
        return bool(self._active_policies)

    @property
    def last_heartbeat(self) -> Optional[str]:
        """Get timestamp of last heartbeat as property."""
        return self.get_last_heartbeat()


# Singleton instance
congress_client = CongressClient()
