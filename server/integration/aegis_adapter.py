"""
Aegis Adapter for Hobbs Agent.

High-level wrapper over aegis_client providing standardized
safety verification for all agent actions.
"""

from typing import Any, Dict, Optional
from datetime import datetime

from config.settings import logger
from server.actuators import aegis_client
from server.utils.time_ops import now_iso


class AegisAdapter:
    """
    High-level adapter for Aegis safety verification.

    Provides:
    - Standardized verification requests
    - Action-type specific verification
    - Verification caching (optional)
    - Audit logging
    """

    def __init__(self):
        """Initialize the Aegis adapter."""
        self._verification_cache = {}
        self._cache_ttl_seconds = 60  # Cache verifications for 1 minute
        self._audit_log = []
        self._max_audit_entries = 100

    def verify_action(
        self,
        action_type: str,
        payload: Dict[str, Any],
        source_agent: str = "hobbs"
    ) -> Dict[str, Any]:
        """
        Verify an action with Aegis.

        Args:
            action_type: Type of action (valve_control, sensor_override, etc.)
            payload: Action-specific payload
            source_agent: Agent requesting verification

        Returns:
            Verification result:
            {
                "verified": bool,
                "signature": str or None,
                "action_type": str,
                "timestamp": str
            }
        """
        # Build verification request based on action type
        verification_request = self._build_verification_request(
            action_type, payload, source_agent
        )

        # Request verification from Aegis
        result = self._request_verification(verification_request)

        # Log for audit
        self._log_verification(action_type, payload, result)

        return {
            "verified": result.get("verified", False),
            "signature": result.get("signature"),
            "action_type": action_type,
            "timestamp": result.get("timestamp", now_iso()),
            "details": result.get("details", {})
        }

    def _build_verification_request(
        self,
        action_type: str,
        payload: Dict[str, Any],
        source_agent: str
    ) -> Dict[str, Any]:
        """Build a verification request based on action type."""
        base_request = {
            "action_type": action_type,
            "source_agent": source_agent,
            "timestamp": now_iso(),
        }

        # Action-type specific fields
        if action_type == "valve_control":
            base_request.update({
                "valve_id": payload.get("valve_id"),
                "action": payload.get("action"),
                "value": payload.get("value"),
                "reason": payload.get("reason"),
                "source_task_id": payload.get("task_id", "unknown"),
            })

        elif action_type == "sensor_override":
            base_request.update({
                "sensor_id": payload.get("sensor_id"),
                "override_value": payload.get("value"),
                "duration": payload.get("duration"),
            })

        elif action_type == "automation_trigger":
            base_request.update({
                "rule_id": payload.get("rule_id"),
                "trigger_type": payload.get("trigger_type"),
                "affected_resources": payload.get("affected_resources", []),
            })

        elif action_type == "security_action":
            base_request.update({
                "security_level": payload.get("security_level"),
                "camera_id": payload.get("camera_id"),
                "action": payload.get("action"),
            })

        else:
            # Generic action - include all payload
            base_request["payload"] = payload

        return base_request

    def _request_verification(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Request verification from Aegis client."""
        try:
            result = aegis_client.request_verification(request)
            return result
        except Exception as e:
            logger.error(f"Aegis verification failed: {e}")
            return {
                "verified": False,
                "signature": None,
                "details": {"error": str(e)},
                "timestamp": now_iso()
            }

    def _log_verification(
        self,
        action_type: str,
        payload: Dict[str, Any],
        result: Dict[str, Any]
    ) -> None:
        """Log verification for audit purposes."""
        entry = {
            "timestamp": now_iso(),
            "action_type": action_type,
            "verified": result.get("verified", False),
            "signature": result.get("signature"),
        }
        self._audit_log.append(entry)

        # Trim if too long
        if len(self._audit_log) > self._max_audit_entries:
            self._audit_log = self._audit_log[-self._max_audit_entries:]

    def verify_valve_command(
        self,
        valve_id: str,
        action: str,
        value: Optional[float] = None,
        reason: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convenience method for valve command verification.

        Args:
            valve_id: Valve identifier
            action: Action to perform
            value: Optional value for set actions
            reason: Optional reason for the action
            task_id: Task ID for tracking

        Returns:
            Verification result
        """
        return self.verify_action(
            action_type="valve_control",
            payload={
                "valve_id": valve_id,
                "action": action,
                "value": value,
                "reason": reason,
                "task_id": task_id,
            }
        )

    def verify_automation_action(
        self,
        rule_id: str,
        trigger_type: str,
        affected_resources: list = None
    ) -> Dict[str, Any]:
        """
        Convenience method for automation action verification.

        Args:
            rule_id: Rule identifier
            trigger_type: Type of trigger
            affected_resources: List of affected resources

        Returns:
            Verification result
        """
        return self.verify_action(
            action_type="automation_trigger",
            payload={
                "rule_id": rule_id,
                "trigger_type": trigger_type,
                "affected_resources": affected_resources or [],
            }
        )

    def verify_security_action(
        self,
        security_level: str,
        action: str,
        camera_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convenience method for security action verification.

        Args:
            security_level: Security level (low, medium, high, critical)
            action: Security action to take
            camera_id: Optional camera ID

        Returns:
            Verification result
        """
        return self.verify_action(
            action_type="security_action",
            payload={
                "security_level": security_level,
                "action": action,
                "camera_id": camera_id,
            }
        )

    def get_audit_log(self, limit: int = 20) -> list:
        """Get recent verification audit log."""
        return self._audit_log[-limit:]

    def get_verification_stats(self) -> Dict[str, Any]:
        """Get verification statistics."""
        total = len(self._audit_log)
        verified = sum(1 for e in self._audit_log if e.get("verified"))

        return {
            "total_verifications": total,
            "verified_count": verified,
            "denied_count": total - verified,
            "verification_rate": (verified / total * 100) if total > 0 else 100.0
        }


# Singleton instance
aegis_adapter = AegisAdapter()
