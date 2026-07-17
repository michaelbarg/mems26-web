#!/usr/bin/env python3
"""Missed-trade / quality watch — live session supervisor (Michael 2026-07-17:
"אני צריך זיהוי של עסקאות איכותיות ופיקוח שלא נפספס עסקאות").

Runs on the trading Mac during RTH. Read-only — NEVER places/cancels anything.

Every POLL_SEC it reads the gateway decisions feed and:

1. FIRED  → immediate quality card: pattern, direction, entry, and the quality
   context (day-type cell verdict + R:R when derivable) → ops_log + phone push.
2. BLOCKED on a QUALITY gate (rr_entry_gate, daytype_playbook, location_gate,
   zone_limit_late_entry, cont_trend_filter, ...) → immediate ops_log line +
   phone push ("נחסם — עוקב"), and the candidate enters a tracking list.
3. TRACKING (up to TRACK_MIN minutes per candidate) against the live price:
   - reached its T1-equivalent (entry ±T1_PTS) BEFORE its stop-equivalent
     (entry ∓STOP_PTS) → 🔴 MISSED-WINNER escalation: ops_log WARN + phone push
     ("החסימה בשער X עלתה +4 נק'") — so Michael can react DURING the session.
   - reached stop first → ✅ "the gate was right" (INFO, no push).
4. EOD summary: per-gate score (blocked-that-won vs blocked-that-lost) appended
   to ops_log — tomorrow's calibration input.

Infra gates (session_gate_closed, kill_switch, feed HALT, eod cutoff) are NOT
tracked — blocking there is policy, not quality judgment.

Usage:  nohup python3 scripts/missed_trade_watch.py > /tmp/missed_watch.log 2>&1 &
Stops itself after RTH close (+grace).
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))
from scripts.ops_log import log_event  # noqa: E402

API = os.getenv("MEMS26_API", "http://localhost:8000")
POLL_SEC = 20
TRACK_MIN = 45
T1_PTS = 4.0          # T1-equivalent for hypothetical outcome (CONFLUENCE C1 basis)
STOP_PTS = 6.0        # stop-equivalent when the candidate carries no stop
IL = ZoneInfo("Asia/Jerusalem")

QUALITY_GATES = {
    "rr_entry_gate", "daytype_playbook", "location_gate", "zone_limit_late_entry",
    "cont_trend_filter", "trend_direction_gate", "daytype_position_gate",
    "direction_context", "reactive_location", "lsma_flat", "day_direction_doctrine",
    "entry_not_confirmed", "opening_type_gate", "chop_searching", "cluster_guard",
    "duplicate_fire", "pattern_loss_breaker", "suffering_side_veto", "cooldown",
}


def _get(path: str):
    try:
        with urllib.request.urlopen(f"{API}{path}", timeout=8) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def _price() -> float | None:
    d = _get("/api/v9/live_price")
    if isinstance(d, dict):
        for k in ("price", "last", "close"):
            v = d.get(k)
            if isinstance(v, (int, float)) and v > 1000:
                return float(v)
    return None


def _push(title: str, body: str, priority: int = 0) -> None:
    try:
        from backend.v9.services.phone_alert import push
        push(f"mtw_{int(time.time())}", title, body, priority=priority)
    except Exception:
        pass


def _in_session(now: _dt.datetime) -> bool:
    m = now.hour * 60 + now.minute
    return (16 * 60 + 15) <= m <= (23 * 60 + 15)  # 16:15–23:15 IL (grace both ends)


def main() -> int:
    seen: set[str] = set()
    tracking: list[dict] = []
    gate_score: dict[str, list[int]] = {}   # gate -> [won(=missed), lost(=right)]
    log_event("missed_watch", "INFO",
              f"session supervisor up (poll {POLL_SEC}s, track {TRACK_MIN}min, "
              f"T1eq +{T1_PTS} / STOPeq -{STOP_PTS})")

    while True:
        now = _dt.datetime.now(IL)
        if now.hour * 60 + now.minute > 23 * 60 + 20:
            break
        if not _in_session(now):
            time.sleep(30)
            continue

        d = _get("/api/v9/gateway/decisions?limit=40") or {}
        px = _price()

        for dec in d.get("decisions", []):
            key = f"{dec.get('ts')}|{dec.get('pattern')}|{dec.get('direction')}|{dec.get('entry')}"
            if key in seen:
                continue
            seen.add(key)
            pat, dr = dec.get("pattern"), dec.get("direction")
            entry, gate = dec.get("entry"), dec.get("blocked_by")
            out = dec.get("outcome")

            if out in ("live", "demo"):
                log_event("missed_watch", "INFO",
                          f"QUALITY-ENTRY {pat} {dr} @{entry} → {out} trade={dec.get('trade_id')}")
                _push("🎯 MEMS26: כניסה", f"{pat} {dr} @{entry} ({out})", 0)
            elif out == "blocked" and gate in QUALITY_GATES and entry:
                log_event("missed_watch", "WARN",
                          f"BLOCK-TRACK {pat} {dr} @{entry} gate={gate} — עוקב {TRACK_MIN}דק'")
                _push("🚧 MEMS26: חסימה", f"{pat} {dr} @{entry} בשער {gate} — עוקב", 0)
                tracking.append({"t0": time.time(), "pat": pat, "dir": (dr or "").upper(),
                                 "entry": float(entry), "gate": gate, "done": False})

        if px is not None:
            for c in tracking:
                if c["done"]:
                    continue
                age_min = (time.time() - c["t0"]) / 60.0
                sign = 1.0 if c["dir"] == "LONG" else -1.0
                move = sign * (px - c["entry"])
                if move >= T1_PTS:
                    c["done"] = True
                    gate_score.setdefault(c["gate"], [0, 0])[0] += 1
                    log_event("missed_watch", "ERROR",
                              f"🔴 MISSED-WINNER {c['pat']} {c['dir']} @{c['entry']} "
                              f"gate={c['gate']} הגיע +{move:.2f} נק' תוך {age_min:.0f}דק'")
                    _push("🔴 MEMS26: פספוס", f"{c['pat']} {c['dir']} @{c['entry']} "
                          f"נחסם ({c['gate']}) והגיע +{move:.1f} נק'", 1)
                elif move <= -STOP_PTS:
                    c["done"] = True
                    gate_score.setdefault(c["gate"], [0, 0])[1] += 1
                    log_event("missed_watch", "INFO",
                              f"✅ gate-right {c['pat']} {c['dir']} @{c['entry']} "
                              f"gate={c['gate']} היה מפסיד ({move:.2f} נק')")
                elif age_min > TRACK_MIN:
                    c["done"] = True
                    log_event("missed_watch", "INFO",
                              f"⏱ track-expire {c['pat']} {c['dir']} @{c['entry']} "
                              f"gate={c['gate']} ({move:+.2f} נק' — לא-חד-משמעי)")

        time.sleep(POLL_SEC)

    if gate_score:
        parts = [f"{g}: פספוסים={w} צדק={l}" for g, (w, l) in sorted(gate_score.items())]
        log_event("missed_watch", "WARN", "סיכום-שערים EOD → " + " · ".join(parts))
    else:
        log_event("missed_watch", "INFO", "EOD: אין חסימות-איכות שנעקבו היום")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
