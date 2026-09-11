"""T-319a — Normal Day Zone Analysis (since 2026-08-01)

Replay all Normal days, classify each trade entry by zone_of, cross with
direction and outcome.

Three outputs:
  (i)  mid_value live entries: count + win count
  (ii) edge-fade entries (near_vah∧SHORT or near_val∧LONG): count + Σ$
  (iii) edge-fade POC-as-T1 simulation vs actual T1 — Σ$ difference

Usage:
    python3 scripts/t319a_normal_day_zones.py
"""

import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://localhost/mems26")

# Must set DATABASE_URL before importing backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.v9.db.read import read_all, read_one  # noqa: E402


# ── zone_of (copied from backend/v9/systems/location_gate.py:145-165) ────────

def _tol(ib_width):
    try:
        if ib_width and float(ib_width) > 0:
            return min(max(0.25 * float(ib_width), 1.0), 4.0)
    except (TypeError, ValueError):
        pass
    return 2.0


def zone_of(entry, vah, val, ib_width):
    """Classify entry location relative to value area."""
    t = _tol(ib_width)
    if entry >= vah + t:
        return "above_value"
    if entry >= vah - t:
        return "near_vah"
    if entry <= val - t:
        return "below_value"
    if entry <= val + t:
        return "near_val"
    return "mid_value"


# ── Step 1: Normal days since 2026-08-01 ────────────────────────────────────

normal_day_rows = read_all(
    """
    SELECT DISTINCT DATE(created_at) AS trading_date
    FROM v9_day_type_state
    WHERE day_type = 'Normal'
      AND created_at >= '2026-08-01'
    ORDER BY 1
    """
)
normal_dates = [str(r["trading_date"]) for r in normal_day_rows]
print(f"Normal days found: {len(normal_dates)}")
for d in normal_dates:
    print(f"  {d}")
print()

if not normal_dates:
    print("No Normal days — nothing to analyse.")
    sys.exit(0)

# ── Step 2 & 3: For each day get TPO + trades ────────────────────────────────

# Accumulators for the three outputs
# (i) mid_value live
mv_live_count = 0
mv_live_wins = 0

# (ii) edge-fade (near_vah+SHORT or near_val+LONG)
ef_count = 0
ef_pnl_sum = 0.0          # live=pnl_sierra, shadow=sign(pnl_usd)*1

# (iii) POC-as-T1 simulation
#   For each edge-fade trade we know: entry_price, direction, poc (T1 sim),
#   actual t1, exit_price/pnl.
#   Sim profit = |entry - poc| * $5 per tick (* 0.25 per tick, $5/tick MES)
#   Actual profit already in pnl (live=sierra, shadow=sign).
#   We report Σ(sim_pnl - actual_pnl) to show whether POC as T1 would have
#   been better or worse than what actually happened.
ef_sim_poc_pnl_sum = 0.0
ef_actual_pnl_sum = 0.0   # same set, for the difference calc

# Per-day detail rows
day_details = []

TICK_VALUE = 5.0  # MES: $5 per 0.25 tick = $5/tick; entry-poc in points → *4*$5 = $20/pt
POINT_VALUE = 20.0  # $20 per full point (4 ticks * $5)

for date_str in normal_dates:
    # --- TPO (prefer CASH session; fallback to GLOBEX if missing) ---
    tpo = read_one(
        """
        SELECT vah_price, val_price, poc_price, ib_high, ib_low, ib_width
        FROM v9_tpo_sessions
        WHERE trading_date = :d
          AND session_type = 'CASH'
        ORDER BY id DESC
        LIMIT 1
        """,
        {"d": date_str},
    )
    if tpo is None:
        tpo = read_one(
            """
            SELECT vah_price, val_price, poc_price, ib_high, ib_low, ib_width
            FROM v9_tpo_sessions
            WHERE trading_date = :d
            ORDER BY id DESC
            LIMIT 1
            """,
            {"d": date_str},
        )
    if tpo is None or tpo.get("vah_price") is None:
        print(f"  {date_str}: no TPO data — skipping")
        continue

    vah = float(tpo["vah_price"])
    val = float(tpo["val_price"])
    poc = float(tpo["poc_price"])
    ib_width = tpo.get("ib_width")

    # --- Trades for that date ---
    trades = read_all(
        """
        SELECT mode, direction, entry_price, pnl_usd, pnl_sierra,
               outcome, t1, exit_price
        FROM v9_trades
        WHERE DATE(entry_ts) = :d
          AND mode IN ('live', 'demo', 'shadow')
          AND entry_price IS NOT NULL
        ORDER BY entry_ts
        """,
        {"d": date_str},
    )

    day_ef = 0
    day_ef_pnl = 0.0

    for tr in trades:
        mode = tr["mode"]
        direction = (tr["direction"] or "").upper()
        entry = float(tr["entry_price"])
        pnl_usd = tr["pnl_usd"]
        pnl_sierra = tr["pnl_sierra"]
        outcome = tr["outcome"]
        t1_price = tr["t1"]

        zone = zone_of(entry, vah, val, ib_width)

        # PnL selector: live/demo → pnl_sierra (fallback pnl_usd); shadow → sign
        if mode in ("live", "demo"):
            if pnl_sierra is not None:
                pnl = float(pnl_sierra)
            elif pnl_usd is not None:
                pnl = float(pnl_usd)
            else:
                pnl = None
        else:
            # shadow: sign of pnl_usd → +1 or -1 (or 0)
            if pnl_usd is not None:
                pnl = 1.0 if float(pnl_usd) > 0 else (-1.0 if float(pnl_usd) < 0 else 0.0)
            else:
                pnl = None

        # (i) mid_value live entries
        if zone == "mid_value" and mode == "live":
            mv_live_count += 1
            if pnl is not None and pnl > 0:
                mv_live_wins += 1

        # (ii)+(iii) edge-fade: near_vah+SHORT or near_val+LONG
        is_edge_fade = (zone == "near_vah" and direction == "SHORT") or \
                       (zone == "near_val" and direction == "LONG")

        if is_edge_fade:
            ef_count += 1
            day_ef += 1
            if pnl is not None:
                ef_pnl_sum += pnl
                ef_actual_pnl_sum += pnl
                day_ef_pnl += pnl

            # (iii) POC-as-T1 simulation
            # Sim: if we had exited at POC instead of actual T1
            # sim_pnl = (entry - poc) * POINT_VALUE for SHORT (fade from VAH toward POC)
            #         = (poc - entry) * POINT_VALUE for LONG  (fade from VAL toward POC)
            # We cap at target (assume full T1 hit at POC); no stop modeling here.
            if direction == "SHORT":
                sim_pnl = (entry - poc) * POINT_VALUE
            else:  # LONG from near_val
                sim_pnl = (poc - entry) * POINT_VALUE
            # sim_pnl can be negative if poc is on wrong side (unusual)
            ef_sim_poc_pnl_sum += sim_pnl

    day_details.append({
        "date": date_str,
        "vah": vah,
        "val": val,
        "poc": poc,
        "ib_width": ib_width,
        "trade_count": len(trades),
        "ef_count": day_ef,
        "ef_pnl": day_ef_pnl,
    })

# ── Output ───────────────────────────────────────────────────────────────────

print("=" * 60)
print("T-319a  Normal Day Zone Analysis — since 2026-08-01")
print("=" * 60)

print("\nPer-day summary:")
print(f"  {'Date':<12} {'VAH':>8} {'VAL':>8} {'POC':>8} {'IB':>6}  {'Trades':>6}  {'EF':>4}  {'EF_Σ$':>10}")
for d in day_details:
    ib_str = f"{d['ib_width']:.2f}" if d["ib_width"] else "n/a"
    ef_pnl_str = f"{d['ef_pnl']:+.2f}" if d["ef_count"] else "—"
    print(
        f"  {d['date']:<12} {d['vah']:>8.2f} {d['val']:>8.2f} {d['poc']:>8.2f} "
        f"{ib_str:>6}  {d['trade_count']:>6}  {d['ef_count']:>4}  {ef_pnl_str:>10}"
    )

print()
print("─" * 60)
print("RESULTS")
print("─" * 60)

print(f"\n(i)  mid_value LIVE entries")
print(f"     Count : {mv_live_count}")
print(f"     Wins  : {mv_live_wins}")
win_rate = (mv_live_wins / mv_live_count * 100) if mv_live_count else 0
print(f"     Win%  : {win_rate:.1f}%")

print(f"\n(ii) Edge-fade entries  (near_vah∧SHORT  or  near_val∧LONG)")
print(f"     Count : {ef_count}")
print(f"     Σ$    : {ef_pnl_sum:+.2f}  (live=pnl_sierra, shadow=sign[-1/+1])")

print(f"\n(iii) Edge-fade POC-as-T1 simulation vs actual")
print(f"      Σ$ sim (POC as T1) : {ef_sim_poc_pnl_sum:+.2f}")
print(f"      Σ$ actual          : {ef_actual_pnl_sum:+.2f}")
print(f"      Difference (sim-actual) : {ef_sim_poc_pnl_sum - ef_actual_pnl_sum:+.2f}")
print(f"      NOTE: sim assumes 1 MES contract, full POC hit, no stops.")

print()
