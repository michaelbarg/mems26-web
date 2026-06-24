"""Per-bar simulation for one RTH day: combines volume + day-type + LSMA +
all pattern fires + the LSMA mean-reversion strategy (Michael's rule: LONG below
LSMA / SHORT above, one-at-a-time, exit on LSMA cross), one row per 5-min bar.

Writes tools/per_bar_sim_<date>.md. READ-ONLY on the DB.
Run: PYTHONPATH=<repo> SIM_DATE=2026-06-23 python3 tools/per_bar_sim.py
"""
import os
from pathlib import Path
from sqlalchemy import create_engine, text

eng = create_engine(os.environ.get("DATABASE_URL", "postgresql://localhost/mems26"))
DATE = os.environ.get("SIM_DATE", "2026-06-23")
USD_PER_PT = 15.0  # 3 MES contracts

BARS = text("""select to_char(ts AT TIME ZONE 'America/Chicago','HH24:MI') ct,
                      open o, high h, low l, close c, volume v,
                      cci_14, lsma_value, trend_state, swi_value,
                      zlr_detected, hfe_detected
               from v9_bars_5min_woodies
               where (ts AT TIME ZONE 'America/Chicago')::date = :d
                 and (ts AT TIME ZONE 'America/Chicago')::time between '08:30' and '15:00'
               order by ts""")
FIRES = text("""select to_char(entry_ts AT TIME ZONE 'America/Chicago','HH24:MI') ct,
                       direction, pattern_id_at_entry pid, firing_system fs
                from v9_trades
                where (entry_ts AT TIME ZONE 'America/Chicago')::date = :d and mode='shadow'
                order by entry_ts""")

with eng.connect() as c:
    bars = [dict(r) for r in c.execute(BARS, {"d": DATE}).mappings()]
    fires = [dict(r) for r in c.execute(FIRES, {"d": DATE}).mappings()]

if not bars:
    print(f"NO RTH bars for {DATE} (session not open yet?). Nothing to simulate.")
    raise SystemExit(0)

# fires grouped by bar-time
from collections import defaultdict
fmap = defaultdict(list)
for f in fires:
    fmap[f["ct"]].append(f"{f['pid'] or '?'}/{(f['direction'] or '')[0]}")

# rolling-20 volume avg for the HIGH/LOW flag
vols = [float(b["v"] or 0) for b in bars]
IB_LOCK_BARS = 12  # 60 min

pos = None          # None / "LONG" / "SHORT"
entry_px = None
strat_pts = 0.0
trades = 0

rows = []
for i, b in enumerate(bars):
    close = float(b["c"]); lsma = float(b["lsma_value"] or close); v = float(b["v"] or 0)
    avg20 = sum(vols[max(0, i - 20):i]) / max(1, len(vols[max(0, i - 20):i])) if i else v
    vflag = "HIGH" if (avg20 and v > 1.5 * avg20) else ("low" if (avg20 and v < 0.5 * avg20) else "")
    zone = "BELOW" if close < lsma else "ABOVE"            # price vs LSMA
    want = "LONG" if zone == "BELOW" else "SHORT"           # Michael's rule: long below / short above
    day_type = "FORMING" if i < IB_LOCK_BARS else "Normal"  # canonical 06-23 (FORMING→Normal at IB lock)
    pats = ",".join(fmap.get(b["ct"], []))

    action = ""
    # exit first: LSMA cross to the opposite side
    if pos == "LONG" and close > lsma:
        strat_pts += (close - entry_px); trades += 1; action = f"EXIT L ({close - entry_px:+.2f})"; pos = None
    elif pos == "SHORT" and close < lsma:
        strat_pts += (entry_px - close); trades += 1; action = f"EXIT S ({entry_px - close:+.2f})"; pos = None
    # entry: a fire this bar aligned with the LSMA zone, and flat
    if pos is None and pats:
        for f in fmap[b["ct"]]:
            fdir = "LONG" if f.endswith("/L") else "SHORT" if f.endswith("/S") else None
            if fdir == want:
                pos = fdir; entry_px = close; action = (action + " " if action else "") + f"ENTER {fdir[0]}@{close:.2f}"
                break
    state = pos[0] if pos else "·"
    rows.append((b["ct"], close, int(v), vflag, day_type, round(lsma, 2), zone,
                 round(float(b["cci_14"] or 0), 0), (b["trend_state"] or ""), pats, f"{state} {action}".strip()))

# close any open position at EOD
if pos:
    last = float(bars[-1]["c"])
    strat_pts += (last - entry_px) if pos == "LONG" else (entry_px - last)
    trades += 1

out = [f"# Per-bar simulation — {DATE} (RTH 08:30–15:00 CT)", "",
       f"_All patterns + volume + day-type + LSMA mean-reversion (LONG below LSMA / SHORT above, "
       f"one-at-a-time, exit on LSMA cross). {len(bars)} bars, {len(fires)} fires._", "",
       f"**LSMA strategy result: {trades} trades, {strat_pts:+.1f} pts (~${strat_pts*USD_PER_PT:+.0f} @ 3 contracts).**", "",
       "| time | close | vol | | day_type | LSMA | P vs LSMA | CCI | trend | fires | strategy |",
       "|------|-------|-----|--|----------|------|-----------|-----|-------|-------|----------|"]
for r in rows:
    out.append("| {} | {:.2f} | {:,} | {} | {} | {} | {} | {:.0f} | {} | {} | {} |".format(*r))

p = Path(__file__).resolve().parent / f"per_bar_sim_{DATE}.md"
p.write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"wrote {p}")
print(f"{len(bars)} RTH bars · {len(fires)} fires · LSMA strategy {trades} trades {strat_pts:+.1f} pts "
      f"(~${strat_pts*USD_PER_PT:+.0f})")
