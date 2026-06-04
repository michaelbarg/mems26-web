"""Frozen-tail watchdog — detect + alert when Sierra DLL writes 5min.json
(mtime advances) but the bars array is stale, while live_price is alive.

Read-only monitoring: no writes to Sierra/DLL/risk-logic.

Detection signature (all must be true simultaneously):
  1. 5min.json mtime advanced within the last CHECK_INTERVAL
  2. Newest bar timestamp in 5min.json has NOT advanced for STALE_THRESHOLD
  3. live_price.json is alive (mtime within LIVE_PRICE_FRESH seconds)
  4. We are inside RTH (09:30–16:00 ET)

If (1) is false AND (3) is false → feed_down (not frozen-tail).
If (1) is true AND (2) is true AND (3) is true → frozen-tail.

Alert: Slack webhook (SLACK_UAT_WEBHOOK / SLACK_WEBHOOK_URL), or
       logger.warning rate-limited if no webhook configured.
       One alert per incident (re-alerts after REALERT_INTERVAL).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger("frozen_tail_watchdog")
ET = ZoneInfo("America/New_York")

# ── Configuration ────────────────────────────────────────────────────
CHECK_INTERVAL = 30.0        # seconds between checks
STALE_THRESHOLD = 600.0      # 10 minutes — bars tip must advance within this
LIVE_PRICE_FRESH = 30.0      # live_price.json mtime must be within this many seconds
REALERT_INTERVAL = 1800.0    # re-alert every 30 minutes if still frozen
RTH_START_HOUR = 9           # 09:30 ET
RTH_START_MIN = 30
RTH_END_HOUR = 16            # 16:00 ET
RTH_END_MIN = 0

EXPORT_DIR = os.getenv(
    "V9_EXPORT_DIR", "/Users/michael/SierraChart_Data/v9_export"
)


# ── State ────────────────────────────────────────────────────────────
class FrozenTailState:
    """Observable state for health endpoints."""
    __slots__ = (
        "status", "last_check_ts", "bars_tip_ts", "bars_tip_iso",
        "file_mtime", "live_price_age", "frozen_since",
        "alert_count", "last_alert_ts",
    )

    def __init__(self) -> None:
        self.status: str = "idle"          # idle | ok | frozen_tail | feed_down
        self.last_check_ts: float = 0.0
        self.bars_tip_ts: Optional[float] = None
        self.bars_tip_iso: Optional[str] = None
        self.file_mtime: float = 0.0
        self.live_price_age: float = -1.0
        self.frozen_since: Optional[float] = None
        self.alert_count: int = 0
        self.last_alert_ts: float = 0.0

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "last_check_ts": self.last_check_ts,
            "bars_tip_ts": self.bars_tip_ts,
            "bars_tip_iso": self.bars_tip_iso,
            "file_mtime": self.file_mtime,
            "live_price_age": round(self.live_price_age, 1),
            "frozen_since": self.frozen_since,
            "alert_count": self.alert_count,
        }


_state = FrozenTailState()


def get_frozen_tail_state() -> dict:
    """Return current watchdog state (for health endpoint)."""
    return _state.to_dict()


# ── File readers ─────────────────────────────────────────────────────

def _read_bars_tip(filepath: Path) -> Optional[float]:
    """Read the newest bar timestamp from 5min.json.

    Returns unix timestamp of the last bar, or None if unreadable.
    The file format is {"bars": [..., {"ts": "...", ...}]} or
    {"bars": [...], "export_ts": ...}.
    """
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
        bars = data.get("bars") or data.get("history") or []
        if not bars:
            return None
        last_bar = bars[-1]
        ts_val = last_bar.get("ts")
        if ts_val is None:
            return None
        if isinstance(ts_val, (int, float)):
            return float(ts_val)
        # ISO string
        try:
            dt = datetime.fromisoformat(str(ts_val).replace("Z", "+00:00"))
            return dt.timestamp()
        except (ValueError, TypeError):
            return None
    except (json.JSONDecodeError, OSError, KeyError):
        return None


def _file_mtime(filepath: Path) -> float:
    """Return file mtime as unix timestamp, or 0 if missing."""
    try:
        return filepath.stat().st_mtime
    except OSError:
        return 0.0


def _is_rth_now() -> bool:
    """True if current time is within RTH (09:30–16:00 ET)."""
    now_et = datetime.now(ET)
    t = now_et.hour * 60 + now_et.minute
    return (RTH_START_HOUR * 60 + RTH_START_MIN) <= t < (RTH_END_HOUR * 60 + RTH_END_MIN)


def _weekday_now() -> int:
    """0=Mon .. 6=Sun in ET."""
    return datetime.now(ET).weekday()


# ── Alert ────────────────────────────────────────────────────────────

def _send_alert(message: str, level: str = "warn") -> None:
    """Send alert via Slack webhook, or logger.warning if no webhook."""
    webhook = os.environ.get("SLACK_UAT_WEBHOOK") or os.environ.get("SLACK_WEBHOOK_URL")
    if webhook:
        try:
            icon = ":snowflake:" if level == "warn" else ":white_check_mark:"
            payload = json.dumps(
                {"text": f"{icon} *MEMS26 Frozen-Tail Watchdog*\n{message}"},
                ensure_ascii=False,
            ).encode("utf-8")
            req = urllib.request.Request(
                webhook,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
            logger.info("[FrozenTail] Slack alert sent: %s", message[:120])
        except Exception as e:
            logger.warning("[FrozenTail] Slack send failed (%s), falling back to log: %s", e, message)
    else:
        logger.warning("[FrozenTail] %s", message)


# ── PG check ─────────────────────────────────────────────────────────

def _pg_max_ts() -> Optional[float]:
    """Query MAX(ts) from v9_bars_5min via PG. Returns unix ts or None."""
    try:
        from backend.v9.db.session import SessionLocal
        from backend.v9.db.models.bars import V9Bar5Min
        from sqlalchemy import func
        db = SessionLocal()
        try:
            row = db.query(func.max(V9Bar5Min.ts)).scalar()
            if row is None:
                return None
            return row.timestamp() if hasattr(row, "timestamp") else float(row)
        finally:
            db.close()
    except Exception as e:
        logger.debug("[FrozenTail] PG query failed: %s", e)
        return None


# ── Core check ───────────────────────────────────────────────────────

def check_once() -> str:
    """Run a single frozen-tail check. Returns status string.

    Designed to be callable from both async loop and tests.
    """
    now = time.time()
    _state.last_check_ts = now

    # Skip outside RTH and weekends
    if not _is_rth_now() or _weekday_now() >= 5:
        _state.status = "idle"
        return "idle"

    fivemin_path = Path(EXPORT_DIR) / "5min.json"
    liveprice_path = Path(EXPORT_DIR) / "live_price.json"

    # File mtimes
    fivemin_mtime = _file_mtime(fivemin_path)
    liveprice_mtime = _file_mtime(liveprice_path)
    _state.file_mtime = fivemin_mtime

    fivemin_age = now - fivemin_mtime if fivemin_mtime > 0 else -1
    liveprice_age = now - liveprice_mtime if liveprice_mtime > 0 else -1
    _state.live_price_age = liveprice_age

    # Live price alive?
    liveprice_alive = liveprice_age >= 0 and liveprice_age < LIVE_PRICE_FRESH

    # 5min.json being written? (mtime within last 2 check intervals)
    fivemin_writing = fivemin_age >= 0 and fivemin_age < CHECK_INTERVAL * 2

    # If both are stale → feed_down (Sierra disconnected / not running)
    if not fivemin_writing and not liveprice_alive:
        _state.status = "feed_down"
        _state.frozen_since = None
        return "feed_down"

    # Read bars tip
    bars_tip = _read_bars_tip(fivemin_path)
    _state.bars_tip_ts = bars_tip
    if bars_tip:
        try:
            _state.bars_tip_iso = datetime.fromtimestamp(bars_tip, ET).strftime("%H:%M:%S ET")
        except (OSError, ValueError):
            _state.bars_tip_iso = str(bars_tip)

    # Cross-check with PG
    pg_max = _pg_max_ts()

    # Determine staleness: bars_tip or pg_max not advancing
    bars_stale = False
    if bars_tip is not None:
        bars_age = now - bars_tip
        if bars_age > STALE_THRESHOLD:
            bars_stale = True
    if pg_max is not None:
        pg_age = now - pg_max
        if pg_age > STALE_THRESHOLD:
            bars_stale = True

    # Frozen-tail: file being written + bars stale + live price alive
    if fivemin_writing and bars_stale and liveprice_alive:
        if _state.frozen_since is None:
            _state.frozen_since = now
        _state.status = "frozen_tail"

        # Rate-limited alert
        since_last_alert = now - _state.last_alert_ts
        if _state.last_alert_ts == 0 or since_last_alert >= REALERT_INTERVAL:
            tip_str = _state.bars_tip_iso or "unknown"
            pg_str = ""
            if pg_max:
                try:
                    pg_str = f", PG MAX(ts)={datetime.fromtimestamp(pg_max, ET).strftime('%H:%M ET')}"
                except (OSError, ValueError):
                    pg_str = f", PG MAX(ts)={pg_max}"
            duration = now - _state.frozen_since
            _send_alert(
                f"frozen-tail detected — 5min bars stuck at {tip_str}{pg_str}, "
                f"live_price alive ({liveprice_age:.0f}s old), "
                f"duration {duration/60:.0f}min. Reload Study required."
            )
            _state.alert_count += 1
            _state.last_alert_ts = now

        return "frozen_tail"

    # Healthy
    _state.status = "ok"
    _state.frozen_since = None
    return "ok"


# ── Async loop ───────────────────────────────────────────────────────

async def run_watchdog_loop() -> None:
    """Run frozen-tail watchdog as a background asyncio task.

    Designed to be started from app startup:
        asyncio.create_task(run_watchdog_loop())
    """
    logger.info("[FrozenTail] watchdog started (check every %.0fs, stale threshold %.0fs)",
                CHECK_INTERVAL, STALE_THRESHOLD)
    while True:
        try:
            status = check_once()
            if status == "frozen_tail":
                logger.info("[FrozenTail] status=frozen_tail, bars_tip=%s", _state.bars_tip_iso)
        except Exception:
            logger.exception("[FrozenTail] check error")
        await asyncio.sleep(CHECK_INTERVAL)
