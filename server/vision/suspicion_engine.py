"""
Suspicion Engine for Hobbs Agent Vision System.

Computes suspiciousness scores for detected events based on
multiple factors including object type, time, movement, and history.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

from config.settings import logger


# Suspicion scoring weights
SUSPICION_WEIGHTS = {
    "human_detected": 0.5,
    "night_time": 0.3,
    "toward_house": 0.2,
    "repeated_presence": 0.25,
    "group_pattern": 0.4,
    "has_text_or_plate": 0.15,
    "vehicle_at_night": 0.2,
    "unknown_object": 0.1,
    "fast_movement": 0.15,
    "multiple_cameras": 0.2
}


class SuspicionEngine:
    """
    Suspiciousness scoring engine for security events.

    Computes scores based on:
    - Object type (human = high)
    - Time of day (night = higher)
    - Movement direction (toward house = higher)
    - Repeated presence within 24 hours
    - Group patterns (multiple people)
    - OCR detection (potential license plates)
    """

    def __init__(self):
        """Initialize the suspicion engine."""
        self.data_base = Path.home() / "Desktop" / "Engineering" / "Hobbs" / "data"
        self.vision_dir = self.data_base / "vision"
        self.scores_file = self.vision_dir / "suspicion_scores.jsonl"

        # Recent events cache for repeated presence detection
        self._recent_events: Dict[str, List[Dict]] = defaultdict(list)
        self._cache_hours = 24

        self._ensure_paths()

    def _ensure_paths(self) -> None:
        """Ensure required directories exist."""
        self.vision_dir.mkdir(parents=True, exist_ok=True)

    def compute_suspicion(
        self,
        event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compute suspiciousness score for an event.

        Args:
            event: Detection event containing:
                - objects: List of detected objects
                - trajectory: Trajectory analysis result
                - ocr_text: Extracted OCR text
                - timestamp: Event timestamp
                - camera_id: Camera identifier
                - tags: List of tags

        Returns:
            Suspicion result:
            {
                "score": float (0.0 - 1.0),
                "reasons": ["human detected", "night time", ...],
                "risk_level": "low" | "medium" | "high" | "critical",
                "factors": {...}
            }
        """
        score = 0.0
        reasons = []
        factors = {}

        objects = event.get("objects", [])
        trajectory = event.get("trajectory", {})
        ocr_text = event.get("ocr_text", "")
        timestamp = event.get("timestamp", "")
        camera_id = event.get("camera_id", "unknown")
        tags = event.get("tags", [])

        # Factor 1: Human detected
        human_count = sum(1 for o in objects if o.get("label") == "person")
        if human_count > 0:
            score += SUSPICION_WEIGHTS["human_detected"]
            reasons.append(f"human detected ({human_count})")
            factors["human_detected"] = True

        # Factor 2: Night time (22:00 - 05:00)
        is_night = self._is_night_time(timestamp)
        if is_night:
            score += SUSPICION_WEIGHTS["night_time"]
            reasons.append("night time activity")
            factors["night_time"] = True

        # Factor 3: Movement toward house
        movement = trajectory.get("overall_movement", "indeterminate")
        if movement == "toward_house":
            score += SUSPICION_WEIGHTS["toward_house"]
            reasons.append("moving toward house")
            factors["toward_house"] = True

        # Factor 4: Repeated presence within 24 hours
        repeated = self._check_repeated_presence(camera_id, objects, timestamp)
        if repeated:
            score += SUSPICION_WEIGHTS["repeated_presence"]
            reasons.append("repeated presence in 24h")
            factors["repeated_presence"] = True

        # Factor 5: Group pattern (multiple people)
        if human_count > 1:
            score += SUSPICION_WEIGHTS["group_pattern"]
            reasons.append(f"group of {human_count} people")
            factors["group_pattern"] = True

        # Factor 6: OCR text with potential identifying info
        if ocr_text and self._has_identifying_text(ocr_text):
            score += SUSPICION_WEIGHTS["has_text_or_plate"]
            reasons.append("text/plate detected")
            factors["has_text"] = True

        # Factor 7: Vehicle at night
        has_vehicle = any(o.get("label") in ["car", "truck", "bus", "motorcycle"] for o in objects)
        if has_vehicle and is_night:
            score += SUSPICION_WEIGHTS["vehicle_at_night"]
            reasons.append("vehicle at night")
            factors["vehicle_at_night"] = True

        # Factor 8: Fast movement
        if trajectory.get("tracked_objects"):
            max_speed = max(
                (t.get("speed", 0) for t in trajectory["tracked_objects"]),
                default=0
            )
            if max_speed > 50:  # Pixels per frame
                score += SUSPICION_WEIGHTS["fast_movement"]
                reasons.append("fast movement detected")
                factors["fast_movement"] = True

        # Clamp score to 1.0
        score = min(score, 1.0)

        # Determine risk level
        risk_level = self._get_risk_level(score)

        result = {
            "score": round(score, 3),
            "reasons": reasons,
            "risk_level": risk_level,
            "factors": factors,
            "timestamp": timestamp,
            "camera_id": camera_id
        }

        # Update recent events cache
        self._update_recent_events(camera_id, objects, timestamp)

        # Save to history
        self._save_score(result)

        return result

    def _is_night_time(self, timestamp: str) -> bool:
        """Check if timestamp is during night hours (22:00 - 05:00)."""
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            hour = dt.hour
            return hour >= 22 or hour < 5
        except Exception:
            return False

    def _check_repeated_presence(
        self,
        camera_id: str,
        objects: List[Dict],
        timestamp: str
    ) -> bool:
        """Check if similar objects were detected recently."""
        try:
            current_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).replace(tzinfo=None)
            cutoff = current_time - timedelta(hours=self._cache_hours)

            # Get labels from current detection
            current_labels = {o.get("label") for o in objects}

            # Check recent events for this camera
            recent = self._recent_events.get(camera_id, [])
            for event in recent:
                event_time = event.get("time")
                if event_time and event_time >= cutoff:
                    event_labels = set(event.get("labels", []))
                    # Check for overlap in detected object types
                    if current_labels & event_labels:
                        return True

            return False
        except Exception:
            return False

    def _update_recent_events(
        self,
        camera_id: str,
        objects: List[Dict],
        timestamp: str
    ) -> None:
        """Update recent events cache."""
        try:
            current_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).replace(tzinfo=None)
            labels = [o.get("label") for o in objects if o.get("label")]

            self._recent_events[camera_id].append({
                "time": current_time,
                "labels": labels
            })

            # Clean old entries
            cutoff = current_time - timedelta(hours=self._cache_hours)
            self._recent_events[camera_id] = [
                e for e in self._recent_events[camera_id]
                if e.get("time") and e["time"] >= cutoff
            ]

        except Exception as e:
            logger.error(f"Failed to update recent events: {e}")

    def _has_identifying_text(self, text: str) -> bool:
        """Check if OCR text contains potential identifying information."""
        if not text:
            return False

        # Check for alphanumeric patterns (license plates, etc.)
        import re

        # License plate pattern (simplified)
        if re.search(r'[A-Z0-9]{2,3}[\s-]?[A-Z0-9]{2,4}', text.upper()):
            return True

        # Contains numbers and letters mixed
        has_letters = any(c.isalpha() for c in text)
        has_numbers = any(c.isdigit() for c in text)
        if has_letters and has_numbers and len(text) >= 4:
            return True

        return False

    def _get_risk_level(self, score: float) -> str:
        """Convert score to risk level."""
        if score >= 0.75:
            return "critical"
        elif score >= 0.5:
            return "high"
        elif score >= 0.25:
            return "medium"
        return "low"

    def _save_score(self, result: Dict[str, Any]) -> None:
        """Save suspicion score to history file."""
        try:
            with open(self.scores_file, "a") as f:
                f.write(json.dumps(result, default=str) + "\n")
        except Exception as e:
            logger.error(f"Failed to save suspicion score: {e}")

    def get_recent_scores(
        self,
        camera_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get recent suspicion scores.

        Args:
            camera_id: Optional filter by camera
            limit: Maximum entries to return

        Returns:
            List of suspicion score entries
        """
        entries = []

        if not self.scores_file.exists():
            return entries

        try:
            with open(self.scores_file, "r") as f:
                lines = f.readlines()

            for line in reversed(lines):
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    if camera_id is None or entry.get("camera_id") == camera_id:
                        entries.append(entry)
                        if len(entries) >= limit:
                            break
                except Exception:
                    continue

        except Exception as e:
            logger.error(f"Failed to load scores: {e}")

        return entries

    def get_scores_count(self) -> int:
        """Get total suspicion scores count."""
        if not self.scores_file.exists():
            return 0
        try:
            with open(self.scores_file, "r") as f:
                return sum(1 for _ in f)
        except Exception:
            return 0

    def get_suspicious_count_today(self) -> int:
        """Get count of suspicious events (score >= 0.5) today."""
        count = 0
        today = datetime.utcnow().date()

        if not self.scores_file.exists():
            return 0

        try:
            with open(self.scores_file, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        ts = entry.get("timestamp", "")
                        score = entry.get("score", 0)

                        if score >= 0.5:
                            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                            if dt.date() == today:
                                count += 1
                    except Exception:
                        continue
        except Exception:
            pass

        return count

    def get_average_score_last_24h(self) -> float:
        """Get average suspicion score over last 24 hours."""
        scores = []
        cutoff = datetime.utcnow() - timedelta(hours=24)

        if not self.scores_file.exists():
            return 0.0

        try:
            with open(self.scores_file, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        ts = entry.get("timestamp", "")
                        score = entry.get("score", 0)

                        dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
                        if dt >= cutoff:
                            scores.append(score)
                    except Exception:
                        continue
        except Exception:
            pass

        if not scores:
            return 0.0

        return round(sum(scores) / len(scores), 3)


# Singleton instance
suspicion_engine = SuspicionEngine()
