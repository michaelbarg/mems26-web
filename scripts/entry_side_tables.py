#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""entry_side_tables.py — turn the entry_side_replay JSON dumps into the tables.

Reads /tmp/esr_e1.json /tmp/esr_e2.json /tmp/esr_e3.json /tmp/esr_comb.json and
prints the rows used in docs/reports/REPLAY_ENTRY_SIDE_2026-08-22.md.  READ-ONLY.
"""
import json
import os
import statistics

SLIPS = (0, 1, 2)
BASE = "k0.0_r2_a0"


def med(xs):
    return round(statistics.median(xs), 2) if xs else 0.0


def daymap(arm, slip):
    return {r["day"]: r["usd"] for r in arm["by_slip"][str(slip)]["days"]}


def e1(path="/tmp/esr_e1.json"):
    if not os.path.exists(path):
        return {}
    j = json.load(open(path))
    e = j["e1"]
    base = e[BASE]
    print("\n=== E1 · k x ATR pivot tolerance  x  right-shoulder confirmation bars ===")
    print("arm            fires  new  newLose | " + " | ".join(
        f"s{s}: total   delta  dExBest medAll medAct +/-/=" for s in SLIPS))
    kb = {(f["day"], f["i"], f["kind"], f["dir"]) for f in base["fire_list"]}
    out = {}
    for arm_name, arm in e.items():
        ka = {(f["day"], f["i"], f["kind"], f["dir"]) for f in arm["fire_list"]}
        new = ka - kb
        cells, row = [], {"fires": arm["fires"], "new": len(new)}
        nl = 0
        for s in SLIPS:
            da, db = daymap(arm, s), daymap(base, s)
            dys = sorted(set(da) | set(db))
            tot = round(sum(da.get(d, 0.0) for d in dys), 2)
            dl = [round(da.get(d, 0.0) - db.get(d, 0.0), 2) for d in dys]
            act = [x for d, x in zip(dys, dl) if da.get(d, 0.0) or db.get(d, 0.0)]
            up = sum(1 for x in dl if x > 0.01)
            dn = sum(1 for x in dl if x < -0.01)
            eq = len(dl) - up - dn
            ex = round(sum(dl) - max(dl), 2) if dl else 0.0   # drop the best day
            cells.append(f"{tot:>8.2f} {round(sum(dl),2):>8.2f} {ex:>8.2f} "
                         f"{med(dl):>6.2f} {med(act):>6.2f} {up:>2d}/{dn:d}/{eq:d}")
            row[f"s{s}"] = dict(total=tot, delta=round(sum(dl), 2), med=med(dl),
                                med_active=med(act), up=up, dn=dn, eq=eq,
                                delta_ex_best=ex, n=arm["by_slip"][str(s)]["n"])
            if s == 1:
                for dd in arm["by_slip"]["1"]["days"]:
                    for t in dd["trades"]:
                        if (dd["day"], t["i"], t["kind"], t["dir"]) in new and t["usd"] < 0:
                            nl += 1
        row["new_lose"] = nl
        row["n_s1"] = arm["by_slip"]["1"]["n"]
        out[arm_name] = row
        print(f"{arm_name:14s} {arm['fires']:>5d} {len(new):>4d} {nl:>8d} | "
              + " | ".join(cells))
    # per-kind breakdown at slip 1 for base and best arm
    print("\n-- E1 fires by pattern kind --")
    for arm_name in e:
        cnt = {}
        for f in e[arm_name]["fire_list"]:
            cnt[f["kind"]] = cnt.get(f["kind"], 0) + 1
        print(f"{arm_name:14s} {cnt}")
    return out


def e2(path="/tmp/esr_e2.json"):
    if not os.path.exists(path):
        return {}
    j = json.load(open(path))
    print("\n=== E2 · limit/stop AT LEVEL (tick fill) vs market-on-close ===")
    lv = [r for d in j["e2"]["days"] for r in d["rows"]]
    ct = sum(1 for r in lv if r["closed"])
    print(f"structural levels touched={len(lv)} · bar CLOSED through={ct} · "
          f"touched-but-no-close={len(lv)-ct} ({round(100*(len(lv)-ct)/max(1,len(lv)))}%)")
    names = ("CLOSE", "TOUCH", "TOUCH_FLOW", "TOUCH_CONFIRMED")
    out = {}
    for s in SLIPS:
        m = j["e2"]["mech"][str(s)]
        ck = {(x["day"], x["i"]) for x in m["CLOSE"]}
        imp = [x["dir"] * (x["close"] - x["lvl"]) for x in m["TOUCH"]
               if (x["day"], x["i"]) in ck]
        row = {}
        for name in names:
            xs = m.get(name, [])
            fs = [x for x in xs if not x["closed"]]
            row[name] = dict(n=len(xs), usd=round(sum(x["usd"] for x in xs), 2),
                             false_starts=len(fs),
                             fs_usd=round(sum(x["usd"] for x in fs), 2),
                             fs_lose=sum(1 for x in fs if x["usd"] < 0),
                             win=sum(1 for x in xs if x["usd"] > 0))
        row["avg_improve_pts"] = round(statistics.fmean(imp), 2) if imp else 0.0
        row["med_improve_pts"] = med(imp)
        out[s] = row
        print(f"\nslip {s} (avg entry improvement on the shared subset = "
              f"{row['avg_improve_pts']} pt, median {row['med_improve_pts']} pt)")
        print(f"  {'mechanism':16s} {'n':>4s} {'$':>10s} {'win':>4s} "
              f"{'falseStart':>10s} {'fs$':>10s} {'fsLose':>6s} {'vsCLOSE$':>9s}")
        for name in names:
            v = row[name]
            print(f"  {name:16s} {v['n']:>4d} {v['usd']:>10.2f} {v['win']:>4d} "
                  f"{v['false_starts']:>10d} {v['fs_usd']:>10.2f} {v['fs_lose']:>6d} "
                  f"{round(v['usd']-row['CLOSE']['usd'],2):>9.2f}")
    print("\n-- E2 per-day deltas vs CLOSE (slip 1) --")
    m = j["e2"]["mech"]["1"]
    dd = {}
    for name in names:
        for x in m.get(name, []):
            dd.setdefault(x["day"], {}).setdefault(name, 0.0)
            dd[x["day"]][name] += x["usd"]
    pd = {}
    for name in names[1:]:
        dl = [round(v.get(name, 0) - v.get("CLOSE", 0), 2) for v in dd.values()]
        pd[name] = dict(sum=round(sum(dl), 2), med=med(dl),
                        up=sum(1 for x in dl if x > 0.01),
                        dn=sum(1 for x in dl if x < -0.01),
                        eq=sum(1 for x in dl if abs(x) <= 0.01))
        print(f"  {name:16s} sum={pd[name]['sum']:>9.2f} med={pd[name]['med']:>7.2f} "
              f"+/-/= {pd[name]['up']}/{pd[name]['dn']}/{pd[name]['eq']}")
    out["perday"] = pd
    return out


def e3(path="/tmp/esr_e3.json"):
    if not os.path.exists(path):
        return {}
    j = json.load(open(path))
    print("\n=== E3 · mid-trade day-type policy switch ===")
    tl = j.get("labels", [])
    print(f"sessions={len(tl)} · with >=1 causal transition="
          f"{sum(1 for x in tl if x['transitions'])} · "
          f"median transitions/session={med([x['transitions'] for x in tl])} · "
          f"max={max([x['transitions'] for x in tl] or [0])}")
    out = {"labels": tl}
    for src in ("e3_causal", "e3_db_live"):
        rows = j.get(src, [])
        print(f"\n-- {src} · n={len(rows)} --")
        if rows:
            print(f"  {'day':11s} {'id':>4s} {'pattern':22s} {'label change':34s} "
                  f"{'booked':>8s} {'base':>9s} {'switch':>9s} {'delta':>8s} exit")
        for r in rows:
            d = round(r["sw_s1"] - r["base_s1"], 2)
            print(f"  {r['day']:11s} {r['id']:>4d} {r['pat'][:22]:22s} "
                  f"{(r['lab0']+' -> '+r['lab1'])[:34]:34s} {r['booked']:>8.2f} "
                  f"{r['base_s1']:>9.2f} {r['sw_s1']:>9.2f} {d:>8.2f} "
                  f"{r['basereason_s1']}->{r['swreason_s1']}")
        st = {}
        for s in SLIPS:
            act = [r for r in rows if r["differs"]]
            dl = [round(r[f"sw_s{s}"] - r[f"base_s{s}"], 2) for r in act]
            st[s] = dict(n=len(rows), actionable=len(act), total=round(sum(dl), 2),
                         med=med(dl), up=sum(1 for x in dl if x > 0.01),
                         dn=sum(1 for x in dl if x < -0.01),
                         eq=sum(1 for x in dl if abs(x) <= 0.01))
            print(f"  slip{s}: policy-differs={len(act)} delta=${st[s]['total']} "
                  f"med=${st[s]['med']} +/-/= {st[s]['up']}/{st[s]['dn']}/{st[s]['eq']}")
        out[src] = st
    return out


def comb(path="/tmp/esr_comb.json"):
    if not os.path.exists(path):
        return {}
    j = json.load(open(path))
    c = j["comb"]
    base = c.get("base_trail") or c["baseline_today"]
    print("\n=== COMBINED · one candidate stream, playbook management ===")
    print(f"{'variant':16s} " + " ".join(
        f"| s{s}: total    delta  medDay  +/-/=  n" for s in SLIPS))
    out = {}
    for tag, per in c.items():
        cells, row = [], {}
        bb = c.get("base_ladder") if tag.endswith("_ladder") else base
        for s in SLIPS:
            da = {x["day"]: x["usd"] for x in per[str(s)]["days"]}
            db = {x["day"]: x["usd"] for x in (bb or base)[str(s)]["days"]}
            dys = sorted(set(da) | set(db))
            dl = [round(da.get(d, 0.0) - db.get(d, 0.0), 2) for d in dys]
            cells.append(f"| {per[str(s)]['total']:>8.2f} {round(sum(dl),2):>8.2f} "
                         f"{med(dl):>7.2f} {sum(1 for x in dl if x>0.01)}/"
                         f"{sum(1 for x in dl if x<-0.01)}/"
                         f"{sum(1 for x in dl if abs(x)<=0.01)} {per[str(s)]['n']:>3d}")
            row[f"s{s}"] = dict(total=per[str(s)]["total"], delta=round(sum(dl), 2),
                                med=med(dl), n=per[str(s)]["n"],
                                up=sum(1 for x in dl if x > 0.01),
                                dn=sum(1 for x in dl if x < -0.01),
                                eq=sum(1 for x in dl if abs(x) <= 0.01))
        out[tag] = row
        print(f"{tag:16s} " + " ".join(cells))
    return out


if __name__ == "__main__":
    r = {"e1": e1(), "e2": e2(), "e3": e3(), "comb": comb()}
    json.dump(r, open("/tmp/esr_tables.json", "w"), default=str)
    print("\n[out] /tmp/esr_tables.json")
