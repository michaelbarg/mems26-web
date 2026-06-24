"""Backtest Michael's LSMA master-direction strategy (2026-06-23).

Rule (state explicitly so it can be corrected):
  * Direction filter: price ABOVE LSMA => LONG zone; price BELOW LSMA => SHORT zone.
  * A pattern fire (ANY pattern, S2 or S4) ENTERS only if flat AND its direction
    matches the current LSMA zone.
  * ONE trade at a time (while in a trade, ignore new fires).
  * Management/EXIT: hold until the bar close crosses the LSMA to the opposite
    side; exit at that close. (No other stop/target — pure LSMA-cross management.)
  * Re-enterable: after exit, the next aligned fire opens a new trade.

P&L in POINTS; $ shown at $15/pt (≈3 MES contracts, the system's sizing scale).
Set LSMA_INVERT=1 to flip the direction filter (LONG below / SHORT above).
READ-ONLY.  Run: PYTHONPATH=<repo> python3 outputs/lsma_strategy_backtest.py
"""
import os
from sqlalchemy import create_engine, text

eng = create_engine(os.environ.get("DATABASE_URL", "postgresql://localhost/mems26"))
INVERT = os.environ.get("LSMA_INVERT", "0") == "1"
USD_PER_PT = 15.0  # 3 MES contracts x $5/pt

DAYS = text("""select distinct (entry_ts AT TIME ZONE 'America/Chicago')::date d
               from v9_trades where mode='shadow' order by d""")
BARS = text("""select extract(epoch from ts) e, close, lsma_value
               from v9_bars_5min_woodies
               where (ts AT TIME ZONE 'America/Chicago')::date = :d
                 and lsma_value is not null
               order by ts""")
FIRES = text("""select extract(epoch from entry_ts) e, direction, entry_price, pnl_usd
                from v9_trades
                where (entry_ts AT TIME ZONE 'America/Chicago')::date = :d and mode='shadow'
                order by entry_ts""")


def zone(close, lsma):
    up = close > lsma
    if INVERT:
        up = not up
    return "LONG" if up else "SHORT"


with eng.connect() as c:
    days = [r[0] for r in c.execute(DAYS)]
    print(f"[rule] LONG={'below' if INVERT else 'above'} LSMA · one-at-a-time · exit on LSMA cross\n")
    print(f"{'day':12} {'fires':>5} {'taken':>5} {'win%':>5} {'pts':>8} {'$@15/pt':>9} {'actual$':>9}")
    T_take = T_win = 0
    T_pts = T_usd = T_act = 0.0
    for d in days:
        bars = [(float(b['e']), float(b['close']), float(b['lsma_value']))
                for b in c.execute(BARS, {'d': str(d)}).mappings()]
        fires = list(c.execute(FIRES, {'d': str(d)}).mappings())
        if not bars:
            continue
        open_until = None
        taken = win = 0
        pts_sum = 0.0
        for f in fires:
            fe = float(f['e'])
            if open_until is not None and fe <= open_until:
                continue
            zbar = None
            for b in bars:
                if b[0] <= fe:
                    zbar = b
                else:
                    break
            if zbar is None:
                continue
            z = zone(zbar[1], zbar[2])
            if (f['direction'] or '').upper() != z:
                continue
            entry = float(f['entry_price'])
            ex_price = ex_e = None
            for b in bars:
                if b[0] <= fe:
                    continue
                crossed = (b[1] < b[2]) if z == "LONG" else (b[1] > b[2])
                if INVERT:
                    crossed = not crossed
                if crossed:
                    ex_price, ex_e = b[1], b[0]
                    break
            if ex_price is None:
                ex_price, ex_e = bars[-1][1], bars[-1][0]
            pts = (ex_price - entry) if z == "LONG" else (entry - ex_price)
            taken += 1
            win += 1 if pts > 0 else 0
            pts_sum += pts
            open_until = ex_e
        act = sum(float(f['pnl_usd'] or 0) for f in fires)
        usd = pts_sum * USD_PER_PT
        wr = (100.0 * win / taken) if taken else 0.0
        print(f"{str(d):12} {len(fires):>5} {taken:>5} {wr:>4.0f}% {pts_sum:>8.1f} {usd:>+9.0f} {act:>+9.0f}")
        T_take += taken; T_win += win; T_pts += pts_sum; T_usd += usd; T_act += act
    print("-" * 64)
    wr = (100.0 * T_win / T_take) if T_take else 0.0
    print(f"{'TOTAL':12} {'':>5} {T_take:>5} {wr:>4.0f}% {T_pts:>8.1f} {T_usd:>+9.0f} {T_act:>+9.0f}")
    print(f"\nLSMA strategy: {T_take} trades, {wr:.0f}% win, {T_pts:+.1f} pts (~${T_usd:+.0f} @ 3 contracts) "
          f"vs actual ${T_act:+.0f}")
