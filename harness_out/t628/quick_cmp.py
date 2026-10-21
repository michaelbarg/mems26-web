import json,glob,os,sys,collections
def load(tag):
    out={}
    for p in glob.glob(f'harness_out/t628/days/{tag}_*.json'):
        d=os.path.basename(p)[len(tag)+1:-5]
        try: j=json.load(open(p))
        except Exception: continue
        tr=j.get('trades') or []
        out[d]=(round(sum((t.get('pnl_usd') or 0) for t in tr),2), len(tr))
    return out
ref=load(sys.argv[1])
for tag in sys.argv[2:]:
    v=load(tag); days=sorted(set(ref)&set(v))
    dn=[(d, v[d][0]-ref[d][0]) for d in days]
    tot=sum(x for _,x in dn); better=sum(1 for _,x in dn if x>0.01); worse=sum(1 for _,x in dn if x<-0.01)
    bym=collections.defaultdict(float)
    for d,x in dn: bym[d[:7]]+=x
    last10=sum(x for d,x in sorted(dn)[-10:]); hold=sum(x for d,x in sorted(dn)[-10:])
    net_abs=sum(v[d][0] for d in days); ntr=sum(v[d][1] for d in days); ntr_ref=sum(ref[d][1] for d in days)
    print(f"{tag:8s} vs {sys.argv[1]}: Δnet {tot:+9.2f}  abs {net_abs:+9.2f}  trades {ntr} (ref {ntr_ref})  better {better} / worse {worse} / same {len(days)-better-worse}  last10 {last10:+8.2f}")
    print("   by month Δ:", {k:round(x,1) for k,x in sorted(bym.items())})
    big=sorted(dn,key=lambda t:abs(t[1]),reverse=True)[:6]
    print("   biggest:", [(d,round(x,1)) for d,x in big])
    print("   21.10:", ref.get('2026-10-21'), '->', v.get('2026-10-21'), " 20.10:", ref.get('2026-10-20'), '->', v.get('2026-10-20'))
