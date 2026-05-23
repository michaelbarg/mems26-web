#!/usr/bin/env python3
"""MEMS26 V9 JSON Bridge — reads DLL exports, pushes to Redis + FastAPI."""

import logging
import os
import signal
import sys
import time
import threading

try:
    from v9_streams import ALL_STREAMS
except ModuleNotFoundError:
    from .v9_streams import ALL_STREAMS

try:
    from v9_startup import wipe_today_bars_if_requested
except ModuleNotFoundError:
    from .v9_startup import wipe_today_bars_if_requested

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("v9_bridge")


def _requested_stream_names(argv):
    """Return explicit stream names from CLI/env, or None for all streams."""
    if "--bars-5min-only" in argv:
        return {"bars_5min"}

    if "--cockpit-minimal" in argv:
        # P30 chart + Woodies panel: bars + S4 CCI (no full 12-stream bridge)
        return {"bars_5min", "woodies_5min"}

    for arg in argv:
        if arg.startswith("--streams="):
            names = arg.split("=", 1)[1]
            return {name.strip() for name in names.split(",") if name.strip()}

    env_names = os.getenv("V9_STREAMS", "")
    if env_names.strip():
        return {name.strip() for name in env_names.split(",") if name.strip()}

    return None


def select_streams(argv=None):
    """Select bridge streams without changing the default all-stream behavior."""
    argv = sys.argv[1:] if argv is None else argv
    requested = _requested_stream_names(argv)
    if requested is None:
        return ALL_STREAMS

    by_name = {StreamClass.name: StreamClass for StreamClass in ALL_STREAMS}
    unknown = sorted(requested - set(by_name))
    if unknown:
        raise SystemExit(
            "Unknown stream(s): "
            + ", ".join(unknown)
            + ". Available: "
            + ", ".join(sorted(by_name))
        )
    return [by_name[name] for name in sorted(requested)]


def main():
    history_only = "--history-only" in sys.argv
    stream_classes = select_streams()

    if history_only:
        logger.info("MEMS26 V9 Bridge — history-only mode (backfill then exit)")
    else:
        logger.info("MEMS26 V9 Bridge starting — %d streams", len(stream_classes))

    # P30 (2026-05-20): opt-in wipe of today's bars BEFORE any stream starts.
    # Default behaviour is unchanged (flag off). When the flag is set the
    # wipe restricts to ts >= today 00:00 ET so multi-day TPO / Day Type
    # windows stay intact. Failure to wipe must not block startup.
    try:
        wipe_today_bars_if_requested()
    except Exception as e:  # belt-and-braces — module-level try/except already swallows
        logger.warning("[BRIDGE STARTUP] wipe-today hook raised: %s — continuing startup", e)

    instances = [StreamClass() for StreamClass in stream_classes]

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
