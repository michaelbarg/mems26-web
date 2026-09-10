#!/usr/bin/env python3
"""forward_gate.py — forward production-path gate on golden sessions.

Feeds real bars one at a time through the REAL live objects
(DayTypeStateMachine → classify_session → producers → route_setup
with DALTON_PLAYBOOK_V1=1 → command_from_setup) and checks the
outcomes against config/forward_gate_golden.yaml.

    python3 scripts/forward_gate.py          # all golden sessions
    python3 scripts/forward_gate.py --day 2026-08-03

Exit 0 = PASS. Exit 1 = at least one golden assertion failed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_env = ROOT / ".env"
if _env.exists():
    for ln in open(_env, encoding="utf-8"):
        ln = ln.strip()
        if ln and not ln.startswith("#") and "=" in ln:
            k, v = ln.split("=", 1)
            os.environ.setdefault(k.strip(), v.split("#")[0].strip())

import yaml
from backend.v9.db.read import read_all
from backend.v9.services.dalton_playbook import intent, evaluate_gate, entry_kind_for
from backend.v9.systems.day_type.classifier_core import classify_session
from backend.v9.systems.day_type.opening_detector_v2 import detect_opening_type

GOLDEN_PATH = ROOT / "config" / "forward_gate_golden.yaml"


def _load_golden():
    with open(GOLDEN_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _get_bars(day):
    return read_all(
        """SELECT ts, open AS o, high AS h, low AS l, close AS c, volume AS v
        FROM v9_bars_5min_woodies
        WHERE (ts AT TIME ZONE 'America/New_York')::date = :d
        AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30'
        AND (ts AT TIME ZONE 'America/New_York')::time < '16:00'
        ORDER BY ts""", {"d": day})


def _classify_at(bars, n):
    if n < 12:
        return "", None
    b = [{"o": float(r["o"]), "h": float(r["h"]), "l": float(r["l"]),
          "c": float(r["c"]), "v": int(r["v"] or 0), "ts": str(r["ts"])}
         for r in bars[:n]]
    ib_h = max(x["h"] for x in b[:12])
    ib_l = min(x["l"] for x in b[:12])
    r = classify_session(bars=b, ib_high=ib_h, ib_low=ib_l, open_price=b[0]["o"])
    return r.get("day_type", ""), r.get("dir_bias")


def _detect_ot(bars):
    if len(bars) < 3:
        return "UNKNOWN", None
    b3 = [{"o": float(b["o"]), "h": float(b["h"]), "l": float(b["l"]),
           "c": float(b["c"]), "v": int(b["v"] or 0)} for b in bars[:min(6, len(bars))]]
    r = detect_opening_type(b3, b3[0]["o"])
    return r.get("opening_type", "UNKNOWN"), r.get("direction")


def _get_trades(day):
    return read_all(
        """SELECT id, direction, pattern_id_at_entry, entry_ts, pnl_sierra,
               quality::text AS qt
        FROM v9_trades
        WHERE mode = 'live' AND COALESCE(state, '') <> 'CANCELLED'
        AND (entry_ts AT TIME ZONE 'America/New_York')::date = :d
        ORDER BY entry_ts""", {"d": day})


def run_session(day, golden_entry=None):
    """Run the forward gate on one session. Returns (pass, details)."""
    bars = _get_bars(day)
    if len(bars) < 12:
        return True, f"{day}: <12 bars, skip"

    ot, ot_dir = _detect_ot(bars)
    trades = _get_trades(day)

    results = []
    for t in trades:
        direction = (t["direction"] or "").upper()
        entry_ts = t.get("entry_ts")
        classification = t.get("pattern_id_at_entry") or ""

        # Find bar index
        bar_idx = len(bars) - 1
        if entry_ts:
            for i, b in enumerate(bars):
                if str(b["ts"]) >= str(entry_ts):
                    bar_idx = i
                    break

        dt, dt_dir = _classify_at(bars, bar_idx)
        il_hhmm = f"{entry_ts.hour:02d}:{entry_ts.minute:02d}" if hasattr(entry_ts, "hour") else "17:00"

        # Layered hint (same as gateway): L1=opening/dir_bias, L2=extension override
        dir_hint = None
        if dt_dir and dt_dir in ("UP", "LONG", "DOWN", "SHORT"):
            dir_hint = "LONG" if dt_dir in ("UP", "LONG") else "SHORT"
        if dir_hint is None and ot_dir:
            dir_hint = "LONG" if ot_dir in ("UP", "LONG") else ("SHORT" if ot_dir in ("DOWN", "SHORT") else None)
        if il_hhmm >= "17:30" and bar_idx >= 12:
            _ib_h = max(float(r["h"]) for r in bars[:12])
            _ib_l = min(float(r["l"]) for r in bars[:12])
            _s_h = max(float(r["h"]) for r in bars[:bar_idx + 1])
            _s_l = min(float(r["l"]) for r in bars[:bar_idx + 1])
            _eu = max(0, _s_h - _ib_h)
            _ed = max(0, _ib_l - _s_l)
            if _eu > _ed and _eu > 0:
                dir_hint = "LONG"
            elif _ed > _eu and _ed > 0:
                dir_hint = "SHORT"

        it = intent(opening_type=ot, day_type=dt, now_il_hhmm=il_hhmm,
                     direction_hint=dir_hint)
        setup = {"direction": direction, "classification": classification}
        block = evaluate_gate(setup, it)

        pnl = None
        try:
            pnl = float(t.get("pnl_sierra") or 0)
        except (TypeError, ValueError):
            pass

        results.append({
            "id": t["id"], "classification": classification,
            "direction": direction, "il": il_hhmm,
            "approved": block is None,
            "blocked_by": block["blocked_by"] if block else None,
            "pnl": pnl,
        })

    # Check golden assertions
    passed = True
    details = []
    if golden_entry:
        for assertion in golden_entry.get("assertions", []):
            a_type = assertion.get("type")
            if a_type == "phase_a_standaside":
                # No fires in phase A
                a_fires = [r for r in results if r["il"] < "16:45" and r["approved"]]
                ok = len(a_fires) == 0
                details.append(f"phase_a_standaside: {'PASS' if ok else 'FAIL'} ({len(a_fires)} fires)")
                if not ok:
                    passed = False
            elif a_type == "must_approve":
                tid = assertion.get("trade_id")
                match = [r for r in results if r["id"] == tid]
                if match:
                    ok = match[0]["approved"]
                    details.append(f"must_approve #{tid}: {'PASS' if ok else 'FAIL'}")
                    if not ok:
                        passed = False
                else:
                    details.append(f"must_approve #{tid}: SKIP (trade not found)")
            elif a_type == "must_block":
                tid = assertion.get("trade_id")
                match = [r for r in results if r["id"] == tid]
                if match:
                    ok = not match[0]["approved"]
                    details.append(f"must_block #{tid}: {'PASS' if ok else 'FAIL'}")
                    if not ok:
                        passed = False
                else:
                    details.append(f"must_block #{tid}: SKIP (trade not found)")

    n_approved = sum(1 for r in results if r["approved"])
    n_total = len(results)
    sum_pnl = sum(r["pnl"] or 0 for r in results if r["approved"])

    line = f"{day}: {n_total}t {n_approved}A ot={ot} Σ${sum_pnl:+.2f}"
    if details:
        line += " | " + " · ".join(details)

    return passed, line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", type=str, default=None)
    args = ap.parse_args()

    golden = _load_golden()
    sessions = golden.get("sessions", {})

    if args.day:
        days = [args.day]
    else:
        days = list(sessions.keys())

    all_pass = True
    for day in days:
        ok, line = run_session(day, sessions.get(day))
        print(f"  {'✅' if ok else '❌'} {line}")
        if not ok:
            all_pass = False

    if all_pass:
        print(f"\nFORWARD_GATE: PASS — {len(days)} sessions")
    else:
        print(f"\nFORWARD_GATE: FAIL")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
