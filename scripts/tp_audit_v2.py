#!/usr/bin/env python3
"""TP audit v2 — target placement analysis (30 days) via direct psql.

Methodology: docs/handoff/RESEARCH_PROMPT_TP_AUDIT_2026-07-08.md
Output: docs/reports/TP_AUDIT_<date>.md — report only, zero code changes.

Data sources (local Postgres, DATABASE_URL=postgresql://localhost/mems26):
  - v9_trades: all trades (shadow/demo/live), pattern, day_type, entry/stop/t1/t2/t3, hits
  - v9_bars_5min_woodies: canonical 5-min bars for MFE/MAE calculation
"""
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta

# Postgres path
PG_BIN = "/Applications/Postgres.app/Contents/Versions/18/bin"
os.environ["PATH"] = PG_BIN + ":" + os.environ.get("PATH", "")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

MES_POINT_VALUE = 5.0


def _db_query(sql, params=None):
    """Query local Postgres via the backend's read helper."""
    from backend.v9.db.read import read_all
    return read_all(sql, params or {}) or []


def main():
    today = date.today()
    since = today - timedelta(days=30)

    # Fetch trades (30 days)
    trades = _db_query(
        """SELECT id, mode, direction, entry_price, stop, t1, t2, t3,
                  t1_hit_ts, t2_hit_ts, t3_hit_ts, stop_hit_ts,
                  exit_price, pnl_usd, outcome, quality,
                  entry_ts, day_type_at_entry, pattern_id_at_entry
           FROM v9_trades
           WHERE entry_ts >= :since AND is_synthetic = 0
           ORDER BY entry_ts""",
        {"since": since.isoformat()})

    # Fetch bars (30 days) — indexed by date for MFE lookup
    bars = _db_query(
        """SELECT ts, high, low, close
           FROM v9_bars_5min_woodies
           WHERE ts >= :since
           ORDER BY ts""",
        {"since": since.isoformat()})

    # Index bars by trading date (ET)
    by_day = defaultdict(list)
    for b in bars:
        ts = b.get("ts")
        if ts is None:
            continue
        if isinstance(ts, datetime):
            d = ts.date().isoformat()
        else:
            d = str(ts)[:10]
        by_day[d].append(b)

    def mfe_mae(trade_date, entry_ts, entry, direction):
        """Compute MFE and MAE from bars after entry on the same day."""
        day_bars = by_day.get(trade_date, [])
        if not day_bars or entry is None:
            return None, None
        # Filter bars after entry
        after = []
        for b in day_bars:
            bts = b.get("ts")
            if bts is None:
                continue
            if isinstance(bts, datetime):
                if entry_ts and isinstance(entry_ts, datetime) and bts < entry_ts:
                    continue
            after.append(b)
        if not after:
            return None, None
        highs = [float(b["high"]) for b in after]
        lows = [float(b["low"]) for b in after]
        if direction == "LONG":
            return max(highs) - entry, entry - min(lows)
        else:
            return entry - min(lows), max(highs) - entry

    # Aggregate per pattern × day_type
    agg = defaultdict(lambda: {
        "n": 0, "t1_dists": [], "mfes": [], "maes": [],
        "t1_hits": 0, "t2_hits": 0, "t3_hits": 0, "stop_hits": 0,
        "pnls": [], "modes": defaultdict(int),
    })
    skipped = 0

    for t in trades:
        entry = t.get("entry_price")
        t1 = t.get("t1")
        if not entry or not t1:
            skipped += 1
            continue
        entry_f = float(entry)
        t1_f = float(t1)
        direction = t.get("direction", "LONG")
        ets = t.get("entry_ts")
        if ets is None:
            skipped += 1
            continue
        trade_date = ets.date().isoformat() if isinstance(ets, datetime) else str(ets)[:10]

        q = t.get("quality") if isinstance(t.get("quality"), dict) else {}
        pattern = (t.get("pattern_id_at_entry")
                   or q.get("classification")
                   or q.get("trigger")
                   or f"S{t.get('firing_system', '?')}")
        day_type = t.get("day_type_at_entry") or "UNKNOWN"

        mfe, mae = mfe_mae(trade_date, ets, entry_f, direction)
        if mfe is None:
            skipped += 1
            continue

        key = (str(pattern)[:20], day_type)
        a = agg[key]
        a["n"] += 1
        a["modes"][t.get("mode", "?")] += 1

        if direction == "LONG":
            a["t1_dists"].append(t1_f - entry_f)
        else:
            a["t1_dists"].append(entry_f - t1_f)
        a["mfes"].append(mfe)
        a["maes"].append(mae)
        if t.get("t1_hit_ts"):
            a["t1_hits"] += 1
        if t.get("t2_hit_ts"):
            a["t2_hits"] += 1
        if t.get("t3_hit_ts"):
            a["t3_hits"] += 1
        if t.get("stop_hit_ts"):
            a["stop_hits"] += 1
        pnl = t.get("pnl_usd")
        if pnl is not None:
            a["pnls"].append(float(pnl))

    def med(xs):
        s = sorted(xs)
        return s[len(s) // 2] if s else 0.0

    def p25(xs):
        s = sorted(xs)
        return s[max(0, len(s) // 4 - 1)] if s else 0.0

    def p75(xs):
        s = sorted(xs)
        return s[min(len(s) - 1, 3 * len(s) // 4)] if s else 0.0

    total_trades = sum(a["n"] for a in agg.values())

    lines = [
        f"# TP Audit v2 · {today.isoformat()}",
        "",
        f"**מקור:** psql ישיר (v9_trades + v9_bars_5min_woodies, 30 יום מ-{since})",
        f"**מדגם:** {total_trades} עסקאות · דולגו: {skipped}",
        "",
        "## סיכום פר תבנית × סוג-יום",
        "",
        "| תבנית | סוג-יום | n | T1 חציוני | MFE p25/p50/p75 | T1/MFE | T1 hit% | סטופ% | דגל |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    flags = []

    for (pat, dt), a in sorted(agg.items(), key=lambda kv: -kv[1]["n"]):
        t1m = med(a["t1_dists"])
        mfe_25, mfe_50, mfe_75 = p25(a["mfes"]), med(a["mfes"]), p75(a["mfes"])
        ratio = (t1m / mfe_50) if mfe_50 > 0 else float("inf")
        hr = a["t1_hits"] / a["n"] if a["n"] else 0
        sr = a["stop_hits"] / a["n"] if a["n"] else 0
        flag = ""

        if a["n"] >= 3:
            if t1m <= 0:
                flag = "🔴 T1 wrong side"
                flags.append(f"{pat}×{dt}: T1 dist = {t1m:.1f} (wrong side of entry)")
            elif ratio > 1.5:
                flag = "🔴 T1 רחוק"
                flags.append(f"{pat}×{dt}: T1 {t1m:.1f} vs MFE {mfe_50:.1f} (ratio {ratio:.1f}) — target too far")
            elif hr < 0.3:
                flag = "🔴 hit-rate נמוך"
                flags.append(f"{pat}×{dt}: hit-rate {hr:.0%} ({a['t1_hits']}/{a['n']}) — consider closer T1")
            elif ratio < 0.35 and hr > 0.7:
                flag = "🟡 T1 קרוב"
                flags.append(f"{pat}×{dt}: T1 captures only {ratio:.0%} of MFE {mfe_50:.1f}")

        lines.append(
            f"| {pat} | {dt} | {a['n']} | {t1m:.1f} | "
            f"{mfe_25:.1f}/{mfe_50:.1f}/{mfe_75:.1f} | "
            f"{'∞' if ratio == float('inf') else f'{ratio:.2f}'} | "
            f"{hr:.0%} | {sr:.0%} | {flag} |"
        )

    lines += ["", "## תאי-הפסד מועמדים", ""]
    if flags:
        lines += [f"- {f}" for f in flags]
    else:
        lines += ["- אין תאים מובהקים במדגם."]

    lines += [
        "", "## MFE גלובלי פר סוג-יום", "",
        "| סוג-יום | n | MFE חציוני | MFE p75 |",
        "|---|---|---|---|",
    ]
    dt_agg = defaultdict(list)
    for (_, dt), a in agg.items():
        dt_agg[dt].extend(a["mfes"])
    for dt, mfes in sorted(dt_agg.items(), key=lambda kv: -len(kv[1])):
        lines.append(f"| {dt} | {len(mfes)} | {med(mfes):.1f} | {p75(mfes):.1f} |")

    lines += [
        "",
        f"_v2 — psql direct, 30 days. L6 sensitivity (P&L from bar not fill) in effect._",
        "_Zero changes made. Recommendations = Michael ruling only._",
    ]

    out_path = os.path.join(ROOT, "docs", "reports", f"TP_AUDIT_{today.isoformat()}.md")
    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Written: {out_path}")
    print(f"Trades: {total_trades}, skipped: {skipped}, cells: {len(agg)}")


if __name__ == "__main__":
    main()
