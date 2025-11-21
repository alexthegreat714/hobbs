"""
Time operations utility for the Hobbs Agent.

Provides functions for timestamp generation and formatting.
"""

from datetime import datetime, timezone


def now_iso() -> str:
    """
    Get the current UTC timestamp in ISO8601 format.

    Returns:
        ISO8601 formatted timestamp string (e.g., "2025-01-21T15:30:45Z")
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_str() -> str:
    """
    Get today's date as a string.

    Returns:
        Date string in YYYY-MM-DD format (e.g., "2025-01-21")
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def timestamp_str() -> str:
    """
    Get the current timestamp as a filename-safe string.

    Returns:
        Timestamp string in YYYYMMDD_HHMMSS format (e.g., "20250121_153045")
    """
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def parse_iso(iso_string: str) -> datetime:
    """
    Parse an ISO8601 timestamp string to datetime.

    Args:
        iso_string: ISO8601 formatted timestamp string

    Returns:
        datetime object
    """
    # Handle both 'Z' suffix and '+00:00' format
    if iso_string.endswith("Z"):
        iso_string = iso_string[:-1] + "+00:00"

    return datetime.fromisoformat(iso_string)


def date_from_iso(iso_string: str) -> str:
    """
    Extract the date portion from an ISO8601 timestamp.

    Args:
        iso_string: ISO8601 formatted timestamp string

    Returns:
        Date string in YYYY-MM-DD format
    """
    dt = parse_iso(iso_string)
    return dt.strftime("%Y-%m-%d")
