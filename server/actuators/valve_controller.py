"""
Valve Controller for the Hobbs Agent.

Responsible for:
- Translating valve commands into actuator operations
- Maintaining local "shadow state" of valves
- Persisting valve history
- Abstracting hardware-specific code

NOTE: This is an abstraction layer - no direct GPIO/relay control.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from config.settings import logger
from server.utils.file_ops import ensure_folder, append_jsonl, count_jsonl_entries
from server.utils.time_ops import now_iso
from schemas.actuators import ValveCommandPayload, VALID_ACTIONS


# Data directories
DATA_DIR = Path.home() / "Desktop" / "Engineering" / "Hobbs" / "data"
ACTUATORS_DIR = DATA_DIR / "actuators"
VALVE_STATE_FILE = ACTUATORS_DIR / "valve_state.json"
VALVE_HISTORY_FILE = ACTUATORS_DIR / "valve_history.jsonl"

# Congress event log
CONGRESS_EVENTS_LOG = Path.home() / "Desktop" / "Engineering" / "Congress" / "memory" / "hobbs_events.log"


class ValveController:
    """
    Controls and tracks valve states.

    Maintains an in-memory shadow state of all known valves,
    persisted to disk for recovery on restart.
    """

    def __init__(self):
        """Initialize the valve controller."""
        self.actuators_dir = ACTUATORS_DIR
        self.state_file = VALVE_STATE_FILE
        self.history_file = VALVE_HISTORY_FILE
        self.valve_state: Dict[str, Dict[str, Any]] = {}

        # Load existing state on startup
        self.load_state()

    def load_state(self) -> None:
        """
        Load valve state from disk.

        If state file doesn't exist, starts with empty state.
        """
        ensure_folder(self.actuators_dir)

        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    self.valve_state = json.load(f)
                logger.info(f"Loaded valve state: {len(self.valve_state)} valves")
            except Exception as e:
                logger.warning(f"Failed to load valve state: {e}. Starting fresh.")
                self.valve_state = {}
        else:
            logger.info("No existing valve state found. Starting fresh.")
            self.valve_state = {}

    def save_state(self) -> None:
        """
        Save current valve state to disk.
        """
        ensure_folder(self.actuators_dir)

        try:
            with open(self.state_file, "w") as f:
                json.dump(self.valve_state, f, indent=2)
            logger.info(f"Saved valve state: {len(self.valve_state)} valves")
        except Exception as e:
            logger.error(f"Failed to save valve state: {e}")

    def get_valve_state(self, valve_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current state of a specific valve.

        Args:
            valve_id: The valve identifier

        Returns:
            Dict with valve state or None if unknown
        """
        return self.valve_state.get(valve_id)

    def apply_command(
        self,
        valve_cmd: ValveCommandPayload,
        aegis_token: Dict[str, Any],
        source_task_id: str,
        source_agent: str,
    ) -> Dict[str, Any]:
        """
        Apply a valve command and update state.

        Args:
            valve_cmd: The validated valve command
            aegis_token: Verification result from Aegis
            source_task_id: Task ID of the originating request
            source_agent: Agent that sent the command

        Returns:
            Dict with result including final valve state
        """
        valve_id = valve_cmd.valve_id
        action = valve_cmd.action.lower()
        value = valve_cmd.value
        reason = valve_cmd.reason

        # Validate action
        if action not in VALID_ACTIONS:
            return {
                "ok": False,
                "error": f"Invalid action '{action}'. Must be one of: {VALID_ACTIONS}",
                "valve_id": valve_id,
            }

        # Get current state (or initialize)
        current = self.valve_state.get(valve_id, {
            "state": "unknown",
            "value": None,
            "last_update": None,
        })

        # Calculate new state based on action
        new_state, new_value = self._calculate_new_state(action, value, current)

        # Update shadow state
        self.valve_state[valve_id] = {
            "state": new_state,
            "value": new_value,
            "last_update": now_iso(),
        }

        # Append to history
        history_entry = {
            "timestamp": now_iso(),
            "valve_id": valve_id,
            "action": action,
            "value": new_value,
            "previous_state": current.get("state"),
            "new_state": new_state,
            "reason": reason,
            "aegis_signature": aegis_token.get("signature"),
            "aegis_verified": aegis_token.get("verified", False),
            "source_task_id": source_task_id,
            "source_agent": source_agent,
        }
        self._append_history(history_entry)

        # Save updated state to disk
        self.save_state()

        # Emit event to Congress
        self._emit_valve_event(valve_id, action, new_value)

        logger.info(f"Valve command applied: {valve_id} -> {new_state} (value={new_value})")

        return {
            "ok": True,
            "valve_id": valve_id,
            "state": new_state,
            "value": new_value,
            "previous_state": current.get("state"),
            "verified": aegis_token.get("verified", False),
        }

    def record_denial(
        self,
        valve_cmd: ValveCommandPayload,
        aegis_token: Dict[str, Any],
        source_task_id: str,
        source_agent: str,
    ) -> None:
        """
        Record a denied command in history.

        Args:
            valve_cmd: The valve command that was denied
            aegis_token: Verification result from Aegis
            source_task_id: Task ID of the originating request
            source_agent: Agent that sent the command
        """
        history_entry = {
            "timestamp": now_iso(),
            "valve_id": valve_cmd.valve_id,
            "action": valve_cmd.action,
            "value": valve_cmd.value,
            "reason": valve_cmd.reason,
            "aegis_signature": aegis_token.get("signature"),
            "aegis_verified": False,
            "denied": True,
            "denial_reason": aegis_token.get("details", {}).get("reason", "Unknown"),
            "source_task_id": source_task_id,
            "source_agent": source_agent,
        }
        self._append_history(history_entry)
        logger.warning(f"Valve command DENIED: {valve_cmd.valve_id} {valve_cmd.action}")

    def _calculate_new_state(
        self,
        action: str,
        value: Optional[float],
        current: Dict[str, Any],
    ) -> tuple:
        """
        Calculate the new state based on action.

        Args:
            action: The action to perform
            value: Optional value for 'set' action
            current: Current valve state

        Returns:
            Tuple of (new_state, new_value)
        """
        if action == "open":
            return ("open", 1.0)

        elif action == "close":
            return ("closed", 0.0)

        elif action == "toggle":
            # Toggle between open and closed
            if current.get("state") == "open":
                return ("closed", 0.0)
            else:
                return ("open", 1.0)

        elif action == "set":
            # Set to specific value
            if value is None:
                value = 0.5  # Default to 50% if not specified

            if value == 0.0:
                return ("closed", 0.0)
            elif value == 1.0:
                return ("open", 1.0)
            else:
                return ("partial", value)

        # Should not reach here if action was validated
        return (current.get("state", "unknown"), current.get("value"))

    def _append_history(self, entry: Dict[str, Any]) -> None:
        """
        Append an entry to valve history.

        Args:
            entry: The history entry to append
        """
        ensure_folder(self.history_file.parent)
        append_jsonl(self.history_file, entry)

    def _emit_valve_event(
        self,
        valve_id: str,
        action: str,
        value: Optional[float],
    ) -> None:
        """
        Emit valve change event to Congress.

        Args:
            valve_id: The valve identifier
            action: The action performed
            value: The new valve value
        """
        ensure_folder(CONGRESS_EVENTS_LOG.parent)

        timestamp = now_iso()
        value_str = f"{value:.2f}" if value is not None else "null"
        event_line = f"{timestamp} hobbs.valve_change VALVE:{valve_id} ACTION:{action} VALUE:{value_str}\n"

        with open(CONGRESS_EVENTS_LOG, "a") as f:
            f.write(event_line)

        logger.info("Emitted valve event to Congress: hobbs.valve_change")

    def get_valves_count(self) -> int:
        """
        Get the number of known valves.

        Returns:
            Number of valves in state
        """
        return len(self.valve_state)

    def get_history_count(self) -> int:
        """
        Get the number of entries in valve history.

        Returns:
            Number of entries in valve_history.jsonl
        """
        return count_jsonl_entries(self.history_file)

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all valve states.

        Returns:
            Dict of all valve states
        """
        return self.valve_state.copy()


# Singleton instance
valve_controller = ValveController()
