"""Direction-signal bake-off on 06-23: LSMA-only vs CVD-only vs Combined.

Per RTH 5-min bar, derive a direction signal three ways, then mark-to-market the
signal over the NEXT bar (position = signal, pnl += signal * (close[i+1]-close[i])).
3 MES, $15/pt. READ-ONLY, reads the portable JSON (no DB).

Signals (per bar i):
  CVD-only  : sign(cvd[i] - cvd[i-3])     +1 up / -1 down / 0 flat   (engine cvd_slope, lookback 3)
  LSMA-only : +1 if close>lsma else -1    (price vs the LSMA line — "which side")
  Combined  : AND — take the direction only when CVD-sign == LSMA-side; else FLAT
              (also report the 'LSMA-trend + CVD-confirm' priority mode for reference)
Run: python3 outputs/direction_compare_2026-06-23.py
"""
import json, os
from pathlib import Path

HERE = Path(__file__).resolve().parent
d = json.load(open(HERE / "sim_data_2026-06-23.json"))
bars = d["bars"]
USD = 15.0
LB = 3


def sign(x):
    return 1 if x > 0 else (-1 if x < 0 else 0)


def evaluate(name, sigfn):
    pts = 0.0; up = dn = nz = 0; hit = 0; decided = 0
    for i in range(len(bars) - 1):
        s = sigfn(i)
        if s > 0: up += 1
        elif s < 0: dn += 1
        else: nz += 1
        fwd = float(bars[i + 1]["close"]) - float(bars[i]["close"])
        pts += s * fwd
        if s != 0:
            decided += 1
            if s * fwd > 0:
                hit += 1
    hr = (100.0 * hit / decided) if decided else 0
    return name, up, dn, nz, hr, pts, pts * USD


def cvd_dir(i):
    if i < LB:
        return 0
    a = bars[i].get("cvd"); b = bars[i - LB].get("cvd")
    if a is None or b is None:
        return 0
    return sign(float(a) - float(b))


def lsma_dir(i):
    return 1 if float(bars[i]["close"]) > float(bars[i]["lsma"]) else -1


def combined_and(i):
    c, l = cvd_dir(i), lsma_dir(i)
    return l if (c != 0 and c == l) else 0


def combined_priority(i):
    # LSMA sets the trend; CVD only blocks when it strongly fights (stays with LSMA otherwise)
    c, l = cvd_dir(i), lsma_dir(i)
    return 0 if c == -l else l   # flat only when CVD directly opposes the LSMA side


def combined_cvd_lead_lsma_veto(i):
    # CVD sets the direction; LSMA is the VETO — flat when the LSMA side opposes CVD
    # (or when CVD is silent). LSMA has no neutral state, so it can only agree or oppose.
    c, l = cvd_dir(i), lsma_dir(i)
    if c == 0:
        return 0
    return 0 if l == -c else c


rows = [
    evaluate("LSMA-only (price vs line)", lsma_dir),
    evaluate("CVD-only  (3-bar slope)", cvd_dir),
    evaluate("Combined AND (both agree)", combined_and),
    evaluate("Combined  (LSMA trend + CVD veto)", combined_priority),
    evaluate("Combined  (CVD lead + LSMA veto)", combined_cvd_lead_lsma_veto),
]

def trades_eval(name, sigfn):
    """Group consecutive same-direction bars into TRADES (a trade = a run of one
    direction; it ends when the signal flips or goes flat). Count win/lose trades."""
    sigs = [sigfn(i) for i in range(len(bars) - 1)]
    n = len(sigs); i = 0
    trades = winning = losing = scratch = 0; pnl = 0.0
    while i < n:
        s = sigs[i]
        if s == 0:
            i += 1; continue
        j = i
        while j < n and sigs[j] == s:
            j += 1
        tp = s * (float(bars[j]["close"]) - float(bars[i]["close"]))  # entry close[i] → exit close[j]
        trades += 1; pnl += tp
        if tp > 0: winning += 1
        elif tp < 0: losing += 1
        else: scratch += 1
        i = j
    wr = (100.0 * winning / trades) if trades else 0
    return name, trades, winning, losing, scratch, wr, pnl * USD


trows = [
    trades_eval("LSMA-only (price vs line)", lsma_dir),
    trades_eval("CVD-only  (3-bar slope)", cvd_dir),
    trades_eval("Combined AND / LSMA-as-veto", combined_and),
    trades_eval("Combined  (LSMA lead + CVD veto)", combined_priority),
]

net = float(bars[-1]["close"]) - float(bars[0]["close"])
print(f"06-23 RTH: {len(bars)} bars · net close-to-close {net:+.2f} pts\n")
print(f"{'signal':34} {'UP':>3} {'DN':>3} {'flat':>4} {'hit%':>5} {'pts':>8} {'$ (3MES)':>9}")
print("-" * 72)
for nm, up, dn, nz, hr, pts, usd in rows:
    print(f"{nm:34} {up:>3} {dn:>3} {nz:>4} {hr:>4.0f}% {pts:>8.1f} {usd:>+9.0f}")

print(f"\nTRADES (runs until the signal flips/goes flat):")
print(f"{'signal':34} {'trades':>6} {'win':>4} {'LOSE':>5} {'scr':>4} {'win%':>5} {'$ (3MES)':>9}")
print("-" * 76)
for nm, t, w, l, sc, wr, usd in trows:
    print(f"{nm:34} {t:>6} {w:>4} {l:>5} {sc:>4} {wr:>4.0f}% {usd:>+9.0f}")
