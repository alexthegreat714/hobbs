"""
Schedule Engine for Hobbs Agent automation.

Manages scheduled automation tasks and time-based triggers.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime, time
from pathlib import Path

from config.settings import settings, logger


class ScheduleEngine:
    """
    Manages scheduled automation tasks.

    Schedules are loaded from config/automation_schedule.json and
    checked against the current time to determine due tasks.
    """

    def __init__(self):
        """Initialize the schedule engine."""
        self.schedule_path = settings.BASE_DIR / "config" / "automation_schedule.json"
        self.schedule: List[Dict[str, Any]] = []
        self._last_run: Dict[str, str] = {}  # track last run date per schedule id
        self._load_schedule()

    def _load_schedule(self) -> None:
        """Load schedule from the configuration file."""
        try:
            if self.schedule_path.exists():
                with open(self.schedule_path, "r") as f:
                    config = json.load(f)
                    self.schedule = config.get("schedule", [])
                logger.info(f"Loaded {len(self.schedule)} scheduled tasks")
            else:
                logger.warning(f"Schedule file not found: {self.schedule_path}")
                self.schedule = []
        except Exception as e:
            logger.error(f"Failed to load schedule: {e}")
            self.schedule = []

    def reload_schedule(self) -> int:
        """
        Reload schedule from configuration file.

        Returns:
            Number of scheduled tasks loaded
        """
        self._load_schedule()
        return len(self.schedule)

    def get_schedule(self) -> List[Dict[str, Any]]:
        """Get all scheduled tasks."""
        return self.schedule.copy()

    def get_schedule_by_id(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific scheduled task by ID."""
        for item in self.schedule:
            if item.get("id") == schedule_id:
                return item.copy()
        return None

    def get_due_tasks(self, current_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get tasks that are due to run.

        Args:
            current_time: Time to check against (defaults to now)

        Returns:
            List of due tasks with their definitions
        """
        if current_time is None:
            current_time = datetime.now()

        current_date = current_time.strftime("%Y-%m-%d")
        current_hour_minute = current_time.strftime("%H:%M")

        due_tasks = []

        for item in self.schedule:
            schedule_id = item.get("id")
            schedule_time = item.get("time")

            if not schedule_id or not schedule_time:
                continue

            # Check if already run today
            last_run_date = self._last_run.get(schedule_id)
            if last_run_date == current_date:
                continue

            # Check if time has passed
            if current_hour_minute >= schedule_time:
                due_tasks.append({
                    "schedule_id": schedule_id,
                    "scheduled_time": schedule_time,
                    "task": item.get("task", {}),
                    "due_at": current_time.isoformat(),
                })

        return due_tasks

    def mark_executed(self, schedule_id: str, execution_time: Optional[datetime] = None) -> None:
        """
        Mark a scheduled task as executed.

        Args:
            schedule_id: ID of the executed schedule
            execution_time: When it was executed (defaults to now)
        """
        if execution_time is None:
            execution_time = datetime.now()

        self._last_run[schedule_id] = execution_time.strftime("%Y-%m-%d")
        logger.info(f"Marked schedule '{schedule_id}' as executed")

    def reset_schedule(self, schedule_id: Optional[str] = None) -> None:
        """
        Reset execution tracking.

        Args:
            schedule_id: Specific schedule to reset, or None for all
        """
        if schedule_id:
            self._last_run.pop(schedule_id, None)
        else:
            self._last_run.clear()

    def get_next_scheduled_time(self, schedule_id: str) -> Optional[str]:
        """
        Get the next scheduled run time for a task.

        Args:
            schedule_id: ID of the schedule

        Returns:
            Time string (HH:MM) or None if not found
        """
        item = self.get_schedule_by_id(schedule_id)
        if item:
            return item.get("time")
        return None


# Singleton instance
schedule_engine = ScheduleEngine()
