# -*- coding: utf-8 -*-
"""Circumstance deck v2 (Michael 20.10 23:5x: "I don't need you to test me — I need us to improve the system,
so it must be general: something that lets us improve the trees in these circumstances").

Unit = a CIRCUMSTANCE = a decision-tree TAKE leaf (its path) and, inside it, the one vector feature value where
the money is lost (zone / pattern / direction / rel_bias / edge / poc_side / ...). Source = the base-20.10 replay
(harness_out/base2010/hist_base2010_*.json: every route carries tree_v3 {leaf, id, path, vec}; executed routes map
to settled trades with pnl_usd / t1_before_stop / mfe_pts). Each card proposes a tree rule; Michael rules on the
circumstance (skip / edge-only / keep / measure) and the ruling becomes a tree variant measured overnight.

usage: python3 ~/mems26_circ_extract.py [--min-n 5] → harness_out/swipe/circ_v2.json
"""
import collections, glob, hashlib, json, os, sys
import datetime as dt
from zoneinfo import ZoneInfo
import psycopg2

REPO = "/Users/michael/Downloads/mems26_web_git"
OUT = REPO + "/harness_out/swipe/circ_v2.json"
MIN_N = int(sys.argv[sys.argv.index("--min-n") + 1]) if "--min-n" in sys.argv else 5
IL, ET, UTC = ZoneInfo("Asia/Jerusalem"), ZoneInfo("America/New_York"), dt.timezone.utc
FEATS = ["zone", "pattern", "direction", "rel_bias", "edge", "poc_side", "value_migration", "prior_zone",
         "structure", "test", "turn_rel", "volume", "kind", "day_type", "opening_type", "phase"]


def _live_dates():
    s = set("2026-10-20 2026-10-19 2026-10-16 2026-10-15 2026-10-14 2026-10-13 2026-10-12".split())
    try:
        s |= {ln.strip() for ln in open("/Users/michael/mems26_hist/sessions70.txt") if ln.strip()}
    except OSError:
        pass
    return s


def load_samples():
    out, sessions = [], set()
    for f in sorted(glob.glob(REPO + "/harness_out/base2010/hist_base2010_*.json")):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        day = d.get("session") or os.path.basename(f)[15:25]
        sessions.add(day)
        trades = {t.get("trade_id"): t for t in d.get("trades") or []}
        for r in d.get("routes") or []:
            tv = r.get("tree_v3") or {}
            if tv.get("leaf") != "TAKE":
                continue
            tid = (((r.get("exec") or {}).get("live")) or {}).get("trade_id")
            t = trades.get(tid)
            if not t or not t.get("filled") or t.get("pnl_usd") is None:
                continue
            vec = tv.get("vec") or {}
            # the REAL T1: leg t1_leg (2 when the T0 leg is on — the harness's t1_target is leg 1, i.e. T0 there)
            e = t.get("fill_price") or t.get("entry")
            legs = t.get("legs") or []
            k = int(t.get("t1_leg") or 1)
            t1px = legs[k - 1].get("target") if len(legs) >= k and legs[k - 1].get("target") else t.get("t1_target")
            sgn = 1 if (r.get("direction") or "").upper() == "LONG" else -1
            t1pts = round(sgn * (float(t1px) - float(e)), 2) if (t1px and e) else None
            out.append(dict(day=day, il=r.get("il"), cls=r.get("classification"), dir=(r.get("direction") or "").upper(),
                            entry=e, leaf=tv.get("id") or tv.get("path"),
                            path=tv.get("path"), vec=vec, pnl=float(t["pnl_usd"]), t1=bool(t.get("t1_before_stop")),
                            mfe=None, mae=None, t1pts=t1pts, outcome=t.get("outcome"),
                            stop=t.get("stop_initial"), t1px=t1px, exit_il=t.get("exit_il"),
                            n=t.get("contracts")))
    return out, sorted(sessions)


def stats(S, holdout_days):
    n = len(S)
    if not n:
        return dict(n=0)
    w = sum(1 for s in S if s["pnl"] > 0)
    t1 = sum(1 for s in S if s["t1"])
    tot = sum(s["pnl"] for s in S)
    months = collections.defaultdict(float)
    for s in S:
        months[s["day"][:7]] += s["pnl"]
    ho = [s for s in S if s["day"] in holdout_days]
    return dict(n=n, win=round(100.0 * w / n), t1=round(100.0 * t1 / n), sum=round(tot, 2), avg=round(tot / n, 2),
                days=len({s["day"] for s in S}), months={k: round(v, 2) for k, v in sorted(months.items())},
                holdout_n=len(ho), holdout_sum=round(sum(s["pnl"] for s in ho), 2))


def cid(*parts):
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:12]


def bars_for(day, t_il, after_min=150):
    db = "mems26" if day in LIVE else "mems26_hist"
    try:
        c = psycopg2.connect(dbname=db)
        q = c.cursor()
        h, m = [int(x) for x in t_il.split(":")[:2]]
        t0 = dt.datetime.fromisoformat(day).replace(hour=h, minute=m, tzinfo=IL)
        q.execute("""select ts, open, high, low, close from v9_bars_5min_woodies where symbol='MES'
                     and ts >= %s and ts <= %s order by ts""",
                  (t0 - dt.timedelta(minutes=60), t0 + dt.timedelta(minutes=after_min)))
        rows = q.fetchall()
        c.close()
        seen, out = set(), []
        for ts, o, hh, ll, cc in rows:
            k = int(ts.timestamp())
            if k in seen:
                continue
            seen.add(k)
            out.append([k, float(o), float(hh), float(ll), float(cc)])
        return out
    except Exception:
        return []


def _ep(day, t_il):
    try:
        h, m = [int(x) for x in str(t_il).split(":")[:2]]
        return int(dt.datetime.fromisoformat(day).replace(hour=h, minute=m, tzinfo=IL).timestamp())
    except Exception:
        return None


def ex_of(s, with_bars):
    e = dict(day=s["day"], il=s["il"], cls=s["cls"], dir=s["dir"], entry=s["entry"], stop=s["stop"], t1px=s["t1px"],
             pnl=s["pnl"], t1=s["t1"], mfe=s["mfe"], t1pts=s["t1pts"], exit_il=s["exit_il"], outcome=s["outcome"],
             zone=s["vec"].get("zone"), n=s["n"], te=_ep(s["day"], s["il"]), tx=_ep(s["day"], s["exit_il"]))
    if with_bars and s.get("il"):
        e["bars"] = bars_for(s["day"], s["il"])
    return e


def main():
    global LIVE
    LIVE = _live_dates()
    S, sessions = load_samples()
    holdout = set(sessions[-10:])
    by_leaf = collections.defaultdict(list)
    for s in S:
        by_leaf[s["leaf"]].append(s)
    cards = []
    for leaf, L in by_leaf.items():
        if len(L) < MIN_N:
            continue
        st_leaf = stats(L, holdout)
        vec0 = L[0]["vec"]
        cand = []
        for f in FEATS:
            groups = collections.defaultdict(list)
            for s in L:
                groups[str(s["vec"].get(f, "?"))].append(s)
            if len(groups) < 2:
                continue
            for v, G in groups.items():
                if len(G) < MIN_N or len(G) == len(L):
                    continue
                st = stats(G, holdout)
                if st["sum"] >= 0:
                    continue
                rest = [s for s in L if str(s["vec"].get(f, "?")) != v]
                cand.append((st["sum"], f, v, st, stats(rest, holdout), G))
        cand.sort(key=lambda x: x[0])
        used = []
        for tot, f, v, st, rest, G in cand:
            ids = frozenset(id(g) for g in G)
            if any(len(ids & u) >= 0.8 * len(ids) for u in used):
                continue          # same trades as a card already proposed for this leaf
            used.append(ids)
            worst = sorted(G, key=lambda s: s["pnl"])[:3]
            best = sorted(G, key=lambda s: -s["pnl"])[:1]
            cards.append(dict(id=cid(leaf, f, v), kind="split", leaf=leaf, path=L[0]["path"], feature=f, value=v,
                              vec0=G[0]["vec"],
                              stats=st, rest=rest, leaf_stats=st_leaf, vec_leaf={k: vec0.get(k) for k in
                              ("opening_type", "phase", "day_type", "rel_bias", "pattern", "direction")},
                              proposal=dict(action="SKIP", when={f: v}, est_delta=round(-st["sum"], 2)),
                              examples=[ex_of(s, i < 2) for i, s in enumerate(worst)] + [ex_of(s, False) for s in best
                                                                                          if s not in worst]))
            if len([c for c in cards if c["leaf"] == leaf]) >= 3:
                break
        if st_leaf["sum"] < 0 and st_leaf["n"] >= 2 * MIN_N:
            worst = sorted(L, key=lambda s: s["pnl"])[:2]
            cards.append(dict(id=cid(leaf, "*"), kind="leaf", leaf=leaf, path=L[0]["path"], feature=None, value=None,
                              vec0=L[0]["vec"],
                              stats=st_leaf, rest=None, leaf_stats=st_leaf,
                              vec_leaf={k: vec0.get(k) for k in ("opening_type", "phase", "day_type", "rel_bias",
                                                                 "pattern", "direction")},
                              proposal=dict(action="SKIP", when={}, est_delta=round(-st_leaf["sum"], 2)),
                              examples=[ex_of(s, True) for s in worst]))
    cards.sort(key=lambda c: c["stats"]["sum"])
    leaves = sorted(({"leaf": k, **stats(v, holdout)} for k, v in by_leaf.items()), key=lambda x: x["sum"])
    meta = dict(built=dt.datetime.now(IL).strftime("%Y-%m-%d %H:%M"), version="base-20.10", sessions=len(sessions),
                first=sessions[0] if sessions else None, last=sessions[-1] if sessions else None,
                samples=len(S), total=round(sum(s["pnl"] for s in S), 2), min_n=MIN_N, holdout=sorted(holdout))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(dict(meta=meta, cards=cards[:40], leaves=leaves), open(OUT, "w"), ensure_ascii=False, default=str)
    print("sessions", len(sessions), "samples", len(S), "Σ", meta["total"], "leaves", len(by_leaf), "cards", len(cards))
    for c in cards[:12]:
        st = c["stats"]
        print(" %-5s %-11s %-18s n=%3d win=%3d%% T1=%3d%% Σ=%8.2f | %s" % (c["kind"], c["feature"] or "*",
              str(c["value"])[:18], st["n"], st["win"], st["t1"], st["sum"], c["leaf"][:90]))


if __name__ == "__main__":
    main()
