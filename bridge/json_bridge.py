#!/usr/bin/env python3
"""MEMS26 V9 JSON Bridge — reads DLL exports, pushes to Redis + FastAPI."""

import logging
import signal
import sys
import threading

from v9_streams import ALL_STREAMS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("v9_bridge")


def main():
    logger.info("MEMS26 V9 Bridge starting — %d streams", len(ALL_STREAMS))

    instances = [StreamClass() for StreamClass in ALL_STREAMS]
    threads = []

    for stream in instances:
        t = threading.Thread(target=stream.start, name=stream.name, daemon=True)
        threads.append(t)
        t.start()
        logger.info("Started thread: %s", stream.name)

    def shutdown(sig, frame):
        logger.info("Shutdown signal received, stopping all streams...")
        for stream in instances:
            stream.stop()
        for t in threads:
            t.join(timeout=5)
        logger.info("All streams stopped. Exiting.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Keep main thread alive
    for t in threads:
        while t.is_alive():
            t.join(timeout=1)


if __name__ == "__main__":
    main()
