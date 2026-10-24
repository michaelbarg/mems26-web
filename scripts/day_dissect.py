#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""day_dissect.py — DAYMAP («פירוק-יום»), version base-20.10 («בסיס-20.10»).

Michael 20.10: for every day we have data on (live/demo, or replayed) split the day into phases and know what day it
was, what opening, what trades the system was looking for, how System 6 managed each trade, and for each fire what
could happen if it was wrong — to sharpen opening type, day type and timely firing per day type.

One JSON per ET session date: <out>/<D>.json with the shared market/truth blocks and one block per view:
  live   — v9_trades (live/demo = fired; shadow = would-fire / blocked + the S1 label snapshot), v9_trade_management_log
           (System 6), v9_day_type_state / v9_day_type_history / v9_decision_vectors (labels), backend log (T-314 opening
           lock, BE_RULE), gateway archive (live gates after the tree).
  replay — a harness JSON (s1[] label timeline, routes[], trades[]); bars from the harness DB (mems26_hist → mems26).
Truth = Michael's label (harness_out/swipe/labels.json) when present, else the rule-based reference (daymap_lib.ref_*).

READ-ONLY: the DB is opened read-only; the only files written are <out>/<D>.json. Never runs the harness.

  python3 scripts/day_dissect.py --date 2026-10-19 [--date 2026-10-16,2026-10-09]
  python3 scripts/day_dissect.py --all                      (live days ≥60 RTH bars since 2026-07-07 + every replay file)
  python3 scripts/day_dissect.py --since 2026-09-01 [--until 2026-09-30] [--no-replay|--no-live]
  options: --version base-20.10 --replay-dir harness_out/t466 --replay-glob 'hist_po_*.json'
           --labels harness_out/swipe/labels.json --out harness_out/daymap/base-20.10/
"""
import os, sys, re, json, glob, time, argparse, collections, datetime as dt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import daymap_lib as L  # noqa: E402

REPO = L.REPO
V2_TRUTH = {}   # T-646: --truth-opening JSON {date: {opening, direction, lock_bar, ...}} — opening truth = v2 (Michael 24.10)
SKIP_PATTERNS = {"SIM_TEST"}
SKIP_OUTCOMES = {"CANCELLED", "REJECTED", "PHANTOM"}
TML_SKIP = {"PNL_CORRECTION", "TRADER_REVIEW"}
SCHEMA = 1


# ── args ─────────────────────────────────────────────────────────────────────────────────────────
def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="DAYMAP — per-day dissection (read-only)")
    ap.add_argument("--date", action="append", help="YYYY-MM-DD; repeatable or comma-separated")
    ap.add_argument("--all", action="store_true", help="every live day since --live-since + every replay file")
    ap.add_argument("--since"); ap.add_argument("--until")
    ap.add_argument("--version", default=L.VERSION_DEFAULT)
    ap.add_argument("--replay-dir", default=None)
    ap.add_argument("--replay-glob", default=None)
    ap.add_argument("--labels", default=os.path.join(REPO, "harness_out", "swipe", "labels.json"))
    ap.add_argument("--truth-opening", default=None,
                    help="T-646: JSON {date: {opening, direction, lock_bar}} used as the opening truth (v2) instead of ref_opening")
    ap.add_argument("--out", default=None)
    ap.add_argument("--live-since", default="2026-07-07")
    ap.add_argument("--no-live", action="store_true"); ap.add_argument("--no-replay", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    b2010 = os.path.join(REPO, "harness_out", "base2010")
    if a.replay_dir is None:
        if glob.glob(os.path.join(b2010, "hist_base2010_*.json")):
            a.replay_dir, a.replay_glob = b2010, a.replay_glob or "hist_base2010_*.json"
        else:
            a.replay_dir, a.replay_glob = os.path.join(REPO, "harness_out", "t466"), a.replay_glob or "hist_po_*.json"
    elif a.replay_glob is None:
        a.replay_glob = "hist_base2010_*.json" if glob.glob(os.path.join(a.replay_dir, "hist_base2010_*.json")) else "hist_po_*.json"
    if not os.path.isabs(a.replay_dir):
        a.replay_dir = os.path.join(REPO, a.replay_dir)
    if not os.path.isabs(a.labels):
        a.labels = os.path.join(REPO, a.labels)
    a.out = a.out or os.path.join(REPO, "harness_out", "daymap", a.version)
    if not os.path.isabs(a.out):
        a.out = os.path.join(REPO, a.out)
    return a


def replay_map(rdir, pattern):
    out = {}
    for p in sorted(glob.glob(os.path.join(rdir, pattern))):
        m = re.search(r"(\d{4}-\d\d-\d\d)\.json$", p)
        if m:
            out[m.group(1)] = p
    return out


def rel(p):
    return os.path.relpath(p, REPO) if p and p.startswith(REPO) else p


# ── label streams ────────────────────────────────────────────────────────────────────────────────
def obs(ep, dt_, ot, conf=None, stage=None, src=None, **kw):
    o = dict(ep=int(ep), dt=L.norm_dt(dt_), ot=L.norm_ot(ot), conf=L.r2(conf), stage=stage, src=src)
    o.update(kw)
    return o


def compress(stream):
    """Keep an observation only when (day_type, opening) changes; → [{t_il, dt, ot, conf, stage, src}]."""
    out, last = [], None
    for o in sorted(stream, key=lambda x: x["ep"]):
        k = (o["dt"], o["ot"])
        if k != last:
            out.append(dict(t_il=L.il_hm(o["ep"]), dt=o["dt"], ot=o["ot"], conf=o.get("conf"), stage=o.get("stage"), src=o.get("src"), ep=o["ep"]))
            last = k
    return out


def asof(stream, ep):
    last = None
    for o in stream:
        if o["ep"] <= ep:
            last = o
        else:
            break
    if not last:
        return dict(dt="UNKNOWN", ot="UNKNOWN", conf=None, t_il=None, src=None)
    return dict(dt=last["dt"], ot=last["ot"], conf=last.get("conf"), t_il=L.il_hm(last["ep"]), src=last.get("src"))


def flips_of(stream, ep_open):
    seq = [o["dt"] for o in stream if o["ep"] >= ep_open and o["dt"] != "UNKNOWN"]
    return sum(1 for a, b in zip(seq, seq[1:]) if a != b)


def conf01(x):
    if x is None:
        return None
    try:
        x = float(x)
    except Exception:
        return None
    return round(x / 100.0, 3) if x > 1.0 else round(x, 3)


# ── shared (market + truth) ──────────────────────────────────────────────────────────────────────
def load_bars_for(d, prefer_live):
    order = ["mems26", "mems26_hist"] if prefer_live else ["mems26_hist", "mems26"]
    best = None
    for db in order:
        try:
            day = L.load_day(d, db)
        except Exception:
            continue
        if len(day["rth"]) >= 60:
            return day
        if best is None or len(day["rth"]) > len(best["rth"]):
            best = day
    return best


def shared_day(d, day, labels):
    rth = day["rth"]
    today_et = dt.datetime.now(L.ET).date().isoformat()
    last_em = rth[-1]["em"] if rth else 0
    partial = bool(rth) and (last_em < 950 or (d == today_et and last_em < L.LAST_RTH_BAR_MIN))
    prev = L.session_profile(day["prev"]["rth"], day["prev"]["date"]) if day.get("prev") and day["prev"]["rth"] else None
    on = day["on"]
    o = rth[0]["o"] if rth else None
    atr0 = L.session_atr(rth)
    ib = L.ib_events(rth)
    ref_ot, ref_why = L.ref_opening(rth, prev)
    ref_dt, feats = L.ref_daytype(rth)
    if partial and ref_dt == "UNKNOWN" and len(rth) >= 13:   # partial day: the as-of reading (truth.partial = True)
        ref_dt, feats = L.ref_daytype_asof(rth, len(rth))
    ref_at = {}
    for lab, n, ep in L.checkpoint_epochs(d):
        if n > len(rth):
            ref_at[lab] = dict(dt=None, n=len(rth), t_il=L.il_hm(ep), future=True)
        else:
            lb, ft = L.ref_daytype_asof(rth, n)
            ref_at[lab] = dict(dt=lb, n=n, t_il=L.il_hm(ep), rib=ft.get("rib"), close_pos=ft.get("close_pos"))
    mich = (labels.get("days") or {}).get(d) or {}
    v2t = V2_TRUTH.get(d) or {}
    t_ot = mich.get("opening") or v2t.get("opening") or ref_ot
    t_dt = mich.get("day_type") or ref_dt
    truth = dict(opening=t_ot, opening_src="michael" if mich.get("opening") else ("v2" if v2t.get("opening") else "ref"),
                 v2_opening=v2t.get("opening"), v2_direction=v2t.get("direction"), v2_lock_bar=v2t.get("lock_bar"),
                 day_type=t_dt, day_type_src="michael" if mich.get("day_type") else "ref", note=mich.get("note") or "",
                 ref_opening=ref_ot, ref_opening_why=ref_why, ref_day_type=ref_dt,
                 ref_feats={k: (L.r2(v) if isinstance(v, float) else v) for k, v in feats.items()}, ref_at=ref_at, partial=partial)
    refs = dict(prev=({k: prev[k] for k in ("date", "high", "low", "close", "poc", "vah", "val")} if prev else None),
                overnight=(dict(high=max(b["h"] for b in on), low=min(b["l"] for b in on), n=len(on)) if on else None),
                open=o, open_loc=L.open_location(o, prev))
    bounds = L.phase_bounds(d)
    mkt = {}
    for p in L.PHASES:
        a, b = bounds[p]
        bs = on if p == "0" else [x for x in rth if a <= x["ts"] < b]
        m = L.market_of(bs) or {}
        m["ib_ev"] = L.ib_events_in(ib, (a, b)) if ib.get("complete") else []
        mkt[p] = m
    ib_out = {k: ({kk: v[kk] for kk in ("t_il", "px")} if isinstance(v, dict) else v) for k, v in ib.items()}
    return dict(rth=rth, on=on, prev=prev, atr0=atr0, ib=ib, bounds=bounds, partial=partial,
                rec=dict(refs=refs, truth=truth, mkt=mkt, ib=ib_out, atr=L.r2(atr0),
                         bars=dict(n_rth=len(rth), n_on=len(on), db=day["db"], first_il=rth[0]["il"] if rth else None,
                                   last_il=L.il_hm(rth[-1]["ts"] + 300) if rth else None)))


# ── live / demo inputs ───────────────────────────────────────────────────────────────────────────
def _sess_window(d, sh):
    """[prev RTH session 16:15 ET, d 16:15 ET) — overnight trades belong to the next session's phase 0."""
    pdate = (sh.get("prev") or {}).get("date")
    a = L.et_dt(pdate, 16, 15) if pdate else L.et_dt(d, 0, 0) - dt.timedelta(hours=8)
    return a, L.et_dt(d, 16, 15)


def _detail(action, v):
    v = v or {}
    try:
        if action in ("SMART_BE", "SWING_TRAIL", "STRUCT_TRAIL", "TRAIL"):
            return "%s→%s" % (v.get("from"), v.get("to"))
        if action == "TARGET_REALISM":
            return "%s %s→%s" % (v.get("target", "t?"), v.get("from"), v.get("to"))
        if action == "STOP_HIT_PARTIAL":
            return "%s@%s (נותרו %s)" % (v.get("qty"), v.get("fill_price"), v.get("remaining"))
        if action.endswith("_HIT") or action == "STOP_AFTER_T2":
            return ("@%s" % v["fill_price"]) if v.get("fill_price") is not None else ""
    except Exception:
        pass
    return json.dumps(v, ensure_ascii=False)[:60] if v else ""


def _plan(contracts, targets, groups, short, entry):
    """Per-contract target list (nearest first)."""
    tg = sorted([t for t in targets if t is not None and ((t < entry) if short else (t > entry))], key=lambda t: abs(t - entry))
    if not tg:
        return [None] * contracts
    if groups and isinstance(groups, list) and sum(int(g or 0) for g in groups) == contracts:
        out = []
        for k, g in enumerate(groups):
            out += [tg[min(k, len(tg) - 1)]] * int(g or 0)
        return out
    return [tg[min(k, len(tg) - 1)] for k in range(contracts)]


def live_inputs(d, sh, logs):
    w0, w1 = _sess_window(d, sh)
    inp = dict(view="live", src="db", stream=[], gate=[], fires=[], would=[], blocked=[], lock=None, negs=[], relocks=[],
               first_read=None, prov=[], eod=None, meta={})
    # real trades
    rows = L.query("""select id, mode, firing_system, direction, state, extract(epoch from entry_ts)::bigint, entry_price, stop, t1, t2, t3, t4,
        extract(epoch from exit_ts)::bigint, exit_price, exit_reason, pnl_usd, pnl_sierra, outcome, day_type_at_entry, pattern_id_at_entry,
        quality, cross_context->0->'systems'->'day_type_machine'
        from v9_trades where mode in ('live','demo') and coalesce(entry_ts, created_at) >= %s and coalesce(entry_ts, created_at) < %s
        order by coalesce(entry_ts, created_at), id""", (w0, w1))
    ids = [r[0] for r in rows]
    tml = collections.defaultdict(list)
    if ids:
        for tid, ep, action, val in L.query("select trade_id, extract(epoch from ts)::bigint, action, value from v9_trade_management_log "
                                            "where trade_id = any(%s) order by trade_id, ts, id", (ids,)):
            if action in TML_SKIP:
                continue
            lst = tml[tid]
            key = (action, json.dumps(val, sort_keys=True, default=str))
            if lst and lst[-1]["_k"] == key:
                continue
            if action.endswith("_HIT") and any(x["action"] == action for x in lst):   # repeated fills of the same target
                continue
            lst.append(dict(ep=int(ep), t_il=L.il_hm(ep), action=action, detail=_detail(action, val), _k=key))
    be = (logs.get(d) or {}).get("be") or {}
    for (tid, mode, sysno, direction, state, te, entry, stop, t1, t2, t3, t4, tx, xpx, xr, pnl_usd, pnl_s, outc, dta, pat, q, dtm) in rows:
        q = q or {}; meta = q.get("metadata") or {}; sit = meta.get("situation") or {}; dtm = dtm or {}
        pat = pat or q.get("pattern_name") or q.get("classification") or "?"
        if pat in SKIP_PATTERNS or state == "CANCELLED" or (outc in SKIP_OUTCOMES) or te is None or entry is None:
            continue
        short = direction == "SHORT"
        try:
            n = max(1, int(float(q.get("contracts") or 1)))
        except Exception:
            n = 1
        stop0 = q.get("initial_stop") or q.get("entry_stop") or meta.get("stop_initial") or stop
        pt = q.get("planned_targets") or {}
        targets = [pt.get("t1", t1), pt.get("t2", t2), pt.get("t3", t3), pt.get("t4", t4)]
        fills = []
        for fl in (q.get("exit_fills") or []):
            try:
                fills.append((L.epoch(fl.get("ts")), int(fl.get("qty") or 1), fl.get("kind"), float(fl.get("price"))))
            except Exception:
                pass
        closed = state == "CLOSED"
        if not fills and closed and tx and xpx is not None:
            fills = [(int(tx), n, xr, float(xpx))]
        usd = pnl_s if pnl_s is not None else pnl_usd
        usd_open = None
        if not closed:                 # an open trade: its books P&L is partial (realised legs so far) — not a result
            usd_open, usd = usd, None
        th_dt = dta or sit.get("day_type") or dtm.get("day_type")
        th_src = "day_type_at_entry" if dta else ("situation" if sit.get("day_type") else ("machine" if dtm.get("day_type") else None))
        sys6 = [{k: v for k, v in x.items() if k != "_k"} for x in tml.get(tid, [])]
        b = be.get(str(tid))
        inp["fires"].append(dict(id=tid, src=mode, sys=sysno, pat=pat, fam=L.fam_of(pat), dir=direction, short=short, te=int(te),
                                 tx=int(tx) if (tx and closed) else None, entry=float(entry), stop0=L.r2(stop0), targets=[L.r2(t) for t in targets if t is not None],
                                 plan=_plan(n, targets, q.get("ladder_groups"), short, float(entry)), contracts=n, fills=fills,
                                 usd=L.r2(usd), usd_open=L.r2(usd_open),
                                 usd_src=("sierra" if pnl_s is not None else ("books" if pnl_usd is not None else None)) if closed else None,
                                 pts=(L.r2(usd / (L.USD_PT * n)) if usd is not None else None),
                                 outcome=("OPEN" if not closed else (outc or "?")), exit_px=L.r2(xpx), exit_reason=xr,
                                 thesis=dict(dt=L.norm_dt(th_dt), ot=L.norm_ot(sit.get("opening_type") or dtm.get("opening_type")), src=th_src),
                                 sys6=sys6, be_rule=(("%s: %s" % (b["rule"], b["reason"])) if b and b.get("reason") else (b["rule"] if b else None)),
                                 parent=meta.get("scale_in_parent"), mfe=None, mae=None))
        if dtm.get("day_type") or dtm.get("opening_type"):
            inp["stream"].append(obs(te, dtm.get("day_type"), dtm.get("opening_type"), conf01(dtm.get("confidence")), dtm.get("stage"), "trade"))
    # shadow trades: would-fire (passed every gate), blocked candidates, and the S1 label snapshot at each entry
    real = [(f["sys"], f["dir"], f["te"], f["fam"]) for f in inp["fires"]]
    seen = set()
    for (sid, sysno, direction, te, entry, stop, t1, outc, pnl, blk, pat, dtm, tx, xpx) in L.query(
            """select id, firing_system, direction, extract(epoch from coalesce(entry_ts, created_at))::bigint, entry_price, stop, t1, outcome, pnl_usd,
               quality->>'blocked_by', coalesce(pattern_id_at_entry, quality->>'pattern_name', quality->>'classification'),
               cross_context->0->'systems'->'day_type_machine', extract(epoch from exit_ts)::bigint, exit_price
               from v9_trades where mode='shadow' and coalesce(entry_ts, created_at) >= %s and coalesce(entry_ts, created_at) < %s order by 4, 1""", (w0, w1)):
        dtm = dtm or {}
        if dtm.get("day_type") or dtm.get("opening_type"):
            inp["stream"].append(obs(te, dtm.get("day_type"), dtm.get("opening_type"), conf01(dtm.get("confidence")), dtm.get("stage"), "shadow",
                                     lock=dtm.get("lock_state")))
        if te is None or entry is None or (pat or "") in SKIP_PATTERNS:
            continue
        fam = L.fam_of(pat); short = direction == "SHORT"
        if blk:
            inp["blocked"].append(dict(te=int(te), dir=direction, fam=fam, pat=pat, gate=blk, sys=sysno))
            continue
        if any(s == sysno and dd == direction and abs(t - te) <= 90 and f == fam for s, dd, t, f in real):
            continue   # the shadow twin of a real fire
        k = (sysno, pat, direction, int(te) // 300)
        if k in seen:
            continue    # T-252: the detector re-runs on the building bar — one thesis per bar
        seen.add(k)
        bp = (L.r2((float(entry) - float(xpx)) if short else (float(xpx) - float(entry))) if xpx is not None else None)
        inp["would"].append(dict(id=sid, src="shadow", sys=sysno, pat=pat, fam=fam, dir=direction, short=short, te=int(te), entry=float(entry),
                                 stop=L.r2(stop), t1=L.r2(t1), book_pts=bp, why_not=None))
    return inp


def live_labels(d, sh, logs, inp):
    """S1 label stream (v9_day_type_state ∪ the shadow/trade snapshots), the gate's view (v9_decision_vectors),
    the opening lock (backend log → v9_day_type_history fallback), EOD labels, and the gateway archive's live gates."""
    w0, w1 = _sess_window(d, sh)
    naive = lambda x: x.astimezone(L.UTC).replace(tzinfo=None)   # v9_day_type_state.ts is naive UTC
    for ep, stage, dtl, conf, ot, lock in L.query(
            "select extract(epoch from ts)::bigint, stage, day_type, confidence, opening_type, lock_state from v9_day_type_state "
            "where ts >= %s and ts < %s order by ts", (naive(w0), naive(w1))):
        inp["stream"].append(obs(ep, dtl, ot, conf01(conf), stage, "dts", lock=lock))
    inp["stream"].sort(key=lambda o: o["ep"])
    for ep, kind, dtl, ot, conf in L.query(
            "select extract(epoch from ts)::bigint, kind, vector->>'day_type', vector->>'opening_type', vector->>'day_type_conf' "
            "from v9_decision_vectors where kind in ('DECISION','TREE_SHADOW') and ts >= %s and ts < %s order by ts", (w0, w1)):
        inp["gate"].append(obs(ep, dtl, ot, conf01(conf), None, "dv"))
    h = L.query("select day_type, opening_type, confidence, status, extract(epoch from locked_at)::bigint, ib_high, ib_low from v9_day_type_history "
                "where date = %s order by id desc limit 1", (d,))
    if h:
        dtl, ot, conf, status, lk, ibh, ibl = h[0]
        inp["eod"] = dict(dt=L.norm_dt(dtl), ot=L.norm_ot(ot), conf=conf01(conf), src="dth", status=status, ibh=ibh, ibl=ibl)
        inp["meta"]["dth_locked_il"] = L.il_hm(lk) if lk else None
    lg = logs.get(d) or {}
    if lg.get("locks"):
        f0 = lg["locks"][0]
        inp["lock"] = dict(t_il=f0["t_il"][:5], type=f0["type"], dir=f0["dir"], how=f0["how"], src="log")
        inp["relocks"] = [dict(t_il=x["t_il"][:5], type=x["type"], dir=x["dir"], how=x["how"]) for x in lg["locks"][1:]]
    inp["negs"] = [dict(t_il=x["t_il"][:5], was=x["was"], reread=x["reread"], dir=x["dir"]) for x in lg.get("negs", [])]
    inp["prov"] = [dict(t_il=x["t_il"][:5], frm=x["frm"], to=x["to"], pattern=x["pattern"], dir=x["dir"]) for x in lg.get("prov", [])]
    if not inp["lock"] and inp["eod"] and inp["eod"]["ot"] != "UNKNOWN" and inp["meta"].get("dth_locked_il"):
        # no T-314 line (the log covers 02.10 → now): the EOD record's lock time, when it has one. Otherwise no lock —
        # the hit then uses the EOD opening (v9_day_type_history), never the S1 day-type lock_state.
        inp["lock"] = dict(t_il=inp["meta"]["dth_locked_il"], type=inp["eod"]["ot"], dir=None, how="v9_day_type_history.locked_at", src="dth")
    rd = [o for o in inp["stream"] if o["ot"] != "UNKNOWN" and o["ep"] >= sh["bounds"]["A"][0]]
    if rd:
        inp["first_read"] = dict(t_il=L.il_hm(rd[0]["ep"]), type=rd[0]["ot"], src=rd[0]["src"])
    if not inp["eod"]:
        last = [o for o in inp["stream"] if o["ep"] < w1]
        if last:
            inp["eod"] = dict(dt=last[-1]["dt"], ot=last[-1]["ot"], conf=last[-1].get("conf"), src=last[-1]["src"])
    # gateway archive: live gates after the tree (live_blocked_by) — annotate would-fire, count as blocked
    gw = []
    for p in (os.path.join(L.EXPORT_DIR, "decisions_archive", "gateway_decisions.%s.jsonl" % d), os.path.join(L.EXPORT_DIR, "gateway_decisions.jsonl")):
        if not os.path.exists(p):
            continue
        try:
            with open(p, encoding="utf-8") as fh:
                for line in fh:
                    if '"GATE_DECISION"' not in line:
                        continue
                    try:
                        r = json.loads(line)
                    except Exception:
                        continue
                    ep = L.epoch(r.get("ts"))
                    if ep and w0.timestamp() <= ep < w1.timestamp():
                        gw.append(r)
        except Exception:
            pass
        if gw:
            break
    inp["meta"]["gateway_rows"] = len(gw)
    for r in gw:
        lb = r.get("live_blocked_by")
        if not lb:
            continue
        ep = L.epoch(r["ts"])
        for w in inp["would"]:
            if w["dir"] == r.get("direction") and w["pat"] == r.get("pattern") and abs(w["te"] - ep) <= 5:
                w["why_not"] = "live:" + lb
    # heartbeat: v9_decision_vectors kind='BAR' rows are written every few seconds while the backend runs (since 16.09) —
    # the 5-min buckets that have one = the system was alive. A leg with no heartbeat in its window is 'uncovered', not 'missed'.
    alive = L.query("select distinct (extract(epoch from ts)::bigint / 300) * 300 from v9_decision_vectors where kind='BAR' and ts >= %s and ts < %s",
                    (L.et_dt(d, 9, 25), L.et_dt(d, 16, 15)))
    inp["alive"] = set(int(r[0]) for r in alive)
    inp["meta"]["coverage"] = "bar_heartbeat" if inp["alive"] else "unknown"
    inp["meta"]["alive_buckets"] = len(inp["alive"])
    inp["meta"]["available"] = bool(inp["fires"] or inp["would"] or inp["blocked"] or inp["stream"] or inp["gate"] or inp["lock"])
    inp["meta"]["n_dts"] = sum(1 for o in inp["stream"] if o["src"] == "dts")
    inp["meta"]["n_snap"] = sum(1 for o in inp["stream"] if o["src"] in ("shadow", "trade"))
    inp["meta"]["n_dv"] = len(inp["gate"])
    return inp


# ── replay inputs (harness JSON) ─────────────────────────────────────────────────────────────────
def _route_sit(r):
    try:
        ctx = ((r.get("exec") or {}).get("live") or {}).get("command", {}).get("context", {})
        return ((ctx.get("metadata") or {}).get("situation") or {})
    except Exception:
        return {}


def replay_inputs(d, sh, path):
    with open(path, encoding="utf-8") as fh:
        J = json.load(fh)
    inp = dict(view="replay", src=rel(path), stream=[], gate=[], fires=[], would=[], blocked=[], lock=None, negs=[], relocks=[],
               first_read=None, prov=[], eod=None,
               meta=dict(variant=J.get("variant"), harness_usd=L.r2(J.get("daily_pnl_harness")), session=J.get("session"),
                         harness_prev=dict(J.get("prev_tpo") or {}, **{k: v for k, v in (J.get("pd_ctx") or {}).items() if k != "pd_context_status"}),
                         flags={k: v for k, v in (J.get("flags") or {}).items()}))
    a0 = sh["bounds"]["A"][0]
    last_lock = None
    for x in J.get("s1") or []:
        ep = L.epoch(L.il_dt(d, x["il"]))
        dtl = x.get("live_label") or x.get("published") or x.get("day_type_pre")
        ot = x.get("ot_locked") or x.get("machine_opening")
        inp["stream"].append(obs(ep, dtl, ot, x.get("conf"), (x.get("stage") or "").replace("Stage.", ""), "s1", otl=bool(x.get("ot_locked")),
                                 pub=L.norm_dt(x.get("published"))))
        if x.get("ot_locked") and not inp["lock"]:
            inp["lock"] = dict(t_il=x["il"][:5], type=x["ot_locked"], dir=None, how="s1.ot_locked", src="s1")
            last_lock = x["ot_locked"]
        elif x.get("ot_locked") and last_lock and x["ot_locked"] != last_lock:
            inp["relocks"].append(dict(t_il=x["il"][:5], type=x["ot_locked"], dir=None, how="s1.ot_locked"))
            inp["negs"].append(dict(t_il=x["il"][:5], was=last_lock, reread=x["ot_locked"], dir=None))
            last_lock = x["ot_locked"]
        if not inp["first_read"] and ep >= a0 and L.norm_ot(x.get("machine_opening")) != "UNKNOWN":
            inp["first_read"] = dict(t_il=x["il"][:5], type=L.norm_ot(x.get("machine_opening")), src="s1.machine_opening")
    if J.get("s1"):
        x = J["s1"][-1]
        inp["eod"] = dict(dt=L.norm_dt(x.get("live_label") or x.get("published")), ot=L.norm_ot(x.get("ot_locked") or x.get("machine_opening")),
                          conf=L.r2(x.get("conf")), src="s1", published=L.norm_dt(x.get("published")))
    routes = J.get("routes") or []
    by_live = {}
    for r in routes:
        res = r.get("result") or {}
        if isinstance(res.get("live"), str):
            by_live[res["live"]] = r
    for t in J.get("trades") or []:
        if not t.get("filled", True):
            continue
        r = by_live.get(t.get("trade_id")) or {}
        sit = _route_sit(r); vec = ((r.get("tree_v3") or {}).get("vec") or {})
        short = t.get("direction") == "SHORT"; n = int(t.get("contracts") or 1)
        if not (t.get("fired_il") or r.get("il")) or (t.get("fill_price") or t.get("entry")) is None:
            continue
        entry = float(t.get("fill_price") or t.get("entry"))
        te = L.epoch(L.il_dt(d, t.get("fired_il") or r.get("il")))
        tx = L.epoch(L.il_dt(d, t["exit_il"])) + 299 if t.get("exit_il") else None
        fills, sys6 = [], []
        for lg in t.get("legs") or []:
            if lg.get("exit_price") is None:
                continue
            fe = L.epoch(L.il_dt(d, lg["bar_il"])) + 1 if lg.get("bar_il") else tx
            fills.append((fe, 1, lg.get("exit"), float(lg["exit_price"])))
            ex = str(lg.get("exit") or "")
            sys6.append(dict(ep=fe, t_il=(lg.get("bar_il") or "")[:5], action=(ex + "_HIT") if re.match(r"^T\d", ex) else ("STOP_HIT" if ex == "STOP" else ex),
                             detail="@%s" % lg["exit_price"]))
        if t.get("be_moved"):
            sys6.insert(0, dict(ep=None, t_il=None, action="BE_MOVED", detail="stop %s→%s" % (t.get("stop_initial"), t.get("stop"))))
        pnl = t.get("pnl_usd"); pts = L.r2(pnl / (L.USD_PT * n)) if pnl is not None else None
        oc = str(t.get("outcome") or "")
        oc = "WIN" if (pts or 0) > 0 else ("BE" if pts == 0 else ("LOSS" if pts is not None else oc or "?"))
        tg = t.get("t1_target") or r.get("t1")
        inp["fires"].append(dict(id=t.get("trade_id"), src="replay", sys=r.get("system"), pat=t.get("classification"), fam=L.fam_of(t.get("classification")),
                                 dir=t.get("direction"), short=short, te=te, tx=tx, entry=entry, stop0=L.r2(t.get("stop_initial") or t.get("stop")),
                                 targets=[L.r2(x) for x in (tg, r.get("t2"), r.get("t3")) if x is not None], plan=[tg] * n, contracts=n, fills=fills,
                                 usd=None, usd_h=L.r2(pnl), usd_src="harness", pts=pts, outcome=oc, exit_px=(fills[-1][3] if fills else None),
                                 exit_reason=t.get("outcome"),
                                 thesis=dict(dt=L.norm_dt(sit.get("day_type") or vec.get("day_type")), ot=L.norm_ot(sit.get("opening_type") or vec.get("opening_type")),
                                             src="situation" if sit.get("day_type") else ("tree_v3.vec" if vec.get("day_type") else None)),
                                 sys6=sys6, be_rule=None, parent=None, mfe=None, mae=None,
                                 mfe_h=L.r2(t.get("mfe_pts")), mae_h=L.r2(abs(t["mae_pts"])) if t.get("mae_pts") is not None else None,
                                 t1_before_stop=t.get("t1_before_stop"), hold_to_close_pts=L.r2(t.get("hold_to_close_pts"))))
    seen = set()
    for r in routes:
        if not r.get("il") or r.get("entry") is None:
            continue
        te = L.epoch(L.il_dt(d, r["il"])); res = r.get("result") or {}
        fam = L.fam_of(r.get("classification")); direction = r.get("direction")
        gate = r.get("blocked_by") or res.get("blocked_by")
        if gate:
            inp["blocked"].append(dict(te=te, dir=direction, fam=fam, pat=r.get("classification"), gate=gate, sys=r.get("system")))
            continue
        if isinstance(res.get("live"), str):
            continue
        k = (r.get("system"), r.get("classification"), direction, te // 300)
        if k in seen:
            continue
        seen.add(k)
        sid = ((r.get("exec") or {}).get("shadow") or {}).get("trade_id") or ("R-" + r["il"])
        inp["would"].append(dict(id=sid, src="route", sys=r.get("system"), pat=r.get("classification"), fam=fam, dir=direction, short=direction == "SHORT",
                                 te=te, entry=float(r["entry"]), stop=L.r2(r.get("stop")), t1=L.r2(r.get("t1")), book_pts=None,
                                 why_not=("shadow_only" if r.get("shadow_only") else (("live:" + r["live_blocked_by"]) if r.get("live_blocked_by") else
                                          ("demo_only" if res.get("demo") else None)))))
    inp["meta"]["available"] = True
    return inp


# ── what-if (Michael 20.10: "let the run measure, then decide") ──────────────────────────────────
def what_if(f, stream, bars, partial, atr0=6.0):
    """If the S1 label changed away from the trade's thesis while it was open: at the flip time tf compare
    EXIT (remaining contracts out at the close of the flip bar) · BE (stop → entry from tf, original targets) ·
    HOLD (the actual outcome; a bar-path simulation when the trade is unpriced). Points per contract."""
    if not bars:
        return None
    te, tx = f["te"], f["tx"]
    i_eod = L.eod_index(bars)
    end = tx if tx else ((bars[i_eod]["ts"] + 300) if i_eod is not None else None)
    th_fam, th_ot = L.dt_family(f["thesis"]["dt"]), L.norm_ot(f["thesis"]["ot"])
    base = asof(stream, te); base_fam, base_ot = L.dt_family(base["dt"]), L.norm_ot(base["ot"])
    flip = None
    for o in stream:
        if o["ep"] <= te or (end is not None and o["ep"] >= end):
            continue
        fam, ot = L.dt_family(o["dt"]), L.norm_ot(o["ot"])
        if th_fam and fam and fam != base_fam and fam != th_fam:
            flip = (o, "day_type", f["thesis"]["dt"], o["dt"]); break
        if th_ot != "UNKNOWN" and ot != "UNKNOWN" and ot != base_ot and ot != th_ot:
            flip = (o, "opening", th_ot, ot); break
    if not flip:
        return None
    o, kind, frm, to = flip; tf = o["ep"]
    ie = L.bar_at(bars, te)
    k = L.bar_closed_at(bars, tf)
    if k is None or ie is None:
        return None
    k = max(k, ie)
    sgn = -1.0 if f["short"] else 1.0; entry = f["entry"]; n = f["contracts"]
    rem = list(f["plan"]); done = []
    for fep, qty, kind_, px in sorted(f["fills"], key=lambda x: x[0] or 0):
        if fep is not None and fep <= tf:
            for _ in range(int(qty or 1)):
                if rem:
                    rem.pop(0); done.append(sgn * (px - entry))
    if not rem:
        return None
    c = bars[k]["c"]; move = sgn * (c - entry)
    exit_pts = (sum(done) + len(rem) * move) / n
    be_note = None
    if move < 0:
        be_pts = exit_pts; be_note = "המחיר כבר מעבר לכניסה — BE = יציאה"
    else:
        tot = sum(done)
        for tg in rem:
            s = L.sim_path(bars, k + 1, f["short"], entry, entry, tg) if k + 1 <= (i_eod if i_eod is not None else -1) else dict(pts=move)
            tot += s["pts"] if s.get("pts") is not None else move
        be_pts = tot / n
    if f.get("pts") is not None:
        hold, hold_src = f["pts"], "actual"
    else:
        tot = 0.0
        for tg in (f["plan"] or [None]):
            st, tg2, _ = L.sane_geometry(f["short"], entry, f.get("stop0"), tg, atr0)
            s = L.sim_path(bars, ie, f["short"], entry, st, tg2)
            tot += s["pts"] or 0.0
        hold, hold_src = tot / max(1, len(f["plan"] or [None])), ("sim-open" if partial and not f["tx"] else "sim")
    opts = dict(EXIT=round(exit_pts, 2), BE=round(be_pts, 2), HOLD=round(hold, 2))
    best = max(opts, key=lambda kk: (opts[kk], kk == "HOLD"))
    return dict(t_il=L.il_hm(tf), kind=kind, frm=frm, to=to, src=o.get("src"), flip_bar=bars[k]["il"], px=c, open_n=len(rem),
                exit=opts["EXIT"], be=opts["BE"], hold=opts["HOLD"], hold_src=hold_src, best=best, be_note=be_note)


def trade_record(f, d, sh, stream, labels):
    bars, ib = sh["rth"], sh["ib"]
    ie = L.bar_at(bars, f["te"])
    ix = L.bar_at(bars, f["tx"]) if f["tx"] else L.eod_index(bars)
    if f.get("mfe") is None and ie is not None and ix is not None:
        f["mfe"], f["mae"] = L.mfe_mae(bars, ie, ix, f["short"], f["entry"])
    at = asof(stream, f["te"])
    rec = dict(id=f["id"], src=f["src"], sys=f["sys"], fam=f["fam"], pat=f["pat"], dir=f["dir"], te=f["te"], tx=f["tx"],
               t_entry=L.il_hm(f["te"]), t_exit=L.il_hm(f["tx"]) if f["tx"] else None, phase=L.phase_of(f["te"], d),
               thesis=f["thesis"], label_at_entry=dict(dt=at["dt"], ot=at["ot"], src=at["src"]), outcome=f["outcome"], pts=f["pts"],
               usd=f.get("usd"), usd_src=f.get("usd_src"), usd_h=f.get("usd_h"), usd_open=f.get("usd_open"), n=f["contracts"], entry=f["entry"], stop0=f.get("stop0"),
               targets=f.get("targets"), exit_px=f.get("exit_px"), exit_reason=f.get("exit_reason"), mfe=f.get("mfe"), mae=f.get("mae"),
               sys6=[{k: v for k, v in x.items() if k != "ep"} for x in f["sys6"]], be_rule=f.get("be_rule"), parent=f.get("parent"),
               mfe_h=f.get("mfe_h"), mae_h=f.get("mae_h"), hold_to_close_pts=f.get("hold_to_close_pts"),
               what_if=what_if(f, stream, bars, sh["partial"], sh["atr0"]),
               wrong_if=L.wrong_if(f["thesis"]["dt"], f["short"], bars, ib, f["te"], f["tx"], f["sys6"]) if ib.get("complete") else [])
    m = (labels.get("trades") or {}).get(str(f["id"]))
    if m:
        rec["michael"] = m
    return rec


def would_record(w, d, sh):
    bars = sh["rth"]
    i0 = L.bar_at(bars, w["te"])
    st, tg, ok = L.sane_geometry(w["short"], w["entry"], w.get("stop"), w.get("t1"), sh["atr0"])
    s = L.sim_path(bars, i0, w["short"], w["entry"], st, tg) if i0 is not None else dict(pts=None, how="NA", t_il=None)
    how = s["how"]
    if how == "EOD" and sh["partial"]:
        how = "OPEN"
    return dict(id=w["id"], src=w["src"], sys=w["sys"], fam=w["fam"], pat=w["pat"], dir=w["dir"], t_il=L.il_hm(w["te"]), te=w["te"],
                phase=L.phase_of(w["te"], d), entry=w["entry"], stop=L.r2(st), t1=L.r2(tg), geom=("ok" if ok else "fallback"),
                pts=s.get("pts"), how=how, t_out=s.get("t_il"), book_pts=w.get("book_pts"), why_not=w.get("why_not"))


# ── one view (live or replay) → system · hit · phases · trades · summary ────────────────────────
def finish_view(d, sh, inp, labels):
    bars, bounds, truth = sh["rth"], sh["bounds"], sh["rec"]["truth"]
    stream = sorted(inp["stream"], key=lambda o: o["ep"])
    o_ep = bounds["A"][0]
    primary = "s1" if stream else ("dv" if inp["gate"] else None)
    pstream = stream if stream else sorted(inp["gate"], key=lambda o: o["ep"])
    tl = compress(pstream)
    if inp["gate"] and stream:
        tl = sorted(tl + compress(inp["gate"]), key=lambda x: x["ep"])
    labels_at = {lab: asof(pstream, ep) for lab, n, ep in L.checkpoint_epochs(d)}
    for lab, n, ep in L.checkpoint_epochs(d):
        if n > len(bars):
            labels_at[lab]["future"] = True
    system = dict(primary=primary, lock=inp["lock"], negs=inp["negs"], relocks=inp["relocks"], first_read=inp["first_read"], prov=inp["prov"],
                  timeline=[{k: v for k, v in x.items() if k != "ep"} for x in tl], labels_at=labels_at,
                  flips=flips_of(pstream, o_ep), eod=inp["eod"])
    # hit
    t_fam, t_ot = L.dt_family(truth["day_type"]), L.norm_ot(truth["opening"])
    if truth["day_type"] == "UNCLEAR" or (truth.get("partial") and truth["day_type_src"] == "ref"):
        t_fam = None   # Michael said unclear / the session is not over: no day-type verdict
    if truth["opening"] == "UNCLEAR":
        t_ot = "UNKNOWN"
    s_ot = L.norm_ot((inp["lock"] or {}).get("type") or (inp["eod"] or {}).get("ot"))
    s_dt = (inp["eod"] or {}).get("dt") or "UNKNOWN"
    rth_obs = [o for o in pstream if o_ep <= o["ep"] < bounds["D"][1]]
    first = next((o for o in rth_obs if L.dt_family(o["dt"]) == t_fam), None) if t_fam else None
    stable = None
    if t_fam and rth_obs and L.dt_family(rth_obs[-1]["dt"]) == t_fam:
        k = len(rth_obs) - 1
        while k > 0 and L.dt_family(rth_obs[k - 1]["dt"]) == t_fam:
            k -= 1
        stable = rth_obs[k]
    ot_first = next((o for o in rth_obs if o["ot"] == t_ot), None) if t_ot != "UNKNOWN" else None
    hit = dict(opening_ok=(None if t_ot == "UNKNOWN" or s_ot == "UNKNOWN" else s_ot == t_ot), sys_opening=s_ot,
               day_type_ok=(None if not t_fam or not L.dt_family(s_dt) else L.dt_family(s_dt) == t_fam),
               day_type_exact=(None if not t_fam or not L.dt_family(s_dt) else L.norm_dt(s_dt) == L.norm_dt(truth["day_type"])), sys_day_type=s_dt,
               first_ok_t_il=L.il_hm(first["ep"]) if first else None, first_ok_min=L.min_after_open(first["ep"], d) if first else None,
               stable_ok_t_il=L.il_hm(stable["ep"]) if stable else None, stable_ok_min=L.min_after_open(stable["ep"], d) if stable else None,
               ot_first_ok_t_il=L.il_hm(ot_first["ep"]) if ot_first else None, ot_first_ok_min=L.min_after_open(ot_first["ep"], d) if ot_first else None,
               truth_partial=truth.get("partial"), at_fire=[])
    trades = [trade_record(f, d, sh, pstream, labels) for f in sorted(inp["fires"], key=lambda f: f["te"])]
    for t in trades:
        fam = L.dt_family(t["thesis"]["dt"])
        hit["at_fire"].append(dict(id=t["id"], t_il=t["t_entry"], thesis=t["thesis"]["dt"], s1=t["label_at_entry"]["dt"],
                                   ok=(None if not t_fam or not fam else fam == t_fam)))
    would = [would_record(w, d, sh) for w in sorted(inp["would"], key=lambda w: w["te"])]
    blocked = sorted(inp["blocked"], key=lambda b: b["te"])
    # legs and who caught them
    legs = []
    for lg in L.legs_of(bars, sh["atr0"]):
        i0, i1 = lg["i0"], lg["i1"]; half = min(len(bars) - 1, i0 + max(1, (i1 - i0) // 2))
        w0, w1 = bars[i0]["ts"], bars[half]["ts"] + 300; dirn = "SHORT" if lg["short"] else "LONG"
        cb = [dict(id=t["id"], k="fired") for t in trades if t["dir"] == dirn and w0 <= t["te"] <= w1]
        cb += [dict(id=w["id"], k="would") for w in would if w["dir"] == dirn and w0 <= w["te"] <= w1]
        bl, seen = [], set()
        for b in blocked:
            if b["dir"] == dirn and w0 <= b["te"] <= w1 and (b["fam"], b["gate"]) not in seen:
                seen.add((b["fam"], b["gate"])); bl.append(dict(fam=b["fam"], gate=b["gate"]))
        alive = inp.get("alive")
        covered = bool(inp["meta"].get("available")) and ((not alive) or any(w0 - 600 <= b <= w1 for b in alive))
        legs.append(dict(dir=dirn, t_from=bars[i0]["il"], t_to=bars[i1]["il"], pts=L.r2(lg["pts"]), p0=lg["p0"], p1=lg["p1"],
                         phase=L.phase_of(bars[i0]["ts"], d), caught_by=cb, missed=(not cb) and covered, covered=covered, blocked=bl[:4]))
    phases = {}
    for p in L.PHASES:
        a, b = bounds[p]
        inph = lambda ep: L.phase_of(ep, d) == p
        seen_l = []
        for o in pstream:
            if (p == "0" and o["ep"] < b) or (p != "0" and a <= o["ep"] < b):
                if o["dt"] not in seen_l:
                    seen_l.append(o["dt"])
        if p != "0":
            st = asof(pstream, a)["dt"]
            if st not in seen_l:
                seen_l.insert(0, st)
        ws = [w for w in would if inph(w["te"])]
        bs = [x for x in blocked if inph(x["te"])]
        phases[p] = dict(labels=seen_l,
                         fired=[dict(id=t["id"], src=t["src"], sys=t["sys"], fam=t["fam"], dir=t["dir"], t_il=t["t_entry"], outcome=t["outcome"],
                                     pts=t["pts"], usd=t["usd"]) for t in trades if inph(t["te"])],
                         would=dict(n=len(ws), pts=L.r2(sum(w["pts"] or 0 for w in ws)), wins=sum(1 for w in ws if (w["pts"] or 0) > 0)),
                         blocked=dict(n=len(bs), top=[[g, c] for g, c in collections.Counter(x["gate"] for x in bs).most_common(4)]),
                         legs=[lg for lg in legs if lg["phase"] == p])
    priced = [t for t in trades if t["pts"] is not None]
    usd_vals = [t["usd"] for t in trades if t.get("usd") is not None]
    topb = collections.Counter(x["gate"] for x in blocked).most_common(1)
    missed = [lg for lg in legs if lg["missed"]]
    n_open = sum(1 for t in trades if t["outcome"] == "OPEN")
    summary = dict(n_fired=len(trades), n_priced=len(priced), n_open=n_open, n_unpriced=len(trades) - len(priced) - n_open,
                   wins=sum(1 for t in priced if t["pts"] > 0), losses=sum(1 for t in priced if t["pts"] < 0),
                   pts=L.r2(sum(t["pts"] for t in priced)), usd=(L.r2(sum(usd_vals)) if (inp["view"] == "live" and usd_vals) else None),
                   harness_usd=inp["meta"].get("harness_usd"), n_would=len(would), would_pts=L.r2(sum(w["pts"] or 0 for w in would)),
                   n_blocked=len(blocked), top_block=(list(topb[0]) if topb else None), n_legs=len(legs), n_missed=len(missed),
                   missed_pts=L.r2(sum(lg["pts"] for lg in missed)), caught_pts=L.r2(sum(lg["pts"] for lg in legs if lg["caught_by"])),
                   n_uncovered=sum(1 for lg in legs if not lg["covered"]), uncovered_pts=L.r2(sum(lg["pts"] for lg in legs if not lg["covered"])))
    view = dict(src=inp["src"], available=bool(inp["meta"].get("available")), meta=inp["meta"], system=system, hit=hit, phases=phases,
                trades=trades, would=would, legs=legs, summary=summary)
    summary["notes"] = notes_for(d, sh, view, inp["view"])
    return view


def _mark(ok):
    return " ✓" if ok is True else (" ✗" if ok is False else "")


def notes_for(d, sh, v, kind):
    """2–4 short Hebrew notes for the day header."""
    tr, sm, sy, hit = sh["rec"]["truth"], v["summary"], v["system"], v["hit"]
    who = "מייקל" if tr["opening_src"] == "michael" else "הייחוס"
    out = []
    if not v["available"]:
        return ["אין נתוני-מערכת ליום הזה (הבקאנד לא רץ / אין רשומות) — רק השוק והייחוס"]
    lk = sy.get("lock")
    if lk:
        s1_ot = [x["ot"] for x in sy.get("timeline", []) if x.get("src") not in ("dv",) and x.get("ot") not in (None, "UNKNOWN")]
        split = s1_ot and L.norm_ot(s1_ot[-1]) != L.norm_ot(lk["type"])
        out.append("הפתיחה ננעלה %s ב-%s%s; %s: %s%s" % (L.ot_short(lk["type"]), lk["t_il"], (" (%s)" % lk["dir"]) if lk.get("dir") else "",
                                                     who, L.ot_short(tr["opening"]), _mark(hit["opening_ok"]))
                   + ((" · %d ביטולים" % len(sy["negs"])) if len(sy.get("negs") or []) > 1 else (" · ביטול אחד" if sy.get("negs") else ""))
                   + ((" · מכונת-S1 מחזיקה %s" % L.ot_short(s1_ot[-1])) if split else ""))
    else:
        out.append("אין נעילת-פתיחה; בסוף-היום %s; %s: %s%s" % (L.ot_short(hit["sys_opening"]), who, L.ot_short(tr["opening"]), _mark(hit["opening_ok"])))
    who2 = "מייקל" if tr["day_type_src"] == "michael" else "הייחוס"
    s = "סוג-היום: המערכת %s, %s %s%s" % (L.dt_heb(hit["sys_day_type"]), who2, L.dt_heb(tr["day_type"]), _mark(hit["day_type_ok"]))
    if hit.get("first_ok_t_il"):
        s += "; התווית הנכונה מ-%s (+%d דק׳)" % (hit["first_ok_t_il"], int(hit["first_ok_min"] or 0))
    elif hit["day_type_ok"] is not None:
        s += "; התווית הנכונה לא הופיעה"
    if sy.get("flips"):
        s += (" · %d ריצודים" % sy["flips"]) if sy["flips"] > 1 else " · ריצוד אחד"
    if tr.get("partial"):
        s += " (יום חלקי)"
    out.append(s)
    s = "%d ירי · Σ %+.2f נק׳" % (sm["n_fired"], sm["pts"] or 0)
    if kind == "live" and sm.get("usd") is not None:
        s += " (%+.2f$)" % sm["usd"]
    if sm.get("n_unpriced"):
        s += " · %d לא-מתומחרות" % sm["n_unpriced"]
    if sm.get("n_open"):
        s += " · %d פתוחות" % sm["n_open"]
    s += " · %d 'היה-יורה' (Σ %+.1f נק׳ בסימולציה)" % (sm["n_would"], sm["would_pts"] or 0)
    if sm.get("top_block"):
        s += " · חסימה מובילה: %s ×%d" % (sm["top_block"][0], sm["top_block"][1])
    out.append(s)
    missed = sorted([lg for lg in v["legs"] if lg["missed"]], key=lambda x: -x["pts"])
    if missed:
        b = missed[0]
        out.append("פספוס: %d רגליים · Σ %.0f נק׳ — הגדולה %s %s–%s (%.0f נק׳)%s" % (
            len(missed), sm["missed_pts"] or 0, "↓" if b["dir"] == "SHORT" else "↑", b["t_from"], b["t_to"], b["pts"],
            ("; נחסמו: " + ", ".join("%s/%s" % (x["fam"], x["gate"]) for x in b["blocked"][:2])) if b["blocked"] else ""))
    elif v["legs"] and not sm.get("n_uncovered"):
        out.append("כל %d הרגליים ≥ הסף נתפסו (ירי או 'היה-יורה')" % len(v["legs"]))
    if sm.get("n_uncovered") and out:
        out[-1] += " · %d רגליים (Σ %.0f נק׳) בזמן שהמערכת לא רצה" % (sm["n_uncovered"], sm["uncovered_pts"] or 0)
    return out[:4]


# ── one day ──────────────────────────────────────────────────────────────────────────────────────
def build_day(d, a, labels, rmap, logs):
    rp = rmap.get(d) if not a.no_replay else None
    want_live = (not a.no_live) and d >= a.live_since
    day = load_bars_for(d, prefer_live=want_live)
    if not day or not day["rth"]:
        return None
    sh = shared_day(d, day, labels)
    rec = dict(schema=SCHEMA, v=a.version, v_heb=L.VERSION_HEB if a.version == L.VERSION_DEFAULT else a.version, date=d,
               dow=dt.date.fromisoformat(d).strftime("%a"), generated=dt.datetime.now(L.IL).strftime("%Y-%m-%d %H:%M"),
               partial=sh["partial"], lib=L.LIB_SRC, labels_src=(None if labels.get("missing") else rel(labels.get("path"))), views=[])
    rec.update(sh["rec"])
    if want_live:
        inp = live_inputs(d, sh, logs)
        live_labels(d, sh, logs, inp)
        rec["live"] = finish_view(d, sh, inp, labels); rec["views"].append("live")
    if rp:
        try:
            rec["replay"] = finish_view(d, sh, replay_inputs(d, sh, rp), labels); rec["views"].append("replay")
        except Exception as e:
            rec["replay_error"] = "%s: %s" % (type(e).__name__, e)
    return rec


def main(argv=None):
    a = parse_args(argv)
    labels = L.load_labels(a.labels)
    if a.truth_opening:
        p = a.truth_opening if os.path.isabs(a.truth_opening) else os.path.join(REPO, a.truth_opening)
        with open(p, encoding="utf-8") as fh:
            V2_TRUTH.update(json.load(fh))
    rmap = replay_map(a.replay_dir, a.replay_glob) if not a.no_replay else {}
    if a.date:
        dates = sorted({x.strip() for s in a.date for x in s.split(",") if x.strip()})
    elif a.all or a.since:
        live = [] if a.no_live else L.rth_dates("mems26", since=max(a.live_since, a.since or a.live_since), until=a.until)
        rd = [d for d in rmap if (not a.since or d >= a.since) and (not a.until or d <= a.until)]
        dates = sorted(set(live) | set(rd))
    else:
        print("nothing to do: --date, --since or --all"); return 2
    os.makedirs(a.out, exist_ok=True)
    logs = L.scan_backend_log() if not a.no_live else {}
    t_all = time.time(); n_ok = 0; errs = []
    for d in dates:
        t0 = time.time()
        try:
            rec = build_day(d, a, labels, rmap, logs)
        except Exception as e:
            import traceback
            errs.append((d, "%s: %s" % (type(e).__name__, e)))
            if not a.quiet:
                traceback.print_exc()
            continue
        if rec is None:
            if not a.quiet:
                print("%s: no RTH bars in mems26 / mems26_hist — skipped" % d)
            continue
        p = os.path.join(a.out, "%s.json" % d)
        with open(p + ".tmp", "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, separators=(",", ":"), default=str)
        os.replace(p + ".tmp", p)
        n_ok += 1
        if not a.quiet:
            vs = []
            for k in rec["views"]:
                s = rec[k]["summary"]
                vs.append("%s: fired %d Σ%+.1f%s would %d Σ%+.1f missed %d/%.0f" % (
                    k, s["n_fired"], s["pts"] or 0, (" $%+.0f" % s["usd"]) if s.get("usd") is not None else "", s["n_would"], s["would_pts"] or 0,
                    s["n_missed"], s["missed_pts"] or 0))
            print("%s %s%s · truth %s/%s · %s · %.2fs" % (d, "PARTIAL " if rec["partial"] else "", rec["bars"]["db"], L.ot_short(rec["truth"]["opening"]),
                                                       rec["truth"]["day_type"], " | ".join(vs) or "no views", time.time() - t0), flush=True)
    print("DAYMAP %s: %d day files → %s (%.1fs)%s" % (a.version, n_ok, rel(a.out), time.time() - t_all,
                                                       ("; errors: " + "; ".join("%s %s" % e for e in errs[:5])) if errs else ""))
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
