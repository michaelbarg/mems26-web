#!/usr/bin/env python3
"""mems26_arming_gate — proves the SYSTEMS are armed, not just the services alive.

Michael 2026-08-13 (after mac-2 sat out a full live session while every existing
check was green): "אני רוצה שמחר מערכת-2, מערכת-1, מערכת-6 וכל המערכות יעבדו
ויהיו דרוכות."

Why the old checks passed a dead machine: flag_guard proves FLAGS match,
mems26_verify proves SERVICES run, fire_drill proves the ROUTE is open — none of
them ever asked "can a pattern actually reach the gateway?". Four broken links
(day_type seed ImportError, FHB not rebuilt on hydrate, legacy bars table for
recency+buffer, stuck opening gate) all hid under green checks.

THE DISTINCTION this gate makes:
  blocked on `data.*` / internals  → the SYSTEM is broken (recency, buffer,
                                     mode, fhb, day_type unknown) → NOT ARMED
  blocked on market conditions     → the system is ALIVE and waiting (awaiting
                                     b1_sellers, swing_highs_found, ...) → ARMED

Usage:
  python3 scripts/mems26_arming_gate.py                      # this machine
  python3 scripts/mems26_arming_gate.py --host 10.1.118.70   # remote (ZeroTier)
  python3 scripts/mems26_arming_gate.py --preopen            # before RTH open
Exit: 0 = ARMED, 1 = NOT ARMED (reasons printed), 2 = could not evaluate.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

# internals = infrastructure the machine owes us; anything else = market wait
INTERNAL_KEYS = (
    "five_min_bar_recency", "cci_14_history", "mode_context", "fhb_eligible",
    "day_type_known", "auth_table_cell", "bar_data", "buffer",
)


def _get(host: str, path: str, timeout: int = 25):
    url = f"http://{host}/api/v9{path}"
    try:
        r = subprocess.run(["/usr/bin/curl", "-s", "-m", str(timeout), url],
                           capture_output=True, timeout=timeout + 5)
        return json.loads(r.stdout.decode() or "{}")
    except Exception as e:
        print(f"  ! fetch {path} failed: {str(e)[:70]}")
        return None


def _classify_block(reason: str) -> str:
    """'internal' (system broken) vs 'market' (system alive, waiting)."""
    low = (reason or "").lower()
    if "missing:" in low and any(k in low for k in INTERNAL_KEYS):
        return "internal"
    return "market"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="localhost:8000")
    ap.add_argument("--preopen", action="store_true",
                    help="before RTH open: day_type UNKNOWN and mode_context are allowed")
    args = ap.parse_args()
    host = args.host if ":" in args.host else f"{args.host}:8000"

    # Outside RTH the trading-window checks (mode_context, day_type, stream
    # cadence) are legitimately not satisfied — grade them like pre-open so the
    # gate never cries wolf at night (and never gives false comfort either: the
    # binding run is 15:50 pre-open and during the session).
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        _et = datetime.now(ZoneInfo("America/New_York"))
        _m = _et.hour * 60 + _et.minute
        in_rth = _et.weekday() < 5 and 570 <= _m <= 960  # 09:30-16:00 ET
    except Exception:
        in_rth = True
    if not in_rth:
        args.preopen = True

    print(f"══ MEMS26 arming gate · {host} · "
          f"{'RTH' if in_rth else 'outside-RTH (window checks relaxed)'} ══")
    failures: list[str] = []

    data = _get(host, "/build/pattern-status", timeout=30)
    if not data or not data.get("systems"):
        print("  ! pattern-status unavailable → cannot evaluate")
        return 2

    for sysd in data["systems"]:
        name = str(sysd.get("system_name") or sysd.get("name") or "?")
        pats = sysd.get("patterns") or []
        if not pats:
            continue
        internal, market, fired, other = [], 0, 0, 0
        for p in pats:
            st = str(p.get("status") or "")
            reason = str(p.get("reason") or "")
            if st == "fired":
                fired += 1
            elif st == "blocked":
                if _classify_block(reason) == "internal":
                    # pre-open grace: day_type/mode are legitimately not ready
                    if args.preopen and any(k in reason.lower() for k in
                                            ("day_type_known", "auth_table_cell", "mode_context")):
                        market += 1
                    else:
                        internal.append(f"{p.get('name')}: {reason[:70]}")
                else:
                    market += 1
            else:
                other += 1
        status = "🔴 NOT ARMED" if internal else "✅ ARMED"
        print(f"  {status}  {name[:40]:40s} fired={fired} waiting={market + other} broken={len(internal)}")
        for line in internal[:3]:
            print(f"        ↳ {line}")
        if internal:
            failures.append(f"{name}: {len(internal)} patterns blocked on internals ({internal[0][:50]})")

    # S6 supervisor + streams sanity (cheap, catches a dead loop)
    streams = _get(host, "/health/streams", timeout=15)
    if streams:
        dead = [s["name"] for s in streams.get("streams", [])
                if s.get("name") in ("5min", "woodies_5min", "live_price")
                and (s.get("status") != "healthy")]
        if dead and in_rth:
            failures.append(f"streams unhealthy: {','.join(dead)}")
            print(f"  🔴 streams unhealthy: {dead}")
        elif dead:
            print(f"  ⚪ streams idle outside RTH (not a failure): {dead}")
        else:
            print("  ✅ core streams healthy (5min · woodies_5min · live_price)")

    print("══", "🔴 NOT ARMED — do not trade until fixed" if failures else "✅ ALL SYSTEMS ARMED", "══")
    for f in failures:
        print("   -", f)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
