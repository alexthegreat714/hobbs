"""
Image operations utility for the Hobbs Agent.

Provides functions for image handling including base64 decoding,
downloading from URLs, and file management.
"""

import base64
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

from config.settings import logger


# Base cameras directory
DATA_DIR = Path.home() / "Desktop" / "Engineering" / "Hobbs" / "data"
CAMERAS_DIR = DATA_DIR / "cameras"


def ensure_camera_folder(camera_id: str) -> Path:
    """
    Ensure a camera folder exists, creating it if necessary.

    Args:
        camera_id: The camera identifier

    Returns:
        Path to the camera folder
    """
    # Sanitize camera_id to prevent directory traversal
    safe_camera_id = "".join(c if c.isalnum() or c in "_-" else "_" for c in camera_id)
    camera_folder = CAMERAS_DIR / safe_camera_id
    camera_folder.mkdir(parents=True, exist_ok=True)
    return camera_folder


def ensure_png_extension(path: Path) -> Path:
    """
    Ensure the file path has a .png extension.

    Args:
        path: The file path

    Returns:
        Path with .png extension
    """
    if path.suffix.lower() != ".png":
        return path.with_suffix(".png")
    return path


def decode_base64_to_file(b64_data: str, filepath: Path) -> Path:
    """
    Decode a base64 string and save it to a file.

    Args:
        b64_data: Base64 encoded image data
        filepath: Destination file path

    Returns:
        Path to the saved file

    Raises:
        ValueError: If base64 decoding fails
    """
    try:
        # Handle data URI prefix if present
        if "," in b64_data:
            # Format: data:image/png;base64,<data>
            b64_data = b64_data.split(",", 1)[1]

        # Decode base64
        image_bytes = base64.b64decode(b64_data)

        # Ensure parent directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Ensure .png extension
        filepath = ensure_png_extension(filepath)

        # Write to file
        with open(filepath, "wb") as f:
            f.write(image_bytes)

        logger.info(f"Decoded base64 image to: {filepath}")
        return filepath

    except Exception as e:
        logger.error(f"Failed to decode base64 image: {e}")
        raise ValueError(f"Failed to decode base64 image: {e}")


def download_image(url: str, filepath: Path, timeout: int = 10) -> Optional[Path]:
    """
    Download an image from a URL and save it to a file.

    Args:
        url: The URL to download from
        filepath: Destination file path
        timeout: Request timeout in seconds

    Returns:
        Path to the saved file, or None if download failed
    """
    try:
        logger.info(f"Downloading image from: {url}")

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "HobbsAgent/0.4.0",
            }
        )

        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                logger.warning(f"Image download failed with status {response.status}")
                return None

            image_bytes = response.read()

            # Ensure parent directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)

            # Ensure .png extension
            filepath = ensure_png_extension(filepath)

            # Write to file
            with open(filepath, "wb") as f:
                f.write(image_bytes)

            logger.info(f"Downloaded image to: {filepath}")
            return filepath

    except urllib.error.URLError as e:
        logger.warning(f"Failed to download image from {url}: {e}")
        return None

    except Exception as e:
        logger.warning(f"Unexpected error downloading image: {e}")
        return None


def get_cameras_dir() -> Path:
    """
    Get the cameras data directory path.

    Returns:
        Path to ~/Desktop/Engineering/Hobbs/data/cameras/
    """
    return CAMERAS_DIR


def get_camera_index_path() -> Path:
    """
    Get the camera index file path.

    Returns:
        Path to ~/Desktop/Engineering/Hobbs/data/index/camera_index.jsonl
    """
    return DATA_DIR / "index" / "camera_index.jsonl"
