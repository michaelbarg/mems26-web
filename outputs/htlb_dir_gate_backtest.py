"""Counterfactual backtest of HTLB_DIRECTION_GATE across recent days.

For each day: replay the LATCHED HTLB zoned-direction bias bar-by-bar over the
woodies CCI bars (same htlb_zoned_direction() the live engine uses), then check
each S4 (firing_system=4) shadow fire — if a bias is latched and the fire's
direction opposes it, the fire would be BLOCKED. Tally the P&L removed (losers
vs winners) -> withGate delta. READ-ONLY.

Run:  PYTHONPATH=<repo> python3 outputs/htlb_dir_gate_backtest.py
"""
import os
from sqlalchemy import create_engine, text
from backend.v9.systems.woodies.schemas import WoodiesBar
from backend.v9.systems.woodies.patterns.htlb import htlb_zoned_direction

eng = create_engine(os.environ.get("DATABASE_URL", "postgresql://localhost/mems26"))

DAYS_SQL = text("""select distinct (entry_ts AT TIME ZONE 'America/Chicago')::date d
                   from v9_trades where mode='shadow' and firing_system=4
                   order by d desc limit 12""")
BARS_SQL = text("""select ts, cci_14, open, high, low, close
                   from v9_bars_5min_woodies
                   where (ts AT TIME ZONE 'America/Chicago')::date = :d
                   order by ts""")
FIRES_SQL = text("""select id, entry_ts, direction, pnl_usd
                    from v9_trades
                    where (entry_ts AT TIME ZONE 'America/Chicago')::date = :d
                      and mode='shadow' and firing_system=4
                    order by entry_ts""")


def allowed(bias):
    return "LONG" if bias == "UP" else "SHORT" if bias == "DOWN" else None


with eng.connect() as c:
    days = sorted(r[0] for r in c.execute(DAYS_SQL))
    print(f"{'day':12} {'S4':>4} {'biasBars':>8} {'blk':>4} {'blkLoss':>9} {'blkWin':>8} {'delta':>8}")
    tot_n = tot_blk = 0
    tot_loss = tot_win = tot_delta = 0.0
    for d in days:
        bars = list(c.execute(BARS_SQL, {"d": str(d)}).mappings())
        wbs = []
        bias = None
        bias_at = []  # (ts, latched-bias-after-this-bar)
        for b in bars:
            wbs.append(WoodiesBar(ts=float(b["ts"].timestamp()),
                                  open=b["open"] or 0, high=b["high"] or 0,
                                  low=b["low"] or 0, close=b["close"] or 0,
                                  cci_14=float(b["cci_14"] or 0)))
            zd = htlb_zoned_direction(wbs)
            if zd:
                bias = zd
            bias_at.append((b["ts"], bias))
        n_bias = sum(1 for _, bb in bias_at if bb)

        fires = list(c.execute(FIRES_SQL, {"d": str(d)}).mappings())
        blk = 0
        blkloss = blkwin = 0.0
        for f in fires:
            fb = None
            for ts, bb in bias_at:
                if ts <= f["entry_ts"]:
                    fb = bb
                else:
                    break
            al = allowed(fb)
            if al and (f["direction"] or "").upper() != al:
                blk += 1
                p = float(f["pnl_usd"] or 0)
                if p < 0:
                    blkloss += p
                else:
                    blkwin += p
        delta = -(blkloss + blkwin)
        print(f"{str(d):12} {len(fires):>4} {n_bias:>8} {blk:>4} {blkloss:>9.0f} {blkwin:>8.0f} {delta:>+8.0f}")
        tot_n += len(fires)
        tot_blk += blk
        tot_loss += blkloss
        tot_win += blkwin
        tot_delta += delta
    print("-" * 60)
    print(f"{'TOTAL':12} {tot_n:>4} {'':>8} {tot_blk:>4} {tot_loss:>9.0f} {tot_win:>8.0f} {tot_delta:>+8.0f}")
    print(f"\nblocked {tot_blk} S4 fires: removes ${tot_loss:.0f} losses + ${tot_win:.0f} wins "
          f"-> net delta ${tot_delta:+.0f}")
