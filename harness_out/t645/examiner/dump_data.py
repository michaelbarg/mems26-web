#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-645 trade examiner — step 1: dump the read-only data the examiner needs into one JSON (no writes to the DB).

  bars   : v9_bars_5min_woodies MES 25.09–23.10 (ETH+RTH) + the latest delta per ts + lsma_value/trend_state
  trades : v9_trades demo/live/shadow for the examined sessions (key fields only; never the whole quality JSON)
  tpo    : v9_tpo_sessions CASH rows (the system's own VAH/VAL/POC/IB per day)
  dts    : v9_day_type_state rows (ts is NAIVE UTC) for the examined sessions

  python3 harness_out/t645/examiner/dump_data.py
"""
import os, sys, json, datetime as dt
ROOT = "/Users/michael/Downloads/mems26_web_git"
sys.path.insert(0, ROOT); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York")
OUT = "harness_out/t645/examiner/data.json"
DAYS = ["2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09",
        "2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23"]

a = dt.datetime(2026, 9, 24, 18, 0, tzinfo=ET); z = dt.datetime(2026, 10, 23, 17, 0, tzinfo=ET)
bars = read_all("""select b.ts, b.open o, b.high h, b.low l, b.close c, b.volume v, b.lsma_value lsma, b.trend_state ts_state,
   cd.delta from v9_bars_5min_woodies b left join (select distinct on (ts) ts, delta from v9_bars_cumulative_delta
   where ts >= :a and ts < :z order by ts, created_at desc) cd on cd.ts = b.ts
   where b.symbol = 'MES' and b.ts >= :a and b.ts < :z order by b.ts""", {"a": a, "z": z})
B = []
for b in bars:
    B.append(dict(ts=b["ts"].isoformat(), o=float(b["o"]), h=float(b["h"]), l=float(b["l"]), c=float(b["c"]),
                  v=float(b["v"] or 0), lsma=(float(b["lsma"]) if b["lsma"] is not None else None),
                  tstate=b["ts_state"], d=(float(b["delta"]) if b["delta"] is not None else None)))

trades = []
for day in DAYS:
    d0 = dt.date.fromisoformat(day)
    lo = dt.datetime.combine(d0, dt.time(9, 0), ET); hi = dt.datetime.combine(d0, dt.time(16, 30), ET)
    rows = read_all("""select id, mode, firing_system, direction, entry_ts, entry_price, stop, t1, t2, t3, t1_hit_ts, t2_hit_ts,
        stop_hit_ts, exit_ts, exit_price, exit_reason, pnl_usd, pnl_r, outcome, day_type_at_entry, pattern_id_at_entry,
        quality->>'blocked_by' blocked_by, quality->>'block_reason' block_reason, quality->>'contracts' contracts,
        quality->>'entry_stop' entry_stop, quality->>'initial_stop' initial_stop, quality->>'classification' cls,
        quality->'metadata'->>'stop_initial' stop_initial, quality->'metadata'->>'structural_anchor' anchor,
        quality->'metadata'->'situation' situation, quality->>'trigger' trig
        from v9_trades where mode in ('demo','live','shadow') and entry_ts >= :lo and entry_ts < :hi order by entry_ts""",
                    {"lo": lo, "hi": hi})
    for r in rows:
        x = {}
        for k, v in r.items():
            if isinstance(v, (dt.datetime, dt.date)):
                x[k] = v.isoformat()
            else:
                x[k] = v
        x["day"] = day
        trades.append(x)

tpo = read_all("""select trading_date, session_type, poc_price, vah_price, val_price, range_high, range_low, ib_high, ib_low,
   opening_type, profile_shape, ib_class from v9_tpo_sessions where session_type = 'CASH'
   and trading_date >= '2026-09-24' and trading_date <= '2026-10-23' order by trading_date, id""", {})
T = []
for r in tpo:
    T.append({k: (v.isoformat() if isinstance(v, (dt.date, dt.datetime)) else (float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v))
              for k, v in r.items()})

dts = []
for day in DAYS:
    d0 = dt.date.fromisoformat(day)
    # naive UTC: RTH 13:30-20:00 UTC in the analysed period (EDT)
    lo = dt.datetime.combine(d0, dt.time(13, 0)); hi = dt.datetime.combine(d0, dt.time(20, 30))
    rows = read_all("""select ts, stage, day_type, classification, confidence, opening_type, direction, lock_state, sides, rib, reason
        from v9_day_type_state where ts >= :lo and ts < :hi order by ts""", {"lo": lo, "hi": hi})
    for r in rows:
        dts.append(dict(day=day, ts_utc=r["ts"].isoformat(), stage=r["stage"], day_type=r["day_type"], cls=r["classification"],
                        conf=(float(r["confidence"]) if r["confidence"] is not None else None), ot=r["opening_type"],
                        direction=r["direction"], lock=r["lock_state"], sides=r["sides"],
                        rib=(float(r["rib"]) if r["rib"] is not None else None), reason=(r["reason"] or "")[:160]))

json.dump(dict(days=DAYS, bars=B, trades=trades, tpo=T, dts=dts), open(OUT, "w"), ensure_ascii=False, default=str)
from collections import Counter
print("bars", len(B), B[0]["ts"], B[-1]["ts"])
print("trades", len(trades), Counter((t["day"], t["mode"]) for t in trades))
print("tpo", len(T), "dts", len(dts), Counter(d["day"] for d in dts))
