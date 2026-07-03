#!/usr/bin/env python3
"""Item-4 backtest — old stop vs STOP_RESOLVER_V1 structural stop, per pattern.

REQUIRED-before-enable gate (CC NOT-DONE 2026-07-03; Michael "לא מממנים סטופים").
Read-only: SELECTs from v9_trades + v9_bars_5min_woodies, calls the real
resolve_stop() (backend.v9.systems.stop_anchors.stop_resolver). Changes nothing.

Method (honest proxy — labelled):
  * Rungs = real bar extremes from the ~12 bars before entry, on the correct
    side of entry, nearest→farthest (SHORT: highs above entry; LONG: lows
    below). This is the defensible generic form of the package §4 ladders
    (b3_low/b2_low/breakout_bar are all recent bar extremes). Pattern-internal
    levels (VEGAS cup, GHOST shoulders) are NOT modelled → those fall back and
    are flagged.
  * ATR_5m = mean true-range of the pre-entry window (<=14 bars).
  * "Financed" = old stop distance < 0.5×ATR floor (too tight — the exact
    problem being measured).
  * MAE = worst adverse excursion after entry, within the post-entry window
    (to exit_ts or +24 bars). "Premature stop-out avoided" = the trade actually
    hit its old stop AND MAE never breached the NEW in-band stop.
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
import psycopg2.extras

from backend.v9.systems.stop_anchors.stop_resolver import resolve_stop

DB = os.environ.get("DATABASE_URL", "postgresql://localhost/mems26")
LOOKBACK = 12          # pre-entry bars for rungs + ATR
POST_MAX = 24          # post-entry bars to scan for MAE if no exit_ts
TICK = 0.25
REV_PATTERNS = {"REACTIVE_SHORT", "REACTIVE_LONG", "HFE", "GHOST", "FAMIR",
                "HNS_TOP_SHORT", "INVERSE_HNS_LONG", "DOUBLE_TOP_AA_SHORT",
                "DOUBLE_BOTTOM_EE_LONG"}


def _atr(bars):
    if not bars:
        return 0.0
    trs = []
    prev_c = None
    for b in bars[-14:]:
        if prev_c is None:
            trs.append(b["high"] - b["low"])
        else:
            trs.append(max(b["high"] - b["low"], abs(b["high"] - prev_c),
                           abs(b["low"] - prev_c)))
        prev_c = b["close"]
    return sum(trs) / len(trs) if trs else 0.0


def _rungs(pre_bars, direction, entry):
    """Real bar extremes on the correct side of entry, nearest→farthest."""
    if direction == "SHORT":
        cand = sorted({round(b["high"], 2) for b in pre_bars if b["high"] > entry})
    else:
        cand = sorted({round(b["low"], 2) for b in pre_bars if b["low"] < entry},
                      reverse=True)
    return cand[:5]


def main():
    conn = psycopg2.connect(DB)
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    cur = conn.cursor()
    cur.execute("""
        SELECT id, firing_system, pattern_id_at_entry AS pattern, direction,
               entry_price, stop, entry_ts, exit_ts,
               (stop_hit_ts IS NOT NULL) AS stopped, pnl_r
        FROM v9_trades
        WHERE entry_ts >= '2026-06-22' AND entry_price IS NOT NULL
              AND stop IS NOT NULL AND pattern_id_at_entry IS NOT NULL
        ORDER BY id
    """)
    trades = cur.fetchall()
    cur.execute("""
        SELECT ts, open, high, low, close FROM v9_bars_5min_woodies
        WHERE ts >= '2026-06-22' ORDER BY ts
    """)
    bars = cur.fetchall()
    conn.close()

    agg = defaultdict(lambda: dict(n=0, old_risk=0.0, new_risk=0.0, financed=0,
                                   rejected=0, avoided=0, salvage_r=0.0))

    for t in trades:
        pat, d, entry = t["pattern"], t["direction"], float(t["entry_price"])
        old_stop = float(t["stop"])
        ets = t["entry_ts"]
        pre = [b for b in bars if b["ts"] < ets][-LOOKBACK:]
        if len(pre) < 3:
            continue
        atr = _atr(pre)
        if atr <= 0:
            continue
        family = "REV" if pat in REV_PATTERNS else "CONT"
        rungs = _rungs(pre, d, entry)
        res = resolve_stop(direction=d, entry_price=entry, rungs=rungs,
                           rung_names=[f"swing_{i+1}" for i in range(len(rungs))],
                           atr_5m=atr, family=family)

        a = agg[pat]
        a["n"] += 1
        old_risk = abs(entry - old_stop)
        a["old_risk"] += old_risk
        floor = max(0.5 * atr, 1.0)
        if old_risk < floor:
            a["financed"] += 1
        if res.rejected or not res.in_band:
            a["rejected"] += 1
            a["new_risk"] += old_risk  # fall back to old
            continue
        a["new_risk"] += res.risk_points

        # Survival: did old stop get hit, but the NEW stop would have held?
        if t["stopped"]:
            post = [b for b in bars if b["ts"] >= ets]
            xts = t["exit_ts"]
            if xts:
                post = [b for b in post if b["ts"] <= xts] or post[:POST_MAX]
            else:
                post = post[:POST_MAX]
            if post:
                if d == "SHORT":
                    mae = max(b["high"] for b in post)
                    fav = min(b["low"] for b in post)
                    survived = mae < res.stop_price
                    salvage = (entry - fav)
                else:
                    mae = min(b["low"] for b in post)
                    fav = max(b["high"] for b in post)
                    survived = mae > res.stop_price
                    salvage = (fav - entry)
                if survived:
                    a["avoided"] += 1
                    if res.risk_points > 0:
                        a["salvage_r"] += max(0.0, salvage) / res.risk_points

    # ---- report ----
    hdr = f"{'pattern':<18}{'n':>3}{'oldRisk':>9}{'newRisk':>9}{'financed':>9}{'reject':>7}{'saved':>6}{'~R+':>7}"
    lines = [hdr, "-" * len(hdr)]
    tot = dict(n=0, financed=0, avoided=0, salvage=0.0)
    for pat in sorted(agg, key=lambda p: -agg[p]["n"]):
        a = agg[pat]
        n = a["n"]
        if not n:
            continue
        lines.append(
            f"{pat:<18}{n:>3}{a['old_risk']/n:>9.1f}{a['new_risk']/n:>9.1f}"
            f"{a['financed']:>9}{a['rejected']:>7}{a['avoided']:>6}{a['salvage_r']:>7.1f}"
        )
        tot["n"] += n
        tot["financed"] += a["financed"]
        tot["avoided"] += a["avoided"]
        tot["salvage"] += a["salvage_r"]
    lines.append("-" * len(hdr))
    lines.append(f"{'TOTAL':<18}{tot['n']:>3}{'':>18}{tot['financed']:>9}{'':>7}"
                 f"{tot['avoided']:>6}{tot['salvage']:>7.1f}")
    out = "\n".join(lines)
    print(out)
    print(f"\nfinanced = old stop below the 0.5xATR floor (too tight) : {tot['financed']}/{tot['n']}")
    print(f"saved    = old stop hit, but the new in-band stop would have held : {tot['avoided']}")
    print(f"~R+      = upper-bound salvaged R on those (favorable excursion / new risk)")
    return out


if __name__ == "__main__":
    main()
