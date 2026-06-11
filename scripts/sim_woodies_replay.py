import os, sys, datetime as dt, json
sys.path.insert(0, '/Users/michael/Downloads/mems26_web_git')
os.environ.setdefault("S1_PROVISIONAL_DAYTYPE","1"); os.environ.setdefault("STOP_ANCHORS_V2","1")
from sqlalchemy import create_engine, text
from backend.v9.systems.woodies.schemas import WoodiesBar
from backend.v9.systems.woodies.pattern_engine import detect_all_patterns
from backend.v9.systems.woodies.pattern_dispatcher import PatternDispatcher
from backend.v9.systems.woodies.stages.a1_strategic_gate import TrendState
from backend.v9.systems.stop_anchors import resolver as SA
from backend.v9.config_loader import load_stop_anchors
from backend.v9.shared.pre_fire_validator import FireRequest, validate_fire
SA_CFG=load_stop_anchors(); DISP=PatternDispatcher(); MES,CONTRACTS=5.0,2
RTH_LO,RTH_HI=13*60+30,20*60; REV={"VEGAS","GHOST","FAMIR","HTLB","HFE"}; COOL=6
e=create_engine('postgresql://localhost/mems26')
with e.connect() as c:
    rows=c.execute(text("""SELECT ts,open,high,low,close,volume,cci_14,cci_6_tcci,ema_34,lsma_value,lsma_above_price,
        swi_value,czi_value,trend_state,predictor_next_cci,zlr_detected,zlr_direction,hfe_detected,hfe_direction,
        hfe_extreme_bars_ago FROM v9_bars_5min_woodies WHERE ts::date=DATE '2026-06-09' ORDER BY ts""")).fetchall()
def mkwb(r): return WoodiesBar(ts=r[0].timestamp(),open=float(r[1]),high=float(r[2]),low=float(r[3]),close=float(r[4]),
    volume=float(r[5] or 0),cci_14=float(r[6] or 0),cci_6_tcci=float(r[7] or 0),ema_34=float(r[8] or 0),lsma_value=float(r[9] or 0),
    lsma_above_price=bool(r[10]),swi_value=float(r[11] or 0),czi_value=float(r[12] or 0),trend_state=(r[13] or "GRAY"),
    predictor_next_cci=float(r[14] or 0),zlr_detected=bool(r[15]),zlr_direction=(r[16] or "NONE"),hfe_detected=bool(r[17]),
    hfe_direction=(r[18] or "NONE"),hfe_extreme_bars_ago=int(r[19] or 0))
wb=[mkwb(r) for r in rows]
um=lambda b:(dt.datetime.utcfromtimestamp(b.ts).hour*60+dt.datetime.utcfromtimestamp(b.ts).minute)
et=lambda b:(dt.datetime.utcfromtimestamp(b.ts)-dt.timedelta(hours=4)).strftime("%H:%M")
def t1_of(en,st,d,pid,grp):
    rev=(pid in REV) or (grp=="REVERSAL"); a=SA_CFG["anchors"].get(pid,{})
    return SA.t1_price(en,st,d,t1_ladder_cont=SA_CFG["t1_ladder_continuation"],reversal=rev,
        reversal_mult=SA_CFG.get("t1_reversal_multiplier",0.8),t1_floor_points=SA_CFG.get("t1_floor_points",3.0),ladder_shift=a.get("t1_ladder_shift",0))
def fill(en,st,t1,d,i0,tb=18):
    s=1 if d=="LONG" else -1; risk=abs(en-st); cur=st; half=False; hwm=en; pts=0.0
    for j in range(i0+1,min(i0+1+tb,len(wb))):
        b=wb[j]; adv=b.low if d=="LONG" else b.high; fav=b.high if d=="LONG" else b.low
        if (d=="LONG" and adv<=cur) or (d=="SHORT" and adv>=cur):
            rem=0.5 if half else 1.0; pts+=rem*s*(cur-en); return pts,("T1+trail" if half else "STOP"),cur,et(b),j
        if not half and ((d=="LONG" and fav>=t1) or (d=="SHORT" and fav<=t1)): pts+=0.5*s*(t1-en); half=True; cur=en
        if half:
            hwm=max(hwm,fav) if d=="LONG" else min(hwm,fav); tr=hwm-s*risk
            if (d=="LONG" and tr>cur) or (d=="SHORT" and tr<cur): cur=tr
    last=wb[min(i0+tb,len(wb)-1)]; rem=0.5 if half else 1.0; pts+=rem*s*(last.close-en)
    return pts,("T1+time" if half else "TIME"),cur,et(last),min(i0+tb,len(wb)-1)
setups=[]; last_i=-99
for i in range(len(wb)):
    b=wb[i]
    if not(RTH_LO<=um(b)<RTH_HI) or b.trend_state in("GRAY","YELLOW"): continue
    if i-last_i<COOL: continue
    cands=[p for p in detect_all_patterns(wb[:i+1]) if p.detected and p.direction in("LONG","SHORT") and p.entry_price>0
        and p.stop>0 and abs(p.entry_price-p.stop)>=0.25]
    if not cands: continue
    try: best=DISP.select_winner(cands,TrendState(b.trend_state)).winner
    except Exception: best=max(cands,key=lambda p:p.confidence)
    if best is None: continue
    en,st=best.entry_price,best.stop; t1=t1_of(en,st,best.direction,best.pattern_id,best.group)
    rev=(best.pattern_id in REV) or (best.group=="REVERSAL")
    if not validate_fire(FireRequest(system_id="T2_WOODIES",direction=best.direction,entry_price=en,stop_price=st,
        t1_price=t1,t2_price=None,time_stop_minutes=90,confidence=int(best.confidence*100),
        expected_t2_r_mult=1.5 if rev else 2.0)).valid: continue
    pts,exr,fstop,ext,jx=fill(en,st,t1,best.direction,i)
    _rk=abs(en-st); _cN=3 if _rk<=15 else (2 if _rk<=25 else 1)   # real risk->contracts ladder
    setups.append(dict(i=i,jx=jx,t=et(b),pat=best.pattern_id,d=best.direction,entry=round(en,2),stop=round(st,2),
        risk=round(_rk,1),cN=_cN,t1=round(t1,2),trail=round(fstop,2),exr=exr,ext=ext,pts=round(pts,2),
        usd=round(pts*MES*_cN,0),trend=b.trend_state)); last_i=i
# single-position overlay
open_until=-1
for s in setups:
    if s['i']>open_until: s['taken']=True; open_until=s['jx']
    else: s['taken']=False
hdr=f"{'ET':>5} {'pattern':<6}{'dir':<6}{'entry':>8}{'stop':>9}{'risk':>5}{'cN':>3}{'T1':>9}{'trailStop':>10} {'exit':<9}{'@':>6}{'netPt':>7}{'$':>7}  TAKEN"
print(hdr); print("-"*106)
for s in setups:
    print(f"{s['t']:>5} {s['pat']:<6}{s['d']:<6}{s['entry']:>8.2f}{s['stop']:>9.2f}{s['risk']:>5.0f}{s['cN']:>3}{s['t1']:>9.2f}{s['trail']:>10.2f} {s['exr']:<9}{s['ext']:>6}{s['pts']:>7.1f}{s['usd']:>7.0f}  {'YES' if s['taken'] else 'skip(in-pos)'}")
print("-"*106)
tk=[s for s in setups if s['taken']]
print(f"ALL scanned setups={len(setups)}  | TAKEN (single-position)={len(tk)} wins={sum(1 for s in tk if s['pts']>0)} loss={sum(1 for s in tk if s['pts']<=0)}")
print(f"TAKEN netPts={sum(s['pts'] for s in tk):.1f}  Σ$={sum(s['usd'] for s in tk):.0f}   (real risk-ladder sizing 3/2/1c @ ${MES}/pt, 50% T1 / 50% runner+trail)")
json.dump(setups, open('/tmp/sim_0609_setups.json','w'))
