"""T-637 — live inputs + lock state for the opening type v2 (backend/v9/systems/opening_classifier_v2.py).

read_opening_v2() → the reading the gateway should use for today's session, or None when it cannot be read.
  • bars: today's CLOSED RTH 5-min bars (trade_context.get_closed_rth_bars_today — canonical table, ts ≤ now−5m)
  • prev: the prior RTH session's high/low + TPO value area (30-min letters, 70% around the POC, same method as
          the 30-day study) and the overnight high/low (bars between yesterday 16:00 ET and today 09:30 ET)
  • atr:  the mean 5-min range over the last 3 FULL RTH sessions (a holiday half-day does not shrink the unit)
  • lock: one OpeningLock per session date (revocation inside the first 8 bars, see the classifier)
Everything is cached per (session date, bar count): the gateway may call this dozens of times per bar.
READ-ONLY. Fail-safe: any error ⇒ None (the caller keeps the T-314 label). One INFO line per new closed bar.
"""
from __future__ import annotations

import collections
import datetime as dt
import logging
import statistics
from typing import Dict, List, Optional

from backend.v9.systems.opening_classifier_v2 import OpeningLock, classify_opening_v2, describe

logger = logging.getLogger(__name__)
TICK = 0.25

_STATE: Dict = {"date": None, "prev": None, "atr": None, "lock": None, "last_n": -1, "last": None}


def session_profile(bars: List[dict]) -> Optional[dict]:
    """TPO value area of one RTH session from its 5-min bars (30-minute letters, 70% around the POC)."""
    if len(bars) < 30:
        return None
    prof = collections.defaultdict(set)
    for i, b in enumerate(bars):
        letter = i // 6
        p = float(b["l"])
        hi = float(b["h"])
        while p <= hi + 1e-9:
            prof[round(p / TICK) * TICK].add(letter)
            p += TICK
    counts = {p: len(v) for p, v in prof.items()}
    total = sum(counts.values())
    mid = (max(counts) + min(counts)) / 2
    poc = max(counts, key=lambda p: (counts[p], -abs(p - mid)))
    lo = hi = poc
    acc = counts[poc]
    while acc < 0.7 * total:
        upn = counts.get(round((hi + TICK) / TICK) * TICK, 0)
        dnn = counts.get(round((lo - TICK) / TICK) * TICK, 0)
        if upn >= dnn and upn > 0:
            hi = round((hi + TICK) / TICK) * TICK; acc += upn
        elif dnn > 0:
            lo = round((lo - TICK) / TICK) * TICK; acc += dnn
        else:
            break
    return {"poc": poc, "vah": hi, "val": lo, "high": max(float(b["h"]) for b in bars),
            "low": min(float(b["l"]) for b in bars), "close": float(bars[-1]["c"])}


def _q(sql: str, params: dict) -> list:
    from backend.v9.db.read import read_all
    return read_all(sql, params) or []


def _session_date_et(now: Optional[dt.datetime] = None) -> dt.date:
    from zoneinfo import ZoneInfo
    n = now or dt.datetime.now(dt.timezone.utc)
    return n.astimezone(ZoneInfo("America/New_York")).date()


def _prior_sessions(today: dt.date, k: int = 3) -> List[dict]:
    """the last k RTH session dates before `today` with their bars (oldest first)."""
    rows = _q("select distinct (ts at time zone 'America/New_York')::date as d from v9_bars_5min_woodies "
              "where symbol='MES' and (ts at time zone 'America/New_York')::date < :d "
              "and (ts at time zone 'America/New_York')::time >= '09:30' and (ts at time zone 'America/New_York')::time < '16:00' "
              "order by d desc limit :k", {"d": today, "k": k + 2})
    out = []
    for r in reversed(rows):
        d = r["d"]
        bars = _q("select ts, open, high, low, close from v9_bars_5min_woodies where symbol='MES' "
                  "and (ts at time zone 'America/New_York')::date = :d and (ts at time zone 'America/New_York')::time >= '09:30' "
                  "and (ts at time zone 'America/New_York')::time < '16:00' order by ts", {"d": d})
        seen, bb = set(), []
        for b in bars:
            if b["ts"] in seen:
                continue
            seen.add(b["ts"])
            bb.append({"o": float(b["open"]), "h": float(b["high"]), "l": float(b["low"]), "c": float(b["close"])})
        out.append({"date": d, "bars": bb})
    return out


def _overnight(today: dt.date, prev_d: dt.date):
    rows = _q("select max(high) as h, min(low) as l from v9_bars_5min_woodies where symbol='MES' and ts > "
              "((CAST(:p AS date) + time '16:00') at time zone 'America/New_York') and ts < ((CAST(:d AS date) + time '09:30') at time zone 'America/New_York')",
              {"p": prev_d, "d": today})
    if rows and rows[0]["h"] is not None:
        return float(rows[0]["h"]), float(rows[0]["l"])
    return None, None


def _inputs_for(today: dt.date) -> Dict:
    sess = _prior_sessions(today)
    prev = None
    full = [statistics.mean(b["h"] - b["l"] for b in s["bars"]) for s in sess if len(s["bars"]) >= 60][-3:]
    atr = statistics.mean(full) if full else None
    for s in reversed(sess):
        if len(s["bars"]) >= 30:
            prev = session_profile(s["bars"])
            if prev:
                prev["date"] = str(s["date"])
                oh, ol = _overnight(today, s["date"])
                prev["on_high"], prev["on_low"] = oh, ol
            break
    return {"prev": prev, "atr": atr}


def read_opening_v2(now: Optional[dt.datetime] = None, bars: Optional[List[dict]] = None) -> Optional[Dict]:
    """The opening-type v2 reading for the current session (None when unreadable). Cached per bar count."""
    try:
        today = _session_date_et(now)
        if _STATE["date"] != today:
            inp = _inputs_for(today)
            _STATE.update({"date": today, "prev": inp["prev"], "atr": inp["atr"], "lock": OpeningLock(), "last_n": -1, "last": None})
            logger.info("[OpeningV2] session %s inputs: prev=%s atr=%s", today,
                        {k: _STATE["prev"].get(k) for k in ("date", "high", "low", "vah", "val", "poc", "on_high", "on_low")} if _STATE["prev"] else None,
                        round(_STATE["atr"], 2) if _STATE["atr"] else None)
        if bars is None:
            from backend.v9.services.trade_context import get_closed_rth_bars_today
            bars = get_closed_rth_bars_today() or []
        n = min(len(bars), 12)
        if n == _STATE["last_n"] and _STATE["last"] is not None:
            return _STATE["last"]
        if n == 0:
            return None
        res = _STATE["lock"].update(bars[:12], _STATE["prev"], _STATE["atr"])
        _STATE["last_n"], _STATE["last"] = n, res
        logger.info("[OpeningV2] bar %d: %s", n, describe(res))
        return res
    except Exception as e:  # fail-open: the caller keeps the T-314 label
        logger.info("[OpeningV2] unreadable (fail-open): %s", e)
        return None


def reset_state() -> None:
    """tests / a new process."""
    _STATE.update({"date": None, "prev": None, "atr": None, "lock": None, "last_n": -1, "last": None})
