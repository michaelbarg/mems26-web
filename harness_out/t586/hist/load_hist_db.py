#!/usr/bin/env python3
"""T-586 · step 5 — load the reconstructed history into the SEPARATE database mems26_hist (never into mems26):
rows are inserted only where the live copy has none (ON CONFLICT DO NOTHING on the natural keys), so the overlap
period stays the live data and every new session is history. usage: load_hist_db.py <merged.csv> <derived_dir>"""
import sys, subprocess, datetime, pandas as pd, numpy as np
PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"; DB = "mems26_hist"
src, dd = sys.argv[1], sys.argv[2]
def run(sql):
    r = subprocess.run([PSQL, "-d", DB, "-v", "ON_ERROR_STOP=1", "-Atc", sql], capture_output=True, text=True)
    if r.returncode != 0:
        print("SQL FAILED:", r.stderr.strip()[:600]); sys.exit(1)
    return r.stdout.strip()
m = pd.read_csv(src)
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
w = pd.DataFrame({"ts": pd.to_datetime(m["ts"], unit="s", utc=True).dt.strftime("%Y-%m-%d %H:%M:%S+00"), "symbol": "MES",
                  "open": m["open"], "high": m["high"], "low": m["low"], "close": m["close"], "volume": m["volume"].astype(int),
                  "cci_14": m["cci_14"], "cci_6_tcci": m["cci_6_tcci"], "lsma_value": m["lsma_value"], "swi_value": m["swi_value"],
                  "czi_value": m["czi_value"], "ema_34": m["ema_34"], "trend_state": m["trend_state"], "predictor_next_cci": m["predictor_next_cci"],
                  "zlr_detected": m["zlr_detected"].astype(bool).astype(int), "zlr_direction": m["zlr_direction"], "created_at": now,
                  "hfe_detected": 0, "hfe_direction": "NONE", "hfe_extreme_bars_ago": 0, "lsma_above_price": m["lsma_above_price"].astype(bool).astype(int)})
w.to_csv(f"{dd}/woodies_load.csv", index=False)
cols = ",".join(w.columns)
run("DROP TABLE IF EXISTS _hist_w; CREATE TEMP TABLE _hist_w AS SELECT " + cols + " FROM v9_bars_5min_woodies LIMIT 0;")
# psql \copy needs one session: do the temp table + copy + insert in a single -c script
script = f"""BEGIN;
CREATE TEMP TABLE _hist_w AS SELECT {cols} FROM v9_bars_5min_woodies LIMIT 0;
\\copy _hist_w ({cols}) FROM '{dd}/woodies_load.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO v9_bars_5min_woodies ({cols}) SELECT {cols} FROM _hist_w ON CONFLICT (ts, symbol) DO NOTHING;
COMMIT;"""
open(f"{dd}/load_woodies.sql", "w").write(script)
r = subprocess.run([PSQL, "-d", DB, "-v", "ON_ERROR_STOP=1", "-f", f"{dd}/load_woodies.sql"], capture_output=True, text=True)
print("woodies:", r.stdout.strip().splitlines()[-2:] if r.returncode == 0 else r.stderr[:500])
# tpo_history
th = pd.read_csv(f"{dd}/tpo_history.csv"); th["ts"] = th["created_at"]; th["profile_shape"] = ""
th = th[["ts", "poc", "vah", "val", "ib_high", "ib_low", "profile_shape", "created_at"]]; th.to_csv(f"{dd}/tpo_history_load.csv", index=False)
c2 = "ts,poc,vah,val,ib_high,ib_low,profile_shape,created_at"
open(f"{dd}/load_tpo.sql", "w").write(f"""BEGIN;
CREATE TEMP TABLE _hist_t AS SELECT {c2} FROM v9_tpo_history LIMIT 0;
\\copy _hist_t ({c2}) FROM '{dd}/tpo_history_load.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO v9_tpo_history ({c2}) SELECT {c2} FROM _hist_t WHERE NOT EXISTS (SELECT 1 FROM v9_tpo_history h WHERE (h.created_at AT TIME ZONE 'UTC')::date = (_hist_t.created_at AT TIME ZONE 'UTC')::date) ON CONFLICT (ts) DO NOTHING;
COMMIT;""")
r = subprocess.run([PSQL, "-d", DB, "-v", "ON_ERROR_STOP=1", "-f", f"{dd}/load_tpo.sql"], capture_output=True, text=True)
print("tpo_history:", r.stdout.strip().splitlines()[-2:] if r.returncode == 0 else r.stderr[:500])

# tpo_sessions (CASH + GLOBEX per trading date; only dates with no live row of that session_type)
ts_ = pd.read_csv(f"{dd}/tpo_sessions.csv"); ts_["profile_shape"] = "NA"; ts_["ib_locked_ts"] = ts_["opened_ts"]
ts_["ib_locked"] = ts_["ib_locked"].fillna(0).astype(int)
c3 = "session_id,session_type,trading_date,opened_ts,poc_price,vah_price,val_price,range_high,range_low,total_volume,profile_shape,ib_high,ib_low,ib_locked,letter_count,ib_width,ib_class,ib_locked_ts"
ts_[c3.split(",")].to_csv(f"{dd}/tpo_sessions_load.csv", index=False)
open(f"{dd}/load_sess.sql", "w").write(f"""BEGIN;
CREATE TEMP TABLE _hist_s AS SELECT {c3} FROM v9_tpo_sessions LIMIT 0;
\\copy _hist_s ({c3}) FROM '{dd}/tpo_sessions_load.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO v9_tpo_sessions ({c3}) SELECT {c3} FROM _hist_s WHERE NOT EXISTS (SELECT 1 FROM v9_tpo_sessions h WHERE h.trading_date = _hist_s.trading_date AND h.session_type = _hist_s.session_type) ON CONFLICT (session_id) DO NOTHING;
COMMIT;""")
r = subprocess.run([PSQL, "-d", DB, "-v", "ON_ERROR_STOP=1", "-f", f"{dd}/load_sess.sql"], capture_output=True, text=True)
print("tpo_sessions:", r.stdout.strip().splitlines()[-2:] if r.returncode == 0 else r.stderr[:500])
# cumulative delta (only ts with no live MES row)
dl = pd.read_csv(f"{dd}/delta.csv")
dl["ts_s"] = pd.to_datetime(dl["ts"], unit="s", utc=True).dt.strftime("%Y-%m-%d %H:%M:%S+00"); dl["bar_id"] = "hist_" + dl["ts"].astype(str)
dl["session"] = "RTH"; dl["created_at"] = now; dl["symbol"] = "MES"; dl["source_version"] = "hist"
c4 = "ts,bar_id,delta,cumulative,direction,session,created_at,symbol,source_version"
d2 = dl.rename(columns={"ts": "ts_raw"}).rename(columns={"ts_s": "ts"})[c4.split(",")]; d2.to_csv(f"{dd}/delta_load.csv", index=False)
open(f"{dd}/load_delta.sql", "w").write(f"""BEGIN;
CREATE TEMP TABLE _hist_d AS SELECT {c4} FROM v9_bars_cumulative_delta LIMIT 0;
\\copy _hist_d ({c4}) FROM '{dd}/delta_load.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO v9_bars_cumulative_delta ({c4}) SELECT {c4} FROM _hist_d WHERE NOT EXISTS (SELECT 1 FROM v9_bars_cumulative_delta h WHERE h.ts = _hist_d.ts AND h.symbol = 'MES') ON CONFLICT DO NOTHING;
COMMIT;""")
r = subprocess.run([PSQL, "-d", DB, "-v", "ON_ERROR_STOP=1", "-f", f"{dd}/load_delta.sql"], capture_output=True, text=True)
print("delta:", r.stdout.strip().splitlines()[-2:] if r.returncode == 0 else r.stderr[:500])
print("counts:", run("select (select count(*) from v9_bars_5min_woodies where symbol='MES'), (select count(*) from v9_tpo_history), (select count(*) from v9_tpo_sessions), (select count(*) from v9_bars_cumulative_delta where symbol='MES')"))
