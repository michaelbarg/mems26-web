#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""open_drive_branch_study.py — the opening-drive BRANCH on every past session
(T-426 / Michael 20.09 "תתקן את הענף … שוב קנית מאוחר מדי").

Replays the REAL opening-engine functions (evaluate_opening_entry → dir-fusion gate →
opening_first_trade_ok → build_opening_setup) on CANONICAL CLOSED RTH bars, session by
session, exactly as the fixed live path will see them (T-422 + T-425: the engine judges
closed bars, never the 3-second developing snapshot). Every candidate is then priced with
the ONE fixed evaluation model (entry = next bar open ± slippage, first-touch stop/target on
5-min bars, AMBIG unassigned, EOD close, $5/pt, 1 contract = single leg to T1; 2-contract
ladder T1/T2 with BE reported alongside).

For each candidate it also records what the CURRENT tree would have done with it:
  admitted  — the T-314 label at decision time is OPEN_DRIVE/OPEN_TEST_DRIVE (or ORR) in the
              candidate's direction → phase A/B row allows WITH_DRIVE
  blocked   — the label is still OPEN_AUCTION_IN/OUT (or UNKNOWN) → the phase-B row allows
              EDGE_FADE only → `dalton_intent:kind` (this is T-426)
so the question "should the branch admit confirmed drives while the label lags?" gets a
number, not an opinion. Variants: min confirmation bars 3 (ruled) vs 2 (Michael: "on the way").

Read-only (SELECT only). ~10s. Run: python3 scripts/open_drive_branch_study.py [--csv out.csv]
"""
import os, sys, json, argparse, collections, statistics
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'scripts')); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, '.env'))
# the opening engine reads these at call time — pin them to the LIVE values (.env 20.09)
os.environ.setdefault("OPENING_LADDER_V1", "1")
os.environ.setdefault("T1_BANK_R", "1.5")
os.environ.setdefault("OPENING_T2_R", "2.5")
os.environ.setdefault("OPENING_T3_R", "4.0")
os.environ["OPENING_OR_ATR_SCALE_V1"] = "1"
os.environ["SITUATION_VECTOR_LOG_V1"] = "0"
from backend.v9.db.read import read_all
from backend.v9.systems import opening_entry as OE
from backend.v9.systems.day_type import detector as DTD
from backend.v9.systems.day_type.opening_detector_v2 import detect_opening_type

ap = argparse.ArgumentParser()
ap.add_argument("--csv", default=None)
ap.add_argument("--since", default="2026-06-01")
args = ap.parse_args()

TICK_USD, SLIP, COMM = 5.0, 0.50, 1.30
EXC = {'2026-06-09','2026-06-10','2026-06-11','2026-06-12','2026-06-17','2026-06-18','2026-06-19',
       '2026-06-26','2026-07-10','2026-07-24','2026-07-28','2026-07-29','2026-09-16','2026-09-17'}

rows = read_all("""select b.ts, (b.ts at time zone 'Asia/Jerusalem')::date d,
  to_char(b.ts at time zone 'Asia/Jerusalem','HH24:MI') t,
  b.open o, b.high h, b.low l, b.close c, b.volume v
  from v9_bars_5min_woodies b
  where b.symbol='MES' and b.ts >= :since
  and (b.ts at time zone 'America/New_York')::time >= '09:30'
  and (b.ts at time zone 'America/New_York')::time < '16:00' order by b.ts""", {"since": args.since})
by_day = collections.defaultdict(list)
for r in rows:
    by_day[str(r['d'])].append({"ts": r['ts'].isoformat(), "il": r['t'], "o": float(r['o']), "h": float(r['h']),
                                "l": float(r['l']), "c": float(r['c']), "v": float(r['v'] or 0)})
alld = sorted(by_day)
days = [d for d in alld if d not in EXC and len(by_day[d]) >= 60]
tpo = {str(r['trading_date']): (r['vah'], r['val']) for r in read_all(
    "select trading_date, max(vah_price) vah, min(val_price) val from v9_tpo_sessions group by trading_date", {})}

def daily_atr(d, n=14):
    prev = [x for x in alld if x < d][-n:]
    rs = [max(b['h'] for b in by_day[x]) - min(b['l'] for b in by_day[x]) for x in prev if len(by_day[x]) >= 10]
    return statistics.mean(rs) if len(rs) >= 3 else None

def prior_ctx(d):
    prev = [x for x in alld if x < d]
    if not prev: return {}
    p = prev[-1]; pb = by_day[p]
    vah, val = tpo.get(p, (None, None))
    meds = [sum(b['v'] for b in by_day[x][:6]) for x in prev if len(by_day[x]) >= 6]
    return {"pdh": max(b['h'] for b in pb), "pdl": min(b['l'] for b in pb), "vah": vah, "val": val,
            "med_ov": statistics.median(meds) if meds else None}

def price(bars, i_entry, direction, stop, targets):
    """fixed model: entry at open of bars[i_entry] ± slip; legs = len(targets) contracts.
    Returns (legs [(event, pts)], entry). First-touch on bars from i_entry (the entry bar itself
    counts); AMBIG when stop and target touch in the same bar; BE after leg-1 target; EOD close."""
    e = bars[i_entry]['o'] + (SLIP/2 if direction == "LONG" else -SLIP/2)
    cur_stop = stop; done = [False]*len(targets); out = [None]*len(targets)
    for j in range(i_entry, len(bars)):
        hi, lo = bars[j]['h'], bars[j]['l']
        for k, t in enumerate(targets):
            if done[k]: continue
            if direction == "SHORT": ht, hs = lo <= t, hi >= cur_stop
            else:                    ht, hs = hi >= t, lo <= cur_stop
            if ht and hs: out[k] = ("AMBIG", 0.0); done[k] = True
            elif ht:
                out[k] = (f"T{k+1}", abs(t - e)); done[k] = True
                if k == 0: cur_stop = e
            elif hs:
                out[k] = ("STOP" if cur_stop != e else "BE", -abs(e - cur_stop) if cur_stop != e else 0.0); done[k] = True
        if all(done): break
    lc = bars[-1]['c']
    for k in range(len(targets)):
        if not done[k]: out[k] = ("EOD", (e - lc) if direction == "SHORT" else (lc - e))
    return out, e

def usd(legs):
    return sum(p for ev, p in legs if ev != "AMBIG") * TICK_USD - COMM * sum(1 for ev, _ in legs if ev != "AMBIG")

def label_at(closed):
    det = detect_opening_type([{"o": b['o'], "h": b['h'], "l": b['l'], "c": b['c'], "v": b['v']} for b in closed[:6]], closed[0]['o'])
    ot, dr = det.get("opening_type"), det.get("direction")
    bias = "LONG" if dr in ("UP", "LONG") else "SHORT" if dr in ("DOWN", "SHORT") else None
    return ot, bias

def admitted_today(ot, bias, direction, phase):
    if phase == "A": return ot == "OPEN_DRIVE" and bias == direction
    return ot in ("OPEN_DRIVE", "OPEN_TEST_DRIVE", "OPEN_REJECTION_REVERSE") and bias == direction

def run(min_bars):
    cands = []
    for d in days:
        bars = by_day[d]
        atr = daily_atr(d)
        DTD.compute_daily_atr = (lambda n_sessions=14, _a=atr: _a)   # causal daily ATR for the OR threshold
        ctx = prior_ctx(d)
        fired, fusion, fusion_done = set(), None, False
        for n in range(2, 13):                      # closed bars 2..12 (OPENING_FIRE_V1 window)
            if n >= len(bars) - 1: break
            closed = bars[:n]
            decide = bars[n]                        # decision at the open of bar n+1 (index n)
            phase = "A" if decide['il'] < "16:45" else "B" if decide['il'] < "17:30" else "C"
            if not fusion_done and n >= 6:
                ov = sum(b['v'] for b in closed[:6])
                fusion = OE.opening_dir_fusion(closed[:6], closed[0]['o'], ov, ctx.get("med_ov"),
                                               pdh=ctx.get("pdh"), pdl=ctx.get("pdl"),
                                               prior_vah=ctx.get("vah"), prior_val=ctx.get("val"))
                if fusion is not None or n >= 8: fusion_done = True
            trig = OE.evaluate_opening_entry(closed, fired, window_last_bar=12, enable_pullback=True, bias=None)
            if not trig: continue
            gate = None
            if fusion_done and (fusion is None or fusion != trig["direction"]):
                gate = f"fusion={fusion}"
            ok, why = OE.opening_first_trade_ok(closed, trig["direction"], None, min_bars=min_bars,
                                                trigger_type=trig.get("type"), closed_bars=closed)
            if gate is None and not ok:
                gate = "strict"
            if gate is not None:
                continue                            # held — engine keeps evaluating next bar (as live)
            fired.add(trig["type"])
            setup = OE.build_opening_setup(trig, closed, shadow_only=False)
            ot, bias = label_at(closed)
            rec = {"d": d, "il": decide['il'], "n": n, "type": trig["type"], "dir": trig["direction"],
                   "label": ot, "label_bias": bias, "phase": phase,
                   "admitted": admitted_today(ot, bias, trig["direction"], phase),
                   "move_from_open": round(abs(closed[-1]['c'] - closed[0]['o']), 2), "atr_d": round(atr or 0, 1)}
            if setup is None:
                rec.update(skipped="risk>25", usd1=0.0, usd2=0.0, risk=None); cands.append(rec); continue
            legs1, e = price(bars, n, trig["direction"], setup["stop"], [setup["t1"]])
            legs2, _ = price(bars, n, trig["direction"], setup["stop"], [setup["t1"], setup["t2"]])
            rec.update(entry=round(e, 2), stop=setup["stop"], t1=setup["t1"], t2=setup["t2"],
                       risk=round(abs(e - setup["stop"]), 2), ev1=legs1[0][0], usd1=round(usd(legs1), 2),
                       ev2="/".join(x[0] for x in legs2), usd2=round(usd(legs2), 2), skipped=None)
            cands.append(rec)
    return cands

def summarize(cs, title):
    cs = [c for c in cs if not c.get("skipped")]
    if not cs:
        print(f"  {title}: N=0"); return
    u = [c["usd1"] for c in cs]; u2 = [c["usd2"] for c in cs]
    w = sum(1 for c in cs if c["ev1"] == "T1"); l = sum(1 for c in cs if c["ev1"] == "STOP")
    a = sum(1 for c in cs if c["ev1"] == "AMBIG"); e = sum(1 for c in cs if c["ev1"] == "EOD")
    print(f"  {title:44s} N={len(cs):3d}  T1={w:3d} STOP={l:3d} AMBIG={a:2d} EOD={e:2d}  "
          f"win%={100*w/max(1,w+l):4.0f}  Σ$1c={sum(u):8.1f} avg={statistics.mean(u):7.1f} med={statistics.median(u):7.1f}  "
          f"| Σ$2c={sum(u2):8.1f}")

cands3 = run(3)
cands2 = run(2)
print(f"sessions={len(days)} ({days[0]}..{days[-1]}), excluded={len([d for d in alld if d in EXC])}, "
      f"model: entry=next open±{SLIP/2}, stop/T1/T2 from build_opening_setup (T1={os.environ['T1_BANK_R']}R, cap 15/skip 25), first-touch, AMBIG unassigned, EOD close")
for mb, cands in ((3, cands3), (2, cands2)):
    print(f"\n=== min confirmation bars = {mb} ===")
    sk = [c for c in cands if c.get("skipped")]
    print(f"  candidates={len(cands)}  skipped(risk>25)={len(sk)}")
    for typ in ("DRIVE", "TEST_DRIVE", "ORR", "PULLBACK_CONT", "EXTREME_REJECT"):
        cs = [c for c in cands if c["type"] == typ]
        if not cs: continue
        summarize(cs, f"{typ} — all")
        summarize([c for c in cs if c["admitted"]], f"{typ} — admitted by today's tree")
        summarize([c for c in cs if not c["admitted"]], f"{typ} — BLOCKED today (label lag, T-426)")
    dr = [c for c in cands if c["type"] == "DRIVE"]
    print("  DRIVE by decision bar (n closed bars → entry at bar n+1):")
    for n in sorted(set(c["n"] for c in dr)):
        summarize([c for c in dr if c["n"] == n], f"    n={n} ({'16:%02d' % (30+5*n) if 30+5*n < 60 else '17:%02d' % (5*n-30)})")
    print("  DRIVE by structural risk (pts):")
    for lo, hi in ((0, 8), (8, 12), (12, 15.01), (15.01, 99)):
        summarize([c for c in dr if c.get("risk") is not None and lo <= c["risk"] < hi], f"    risk [{lo},{hi})")
    print("  DRIVE by move-from-open at decision / daily ATR:")
    for lo, hi in ((0, 0.15), (0.15, 0.3), (0.3, 9)):
        summarize([c for c in dr if c["atr_d"] and lo <= c["move_from_open"]/c["atr_d"] < hi], f"    move/ATRd [{lo},{hi})")
    print("  DRIVE by label at decision:")
    for lab in sorted(set(c["label"] for c in dr)):
        summarize([c for c in dr if c["label"] == lab], f"    label={lab}")

print("\n=== DRIVE candidates, min_bars=3 (date time dir entry stop t1 risk | label admitted | 1c result $ | 2c) ===")
for c in [c for c in cands3 if c["type"] == "DRIVE"]:
    if c.get("skipped"):
        print(f"  {c['d']} {c['il']} n={c['n']} {c['dir']:5s} SKIPPED {c['skipped']} label={c['label']}")
        continue
    print(f"  {c['d']} {c['il']} n={c['n']} {c['dir']:5s} e={c['entry']:8.2f} s={c['stop']:8.2f} t1={c['t1']:8.2f} r={c['risk']:5.2f} "
          f"| {c['label']:22s} {'ADMIT' if c['admitted'] else 'BLOCK'} | {c['ev1']:5s} {c['usd1']:7.1f} | {c['ev2']:9s} {c['usd2']:7.1f}")
if args.csv:
    import csv
    keys = sorted({k for c in cands3 + cands2 for k in c})
    with open(args.csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["min_bars"] + keys); w.writeheader()
        for mb, cs in ((3, cands3), (2, cands2)):
            for c in cs: w.writerow({"min_bars": mb, **c})
    print(f"csv → {args.csv}")
