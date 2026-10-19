# -*- coding: utf-8 -*-
"""T-595 -- DAYTYPE_MACHINE_CLOSED_BARS_V1: the day-type state machine judges CLOSED 5-minute bars.

FINDING (Michael ruling 19.10.2026, "fix all the gaps").  `_day_type_on_bar` (backend/main.py) de-duplicates the
'5min' topic by bar ts -- the bridge re-publishes the developing bar ~41 times per 5 minutes -- so
`DayTypeStateMachine.process_bar` has only ever been handed the FIRST push of each bar: the one Sierra emits at the
bar's first tick, o == h == l == c with ~1% of the final volume.  Everything the machine decides from a bar's shape
therefore judged a point, not a bar: the A2 opening type ("OPEN_DRIVE" on 147 of 166 reconstructed days on flat
bars, 31 of 166 on closed bars), the first-hour Trend_Normal artifact (154/166), the acceptance demotion and the
exhaustion veto.

FIX (flag-gated, default OFF => main.py runs exactly the code it ran before).  With the flag ON the machine is fed,
for every ts, the bar as it stood at its LAST push, handed over the moment the next ts arrives (a bar is closed when
its successor starts).  Of the two routes in the ruling -- "the previous ts's last push" or "the canonical closed bar
the way the opening engine reads it (OPENING_ENGINE_CLOSED_BARS_V1)" -- this is the first, because
  1. the handler is push-driven: the last push is already in hand, no DB read on an async hot path;
  2. it is the very object S1_BAR_REFRESH_V1 already trusts for `_cls_rth_bars[-1]`, so the machine and the
     classifier agree on what a bar is;
  3. the canonical row of the bar that just closed may not be written yet when the next ts arrives (the race the
     opening engine documents as T7b);
  4. the wall-clock stage clocks stay wall-clock (`session_min`: provisional label at 30 min, IB lock at 60) --
     only the bar CONTENT changes (the IB lock now sees the 12 closed IB bars, not 12 + a flat 13th).
KNOWN LIMITS: the last push trails the final print by up to one push interval (a few seconds), so H/L/C/V can differ
by a tick or a few contracts from the canonical row; the machine is one bar behind by design, and the last bar of the
session is judged only if a later push arrives.

What the machine is handed: the BarInput main.py builds from the wall clock (ts, session_min, pd_*, ib_*) with the
closed bar's OHLCV and an `is_rth` taken from the closed bar's OWN timestamp (the Globex 09:25 bar that closes at
09:30:03 is not RTH, the 15:55 bar that closes at 16:00:03 is) -- unless that timestamp is more than an hour from the
wall clock, then it cannot be trusted to decide RTH and today's wall flag is kept.

FAIL-SAFE: any exception in here is a WARNING and the machine gets the old first-push input.
"""
from __future__ import annotations

import logging
import math
import os
import time as _time
from datetime import datetime, time as _dtime
from typing import Any, Dict, Optional, Tuple

from backend.v9.services.market_clock import ET, parse_market_timestamp

_log = logging.getLogger(__name__)

FLAG = "DAYTYPE_MACHINE_CLOSED_BARS_V1"
_TRUE = ("1", "true", "yes")
_RTH_OPEN = _dtime(9, 30)      # the window main.py's `_is_rth_bar` uses: time of day only
_RTH_CLOSE = _dtime(16, 0)
_RTH_TRUST_S = 3600.0          # a bar ts further than this from the wall clock does not decide RTH
_WARN_EVERY_S = 30.0
_last_warn: Dict[str, float] = {}

__all__ = ["FLAG", "enabled", "ClosedBarFeed", "run_machine", "closed_input", "ohlcv_of", "is_rth_ts"]


def enabled() -> bool:
    """Read at call time (never cached): the flag flips with env + restart, tests flip it per case."""
    return os.getenv(FLAG, "0").strip().lower() in _TRUE


def _warn(site: str, msg: str, *args: Any) -> None:
    """WARNING, at most one per site per 30 s (note_push runs on each of the ~41 pushes of a bar)."""
    now = _time.monotonic()
    if now - _last_warn.get(site, -1e9) >= _WARN_EVERY_S:
        _last_warn[site] = now
        _log.warning(msg, *args)


def _utc(ts: Any) -> Optional[datetime]:
    """Epoch / ISO text / datetime -> aware UTC datetime (naive text is read as UTC, the market_clock rule)."""
    try:
        return parse_market_timestamp(ts)
    except Exception:          # OverflowError / OSError on an absurd epoch
        return None


def _et_date(dt: datetime):
    return dt.astimezone(ET).date()


def is_rth_ts(dt: datetime) -> bool:
    """main.py's `_is_rth_bar` rule (09:30 <= t < 16:00 ET, time of day only) applied to the bar's OWN timestamp."""
    return _RTH_OPEN <= dt.astimezone(ET).time() < _RTH_CLOSE


def ohlcv_of(bar: Any) -> Tuple[float, float, float, float, float]:
    """O/H/L/C/V read exactly the way main.py builds its BarInput (long keys first, then o/h/l/c/v)."""
    vals = (
        float(bar.get("open", bar.get("o", 0))),
        float(bar.get("high", bar.get("h", 0))),
        float(bar.get("low", bar.get("l", 0))),
        float(bar.get("close", bar.get("c", 0))),
        float(bar.get("volume", bar.get("v", 0))),
    )
    if not all(math.isfinite(x) for x in vals):
        raise ValueError("non-finite OHLCV")
    return vals


def _snap(bar: Any, dt: datetime, prev: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """One push of a bar, frozen (the router may reuse the payload dict).  `first_*` keep the FIRST push of this
    ts so the log can show what the machine used to be fed."""
    o, h, l, c, v = ohlcv_of(bar)
    return {
        "ts": bar.get("ts"), "dt": dt, "o": o, "h": h, "l": l, "c": c, "v": v,
        "first_range": prev["first_range"] if prev else round(h - l, 4),
        "first_v": prev["first_v"] if prev else v,
        "pushes": prev["pushes"] + 1 if prev else 1,
    }


class ClosedBarFeed:
    """Holds the newest push of the bar being built; hands it out when the next ts arrives."""

    def __init__(self) -> None:
        self.held: Optional[Dict[str, Any]] = None

    def reset(self) -> None:
        self.held = None

    def note_push(self, bar: Any) -> None:
        """A repeat push of the bar being held (main.py's dedup branch): remember its newest state.  Never raises."""
        try:
            held = self.held
            if held is None:
                return
            dt = _utc(bar.get("ts"))
            if dt is None or dt != held["dt"]:
                return
            self.held = _snap(bar, dt, prev=held)
        except Exception as exc:
            _warn("note_push", "[T-595] note_push failed (%s) -- the previous push of this bar is kept", exc)

    def on_new_ts(self, bar: Any) -> Optional[Dict[str, Any]]:
        """The first push of a ts main.py has not seen.  Returns the bar that just CLOSED (the last push of the
        previous ts) or None when there is nothing to judge: first bar after a start, the same instant spelled
        differently (epoch vs ISO), an older ts (replayed / out-of-order), or a different ET date (a session's last
        bar is never judged inside the next session).  Raises ValueError for a bar without a usable ts or OHLCV;
        `run_machine` turns that into the old first-push feed."""
        dt = _utc(bar.get("ts"))
        if dt is None:
            raise ValueError("bar ts missing or unparseable")
        held = self.held
        if held is not None and dt == held["dt"]:
            self.held = _snap(bar, dt, prev=held)
            return None
        if held is not None and dt < held["dt"]:
            return None
        try:
            new = _snap(bar, dt)
        except Exception:
            self.held = None       # never keep a bar that could later be mistaken for this one's predecessor
            raise
        self.held = new
        if held is None or _et_date(dt) != _et_date(held["dt"]):
            return None
        return held


def closed_input(wall_input: Any, closed: Dict[str, Any]) -> Any:
    """The wall-clock BarInput with the closed bar's OHLCV; `is_rth` from the bar's own timestamp when that
    timestamp is within an hour of the wall clock, otherwise today's wall flag."""
    is_rth = bool(wall_input.is_rth)
    if abs(float(wall_input.ts) - closed["dt"].timestamp()) <= _RTH_TRUST_S:
        is_rth = is_rth_ts(closed["dt"])
    return wall_input.model_copy(update={
        "open": closed["o"], "high": closed["h"], "low": closed["l"], "close": closed["c"],
        "volume": closed["v"], "is_rth": is_rth,
    })


def _idle_state(machine: Any, wall_input: Any) -> Any:
    """Nothing closed on this push: the machine is not advanced; its cached state (or a pure build) is returned."""
    st = getattr(machine, "_last_state", None)
    return st if st is not None else machine._build_state(wall_input)


def run_machine(machine: Any, feed: ClosedBarFeed, bar: Any, wall_input: Any) -> Tuple[Any, Optional[Any]]:
    """Replacement for `state = machine.process_bar(wall_input)` when the flag is ON.

    Returns (state, judged): `judged` is the BarInput the machine actually processed (the closed bar) or None when
    nothing closed on this push.  Any exception: WARNING + the machine gets `wall_input` (the old behaviour)."""
    try:
        closed = feed.on_new_ts(bar)
        if closed is None:
            return _idle_state(machine, wall_input), None
        judged = closed_input(wall_input, closed)
        state = machine.process_bar(judged)
        _log.info(
            "[T-595] machine fed CLOSED bar ts=%s o=%.2f h=%.2f l=%.2f c=%.2f v=%.0f is_rth=%s session_min=%s "
            "(first push was range=%.2f v=%.0f; %d pushes)",
            closed["dt"].isoformat(), closed["o"], closed["h"], closed["l"], closed["c"], closed["v"],
            judged.is_rth, getattr(wall_input, "session_min", None), closed["first_range"], closed["first_v"],
            closed["pushes"])
        return state, judged
    except Exception as exc:
        _warn("run_machine", "[T-595] closed-bar feed failed (%s) -- machine fed the first-push bar as before", exc)
        return machine.process_bar(wall_input), wall_input
