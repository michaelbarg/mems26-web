import pandas as pd, numpy as np, pickle
exec(open("/tmp/reactive_search.py").read().split("# ---------- run full grid")[0])
frames=pickle.load(open("/tmp/reactive_frames.pkl","rb"))

# Focus on the robust combo: setup_extreme + fix5_10, GOOD-loc. Per-direction OOS.
fr=frames[("setup_extreme","fix5_10")]; fg=fr[fr["good"]].copy()
cut=pd.Timestamp("2026-06-18").date()
print("=== setup_extreme+fix5_10 GOOD-loc: per-direction TRAIN vs TEST ===")
for dirn in ["SHORT","LONG"]:
    s=fg[fg["dir"]==dirn]
    tr=s[s["date"]<cut]; te=s[s["date"]>=cut]
    print(f"{dirn:<6} FULL {metrics(s)}")
    print(f"       TRAIN {metrics(tr)}")
    print(f"       TEST  {metrics(te)}")

# Leave-one-day-out (LODO): for each good-day, expectancy of the OTHER days. How stable?
print("\n=== LEAVE-ONE-DAY-OUT stability (setup_extreme+fix5_10, good-loc) ===")
days=sorted(fg["date"].unique())
exps=[]
for d in days:
    rest=fg[fg["date"]!=d]
    exps.append(metrics(rest)["exp"])
print("LODO expectancy range:", round(min(exps),3),"to",round(max(exps),3),"| mean",round(np.mean(exps),3))
print("(all positive)" if min(exps)>0 else "(SOME NEGATIVE -> fragile)")

# What fraction of good-loc days are net-positive at day level?
print("\n=== per-day net pts/contract (good-loc, setup_extreme+fix5_10) ===")
byday=(fg.assign(pc=fg["pts"]/3.0).groupby("date")["pc"].agg(["sum","size"]))
print(byday.round(2).to_string())
print("net-positive days:", (byday["sum"]>0).sum(), "of", len(byday))

# Compare: what would the SAME trades earn with the established baseline T3=swing? Already that's fix5_10. Good.
# Sanity: also report the ALL (no-loc) baseline OOS to show filter is doing the work consistently OOS.
print("\n=== Filter value OOS: ALL vs GOOD, test window only (>=cut) ===")
te_all=fr[fr["date"]>=cut]; te_good=fg[fg["date"]>=cut]
print("ALL  (no filter) test:", metrics(te_all))
print("GOOD (filtered)  test:", metrics(te_good))
