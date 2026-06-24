"""LSMA-crossover always-in strategy (Michael's corrected rule).

ONE trade per side of the LSMA. Enter when price crosses to a side, EXIT ONLY when
it flips (crosses to the other side), then take the opposite. Always in the market,
one position. NOT pattern-triggered — the LSMA cross IS the entry/exit.

Two directions (exact mirrors):
  * MEAN-REV  : below LSMA = LONG, above = SHORT  (Michael's earlier profitable read)
  * TREND     : above LSMA = LONG, below = SHORT  (= -MEAN-REV)

P&L in points; $ at $15/pt (3 MES contracts). READ-ONLY.
Run: PYTHONPATH=<repo> python3 outputs/lsma_crossover_backtest.py
"""
import os
from sqlalchemy import create_engine, text

eng = create_engine(os.environ.get("DATABASE_URL", "postgresql://localhost/mems26"))
USD = 15.0
DAYS = text("""select distinct (entry_ts AT TIME ZONE 'America/Chicago')::date d
               from v9_trades where mode='shadow' order by d""")
BARS = text("""select close c, lsma_value l from v9_bars_5min_woodies
               where (ts AT TIME ZONE 'America/Chicago')::date = :d
                 and (ts AT TIME ZONE 'America/Chicago')::time between '08:30' and '15:00'
                 and lsma_value is not null
               order by ts""")


def side(c, l):
    return "A" if c > l else "B"   # Above / Below the LSMA


with eng.connect() as c:
    days = [r[0] for r in c.execute(DAYS)]
    print(f"{'day':12} {'trades':>6} {'win%':>5} {'MEANREV pts':>11} {'MEANREV$':>9} {'TREND$':>8}")
    T_tr = T_win = 0
    T_mr = 0.0
    for d in days:
        bars = [(float(b['c']), float(b['l'])) for b in c.execute(BARS, {'d': str(d)}).mappings()]
        if len(bars) < 2:
            continue
        segs = []
        cur = side(*bars[0]); en = bars[0][0]
        for cl, ls in bars[1:]:
            s = side(cl, ls)
            if s != cur:
                segs.append((cur, en, cl)); cur = s; en = cl
        segs.append((cur, en, bars[-1][0]))
        mr = 0.0; win = 0
        for sd, enp, exp in segs:
            pts = (exp - enp) if sd == "B" else (enp - exp)   # B(below)=LONG, A(above)=SHORT
            mr += pts; win += 1 if pts > 0 else 0
        wr = 100.0 * win / len(segs)
        print(f"{str(d):12} {len(segs):>6} {wr:>4.0f}% {mr:>11.1f} {mr*USD:>+9.0f} {-mr*USD:>+8.0f}")
        T_tr += len(segs); T_win += win; T_mr += mr
    print("-" * 56)
    wr = 100.0 * T_win / T_tr if T_tr else 0
    print(f"{'TOTAL':12} {T_tr:>6} {wr:>4.0f}% {T_mr:>11.1f} {T_mr*USD:>+9.0f} {-T_mr*USD:>+8.0f}")
    print(f"\nLSMA-crossover always-in: {T_tr} trades, {wr:.0f}% win-segments. "
          f"MEAN-REV (long below) ${T_mr*USD:+.0f} · TREND (long above) ${-T_mr*USD:+.0f}")
