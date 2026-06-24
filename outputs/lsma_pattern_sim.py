"""LSMA-flip strategy with S1/S2/S4 filters — portable engine (Michael 2026-06-23).

Michael's rule (exact): start LONG with the opening drive; at each LSMA cross FLIP
the position (LONG above the LSMA / SHORT below). Exit ONLY at a flip. The flip's
NEW-direction entry is gated by optional filters; when a filter blocks it we go FLAT
and record the missed flip + which patterns were available there ("if it doesn't
trade, which patterns could have fired").

Reads a portable JSON (no DB needed) so agents can run it in-sandbox:
  bars : [{ct, close, lsma, trend, vol, cvd, cci, dt}]   (RTH 08:30–15:00 CT)
  fires: [{ct, sys, dir, pid, dt, px, pnl}]   (all S2+S4 fires we have for the day)

Filters via env (default = raw base, no filter):
  DIRRULE   = trend (long above) | meanrev (long below)         [default trend]
  OPEN_SEED = 1 seed the opening-drive position at bar 0 | 0     [default 1]
  REQ_PATTERN=1  only take a flip if an aligned S2/S4 fire is within PAT_WIN bars
  PAT_WIN   = N bars window (default 2)
  PAT_SET   = csv of allowed patterns (e.g. ZLR,TLB,REACTIVE_SHORT); empty = any
  SYS_SET   = csv of systems to use as entries (2,4); empty = both
  DT_OK     = csv of allowed day-types (e.g. Normal,Opening); empty = any
  REQ_TREND = 1 require trend_state aligns (BLUE long / RED short)
  REQ_CVD   = 1 require CVD slope (over CVD_WIN bars) aligns with the new direction
  CVD_WIN   = bars for the CVD slope (default 1)
  TRACE     = 1 also write a per-bar markdown trace next to the data file
P&L in points; $ at $15/pt (3 MES). READ-ONLY.
Run: SIM_DATA=outputs/sim_data_2026-06-23.json [filters...] python3 outputs/lsma_pattern_sim.py
"""
import os, json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = os.environ.get("SIM_DATA", str(HERE / "sim_data_2026-06-23.json"))
USD = 15.0
DIRRULE = os.environ.get("DIRRULE", "trend")
OPEN_SEED = os.environ.get("OPEN_SEED", "1") == "1"
REQ_PATTERN = os.environ.get("REQ_PATTERN", "0") == "1"
PAT_WIN = int(os.environ.get("PAT_WIN", "2"))
PAT_SET = set(p for p in os.environ.get("PAT_SET", "").split(",") if p)
SYS_SET = set(int(s) for s in os.environ.get("SYS_SET", "").split(",") if s.strip())
DT_OK = set(p for p in os.environ.get("DT_OK", "").split(",") if p)
REQ_TREND = os.environ.get("REQ_TREND", "0") == "1"
REQ_CVD = os.environ.get("REQ_CVD", "0") == "1"
CVD_WIN = int(os.environ.get("CVD_WIN", "1"))
TRACE = os.environ.get("TRACE", "0") == "1"

d = json.load(open(DATA))
bars = d["bars"]
fires = d["fires"]
DATE = d.get("date", "?")
if len(bars) < 2:
    print(f"NO bars in {DATA}"); raise SystemExit(0)

# fires grouped by bar-time -> list of (pid, dir, sys)
fmap = defaultdict(list)
for f in fires:
    fmap[f["ct"]].append((f["pid"] or "?", (f["dir"] or "").upper(), int(f.get("sys") or 0)))


def side(b):
    return "A" if float(b["close"]) > float(b["lsma"]) else "B"   # Above / Below LSMA


def newdir_for(s):
    if DIRRULE == "meanrev":
        return "SHORT" if s == "A" else "LONG"
    return "LONG" if s == "A" else "SHORT"          # trend: above=LONG


def patterns_near(i, direction=None):
    """Patterns within PAT_WIN bars up to i; optionally filtered to a direction,
    to PAT_SET, and to SYS_SET."""
    out = []
    for j in range(max(0, i - PAT_WIN), i + 1):
        for pid, dr, sy in fmap.get(bars[j]["ct"], []):
            if direction and dr != direction:
                continue
            if PAT_SET and pid not in PAT_SET:
                continue
            if SYS_SET and sy not in SYS_SET:
                continue
            out.append(f"{pid}/{dr[0] if dr else '?'}")
    return out


def cvd_aligns(i, direction):
    if i - CVD_WIN < 0:
        return True
    slope = float(bars[i]["cvd"]) - float(bars[i - CVD_WIN]["cvd"])
    if slope == 0:
        return True
    return (slope > 0) == (direction == "LONG")


pos = entry = None
pnl = 0.0; trades = 0; win = 0
missed = []
trace_rows = []
prev_side = side(bars[0])
if OPEN_SEED:
    pos, entry = newdir_for(prev_side), float(bars[0]["close"])   # opening-drive seed


def gate(i, nd):
    """Return (ok, reason). All active filters must pass."""
    b = bars[i]
    if REQ_PATTERN and not patterns_near(i, nd):
        return False, "no-pattern"
    if DT_OK and b.get("dt") not in DT_OK:
        return False, f"dt={b.get('dt')}"
    if REQ_TREND:
        need = "BLUE" if nd == "LONG" else "RED"
        if (b.get("trend") or "").upper() != need:
            return False, f"trend={b.get('trend')}"
    if REQ_CVD and not cvd_aligns(i, nd):
        return False, "cvd-against"
    return True, "ok"


for i in range(1, len(bars)):
    b = bars[i]
    s = side(b)
    action = ""
    if s != prev_side:                       # ── FLIP ──
        if pos:
            p = (float(b["close"]) - entry) if pos == "LONG" else (entry - float(b["close"]))
            pnl += p; trades += 1; win += 1 if p > 0 else 0
            action = f"EXIT {pos[0]} {p:+.2f}"
            pos = None
        nd = newdir_for(s)
        ok, why = gate(i, nd)
        if ok:
            pos, entry = nd, float(b["close"])
            action += f" | ENTER {nd[0]}@{b['close']:.2f}"
        else:
            avail = patterns_near(i, nd) or [f"{p}/{dr[0]}" for p, dr, _ in fmap.get(b["ct"], [])]
            missed.append((b["ct"], nd, why, avail))
            action += f" | FLAT ({why})"
    pats = ",".join(f"{p}/{dr[0] if dr else '?'}" for p, dr, _ in fmap.get(b["ct"], []))
    trace_rows.append((b["ct"], float(b["close"]), b.get("lsma"), "A" if s == "A" else "B",
                       b.get("trend"), b.get("dt"), int(b.get("vol") or 0), b.get("cvd"),
                       pats, (pos[0] if pos else "·") + (" " + action if action else "")))
    prev_side = s

if pos:                                      # close at EOD
    last = float(bars[-1]["close"])
    p = (last - entry) if pos == "LONG" else (entry - last)
    pnl += p; trades += 1; win += 1 if p > 0 else 0

cfg = (f"DIRRULE={DIRRULE} OPEN_SEED={int(OPEN_SEED)} REQ_PATTERN={int(REQ_PATTERN)} "
       f"PAT_SET={','.join(sorted(PAT_SET)) or '-'} SYS={','.join(map(str,sorted(SYS_SET))) or 'all'} "
       f"DT_OK={','.join(sorted(DT_OK)) or '-'} REQ_TREND={int(REQ_TREND)} REQ_CVD={int(REQ_CVD)}")
wr = (100.0 * win / trades) if trades else 0
print(f"[{DATE}] {cfg}")
print(f"  -> {trades} trades, {wr:.0f}% win, {pnl:+.1f} pts (~${pnl*USD:+.0f}) | {len(missed)} flips blocked")
for m in missed:
    print(f"     blocked flip {m[0]} {m[1]:<5} [{m[2]}]  patterns available = {m[3] or 'none'}")

if TRACE:
    out = [f"# Per-bar trace — {DATE}", "", f"`{cfg}`", "",
           f"**Result: {trades} trades, {wr:.0f}% win, {pnl:+.1f} pts (~${pnl*USD:+.0f}).**", "",
           "| time | close | LSMA | side | trend | day_type | vol | CVD | fires | position / action |",
           "|------|-------|------|------|-------|----------|-----|-----|-------|-------------------|"]
    for r in trace_rows:
        out.append("| {} | {:.2f} | {} | {} | {} | {} | {:,} | {} | {} | {} |".format(*r))
    tp = HERE / f"lsma_trace_{DATE}.md"
    tp.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"  wrote {tp}")
