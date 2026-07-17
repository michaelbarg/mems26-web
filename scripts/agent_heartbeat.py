#!/usr/bin/env python3
"""Write docs/reports/AGENT_HEARTBEAT.json — the session-watch liveness beacon the
dashboard TopBar shows as a green/yellow/red dot (§6, PROMPT_SYSTEMS_TRADE_UX_2026-07-10).

The live supervisor (session-watch) MUST call this at the end of every run, e.g.:
    python3 scripts/agent_heartbeat.py --verdict 🟢 \
        --note "flag_guard 47/47 · fire_drill GO · feed 1s" \
        --check flag_guard=PASS --check fire_drill=GO --check feed=fresh

Schema: {ts (ISO-8601 UTC), verdict "🟢|🟡|🔴", note, checks{}, source}.
The TopBar renders the dot + tooltip (note + "לפני X דק'"); a ts older than 40 min during
trading hours degrades to gray "הסוכן לא נבדק" — so a stale beacon reads as "not checked",
never as a false-green. This writer never fabricates a verdict; pass the real one.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "docs", "reports", "AGENT_HEARTBEAT.json")

# ── central ops log (N12) — GUARDED: logging must never break the beacon
try:
    sys.path.insert(0, REPO)
    from scripts.ops_log import log_event
except Exception:  # pragma: no cover
    def log_event(*_a, **_k):
        return False


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verdict", required=True, choices=["🟢", "🟡", "🔴"])
    ap.add_argument("--note", default="")
    ap.add_argument("--check", action="append", default=[], metavar="key=value",
                    help="repeatable; e.g. --check flag_guard=PASS")
    ap.add_argument("--source", default="session-watch")
    a = ap.parse_args()

    checks = {}
    for kv in a.check:
        if "=" in kv:
            k, v = kv.split("=", 1)
            checks[k.strip()] = v.strip()

    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "verdict": a.verdict,
        "note": a.note,
        "checks": checks,
        "source": a.source,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
    print(f"[agent_heartbeat] wrote {OUT}: {a.verdict} {a.note}")
    # N12 central ops log — one line per session-watch run (source = --source)
    level = {"🟢": "INFO", "🟡": "WARN", "🔴": "ERROR"}.get(a.verdict, "INFO")
    checks_str = " ".join(f"{k}={v}" for k, v in checks.items())
    log_event(a.source or "session-watch", level,
              f"{a.verdict} {a.note}" + (f" · {checks_str}" if checks_str else ""))


if __name__ == "__main__":
    main()
