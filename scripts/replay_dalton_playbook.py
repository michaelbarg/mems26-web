#!/usr/bin/env python3
"""replay_dalton_playbook.py — replay the DaltonPlaybook on 39 sessions.

For each session and each setup in the decision archive + v9_trades,
compute intent() at the signal time and report:
  - profit days: how many winners the playbook would approve (target ≥75%)
  - loss days: how many losers it would reject (target ≥60%)
  - total Σ$ of approved vs actual
  - n approved (target ≥40)
  - per-trade: bar where playbook first approves vs actual entry bar (latency)
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
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


def _get_sessions():
    """Get all trading sessions since 2026-08-01."""
    rows = read_all(
        """SELECT DISTINCT (entry_ts AT TIME ZONE 'America/New_York')::date AS d
        FROM v9_trades
        WHERE mode IN ('demo', 'live')
        AND entry_ts >= '2026-08-01'
        ORDER BY d""", {}
    )
    return [str(r["d"]) for r in rows]


def _get_trades(session_date):
    """Get trades for a session."""
    return read_all(
        """SELECT id, direction, day_type_at_entry, entry_price, stop, t1, t2, t3,
               pnl_usd, exit_reason, entry_ts, pattern_id_at_entry,
               quality::text AS quality_text
        FROM v9_trades
        WHERE mode IN ('demo', 'live')
        AND (entry_ts AT TIME ZONE 'America/New_York')::date = :d
        ORDER BY entry_ts""",
        {"d": session_date},
    )


def _get_bars(session_date):
    """Get RTH bars for a session."""
    return read_all(
        """SELECT ts, open AS o, high AS h, low AS l, close AS c, volume AS v
        FROM v9_bars_5min_woodies
        WHERE (ts AT TIME ZONE 'America/New_York')::date = :d
        AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30'
        AND (ts AT TIME ZONE 'America/New_York')::time < '16:00'
        ORDER BY ts""",
        {"d": session_date},
    )


def _opening_type_from_bars(bars):
    """Detect opening type from first 3-6 bars."""
    if len(bars) < 3:
        return "UNKNOWN", None
    from backend.v9.systems.day_type.opening_detector_v2 import detect_opening_type
    bar_dicts = [{"o": float(b["o"]), "h": float(b["h"]),
                  "l": float(b["l"]), "c": float(b["c"]),
                  "v": int(b["v"] or 0)} for b in bars[:6]]
    open_price = bar_dicts[0]["o"]
    result = detect_opening_type(bar_dicts, open_price)
    ot = result.get("opening_type", "UNKNOWN")
    direction = result.get("direction")
    return ot, direction


def _day_type_at_bar(bars, bar_idx):
    """Classify day type using bars up to bar_idx."""
    if bar_idx < 12:
        return None, None
    b = [{"o": float(r["o"]), "h": float(r["h"]),
          "l": float(r["l"]), "c": float(r["c"]),
          "v": int(r["v"] or 0), "ts": str(r["ts"])} for r in bars[:bar_idx]]
    ib_h = max(x["h"] for x in b[:12])
    ib_l = min(x["l"] for x in b[:12])
    result = classify_session(bars=b, ib_high=ib_h, ib_low=ib_l,
                               open_price=b[0]["o"])
    dt = result.get("day_type", "")
    direction = result.get("direction")
    return dt, direction


def _ts_to_il_hhmm(ts):
    """Convert a DB timestamp to IL HH:MM."""
    from datetime import datetime
    if hasattr(ts, "hour"):
        # DB returns timezone-aware datetimes in +03:00 (IL)
        return f"{ts.hour:02d}:{ts.minute:02d}"
    s = str(ts)
    try:
        dt = datetime.fromisoformat(s.replace(" ", "T"))
        return f"{dt.hour:02d}:{dt.minute:02d}"
    except Exception:
        return "17:00"


def main():
    sessions = _get_sessions()
    print(f"Sessions: {len(sessions)}")

    total_approved = 0
    total_approved_pnl = 0.0
    total_actual_pnl = 0.0
    total_trades = 0
    profit_day_approved = 0
    profit_day_total = 0
    loss_day_rejected = 0
    loss_day_total = 0

    for day in sessions:
        trades = _get_trades(day)
        bars = _get_bars(day)
        if not trades or len(bars) < 12:
            continue

        # Get opening_type from the DB (v9_day_type_state) — more accurate than re-detecting
        _ot_rows = read_all(
            """SELECT opening_type FROM v9_day_type_state
            WHERE (ts AT TIME ZONE 'America/New_York')::date = :d
            AND opening_type IS NOT NULL AND opening_type != 'NA'
            ORDER BY ts LIMIT 1""", {"d": day})
        if _ot_rows:
            ot = str(_ot_rows[0]["opening_type"]).replace("OpeningType.", "")
        else:
            ot, _ = _opening_type_from_bars(bars)
        ot_dir = None  # will be resolved from classify_session direction
        day_pnl = sum(float(t["pnl_usd"] or 0) for t in trades)
        is_profit_day = day_pnl > 0

        approved = 0
        rejected = 0
        for t in trades:
            pnl = float(t["pnl_usd"] or 0)
            direction = (t["direction"] or "").upper()

            # Find the bar index closest to entry time
            entry_ts = t.get("entry_ts")
            bar_idx = len(bars) - 1
            if entry_ts:
                for i, b in enumerate(bars):
                    if str(b["ts"]) >= str(entry_ts):
                        bar_idx = i
                        break

            # Day type: prefer the trade's own label; fall back to replay classify
            dt = t.get("day_type_at_entry") or ""
            dt_dir = None
            if not dt:
                dt, dt_dir = _day_type_at_bar(bars, bar_idx)
            il_hhmm = _ts_to_il_hhmm(entry_ts)

            # Direction hint
            dir_hint = ot_dir or dt_dir
            if dir_hint == "UP":
                dir_hint = "LONG"
            elif dir_hint == "DOWN":
                dir_hint = "SHORT"

            it = intent(opening_type=ot, day_type=dt or "",
                        now_il_hhmm=il_hhmm, direction_hint=dir_hint)

            classification = t.get("pattern_id_at_entry") or ""
            if not classification:
                try:
                    _qt = json.loads(t.get("quality_text") or "{}")
                    classification = _qt.get("classification") or _qt.get("pattern_name") or ""
                except Exception:
                    pass
            setup = {"direction": direction, "classification": classification,
                     "pattern": classification}
            block = evaluate_gate(setup, it)

            if block is None:
                approved += 1
                total_approved += 1
                total_approved_pnl += pnl
            else:
                rejected += 1

            total_actual_pnl += pnl
            total_trades += 1

        if is_profit_day:
            profit_day_total += 1
            if approved > 0:
                profit_day_approved += 1
        else:
            loss_day_total += 1
            if rejected > 0:
                loss_day_rejected += 1

        sym = "+" if day_pnl >= 0 else ""
        print(f"  {day}: {len(trades)}t {approved}A/{rejected}R "
              f"pnl={sym}${day_pnl:.2f} ot={ot} | intent.bias={it.bias if trades else '-'}")

    print(f"\n{'='*60}")
    print(f"Sessions: {len(sessions)} | Trades: {total_trades}")
    print(f"Approved: {total_approved} (target ≥40)")
    print(f"Approved Σ$: ${total_approved_pnl:.2f}")
    print(f"Actual Σ$: ${total_actual_pnl:.2f}")
    if profit_day_total:
        print(f"Profit days with approvals: {profit_day_approved}/{profit_day_total} "
              f"({100*profit_day_approved/profit_day_total:.0f}%, target ≥75%)")
    if loss_day_total:
        print(f"Loss days with rejections: {loss_day_rejected}/{loss_day_total} "
              f"({100*loss_day_rejected/loss_day_total:.0f}%, target ≥60%)")


if __name__ == "__main__":
    main()
