"""
Query Engine for Hobbs Agent memory.

Provides keyword/tag-based retrieval and time-based aggregation
for searching the unified event memory.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

from config.settings import logger
from schemas.memory import MemoryEvent, IntruderStats


class QueryEngine:
    """
    Query engine for memory search and aggregation.

    Provides text search, filtering, and basic pattern analysis
    over the unified event memory.
    """

    def __init__(self):
        """Initialize the query engine."""
        self.data_base = Path.home() / "Desktop" / "Engineering" / "Hobbs" / "data"
        self.memory_dir = self.data_base / "memory"
        self.index_dir = self.data_base / "index"

        self.events_file = self.memory_dir / "events.jsonl"
        self.intruders_file = self.memory_dir / "intruders.jsonl"
        logger.info("QueryEngine initialized")

    def _load_events(self, file_path: Path) -> List[MemoryEvent]:
        """Load all events from a JSONL file."""
        events = []
        if not file_path.exists():
            return events

        try:
            with open(file_path, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        events.append(MemoryEvent(**data))
                    except Exception as e:
                        logger.warning(f"Failed to parse event: {e}")
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")

        return events

    def _parse_timestamp(self, ts: str) -> Optional[datetime]:
        """Parse an ISO8601 timestamp string."""
        try:
            # Handle various ISO8601 formats
            if ts.endswith("Z"):
                ts = ts[:-1] + "+00:00"
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            try:
                return datetime.fromisoformat(ts)
            except Exception:
                return None

    def search_memory(
        self,
        text_query: Optional[str] = None,
        source_filter: Optional[List[str]] = None,
        subtype_filter: Optional[List[str]] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        tag_filter: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[MemoryEvent]:
        """
        Search memory events with filtering.

        Args:
            text_query: Case-insensitive substring match in summary
            source_filter: List of sources to include
            subtype_filter: List of subtypes to include
            start_time: Start of time range (ISO8601)
            end_time: End of time range (ISO8601)
            tag_filter: Tags that must ALL be present
            limit: Maximum results to return

        Returns:
            List of matching MemoryEvents, sorted by timestamp descending
        """
        events = self._load_events(self.events_file)

        # Parse time bounds
        start_dt = self._parse_timestamp(start_time) if start_time else None
        end_dt = self._parse_timestamp(end_time) if end_time else None

        # Filter events
        filtered = []
        for event in events:
            # Time range filter
            if start_dt or end_dt:
                event_dt = self._parse_timestamp(event.timestamp)
                if event_dt:
                    if start_dt and event_dt < start_dt:
                        continue
                    if end_dt and event_dt > end_dt:
                        continue

            # Source filter
            if source_filter and event.source not in source_filter:
                continue

            # Subtype filter
            if subtype_filter and event.subtype not in subtype_filter:
                continue

            # Tag filter (all tags must be present)
            if tag_filter:
                event_tags_lower = [t.lower() for t in event.tags]
                if not all(t.lower() in event_tags_lower for t in tag_filter):
                    continue

            # Text query (case-insensitive substring match in summary)
            if text_query:
                if text_query.lower() not in event.summary.lower():
                    continue

            filtered.append(event)

        # Sort by timestamp descending
        filtered.sort(
            key=lambda e: self._parse_timestamp(e.timestamp) or datetime.min,
            reverse=True
        )

        # Apply limit
        return filtered[:limit]

    def get_intruder_stats(self, days: int = 30) -> IntruderStats:
        """
        Get statistics about intruder detections.

        Args:
            days: Number of days to analyze

        Returns:
            IntruderStats with aggregated intruder data
        """
        # Calculate cutoff time
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Load camera index for intruder data
        camera_index = self.index_dir / "camera_index.jsonl"

        total = 0
        by_camera: Dict[str, int] = defaultdict(int)
        by_hour: Dict[str, int] = defaultdict(int)
        last_seen: Optional[str] = None
        last_seen_dt: Optional[datetime] = None

        if camera_index.exists():
            try:
                with open(camera_index, "r") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            entry = json.loads(line)

                            # Only count intruder events
                            if not entry.get("intruder_detected", False):
                                continue

                            timestamp = entry.get("timestamp", "")
                            event_dt = self._parse_timestamp(timestamp)

                            # Skip events outside time range
                            if event_dt and event_dt < cutoff:
                                continue

                            total += 1

                            # Count by camera
                            camera_id = entry.get("camera_id", "unknown")
                            by_camera[camera_id] += 1

                            # Count by hour
                            if event_dt:
                                hour = event_dt.strftime("%H")
                                by_hour[hour] += 1

                                # Track last seen
                                if last_seen_dt is None or event_dt > last_seen_dt:
                                    last_seen_dt = event_dt
                                    last_seen = timestamp

                        except Exception as e:
                            logger.warning(f"Failed to parse camera entry for stats: {e}")
            except Exception as e:
                logger.error(f"Failed to read camera_index.jsonl: {e}")

        # Also check intruders.jsonl if it exists
        if self.intruders_file.exists():
            try:
                with open(self.intruders_file, "r") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            event = MemoryEvent(**data)

                            event_dt = self._parse_timestamp(event.timestamp)
                            if event_dt and event_dt < cutoff:
                                continue

                            # Only count if not already counted (dedup by checking metadata)
                            metadata = event.metadata
                            camera_id = metadata.get("camera_id", "unknown")

                            # This is a simplified approach - in production
                            # we'd deduplicate by event_id
                            # For now, we just use the index file stats

                        except Exception:
                            pass
            except Exception:
                pass

        return IntruderStats(
            total_intruders=total,
            by_camera=dict(by_camera),
            by_hour=dict(by_hour),
            last_seen=last_seen
        )

    def get_sensor_trends(
        self,
        sensor_type: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get trend data for a sensor type.

        Args:
            sensor_type: Type of sensor to analyze
            days: Number of days to analyze

        Returns:
            Dictionary with trend statistics
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        events = self.search_memory(
            source_filter=["sensor"],
            subtype_filter=[sensor_type],
            limit=1000
        )

        values = []
        for event in events:
            event_dt = self._parse_timestamp(event.timestamp)
            if event_dt and event_dt < cutoff:
                continue

            value = event.metadata.get("value")
            if isinstance(value, (int, float)):
                values.append(value)

        if not values:
            return {
                "sensor_type": sensor_type,
                "days": days,
                "count": 0,
                "min": None,
                "max": None,
                "avg": None,
            }

        return {
            "sensor_type": sensor_type,
            "days": days,
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
        }


# Singleton instance
query_engine = QueryEngine()
