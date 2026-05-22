"""LivePriceStream — watches live_price.json from DLL, publishes price.tick events to Event Bus.

Unlike other streams that POST to FastAPI, this stream publishes directly
to the Event Bus (Redis Streams) for minimum latency. The DLL writes
live_price.json every ~200ms with: {price, ts, bid, ask, vol}
"""

import json
import logging
import os
import time
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger("v9_bridge")

# ── Try watchdog for fsevents ──
_WATCHDOG_AVAILABLE = False
if os.getenv("V9_DISABLE_WATCHDOG", "").lower() not in ("1", "true", "yes"):
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        _WATCHDOG_AVAILABLE = True
    except ImportError:
        pass

EXPORT_DIR = os.getenv("V9_EXPORT_DIR", "/Users/michael/SierraChart_Data/v9_export")
REDIS_URL = os.getenv("UPSTASH_REDIS_REST_URL", "")
REDIS_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")

POLL_INTERVAL = 0.2  # 200ms to match DLL interval
LOG_EVERY_N = 100    # Log stats every 100 ticks


class LivePriceStream:
    """Watches live_price.json and publishes price.tick to Event Bus."""

    name = "live_price"
    filename = "live_price.json"

    def __init__(self):
        self._stop = threading.Event()
        self._file_changed = threading.Event()
        self._observer: Optional[object] = None
        self._last_mtime: float = 0
        self._last_sig = None  # (mtime, price) dedup tuple
        self._correlation_id: str = ""
        # Public metrics (compatible with bridge heartbeat)
        self.last_update_ts: float = 0
        self.push_count: int = 0
        self.error_count: int = 0
        self.last_push_ts: float = 0

    @property
    def filepath(self) -> Path:
        return Path(EXPORT_DIR) / self.filename

    def _init_correlation_id(self):
        """Create a session correlation ID."""
        import uuid
        self._correlation_id = uuid.uuid4().hex[:12]
        logger.info("[%s] session correlation_id: %s", self.name, self._correlation_id)

    def _start_watchdog(self) -> bool:
        if not _WATCHDOG_AVAILABLE:
            return False

        stream = self

        class Handler(FileSystemEventHandler):
            def on_modified(self, event):
                if not event.is_directory and Path(event.src_path).name == stream.filename:
                    stream._file_changed.set()

            def on_created(self, event):
                if not event.is_directory and Path(event.src_path).name == stream.filename:
                    stream._file_changed.set()

        watch_dir = str(Path(EXPORT_DIR))
        if not os.path.isdir(watch_dir):
            return False

        try:
            self._observer = Observer()
            self._observer.schedule(Handler(), watch_dir, recursive=False)
            self._observer.daemon = True
            self._observer.start()
            logger.info("[%s] watchdog observer started on %s", self.name, watch_dir)
            return True
        except Exception as e:
            logger.warning("[%s] watchdog start failed: %s", self.name, e)
            self._observer = None
            return False

    def start(self):
        """Main loop — watch file, publish to Event Bus."""
        logger.info("[%s] Starting — watching %s", self.name, self.filepath)
        self._init_correlation_id()

        use_watchdog = self._start_watchdog()
        mode = "watchdog" if use_watchdog else "polling"
        logger.info("[%s] Mode: %s (interval=%.1fms)", self.name, mode, POLL_INTERVAL * 1000)

        while not self._stop.is_set():
            try:
                if use_watchdog:
                    triggered = self._file_changed.wait(timeout=POLL_INTERVAL)
                    if triggered:
                        self._file_changed.clear()
                self._tick()
            except Exception as e:
                self.error_count += 1
                logger.error("[%s] Error: %s", self.name, e)
            if not use_watchdog:
                self._stop.wait(POLL_INTERVAL)

        if self._observer:
            try:
                self._observer.stop()
                self._observer.join(timeout=3)
            except Exception:
                pass
        logger.info("[%s] Stopped", self.name)

    def stop(self):
        self._stop.set()

    def historical_load(self) -> bool:
        """No historical load for live price — real-time only."""
        return False

    def _tick(self):
        if not self.filepath.exists():
            return

        mtime = self.filepath.stat().st_mtime
        if mtime <= self._last_mtime:
            return

        data = self._read_file()
        if data is None:
            return

        # Dedup on (mtime, price) — NOT ts alone.
        # DLL ts is time(nullptr) = seconds resolution, so multiple
        # 200ms ticks share the same ts. mtime is sub-second.
        price = data.get("price")
        sig = (mtime, price)
        if sig == self._last_sig:
            return
        self._last_sig = sig

        self._last_mtime = mtime
        self.last_update_ts = time.time()
        self.push_count += 1
        self.last_push_ts = time.time()

        self._publish_to_local_backend(data)
        self._publish_to_event_bus(data)

        if self.push_count % 20 == 0:
            logger.info(
                "[%s] %d ticks pushed — price=%.2f corr=%s",
                self.name, self.push_count,
                data.get("price", 0), self._correlation_id,
            )

    def _read_file(self) -> Optional[dict]:
        try:
            with open(self.filepath, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning("[%s] Read error: %s", self.name, e)
            return None

    def _publish_to_local_backend(self, data: dict):
        """POST tick to localhost:8000 — backend caches + broadcasts via WS.

        Fire-and-forget with tight timeout (0.3s). Failure is silent because
        the GET /api/v9/live_price fallback reads the file directly.
        """
        try:
            import urllib.request as _req
            body = json.dumps({
                "price": data.get("price", 0),
                "ts": data.get("ts"),
                "bid": data.get("bid"),
                "ask": data.get("ask"),
                "vol": data.get("vol"),
            }).encode()
            req = _req.Request(
                "http://localhost:8000/api/v9/live_price",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with _req.urlopen(req, timeout=0.3):
                pass
        except Exception:
            pass

    def _publish_to_event_bus(self, data: dict):
        """Publish price.tick event to Redis Streams via Upstash REST."""
        import urllib.request
        import urllib.error

        if not REDIS_URL or not REDIS_TOKEN:
            return

        ts_ms = int(data.get("ts", time.time()) * 1000) if data.get("ts") else int(time.time() * 1000)

        event_data = json.dumps({
            "event_type": "price.tick",
            "correlation_id": self._correlation_id,
            "ts_ms": ts_ms,
            "source": "bridge.live_price",
            "version": "1.0",
            "price": data.get("price", 0),
            "bid": data.get("bid"),
            "ask": data.get("ask"),
            "last_size": data.get("vol"),
            "payload": {},
        })

        # XADD mems26:events:price.tick MAXLEN ~ 1000 * event_type price.tick data <json>
        args = [
            "XADD", "mems26:events:price.tick",
            "MAXLEN", "~", "1000", "*",
            "event_type", "price.tick",
            "correlation_id", self._correlation_id,
            "ts_ms", str(ts_ms),
            "source", "bridge.live_price",
            "price", str(data.get("price", 0)),
            "data", event_data,
        ]

        try:
            body = json.dumps(args).encode()
            req = urllib.request.Request(
                REDIS_URL,
                data=body,
                headers={
                    "Authorization": f"Bearer {REDIS_TOKEN}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                pass  # Fire and forget
        except urllib.error.URLError as e:
            self.error_count += 1
            logger.warning("[%s] Event Bus publish error: %s", self.name, e)
