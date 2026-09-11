"""T-319a — Normal Day Zone Analysis

Replay all Normal days (tagged via day_type_at_entry on each trade — NOT the
day's final label), classify each trade entry by zone_of, simulate POC-target
vs IB-edge stop using 5-min bars bar-by-bar.

Outputs:
  Header:  N days tagged in v9_day_type_state, M total trades, L live trades
  (i)   mid_value entries: count, wins, losses — live/$ separate, shadow/sign separate
  (ii)  edge-fade entries: count, Σ$ live, sign-count shadow
  (iii) POC-target sim WITH stops: count hit POC, count stopped out, Σ$ sim, Σ$ actual live

Usage:
    DATABASE_URL=postgresql://localhost/mems26 python3 scripts/t319a_normal_day_zones.py
"""

import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://localhost/mems26")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.v9.db.read import read_all, read_one  # noqa: E402
from backend.v9.systems.location_gate import zone_of  # noqa: E402

# ── POINT_VALUE ───────────────────────────────────────────────────────────────
try:
    from backend.v9.services.sierra_ledger import DEFAULT_POINT_VALUE  # type: ignore
    POINT_VALUE = float(DEFAULT_POINT_VALUE)
except Exception:
    POINT_VALUE = 5.0  # MES: $5 per point

TICK_SIZE = 0.25       # MES minimum tick
TICK_VALUE = POINT_VALUE * TICK_SIZE  # $1.25 per tick on MES (but per-point = $5)

# ── 1. Date range from v9_day_type_state ─────────────────────────────────────
dts_range = read_one("""
    SELECT MIN(DATE(ts)) AS min_date, MAX(DATE(ts)) AS max_date,
           COUNT(DISTINCT DATE(ts)) AS n_dates
    FROM v9_day_type_state
""")
min_date = dts_range["min_date"]
max_date = dts_range["max_date"]
n_dates_tagged = dts_range["n_dates"] or 0

# ── 2. Pull all Normal-tagged trades (use day_type_at_entry, not day's final) ─
all_normal_trades = read_all("""
    SELECT id, mode, direction, entry_price, stop AS stop_price, t1,
           pnl_usd, pnl_sierra, outcome, quality, entry_ts,
           DATE(entry_ts) AS trade_date
    FROM v9_trades
    WHERE day_type_at_entry = 'Normal'
      AND entry_price IS NOT NULL
    ORDER BY entry_ts
""")

total_trades = len(all_normal_trades)
live_trades = sum(1 for t in all_normal_trades if t["mode"] in ("live", "demo"))

# Collect unique trade dates for TPO lookup
trade_dates = sorted(set(
    str(t["trade_date"]) for t in all_normal_trades if t["trade_date"] is not None
))

# ── 3. Pre-fetch TPO for each date (CASH session only; IB from CASH row) ──────
tpo_cache: dict = {}
for date_str in trade_dates:
    tpo = read_one("""
        SELECT vah_price, val_price, poc_price, ib_high, ib_low, ib_width
        FROM v9_tpo_sessions
        WHERE trading_date = :d AND session_type = 'CASH'
        ORDER BY id DESC
        LIMIT 1
    """, {"d": date_str})
    if tpo and tpo.get("vah_price") is not None:
        tpo_cache[date_str] = tpo

# ── 4. Pre-fetch 5-min bars for each date ─────────────────────────────────────
bars_cache: dict = {}
for date_str in trade_dates:
    # Bars within the trading session window for that date.
    # The bars have tz-aware timestamps; entry_ts uses UTC+3 (Israel).
    # We load all bars on that calendar date (local TZ), covering RTH+after.
    bars = read_all("""
        SELECT ts, high, low
        FROM v9_bars_5min_woodies
        WHERE DATE(ts) = :d
        ORDER BY ts
    """, {"d": date_str})
    bars_cache[date_str] = bars

# ── 5. Accumulators ───────────────────────────────────────────────────────────
# (i) mid_value
mv_live_count = 0
mv_live_wins = 0
mv_live_losses = 0
mv_shadow_count = 0
mv_shadow_wins = 0   # sign = +1
mv_shadow_losses = 0  # sign = -1

# (ii) edge-fade
ef_live_count = 0
ef_live_pnl = 0.0    # Σ$ live (pnl_sierra × contracts)
ef_shadow_count = 0
ef_shadow_signs = 0  # Σ signs (+1/-1)

# (iii) POC sim with stops
sim_count = 0         # trades attempted (have t1/stop + bars)
sim_poc_hit = 0
sim_stopped = 0
sim_neither = 0       # neither hit in bars window
sim_pnl_sum = 0.0    # Σ$ sim
actual_live_pnl = 0.0  # Σ$ actual live (for those same trades)

# Per-trade detail for per-day table
day_accumulator: dict = {}

# ── 6. Process each trade ─────────────────────────────────────────────────────
skipped_no_tpo = 0
skipped_no_bars = 0

for tr in all_normal_trades:
    date_str = str(tr["trade_date"]) if tr["trade_date"] else None
    if date_str is None:
        continue

    tpo = tpo_cache.get(date_str)
    if tpo is None:
        skipped_no_tpo += 1
        continue

    vah = float(tpo["vah_price"])
    val = float(tpo["val_price"])
    poc = float(tpo["poc_price"])
    ib_high = float(tpo["ib_high"]) if tpo.get("ib_high") is not None else None
    ib_low = float(tpo["ib_low"]) if tpo.get("ib_low") is not None else None
    ib_width = tpo.get("ib_width")

    mode = tr["mode"]
    direction = (tr["direction"] or "").upper()
    entry = float(tr["entry_price"])
    pnl_usd = tr.get("pnl_usd")
    pnl_sierra = tr.get("pnl_sierra")
    outcome = tr.get("outcome", "")

    # Contracts from quality JSON
    quality = tr.get("quality") or {}
    if isinstance(quality, dict):
        contracts = int(quality.get("contracts", 1) or 1)
    else:
        contracts = 1

    # PnL: live/demo = pnl_sierra × contracts ($); shadow = sign
    if mode in ("live", "demo"):
        if pnl_sierra is not None:
            pnl_dollars = float(pnl_sierra)
        elif pnl_usd is not None:
            pnl_dollars = float(pnl_usd)
        else:
            pnl_dollars = None
    else:
        # shadow → sign only
        pnl_dollars = None
        if pnl_usd is not None:
            pnl_sign = 1 if float(pnl_usd) > 0 else (-1 if float(pnl_usd) < 0 else 0)
        elif outcome == "WIN":
            pnl_sign = 1
        elif outcome == "LOSS":
            pnl_sign = -1
        else:
            pnl_sign = 0
        # bind for below
        shadow_sign = pnl_sign

    zone = zone_of(entry, vah, val, ib_width)

    # --- Accumulate day totals ---
    if date_str not in day_accumulator:
        day_accumulator[date_str] = {
            "vah": vah, "val": val, "poc": poc, "ib_width": ib_width,
            "trades": 0, "live_trades": 0, "shadow_trades": 0,
            "ef_live": 0, "ef_shadow": 0,
        }
    day_accumulator[date_str]["trades"] += 1
    if mode in ("live", "demo"):
        day_accumulator[date_str]["live_trades"] += 1
    else:
        day_accumulator[date_str]["shadow_trades"] += 1

    # ── (i) mid_value ──
    if zone == "mid_value":
        if mode in ("live", "demo"):
            mv_live_count += 1
            if pnl_dollars is not None and pnl_dollars > 0:
                mv_live_wins += 1
            elif pnl_dollars is not None and pnl_dollars < 0:
                mv_live_losses += 1
        else:
            mv_shadow_count += 1
            if shadow_sign > 0:
                mv_shadow_wins += 1
            elif shadow_sign < 0:
                mv_shadow_losses += 1

    # ── (ii) edge-fade: near_vah+SHORT or near_val+LONG ──
    is_ef = (zone == "near_vah" and direction == "SHORT") or \
            (zone == "near_val" and direction == "LONG")

    if is_ef:
        if mode in ("live", "demo"):
            ef_live_count += 1
            if pnl_dollars is not None:
                ef_live_pnl += pnl_dollars
            day_accumulator[date_str]["ef_live"] += 1
        else:
            ef_shadow_count += 1
            ef_shadow_signs += shadow_sign
            day_accumulator[date_str]["ef_shadow"] += 1

    # ── (iii) POC sim with stops ──
    # Only for edge-fade trades (the ones we're studying as "fade the edge")
    # Stop = IB_HIGH + 1 tick (LONG) or IB_LOW - 1 tick (SHORT)
    # Target = POC
    # Walk 5-min bars after entry; whichever hits first wins.
    if is_ef and ib_high is not None and ib_low is not None:
        # Stop levels: BEYOND_IB_EDGE = ib_high+1tick for SHORT (stop out if high >= stop)
        #                               ib_low-1tick for LONG (stop out if low <= stop)
        if direction == "SHORT":
            stop_level = ib_high + TICK_SIZE   # stop above IB high
            target_level = poc                 # target below entry at poc
        else:  # LONG from near_val
            stop_level = ib_low - TICK_SIZE    # stop below IB low
            target_level = poc                 # target above entry at poc

        entry_ts = tr.get("entry_ts")
        bars = bars_cache.get(date_str, [])
        # Only bars after entry
        bars_after = [b for b in bars if entry_ts is None or b["ts"] > entry_ts]

        if not bars_after:
            skipped_no_bars += 1
            # can't simulate — still count the trade in the section
            sim_count += 1
            sim_neither += 1
            # carry actual live pnl
            if mode in ("live", "demo") and pnl_dollars is not None:
                actual_live_pnl += pnl_dollars
            continue

        sim_count += 1
        result = "neither"
        sim_trade_pnl = 0.0

        for bar in bars_after:
            bar_high = float(bar["high"])
            bar_low = float(bar["low"])

            if direction == "SHORT":
                # SHORT: stop hit if bar_high >= stop_level; target if bar_low <= poc
                hit_stop = bar_high >= stop_level
                hit_target = bar_low <= poc
            else:
                # LONG: stop hit if bar_low <= stop_level; target if bar_high >= poc
                hit_stop = bar_low <= stop_level
                hit_target = bar_high >= poc

            if hit_stop and hit_target:
                # Same bar: conservative — assume open determines order
                # If target is closer to entry, assume target hits first
                if direction == "SHORT":
                    dist_stop = abs(stop_level - entry)
                    dist_target = abs(poc - entry)
                else:
                    dist_stop = abs(entry - stop_level)
                    dist_target = abs(entry - poc)

                if dist_target <= dist_stop:
                    result = "poc_hit"
                    sim_trade_pnl = abs(entry - poc) * POINT_VALUE * contracts
                    if direction == "SHORT":
                        sim_trade_pnl = (entry - poc) * POINT_VALUE * contracts
                    else:
                        sim_trade_pnl = (poc - entry) * POINT_VALUE * contracts
                else:
                    result = "stopped"
                    # Loss: stop distance × point value × contracts
                    if direction == "SHORT":
                        sim_trade_pnl = -(abs(stop_level - entry) * POINT_VALUE * contracts)
                    else:
                        sim_trade_pnl = -(abs(entry - stop_level) * POINT_VALUE * contracts)
                break
            elif hit_stop:
                result = "stopped"
                if direction == "SHORT":
                    sim_trade_pnl = -(abs(stop_level - entry) * POINT_VALUE * contracts)
                else:
                    sim_trade_pnl = -(abs(entry - stop_level) * POINT_VALUE * contracts)
                break
            elif hit_target:
                result = "poc_hit"
                if direction == "SHORT":
                    sim_trade_pnl = (entry - poc) * POINT_VALUE * contracts
                else:
                    sim_trade_pnl = (poc - entry) * POINT_VALUE * contracts
                break

        if result == "poc_hit":
            sim_poc_hit += 1
        elif result == "stopped":
            sim_stopped += 1
        else:
            sim_neither += 1

        sim_pnl_sum += sim_trade_pnl

        if mode in ("live", "demo") and pnl_dollars is not None:
            actual_live_pnl += pnl_dollars

# ── 7. Output ─────────────────────────────────────────────────────────────────
print("=" * 68)
print("T-319a  Normal Day Zone Analysis")
print("=" * 68)
print()
print(f"v9_day_type_state date range:  {min_date} … {max_date}  ({n_dates_tagged} days tagged)")
print()
print(f"N days tagged in v9_day_type_state : {n_dates_tagged}")
print(f"M total Normal-tagged trades        : {total_trades}")
print(f"L live/demo Normal-tagged trades    : {live_trades}")
print(f"Shadow Normal-tagged trades         : {total_trades - live_trades}")
print(f"Skipped (no CASH TPO)               : {skipped_no_tpo}")
print()

# Per-day summary
print("Per-day summary (Normal-tagged trades):")
header = f"  {'Date':<12} {'VAH':>8} {'VAL':>8} {'POC':>8} {'IB':>6}  {'Total':>6}  {'Live':>5}  {'Shadow':>7}  {'EF-Live':>8}  {'EF-Shad':>8}"
print(header)
for d in sorted(day_accumulator.keys()):
    da = day_accumulator[d]
    ib_str = f"{da['ib_width']:.2f}" if da["ib_width"] else "n/a"
    print(
        f"  {d:<12} {da['vah']:>8.2f} {da['val']:>8.2f} {da['poc']:>8.2f} "
        f"{ib_str:>6}  {da['trades']:>6}  {da['live_trades']:>5}  {da['shadow_trades']:>7}  "
        f"{da['ef_live']:>8}  {da['ef_shadow']:>8}"
    )

print()
print("─" * 68)
print("RESULTS")
print("─" * 68)

# (i) mid_value
print()
print("(i)  mid_value entries")
print(f"     LIVE/DEMO ({mv_live_count} trades)")
print(f"       Wins  : {mv_live_wins}")
print(f"       Losses: {mv_live_losses}")
wr = (mv_live_wins / mv_live_count * 100) if mv_live_count else 0.0
print(f"       Win%  : {wr:.1f}%")
print(f"     SHADOW ({mv_shadow_count} trades)  [sign counts, NOT $]")
print(f"       +1    : {mv_shadow_wins}")
print(f"       -1    : {mv_shadow_losses}")
shad_wr = (mv_shadow_wins / mv_shadow_count * 100) if mv_shadow_count else 0.0
print(f"       Win%  : {shad_wr:.1f}%")

# (ii) edge-fade
print()
print("(ii) Edge-fade entries  (near_vah∧SHORT  or  near_val∧LONG)")
print(f"     LIVE/DEMO")
print(f"       Count : {ef_live_count}")
print(f"       Σ$    : {ef_live_pnl:+.2f}  (pnl_sierra × contracts, $5/pt)")
print(f"     SHADOW  [sign counts, NOT $]")
print(f"       Count : {ef_shadow_count}")
print(f"       Σ signs: {ef_shadow_signs:+d}  (+1=win / -1=loss)")

# (iii) POC sim
print()
print("(iii) POC-target sim WITH IB-edge stops  (edge-fade trades only)")
print(f"      Stop = IB_edge ± 1 tick | Target = POC")
print(f"      Walk bar-by-bar (5-min); whichever hits first wins.")
print()
print(f"      Trades simulated      : {sim_count}")
print(f"      Hit POC (win)         : {sim_poc_hit}")
print(f"      Stopped (loss)        : {sim_stopped}")
print(f"      Neither (no hit)      : {sim_neither}")
print(f"      Σ$ sim                : {sim_pnl_sum:+.2f}  (@ $5/pt/contract)")
print(f"      Σ$ actual live        : {actual_live_pnl:+.2f}  (pnl_sierra of live trades in this set)")
print()
print(f"      POINT_VALUE used      : ${POINT_VALUE:.1f}/point")
print()
print(f"NOTE: Live/demo $ and shadow signs are NEVER added together.")
print()
