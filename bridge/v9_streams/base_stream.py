"""Base v9 stream reader — watches a DLL JSON export, pushes to Redis + FastAPI."""

import json
import os
import time
import logging
import threading
from pathlib import Path
from typing import Optional
import urllib.request
import urllib.error

logger = logging.getLogger("v9_bridge")

EXPORT_DIR = os.getenv("V9_EXPORT_DIR", "/Users/michael/SierraChart_Data/v9_export")
REDIS_URL = os.getenv("UPSTASH_REDIS_REST_URL", "")
REDIS_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
CLOUD_URL = os.getenv("CLOUD_URL", "https://mems26-web.onrender.com")
BRIDGE_TOKEN = os.getenv("BRIDGE_TOKEN", "michael-mems26-2026")

POLL_INTERVAL = float(os.getenv("V9_POLL_INTERVAL", "2.0"))
MAX_RETRIES = 3
RETRY_DELAY = 5.0
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

    def start(self):
        logger.info(f"[{self.name}] Starting stream — watching {self.filepath}")

        # Historical backfill before going live (V8 parity)
        try:
            loaded = self.historical_load()
            if loaded:
                logger.info(f"[{self.name}] Historical backfill complete")
        except Exception as e:
            logger.warning(f"[{self.name}] Historical backfill failed: {e}")

        while not self._stop.is_set():
            try:
                self._tick()
            except Exception as e:
                self._consecutive_errors += 1
                logger.error(f"[{self.name}] Error (#{self._consecutive_errors}): {e}")
                if self._consecutive_errors >= MAX_RETRIES:
                    logger.warning(f"[{self.name}] {MAX_RETRIES} consecutive errors, backing off")
                    self._stop.wait(RETRY_DELAY * self._consecutive_errors)
            self._stop.wait(POLL_INTERVAL)
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

        logger.info(f"[{self.name}] New data — export_ts={export_ts}")
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

    def _redis_set(self, key: str, value: str):
        self._redis_cmd(["SET", key, value])

    def _redis_lpush(self, key: str, value: str):
        self._redis_cmd(["LPUSH", key, value])
        self._redis_cmd(["LTRIM", key, "0", "99"])

    def _redis_cmd(self, args: list):
        if not REDIS_URL or not REDIS_TOKEN:
            return
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
            with urllib.request.urlopen(req, timeout=10):
                pass
        except urllib.error.URLError as e:
            logger.warning(f"[{self.name}] Redis cmd {args[0]} error: {e}")

    def _push_api(self, data: dict):
        url = f"{CLOUD_URL}{self.api_path}"
        try:
            body = json.dumps(data).encode()
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
            logger.debug(f"[{self.name}] API push error (W3 placeholder): {e}")

    def _send_heartbeat(self):
        ts = int(time.time())
        self._redis_set(f"{self.redis_key}:heartbeat", str(ts))
        logger.debug(f"[{self.name}] Heartbeat sent at {ts}")
