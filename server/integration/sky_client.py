"""
Sky Client for Hobbs Agent.

Handles communication with Sky (the orchestrator agent).
Currently file-based; future versions may use HTTP.
"""

import json
from typing import Any, Dict
from datetime import datetime
from pathlib import Path

from config.settings import settings, logger


# Sky paths
SKY_MEMORY_DIR = Path.home() / "Desktop" / "Engineering" / "Sky" / "memory"
HOBBS_SUMMARIES_FILE = SKY_MEMORY_DIR / "hobbs_summaries.jsonl"


class SkyClient:
    """
    Client for communicating with Sky orchestrator.

    Handles:
    - Sending summaries to Sky
    - Status reporting
    - Command acknowledgment
    """

    def __init__(self):
        """Initialize the Sky client."""
        self._ensure_paths()

    def _ensure_paths(self) -> None:
        """Ensure required directories exist."""
        SKY_MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    def send_summary(self, summary: Dict[str, Any]) -> bool:
        """
        Send a summary report to Sky.

        Args:
            summary: Summary data to send

        Returns:
            True if summary was sent successfully
        """
        try:
            self._ensure_paths()

            # Add metadata
            entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "agent": settings.AGENT_NAME,
                "version": settings.VERSION,
                "summary": summary
            }

            with open(HOBBS_SUMMARIES_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")

            logger.info("Summary sent to Sky")
            return True

        except Exception as e:
            logger.error(f"Failed to send summary to Sky: {e}")
            return False

    def send_status_update(self, status: Dict[str, Any]) -> bool:
        """
        Send a status update to Sky.

        Args:
            status: Status data to send

        Returns:
            True if status was sent successfully
        """
        return self.send_summary({
            "type": "status_update",
            "status": status
        })

    def acknowledge_command(self, command_id: str, result: Dict[str, Any]) -> bool:
        """
        Acknowledge a command from Sky.

        Args:
            command_id: ID of the command being acknowledged
            result: Result of command execution

        Returns:
            True if acknowledgment was sent successfully
        """
        return self.send_summary({
            "type": "command_ack",
            "command_id": command_id,
            "result": result
        })

    def request_guidance(self, context: Dict[str, Any]) -> bool:
        """
        Request guidance from Sky.

        Args:
            context: Context for the guidance request

        Returns:
            True if request was sent successfully
        """
        return self.send_summary({
            "type": "guidance_request",
            "context": context
        })


# Singleton instance
sky_client = SkyClient()
