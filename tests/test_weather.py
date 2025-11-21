"""
Tests for Hobbs Agent weather prediction functionality.

Tests verify:
- Weather forecast retrieval (remote and offline)
- Forecast storage to file system
- Index entry appending
- Endpoint returns forecast with confidence
"""

import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from app import app
from server.weather.weather_manager import WeatherManager, WEATHER_DIR, WEATHER_INDEX_PATH
from server.utils.time_ops import today_str


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def valid_weather_envelope():
    """Create a valid TaskEnvelope for weather prediction."""
    return {
        "task_id": "test-weather-001",
        "source": "test-source",
        "target": "hobbs",
        "type": "weather",
        "payload": {
            "location": {"lat": 34.73, "lon": -86.58}
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@pytest.fixture
def weather_envelope_no_location():
    """Create a TaskEnvelope without location (uses default)."""
    return {
        "task_id": "test-weather-002",
        "source": "test-source",
        "target": "hobbs",
        "type": "weather",
        "payload": {},
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@pytest.fixture
def mock_remote_forecast():
    """Mock remote forecast response."""
    return {
        "hourly": {
            "time": [f"2025-01-21T{h:02d}:00" for h in range(24)],
            "temperature_2m": [20.0 + h * 0.5 for h in range(24)],
            "precipitation_probability": [10] * 24,
            "wind_speed_10m": [5.0] * 24,
        },
        "hourly_units": {
            "temperature_2m": "°C",
            "precipitation_probability": "%",
            "wind_speed_10m": "km/h",
        }
    }


@pytest.fixture
def cleanup_weather_data():
    """Fixture to clean up test weather data after tests."""
    yield
    # Cleanup: Remove today's weather folder if it exists
    today_folder = WEATHER_DIR / today_str()
    if today_folder.exists():
        shutil.rmtree(today_folder)

    # Clear the weather index file
    if WEATHER_INDEX_PATH.exists():
        WEATHER_INDEX_PATH.write_text("")


class TestWeatherManager:
    """Tests for the WeatherManager class."""

    def test_offline_estimate_returns_forecast(self):
        """Test that offline estimate returns valid forecast data."""
        manager = WeatherManager()
        estimate = manager.offline_estimate()

        assert "source" in estimate
        assert estimate["source"] == "offline"
        assert "hourly" in estimate
        assert "time" in estimate["hourly"]
        assert "temperature_2m" in estimate["hourly"]
        assert "precipitation_probability" in estimate["hourly"]
        assert "wind_speed_10m" in estimate["hourly"]

    def test_offline_estimate_has_24_hours(self):
        """Test that offline estimate provides 24 hours of data."""
        manager = WeatherManager()
        estimate = manager.offline_estimate()

        assert len(estimate["hourly"]["time"]) == 24
        assert len(estimate["hourly"]["temperature_2m"]) == 24

    @patch("server.weather.weather_manager.get_json")
    def test_fetch_remote_forecast_success(self, mock_get_json, mock_remote_forecast):
        """Test successful remote forecast fetch."""
        mock_get_json.return_value = mock_remote_forecast

        manager = WeatherManager()
        result = manager.fetch_remote_forecast(34.73, -86.58)

        assert result is not None
        assert "hourly" in result

    @patch("server.weather.weather_manager.get_json")
    def test_fetch_remote_forecast_failure(self, mock_get_json):
        """Test remote forecast fetch failure."""
        mock_get_json.return_value = None

        manager = WeatherManager()
        result = manager.fetch_remote_forecast(34.73, -86.58)

        assert result is None

    @patch("server.weather.weather_manager.get_json")
    def test_get_forecast_uses_remote_when_available(
        self, mock_get_json, mock_remote_forecast, cleanup_weather_data
    ):
        """Test that get_forecast uses remote data when available."""
        mock_get_json.return_value = mock_remote_forecast

        manager = WeatherManager()
        forecast, confidence, source = manager.get_forecast({"lat": 34.73, "lon": -86.58})

        assert source == "remote"
        assert confidence == 0.85

    @patch("server.weather.weather_manager.get_json")
    def test_get_forecast_falls_back_to_offline(self, mock_get_json, cleanup_weather_data):
        """Test that get_forecast falls back to offline when remote fails."""
        mock_get_json.return_value = None

        manager = WeatherManager()
        forecast, confidence, source = manager.get_forecast({"lat": 34.73, "lon": -86.58})

        assert source == "offline"
        assert confidence == 0.4

    @patch("server.weather.weather_manager.get_json")
    def test_get_forecast_saves_file(self, mock_get_json, cleanup_weather_data):
        """Test that get_forecast saves forecast to file."""
        mock_get_json.return_value = None  # Force offline

        manager = WeatherManager()
        manager.get_forecast({"lat": 34.73, "lon": -86.58})

        today_folder = WEATHER_DIR / today_str()
        assert today_folder.exists()

        json_files = list(today_folder.glob("weather_*.json"))
        assert len(json_files) >= 1

    @patch("server.weather.weather_manager.get_json")
    def test_get_forecast_updates_index(self, mock_get_json, cleanup_weather_data):
        """Test that get_forecast updates the weather index."""
        mock_get_json.return_value = None  # Force offline

        # Clear index first
        WEATHER_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        WEATHER_INDEX_PATH.write_text("")

        manager = WeatherManager()
        manager.get_forecast({"lat": 34.73, "lon": -86.58})

        with open(WEATHER_INDEX_PATH, "r") as f:
            lines = [line.strip() for line in f if line.strip()]

        assert len(lines) >= 1

        entry = json.loads(lines[-1])
        assert "timestamp" in entry
        assert "source" in entry
        assert "forecast_path" in entry
        assert "confidence" in entry


class TestPredictWeatherEndpoint:
    """Tests for the /predict_weather endpoint."""

    @patch("server.weather.weather_manager.get_json")
    def test_predict_weather_returns_200(
        self, mock_get_json, client, valid_weather_envelope, cleanup_weather_data
    ):
        """Test that /predict_weather returns 200 OK."""
        mock_get_json.return_value = None  # Force offline for predictable test

        response = client.post("/predict_weather", json=valid_weather_envelope)
        assert response.status_code == 200

    @patch("server.weather.weather_manager.get_json")
    def test_predict_weather_returns_expected_keys(
        self, mock_get_json, client, valid_weather_envelope, cleanup_weather_data
    ):
        """Test that /predict_weather returns expected response keys."""
        mock_get_json.return_value = None

        response = client.post("/predict_weather", json=valid_weather_envelope)
        data = response.json()

        assert "ok" in data
        assert "forecast" in data
        assert "confidence" in data
        assert "source" in data
        assert data["ok"] is True

    @patch("server.weather.weather_manager.get_json")
    def test_predict_weather_returns_forecast_list(
        self, mock_get_json, client, valid_weather_envelope, cleanup_weather_data
    ):
        """Test that /predict_weather returns a list of forecast entries."""
        mock_get_json.return_value = None

        response = client.post("/predict_weather", json=valid_weather_envelope)
        data = response.json()

        assert isinstance(data["forecast"], list)
        assert len(data["forecast"]) > 0

        # Check structure of first forecast entry
        first_entry = data["forecast"][0]
        assert "time" in first_entry
        assert "temperature" in first_entry
        assert "precipitation_probability" in first_entry

    @patch("server.weather.weather_manager.get_json")
    def test_predict_weather_without_location(
        self, mock_get_json, client, weather_envelope_no_location, cleanup_weather_data
    ):
        """Test that /predict_weather works without location (uses default)."""
        mock_get_json.return_value = None

        response = client.post("/predict_weather", json=weather_envelope_no_location)
        assert response.status_code == 200

        data = response.json()
        assert "location" in data
        assert "lat" in data["location"]
        assert "lon" in data["location"]

    @patch("server.weather.weather_manager.get_json")
    def test_predict_weather_offline_confidence(
        self, mock_get_json, client, valid_weather_envelope, cleanup_weather_data
    ):
        """Test that offline forecast has lower confidence."""
        mock_get_json.return_value = None  # Force offline

        response = client.post("/predict_weather", json=valid_weather_envelope)
        data = response.json()

        assert data["source"] == "offline"
        assert data["confidence"] == 0.4

    @patch("server.weather.weather_manager.get_json")
    def test_predict_weather_creates_file(
        self, mock_get_json, client, valid_weather_envelope, cleanup_weather_data
    ):
        """Test that /predict_weather creates a forecast file."""
        mock_get_json.return_value = None

        response = client.post("/predict_weather", json=valid_weather_envelope)
        assert response.status_code == 200

        today_folder = WEATHER_DIR / today_str()
        json_files = list(today_folder.glob("weather_*.json"))
        assert len(json_files) >= 1


class TestStatusWithWeatherStats:
    """Tests for /status endpoint with weather statistics."""

    def test_status_includes_weather_stats(self, client):
        """Test that /status includes weather forecast statistics."""
        response = client.get("/status")
        assert response.status_code == 200

        data = response.json()
        assert "weather_forecasts_today" in data
        assert "weather_index_size" in data
        assert isinstance(data["weather_forecasts_today"], int)
        assert isinstance(data["weather_index_size"], int)
