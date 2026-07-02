#!/usr/bin/env python3
"""REACTIVE deep backtest: stop x target placement search + OOS robustness.
Self-contained on v9_bars_5min. Reuses the established 4-bar pattern + intrabar
conservative (stop-before-target) 3-unit scale-out, stop->BE after T1.

Stop variants:
  setup_extreme : min(low B1..B3) [LONG] / max(high B1..B3) [SHORT]   (baseline)
  b3            : B3 low [LONG] / B3 high [SHORT]
  b4            : B4 low [LONG] / B4 high [SHORT]
  atr0.5 / atr1.0 : entry -/+ k*ATR  (ATR = mean bar (h-l) over prior 14 bars same day, fallback all-prior)
  fix3/4/6/8    : entry -/+ N points
Target variants (3-unit ladder; T3 may be None => runner exits at last close):
  fix5_10       : T1=+5, T2=+10, T3=swing20 capped 25 (baseline ladder)
  R1_2_3        : T1=1R, T2=2R, T3=3R  where R = |entry-stop|
  vp_levels     : T1/T2/T3 = the nearest vah/val/poc levels strictly beyond entry (from b4 row),
                  sorted by distance; if fewer than 3 available, remaining tiers fall back to R-multiples.
"""
import pandas as pd, numpy as np, itertools

CSV="/sessions/bold-adoring-cerf/mnt/mems26_web_git/outputs/_reactive_bt_bars.csv"
SWING=20; T3CAP=25.0; ATR_N=14
THRESHOLD=0.90   # established best-ish; we also sweep later

df=pd.read_csv(CSV,parse_dates=["ct"]).sort_values("ct").reset_index(drop=True)
df["date"]=df["ct"].dt.date

STOPS=["setup_extreme","b3","b4","atr0.5","atr1.0","fix3","fix4","fix6","fix8"]
TARGETS=["fix5_10","R1_2_3","vp_levels"]

def compute_stop(kind,sig,entry,l,h,b1,b2,b3,b4,atr):
    if kind=="setup_extreme":
        return min(l[b1],l[b2],l[b3]) if sig=="LONG" else max(h[b1],h[b2],h[b3])
    if kind=="b3":
        return l[b3] if sig=="LONG" else h[b3]
    if kind=="b4":
        return l[b4] if sig=="LONG" else h[b4]
    if kind=="atr0.5":
        return entry-0.5*atr if sig=="LONG" else entry+0.5*atr
    if kind=="atr1.0":
        return entry-1.0*atr if sig=="LONG" else entry+1.0*atr
    if kind.startswith("fix"):
        n=float(kind[3:])
        return entry-n if sig=="LONG" else entry+n
    raise ValueError(kind)

def compute_targets(kind,sig,entry,stop,h,l,vah,val,poc,b4,lo):
    R=abs(entry-stop)
    if R<=0: R=1.0  # degenerate guard (e.g. stop==entry on a doji b4); keep it but flag via R
    if kind=="fix5_10":
        if sig=="LONG":
            t1=entry+5; t2=entry+10
            res=h[lo:b4].max() if b4>lo else entry
            t3=min(res,entry+T3CAP) if res>entry+10 else None
        else:
            t1=entry-5; t2=entry-10
            res=l[lo:b4].min() if b4>lo else entry
            t3=max(res,entry-T3CAP) if res<entry-10 else None
        return t1,t2,t3,R
    if kind=="R1_2_3":
        if sig=="LONG": return entry+R,entry+2*R,entry+3*R,R
        else:           return entry-R,entry-2*R,entry-3*R,R
    if kind=="vp_levels":
        # candidate VP levels for THIS bar
        levels=[vah[b4],val[b4],poc[b4]]
        levels=[x for x in levels if x and x>0]
        if sig=="LONG":
            beyond=sorted(set(x for x in levels if x>entry))         # ascending
        else:
            beyond=sorted(set(x for x in levels if x<entry),reverse=True)  # descending (closest first)
        tg=list(beyond[:3])
        # fall back to R-multiples for missing tiers
        mults=[1,2,3]
        out=[]
        for idx in range(3):
            if idx<len(tg): out.append(tg[idx])
            else:
                m=mults[idx]
                out.append(entry+m*R if sig=="LONG" else entry-m*R)
        # enforce monotonic ordering away from entry so T3>=T2>=T1 (LONG) / <= (SHORT)
        if sig=="LONG": out=sorted(out)
        else: out=sorted(out,reverse=True)
        return out[0],out[1],out[2],R
    raise ValueError(kind)

def simulate(sig,entry,stop,t1,t2,t3,h,l,c,b4,n):
    """Conservative intrabar: within a bar, check STOP before TARGET. 3 units, BE after T1."""
    units=[None,None,None]; cur_stop=stop; t1_done=False
    reached={"t1":False,"t2":False,"t3":False}; j=b4+1
    while j<n and any(u is None for u in units):
        hi,loo=h[j],l[j]
        if sig=="LONG":
            if loo<=cur_stop:                       # stop first (conservative)
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
    return pts,reached

def detect_and_run(stop_kind,tgt_kind,threshold=THRESHOLD,date_filter=None):
    out=[]
    for d,g in df.groupby("date"):
        if date_filter is not None and not date_filter(d): continue
        g=g.sort_values("ct").reset_index(drop=True); n=len(g)
        ct=g["ct"].values; o=g["open"].values; h=g["high"].values; l=g["low"].values
        c=g["close"].values; v=g["volume"].values; cvd=g["cumulative_delta"].values
        vah=g["vah"].values; val=g["val"].values; poc=g["poc_vol"].values
        rng=h-l
        i=0
        while i+3<n:
            if not all((ct[i+k+1]-ct[i+k])==np.timedelta64(5,'m') for k in range(3)):
                i+=1; continue
            b1,b2,b3,b4=i,i+1,i+2,i+3
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
            # ATR proxy: mean bar range over prior ATR_N bars same day (fallback: all prior, else b4 range)
            lo_atr=max(0,b4-ATR_N)
            atr = rng[lo_atr:b4].mean() if b4>lo_atr else (rng[:b4].mean() if b4>0 else rng[b4])
            if not np.isfinite(atr) or atr<=0: atr=max(rng[b4],1.0)
            stop=compute_stop(stop_kind,sig,entry,l,h,b1,b2,b3,b4,atr)
            lo_sw=max(0,b4-SWING)
            t1,t2,t3,R=compute_targets(tgt_kind,sig,entry,stop,h,l,vah,val,poc,b4,lo_sw)
            pts,reached=simulate(sig,entry,stop,t1,t2,t3,h,l,c,b4,n)
            # good-location: SHORT >= VAH (i.e. above_vah), LONG <= VAH (inside_va or below_val)
            good = (loc!="NA") and ((sig=="SHORT" and loc=="above_vah") or (sig=="LONG" and loc in ("inside_va","below_val")))
            out.append({"date":d,"dir":sig,"loc":loc,"good":good,"R":R,
                        "stopdist":abs(entry-stop),
                        "t1":reached["t1"],"t2":reached["t2"],"t3":reached["t3"],
                        "pts":pts,"win":1 if pts>0 else 0})
            i=b4+1
    return pd.DataFrame(out)

def metrics(r):
    """expectancy pts/contract (per 1 contract = pts/3 of the 3-unit total), win%, profit factor."""
    if len(r)==0: return dict(n=0,exp=0.0,win=0.0,pf=float('nan'),tot=0.0,t1=0.0)
    pc=r["pts"]/3.0  # per-contract
    gains=pc[pc>0].sum(); losses=-pc[pc<0].sum()
    pf=(gains/losses) if losses>0 else float('inf')
    return dict(n=len(r),exp=round(pc.mean(),3),win=round((r["win"].mean())*100,1),
                pf=round(pf,2) if np.isfinite(pf) else pf,tot=round(r["pts"].sum(),1),
                t1=round(r["t1"].mean()*100,1))

# ---------- run full grid, cache trade-level frames ----------
frames={}
for sk in STOPS:
    for tk in TARGETS:
        frames[(sk,tk)]=detect_and_run(sk,tk)

print("######## STOP x TARGET SEARCH (threshold=0.90) ########")
print("\n=== ALL detections (no location filter) — expectancy pts/contract ===")
hdr=f"{'stop':<14}{'target':<10}{'n':>4}{'exp':>8}{'win%':>7}{'pf':>7}{'t1%':>7}{'tot':>9}"
print(hdr); print("-"*len(hdr))
rowsall=[]
for sk in STOPS:
    for tk in TARGETS:
        m=metrics(frames[(sk,tk)])
        print(f"{sk:<14}{tk:<10}{m['n']:>4}{m['exp']:>8}{m['win']:>7}{str(m['pf']):>7}{m['t1']:>7}{m['tot']:>9}")
        rowsall.append((sk,tk,'ALL',m))

print("\n=== GOOD-LOCATION subset (SHORT>=VAH, LONG<=VAH) — the edge subset ===")
print(hdr); print("-"*len(hdr))
rowsgood=[]
for sk in STOPS:
    for tk in TARGETS:
        sub=frames[(sk,tk)]; sub=sub[sub["good"]]
        m=metrics(sub)
        print(f"{sk:<14}{tk:<10}{m['n']:>4}{m['exp']:>8}{m['win']:>7}{str(m['pf']):>7}{m['t1']:>7}{m['tot']:>9}")
        rowsgood.append((sk,tk,m))

# best on good-location by expectancy (require n>=10 to be meaningful)
print("\n=== TOP combos on GOOD-LOCATION (ranked by expectancy, n>=10) ===")
ranked=sorted([x for x in rowsgood if x[2]['n']>=10], key=lambda x:-x[2]['exp'])
print(f"{'stop':<14}{'target':<10}{'n':>4}{'exp':>8}{'win%':>7}{'pf':>7}{'t1%':>7}")
for sk,tk,m in ranked[:10]:
    print(f"{sk:<14}{tk:<10}{m['n']:>4}{m['exp']:>8}{m['win']:>7}{str(m['pf']):>7}{m['t1']:>7}")

# ---------- direction + location breakdown for the chosen best ----------
best=ranked[0] if ranked else None
if best:
    sk,tk,_=best
    print(f"\n=== BEST COMBO breakdown: stop={sk}  target={tk} ===")
    fr=frames[(sk,tk)]
    print("\n-- by direction (ALL) --")
    for dirn in ["LONG","SHORT"]:
        print(f"  {dirn:<6}", metrics(fr[fr['dir']==dirn]))
    print("-- by location bucket (ALL) --")
    for lc in ["above_vah","inside_va","below_val","NA"]:
        print(f"  {lc:<10}", metrics(fr[fr['loc']==lc]))
    print("-- GOOD-LOCATION by direction --")
    fg=fr[fr['good']]
    for dirn in ["LONG","SHORT"]:
        print(f"  {dirn:<6}", metrics(fg[fg['dir']==dirn]))

# save for OOS step
import pickle
with open("/tmp/reactive_frames.pkl","wb") as f:
    pickle.dump(frames,f)
print("\n[frames cached]")
