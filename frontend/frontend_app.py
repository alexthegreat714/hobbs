"""
Hobbs Frontend - Flask Application

Provides web UI with:
- Chat interface with Gemma 3 + DeepCoder reasoning
- Camera grid with RTSP streams
- Farm data dashboard
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
import httpx
import json
from datetime import datetime

from frontend.llm.reasoning_orchestrator import reasoning_orchestrator
from frontend.llm.ollama_client import ollama_client
from config.settings import logger

app = Flask(__name__)
CORS(app)

# Hobbs API base URL
HOBBS_API = "http://localhost:5055"


# =============================================================================
# Page Routes
# =============================================================================

@app.route("/")
def index():
    """Main dashboard page."""
    return render_template("index.html")


# =============================================================================
# Chat API
# =============================================================================

@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Process a chat message through the reasoning orchestrator.

    Gemma decides if DeepCoder reasoning is needed.
    """
    data = request.json
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "No message provided"}), 400

    try:
        result = reasoning_orchestrator.process_message(message)

        return jsonify({
            "ok": True,
            "response": result.user_response,
            "reasoning_used": result.reasoning_used,
            "reasoning_trace": result.reasoning_trace,
            "reasoning_summary": result.reasoning_summary,
            "model_used": result.model_used,
            "reasoning_model": result.reasoning_model if result.reasoning_used else None,
            "timestamp": result.timestamp
        })

    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat/clear", methods=["POST"])
def clear_chat():
    """Clear conversation history."""
    reasoning_orchestrator.clear_history()
    return jsonify({"ok": True, "message": "History cleared"})


@app.route("/api/models/status", methods=["GET"])
def model_status():
    """Get LLM model status."""
    status = reasoning_orchestrator.get_model_status()
    return jsonify(status)


# =============================================================================
# Hobbs API Proxy
# =============================================================================

@app.route("/api/hobbs/status", methods=["GET"])
def hobbs_status():
    """Proxy to Hobbs /status endpoint."""
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{HOBBS_API}/status")
            return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/hobbs/learning", methods=["GET"])
def hobbs_learning():
    """Proxy to Hobbs /learning_report endpoint."""
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{HOBBS_API}/learning_report")
            return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/hobbs/memory", methods=["POST"])
def hobbs_memory():
    """Proxy to Hobbs /memory_query endpoint."""
    try:
        data = request.json or {}
        payload = {
            "task_id": f"frontend-{datetime.utcnow().timestamp()}",
            "source": "frontend",
            "target": "hobbs",
            "type": "memory_query",
            "payload": data,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        with httpx.Client(timeout=10.0) as client:
            response = client.post(f"{HOBBS_API}/memory_query", json=payload)
            return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =============================================================================
# Camera API
# =============================================================================

@app.route("/api/cameras", methods=["GET"])
def list_cameras():
    """List configured cameras."""
    # This would come from config - hardcoded for now
    cameras = [
        {"id": "cam_woods", "name": "Woods Camera", "rtsp_url": "", "enabled": True},
        {"id": "cam_driveway", "name": "Driveway Camera", "rtsp_url": "", "enabled": True},
        {"id": "cam_barn", "name": "Barn Camera", "rtsp_url": "", "enabled": True},
        {"id": "cam_field", "name": "Field Camera", "rtsp_url": "", "enabled": False},
    ]
    return jsonify({"cameras": cameras})


@app.route("/api/cameras/<camera_id>/snapshot", methods=["GET"])
def camera_snapshot(camera_id):
    """
    Get latest snapshot from a camera.

    For RTSP cameras, this would capture a frame.
    Returns placeholder for now.
    """
    # In production: capture frame from RTSP stream using ffmpeg/opencv
    # For now, return info about the camera
    return jsonify({
        "camera_id": camera_id,
        "snapshot_url": f"/static/placeholder_cam.jpg",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "placeholder"
    })


@app.route("/api/cameras/<camera_id>/stream")
def camera_stream(camera_id):
    """
    Stream camera feed.

    For RTSP: would transcode to MJPEG or HLS.
    Returns placeholder response for now.
    """
    # In production: use ffmpeg to transcode RTSP to MJPEG
    # Example: ffmpeg -i rtsp://... -f mjpeg -
    return jsonify({
        "camera_id": camera_id,
        "stream_type": "not_implemented",
        "message": "Configure RTSP URL in camera settings"
    })


# =============================================================================
# Farm Data API
# =============================================================================

@app.route("/api/farm/zones", methods=["GET"])
def farm_zones():
    """Get farm zone data."""
    # This would aggregate from Hobbs sensors
    # Placeholder data structure
    zones = [
        {
            "id": "zone_1",
            "name": "North Field",
            "sensors": {
                "moisture": 0.35,
                "temperature": 72.5,
                "ph": 6.8
            },
            "valve_status": "closed",
            "last_update": datetime.utcnow().isoformat() + "Z"
        },
        {
            "id": "zone_2",
            "name": "South Field",
            "sensors": {
                "moisture": 0.18,
                "temperature": 74.2,
                "ph": 6.5
            },
            "valve_status": "open",
            "last_update": datetime.utcnow().isoformat() + "Z"
        },
        {
            "id": "zone_3",
            "name": "Greenhouse",
            "sensors": {
                "moisture": 0.55,
                "temperature": 78.0,
                "ph": 7.0
            },
            "valve_status": "closed",
            "last_update": datetime.utcnow().isoformat() + "Z"
        },
        {
            "id": "zone_4",
            "name": "Orchard",
            "sensors": {
                "moisture": 0.42,
                "temperature": 71.0,
                "ph": 6.2
            },
            "valve_status": "closed",
            "last_update": datetime.utcnow().isoformat() + "Z"
        }
    ]
    return jsonify({"zones": zones})


@app.route("/api/farm/weather", methods=["GET"])
def farm_weather():
    """Get weather data from Hobbs."""
    try:
        # Try to get from Hobbs
        with httpx.Client(timeout=10.0) as client:
            payload = {
                "task_id": f"frontend-weather-{datetime.utcnow().timestamp()}",
                "source": "frontend",
                "target": "hobbs",
                "type": "weather",
                "payload": {"location": "farm"},
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            response = client.post(f"{HOBBS_API}/predict_weather", json=payload)
            if response.status_code == 200:
                return jsonify(response.json())
    except Exception as e:
        logger.warning(f"Weather fetch failed: {e}")

    # Fallback placeholder
    return jsonify({
        "ok": True,
        "current": {
            "temperature": 72,
            "humidity": 45,
            "condition": "Partly Cloudy"
        },
        "forecast": "No data available"
    })


@app.route("/api/farm/alerts", methods=["GET"])
def farm_alerts():
    """Get recent alerts."""
    # Would come from Hobbs memory/events
    alerts = [
        {
            "id": "alert_1",
            "type": "moisture_low",
            "zone": "South Field",
            "message": "Moisture below threshold (0.18)",
            "severity": "warning",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    ]
    return jsonify({"alerts": alerts})


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("Starting Hobbs Frontend...")
    print("Make sure Ollama is running with gemma3 and deepseek-coder models")
    print("Make sure Hobbs API is running on localhost:5055")
    app.run(host="0.0.0.0", port=5050, debug=True)
