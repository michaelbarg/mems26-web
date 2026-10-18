#!/usr/bin/env python3
"""T-586 · step 3 — validate the tick-built series against the live DB (v9_bars_5min_woodies) on an overlap day.
usage: validate_vs_db.py <merged.csv> <YYYY-MM-DD (UTC day)>"""
import sys, subprocess, io, numpy as np, pandas as pd
PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
f, day = sys.argv[1], sys.argv[2]
cols = "ts,open,high,low,close,volume,cci_14,cci_6_tcci,lsma_value,swi_value,czi_value,ema_34,trend_state,predictor_next_cci,zlr_detected,zlr_direction,lsma_above_price"
sql = (f"select extract(epoch from ts)::bigint as ts,{cols[3:]} from v9_bars_5min_woodies where symbol='MES' and ts >= '{day} 00:00+00' "
       f"and ts < '{day} 23:59+00' order by ts")
raw = subprocess.run([PSQL, "-d", "mems26", "-Atc", sql], capture_output=True, text=True).stdout
db = pd.read_csv(io.StringIO(raw), sep="|", header=None, names=cols.split(","))
mine = pd.read_csv(f); mine = mine[(mine["ts"] >= db["ts"].min()) & (mine["ts"] <= db["ts"].max())]
j = db.merge(mine, on="ts", suffixes=("_db", "_my"), how="outer", indicator=True)
print(f"{day}: db bars {len(db)} · mine {len(mine)} · matched {int((j['_merge']=='both').sum())} · db-only {int((j['_merge']=='left_only').sum())} · mine-only {int((j['_merge']=='right_only').sum())}")
b = j[j["_merge"] == "both"]
for ccol in ("open", "high", "low", "close", "volume", "cci_14", "cci_6_tcci", "lsma_value", "ema_34", "swi_value", "czi_value", "predictor_next_cci"):
    d = (b[ccol + "_my"].astype(float) - b[ccol + "_db"].astype(float))
    print(f"  {ccol:18s} max|Δ| {d.abs().max():10.3f} · mean|Δ| {d.abs().mean():8.3f} · exact {(d.abs() < 1e-6).mean()*100:5.1f}%")
for ccol in ("trend_state", "zlr_detected", "lsma_above_price"):
    a = b[ccol + "_db"].astype(str).str.lower(); m = b[ccol + "_my"].astype(str).str.lower()
    print(f"  {ccol:18s} agree {(a == m).mean()*100:5.1f}%  (db {dict(a.value_counts().head(4))} · mine {dict(m.value_counts().head(4))})")
