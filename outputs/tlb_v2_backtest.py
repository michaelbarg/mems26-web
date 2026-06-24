"""Counterfactual backtest of TLB_SPEC_V2 across recent days.

For each ACTUAL TLB shadow fire, reconstruct the woodies bars up to the fire and
run the v2 gate (_tlb_v2_gate: ±200 extreme on the trade side + a confirming CONT
partner GB100/ZLR/TT). If the gate rejects, the fire would be BLOCKED. Tally the
P&L removed (losers vs winners) -> withGate delta. READ-ONLY.

Run:  PYTHONPATH=<repo> python3 outputs/tlb_v2_backtest.py
"""
import os
from sqlalchemy import create_engine, text
from backend.v9.systems.woodies.schemas import WoodiesBar
from backend.v9.systems.woodies.patterns.tlb import _tlb_v2_gate

eng = create_engine(os.environ.get("DATABASE_URL", "postgresql://localhost/mems26"))

# Tuning knobs for the validation sweep (sources disagree: Zohar image ±200 vs
# TABLE_A "anchor past ±100"). Override the gate's module globals before calling.
import backend.v9.systems.woodies.patterns.tlb as _tlbmod
_tlbmod._V2_EXTREME_LEVEL = float(os.environ.get("V2_LEVEL", "200"))
if os.environ.get("V2_NOCOMBO") == "1":
    _tlbmod._V2_REQUIRE_COMBO = False
print(f"[config] extreme=+/-{_tlbmod._V2_EXTREME_LEVEL:.0f}  "
      f"combo={'OFF' if not _tlbmod._V2_REQUIRE_COMBO else 'ON'}")

DAYS = text("""select distinct (entry_ts AT TIME ZONE 'America/Chicago')::date d
               from v9_trades where mode='shadow' and pattern_id_at_entry='TLB' order by d""")
BARS = text("""select ts, cci_14, trend_state, zlr_detected, zlr_direction, hfe_detected,
                      hfe_direction, swi_value, open, high, low, close
               from v9_bars_5min_woodies
               where (ts AT TIME ZONE 'America/Chicago')::date = :d order by ts""")
FIRES = text("""select id, entry_ts, direction, pnl_usd from v9_trades
                where (entry_ts AT TIME ZONE 'America/Chicago')::date = :d
                  and mode='shadow' and pattern_id_at_entry='TLB' order by entry_ts""")


def wb(r):
    return WoodiesBar(ts=float(r["ts"].timestamp()), open=r["open"] or 0, high=r["high"] or 0,
                      low=r["low"] or 0, close=r["close"] or 0, cci_14=float(r["cci_14"] or 0),
                      trend_state=(r["trend_state"] or "GRAY"),
                      zlr_detected=bool(r["zlr_detected"]), zlr_direction=(r["zlr_direction"] or "NONE"),
                      hfe_detected=bool(r["hfe_detected"]), hfe_direction=(r["hfe_direction"] or "NONE"),
                      swi_value=float(r["swi_value"] or 0))


with eng.connect() as c:
    days = sorted(r[0] for r in c.execute(DAYS))
    print(f"{'day':12} {'TLB':>4} {'blk':>4} {'blkLoss':>9} {'blkWin':>8} {'delta':>8}  reasons")
    tn = tb = 0
    tl = tw = td = 0.0
    for d in days:
        bars = [wb(r) for r in c.execute(BARS, {"d": str(d)}).mappings()]
        fires = list(c.execute(FIRES, {"d": str(d)}).mappings())
        blk = 0
        bl = bw = 0.0
        reasons = set()
        for f in fires:
            cut = f["entry_ts"].timestamp()
            upto = [b for b in bars if b.ts <= cut]
            if len(upto) < 12:
                continue
            ok, why = _tlb_v2_gate(upto, (f["direction"] or "").upper())
            if not ok:
                blk += 1
                p = float(f["pnl_usd"] or 0)
                if p < 0:
                    bl += p
                else:
                    bw += p
                reasons.add(why[:22])
        delta = -(bl + bw)
        print(f"{str(d):12} {len(fires):>4} {blk:>4} {bl:>9.0f} {bw:>8.0f} {delta:>+8.0f}  {'; '.join(sorted(reasons))[:46]}")
        tn += len(fires)
        tb += blk
        tl += bl
        tw += bw
        td += delta
    print("-" * 78)
    print(f"{'TOTAL':12} {tn:>4} {tb:>4} {tl:>9.0f} {tw:>8.0f} {td:>+8.0f}")
    print(f"\nblocked {tb}/{tn} TLB fires: removes ${tl:.0f} losses + ${tw:.0f} wins -> net delta ${td:+.0f}")
