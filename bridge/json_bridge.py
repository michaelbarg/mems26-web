#!/usr/bin/env python3
"""MEMS26 V9 JSON Bridge — reads DLL exports, pushes to Redis + FastAPI."""

import logging
import signal
import sys
import time
import threading

from v9_streams import ALL_STREAMS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("v9_bridge")


def main():
    history_only = "--history-only" in sys.argv

    if history_only:
        logger.info("MEMS26 V9 Bridge — history-only mode (backfill then exit)")
    else:
        logger.info("MEMS26 V9 Bridge starting — %d streams", len(ALL_STREAMS))

    instances = [StreamClass() for StreamClass in ALL_STREAMS]

    if history_only:
        for stream in instances:
            try:
                loaded = stream.historical_load()
                status = "OK" if loaded else "skipped"
            except Exception as e:
                status = f"FAILED: {e}"
            logger.info("  %s: %s", stream.name, status)
        logger.info("History backfill complete. Exiting.")
        return

    threads = []

    for stream in instances:
        t = threading.Thread(target=stream.start, name=stream.name, daemon=True)
        threads.append(t)
        t.start()
        logger.info("Started thread: %s", stream.name)

    # Heartbeat thread — logs alive status every 60s
    stop_event = threading.Event()

    def heartbeat_loop():
        while not stop_event.is_set():
            stop_event.wait(60)
            if stop_event.is_set():
                break
            now = time.time()
            active = sum(1 for s in instances if s.last_update_ts > 0)
            newest = max((s.last_update_ts for s in instances), default=0)
            age = int(now - newest) if newest > 0 else -1
            total_pushes = sum(s.push_count for s in instances)
            total_errors = sum(s.error_count for s in instances)
            if age < 0:
                logger.info("[heartbeat] alive — no data received yet, streams=%d/%d "
                            "total_pushes=%d total_errors=%d",
                            active, len(instances), total_pushes, total_errors)
            elif age > 300:
                logger.info("[heartbeat] alive — market likely closed (data %ds old), "
                            "streams=%d/%d total_pushes=%d total_errors=%d",
                            age, active, len(instances), total_pushes, total_errors)
            else:
                logger.info("[heartbeat] alive — newest_data_age=%ds streams=%d/%d "
                            "total_pushes=%d total_errors=%d",
                            age, active, len(instances), total_pushes, total_errors)

    hb_thread = threading.Thread(target=heartbeat_loop, name="heartbeat", daemon=True)
    hb_thread.start()

    def shutdown(sig, frame):
        logger.info("Shutdown signal received, stopping all streams...")
        stop_event.set()
        for stream in instances:
            stream.stop()
        for t in threads:
            t.join(timeout=5)
        logger.info("All streams stopped. Exiting.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Keep main thread alive — monitor ALL threads uniformly
    while any(t.is_alive() for t in threads):
        time.sleep(1)


if __name__ == "__main__":
    main()
