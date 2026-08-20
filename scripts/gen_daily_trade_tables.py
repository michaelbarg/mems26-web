#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate per-day trade tables for every live session.

Produces one markdown file per session in docs/reports/DAILY_TRADE_TABLES/,
each in the TODAY_TRADER_TABLE format:
  - Day shape (IB, extremes, day-type live vs post-hoc)
  - Trade table (causal triggers, entry/stop/targets, $4c/$6c, system comparison)
  - Summary

Mechanics engine imported from oracle_study.py (same thresholds, costs, slippage).
READ-ONLY — writes nothing to DB.

Usage: python3 scripts/gen_daily_trade_tables.py [--date 2026-08-20] [--all]
"""

import argparse
import collections
import datetime as dt
import os
import sys
import statistics

import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import importlib.util as _ilu
_OS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oracle_study.py")
_spec = _ilu.spec_from_file_location("oracle_study", _OS_PATH)
ORA = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(ORA)

DSN = os.environ.get("MEMS26_DSN", "postgresql://localhost/mems26")
D_LIVE0 = "2026-07-07"
RTH0, RTH1 = dt.time(9, 30), dt.time(16, 0)
IB_BARS = 12
CONTRACTS_4 = 4
CONTRACTS_6 = 6
POINT_USD = ORA.POINT_USD
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "docs", "reports", "DAILY_TRADE_TABLES")


def load_trades_for_day(cur, day):
    cur.execute("""
        SELECT id, pattern_id_at_entry, firing_system, direction, mode,
               to_char(entry_ts AT TIME ZONE 'America/New_York', 'HH24:MI') AS t_in,
               to_char(exit_ts AT TIME ZONE 'America/New_York', 'HH24:MI') AS t_out,
               entry_price, exit_price, stop, t1, t2, t3, pnl_usd, outcome,
               exit_reason, day_type_at_entry
        FROM v9_trades
        WHERE state = 'CLOSED'
          AND (entry_ts AT TIME ZONE 'America/New_York')::date = %s
        ORDER BY entry_ts
    """, (str(day),))
    return [dict(r) for r in cur.fetchall()]


def load_daytype_history(cur, day):
    cur.execute("""
        SELECT day_type, ib_high, ib_low, opening_type, confidence
        FROM v9_day_type_history WHERE date = %s LIMIT 1
    """, (str(day),))
    row = cur.fetchone()
    if row:
        return dict(day_type=row["day_type"],
                    ib_high=float(row["ib_high"]) if row.get("ib_high") else None,
                    ib_low=float(row["ib_low"]) if row.get("ib_low") else None,
                    opening_type=row.get("opening_type"),
                    confidence=float(row["confidence"]) if row.get("confidence") else None)
    return None


def compute_ib(bars):
    ib = bars[:IB_BARS] if len(bars) >= IB_BARS else bars
    return max(b["h"] for b in ib), min(b["l"] for b in ib)


def classify_posthoc(bars):
    """Run the 7-type classifier on the full session (post-hoc)."""
    try:
        from backend.v9.systems.day_type.classifier_core import classify_session
        result = classify_session(bars, is_eod=True)
        return result.get("day_type", "?") if isinstance(result, dict) else str(result)
    except Exception:
        return "?"


def usd_4c(pts):
    return round(pts * CONTRACTS_4 * POINT_USD - ORA.costs(CONTRACTS_4), 2)


def usd_6c(pts):
    return round(pts * CONTRACTS_6 * POINT_USD - ORA.costs(CONTRACTS_6), 2)


def generate_day_table(cur, day, all_bars_dict):
    bars = all_bars_dict.get(day, [])
    if len(bars) < 20:
        return None

    trades = load_trades_for_day(cur, day)
    dth = load_daytype_history(cur, day)
    thr = ORA.thr_for(all_bars_dict, day)

    # IB
    ibh, ibl = compute_ib(bars)
    ib_width = round(ibh - ibl, 2)

    # RTH extremes
    rth_high = max(b["h"] for b in bars)
    rth_low = min(b["l"] for b in bars)
    rth_range = round(rth_high - rth_low, 2)

    # Find when extremes formed
    hi_bar = next(b for b in bars if b["h"] == rth_high)
    lo_bar = next(b for b in bars if b["l"] == rth_low)
    hi_time = hi_bar["t"].strftime("%H:%M")
    lo_time = lo_bar["t"].strftime("%H:%M")

    # IB breaks
    ib_high_break = ib_low_break = None
    for b in bars[IB_BARS:]:
        if ib_high_break is None and b["h"] > ibh:
            ib_high_break = b["t"].strftime("%H:%M")
        if ib_low_break is None and b["l"] < ibl:
            ib_low_break = b["t"].strftime("%H:%M")

    # Day type
    live_dt = dth["day_type"] if dth else "?"
    posthoc_dt = classify_posthoc(bars)

    # Swing triggers
    piv = ORA.zigzag(bars, thr)
    trigs = ORA.find_triggers(bars, piv, thr)

    # Causal sequence (all triggers, one at a time)
    causal_all = ORA.causal_sequence(bars, trigs, thr, mode="trail")
    causal_ladder = ORA.causal_sequence(bars, trigs, thr, mode="ladder")

    # System trades
    live_trades = [t for t in trades if t["mode"] == "live"]
    shadow_trades = [t for t in trades if t["mode"] == "shadow"]
    live_pnl = sum(float(t["pnl_usd"] or 0) for t in live_trades)

    # Build markdown
    lines = []
    lines.append(f"# {day} · טבלת-הסוחר")
    lines.append("")
    lines.append(f"**Trail threshold:** {thr:.2f}pt (1×ATR prev session)")
    lines.append(f"**Contracts:** 4c ($5/pt, $1.50 RT, 1 tick slip/side)")
    lines.append("")

    # §0 Day shape
    lines.append("## צורת-היום")
    lines.append("")
    lines.append("```")
    lines.append(f"IB (09:30-10:30 ET)   {ibl:.2f} - {ibh:.2f}   width {ib_width}pt")
    lines.append(f"RTH                   {rth_low:.2f} - {rth_high:.2f}   range {rth_range}pt")
    lines.append(f"High @ {hi_time} ET   Low @ {lo_time} ET")
    if ib_high_break:
        lines.append(f"IB-HIGH break         {ib_high_break} ET")
    if ib_low_break:
        lines.append(f"IB-LOW break          {ib_low_break} ET")
    lines.append("```")
    lines.append("")
    lines.append(f"**Day-type live:** {live_dt}" +
                 (f" (conf {dth['confidence']:.2f})" if dth and dth.get("confidence") else ""))
    lines.append(f"**Day-type post-hoc:** {posthoc_dt}")
    if live_dt != posthoc_dt and posthoc_dt != "?":
        lines.append(f"**MISMATCH** — live said {live_dt}, post-hoc says {posthoc_dt}")
    lines.append("")

    # §1 Causal trade table
    lines.append("## עסקאות-מכניקה (causal, no hindsight)")
    lines.append("")
    if causal_all:
        lines.append("| # | שעה ET | כיוון | טריגר | כניסה | סטופ | R (pts) | יציאה | סיבה | נק' | $4c | $6c |")
        lines.append("|---|--------|-------|-------|-------|------|---------|-------|------|-----|-----|-----|")
        total_4 = total_6 = 0.0
        for idx, t in enumerate(causal_all, 1):
            d_str = "LONG" if t["dir"] > 0 else "SHORT"
            t_in = t["t_in"].strftime("%H:%M") if hasattr(t["t_in"], "strftime") else str(t["t_in"])
            u4 = usd_4c(t["pts"])
            u6 = usd_6c(t["pts"])
            total_4 += u4
            total_6 += u6
            lines.append(f"| {idx} | {t_in} | {d_str} | {t.get('kind', '?')} | "
                         f"{t['entry']:.2f} | {t['stop']:.2f} | {t['risk']:.1f} | "
                         f"{t['exit']:.2f} | {t['reason']} | {t['pts']:.1f} | "
                         f"${u4:+.0f} | ${u6:+.0f} |")
        lines.append(f"| | | | | | | | | **NET** | | **${total_4:+.0f}** | **${total_6:+.0f}** |")
    else:
        lines.append("*No causal triggers fired.*")
    lines.append("")

    # §2 System comparison
    lines.append("## מה המערכת עשתה בפועל")
    lines.append("")
    if live_trades:
        lines.append("| id | שעה | כיוון | תבנית | כניסה | סטופ | יציאה | $ | תוצאה |")
        lines.append("|---|------|-------|-------|-------|------|-------|---|-------|")
        for t in live_trades:
            lines.append(f"| {t['id']} | {t['t_in']} | {t['direction']} | "
                         f"{t['pattern_id_at_entry'] or '?'} | "
                         f"{t['entry_price']} | {t['stop']} | "
                         f"{t['t_out'] or 'open'} {t['exit_reason'] or ''} | "
                         f"${float(t['pnl_usd'] or 0):+.0f} | {t['outcome']} |")
        lines.append(f"| | | | | | | **NET** | **${live_pnl:+.0f}** | |")
    else:
        lines.append("*No live trades.*")
    lines.append("")

    if shadow_trades:
        lines.append(f"Shadow trades: {len(shadow_trades)} "
                     f"(net ${sum(float(t['pnl_usd'] or 0) for t in shadow_trades):+.0f})")
        lines.append("")

    # §3 Gap
    causal_pnl_4 = sum(usd_4c(t["pts"]) for t in causal_all) if causal_all else 0
    gap = causal_pnl_4 - live_pnl
    lines.append("## סיכום")
    lines.append("")
    lines.append(f"| | 4c | 6c |")
    lines.append(f"|---|---|---|")
    lines.append(f"| מכניקה-סיבתית (all triggers) | ${causal_pnl_4:+.0f} | "
                 f"${sum(usd_6c(t['pts']) for t in causal_all) if causal_all else 0:+.0f} |")
    ladder_pnl = sum(t["usd"] for t in causal_ladder) if causal_ladder else 0
    lines.append(f"| מכניקה-סולם (ladder) | ${ladder_pnl:+.0f} | |")
    lines.append(f"| מערכת-לייב | ${live_pnl:+.0f} | |")
    lines.append(f"| **פער** | **${gap:+.0f}** | |")
    lines.append("")

    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--date", help="Single date YYYY-MM-DD")
    p.add_argument("--all", action="store_true", help="All live sessions")
    p.add_argument("--from-date", default=D_LIVE0)
    p.add_argument("--to-date", default="2026-08-20")
    a = p.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    dict_cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Load all bars
    print("Loading bars...")
    cur.execute("""
        SELECT (ts AT TIME ZONE 'America/New_York') AS et,
               open, high, low, close, volume
        FROM v9_bars_5min_woodies
        WHERE (ts AT TIME ZONE 'America/New_York')::date BETWEEN %s AND %s
          AND (ts AT TIME ZONE 'America/New_York')::time >= %s
          AND (ts AT TIME ZONE 'America/New_York')::time < %s
        ORDER BY ts
    """, ("2026-06-01", a.to_date, RTH0, RTH1))
    all_bars = collections.OrderedDict()
    for et, o, h, l, c, v in cur.fetchall():
        all_bars.setdefault(et.date(), []).append(
            dict(t=et, o=float(o), h=float(h), l=float(l), c=float(c), v=float(v or 0)))
    print(f"  {len(all_bars)} sessions loaded")

    if a.date:
        dates = [dt.date.fromisoformat(a.date)]
    elif a.all:
        dates = [d for d in all_bars if d >= dt.date.fromisoformat(a.from_date)]
    else:
        dates = [d for d in all_bars if d >= dt.date.fromisoformat(a.from_date)]

    generated = 0
    for day in dates:
        md = generate_day_table(dict_cur, day, all_bars)
        if md is None:
            continue
        path = os.path.join(OUT_DIR, f"TRADE_TABLE_{day}.md")
        with open(path, "w") as f:
            f.write(md)
        generated += 1
        # Quick summary
        lines = md.split("\n")
        net_line = [l for l in lines if "NET" in l and "$" in l]
        net_str = net_line[0] if net_line else ""
        print(f"  {day} → {os.path.basename(path)}  {net_str[:60]}")

    print(f"\n{generated} tables written to {OUT_DIR}/")
    conn.close()


if __name__ == "__main__":
    main()
