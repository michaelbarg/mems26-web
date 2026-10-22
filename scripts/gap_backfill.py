#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gap_backfill.py — fill RTH gaps in the LIVE DB (mems26) from Sierra's .scid tick files, for days the Mac slept or the
backend was down (12–16.10.2026 was the first case: a whole trading week with zero bars, zero decisions, zero trades).

What it does (read `--check` first, then `--apply`):
  1. Finds ET trading dates in the last --days weekdays with ZERO RTH bars in v9_bars_5min_woodies (gap dates) and
     confirms Sierra's front-contract .scid holds RTH ticks for them (Sierra backfills ticks from the provider on reconnect).
  2. Rebuilds 5-min bars from the .scid with the T-586 history pipeline (harness_out/t586/hist: build_bars.py →
     merge_studies.py [Woodies studies, DLL-reference formulas] → build_tpo_delta.py [30-min TPO snapshots, CASH/GLOBEX
     sessions, RTH delta]).
  3. Inserts ONLY rows for the gap dates, each guarded by NOT EXISTS / ON CONFLICT DO NOTHING — a live row is never
     overwritten:  v9_bars_5min_woodies · v9_bars_5min (OHLCV, 06:30–16:55 ET; vah/val/poc_vol/cumulative_delta NULL) ·
     v9_tpo_sessions (CASH + GLOBEX) · v9_tpo_history · v9_bars_cumulative_delta (source_version='scid').
  4. Writes one line at the top of docs/handoff/LIVE_CHANNEL.md; `--phone` also sends one phone message (argv, T-260).
  5. Battery guard: on battery below 40 % it says so (the 12.10 outage was 'Low Power Sleep' — the MacBook unplugged).

Caveat (T-590): the live TPO system's own CASH value areas are known-wrong on most days; the scid-built profile uses 30-min
letters and a 70 % value area around the POC (Dalton). The two differ by 10–20 pts on 08–09.10 — a backfilled CASH row is a
Dalton-style profile, not a copy of what the live system would have written.

usage: python3 scripts/gap_backfill.py [--check] [--apply] [--days=15] [--phone] [--force-rth] [--quiet]
exit 0 = ok / nothing to do · 1 = error · 3 = gaps found (check mode) · 4 = inside RTH, apply skipped
"""
import sys, os, re, glob, struct, subprocess, datetime as dt, collections
from zoneinfo import ZoneInfo

REPO = "/Users/michael/Downloads/mems26_web_git"
PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
DB = "mems26"
HIST = f"{REPO}/harness_out/t586/hist"
# T-632 (22.10, iMac): Sierra may run from a second bottle (~/SierraChart2 on the iMac) — honour SIERRA_SCID_DIR and
# otherwise look in every bottle's Data folder; front_scid() keeps the file with the newest tick, wherever it lives.
SCID_DIR = os.getenv("SIERRA_SCID_DIR") or "/Users/michael/SierraChart/Data"
SCID_DIRS = [d for d in dict.fromkeys([SCID_DIR, os.path.expanduser("~/SierraChart/Data"),
                                       os.path.expanduser("~/SierraChart2/Data")]) if os.path.isdir(d)]
ET, IL = ZoneInfo("America/New_York"), ZoneInfo("Asia/Jerusalem")
EPOCH = dt.datetime(1899, 12, 30)
opt = {a.split("=")[0][2:]: (a.split("=", 1)[1] if "=" in a else "1") for a in sys.argv[1:] if a.startswith("--")}
APPLY, PHONE, QUIET, FORCE = "apply" in opt, "phone" in opt, "quiet" in opt, "force-rth" in opt
DAYS = int(opt.get("days", "15"))


def say(*a):
    if not QUIET:
        print(*a, flush=True)


def q(sql, db=DB):
    r = subprocess.run([PSQL, "-d", db, "-v", "ON_ERROR_STOP=1", "-Atc", sql], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:400])
    return r.stdout.strip().splitlines()


def in_rth_il(now=None):
    now = now or dt.datetime.now(IL)
    return now.weekday() < 5 and dt.time(16, 0) <= now.time() < dt.time(23, 10)


# ---------- 1. gap detection ----------
def trading_dates(n):
    d = dt.datetime.now(ET).date(); out = []
    while len(out) < n:
        d -= dt.timedelta(days=1)
        if d.weekday() < 5:
            out.append(d)
    return sorted(out)


def rth_counts():
    rows = q("select (ts at time zone 'America/New_York')::date, count(*) from v9_bars_5min_woodies where symbol='MES' "
             "and (ts at time zone 'America/New_York')::time between '09:30' and '15:55' "
             f"and ts > now() - interval '{DAYS + 10} days' group by 1")
    return {dt.date.fromisoformat(r.split("|")[0]): int(r.split("|")[1]) for r in rows}


def cash_sessions():
    return {r for r in q("select trading_date from v9_tpo_sessions where session_type='CASH' and trading_date >= "
                         f"'{(dt.date.today() - dt.timedelta(days=DAYS + 10)).isoformat()}'")}


def front_scid():
    best = None
    for f in [p for d in SCID_DIRS for p in glob.glob(f"{d}/MES*_FUT_CME.scid")]:
        sz = os.path.getsize(f)
        if sz < 96:
            continue
        with open(f, "rb") as fh:
            fh.seek(sz - 40); t = struct.unpack("<q", fh.read(8))[0]
        last = EPOCH + dt.timedelta(microseconds=t)
        if best is None or last > best[1]:
            best = (f, last)
    return best


def scid_rth_ticks(path, dates):
    """RTH tick count per ET date (binary search to the first record of the window, then vectorised counting)."""
    import numpy as np
    def us(d, t):  # SCDateTime microseconds (UTC) of an ET wall-clock time
        return int((dt.datetime.combine(d, t, tzinfo=ET).astimezone(dt.timezone.utc).replace(tzinfo=None) - EPOCH).total_seconds() * 1e6)
    wins = [(us(d, dt.time(9, 30)), us(d, dt.time(16, 0)), d) for d in dates]
    lo_t, hi_t = wins[0][0], wins[-1][1]
    sz = os.path.getsize(path); n = (sz - 56) // 40
    per = collections.Counter()
    rec = np.dtype([("dt", "<i8"), ("rest", "V32")])
    with open(path, "rb") as fh:
        def ts_at(i):
            fh.seek(56 + i * 40); return struct.unpack("<q", fh.read(8))[0]
        a, b = 0, n
        while a < b:
            m = (a + b) // 2
            if ts_at(m) < lo_t: a = m + 1
            else: b = m
        fh.seek(56 + a * 40); done = a
        while done < n:
            arr = np.fromfile(fh, dtype=rec, count=min(2_000_000, n - done))
            if not len(arr):
                break
            done += len(arr); t = arr["dt"]
            for lo, hi, d in wins:
                per[d] += int(((t >= lo) & (t < hi)).sum())
            if t[-1] >= hi_t:
                break
    return per


def battery():
    try:
        out = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
        pct = re.search(r"(\d+)%", out); src = "AC" if "AC Power" in out else "Battery"
        return src, int(pct.group(1)) if pct else None
    except Exception:
        return "?", None


# ---------- 2+3. rebuild + load ----------
def psql_script(sql):
    r = subprocess.run([PSQL, "-d", DB, "-v", "ON_ERROR_STOP=1"], input=sql, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:600])
    return [l for l in r.stdout.splitlines() if l.startswith("INSERT")]


def rebuild_and_load(gaps, scid):
    import pandas as pd
    stamp = dt.datetime.now(IL).strftime("%Y%m%dT%H%M")
    wd = f"{REPO}/harness_out/gap_backfill/{stamp}"; os.makedirs(wd, exist_ok=True)
    contract = os.path.basename(scid).replace(".scid", "")
    say(f"[1/4] bars from {contract} …")
    subprocess.run([sys.executable, f"{HIST}/build_bars.py", scid, f"{wd}/{contract}.csv"], check=True, capture_output=True, text=True)
    say("[2/4] Woodies studies …")
    subprocess.run([sys.executable, f"{HIST}/merge_studies.py", f"{wd}/merged.csv", f"{wd}/{contract}.csv"], check=True, capture_output=True, text=True)
    m = pd.read_csv(f"{wd}/merged.csv")
    t = pd.to_datetime(m["ts"], unit="s", utc=True).dt.tz_convert(ET); m["etd"] = t.dt.date; m["ett"] = t.dt.time
    lo = int(dt.datetime.combine(min(gaps) - dt.timedelta(days=3), dt.time(0), tzinfo=dt.timezone.utc).timestamp())
    hi = int(dt.datetime.combine(max(gaps) + dt.timedelta(days=1), dt.time(0), tzinfo=dt.timezone.utc).timestamp())
    win = m[(m.ts >= lo) & (m.ts < hi)].copy(); win.drop(columns=["etd", "ett"]).to_csv(f"{wd}/merged_gap.csv", index=False)
    say("[3/4] TPO snapshots / sessions / delta …")
    os.makedirs(f"{wd}/derived", exist_ok=True)
    subprocess.run([sys.executable, f"{HIST}/build_tpo_delta.py", f"{wd}/merged_gap.csv", f"{wd}/derived"], check=True, capture_output=True, text=True)
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    gap_list = ",".join(f"'{d.isoformat()}'" for d in gaps)
    inserted = {}
    # --- woodies (full session bars of the gap ET dates) ---
    g = m[m["etd"].isin(set(gaps))]
    w = pd.DataFrame({"ts": pd.to_datetime(g["ts"], unit="s", utc=True).dt.strftime("%Y-%m-%d %H:%M:%S+00"), "symbol": "MES",
                      "open": g["open"], "high": g["high"], "low": g["low"], "close": g["close"], "volume": g["volume"].astype(int),
                      "cci_14": g["cci_14"], "cci_6_tcci": g["cci_6_tcci"], "lsma_value": g["lsma_value"], "swi_value": g["swi_value"],
                      "czi_value": g["czi_value"], "ema_34": g["ema_34"], "trend_state": g["trend_state"], "predictor_next_cci": g["predictor_next_cci"],
                      "zlr_detected": g["zlr_detected"].astype(bool).astype(int), "zlr_direction": g["zlr_direction"], "created_at": now,
                      "hfe_detected": 0, "hfe_direction": "NONE", "hfe_extreme_bars_ago": 0, "lsma_above_price": g["lsma_above_price"].astype(bool).astype(int)})
    w.to_csv(f"{wd}/woodies_load.csv", index=False); c = ",".join(w.columns)
    inserted["v9_bars_5min_woodies"] = psql_script(f"""BEGIN;
CREATE TEMP TABLE _g_w AS SELECT {c} FROM v9_bars_5min_woodies LIMIT 0;
\\copy _g_w ({c}) FROM '{wd}/woodies_load.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO v9_bars_5min_woodies ({c}) SELECT {c} FROM _g_w WHERE (ts AT TIME ZONE 'America/New_York')::date IN ({gap_list}) ON CONFLICT (ts, symbol) DO NOTHING;
COMMIT;""")
    # --- v9_bars_5min (S1/S2 table): OHLCV only, the live 06:30–16:55 ET window ---
    b = g[(g["ett"] >= dt.time(6, 30)) & (g["ett"] <= dt.time(16, 55))]
    b5 = pd.DataFrame({"ts": pd.to_datetime(b["ts"], unit="s", utc=True).dt.strftime("%Y-%m-%d %H:%M:%S+00"), "symbol": "MES",
                       "open": b["open"], "high": b["high"], "low": b["low"], "close": b["close"], "volume": b["volume"].astype(int),
                       "is_synthetic": 0, "created_at": now})
    b5.to_csv(f"{wd}/bars5_load.csv", index=False); c5 = ",".join(b5.columns)
    inserted["v9_bars_5min"] = psql_script(f"""BEGIN;
CREATE TEMP TABLE _g_b AS SELECT {c5} FROM v9_bars_5min LIMIT 0;
\\copy _g_b ({c5}) FROM '{wd}/bars5_load.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO v9_bars_5min ({c5}) SELECT {c5} FROM _g_b WHERE (ts AT TIME ZONE 'America/New_York')::date IN ({gap_list}) ON CONFLICT (ts, symbol) DO NOTHING;
COMMIT;""")
    # --- tpo_history (30-min snapshots of the gap dates) ---
    th = pd.read_csv(f"{wd}/derived/tpo_history.csv"); th["ts"] = th["created_at"]; th["profile_shape"] = ""
    th = th[["ts", "poc", "vah", "val", "ib_high", "ib_low", "profile_shape", "created_at"]]; th.to_csv(f"{wd}/tpo_history_load.csv", index=False)
    c2 = ",".join(th.columns)
    inserted["v9_tpo_history"] = psql_script(f"""BEGIN;
CREATE TEMP TABLE _g_t AS SELECT {c2} FROM v9_tpo_history LIMIT 0;
\\copy _g_t ({c2}) FROM '{wd}/tpo_history_load.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO v9_tpo_history ({c2}) SELECT {c2} FROM _g_t WHERE (_g_t.created_at::timestamptz AT TIME ZONE 'America/New_York')::date IN ({gap_list})
  AND NOT EXISTS (SELECT 1 FROM v9_tpo_history h WHERE (h.created_at AT TIME ZONE 'America/New_York')::date = (_g_t.created_at::timestamptz AT TIME ZONE 'America/New_York')::date)
  ON CONFLICT (ts) DO NOTHING;
COMMIT;""")
    # --- tpo_sessions (CASH + GLOBEX of the gap dates; never a date/type that already has a live row) ---
    ts_ = pd.read_csv(f"{wd}/derived/tpo_sessions.csv"); ts_["profile_shape"] = "NA"; ts_["ib_locked_ts"] = ts_["opened_ts"]
    ts_["ib_locked"] = ts_["ib_locked"].fillna(0).astype(int)
    c3 = "session_id,session_type,trading_date,opened_ts,poc_price,vah_price,val_price,range_high,range_low,total_volume,profile_shape,ib_high,ib_low,ib_locked,letter_count,ib_width,ib_class,ib_locked_ts"
    ts_[c3.split(",")].to_csv(f"{wd}/tpo_sessions_load.csv", index=False)
    inserted["v9_tpo_sessions"] = psql_script(f"""BEGIN;
CREATE TEMP TABLE _g_s AS SELECT {c3} FROM v9_tpo_sessions LIMIT 0;
\\copy _g_s ({c3}) FROM '{wd}/tpo_sessions_load.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO v9_tpo_sessions ({c3}) SELECT {c3} FROM _g_s WHERE trading_date IN ({gap_list})
  AND NOT EXISTS (SELECT 1 FROM v9_tpo_sessions h WHERE h.trading_date = _g_s.trading_date AND h.session_type = _g_s.session_type)
  ON CONFLICT (session_id) DO NOTHING;
COMMIT;""")
    # --- cumulative delta (RTH bars of the gap dates) ---
    dl = pd.read_csv(f"{wd}/derived/delta.csv")
    dl["ts_s"] = pd.to_datetime(dl["ts"], unit="s", utc=True).dt.strftime("%Y-%m-%d %H:%M:%S+00"); dl["bar_id"] = "scid_" + dl["ts"].astype(str)
    dl["session"] = "RTH"; dl["created_at"] = now; dl["symbol"] = "MES"; dl["source_version"] = "scid"
    c4 = "ts,bar_id,delta,cumulative,direction,session,created_at,symbol,source_version"
    dl.rename(columns={"ts": "ts_raw"}).rename(columns={"ts_s": "ts"})[c4.split(",")].to_csv(f"{wd}/delta_load.csv", index=False)
    inserted["v9_bars_cumulative_delta"] = psql_script(f"""BEGIN;
CREATE TEMP TABLE _g_d AS SELECT {c4} FROM v9_bars_cumulative_delta LIMIT 0;
\\copy _g_d ({c4}) FROM '{wd}/delta_load.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO v9_bars_cumulative_delta ({c4}) SELECT {c4} FROM _g_d WHERE (ts AT TIME ZONE 'America/New_York')::date IN ({gap_list})
  AND NOT EXISTS (SELECT 1 FROM v9_bars_cumulative_delta h WHERE h.ts = _g_d.ts AND h.symbol = 'MES') ON CONFLICT DO NOTHING;
COMMIT;""")
    say("[4/4] loaded:", {k: (v[-1] if v else "INSERT 0 0") for k, v in inserted.items()})
    return wd, {k: int((v[-1] if v else "INSERT 0 0").split()[-1]) for k, v in inserted.items()}


def note(line):
    p = f"{REPO}/docs/handoff/LIVE_CHANNEL.md"
    try:
        old = open(p, encoding="utf-8").read()
        open(p, "w", encoding="utf-8").write(line + "\n\n" + old)
    except Exception as e:
        say("LIVE_CHANNEL note failed:", e)


def main():
    src, pct = battery()
    batt = f"{src} {pct}%" if pct is not None else src
    dates = trading_dates(DAYS)
    have = rth_counts(); cash = cash_sessions()
    scid = front_scid()
    if not scid:
        print("no MES .scid found"); return 1
    cands = [d for d in dates if have.get(d, 0) < 78]
    if not cands:   # the cheap path for the 30-min LaunchAgent run: no DB holes → no 30-second .scid scan
        print(f"gap_backfill {dt.datetime.now(IL):%Y-%m-%d %H:%M} IL · battery {batt} · all {len(dates)} trading days have 78 RTH bars — nothing to do", flush=True)
        if src == "Battery" and pct is not None and pct < 40:
            say(f"⚠️ on battery {pct}% — the 12.10 outage was 'Low Power Sleep'; plug the MacBook in")
        return 0
    ticks = scid_rth_ticks(scid[0], dates)
    # a gap date = fewer than the 78 RTH bars of a full session (zero = the Mac slept; partial = feed/ingest cut) and
    # the .scid has the ticks; every insert is NOT EXISTS / ON CONFLICT DO NOTHING, so a partial day only gains its holes
    gaps = [d for d in dates if have.get(d, 0) < 78 and ticks.get(d, 0) >= 1000]
    closed = [d for d in dates if have.get(d, 0) == 0 and ticks.get(d, 0) < 1000]
    partial = [d for d in gaps if have.get(d, 0) > 0]
    say(f"gap_backfill {dt.datetime.now(IL):%Y-%m-%d %H:%M} IL · battery {batt} · scid {os.path.basename(scid[0])} (last {scid[1]:%Y-%m-%d %H:%M} UTC)")
    for d in dates:
        say(f"  {d} {d.strftime('%a')}: woodies RTH bars {have.get(d, 0):>2} · CASH session {'yes' if d.isoformat() in cash else 'NO '} · scid RTH ticks {ticks.get(d, 0):>7}"
            + ("  ← GAP (partial)" if d in partial else "  ← GAP" if d in gaps else "  (market closed / no ticks)" if d in closed else ""))
    if src == "Battery" and pct is not None and pct < 40:
        say(f"⚠️ on battery {pct}% — the 12.10 outage was 'Low Power Sleep'; plug the MacBook in")
    if not gaps:
        say("no gap dates — nothing to do"); return 0
    if not APPLY:
        say(f"check only — {len(gaps)} gap date(s): {', '.join(d.isoformat() for d in gaps)} (run with --apply)"); return 3
    if in_rth_il() and not FORCE:
        say("inside RTH (16:00–23:10 IL) — apply skipped (use --force-rth to override)"); return 4
    wd, ins = rebuild_and_load(gaps, scid[0])
    summary = " · ".join(f"{k.replace('v9_', '')} +{v}" for k, v in ins.items())
    line = (f"## {dt.datetime.now(IL):%Y-%m-%d %H:%M} IL · gap_backfill · {len(gaps)} ימים חסרים/חלקיים ({', '.join(d.strftime('%d.%m') for d in gaps)}) "
            f"שוחזרו מ-{os.path.basename(scid[0])} ל-mems26 (NOT EXISTS/ON CONFLICT בלבד): {summary} · workdir {wd.replace(REPO + '/', '')}")
    note(line); say(line)
    if PHONE:
        msg = f"gap_backfill: {len(gaps)} ימים חסרים/חלקיים ({', '.join(d.strftime('%d.%m') for d in gaps)}) שוחזרו מסיירה ל-DB: {summary}. סוללה {batt}."
        subprocess.run([sys.executable, f"{REPO}/scripts/phone_reply.py", msg], capture_output=True, text=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("gap_backfill ERROR:", e); sys.exit(1)
