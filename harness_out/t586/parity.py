#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-586 — daily parity: the system's own books (mode=live|demo) vs the frozen-config replay, trade by trade.
Generalises recon.py: reads v9_trades directly (psql), any date range, any mode. Read-only.
usage: parity.py --mode demo --from 2026-10-19 --to 2026-10-19 [--ref rc1] [--detail]
exit code 0 always; prints the per-session table + the leak categories (both / live-only / replay-only / rejected)."""
import argparse, subprocess, os, sys, io
ap = argparse.ArgumentParser()
ap.add_argument("--mode", default="demo"); ap.add_argument("--from", dest="d0", required=True)
ap.add_argument("--to", dest="d1", required=True); ap.add_argument("--ref", default="t567ref")
ap.add_argument("--detail", action="store_true")
a = ap.parse_args()
PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
ROOT = "/Users/michael/Downloads/mems26_web_git"
q = ("select id, firing_system, direction, state, to_char(entry_ts at time zone 'Asia/Jerusalem','MM-DD HH24:MI:SS') e, "
     "entry_price, stop, t1, to_char(exit_ts at time zone 'Asia/Jerusalem','HH24:MI:SS') x, exit_price, exit_reason, pnl_usd, "
     "pnl_sierra, pattern_id_at_entry, day_type_at_entry, session_at_entry from v9_trades where mode='%s' "
     "and (entry_ts at time zone 'Asia/Jerusalem')::date between '%s' and '%s' order by id" % (a.mode, a.d0, a.d1))
out = subprocess.run([PSQL, "-d", "mems26", "-Atc", q], capture_output=True, text=True)
if out.returncode != 0:
    print("psql failed:", out.stderr.strip()); sys.exit(0)
psv = f"{ROOT}/harness_out/t586/live_trades.psv"
io.open(psv, "w", encoding="utf-8").write(out.stdout)
# recon.py reads the psv + harness_out/t466/<REF>_<d>.json and prints the categories
argv = [sys.executable, f"{ROOT}/harness_out/t586/recon.py", a.ref] + (["--detail"] if a.detail else [])
print("mode=%s %s..%s rows=%d · ref=%s" % (a.mode, a.d0, a.d1, len([l for l in out.stdout.splitlines() if l.strip()]), a.ref))
os.environ["RECON_FROM"], os.environ["RECON_TO"] = a.d0, a.d1
sys.stdout.flush()
os.execv(sys.executable, argv)
