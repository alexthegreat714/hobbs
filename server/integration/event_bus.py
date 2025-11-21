"""
Event Bus for Hobbs Agent Multi-Agent Integration.

Centralizes inter-agent event handling and publishing.
Manages routing of incoming events and outgoing event publication.
"""

import json
from typing import Any, Dict, Optional
from datetime import datetime
from pathlib import Path

from config.settings import logger
from schemas.shared import TaskEnvelope


# Event log paths
CONGRESS_EVENTS_LOG = Path.home() / "Desktop" / "Engineering" / "Congress" / "memory" / "hobbs_events.log"


class EventBus:
    """
    Central event bus for inter-agent communication.

    Handles:
    - Publishing events to Congress event log
    - Routing incoming events to appropriate handlers
    - Event type registration and dispatch
    """

    def __init__(self):
        """Initialize the event bus."""
        self._handlers = {}
        self._event_history = []
        self._max_history = 100
        self._setup_default_handlers()

    def _setup_default_handlers(self) -> None:
        """Set up default event type handlers."""
        # Will be populated when handlers are registered
        pass

    def register_handler(self, event_type: str, handler_func) -> None:
        """
        Register a handler function for an event type.

        Args:
            event_type: The event type to handle
            handler_func: Function to call when event is received
        """
        self._handlers[event_type] = handler_func
        logger.info(f"Registered handler for event type: {event_type}")

    def publish_event(
        self,
        event: Dict[str, Any],
        target: Optional[str] = None
    ) -> bool:
        """
        Publish an event to the Congress event log.

        Args:
            event: Event data dictionary
            target: Optional target agent (for future routing)

        Returns:
            True if event was published successfully
        """
        try:
            # Ensure Congress memory directory exists
            CONGRESS_EVENTS_LOG.parent.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.utcnow().isoformat() + "Z"
            event_type = event.get("type", "unknown")
            source = event.get("source", "hobbs")

            # Build event line
            event_data = json.dumps(event, default=str)
            event_line = f"{timestamp} {source}.{event_type} {event_data}\n"

            with open(CONGRESS_EVENTS_LOG, "a") as f:
                f.write(event_line)

            logger.info(f"Published event: {source}.{event_type}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return False

    def handle_incoming_event(self, envelope: TaskEnvelope) -> Dict[str, Any]:
        """
        Handle an incoming event from another agent.

        Routes the event to the appropriate handler based on type.

        Args:
            envelope: The TaskEnvelope containing the event

        Returns:
            Result dictionary with handling status
        """
        event_type = envelope.type
        source = envelope.source
        payload = envelope.payload

        logger.info(f"Handling incoming event: {event_type} from {source}")

        # Track event in history
        self._track_event(envelope)

        # Route to appropriate handler
        result = self._route_event(event_type, envelope)

        return {
            "handled": True,
            "event_type": event_type,
            "source": source,
            "result": result
        }

    def _route_event(self, event_type: str, envelope: TaskEnvelope) -> Dict[str, Any]:
        """
        Route an event to its handler based on type.

        Args:
            event_type: The event type
            envelope: The full event envelope

        Returns:
            Handler result or default response
        """
        # Check for registered handler
        if event_type in self._handlers:
            try:
                return self._handlers[event_type](envelope)
            except Exception as e:
                logger.error(f"Handler error for {event_type}: {e}")
                return {"error": str(e)}

        # Default routing based on event type patterns
        result = {"action": "default_handling"}

        # Weather events
        if event_type == "weather.alert":
            result = self._handle_weather_alert(envelope)

        # Security events
        elif event_type == "security.alert":
            result = self._handle_security_alert(envelope)

        # Sensor events
        elif event_type == "farm.sensor.update":
            result = self._handle_sensor_update(envelope)

        # Sky commands
        elif event_type == "sky.command":
            result = self._handle_sky_command(envelope)

        # Memory rebuild
        elif event_type in ["hobbs.memory.rebuild", "memory.rebuild"]:
            result = self._handle_memory_rebuild(envelope)

        # Learning trigger
        elif event_type == "learning.trigger":
            result = self._handle_learning_trigger(envelope)

        # Experiment validation (future use)
        elif event_type == "aero.experiment.validation.ready":
            result = self._handle_experiment_validation(envelope)

        # Policy update
        elif event_type == "congress.policy.update":
            result = self._handle_policy_update(envelope)

        else:
            logger.warning(f"No handler for event type: {event_type}")
            result = {"action": "unhandled", "event_type": event_type}

        return result

    def _handle_weather_alert(self, envelope: TaskEnvelope) -> Dict[str, Any]:
        """Handle weather alert from Apollo."""
        from server.automation.automation_engine import automation_engine

        payload = envelope.payload
        alert_type = payload.get("alert_type", "unknown")

        # Process through automation engine
        automation_result = automation_engine.process_event(
            event_type="weather.alert",
            event_payload=payload
        )

        logger.info(f"Processed weather alert: {alert_type}")
        triggered = automation_result.get("triggered_actions", [])
        return {
            "action": "weather_alert_processed",
            "alert_type": alert_type,
            "automation_triggered": len(triggered) > 0 if isinstance(triggered, list) else triggered > 0
        }

    def _handle_security_alert(self, envelope: TaskEnvelope) -> Dict[str, Any]:
        """Handle security alert from Aegis."""
        from server.automation.automation_engine import automation_engine

        payload = envelope.payload

        # Process through automation engine
        automation_result = automation_engine.process_event(
            event_type="security.alert",
            event_payload=payload
        )

        logger.info("Processed security alert from Aegis")
        triggered = automation_result.get("triggered_actions", [])
        return {
            "action": "security_alert_processed",
            "automation_triggered": len(triggered) > 0 if isinstance(triggered, list) else triggered > 0
        }

    def _handle_sensor_update(self, envelope: TaskEnvelope) -> Dict[str, Any]:
        """Handle sensor update event."""
        from server.automation.automation_engine import automation_engine

        payload = envelope.payload
        sensor_type = payload.get("sensor_type", "unknown")
        value = payload.get("value")

        # Process through automation if numeric value
        if isinstance(value, (int, float)):
            automation_engine.process_sensor_data(
                sensor_id=envelope.task_id,
                sensor_type=sensor_type,
                value=float(value)
            )

        return {
            "action": "sensor_update_processed",
            "sensor_type": sensor_type
        }

    def _handle_sky_command(self, envelope: TaskEnvelope) -> Dict[str, Any]:
        """Handle command from Sky."""
        payload = envelope.payload
        command = payload.get("command", "unknown")

        logger.info(f"Received Sky command: {command}")

        # Route based on command type
        if command == "status":
            return {"action": "status_requested"}
        elif command == "learning_cycle":
            return self._handle_learning_trigger(envelope)
        elif command == "memory_rebuild":
            return self._handle_memory_rebuild(envelope)
        else:
            return {"action": "sky_command_received", "command": command}

    def _handle_memory_rebuild(self, envelope: TaskEnvelope) -> Dict[str, Any]:
        """Handle memory rebuild request."""
        from server.memory.memory_manager import memory_manager

        counts = memory_manager.rebuild_full_memory()
        logger.info(f"Memory rebuild complete: {counts}")

        return {
            "action": "memory_rebuilt",
            "counts": counts
        }

    def _handle_learning_trigger(self, envelope: TaskEnvelope) -> Dict[str, Any]:
        """Handle learning cycle trigger."""
        from server.learning.learning_engine import learning_engine

        result = learning_engine.run_full_learning_cycle()
        logger.info("Learning cycle triggered via event")

        return {
            "action": "learning_cycle_complete",
            "events_analyzed": result.get("events_analyzed", 0)
        }

    def _handle_experiment_validation(self, envelope: TaskEnvelope) -> Dict[str, Any]:
        """Handle experiment validation ready event (future use)."""
        logger.info("Received experiment validation ready event")
        return {"action": "experiment_validation_acknowledged"}

    def _handle_policy_update(self, envelope: TaskEnvelope) -> Dict[str, Any]:
        """Handle policy update from Congress."""
        from server.integration.congress_client import congress_client

        policies = congress_client.load_policies()
        congress_client.apply_policies(policies)

        logger.info("Policy update processed")
        return {"action": "policies_updated"}

    def _track_event(self, envelope: TaskEnvelope) -> None:
        """Track event in history for debugging/metrics."""
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": envelope.type,
            "source": envelope.source,
            "task_id": envelope.task_id
        }
        self._event_history.append(entry)

        # Trim history if too long
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

    def get_recent_events(self, limit: int = 20) -> list:
        """Get recent event history."""
        return self._event_history[-limit:]


# Singleton instance
event_bus = EventBus()
