"""Counterfactual backtest of the DIRECTION_CONTEXT gate across all days.

For each ACTUAL trade, recompute direction_context POINT-IN-TIME (only bars up to
the fire; IB only after its 09:30 CT lock — no lookahead) and decide whether the
gate would BLOCK it (its side conflicts with the live UP/DOWN context). Removing a
blocked trade removes its realized pnl_usd → delta = -sum(blocked pnl).

Honest caveats (printed): first-order (no re-entry/cascade modeling); the balance
branch uses the FINAL session POC (mild lookahead, POC-branch only — accepted/failed
branches use IB+CVD+session-extremes which ARE point-in-time).
"""
from datetime import time as dtime
from backend.v9.db.read import read_all
from backend.v9.systems.direction_context import compute_direction

IB_LOCK = dtime(9, 30)  # first hour after 08:30 CT open → IB locked

trades = read_all(
    "SELECT id, (entry_ts AT TIME ZONE 'America/Chicago')::date d, "
    "(entry_ts AT TIME ZONE 'America/Chicago')::time ct, direction, "
    "pnl_usd, outcome, day_type_at_entry, firing_system "
    "FROM v9_trades WHERE pnl_usd IS NOT NULL ORDER BY entry_ts")

days = sorted({t['d'] for t in trades})
bars_by_day, tpo_by_day = {}, {}
for d in days:
    bars_by_day[d] = read_all(
        "SELECT (ts AT TIME ZONE 'America/Chicago')::time ct, high, low, close, cumulative_delta "
        "FROM v9_bars_5min WHERE (ts AT TIME ZONE 'America/Chicago')::date = :d "
        "AND (ts AT TIME ZONE 'America/Chicago')::time BETWEEN '08:30' AND '15:00' ORDER BY ts", {"d": d})
    tpo_by_day[d] = read_all(
        "SELECT ib_high, ib_low, poc_price FROM v9_tpo_sessions "
        "WHERE trading_date = :d AND session_type='CASH' ORDER BY id DESC LIMIT 1", {"d": d.isoformat()})
    _t = tpo_by_day[d][0] if tpo_by_day[d] else None
    print("  [data] %s bars=%d IB=%s POC=%s" % (
        d, len(bars_by_day[d]),
        ("%.2f-%.2f" % (_t['ib_high'], _t['ib_low'])) if (_t and _t.get('ib_high') is not None) else "MISSING",
        ("%.2f" % _t['poc_price']) if (_t and _t.get('poc_price') is not None) else "MISSING"))


def dc_for(t):
    day, ct = t['d'], t['ct']
    pit = [b for b in bars_by_day[day] if b['ct'] <= ct]  # point-in-time
    bars = [{"high": float(b['high']), "low": float(b['low']), "close": float(b['close']),
             "cumulative_delta": (float(b['cumulative_delta']) if b['cumulative_delta'] is not None else None)}
            for b in pit]
    tpo = tpo_by_day[day][0] if tpo_by_day[day] else None
    ib_avail = ct >= IB_LOCK
    ibh = float(tpo['ib_high']) if (tpo and ib_avail and tpo.get('ib_high') is not None) else None
    ibl = float(tpo['ib_low']) if (tpo and ib_avail and tpo.get('ib_low') is not None) else None
    poc = float(tpo['poc_price']) if (tpo and tpo.get('poc_price') is not None) else None
    return compute_direction(bars=bars, ib_high=ibh, ib_low=ibl, poc=poc)


rows = []
TOT = dict(n=0, blk=0, blk_pnl=0.0, blk_loss=0.0, blk_win=0.0, actual=0.0)
print("%-11s %4s %6s %4s %9s %9s %9s %9s" % ("day", "n", "actual", "blk", "blkLoss", "blkWin", "withDC", "delta"))
for d in days:
    ts = [t for t in trades if t['d'] == d]
    actual = sum(float(t['pnl_usd']) for t in ts)
    blk = [t for t in ts if (lambda dc: dc['dir'] in ("UP", "DOWN") and ("UP" if t['direction'] == "LONG" else "DOWN") != dc['dir'])(dc_for(t))]
    blk_pnl = sum(float(t['pnl_usd']) for t in blk)
    blk_loss = sum(float(t['pnl_usd']) for t in blk if float(t['pnl_usd']) < 0)
    blk_win = sum(float(t['pnl_usd']) for t in blk if float(t['pnl_usd']) > 0)
    withdc = actual - blk_pnl
    print("%-11s %4d %6.0f %4d %9.0f %9.0f %9.0f %+9.0f" % (
        str(d), len(ts), actual, len(blk), blk_loss, blk_win, withdc, -blk_pnl))
    TOT['n'] += len(ts); TOT['blk'] += len(blk); TOT['blk_pnl'] += blk_pnl
    TOT['blk_loss'] += blk_loss; TOT['blk_win'] += blk_win; TOT['actual'] += actual

print("-" * 70)
print("%-11s %4d %6.0f %4d %9.0f %9.0f %9.0f %+9.0f" % (
    "TOTAL", TOT['n'], TOT['actual'], TOT['blk'], TOT['blk_loss'], TOT['blk_win'],
    TOT['actual'] - TOT['blk_pnl'], -TOT['blk_pnl']))
# excluding today (06-22, session in progress)
import datetime as _dt
ex = [t for t in trades if t['d'] != _dt.date(2026, 6, 22)]
ex_actual = sum(float(t['pnl_usd']) for t in ex)
ex_blk = [t for t in ex if (lambda dc: dc['dir'] in ("UP", "DOWN") and ("UP" if t['direction'] == "LONG" else "DOWN") != dc['dir'])(dc_for(t))]
ex_blk_pnl = sum(float(t['pnl_usd']) for t in ex_blk)
print("\nexcluding 06-22 (in-progress): actual %.0f → withDC %.0f (delta %+.0f) | blocked %d (loss %.0f / win %.0f)" % (
    ex_actual, ex_actual - ex_blk_pnl, -ex_blk_pnl, len(ex_blk),
    sum(float(t['pnl_usd']) for t in ex_blk if float(t['pnl_usd']) < 0),
    sum(float(t['pnl_usd']) for t in ex_blk if float(t['pnl_usd']) > 0)))
print("\nblocked-trade quality: of %d blocked, %d were losers / %d winners" % (
    TOT['blk'], sum(1 for t in trades if (lambda dc: dc['dir'] in ("UP", "DOWN") and ("UP" if t['direction'] == "LONG" else "DOWN") != dc['dir'])(dc_for(t)) and float(t['pnl_usd']) < 0),
    sum(1 for t in trades if (lambda dc: dc['dir'] in ("UP", "DOWN") and ("UP" if t['direction'] == "LONG" else "DOWN") != dc['dir'])(dc_for(t)) and float(t['pnl_usd']) > 0)))
