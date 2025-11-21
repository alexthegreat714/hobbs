"""
Camera Manager for the Hobbs Agent.

Coordinates:
- Camera image storage
- Object classification
- Direction estimation
- Camera index management
- Event emission to Congress
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from server.utils.file_ops import (
    ensure_folder,
    append_jsonl,
    count_files_in_folder,
    count_jsonl_entries,
)
from server.utils.time_ops import now_iso, today_str, timestamp_str
from server.utils.image_ops import (
    decode_base64_to_file,
    download_image,
    ensure_camera_folder,
    get_cameras_dir,
    get_camera_index_path,
)
from server.camera.classifier_stub import classify
from server.camera.direction_stub import estimate_direction
from config.settings import logger


# Data directories
DATA_DIR = Path.home() / "Desktop" / "Engineering" / "Hobbs" / "data"
CAMERAS_DIR = DATA_DIR / "cameras"
INDEX_DIR = DATA_DIR / "index"
CAMERA_INDEX_PATH = INDEX_DIR / "camera_index.jsonl"

# Congress event log
CONGRESS_EVENTS_LOG = Path.home() / "Desktop" / "Engineering" / "Congress" / "memory" / "hobbs_events.log"


class CameraManager:
    """
    Manages camera image storage, classification, and indexing.
    """

    def __init__(self):
        """Initialize the camera manager."""
        self.cameras_dir = CAMERAS_DIR
        self.index_path = CAMERA_INDEX_PATH

    def save_image(
        self,
        camera_id: str,
        image_data: Optional[str] = None,
        image_url: Optional[str] = None,
        filename_prefix: str = "",
    ) -> Optional[Path]:
        """
        Save an image from base64 data or URL.

        Args:
            camera_id: The camera identifier
            image_data: Base64 encoded image data (optional)
            image_url: URL to download image from (optional)
            filename_prefix: Optional prefix for filename

        Returns:
            Path to saved image, or None if save failed
        """
        # Ensure camera folder exists
        camera_folder = ensure_camera_folder(camera_id)

        # Generate filename
        ts = timestamp_str()
        if filename_prefix:
            filename = f"{filename_prefix}_{ts}.png"
        else:
            filename = f"{ts}.png"
        filepath = camera_folder / filename

        # Save from base64 or URL
        if image_data:
            try:
                saved_path = decode_base64_to_file(image_data, filepath)
                logger.info(f"Saved image from base64 to: {saved_path}")
                return saved_path
            except Exception as e:
                logger.error(f"Failed to save base64 image: {e}")
                return None

        elif image_url:
            saved_path = download_image(image_url, filepath)
            if saved_path:
                logger.info(f"Saved image from URL to: {saved_path}")
            return saved_path

        else:
            logger.error("No image_data or image_url provided")
            return None

    def classify_image(self, image_path: str) -> Dict[str, Any]:
        """
        Classify an object in an image.

        Args:
            image_path: Path to the image file

        Returns:
            Classification result dict with 'object' and 'confidence'
        """
        return classify(image_path)

    def determine_direction(self, camera_id: str) -> Dict[str, Any]:
        """
        Determine the direction of movement for a camera.

        Args:
            camera_id: The camera identifier

        Returns:
            Direction result dict with 'direction' and 'confidence'
        """
        return estimate_direction(camera_id)

    def process_detection(
        self,
        camera_id: str,
        image_data: Optional[str] = None,
        image_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], Optional[Path]]:
        """
        Process a complete intruder detection request.

        Args:
            camera_id: The camera identifier
            image_data: Base64 encoded image data (optional)
            image_url: URL to download image from (optional)
            metadata: Additional metadata (optional)

        Returns:
            Tuple of (result_dict, image_path)
        """
        # Save the image
        image_path = self.save_image(camera_id, image_data, image_url)

        if not image_path:
            return {
                "ok": False,
                "error": "Failed to save image",
                "object": None,
                "confidence": 0.0,
                "direction": None,
                "dir_confidence": 0.0,
            }, None

        # Classify the object
        classification = self.classify_image(str(image_path))

        # Determine direction
        direction = self.determine_direction(camera_id)

        # Create index entry
        relative_path = str(image_path.relative_to(DATA_DIR))
        index_entry = {
            "timestamp": now_iso(),
            "camera_id": camera_id,
            "object": classification["object"],
            "obj_conf": classification["confidence"],
            "direction": direction["direction"],
            "dir_conf": direction["confidence"],
            "image_path": relative_path,
        }

        # Add metadata if provided
        if metadata:
            index_entry["metadata"] = metadata

        # Append to index
        self.append_index(index_entry)

        # Emit event to Congress
        self._emit_intruder_event(
            camera_id,
            classification["object"],
            classification["confidence"],
            image_path,
        )

        # Build result
        result = {
            "ok": True,
            "object": classification["object"],
            "confidence": classification["confidence"],
            "direction": direction["direction"],
            "dir_confidence": direction["confidence"],
        }

        return result, image_path

    def append_index(self, entry: Dict[str, Any]) -> None:
        """
        Append an entry to the camera index.

        Args:
            entry: The index entry to append
        """
        ensure_folder(self.index_path.parent)
        append_jsonl(self.index_path, entry)
        logger.info(f"Updated camera index: {self.index_path}")

    def _emit_intruder_event(
        self,
        camera_id: str,
        object_type: str,
        confidence: float,
        image_path: Path,
    ) -> None:
        """
        Emit an intruder detection event to Congress.

        Args:
            camera_id: The camera identifier
            object_type: Detected object type
            confidence: Detection confidence
            image_path: Path to the saved image
        """
        ensure_folder(CONGRESS_EVENTS_LOG.parent)

        timestamp = now_iso()
        event_line = (
            f"{timestamp} hobbs.intruder_detected "
            f"camera={camera_id} object={object_type} "
            f"confidence={confidence:.2f} image={image_path}\n"
        )

        with open(CONGRESS_EVENTS_LOG, "a") as f:
            f.write(event_line)

        logger.info("Emitted intruder event to Congress: hobbs.intruder_detected")

    def get_camera_events_today_count(self) -> int:
        """
        Get the count of camera events for today across all cameras.

        Returns:
            Total number of camera image files created today
        """
        today = today_str()
        total = 0

        # Count files in each camera's today folder
        if self.cameras_dir.exists():
            for camera_folder in self.cameras_dir.iterdir():
                if camera_folder.is_dir():
                    # Check for files that match today's timestamp pattern
                    # Files are named like: 20250121_153045.png
                    today_pattern = today.replace("-", "")
                    for file in camera_folder.glob(f"{today_pattern}_*.png"):
                        total += 1

        return total

    def get_index_size(self) -> int:
        """
        Get the number of entries in the camera index.

        Returns:
            Number of entries in camera_index.jsonl
        """
        return count_jsonl_entries(self.index_path)


# Singleton instance
camera_manager = CameraManager()
