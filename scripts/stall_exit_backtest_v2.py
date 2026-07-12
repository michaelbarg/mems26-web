#!/usr/bin/env python3
"""STALL_EXIT v2 backtest — drawdown-gated (Cowork, 2026-07-12). Research only.

v1 result (CC 07-11): 7 improved / 15 hurt — the naive stall-exit cuts WINNERS
that pause near highs and then continue. v2 adds the missing condition:

  Exit fires only when the runner is GIVING BACK — price has retraced at least
  DD_FRAC of the post-T1 leg from its MFE — AND a stall near the extreme was
  seen first. A runner pressing its highs is never touched.

Grid over DD_FRAC ∈ {0.3, 0.4, 0.5}; same data as v1 for apples-to-apples.
Output: docs/reports/STALL_EXIT_BACKTEST_V2_2026-07-12.md
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.v9.db.read import read_all

TICK = 0.25
STALL_RANGE_PTS = 3.0
STALL_BARS = 3
NEAR_EXTREME_PTS = 4.0
DD_GRID = (0.3, 0.4, 0.5)


def saw_stall_near_extreme(post_bars, i_end, direction):
    """Was there a v1-style stall window anywhere up to bar i_end?"""
    for i in range(max(0, i_end - 40), i_end - STALL_BARS + 2):
        window = post_bars[i:i + STALL_BARS]
        if len(window) < STALL_BARS:
            break
        highs = [float(b["high"]) for b in window]
        lows = [float(b["low"]) for b in window]
        if max(highs) - min(lows) > STALL_RANGE_PTS:
            continue
        upto = post_bars[:i + STALL_BARS]
        mid = (max(highs) + min(lows)) / 2
        if direction == "LONG":
            best = max(float(b["high"]) for b in upto)
            if best - mid <= NEAR_EXTREME_PTS:
                return True
        else:
            best = min(float(b["low"]) for b in upto)
            if mid - best <= NEAR_EXTREME_PTS:
                return True
    return False


def simulate_v2(bars, direction, t1_idx, entry, dd_frac):
    """Exit when: stall-near-extreme happened AND close retraces >= dd_frac of
    the post-T1 leg from MFE. Returns exit price or None (never fired)."""
    post = bars[t1_idx + 1:]
    if not post:
        return None
    long = direction == "LONG"
    mfe = float(post[0]["high"]) if long else float(post[0]["low"])
    for i, b in enumerate(post):
        h, l, c = float(b["high"]), float(b["low"]), float(b["close"])
        mfe = max(mfe, h) if long else min(mfe, l)
        leg = (mfe - entry) if long else (entry - mfe)
        if leg <= 0.5:
            continue
        retrace = (mfe - c) if long else (c - mfe)
        if retrace >= dd_frac * leg and saw_stall_near_extreme(post, i, direction):
            return c
    return None


def main():
    trades = read_all("""
        SELECT id, direction, entry_price, t1, entry_ts, pnl_usd,
               firing_system, day_type_at_entry, pattern_id_at_entry
        FROM v9_trades
        WHERE entry_ts IS NOT NULL AND outcome IS NOT NULL
        ORDER BY entry_ts
    """)
    grid_stats = {dd: {"improved": 0, "hurt": 0, "neutral": 0, "net": 0.0, "rows": []}
                  for dd in DD_GRID}
    considered = 0

    for t in trades:
        entry = float(t["entry_price"]) if t["entry_price"] else None
        t1 = float(t["t1"]) if t.get("t1") else None
        direction = str(t.get("direction", "")).upper()
        entry_ts = str(t.get("entry_ts", ""))
        pnl = float(t.get("pnl_usd", 0) or 0)
        if not entry or not t1 or len(entry_ts) < 16:
            continue
        day = entry_ts[:10]
        bars = read_all("""
            SELECT ts, high, low, close FROM v9_bars_5min_woodies
            WHERE ts::date = :day ORDER BY ts
        """, {"day": day})
        if len(bars) < 10:
            continue
        entry_time = entry_ts[11:16]
        entry_idx = next((bi for bi, b in enumerate(bars)
                          if str(b["ts"])[11:16] >= entry_time), None)
        if entry_idx is None:
            continue
        t1_idx = None
        for bi in range(entry_idx, len(bars)):
            h, l = float(bars[bi]["high"]), float(bars[bi]["low"])
            if (direction == "LONG" and h >= t1) or (direction == "SHORT" and l <= t1):
                t1_idx = bi
                break
        if t1_idx is None:
            continue
        considered += 1

        for dd in DD_GRID:
            px = simulate_v2(bars, direction, t1_idx, entry, dd)
            if px is None:
                continue  # v2 never fired → actual outcome stands (0 delta, not counted)
            sim_pnl = (px - entry) * 5.0 if direction == "LONG" else (entry - px) * 5.0
            delta = sim_pnl - pnl
            g = grid_stats[dd]
            g["net"] += delta
            if delta > 1.0:
                g["improved"] += 1
                label = "IMPROVED"
            elif delta < -1.0:
                g["hurt"] += 1
                label = "HURT"
            else:
                g["neutral"] += 1
                label = "NEUTRAL"
            g["rows"].append((t["id"], day, direction, pnl, sim_pnl, delta, label))

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(repo, "docs", "reports", "STALL_EXIT_BACKTEST_V2_2026-07-12.md")
    lines = [
        "# STALL_EXIT v2 — drawdown-gated backtest (2026-07-12)",
        "",
        f"בסיס: אותם נתונים כמו v1 (‏{considered} ראנרים עם T1). ‏v1 = ‏7:15 נגד. "
        "‏v2 יורה רק כשהראנר מחזיר ≥DD מהרגל אחרי-שראינו-סטול ליד הקיצון —",
        "ראנר שלוחץ על השיאים לא נגוע.",
        "",
        "| DD gate | fired | improved | hurt | neutral | Σ delta |",
        "|---------|-------|----------|------|---------|---------|",
    ]
    for dd in DD_GRID:
        g = grid_stats[dd]
        fired = g["improved"] + g["hurt"] + g["neutral"]
        lines.append(f"| {int(dd*100)}% | {fired} | {g['improved']} | {g['hurt']} "
                     f"| {g['neutral']} | ${g['net']:+.2f} |")
    best = max(DD_GRID, key=lambda d: grid_stats[d]["net"])
    lines += ["", f"**המועמד הטוב ביותר: DD={int(best*100)}%** "
              f"(Σ ${grid_stats[best]['net']:+.2f}, "
              f"{grid_stats[best]['improved']}:{grid_stats[best]['hurt']}).", "",
              f"## פירוט DD={int(best*100)}%", "",
              "| ID | Date | Dir | Actual | v2 Exit PnL | Δ | Verdict |",
              "|----|------|-----|--------|-------------|---|---------|"]
    for r in sorted(grid_stats[best]["rows"], key=lambda x: -abs(x[5])):
        lines.append(f"| {r[0]} | {r[1]} | {r[2]} | ${r[3]:.2f} | ${r[4]:.2f} "
                     f"| ${r[5]:+.2f} | {r[6]} |")
    lines += ["", "---", "*Research only — אין קוד חי בלי פסיקת מייקל.*"]
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines[:14]))
    print(f"\nReport: {path}")


if __name__ == "__main__":
    main()
