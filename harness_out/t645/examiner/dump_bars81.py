#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dump the 5-min MES bars (RTH + ETH) + delta for the 81 replay sessions (12.06–23.10) → bars81.json (read-only SELECT).
Used only for the secondary candidate-level check of the questions (xquestions.py)."""
import os, sys, json, datetime as dt
ROOT = "/Users/michael/Downloads/mems26_web_git"
sys.path.insert(0, ROOT); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York")
a = dt.datetime(2026, 6, 10, 18, 0, tzinfo=ET); z = dt.datetime(2026, 10, 23, 17, 0, tzinfo=ET)
rows = read_all("""select b.ts, b.open o, b.high h, b.low l, b.close c, b.volume v, b.lsma_value lsma, b.trend_state ts_state, cd.delta
   from v9_bars_5min_woodies b left join (select distinct on (ts) ts, delta from v9_bars_cumulative_delta
   where ts >= :a and ts < :z order by ts, created_at desc) cd on cd.ts = b.ts
   where b.symbol = 'MES' and b.ts >= :a and b.ts < :z order by b.ts""", {"a": a, "z": z})
B = [dict(ts=b["ts"].isoformat(), o=float(b["o"]), h=float(b["h"]), l=float(b["l"]), c=float(b["c"]), v=float(b["v"] or 0),
          lsma=(float(b["lsma"]) if b["lsma"] is not None else None), tstate=b["ts_state"],
          d=(float(b["delta"]) if b["delta"] is not None else None)) for b in rows]
json.dump(dict(bars=B), open("harness_out/t645/examiner/bars81.json", "w"))
print(len(B), B[0]["ts"], B[-1]["ts"])
