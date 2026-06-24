"""Which trades lost on 06-23, and which pattern(s) fired in each losing window.
LSMA-only direction (price vs line) — Michael's base rule. READ-ONLY, reads the JSON.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
d = json.load(open(HERE / "sim_data_2026-06-23.json"))
bars = d["bars"]; fires = d["fires"]; USD = 15.0


def lsma_side(b):
    return 1 if float(b["close"]) > float(b["lsma"]) else -1


# build LSMA-only trades (runs of the same side) over bars[i]->bars[i+1]
sides = [lsma_side(b) for b in bars]
trades = []
i = 0
n = len(bars)
while i < n - 1:
    s = sides[i]
    j = i
    while j < n - 1 and sides[j] == s:
        j += 1
    entry, exit_ = bars[i], bars[j]
    pnl = s * (float(exit_["close"]) - float(entry["close"])) * USD
    trades.append({"dir": "LONG" if s > 0 else "SHORT", "i": i, "j": j,
                   "entry_ct": entry["ct"], "exit_ct": exit_["ct"],
                   "entry_px": float(entry["close"]), "exit_px": float(exit_["close"]), "pnl": pnl})
    i = j


def fires_in(a_ct, b_ct):
    return [f for f in fires if a_ct <= f["ct"] <= b_ct]


print(f"LSMA-only trades on 06-23: {len(trades)} total\n")
for t in trades:
    tag = "LOSS" if t["pnl"] < 0 else ("win " if t["pnl"] > 0 else "flat")
    print(f"[{tag}] {t['entry_ct']}->{t['exit_ct']} {t['dir']:5} "
          f"{t['entry_px']:.2f}->{t['exit_px']:.2f}  ${t['pnl']:+.0f}")

print("\n=== LOSING trades — who fired in each window ===")
for t in trades:
    if t["pnl"] >= 0:
        continue
    fs = fires_in(t["entry_ct"], t["exit_ct"])
    print(f"\nLOSS {t['entry_ct']}->{t['exit_ct']} {t['dir']} ${t['pnl']:+.0f}:")
    if not fs:
        print("   no S2/S4 pattern fired in this window")
    for f in fs:
        sysn = {2: "S2", 4: "S4"}.get(f["sys"], f"S{f['sys']}")
        agree = "SAME-dir as trade" if (f["dir"] == t["dir"]) else "opposite-dir"
        print(f"   {f['ct']} {sysn} {f['pid']:<16} {f['dir']:5} (actual ${f['pnl']:+.0f})  [{agree}]")
