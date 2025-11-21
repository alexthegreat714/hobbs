"""
Weather Manager for the Hobbs Agent.

Coordinates:
- Remote weather forecast fetching
- Local caching of forecasts
- Offline fallback prediction
- Weather index management
- Event emission to Congress
"""

import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from server.utils.file_ops import (
    ensure_folder,
    write_json,
    append_jsonl,
    safe_filename,
    count_files_in_folder,
    count_jsonl_entries,
)
from server.utils.time_ops import now_iso, today_str, timestamp_str
from server.utils.http_ops import get_json
from config.settings import logger


# Default location (Huntsville, AL - placeholder)
DEFAULT_LOCATION = {"lat": 34.73, "lon": -86.58}

# Data directories
DATA_DIR = Path.home() / "Desktop" / "Engineering" / "Hobbs" / "data"
WEATHER_DIR = DATA_DIR / "weather"
INDEX_DIR = DATA_DIR / "index"
WEATHER_INDEX_PATH = INDEX_DIR / "weather_index.jsonl"

# Congress event log
CONGRESS_EVENTS_LOG = Path.home() / "Desktop" / "Engineering" / "Congress" / "memory" / "hobbs_events.log"

# Open-Meteo API base URL
OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"


class WeatherManager:
    """
    Manages weather forecast retrieval, caching, and indexing.
    """

    def __init__(self):
        """Initialize the weather manager."""
        self.weather_dir = WEATHER_DIR
        self.index_path = WEATHER_INDEX_PATH
        self._last_temperature = 20.0  # Default starting temperature (Celsius)

    def fetch_remote_forecast(
        self, lat: float, lon: float
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch weather forecast from Open-Meteo API.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Forecast dict or None if fetch failed
        """
        url = (
            f"{OPEN_METEO_BASE}"
            f"?latitude={lat}"
            f"&longitude={lon}"
            f"&hourly=temperature_2m,precipitation_probability,wind_speed_10m"
            f"&forecast_days=3"
            f"&timezone=auto"
        )

        logger.info(f"Fetching remote weather forecast for ({lat}, {lon})")
        response = get_json(url, timeout=10)

        if response and "hourly" in response:
            logger.info("Remote forecast fetch successful")
            return response

        logger.warning("Remote forecast fetch failed")
        return None

    def offline_estimate(self) -> Dict[str, Any]:
        """
        Generate an offline heuristic weather estimate.

        Simple model:
        - Temperature: previous_average +/- small delta
        - Precipitation chance: ~15%
        - Wind speed: 3-8 mph

        Returns:
            Dict with forecast data and confidence=0.4
        """
        logger.info("Generating offline weather estimate")

        # Apply small random delta to last known temperature
        delta = random.uniform(-3.0, 3.0)
        temperature = self._last_temperature + delta
        self._last_temperature = temperature

        # Generate 24 hours of hourly estimates
        hours = 24
        temperatures = []
        precipitation_probs = []
        wind_speeds = []

        for hour in range(hours):
            # Temperature varies by time of day (simple sine wave)
            hour_offset = (hour - 14) / 24.0 * 6.28  # Peak at 2 PM
            temp_variation = 5.0 * (0.5 + 0.5 * (1 + random.uniform(-0.2, 0.2)))
            hourly_temp = temperature + temp_variation * (0.5 - abs(hour_offset) / 3.14)
            temperatures.append(round(hourly_temp, 1))

            # Precipitation chance around 15%
            precip = random.uniform(0.05, 0.25) * 100
            precipitation_probs.append(round(precip, 0))

            # Wind speed 3-8 mph (convert to km/h for consistency)
            wind_mph = random.uniform(3.0, 8.0)
            wind_kmh = wind_mph * 1.60934
            wind_speeds.append(round(wind_kmh, 1))

        # Generate time strings for the next 24 hours
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        times = [
            (now + timedelta(hours=h)).strftime("%Y-%m-%dT%H:00")
            for h in range(hours)
        ]

        estimate = {
            "source": "offline",
            "generated_at": now_iso(),
            "location": DEFAULT_LOCATION,
            "hourly": {
                "time": times,
                "temperature_2m": temperatures,
                "precipitation_probability": precipitation_probs,
                "wind_speed_10m": wind_speeds,
            },
            "hourly_units": {
                "temperature_2m": "°C",
                "precipitation_probability": "%",
                "wind_speed_10m": "km/h",
            },
        }

        return estimate

    def get_forecast(
        self, location: Optional[Dict[str, float]] = None
    ) -> Tuple[Dict[str, Any], float, str]:
        """
        Get weather forecast, trying remote first then falling back to offline.

        Args:
            location: Dict with 'lat' and 'lon' keys (optional)

        Returns:
            Tuple of (forecast_data, confidence, source)
            - confidence: 0.0-1.0 (higher = more reliable)
            - source: "remote" or "offline"
        """
        loc = location or DEFAULT_LOCATION
        lat = loc.get("lat", DEFAULT_LOCATION["lat"])
        lon = loc.get("lon", DEFAULT_LOCATION["lon"])

        # Try remote fetch first
        remote_data = self.fetch_remote_forecast(lat, lon)

        if remote_data:
            forecast = {
                "source": "remote",
                "fetched_at": now_iso(),
                "location": {"lat": lat, "lon": lon},
                "hourly": remote_data.get("hourly", {}),
                "hourly_units": remote_data.get("hourly_units", {}),
            }
            confidence = 0.85
            source = "remote"
        else:
            # Fall back to offline estimate
            forecast = self.offline_estimate()
            forecast["location"] = {"lat": lat, "lon": lon}
            confidence = 0.4
            source = "offline"

        # Save forecast to file
        filepath = self._save_forecast(forecast)

        # Update index
        self._update_index(source, filepath, confidence)

        # Emit event to Congress
        self._emit_weather_event(filepath)

        return forecast, confidence, source

    def _save_forecast(self, forecast: Dict[str, Any]) -> Path:
        """
        Save forecast data to a JSON file.

        Args:
            forecast: The forecast data to save

        Returns:
            Path to the saved file
        """
        today = today_str()
        ts = timestamp_str()

        # Ensure today's weather folder exists
        today_folder = self.weather_dir / today
        ensure_folder(today_folder)

        # Generate filename
        filename = f"weather_{ts}.json"
        filepath = today_folder / filename

        # Write forecast file
        write_json(filepath, forecast)
        logger.info(f"Saved weather forecast: {filepath}")

        return filepath

    def _update_index(self, source: str, filepath: Path, confidence: float) -> None:
        """
        Append entry to weather index.

        Args:
            source: "remote" or "offline"
            filepath: Path to saved forecast file
            confidence: Confidence score (0.0-1.0)
        """
        # Calculate relative path
        relative_path = str(filepath.relative_to(DATA_DIR))

        index_entry = {
            "timestamp": now_iso(),
            "source": source,
            "forecast_path": relative_path,
            "confidence": confidence,
        }

        ensure_folder(self.index_path.parent)
        append_jsonl(self.index_path, index_entry)
        logger.info(f"Updated weather index: {self.index_path}")

    def _emit_weather_event(self, filepath: Path) -> None:
        """
        Emit weather update event to Congress.

        Args:
            filepath: Path to the saved forecast file
        """
        ensure_folder(CONGRESS_EVENTS_LOG.parent)

        timestamp = now_iso()
        event_line = f"{timestamp} hobbs.weather.update FORECAST_SAVED:{filepath}\n"

        with open(CONGRESS_EVENTS_LOG, "a") as f:
            f.write(event_line)

        logger.info("Emitted weather event to Congress: hobbs.weather.update")

    def get_forecasts_today_count(self) -> int:
        """
        Get the count of weather forecast files for today.

        Returns:
            Number of forecast JSON files in today's folder
        """
        today_folder = self.weather_dir / today_str()
        return count_files_in_folder(today_folder, "*.json")

    def get_index_size(self) -> int:
        """
        Get the number of entries in the weather index.

        Returns:
            Number of entries in weather_index.jsonl
        """
        return count_jsonl_entries(self.index_path)


# Singleton instance
weather_manager = WeatherManager()
