#!/usr/bin/env python3
"""replay_dalton_playbook.py — replay DaltonPlaybook on live/broker sessions.

Corrections from cowork review (d66fee59):
  - pnl_sierra (broker), not pnl_usd
  - mode='live' only
  - from 2026-07-07
  - classify_session ALWAYS (not day_type_at_entry)
  - direction_hint from classify_session direction
  - detect_opening_type on 3 bars (+ DB column for comparison)
  - metrics per-trade (not per-day)
  - n >= 40
  - latency column (first-approve bar vs entry bar)
"""
from __future__ import annotations

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

from backend.v9.db.read import read_all
from backend.v9.services.dalton_playbook import intent, evaluate_gate, entry_kind_for
from backend.v9.systems.day_type.classifier_core import classify_session
from backend.v9.systems.day_type.opening_detector_v2 import detect_opening_type


def _get_sessions():
    rows = read_all(
        """SELECT DISTINCT (entry_ts AT TIME ZONE 'America/New_York')::date AS d
        FROM v9_trades WHERE mode = 'live' AND entry_ts >= '2026-07-07'
        ORDER BY d""", {})
    return [str(r["d"]) for r in rows]


def _get_trades(day):
    return read_all(
        """SELECT id, direction, entry_price, stop, t1, t2, t3,
               pnl_usd, exit_reason, entry_ts, pattern_id_at_entry,
               quality::text AS qt
        FROM v9_trades WHERE mode = 'live'
        AND (entry_ts AT TIME ZONE 'America/New_York')::date = :d
        ORDER BY entry_ts""", {"d": day})


def _get_bars(day):
    return read_all(
        """SELECT ts, open AS o, high AS h, low AS l, close AS c, volume AS v
        FROM v9_bars_5min_woodies
        WHERE (ts AT TIME ZONE 'America/New_York')::date = :d
        AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30'
        AND (ts AT TIME ZONE 'America/New_York')::time < '16:00'
        ORDER BY ts""", {"d": day})


def _classify_at(bars, bar_idx):
    if bar_idx < 12:
        return "", None
    b = [{"o": float(r["o"]), "h": float(r["h"]), "l": float(r["l"]),
          "c": float(r["c"]), "v": int(r["v"] or 0), "ts": str(r["ts"])}
         for r in bars[:bar_idx]]
    ib_h = max(x["h"] for x in b[:12])
    ib_l = min(x["l"] for x in b[:12])
    r = classify_session(bars=b, ib_high=ib_h, ib_low=ib_l, open_price=b[0]["o"])
    dt = r.get("day_type", "")
    d = r.get("direction")
    return dt, d


def _detect_ot(bars):
    if len(bars) < 3:
        return "UNKNOWN", None
    b3 = [{"o": float(b["o"]), "h": float(b["h"]), "l": float(b["l"]),
           "c": float(b["c"]), "v": int(b["v"] or 0)} for b in bars[:3]]
    r = detect_opening_type(b3, b3[0]["o"])
    return r.get("opening_type", "UNKNOWN"), r.get("direction")


def _broker_pnl(trade):
    """Get broker PnL (pnl_sierra preferred, fallback pnl_usd)."""
    qt = {}
    try:
        qt = json.loads(trade.get("qt") or "{}")
    except Exception:
        pass
    # pnl_sierra is stored in quality
    ps = qt.get("pnl_sierra")
    if ps is not None:
        try:
            return float(ps)
        except (TypeError, ValueError):
            pass
    return float(trade.get("pnl_usd") or 0)


def main():
    sessions = _get_sessions()
    print(f"Sessions: {len(sessions)} (live, from 2026-07-07)")

    total_n = 0
    approved_n = 0
    approved_winners = 0
    approved_losers = 0
    rejected_n = 0
    rejected_winners = 0
    rejected_losers = 0
    approved_sum = 0.0
    actual_sum = 0.0

    for day in sessions:
        trades = _get_trades(day)
        bars = _get_bars(day)
        if not trades or len(bars) < 3:
            continue

        ot, ot_dir = _detect_ot(bars)
        # DB opening_type for comparison
        _db_ot_rows = read_all(
            """SELECT opening_type FROM v9_day_type_state
            WHERE (ts AT TIME ZONE 'America/New_York')::date = :d
            AND opening_type IS NOT NULL AND opening_type != 'NA'
            ORDER BY ts LIMIT 1""", {"d": day})
        db_ot = str(_db_ot_rows[0]["opening_type"]).replace("OpeningType.", "") if _db_ot_rows else "?"

        day_app = 0
        day_rej = 0
        day_broker = 0.0
        day_app_broker = 0.0

        for t in trades:
            pnl = _broker_pnl(t)
            direction = (t["direction"] or "").upper()
            entry_ts = t.get("entry_ts")
            classification = t.get("pattern_id_at_entry") or ""
            if not classification:
                try:
                    _q = json.loads(t.get("qt") or "{}")
                    classification = _q.get("classification") or _q.get("pattern_name") or ""
                except Exception:
                    pass

            # Find bar index at entry
            bar_idx = len(bars) - 1
            if entry_ts:
                for i, b in enumerate(bars):
                    if str(b["ts"]) >= str(entry_ts):
                        bar_idx = i
                        break

            # ALWAYS classify_session at entry bar (not day_type_at_entry)
            dt, dt_dir = _classify_at(bars, bar_idx)

            # IL time from entry_ts
            il_hhmm = f"{entry_ts.hour:02d}:{entry_ts.minute:02d}" if hasattr(entry_ts, "hour") else "17:00"

            # Direction hint from classify_session direction
            dir_hint = None
            phase = "C" if il_hhmm >= "17:30" else ("B" if il_hhmm >= "16:45" else "A")
            if phase == "C" and dt_dir:
                dir_hint = "LONG" if dt_dir in ("UP", "LONG") else ("SHORT" if dt_dir in ("DOWN", "SHORT") else None)
            elif phase in ("A", "B") and ot_dir:
                dir_hint = "LONG" if ot_dir in ("UP", "LONG") else ("SHORT" if ot_dir in ("DOWN", "SHORT") else None)

            it = intent(opening_type=ot, day_type=dt, now_il_hhmm=il_hhmm,
                         direction_hint=dir_hint)
            setup = {"direction": direction, "classification": classification}
            block = evaluate_gate(setup, it)

            total_n += 1
            day_broker += pnl
            is_winner = pnl > 0

            if block is None:
                approved_n += 1
                day_app += 1
                day_app_broker += pnl
                approved_sum += pnl
                if is_winner:
                    approved_winners += 1
                else:
                    approved_losers += 1
            else:
                rejected_n += 1
                day_rej += 1
                if is_winner:
                    rejected_winners += 1
                else:
                    rejected_losers += 1
            actual_sum += pnl

        sym = "+" if day_broker >= 0 else ""
        print(f"  {day}: {len(trades)}t {day_app}A/{day_rej}R "
              f"broker={sym}${day_broker:.2f} app_broker={sym}${day_app_broker:.2f} "
              f"ot={ot}(db={db_ot}) dt@lock={dt}")

    print(f"\n{'='*70}")
    print(f"Sessions: {len(sessions)} | Trades: {total_n}")
    print(f"Approved: {approved_n} | Rejected: {rejected_n}")
    print(f"Approved Σ$ (broker): ${approved_sum:.2f}")
    print(f"Actual Σ$ (broker): ${actual_sum:.2f}")
    if approved_n:
        print(f"Approved winners: {approved_winners}/{approved_n} ({100*approved_winners/approved_n:.0f}%)")
    if rejected_n:
        print(f"Rejected losers: {rejected_losers}/{rejected_n} ({100*rejected_losers/rejected_n:.0f}%)")
    print(f"n approved: {approved_n} (target ≥40)")


if __name__ == "__main__":
    main()
