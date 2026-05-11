"""Audit Consumer runner — entry point for background process.

Usage: python3 -m backend.v9.audit.runner
"""

import logging
import signal
import sys
import time

from backend.v9.audit.consumer import AuditConsumer, POLL_MS
from backend.v9.db.session import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("mems26.audit")

# Global instance for status endpoint access
_consumer: AuditConsumer = None


def get_consumer() -> AuditConsumer:
    return _consumer


def main():
    global _consumer

    logger.info("[Audit] Starting AuditConsumer...")
    init_db()

    consumer = AuditConsumer()
    _consumer = consumer
    consumer._init_offsets()
    consumer._running = True
    consumer._start_ts = time.time()

    stop = False

    def shutdown(sig, frame):
        nonlocal stop
        logger.info("[Audit] Shutdown signal received")
        stop = True

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    poll_sec = POLL_MS / 1000.0
    heartbeat_interval = 30
    last_heartbeat = 0

    logger.info("[Audit] Consumer running (poll=%dms, batch=%d)", POLL_MS, consumer.events_written)

    while not stop:
        try:
            count = consumer.poll_once()
            now = time.time()

            # Heartbeat log
            if now - last_heartbeat >= heartbeat_interval:
                last_heartbeat = now
                epm = consumer.events_per_minute
                logger.info(
                    "[Audit] heartbeat — written=%d skipped=%d errors=%d epm=%.1f",
                    consumer.events_written, consumer.events_skipped,
                    consumer.errors, epm,
                )

            if count == 0:
                time.sleep(poll_sec)
        except Exception:
            logger.exception("[Audit] poll loop error")
            time.sleep(1)

    consumer._running = False
    logger.info(
        "[Audit] Stopped. Total written=%d skipped=%d errors=%d",
        consumer.events_written, consumer.events_skipped, consumer.errors,
    )


if __name__ == "__main__":
    main()
