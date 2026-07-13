"""news_blackout — IDEA-1: NO_TRADE window around red economic events (Michael 07-13).

Dalton: pre-news days trade like Nontrend — the market waits; a red release
(FOMC/CPI/NFP/PPI) detonates volatility that no pattern-edge survives. The gate
blocks NEW entries inside [event − BEFORE_MIN, event + AFTER_MIN]; it never
touches management of an already-open trade (stops/targets keep working).

Calendar: config/news_calendar.yaml, hand-maintained (agent seeds a week ahead
each Monday from official sources). Times are ET in the file (explicit per
Rule 4), converted here. Honest fail-open: missing/invalid calendar → PASS +
rate-limited warning; an event not in the file simply doesn't block.

Flag: NEWS_BLACKOUT_V1 (default OFF). Params: NEWS_BLACKOUT_BEFORE_MIN (15),
NEWS_BLACKOUT_AFTER_MIN (30).
"""
from __future__ import annotations

import logging
import os
import time as _time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")
CAL = Path(__file__).resolve().parents[3] / "config" / "news_calendar.yaml"

_cache: Dict[str, Any] = {"mtime": None, "events": []}
_last_warn = 0.0


def _load_events():
    """Parsed red events as aware-ET datetimes; cached by file mtime."""
    global _last_warn
    try:
        mt = CAL.stat().st_mtime
        if _cache["mtime"] == mt:
            return _cache["events"]
        import yaml
        data = yaml.safe_load(CAL.read_text(encoding="utf-8")) or {}
        evs = []
        for e in data.get("events") or []:
            try:
                if str(e.get("severity", "")).lower() != "red":
                    continue
                d = str(e["date"])
                hh, mm = str(e["time_et"]).split(":")
                dt = datetime.fromisoformat(d).replace(
                    hour=int(hh), minute=int(mm), tzinfo=ET)
                evs.append({"dt": dt, "name": str(e.get("name", "?"))})
            except Exception:
                continue  # one bad row never kills the calendar
        _cache.update(mtime=mt, events=evs)
        return evs
    except Exception as e:
        if _time.time() - _last_warn > 300:
            logger.warning("[news_blackout] calendar unavailable (fail-open): %s", e)
            _last_warn = _time.time()
        return []


def check(now: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
    """Inside a red-event window? → {'event','window'} else None. Pure given `now`."""
    before = int(os.getenv("NEWS_BLACKOUT_BEFORE_MIN", "15"))
    after = int(os.getenv("NEWS_BLACKOUT_AFTER_MIN", "30"))
    now = now.astimezone(ET) if now else datetime.now(ET)
    for e in _load_events():
        lo = e["dt"] - timedelta(minutes=before)
        hi = e["dt"] + timedelta(minutes=after)
        if lo <= now <= hi:
            return {"event": e["name"], "event_time_et": e["dt"].strftime("%H:%M"),
                    "window": f"-{before}m..+{after}m"}
    return None


def enabled() -> bool:
    return os.getenv("NEWS_BLACKOUT_V1", "0").lower() in ("1", "true", "yes")


def start_auto_refresh(interval_h: float = 6.0) -> None:
    """מייקל 07-13 ("ואיך הוא מתעדכן?"): הבקאנד מרענן את הלוח בעצמו —
    בכל עלייה + כל `interval_h` שעות — מ-API-TradingView (גיבוי FF), דרך
    scripts/update_news_calendar.py בתת-תהליך (source-of-truth יחיד לפרסינג).
    כישלון-רענון = הקובץ הקיים נשאר (הסקריפט מסרב לדרוס בריק) + אזהרה בלוג.
    ‏Thread-דמון; לעולם לא נוגע בנתיב-המסחר."""
    import subprocess
    import threading

    script = Path(__file__).resolve().parents[3] / "scripts" / "update_news_calendar.py"

    def _loop():
        while True:
            try:
                r = subprocess.run(["python3", str(script)], capture_output=True,
                                   text=True, timeout=90, cwd=str(script.parent.parent))
                tail = (r.stdout.strip().splitlines() or ["?"])[-1]
                if r.returncode == 0:
                    logger.info("[news_cal] auto-refresh OK: %s", tail)
                else:
                    logger.warning("[news_cal] auto-refresh failed (keeping current file): %s",
                                   (r.stderr or r.stdout)[-200:])
            except Exception as e:
                logger.warning("[news_cal] auto-refresh error: %s", e)
            _time.sleep(interval_h * 3600)

    threading.Thread(target=_loop, daemon=True, name="news-cal-refresh").start()
