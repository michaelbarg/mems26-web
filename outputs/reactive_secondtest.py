#!/usr/bin/env python3
"""REACTIVE 'second-test' variant on v9_bars_5min (all days).
At-edge = entry near VA edge (LONG<=VAL+EZ / SHORT>=VAH-EZ).
2nd-test = the VA edge level was already touched earlier the same day (prior bar reached it).
Targets: T1=+5, T2=POC(VA mid), T3=opposite VA edge. Stop=setup extreme, BE after T1.
"""
import pandas as pd, numpy as np
CSV="/sessions/nice-vibrant-noether/mnt/mems26_web_git/outputs/_reactive_bt_bars.csv"
T1P=5.0
df=pd.read_csv(CSV,parse_dates=["ct"]).sort_values("ct").reset_index(drop=True)
df["date"]=df["ct"].dt.date
_dt=pd.read_csv("/sessions/nice-vibrant-noether/mnt/mems26_web_git/outputs/_daytype_by_date.csv",parse_dates=["date"])
DTMAP={d.date():t for d,t in zip(_dt["date"],_dt["day_type"])}

def run(threshold, EZ, TT):
    out=[]
    for d,g in df.groupby("date"):
        g=g.sort_values("ct").reset_index(drop=True); n=len(g)
        ct=g["ct"].values;o=g["open"].values;h=g["high"].values;l=g["low"].values
        c=g["close"].values;v=g["volume"].values;vah=g["vah"].values;val=g["val"].values
        i=0
        while i+3<n:
            if not all((ct[i+k+1]-ct[i+k])==np.timedelta64(5,'m') for k in range(3)): i+=1;continue
            b1,b2,b3,b4=i,i+1,i+2,i+3
            sig=None
            if c[b1]<o[b1] and v[b1]>0 and v[b2]<=threshold*v[b1] and c[b3]>o[b3] and c[b4]>h[b3]: sig="LONG"
            elif c[b1]>o[b1] and v[b1]>0 and v[b2]<=threshold*v[b1] and c[b3]<o[b3] and c[b4]<l[b3]: sig="SHORT"
            if sig is None: i+=1;continue
            if vah[b4]<=0 or val[b4]<=0: i+=1;continue
            entry=c[b4]; pocp=(vah[b4]+val[b4])/2.0
            if sig=="LONG":
                if entry>val[b4]+EZ: i+=1;continue                       # entry AT/below VAL
                touches=int(np.sum(l[0:b1]<=val[b4]+TT))                 # VAL tested earlier today
                ext=min(l[b1],l[b2],l[b3]); stop=ext; t1=entry+T1P
                t2=max(pocp,entry+T1P+0.25); t3=max(vah[b4],t2+0.25)
            else:
                if entry<vah[b4]-EZ: i+=1;continue                       # entry AT/above VAH
                touches=int(np.sum(h[0:b1]>=vah[b4]-TT))                 # VAH tested earlier today
                ext=max(h[b1],h[b2],h[b3]); stop=ext; t1=entry-T1P
                t2=min(pocp,entry-T1P-0.25); t3=min(val[b4],t2-0.25)
            units=[None,None,None]; cs=stop; t1d=False; rc={"t1":0,"t2":0,"t3":0}; j=b4+1
            while j<n and any(u is None for u in units):
                hi,loo=h[j],l[j]
                if sig=="LONG":
                    if loo<=cs:
                        for k in range(3):
                            if units[k] is None: units[k]=cs
                        break
                    if not t1d and hi>=t1: units[0]=t1;t1d=True;cs=entry;rc["t1"]=1
                    if t1d and units[1] is None and hi>=t2: units[1]=t2;rc["t2"]=1
                    if t1d and units[2] is None and hi>=t3: units[2]=t3;rc["t3"]=1
                else:
                    if hi>=cs:
                        for k in range(3):
                            if units[k] is None: units[k]=cs
                        break
                    if not t1d and loo<=t1: units[0]=t1;t1d=True;cs=entry;rc["t1"]=1
                    if t1d and units[1] is None and loo<=t2: units[1]=t2;rc["t2"]=1
                    if t1d and units[2] is None and loo<=t3: units[2]=t3;rc["t3"]=1
                j+=1
            lastc=c[min(j,n-1)]
            for k in range(3):
                if units[k] is None: units[k]=lastc
            pts=sum(u-entry for u in units) if sig=="LONG" else sum(entry-u for u in units)
            out.append({"dir":sig,"touches":touches,"second":touches>=1,"dt":DTMAP.get(d,None),
                        "t1":rc["t1"],"t2":rc["t2"],"t3":rc["t3"],"pts":pts})
            i=b4+1
    return pd.DataFrame(out)

def summ(g):
    if len(g)==0: return "n=0"
    return (f"n={len(g):>3}  t1%={g['t1'].mean()*100:>3.0f}  t2%={g['t2'].mean()*100:>3.0f}  "
            f"avg_pt/1c={g['pts'].mean()/3:>6.2f}  tot_pts={g['pts'].sum():>5.0f}")

r=run(0.90,10,6)
rk=r[r["dt"].notna()].copy()
print(f"=== at-edge REACTIVE + structural targets, SPLIT BY DAY-TYPE (thr0.90 edge10 touch6) ===")
print(f"total setups={len(r)}  day-type-covered={len(rk)}  (covered dates 06-03..06-28)\n")
g=rk.groupby("dt").agg(n=("pts","size"),t1=("t1","mean"),t2=("t2","mean"),
                       avg_pt1c=("pts",lambda x:x.mean()/3),tot=("pts","sum")).reset_index()
g["t1"]=(g["t1"]*100).round();g["t2"]=(g["t2"]*100).round();g["avg_pt1c"]=g["avg_pt1c"].round(2);g["tot"]=g["tot"].round()
print("-- by day_type --"); print(g.to_string(index=False))
g2=rk.groupby(["dt","dir"]).agg(n=("pts","size"),t1=("t1","mean"),
                                avg_pt1c=("pts",lambda x:x.mean()/3),tot=("pts","sum")).reset_index()
g2["t1"]=(g2["t1"]*100).round();g2["avg_pt1c"]=g2["avg_pt1c"].round(2);g2["tot"]=g2["tot"].round()
print("\n-- by day_type x direction --"); print(g2.to_string(index=False))
