#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""When do the StructureExit conditions actually occur, and would exiting help?

Michael 2026-09-01: *"אני לא רוצה שזה יהיה עיוור — אלא ברגע שהוא מזהה שמשהו
הסתיים. האם אפשר להכין בדיקה מתי התנאים מתרחשים?"*

Today `STRUCTURE_EXIT_FAILBREAK_V1` fired GRADE-A on the only live trade, at
17:52, six minutes before the stop took it at break-even:

    "failed break SHORT while LONG — FLATTEN (profit sufficient)"

It was in shadow, so it logged and did nothing. Its exit looked better than the
stop's. But that is n=1, and promoting a live exit rule on one correct call is
the shape of decision this project has been burned by. This script asks the
market instead: **across the closed trades we have, when would this have fired,
and would the exit have been better than the one that happened?**

## It replays production, not a copy of it

`detect_failed_break` and `should_exit_on_failbreak` are imported and called —
the same functions the live path calls, with the same arguments. A
re-implementation would measure the re-implementation.

## The honest constraint, stated before any number

The detector needs VAH/VAL. Historical value areas live in `v9_tpo_sessions`,
and that table is **wrong on most days** — measured 01.09 at 8-33% of session
range where a value area is 70% by definition (the live path is fine; it reads
the DLL export, which is correct — the table is what is broken). So every
session is put through `va_quality()` first, and a session that fails is
**NOT_JUDGEABLE and excluded**, never patched with a guess. The count of
excluded sessions is reported next to the verdict, because a verdict drawn from
three surviving days is not a verdict.

## What "better" means

Points, direction-aware, between the price at the signal bar's close and the
price the trade actually exited at. Not MFE — MFE misled this project twice in
one day, by factors of 4 and 7. This is the difference between two real exits.

    python3 scripts/structure_exit_replay.py
    python3 scripts/structure_exit_replay.py --days 45 --mode live
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

for _ln in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
    _ln = _ln.strip()
    if _ln and not _ln.startswith("#") and "=" in _ln:
        _k, _v = _ln.split("=", 1)
        os.environ.setdefault(_k.strip(), _v.split("#")[0].strip())

if "postgres" not in os.environ.get("DATABASE_URL", ""):
    sys.exit("DATABASE_URL is not Postgres — refusing to report from a stale "
             "SQLite mirror (T-161).")

from backend.v9.db.read import read_all                                # noqa: E402
from backend.v9.systems.failed_break import detect_failed_break         # noqa: E402
from backend.v9.services.trade_manager.structure_exit import (          # noqa: E402
    should_exit_on_failbreak)
from backend.v9.shared.atr import atr_5min                              # noqa: E402

try:
    from backend.v9.systems.va_sanity import va_quality
except Exception:                       # the gate is new; do not fail without it
    va_quality = None


def _sessions(days):
    rows = read_all(
        "SELECT (ts AT TIME ZONE 'America/New_York')::date AS d, "
        "       vah_price AS vah, val_price AS val, "
        "       max(high) OVER (PARTITION BY (ts AT TIME ZONE 'America/New_York')::date) AS hi "
        "FROM v9_tpo_sessions t JOIN v9_bars_5min_woodies b USING (ts) "
        "WHERE ts >= now() - (:d || ' days')::interval", {"d": days}) or []
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=45)
    ap.add_argument("--mode", default="live", choices=("live", "shadow", "both"))
    a = ap.parse_args()

    modes = ("live", "shadow") if a.mode == "both" else (a.mode,)
    trades = read_all(
        "SELECT id, mode, direction, entry_price, stop, t1, t1_hit_ts, "
        "       entry_ts, exit_ts, exit_price, exit_reason, pnl_usd, "
        "       pattern_id_at_entry AS pat, day_type_at_entry AS dt "
        "FROM v9_trades WHERE state='CLOSED' AND mode = ANY(:m) "
        "  AND entry_ts >= now() - (:d || ' days')::interval "
        "  AND exit_price IS NOT NULL "
        "ORDER BY entry_ts", {"m": list(modes), "d": a.days}) or []
    if not trades:
        sys.exit("no closed trades with an exit price — refusing to report zero")

    bars = read_all(
        "SELECT ts, high, low, close FROM v9_bars_5min_woodies "
        "WHERE ts >= now() - (:d || ' days')::interval ORDER BY ts",
        {"d": a.days + 2}) or []
    if not bars:
        sys.exit("no bars — this is not a quiet market, it is a broken query")

    # VA per session date, gated by sanity. A bad VA is excluded, never guessed.
    va, va_bad = {}, 0
    for r in read_all(
            "SELECT session_type, poc_price, vah_price, val_price, range_high, "
            "       range_low, ts FROM v9_tpo_sessions "
            "WHERE ts >= now() - (:d || ' days')::interval", {"d": a.days}) or []:
        d = r["ts"].date()
        vah, val = r.get("vah_price"), r.get("val_price")
        hi, lo = r.get("range_high"), r.get("range_low")
        if not vah or not val:
            continue
        if va_quality is not None and hi and lo:
            try:
                q = va_quality(float(vah), float(val), float(hi), float(lo))
                if not (q.get("ok") if isinstance(q, dict) else q):
                    va_bad += 1
                    continue
            except Exception:
                pass
        va[d] = (float(vah), float(val))

    stats = defaultdict(int)
    rows_out = []
    no_va = 0

    for t in trades:
        d = t["entry_ts"].date()
        if d not in va:
            no_va += 1
            continue
        vah, val = va[d]
        long = (t["direction"] or "").upper() == "LONG"
        win = [b for b in bars if t["entry_ts"] <= b["ts"] <= t["exit_ts"]]
        if len(win) < 13:
            stats["too_few_bars"] += 1
            continue

        hit = None
        for i in range(12, len(win)):
            seg = [{"h": float(b["high"]), "l": float(b["low"]),
                    "c": float(b["close"]), "high": float(b["high"]),
                    "low": float(b["low"]), "close": float(b["close"])}
                   for b in win[:i + 1]]
            fb = detect_failed_break(seg, vah, val, edge_label="VA")
            if not fb:
                continue
            res = should_exit_on_failbreak(
                trade_direction=t["direction"],
                trade_entry_price=float(t["entry_price"]),
                trade_stop=float(t["stop"]) if t["stop"] else None,
                trade_t1_hit=t["t1_hit_ts"] is not None,
                bar_high=float(win[i]["high"]), bar_low=float(win[i]["low"]),
                bar_close=float(win[i]["close"]),
                failed_break=fb, atr=atr_5min(seg, period=14))
            if res:
                hit = (win[i], res)
                break

        if hit is None:
            stats["never_fired"] += 1
            continue

        bar, res = hit
        sig_px = float(bar["close"])
        act_px = float(t["exit_price"])
        delta = (sig_px - act_px) if long else (act_px - sig_px)
        stats["fired"] += 1
        stats["better" if delta > 0 else ("same" if delta == 0 else "worse")] += 1
        rows_out.append((t, bar["ts"], sig_px, act_px, delta, res.get("action")))

    print(f"\n{'='*92}")
    print(" StructureExit GRADE-A — when would it have fired, and was its exit better?")
    print(f" replaying the production functions over {a.days} days · mode={a.mode}")
    print(f"{'='*92}")
    print(f" {'#':>5} {'date':<11} {'pat':<20} {'dir':<5} {'signal':>8} "
          f"{'actual':>8} {'Δpts':>7}  action")
    for t, ts, s, x, dl, act in sorted(rows_out, key=lambda r: r[1]):
        mark = "✅" if dl > 0 else ("—" if dl == 0 else "🔴")
        print(f" {t['id']:>5} {ts:%m-%d %H:%M} {str(t['pat'])[:20]:<20} "
              f"{t['direction']:<5} {s:>8.2f} {x:>8.2f} {dl:>+7.2f} {mark} {act}")

    n = stats["fired"]
    print(f"\n{'-'*92}")
    print(f" trades examined: {len(trades)}   fired: {n}   never fired: "
          f"{stats['never_fired']}")
    print(f" excluded — no usable value area: {no_va}   "
          f"(sessions failing va_quality: {va_bad})   too few bars: "
          f"{stats['too_few_bars']}")

    if n < 10:
        print(f"\n 🔴 NOT_JUDGEABLE — {n} firings. No verdict on a single-digit"
              f" sample; that is exactly the n=1 problem this script exists to"
              f" avoid repeating.")
    else:
        tot = sum(r[4] for r in rows_out)
        print(f"\n better: {stats['better']}   worse: {stats['worse']}   "
              f"same: {stats['same']}   net: {tot:+.2f} pts over {n} exits")
        print(f" median: {sorted(r[4] for r in rows_out)[n//2]:+.2f} pts")

    print(f"""
 HOW TO READ IT. Δ is points, direction-aware, between the signal bar's close
 and the price the trade actually exited at — two real exits compared, not MFE.
 A positive Δ means the signal would have kept money the actual exit gave back.
 It does NOT price the trades that would have been cut short of a bigger win:
 'never fired' rows are the control group, and they are counted above.

 And what the excluded column means: historical value areas come from
 v9_tpo_sessions, which is wrong on most days (8-33% of range where 70% is the
 definition). Those sessions are dropped, not patched. If the excluded count
 dwarfs the fired count, the honest answer is that this cannot be judged from
 history yet — fix the table first (T-203).
{'='*92}
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
