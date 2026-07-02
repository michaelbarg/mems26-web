#!/usr/bin/env python3
"""REACTIVE backtest on v9_bars_5min (the live-CVD series).
Parameterized B2 volume-drop threshold + optional CVD filter (per investigation A).
Exits: T1=+5pt, T2=+10pt, T3=swing-resistance(prior 20 bars), stop=setup extreme, BE after T1.
Self-contained on v9_bars_5min so the price-basis offset is irrelevant (targets are relative).
"""
import pandas as pd, numpy as np

CSV = "/sessions/nice-vibrant-noether/mnt/mems26_web_git/outputs/_reactive_bt_bars.csv"
T1P, T2P, SWING, T3CAP = 5.0, 10.0, 20, 25.0

df = pd.read_csv(CSV, parse_dates=["ct"]).sort_values("ct").reset_index(drop=True)
df["date"] = df["ct"].dt.date

def run(threshold, cvd_filter, loc_filter=False):
    out = []
    for d, g in df.groupby("date"):
        g = g.sort_values("ct").reset_index(drop=True); n = len(g)
        ct=g["ct"].values; o=g["open"].values; h=g["high"].values; l=g["low"].values
        c=g["close"].values; v=g["volume"].values; cvd=g["cumulative_delta"].values
        vah=g["vah"].values; val=g["val"].values
        i = 0
        while i+3 < n:
            if not all((ct[i+k+1]-ct[i+k])==np.timedelta64(5,'m') for k in range(3)):
                i += 1; continue
            b1,b2,b3,b4 = i,i+1,i+2,i+3
            sig=None
            if c[b1]<o[b1] and v[b1]>0 and v[b2]<=threshold*v[b1] and c[b3]>o[b3] and c[b4]>h[b3]:
                sig="LONG"
            elif c[b1]>o[b1] and v[b1]>0 and v[b2]<=threshold*v[b1] and c[b3]<o[b3] and c[b4]<l[b3]:
                sig="SHORT"
            if sig is None: i+=1; continue
            entry=c[b4]
            loc="NA"
            if vah[b4]>0 and val[b4]>0:
                loc=("above_vah" if entry>vah[b4] else "below_val" if entry<val[b4] else "inside_va")
            if loc_filter:
                if loc=="NA": i+=1; continue
                if sig=="LONG" and loc=="above_vah": i+=1; continue
                if sig=="SHORT" and loc=="inside_va": i+=1; continue
            if cvd_filter:
                if sig=="LONG" and not (cvd[b4]-cvd[b3] > 0): i+=1; continue
                if sig=="SHORT" and not (cvd[b4]-cvd[b1] < 0): i+=1; continue
            lo=max(0,b4-SWING)
            if sig=="LONG":
                stop=min(l[b1],l[b2],l[b3]); t1=entry+T1P; t2=entry+T2P
                res=h[lo:b4].max() if b4>lo else entry
                t3=min(res,entry+T3CAP) if res>entry+T2P else None
            else:
                stop=max(h[b1],h[b2],h[b3]); t1=entry-T1P; t2=entry-T2P
                res=l[lo:b4].min() if b4>lo else entry
                t3=max(res,entry-T3CAP) if res<entry-T2P else None
            units=[None,None,None]; cur_stop=stop; t1_done=False
            reached={"t1":False,"t2":False,"t3":False}; j=b4+1
            while j<n and any(u is None for u in units):
                hi,loo=h[j],l[j]
                if sig=="LONG":
                    if loo<=cur_stop:
                        for k in range(3):
                            if units[k] is None: units[k]=cur_stop
                        break
                    if not t1_done and hi>=t1: units[0]=t1; t1_done=True; cur_stop=entry; reached["t1"]=True
                    if t1_done and units[1] is None and hi>=t2: units[1]=t2; reached["t2"]=True
                    if t1_done and units[2] is None and t3 is not None and hi>=t3: units[2]=t3; reached["t3"]=True
                else:
                    if hi>=cur_stop:
                        for k in range(3):
                            if units[k] is None: units[k]=cur_stop
                        break
                    if not t1_done and loo<=t1: units[0]=t1; t1_done=True; cur_stop=entry; reached["t1"]=True
                    if t1_done and units[1] is None and loo<=t2: units[1]=t2; reached["t2"]=True
                    if t1_done and units[2] is None and t3 is not None and loo<=t3: units[2]=t3; reached["t3"]=True
                j+=1
            last_close=c[min(j,n-1)]
            for k in range(3):
                if units[k] is None: units[k]=last_close
            pts = sum(u-entry for u in units) if sig=="LONG" else sum(entry-u for u in units)
            b1rng=h[b1]-l[b1]; b3rng=h[b3]-l[b3]; b4rng=h[b4]-l[b4]
            b3bf=(abs(c[b3]-o[b3])/b3rng) if b3rng>0 else 0
            b4cp=((c[b4]-l[b4])/b4rng if sig=="LONG" else (h[b4]-c[b4])/b4rng) if b4rng>0 else 0
            b3big=1 if abs(c[b3]-o[b3])>abs(c[b1]-o[b1]) else 0
            out.append({"dir":sig,"loc":loc,"t1":reached["t1"],"t2":reached["t2"],"t3":reached["t3"],"pts":pts,
                        "b1rng":b1rng,"b3bf":b3bf,"b4cp":b4cp,"b3big":b3big,"win":1 if pts>0 else 0})
            i=b4+1
    return pd.DataFrame(out)

def summ(r):
    if len(r)==0: return (0,0,0,0.0,0)
    return (len(r), round(r["t1"].mean()*100), round(r["t2"].mean()*100),
            round(r["pts"].mean()/3,2), round(r["pts"].sum()))

print("=== BASELINE vs LOCATION-FILTER vs LOCATION+CVD  (per single threshold, no pooling) ===")
print(f"{'thr':>5} {'config':<12} {'n':>4} {'t1%':>4} {'t2%':>4} {'avg_pt/1c':>9} {'$/1c':>6} {'tot_pts':>8}")
for T in [0.75,0.85,0.90]:
    for label,cf,lf in [("baseline",False,False),("loc-filter",False,True),("loc+CVD",True,True)]:
        n,t1,t2,avg,tot=summ(run(T,cf,lf))
        print(f"{T:>5} {label:<12} {n:>4} {t1:>4} {t2:>4} {avg:>9} {round(avg*5,1):>6} {tot:>8}")

print("\n=== LOCATION breakdown @ T=0.90 single-threshold (clean, no double-count) ===")
r=run(0.90,False,False)
for dirn in ["LONG","SHORT"]:
    sub=r[(r["dir"]==dirn)&(r["loc"]!="NA")]
    g=sub.groupby("loc").agg(n=("pts","size"),t1=("t1","mean"),avg_pt1c=("pts",lambda x:x.mean()/3)).reset_index()
    g["t1"]=(g["t1"]*100).round(); g["avg_pt1c"]=g["avg_pt1c"].round(2)
    print(f"\n-- {dirn} --"); print(g.to_string(index=False))

print("\n=== COMBINED PICK: T=0.90 + location-filter — direction split ===")
r=run(0.90,False,True)
g=r.groupby("dir").agg(n=("pts","size"),t1=("t1","mean"),avg_pt1c=("pts",lambda x:x.mean()/3),tot=("pts","sum")).reset_index()
g["t1"]=(g["t1"]*100).round(); g["avg_pt1c"]=g["avg_pt1c"].round(2); g["tot"]=g["tot"].round()
print(g.to_string(index=False))
print(f"\nALL: n={len(r)}  avg_pt/1c={round(r['pts'].mean()/3,2)}  $/1c={round(r['pts'].mean()/3*5,1)}  total_pts(3c)={round(r['pts'].sum())}  total$≈{round(r['pts'].sum()*5)}")

print("\n=== CANDLE morphology: winners(pts>0) vs losers @ T=0.90 no-filter ===")
rc=run(0.90,False,False)
for w in [1,0]:
    s=rc[rc["win"]==w]
    if len(s)==0: continue
    print(f"win={w} n={len(s)} | b1_range={s['b1rng'].mean():.2f}  b3_bodyfrac={s['b3bf'].mean():.2f}  b4_closepos={s['b4cp'].mean():.2f}  b3body>b1body={s['b3big'].mean():.2f}")
# split by direction too
for dirn in ["LONG","SHORT"]:
    sd=rc[rc["dir"]==dirn]
    for w in [1,0]:
        s=sd[sd["win"]==w]
        if len(s)==0: continue
        print(f"  {dirn} win={w} n={len(s)} | b3_bodyfrac={s['b3bf'].mean():.2f}  b4_closepos={s['b4cp'].mean():.2f}  b3>b1={s['b3big'].mean():.2f}")
print("(b3_bodyfrac=reversal body/range; b4_closepos=close near extreme,1=strong; b3>b1=reversal bigger than climax)")
