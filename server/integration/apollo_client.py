"""
Apollo Client for Hobbs Agent.

Handles communication with Apollo (economic/resource agent).
Currently file-based; future versions may use HTTP.
"""

import json
from typing import Any, Dict
from datetime import datetime
from pathlib import Path

from config.settings import settings, logger


# Apollo paths
APOLLO_MEMORY_DIR = Path.home() / "Desktop" / "Engineering" / "Apollo" / "memory"
HOBBS_ECON_FILE = APOLLO_MEMORY_DIR / "hobbs_econ_relevant.jsonl"


class ApolloClient:
    """
    Client for communicating with Apollo economic agent.

    Handles:
    - Sending economically relevant events
    - Resource usage reporting
    - Cost-related notifications
    """

    def __init__(self):
        """Initialize the Apollo client."""
        self._ensure_paths()

    def _ensure_paths(self) -> None:
        """Ensure required directories exist."""
        APOLLO_MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    def notify_event(self, event: Dict[str, Any]) -> bool:
        """
        Notify Apollo of an economically relevant event.

        Args:
            event: Event data to send

        Returns:
            True if event was sent successfully
        """
        try:
            self._ensure_paths()

            # Add metadata
            entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "agent": settings.AGENT_NAME,
                "version": settings.VERSION,
                "event": event
            }

            with open(HOBBS_ECON_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")

            logger.info("Economic event sent to Apollo")
            return True

        except Exception as e:
            logger.error(f"Failed to notify Apollo: {e}")
            return False

    def report_resource_usage(
        self,
        resource_type: str,
        amount: float,
        unit: str,
        context: Dict[str, Any] = None
    ) -> bool:
        """
        Report resource usage to Apollo.

        Args:
            resource_type: Type of resource (water, power, etc.)
            amount: Amount used
            unit: Unit of measurement
            context: Additional context

        Returns:
            True if report was sent successfully
        """
        return self.notify_event({
            "type": "resource_usage",
            "resource_type": resource_type,
            "amount": amount,
            "unit": unit,
            "context": context or {}
        })

    def report_valve_action(
        self,
        valve_id: str,
        action: str,
        duration_estimate: float = 0
    ) -> bool:
        """
        Report valve action to Apollo for resource tracking.

        Args:
            valve_id: Valve identifier
            action: Action taken (open, close, etc.)
            duration_estimate: Estimated duration in minutes

        Returns:
            True if report was sent successfully
        """
        return self.notify_event({
            "type": "valve_action",
            "valve_id": valve_id,
            "action": action,
            "duration_estimate": duration_estimate
        })

    def report_weather_impact(
        self,
        impact_type: str,
        severity: str,
        expected_cost: float = 0
    ) -> bool:
        """
        Report weather impact to Apollo.

        Args:
            impact_type: Type of weather impact
            severity: low, medium, high
            expected_cost: Estimated economic impact

        Returns:
            True if report was sent successfully
        """
        return self.notify_event({
            "type": "weather_impact",
            "impact_type": impact_type,
            "severity": severity,
            "expected_cost": expected_cost
        })

    def send_alert(
        self,
        alert_type: str,
        message: str,
        severity: str = "medium",
        context: Dict[str, Any] = None
    ) -> bool:
        """
        Send an alert to Apollo.

        Args:
            alert_type: Type of alert (security, weather, system, etc.)
            message: Alert message
            severity: Alert severity (low, medium, high, critical)
            context: Additional context

        Returns:
            True if alert was sent successfully
        """
        return self.notify_event({
            "type": "alert",
            "alert_type": alert_type,
            "message": message,
            "severity": severity,
            "context": context or {}
        })


# Singleton instance
apollo_client = ApolloClient()
