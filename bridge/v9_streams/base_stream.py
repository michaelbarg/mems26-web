"""Base v9 stream reader — watches a DLL JSON export, pushes to Redis + FastAPI.

Supports two file-change detection modes:
  1. watchdog/fsevents (preferred, ~10ms latency) — resolves latency violation #L2
  2. mtime polling (fallback, ~2s latency) — used if watchdog unavailable
"""

import json
import os
import random
import time
import logging
import threading
from pathlib import Path
from typing import Optional
import urllib.request
import urllib.error

logger = logging.getLogger("v9_bridge")

# ── Try to import watchdog for file watching (latency #L2) ──
_WATCHDOG_AVAILABLE = False
if os.getenv("V9_DISABLE_WATCHDOG", "").lower() in ("1", "true", "yes"):
    logger.warning("watchdog disabled via V9_DISABLE_WATCHDOG — using mtime polling")
else:
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent
        _WATCHDOG_AVAILABLE = True
        logger.info("watchdog available — using fsevents file watching (latency #L2 resolved)")
    except ImportError:
        logger.warning("watchdog not installed — falling back to mtime polling (latency #L2 active)")

EXPORT_DIR = os.getenv("V9_EXPORT_DIR", "/Users/michael/SierraChart_Data/v9_export")
REDIS_URL = os.getenv("UPSTASH_REDIS_REST_URL", "")
REDIS_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
# Bridge Local-Only Rule: default to local backend. Any non-localhost CLOUD_URL
# is rejected at startup so we never silently push to render again. See CLAUDE.md.
CLOUD_URL = os.getenv("CLOUD_URL", "http://localhost:8000")
if "localhost" not in CLOUD_URL and "127.0.0.1" not in CLOUD_URL:
    raise RuntimeError(
        f"CLOUD_URL must be local (localhost or 127.0.0.1). Got: {CLOUD_URL}. "
        "Set CLOUD_URL=http://localhost:8000 in .env or unset to use default."
    )
BRIDGE_TOKEN = os.getenv("BRIDGE_TOKEN", "")
if not BRIDGE_TOKEN:
    raise RuntimeError(
        "BRIDGE_TOKEN env var is required but not set. "
        "Set it in .env or your hosting provider's environment variables."
    )

POLL_INTERVAL = float(os.getenv("V9_POLL_INTERVAL", "2.0"))
MAX_RETRIES = 3
RETRY_DELAY = 5.0
MAX_BACKOFF = 300.0  # 5 minutes max backoff
HEARTBEAT_INTERVAL = 30.0


class BaseV9Stream:
    """Base class for v9 DLL export stream readers."""

    name: str = ""
    filename: str = ""
    redis_key: str = ""
    api_path: str = ""

    def __init__(self):
        self._stop = threading.Event()
        self._last_mtime: float = 0
        self._last_export_ts: Optional[float] = None
        self._last_heartbeat: float = 0
        self._consecutive_errors: int = 0
        self.last_update_ts: float = 0  # public: last successful data read
        # ── Per-stream metrics (V6 audit: structured logging) ──
        self.push_count: int = 0
        self.error_count: int = 0
        self.last_push_ts: float = 0
        # ── Watchdog state ──
        self._file_changed = threading.Event()
        self._observer: Optional[object] = None

    @property
    def filepath(self) -> Path:
        return Path(EXPORT_DIR) / self.filename

    def historical_load(self) -> bool:
        """Load historical data from DLL export file on startup.
        Ported from V8 json_bridge.py history loading strategy."""
        from v9_history import historical_load as _load
        return _load(
            stream_name=self.name,
            filepath=self.filepath,
            redis_key=self.redis_key,
            api_path=self.api_path,
            redis_url=REDIS_URL,
            redis_token=REDIS_TOKEN,
            cloud_url=CLOUD_URL,
            bridge_token=BRIDGE_TOKEN,
        )

    def _backoff_delay(self) -> float:
        """Exponential backoff with jitter: min(RETRY_DELAY * 2^errors, MAX_BACKOFF) + jitter."""
        delay = min(RETRY_DELAY * (2 ** self._consecutive_errors), MAX_BACKOFF)
        jitter = random.uniform(0, delay * 0.1)  # up to 10% jitter
        return delay + jitter

    def _start_watchdog(self):
        """Start watchdog observer for fsevents-based file change detection."""
        if not _WATCHDOG_AVAILABLE:
            return False

        stream = self

        class _Handler(FileSystemEventHandler):
            def on_modified(self, event):
                if not event.is_directory and Path(event.src_path).name == stream.filename:
                    stream._file_changed.set()

            def on_created(self, event):
                if not event.is_directory and Path(event.src_path).name == stream.filename:
                    stream._file_changed.set()

        watch_dir = str(Path(EXPORT_DIR))
        if not os.path.isdir(watch_dir):
            logger.warning(f"[{self.name}] Export dir {watch_dir} does not exist, watchdog skipped")
            return False

        try:
            self._observer = Observer()
            self._observer.schedule(_Handler(), watch_dir, recursive=False)
            self._observer.daemon = True
            self._observer.start()
            logger.info(f"[{self.name}] watchdog observer started on {watch_dir}")
            return True
        except Exception as e:
            logger.warning(f"[{self.name}] watchdog start failed: {e}, falling back to polling")
            self._observer = None
            return False

    def _stop_watchdog(self):
        """Stop watchdog observer if running."""
        if self._observer is not None:
            try:
                self._observer.stop()
                self._observer.join(timeout=3)
            except Exception:
                pass
            self._observer = None

    def start(self):
        logger.info(f"[{self.name}] Starting stream — watching {self.filepath}")

        # Historical backfill before going live (V8 parity)
        try:
            loaded = self.historical_load()
            if loaded:
                logger.info(f"[{self.name}] Historical backfill complete")
        except Exception as e:
            logger.warning(f"[{self.name}] Historical backfill failed: {e}")

        # Try watchdog/fsevents first (latency #L2), fall back to polling
        use_watchdog = self._start_watchdog()
        if use_watchdog:
            logger.info(f"[{self.name}] Mode: watchdog/fsevents (low latency)")
        else:
            logger.info(f"[{self.name}] Mode: mtime polling (interval={POLL_INTERVAL}s)")

        while not self._stop.is_set():
            try:
                if use_watchdog:
                    # Wait for fsevents notification OR timeout (for heartbeat)
                    triggered = self._file_changed.wait(timeout=POLL_INTERVAL)
                    if triggered:
                        self._file_changed.clear()
                self._tick()
            except Exception as e:
                self._consecutive_errors += 1
                self.error_count += 1
                logger.error(f"[{self.name}] Error (#{self._consecutive_errors}): {e}")
                if self._consecutive_errors >= MAX_RETRIES:
                    backoff = self._backoff_delay()
                    logger.warning(f"[{self.name}] {MAX_RETRIES}+ consecutive errors, "
                                   f"backing off {backoff:.1f}s")
                    self._stop.wait(backoff)
            if not use_watchdog:
                self._stop.wait(POLL_INTERVAL)

        self._stop_watchdog()
        logger.info(f"[{self.name}] Stopped")

    def stop(self):
        self._stop.set()

    def _tick(self):
        now = time.time()

        # Heartbeat
        if now - self._last_heartbeat >= HEARTBEAT_INTERVAL:
            self._send_heartbeat()
            self._last_heartbeat = now

        # Check file
        if not self.filepath.exists():
            return

        mtime = self.filepath.stat().st_mtime
        if mtime <= self._last_mtime:
            return

        data = self._read_file()
        if data is None:
            return

        export_ts = data.get("export_ts")
        if export_ts and export_ts == self._last_export_ts:
            return

        self._last_mtime = mtime
        self._last_export_ts = export_ts
        self._consecutive_errors = 0
        self.last_update_ts = time.time()
        self.push_count += 1
        self.last_push_ts = time.time()

        logger.info(f"[{self.name}] New data — export_ts={export_ts} "
                     f"(push #{self.push_count})")
        self._push_redis(data)
        self._push_api(data)

    def _read_file(self) -> Optional[dict]:
        try:
            with open(self.filepath, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"[{self.name}] Read error: {e}")
            return None

    def _push_redis(self, data: dict):
        if not REDIS_URL or not REDIS_TOKEN:
            logger.debug(f"[{self.name}] Redis not configured, skipping")
            return

        payload = json.dumps(data)
        key = self.redis_key

        self._redis_set(f"{key}:latest", payload)
        self._redis_lpush(key, payload)

        # Update mems26:latest with live price from any stream that has OHLC data
        self._update_latest_price(data)

    def _update_latest_price(self, data: dict):
        """Update mems26:latest Redis key with live price if OHLC data is present.

        Extracts price from the 'close' field of the data payload. Streams that
        carry OHLC data (cumulative_delta, woodies_30min, tick_reversal, 5min, etc.)
        will update this key on every push cycle (~3s when market is open).

        The top bar reads this key to display the current price.
        """
        # Try multiple field names for close price
        price = data.get("close") or data.get("last") or data.get("price")

        # For streams with nested bar data (e.g. {"bars": [...]})
        if price is None and "bars" in data and isinstance(data["bars"], list) and data["bars"]:
            last_bar = data["bars"][-1]
            price = last_bar.get("close") or last_bar.get("last") or last_bar.get("price")

        # For footprint stream with bid/ask
        bid = data.get("bid")
        ask = data.get("ask")

        if price is None:
            return  # This stream does not carry price data

        try:
            price = float(price)
        except (TypeError, ValueError):
            return

        latest_payload = json.dumps({
            "price": price,
            "ts": int(time.time()),
            "bid": float(bid) if bid is not None else None,
            "ask": float(ask) if ask is not None else None,
            "source": self.name,
        })
        self._redis_set("mems26:latest", latest_payload)

    def _redis_set(self, key: str, value: str):
        self._redis_cmd(["SET", key, value])

    def _redis_lpush(self, key: str, value: str):
        self._redis_cmd(["LPUSH", key, value])
        # LTRIM to cap list at 100 items — log failures explicitly
        resp = self._redis_cmd(["LTRIM", key, "0", "99"])
        if resp is not None and "error" in str(resp).lower():
            logger.error(f"[{self.name}] LTRIM failed for {key}: {resp}")

    def _redis_cmd(self, args: list):
        if not REDIS_URL or not REDIS_TOKEN:
            return None
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
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                return result.get("result")
        except urllib.error.URLError as e:
            logger.warning(f"[{self.name}] Redis cmd {args[0]} error: {e}")
            return None

    def _push_api(self, data: dict):
        url = f"{CLOUD_URL}{self.api_path}"
        if not getattr(self, "_logged_push_url", False):
            logger.info(f"[{self.name}] API push target: {url}")
            self._logged_push_url = True
        try:
            payload = data.get("bars") if self.api_path.endswith("/bars/5min") and isinstance(data.get("bars"), list) else data
            body = json.dumps(payload).encode()
            req = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Authorization": f"Bearer {BRIDGE_TOKEN}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                logger.debug(f"[{self.name}] API push OK: {resp.status}")
        except urllib.error.URLError as e:
            self.error_count += 1
            if self.error_count <= 3 or self.error_count % 50 == 0:
                logger.warning(
                    f"[{self.name}] API push FAILED to {url}: {e} "
                    f"(error_count={self.error_count})"
                )

    def _send_heartbeat(self):
        ts = int(time.time())
        self._redis_set(f"{self.redis_key}:heartbeat", str(ts))

        # Per-stream stats in heartbeat (V6 audit: structured logging)
        age = int(ts - self.last_push_ts) if self.last_push_ts > 0 else -1
        mode = "watchdog" if self._observer is not None else "polling"
        logger.info(
            f"[{self.name}] heartbeat — pushes={self.push_count} "
            f"errors={self.error_count} last_push_age={age}s mode={mode}"
        )

        # LLEN check moved here from every-push (V6 audit: reduce Redis calls)
        llen_resp = self._redis_cmd(["LLEN", self.redis_key])
        if llen_resp is not None:
            try:
                length = int(llen_resp) if isinstance(llen_resp, (int, str)) else 0
                if length > 10_000:
                    logger.error(
                        f"[{self.name}] ALERT: Redis list {self.redis_key} has {length} items "
                        f"(>10K) — unbounded growth detected, LTRIM may be failing"
                    )
                elif length > 200:
                    logger.warning(
                        f"[{self.name}] Redis list {self.redis_key} has {length} items "
                        f"(expected <=100) — LTRIM may be failing"
                    )
            except (ValueError, TypeError):
                pass
