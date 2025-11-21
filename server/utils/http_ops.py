"""
HTTP operations utility for the Hobbs Agent.

Provides functions for making HTTP requests with error handling.
"""

import urllib.request
import urllib.error
import json
from typing import Any, Dict, Optional

from config.settings import logger


def get_json(url: str, timeout: int = 5) -> Optional[Dict[str, Any]]:
    """
    Make a GET request and return JSON response.

    Handles:
    - Timeouts
    - Connection errors
    - Invalid JSON responses

    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds (default: 5)

    Returns:
        Parsed JSON as dict, or None if request failed
    """
    try:
        logger.info(f"HTTP GET: {url}")

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "HobbsAgent/0.3.0",
                "Accept": "application/json",
            }
        )

        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                logger.warning(f"HTTP GET failed with status {response.status}: {url}")
                return None

            data = response.read().decode("utf-8")
            result = json.loads(data)
            logger.info(f"HTTP GET success: {url}")
            return result

    except urllib.error.URLError as e:
        logger.warning(f"HTTP connection error for {url}: {e}")
        return None

    except urllib.error.HTTPError as e:
        logger.warning(f"HTTP error {e.code} for {url}: {e.reason}")
        return None

    except TimeoutError:
        logger.warning(f"HTTP timeout for {url}")
        return None

    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON response from {url}: {e}")
        return None

    except Exception as e:
        logger.warning(f"Unexpected error fetching {url}: {e}")
        return None
