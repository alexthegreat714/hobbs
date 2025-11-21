#!/usr/bin/env python3
"""
Hobbs Agent Runner - Daemon-like operation with heartbeat.

This script provides:
- Optional FastAPI server startup
- Periodic heartbeat to Congress
- Metrics publishing to Argus
- Periodic learning cycles
- Graceful shutdown handling

Usage:
    python run_hobbs.py                    # Run heartbeat loop only (server started separately)
    python run_hobbs.py --with-server      # Start server and heartbeat loop
    python run_hobbs.py --single-tick      # Run one heartbeat cycle and exit (for testing)
"""

import argparse
import signal
import sys
import time
import threading
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings, logger


# Global flag for graceful shutdown
_shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global _shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    _shutdown_requested = True


def run_server(host: str = "0.0.0.0", port: int = 5055):
    """
    Start the FastAPI server in a separate thread.

    Args:
        host: Host to bind to
        port: Port to listen on
    """
    import uvicorn
    from app import app

    logger.info(f"Starting Hobbs server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


def run_heartbeat_loop(
    heartbeat_interval: int = 60,
    metrics_interval: int = 300,
    learning_interval: int = 1800,
    single_tick: bool = False
):
    """
    Run the main heartbeat loop.

    Args:
        heartbeat_interval: Seconds between heartbeats (default: 60)
        metrics_interval: Seconds between metrics publish (default: 300)
        learning_interval: Seconds between learning cycles (default: 1800)
        single_tick: If True, run one iteration and exit
    """
    global _shutdown_requested

    from server.integration.congress_client import congress_client
    from server.integration.argus_client import argus_client
    from server.learning.learning_engine import learning_engine
    from server.memory.memory_manager import memory_manager

    logger.info("Starting Hobbs heartbeat loop")

    # Load and apply policies on startup
    policies = congress_client.load_policies()
    congress_client.apply_policies(policies)
    logger.info("Policies loaded and applied")

    # Track intervals
    last_heartbeat = 0
    last_metrics = 0
    last_learning = 0
    tick_count = 0

    while not _shutdown_requested:
        tick_count += 1
        current_time = time.time()

        try:
            # Heartbeat (every heartbeat_interval seconds)
            if current_time - last_heartbeat >= heartbeat_interval:
                congress_client.send_heartbeat()
                last_heartbeat = current_time
                logger.debug("Heartbeat sent")

            # Metrics (every metrics_interval seconds)
            if current_time - last_metrics >= metrics_interval:
                metrics = argus_client.collect_metrics()
                argus_client.publish_metrics(metrics)
                last_metrics = current_time
                logger.info(f"Metrics published: health={metrics.get('health_status')}")

            # Learning cycle (every learning_interval seconds)
            if current_time - last_learning >= learning_interval:
                # Check if learning is enabled by policy
                if congress_client.check_permission("learning_cycle"):
                    result = learning_engine.run_full_learning_cycle()
                    logger.info(f"Learning cycle complete: {result.get('events_analyzed', 0)} events analyzed")
                last_learning = current_time

            # Single tick mode
            if single_tick:
                logger.info("Single tick complete, exiting")
                break

            # Sleep until next check (minimum of remaining intervals)
            next_heartbeat = heartbeat_interval - (current_time - last_heartbeat)
            next_metrics = metrics_interval - (current_time - last_metrics)
            next_learning = learning_interval - (current_time - last_learning)

            sleep_time = max(1, min(next_heartbeat, next_metrics, next_learning, 10))
            time.sleep(sleep_time)

        except Exception as e:
            logger.error(f"Error in heartbeat loop: {e}")
            time.sleep(5)  # Brief pause before retry

    logger.info("Heartbeat loop terminated")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Hobbs Agent Runner - Daemon-like operation with heartbeat"
    )
    parser.add_argument(
        "--with-server",
        action="store_true",
        help="Start FastAPI server alongside heartbeat loop"
    )
    parser.add_argument(
        "--single-tick",
        action="store_true",
        help="Run one heartbeat cycle and exit (for testing)"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Server host (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5055,
        help="Server port (default: 5055)"
    )
    parser.add_argument(
        "--heartbeat-interval",
        type=int,
        default=60,
        help="Heartbeat interval in seconds (default: 60)"
    )
    parser.add_argument(
        "--metrics-interval",
        type=int,
        default=300,
        help="Metrics publish interval in seconds (default: 300)"
    )
    parser.add_argument(
        "--learning-interval",
        type=int,
        default=1800,
        help="Learning cycle interval in seconds (default: 1800)"
    )

    args = parser.parse_args()

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info(f"Hobbs Agent v{settings.VERSION} starting...")
    logger.info(f"Heartbeat interval: {args.heartbeat_interval}s")
    logger.info(f"Metrics interval: {args.metrics_interval}s")
    logger.info(f"Learning interval: {args.learning_interval}s")

    # Start server in background thread if requested
    server_thread = None
    if args.with_server:
        server_thread = threading.Thread(
            target=run_server,
            args=(args.host, args.port),
            daemon=True
        )
        server_thread.start()
        logger.info("Server started in background")
        time.sleep(2)  # Give server time to start

    # Run heartbeat loop
    run_heartbeat_loop(
        heartbeat_interval=args.heartbeat_interval,
        metrics_interval=args.metrics_interval,
        learning_interval=args.learning_interval,
        single_tick=args.single_tick
    )

    logger.info("Hobbs Agent shutdown complete")


if __name__ == "__main__":
    main()
