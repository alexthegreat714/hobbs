"""
Aegis Client stub for the Hobbs Agent.

This module represents the call to Aegis for safety verification.
Currently returns simulated verification responses.

In later phases, this will be replaced with real HTTP calls
to Aegis' /verify endpoint.
"""

from typing import Any, Dict

from config.settings import logger
from server.utils.time_ops import now_iso


def request_verification(command: Dict[str, Any]) -> Dict[str, Any]:
    """
    Request verification from Aegis for a control command.

    This is a STUB implementation that simulates Aegis verification.
    In production, this would make an HTTP call to Aegis.

    Args:
        command: Dictionary containing the command details to verify
            Expected keys:
            - valve_id: str
            - action: str
            - value: float or None
            - reason: str or None
            - source_task_id: str
            - source_agent: str

    Returns:
        Dict with verification result:
            - verified: bool
            - signature: str (token from Aegis)
            - details: dict with additional info
            - timestamp: str (ISO8601)
    """
    logger.info(f"Aegis verification request (stub): {command}")

    # Extract command details for logging
    valve_id = command.get("valve_id", "unknown")
    action = command.get("action", "unknown")
    source = command.get("source_agent", "unknown")

    # STUB: Always return verified=True
    # In production, this would:
    # 1. Make HTTP POST to Aegis /verify endpoint
    # 2. Include command details in request body
    # 3. Wait for Aegis response
    # 4. Return actual verification result

    verification_result = {
        "verified": True,
        "signature": f"aegis-simulated-token-{now_iso().replace(':', '-')}",
        "details": {
            "reason": "PHASE_5_STUB_VERIFICATION_ONLY",
            "valve_id": valve_id,
            "action": action,
            "requested_by": source,
        },
        "timestamp": now_iso(),
    }

    logger.info(f"Aegis verification result (stub): verified={verification_result['verified']}")
    return verification_result


def request_denial_simulation(command: Dict[str, Any], reason: str) -> Dict[str, Any]:
    """
    Simulate a denial response from Aegis (for testing).

    Args:
        command: Dictionary containing the command details
        reason: Reason for denial

    Returns:
        Dict with denial result
    """
    logger.warning(f"Aegis verification DENIED (simulated): {reason}")

    return {
        "verified": False,
        "signature": None,
        "details": {
            "reason": reason,
            "valve_id": command.get("valve_id", "unknown"),
            "action": command.get("action", "unknown"),
        },
        "timestamp": now_iso(),
    }
