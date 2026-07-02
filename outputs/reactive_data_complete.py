import pandas as pd, numpy as np
CSV="/sessions/bold-adoring-cerf/mnt/mems26_web_git/outputs/_reactive_bt_bars.csv"
df=pd.read_csv(CSV,parse_dates=["ct"]).sort_values("ct").reset_index(drop=True)
df["date"]=df["ct"].dt.date
print("=== OVERALL ===")
print("total bars:", len(df))
print("date span:", df["ct"].min(), "->", df["ct"].max())
print("unique dates:", df["date"].nunique())
# RTH window: CME ES/MES RTH 08:30-15:00 CT = 78 5-min bars (08:30..14:55) + maybe a 15:00 close bar.
# Let's check the time-of-day distribution
df["tod"]=df["ct"].dt.time
print("\n=== TIME-OF-DAY range per bar ===")
print("min tod:", df["tod"].min(), " max tod:", df["tod"].max())
# bars per day
bpd=df.groupby("date").size()
print("\n=== BARS PER DAY distribution ===")
print(bpd.describe())
print("\nfull histogram of bars/day:")
print(bpd.value_counts().sort_index())
EXP=78
print(f"\nexpected RTH bars/day (08:30-14:55, 5min) = {EXP}")
print("days with >= 78 bars:", (bpd>=78).sum())
print("days with >= 70 bars:", (bpd>=70).sum())
print("days with >= 50 bars:", (bpd>=50).sum())
print("days with >= 20 bars:", (bpd>=20).sum())
print("days with <= 5 bars:", (bpd<=5).sum())
print("median bars/day:", bpd.median(), " mean:", round(bpd.mean(),1))
print("total RTH bars present vs expected if all days full:", len(df), "vs", EXP*df["date"].nunique())
print("overall completeness ratio:", round(len(df)/(EXP*df["date"].nunique()),3))

# Consecutive 5-min run analysis + 4-bar windows
print("\n=== CONSECUTIVE 5-MIN WINDOW ANALYSIS ===")
total_4windows=0
runs_all=[]
per_day_windows={}
for d,g in df.groupby("date"):
    g=g.sort_values("ct").reset_index(drop=True)
    ct=g["ct"].values
    n=len(g)
    # find maximal consecutive 5-min runs
    run_len=1; runs=[]
    for k in range(1,n):
        if (ct[k]-ct[k-1])==np.timedelta64(5,'m'):
            run_len+=1
        else:
            runs.append(run_len); run_len=1
    runs.append(run_len)
    runs_all.extend(runs)
    # number of valid 4-consecutive-bar windows = sum over runs of max(0, run-3)
    w=sum(max(0,r-3) for r in runs)
    per_day_windows[d]=w
    total_4windows+=w
runs_all=np.array(runs_all)
print("total maximal consecutive runs:", len(runs_all))
print("run-length distribution:")
print(pd.Series(runs_all).value_counts().sort_index().head(40))
print("longest run:", runs_all.max(), " runs>=4:", (runs_all>=4).sum(), " runs of len 1 (isolated bars):", (runs_all==1).sum())
print("\nTOTAL valid consecutive 4-bar detection windows:", total_4windows)
pdw=pd.Series(per_day_windows)
print("days with >=1 valid 4-bar window:", (pdw>0).sum(), "of", df["date"].nunique())
print("4-bar windows per day describe:")
print(pdw.describe())

# Theoretical max windows if every day were fully contiguous (78 bars -> 75 windows/day)
theo = (78-3)*df["date"].nunique()
print(f"\ntheoretical 4-bar windows if fully contiguous = (78-3)*{df['date'].nunique()} = {theo}")
print("actual/theoretical:", round(total_4windows/theo,3))

# VP columns populated?
print("\n=== VP COLUMN COVERAGE (vah/val/poc) ===")
print("bars with vah>0 & val>0:", ((df['vah']>0)&(df['val']>0)).sum(), "of", len(df), "=", round(((df['vah']>0)&(df['val']>0)).mean(),3))
print("bars with cumulative_delta != 0:", (df['cumulative_delta']!=0).sum(), "of", len(df))
# dates where VP is populated
vp_dates = df[(df['vah']>0)&(df['val']>0)]['date'].nunique()
print("distinct dates with any VP-populated bar:", vp_dates)
