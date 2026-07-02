import pandas as pd, numpy as np, pickle
exec(open("/tmp/reactive_search.py").read().split("# ---------- run full grid")[0])  # reuse funcs+df

# Reload cached frames
frames=pickle.load(open("/tmp/reactive_frames.pkl","rb"))

print("######## ROBUSTNESS / OOS ########\n")

# --- where do GOOD-location trades actually fall (dates)? ---
fr0=frames[("setup_extreme","fix5_10")]  # location attribution identical across combos (same detections)
g=fr0[fr0["good"]].copy()
print("GOOD-location trades: n=",len(g))
print("dates of good-location trades:")
print(g.groupby("date").size().to_string())
print("\nGOOD-location direction counts:", g["dir"].value_counts().to_dict())
print("ALL detections n=",len(fr0)," date span:",fr0["date"].min(),"->",fr0["date"].max())
print("location bucket counts (ALL):", fr0["loc"].value_counts().to_dict())

# --- OOS split: chronological. Use median trade-date as cut so both halves have trades. ---
all_dates=sorted(fr0["date"].unique())
# Choose split so train has the earlier ~60% of GOOD trades
good_dates=sorted(g["date"].unique())
print("\nGOOD-location distinct dates (n=%d):"%len(good_dates), [str(d) for d in good_dates])

# Cut date: trades strictly before cut = train, >= cut = test.
# Pick cut at the good-date that splits good-trades ~60/40
import numpy as np
gd_counts=g.groupby("date").size()
cum=gd_counts.cumsum()
total=cum.iloc[-1]
cut_idx=np.searchsorted(cum.values, total*0.6)
cut_date=gd_counts.index[min(cut_idx,len(gd_counts)-1)]
print(f"\nChosen OOS cut date = {cut_date} (train < cut, test >= cut)")

def split_metrics(frame, good_only=True):
    fr=frame[frame["good"]] if good_only else frame
    tr=fr[fr["date"]<cut_date]; te=fr[fr["date"]>=cut_date]
    return metrics(tr),metrics(te),tr,te

# Evaluate the location-filtered strategy for the headline combos OOS
candidates=[("setup_extreme","fix5_10"),("b3","fix5_10"),("setup_extreme","vp_levels"),
            ("b3","R1_2_3"),("b3","vp_levels"),("atr1.0","fix5_10"),("fix4","fix5_10")]
print("\n=== OOS (GOOD-location only): TRAIN vs TEST expectancy pts/contract ===")
print(f"{'stop':<14}{'target':<10}| {'n_tr':>4}{'exp_tr':>8}{'win_tr':>7} | {'n_te':>4}{'exp_te':>8}{'win_te':>7}{'pf_te':>7}")
for sk,tk in candidates:
    mtr,mte,tr,te=split_metrics(frames[(sk,tk)],good_only=True)
    print(f"{sk:<14}{tk:<10}| {mtr['n']:>4}{mtr['exp']:>8}{mtr['win']:>7} | {mte['n']:>4}{mte['exp']:>8}{mte['win']:>7}{str(mte['pf']):>7}")

# Also OOS for the BASELINE location-filter strategy (matches established +4.4 claim) with baseline ladder
print("\n=== Baseline established strategy (setup_extreme + fix5_10, GOOD-loc) — full + OOS ===")
fr=frames[("setup_extreme","fix5_10")]; frg=fr[fr["good"]]
print("FULL good-loc:", metrics(frg))
mtr,mte,tr,te=split_metrics(fr,good_only=True)
print(f"TRAIN(<{cut_date}):", mtr)
print(f"TEST (>={cut_date}):", mte)

# threshold sweep on the good-loc baseline to see sensitivity (re-detect needed)
print("\n=== THRESHOLD sensitivity (setup_extreme+fix5_10, GOOD-loc) ===")
print(f"{'thr':>5}{'n_all':>7}{'n_good':>7}{'exp_good':>10}{'win_good':>9}")
for T in [0.70,0.75,0.80,0.85,0.90,0.95,1.00]:
    fr=detect_and_run("setup_extreme","fix5_10",threshold=T)
    fg=fr[fr["good"]]
    m=metrics(fg)
    print(f"{T:>5}{len(fr):>7}{len(fg):>7}{m['exp']:>10}{m['win']:>9}")

# --- Stability check: how concentrated is the R-multiple expectancy? (a couple of runners?) ---
print("\n=== CONCENTRATION: per-trade pts (good-loc) for high-exp R-multiple combos ===")
for sk,tk in [("b3","R1_2_3"),("setup_extreme","vp_levels"),("setup_extreme","fix5_10")]:
    s=frames[(sk,tk)]; sg=(s[s["good"]]["pts"]/3.0).sort_values()
    print(f"\n{sk}+{tk}: per-contract pts sorted:")
    print("  ", [round(x,1) for x in sg.values])
    print(f"   sum={sg.sum():.1f}  top-2 trades contribute {sg.nlargest(2).sum():.1f} ({100*sg.nlargest(2).sum()/sg.sum():.0f}% of total)")
