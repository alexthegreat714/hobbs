"""
Trajectory Engine for Hobbs Agent Vision System.

Tracks object motion across multiple frames from the same camera
to infer movement direction and patterns.
"""

import json
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

from config.settings import logger


# Default camera direction mappings (can be overridden via config)
# Positive Y typically means moving down in image (toward camera/house)
DEFAULT_CAMERA_DIRECTIONS = {
    "default": {
        "toward_house": {"dy_min": 10},  # Moving down in frame
        "away_from_house": {"dy_max": -10},  # Moving up in frame
        "lateral_left": {"dx_max": -10, "dy_range": [-10, 10]},
        "lateral_right": {"dx_min": 10, "dy_range": [-10, 10]}
    }
}


class TrajectoryEngine:
    """
    Multi-frame object trajectory tracking engine.

    Tracks objects across frames to determine:
    - Movement direction (toward/away from house, lateral)
    - Speed estimation
    - Path prediction
    """

    def __init__(self):
        """Initialize the trajectory engine."""
        self.data_base = Path.home() / "Desktop" / "Engineering" / "Hobbs" / "data"
        self.cameras_dir = self.data_base / "cameras"
        self.vision_dir = self.data_base / "vision"
        self.history_file = self.vision_dir / "trajectory_history.jsonl"
        self.camera_config_file = self.vision_dir / "camera_directions.json"

        # In-memory tracking buffer (camera_id -> list of recent detections)
        self._tracking_buffer: Dict[str, List[Dict]] = defaultdict(list)
        self._buffer_max_size = 10
        self._buffer_max_age_seconds = 300  # 5 minutes

        self._ensure_paths()
        self._camera_directions = self._load_camera_directions()

    def _ensure_paths(self) -> None:
        """Ensure required directories exist."""
        self.vision_dir.mkdir(parents=True, exist_ok=True)

    def _load_camera_directions(self) -> Dict:
        """Load camera direction configuration."""
        if self.camera_config_file.exists():
            try:
                with open(self.camera_config_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load camera directions: {e}")
        return DEFAULT_CAMERA_DIRECTIONS

    def track(
        self,
        camera_id: str,
        timestamp: str,
        objects: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Track objects and compute trajectories.

        Args:
            camera_id: Camera identifier
            timestamp: Detection timestamp
            objects: List of detected objects with bounding boxes

        Returns:
            Trajectory analysis result:
            {
                "camera_id": str,
                "timestamp": str,
                "tracked_objects": [
                    {
                        "label": str,
                        "centroid": [x, y],
                        "movement": "toward_house" | "away_from_house" | "lateral" | "stationary" | "indeterminate",
                        "delta": [dx, dy],
                        "speed": float,
                        "confidence": float
                    }
                ],
                "overall_movement": str,
                "frame_count": int
            }
        """
        result = {
            "camera_id": camera_id,
            "timestamp": timestamp,
            "tracked_objects": [],
            "overall_movement": "indeterminate",
            "frame_count": 0
        }

        # Clean old entries from buffer
        self._clean_buffer(camera_id)

        # Get previous detections for this camera
        prev_detections = self._tracking_buffer[camera_id]
        result["frame_count"] = len(prev_detections) + 1

        # Process each detected object
        for obj in objects:
            if "bbox" not in obj:
                continue

            centroid = self._compute_centroid(obj["bbox"])
            label = obj.get("label", "object")

            tracked_obj = {
                "label": label,
                "centroid": centroid,
                "movement": "indeterminate",
                "delta": [0, 0],
                "speed": 0.0,
                "confidence": 0.0
            }

            # Try to match with previous frame
            if prev_detections:
                match = self._find_best_match(
                    label, centroid, prev_detections[-1].get("objects", [])
                )
                if match:
                    prev_centroid = match["centroid"]
                    dx = centroid[0] - prev_centroid[0]
                    dy = centroid[1] - prev_centroid[1]

                    tracked_obj["delta"] = [round(dx, 2), round(dy, 2)]
                    tracked_obj["speed"] = round((dx**2 + dy**2)**0.5, 2)
                    tracked_obj["movement"] = self._classify_movement(
                        camera_id, dx, dy
                    )
                    tracked_obj["confidence"] = match.get("confidence", 0.5)

            result["tracked_objects"].append(tracked_obj)

        # Determine overall movement
        if result["tracked_objects"]:
            movements = [t["movement"] for t in result["tracked_objects"]]
            # Count movement types
            movement_counts = {}
            for m in movements:
                movement_counts[m] = movement_counts.get(m, 0) + 1

            # Most common non-indeterminate movement
            for movement in ["toward_house", "away_from_house", "lateral", "stationary"]:
                if movement in movement_counts:
                    result["overall_movement"] = movement
                    break

        # Store current detection in buffer
        self._tracking_buffer[camera_id].append({
            "timestamp": timestamp,
            "objects": [
                {
                    "label": obj.get("label"),
                    "centroid": self._compute_centroid(obj["bbox"]),
                    "confidence": obj.get("confidence", 0.5)
                }
                for obj in objects if "bbox" in obj
            ]
        })

        # Trim buffer
        if len(self._tracking_buffer[camera_id]) > self._buffer_max_size:
            self._tracking_buffer[camera_id] = self._tracking_buffer[camera_id][-self._buffer_max_size:]

        # Save to history
        self._save_trajectory(result)

        return result

    def _compute_centroid(self, bbox: List[float]) -> List[float]:
        """Compute centroid from bounding box [x1, y1, x2, y2]."""
        x1, y1, x2, y2 = bbox
        return [round((x1 + x2) / 2, 2), round((y1 + y2) / 2, 2)]

    def _find_best_match(
        self,
        label: str,
        centroid: List[float],
        prev_objects: List[Dict]
    ) -> Optional[Dict]:
        """
        Find the best matching object from previous frame.

        Uses label matching and centroid proximity.
        """
        best_match = None
        best_distance = float('inf')
        max_distance = 200  # Maximum pixel distance for matching

        for prev_obj in prev_objects:
            if prev_obj.get("label") != label:
                continue

            prev_centroid = prev_obj.get("centroid", [0, 0])
            distance = (
                (centroid[0] - prev_centroid[0])**2 +
                (centroid[1] - prev_centroid[1])**2
            )**0.5

            if distance < best_distance and distance < max_distance:
                best_distance = distance
                best_match = prev_obj

        return best_match

    def _classify_movement(
        self,
        camera_id: str,
        dx: float,
        dy: float
    ) -> str:
        """
        Classify movement direction based on delta.

        Args:
            camera_id: Camera identifier for direction config
            dx: X-axis movement (positive = right)
            dy: Y-axis movement (positive = down)

        Returns:
            Movement classification string
        """
        # Get camera-specific config or default
        config = self._camera_directions.get(
            camera_id,
            self._camera_directions.get("default", DEFAULT_CAMERA_DIRECTIONS["default"])
        )

        # Check if stationary (minimal movement)
        if abs(dx) < 5 and abs(dy) < 5:
            return "stationary"

        # Check toward_house (typically moving down/toward camera)
        if dy > config.get("toward_house", {}).get("dy_min", 10):
            return "toward_house"

        # Check away_from_house (moving up/away from camera)
        if dy < config.get("away_from_house", {}).get("dy_max", -10):
            return "away_from_house"

        # Check lateral movement
        if abs(dx) > abs(dy):
            return "lateral"

        return "indeterminate"

    def _clean_buffer(self, camera_id: str) -> None:
        """Remove old entries from tracking buffer."""
        cutoff = datetime.utcnow() - timedelta(seconds=self._buffer_max_age_seconds)

        if camera_id in self._tracking_buffer:
            self._tracking_buffer[camera_id] = [
                entry for entry in self._tracking_buffer[camera_id]
                if self._parse_timestamp(entry.get("timestamp", "")) >= cutoff
            ]

    def _parse_timestamp(self, ts: str) -> datetime:
        """Parse ISO timestamp to datetime."""
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            return datetime.min

    def _save_trajectory(self, result: Dict[str, Any]) -> None:
        """Save trajectory result to history file."""
        try:
            # Build entry for each tracked object
            for obj in result["tracked_objects"]:
                entry = {
                    "timestamp": result["timestamp"],
                    "camera_id": result["camera_id"],
                    "object": obj["label"],
                    "movement": obj["movement"],
                    "delta": obj["delta"],
                    "confidence": obj["confidence"]
                }

                with open(self.history_file, "a") as f:
                    f.write(json.dumps(entry) + "\n")

        except Exception as e:
            logger.error(f"Failed to save trajectory: {e}")

    def get_recent_trajectories(
        self,
        camera_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get recent trajectory entries.

        Args:
            camera_id: Optional filter by camera
            limit: Maximum entries to return

        Returns:
            List of trajectory entries
        """
        entries = []

        if not self.history_file.exists():
            return entries

        try:
            with open(self.history_file, "r") as f:
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
            logger.error(f"Failed to load trajectories: {e}")

        return entries

    def get_history_count(self) -> int:
        """Get total trajectory history count."""
        if not self.history_file.exists():
            return 0
        try:
            with open(self.history_file, "r") as f:
                return sum(1 for _ in f)
        except Exception:
            return 0


# Singleton instance
trajectory_engine = TrajectoryEngine()
