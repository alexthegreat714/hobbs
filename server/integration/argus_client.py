"""
Argus Client for Hobbs Agent.

Provides metrics collection and publishing for system monitoring.
"""

import json
import os
from typing import Any, Dict
from datetime import datetime
from pathlib import Path

from config.settings import settings, logger


# Argus paths
ARGUS_METRICS_DIR = Path.home() / "Desktop" / "Engineering" / "Argus" / "metrics"
HOBBS_METRICS_FILE = ARGUS_METRICS_DIR / "hobbs_metrics.jsonl"

# Local metrics cache
HOBBS_DATA_DIR = Path.home() / "Desktop" / "Engineering" / "Hobbs" / "data"
METRICS_CACHE_FILE = HOBBS_DATA_DIR / "metrics_cache.json"


class ArgusClient:
    """
    Client for communicating with Argus monitoring system.

    Handles:
    - Metrics collection (CPU, memory, event counts)
    - Metrics publishing to Argus
    - Health status reporting
    """

    def __init__(self):
        """Initialize the Argus client."""
        self._startup_time = datetime.utcnow()
        self._last_metrics = {}
        self._ensure_paths()

    def _ensure_paths(self) -> None:
        """Ensure required directories exist."""
        ARGUS_METRICS_DIR.mkdir(parents=True, exist_ok=True)
        HOBBS_DATA_DIR.mkdir(parents=True, exist_ok=True)

    def collect_metrics(self) -> Dict[str, Any]:
        """
        Collect current system metrics.

        Returns:
            Dictionary containing:
            - cpu_usage: float (placeholder)
            - mem_usage: float (placeholder)
            - events_today: dict with counts by type
            - suspicious_events_today: int
            - uptime_estimate: float (hours since startup)
        """
        metrics = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "agent": settings.AGENT_NAME,
            "version": settings.VERSION,
            "cpu_usage": self._get_cpu_usage(),
            "mem_usage": self._get_memory_usage(),
            "events_today": self._get_events_today(),
            "suspicious_events_today": self._get_suspicious_events_today(),
            "uptime_estimate": self._get_uptime_hours(),
            "health_status": self._get_health_status()
        }

        self._last_metrics = metrics
        return metrics

    def _get_cpu_usage(self) -> float:
        """
        Get CPU usage percentage.

        Returns:
            CPU usage as float (0.0-100.0), or -1 if unavailable
        """
        try:
            # Try psutil if available
            import psutil
            return psutil.cpu_percent(interval=0.1)
        except ImportError:
            pass

        # Fallback: try reading from /proc/stat (Linux)
        try:
            with open('/proc/loadavg', 'r') as f:
                load_avg = float(f.read().split()[0])
                # Normalize to percentage (rough estimate)
                cpu_count = os.cpu_count() or 1
                return min(100.0, (load_avg / cpu_count) * 100)
        except Exception:
            pass

        return -1.0  # Unavailable

    def _get_memory_usage(self) -> float:
        """
        Get memory usage percentage.

        Returns:
            Memory usage as float (0.0-100.0), or -1 if unavailable
        """
        try:
            # Try psutil if available
            import psutil
            mem = psutil.virtual_memory()
            return mem.percent
        except ImportError:
            pass

        # Fallback: try reading from /proc/meminfo (Linux)
        try:
            meminfo = {}
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        meminfo[parts[0].rstrip(':')] = int(parts[1])

            total = meminfo.get('MemTotal', 0)
            available = meminfo.get('MemAvailable', meminfo.get('MemFree', 0))
            if total > 0:
                used = total - available
                return (used / total) * 100
        except Exception:
            pass

        return -1.0  # Unavailable

    def _get_events_today(self) -> Dict[str, int]:
        """
        Get event counts for today by type.

        Returns:
            Dictionary with event counts
        """
        counts = {
            "sensors": 0,
            "weather": 0,
            "camera": 0,
            "valves": 0,
            "automation": 0
        }

        try:
            from server.sensors.sensor_manager import sensor_manager
            from server.weather.weather_manager import weather_manager
            from server.camera.camera_manager import camera_manager
            from server.actuators.valve_controller import valve_controller
            from server.automation.automation_engine import automation_engine

            counts["sensors"] = sensor_manager.get_sensors_today_count()
            counts["weather"] = weather_manager.get_forecasts_today_count()
            counts["camera"] = camera_manager.get_camera_events_today_count()

            # Valve events today (approximate from history)
            counts["valves"] = self._count_today_entries_from_jsonl(
                HOBBS_DATA_DIR / "actuators" / "valve_history.jsonl"
            )

            # Automation events today
            counts["automation"] = self._count_today_entries_from_jsonl(
                HOBBS_DATA_DIR / "automation" / "automation_history.jsonl"
            )

        except Exception as e:
            logger.warning(f"Error collecting event counts: {e}")

        return counts

    def _count_today_entries_from_jsonl(self, filepath: Path) -> int:
        """Count entries from today in a JSONL file."""
        if not filepath.exists():
            return 0

        today = datetime.utcnow().date().isoformat()
        count = 0

        try:
            with open(filepath, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        ts = entry.get("timestamp", "")
                        if ts.startswith(today):
                            count += 1
                    except Exception:
                        continue
        except Exception:
            pass

        return count

    def _get_suspicious_events_today(self) -> int:
        """Get count of suspicious events today."""
        try:
            from server.vision.suspicion_engine import suspicion_engine
            return suspicion_engine.get_suspicious_count_today()
        except Exception:
            return 0

    def _get_uptime_hours(self) -> float:
        """Get estimated uptime in hours."""
        delta = datetime.utcnow() - self._startup_time
        return round(delta.total_seconds() / 3600, 2)

    def _get_health_status(self) -> str:
        """
        Determine overall health status.

        Returns:
            "healthy", "degraded", or "unhealthy"
        """
        try:
            # Check basic functionality
            from server.sensors.sensor_manager import sensor_manager
            from server.weather.weather_manager import weather_manager

            # If we can access managers, we're at least functional
            _ = sensor_manager.get_index_size()
            _ = weather_manager.get_index_size()

            return "healthy"
        except Exception:
            return "degraded"

    def publish_metrics(self, metrics: Dict[str, Any]) -> bool:
        """
        Publish metrics to Argus.

        Appends metrics to the Argus metrics file.

        Args:
            metrics: Metrics dictionary to publish

        Returns:
            True if metrics were published successfully
        """
        try:
            self._ensure_paths()

            with open(HOBBS_METRICS_FILE, "a") as f:
                f.write(json.dumps(metrics) + "\n")

            # Also cache locally
            with open(METRICS_CACHE_FILE, "w") as f:
                json.dump(metrics, f, indent=2)

            logger.debug("Metrics published to Argus")
            return True

        except Exception as e:
            logger.error(f"Failed to publish metrics: {e}")
            return False

    def get_last_metrics(self) -> Dict[str, Any]:
        """Get the last collected metrics."""
        if self._last_metrics:
            return self._last_metrics

        # Try to load from cache
        if METRICS_CACHE_FILE.exists():
            try:
                with open(METRICS_CACHE_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass

        return {}

    def get_metrics_count(self) -> int:
        """Get total metrics entries published."""
        if not HOBBS_METRICS_FILE.exists():
            return 0
        try:
            with open(HOBBS_METRICS_FILE, "r") as f:
                return sum(1 for _ in f)
        except Exception:
            return 0

    @property
    def last_metrics(self) -> Dict[str, Any]:
        """Get the last collected metrics as property."""
        return self.get_last_metrics()


# Singleton instance
argus_client = ArgusClient()
