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
               pnl_usd, pnl_sierra, state, exit_reason, entry_ts, pattern_id_at_entry,
               quality::text AS qt
        FROM v9_trades WHERE mode = 'live'
        AND COALESCE(state, '') <> 'CANCELLED'
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
    """Broker P&L ONLY — the `pnl_sierra` column written by sierra_activity_join.

    cowork 09.09 11:10: no fallback to pnl_usd. A trade the broker never priced
    is not evidence (Rule 1); it is EXCLUDED from every gate number and counted
    separately. The earlier fallback relabelled the books as 'broker' and turned
    -313.75 into +221.25.
    """
    ps = trade.get("pnl_sierra")
    if ps is None:
        return None
    try:
        return float(ps)
    except (TypeError, ValueError):
        return None


def main():
    sessions = _get_sessions()
    print(f"Sessions: {len(sessions)} (live, from 2026-07-07)")

    total_n = 0
    unpriced_n = 0          # no broker price → excluded from every gate number
    approved_n = 0
    approved_winners = 0
    approved_losers = 0
    rejected_n = 0
    rejected_winners = 0
    rejected_losers = 0
    approved_sum = 0.0
    actual_sum = 0.0
    misses = []             # rejected winners  (the playbook's cost)
    leaks = []              # approved losers   (the playbook's blind spot)
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    # ── lab toggles (cowork 09.09 11:15) — simulate a tree variant WITHOUT touching
    # the playbook; the winning variant is then written into dalton_playbook.yaml by
    # cc and this script is re-run on the real code (the ship is the YAML, not these).
    phase_d_as_c = "--phase-d-as-c" in sys.argv     # 21:00+ keeps phase-C rules (Michael: "אתה לא מגביל שעות")
    phase_b_both = "--phase-b-both" in sys.argv     # opening direction is a hint, not a veto, in 16:45–17:30
    kinds_advisory = "--kinds-advisory" in sys.argv # entry_kind list is logged, not a veto
    with_bias_any_kind = "--with-bias-any-kind" in sys.argv  # directional bias ⇒ any kind in that direction (Dalton: trade WITH the drive)
    drive_fail_flip = "--drive-fail-flip" in sys.argv  # phase B: close back through the session open against the drive ⇒ drive failed ⇒ BOTH
    kind_would_block = 0
    drive_flips = 0
    rej_losers_rows = []

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

            _eval_hhmm = il_hhmm
            if phase_d_as_c and il_hhmm >= "21:00":
                _eval_hhmm = "20:59"
            if phase_b_both and phase == "B":
                dir_hint = None
            if drive_fail_flip and phase in ("A", "B") and dir_hint and bar_idx >= 1:
                # the market answers: a drive that has closed back through the open has failed
                _open = float(bars[0]["o"])
                _prev_c = float(bars[bar_idx - 1]["c"])
                if (dir_hint == "LONG" and _prev_c < _open) or (dir_hint == "SHORT" and _prev_c > _open):
                    dir_hint = None
                    drive_flips += 1
            it = intent(opening_type=ot, day_type=dt, now_il_hhmm=_eval_hhmm,
                         direction_hint=dir_hint)
            setup = {"direction": direction, "classification": classification}
            block = evaluate_gate(setup, it)
            if kinds_advisory and block and str((block or {}).get("reason", "")).startswith("entry_kind="):
                kind_would_block += 1
                block = None
            if (with_bias_any_kind and block and it.bias in ("LONG", "SHORT") and direction == it.bias
                    and str((block or {}).get("reason", "")).startswith("entry_kind=")):
                kind_would_block += 1
                block = None

            if pnl is None:
                unpriced_n += 1
                if verbose:
                    print(f"      · #{t['id']} {il_hhmm} {classification or '?'} {direction} "
                          f"UNPRICED (no broker row) → {'approved' if block is None else 'rejected'}")
                continue

            total_n += 1
            day_broker += pnl
            is_winner = pnl > 0
            row = {"day": day, "id": t["id"], "hhmm": il_hhmm, "phase": phase,
                   "cls": classification or "?", "dir": direction, "ot": ot, "dt": dt or "-",
                   "bias": it.bias, "kinds": ",".join(sorted(it.entry_kinds)) if getattr(it, "entry_kinds", None) else "-",
                   "kind": entry_kind_for(classification) if classification else "?",
                   "pnl": pnl, "why": (block or {}).get("reason") or (block or {}).get("blocked_by") or ""}

            if block is None:
                approved_n += 1
                day_app += 1
                day_app_broker += pnl
                approved_sum += pnl
                if is_winner:
                    approved_winners += 1
                else:
                    approved_losers += 1
                    leaks.append(row)
            else:
                rejected_n += 1
                day_rej += 1
                if is_winner:
                    rejected_winners += 1
                    misses.append(row)
                else:
                    rejected_losers += 1
                    rej_losers_rows.append(row)
            actual_sum += pnl

        sym = "+" if day_broker >= 0 else ""
        print(f"  {day}: {len(trades)}t {day_app}A/{day_rej}R "
              f"broker={sym}${day_broker:.2f} app_broker={sym}${day_app_broker:.2f} "
              f"ot={ot}(db={db_ot}) dt@lock={dt}")

    winners = approved_winners + rejected_winners
    losers = approved_losers + rejected_losers
    win_recall = 100.0 * approved_winners / winners if winners else 0.0
    loss_recall = 100.0 * rejected_losers / losers if losers else 0.0

    def _dump(title, rows):
        print(f"\n{title} ({len(rows)}):")
        print("  date        id    IL    ph  dt                 ot                     bias   kind          cls                     dir    $      why")
        for r in sorted(rows, key=lambda x: x["pnl"], reverse=("winner" in title)):
            print(f"  {r['day']}  {r['id']:<5} {r['hhmm']}  {r['phase']}   {r['dt'][:18]:<18} {r['ot'][:22]:<22} "
                  f"{r['bias']:<6} {r['kind'][:13]:<13} {r['cls'][:23]:<23} {r['dir'][:5]:<5} {r['pnl']:>+8.2f}  {r['why'][:60]}")

    _dump("REJECTED WINNERS — what the playbook would have cost", misses)
    _dump("APPROVED LOSERS — what it would not have stopped", leaks)

    # Which rule does the rejecting? (reason string prefix up to ':' or first 40 chars)
    from collections import Counter as _C
    by_rule = _C((r["why"].split(":")[0] if ":" in r["why"] else r["why"][:40]) for r in misses)
    if by_rule:
        print("\nRejected winners by rule:")
        for k, v in by_rule.most_common():
            print(f"  {v:>3}  {k}")
    by_rule_l = _C((r["why"].split(":")[0] if ":" in r["why"] else r["why"][:40]) for r in rej_losers_rows)
    if by_rule_l:
        print("\nRejected losers by rule (what each rule SAVES):")
        for k, v in by_rule_l.most_common():
            saved = -sum(r["pnl"] for r in rej_losers_rows
                         if (r["why"].split(":")[0] if ":" in r["why"] else r["why"][:40]) == k)
            print(f"  {v:>3}  {k:<42} saves ${saved:+.2f}")
    if kinds_advisory or phase_d_as_c or phase_b_both or with_bias_any_kind or drive_fail_flip:
        print(f"\nLAB VARIANT: phase_d_as_c={phase_d_as_c} phase_b_both={phase_b_both} "
              f"kinds_advisory={kinds_advisory} with_bias_any_kind={with_bias_any_kind} "
              f"drive_fail_flip={drive_fail_flip} (kind overridden {kind_would_block}, drive flips {drive_flips})")

    print(f"\n{'='*70}")
    print(f"Sessions: {len(sessions)} | broker-priced trades: {total_n} | excluded (no broker price): {unpriced_n}")
    print(f"Approved: {approved_n} | Rejected: {rejected_n}")
    print(f"Approved Σ$ (broker): ${approved_sum:+.2f}    Actual Σ$ (broker): ${actual_sum:+.2f}    (gate: approved > -313.75)")
    print(f"Winners approved : {approved_winners}/{winners} = {win_recall:.0f}%   (gate ≥75%)")
    print(f"Losers rejected  : {rejected_losers}/{losers} = {loss_recall:.0f}%   (gate ≥60%)")
    print(f"n approved       : {approved_n}   (gate ≥40)")
    gates = [win_recall >= 75.0, loss_recall >= 60.0, approved_sum > -313.75, approved_n >= 40]
    print(f"GATE: {'PASS' if all(gates) else 'FAIL'}  [{'/'.join('ok' if g else 'X' for g in gates)}]")


if __name__ == "__main__":
    main()
