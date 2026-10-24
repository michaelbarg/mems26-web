#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Part C — every real trade (demo/live) of the examined sessions against the direction state, location, acceptance,
effort and the system's own reads; the class of every bad trade (א/ב/ג/ד), the confirmation entry for class ב, and the
alternative candidates around it (live shadow twins of the same day, labelled on the bars). Read-only.

  python3 harness_out/t645/examiner/xtrades.py > harness_out/t645/examiner/trades_exam.txt   (+ trades_exam.json)
"""
import os, sys, json, datetime as dt, collections
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git/harness_out/t645/examiner")
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")
import xlib
from backend.v9.services import turn_state as TS

D = xlib.rth_days()
DATA = xlib.data()
V = json.load(open("/Users/michael/Downloads/mems26_web_git/harness_out/t643/verdicts.json"))
VER = {}
for g in ("demo", "live"):
    for k, x in V[g].items():
        VER[int(k)] = x
LOG = json.load(open(os.path.join(xlib.HERE, "log_tree.json")))
OPP = {"UP": "DOWN", "DOWN": "UP"}


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def init_stop(t):
    for k in ("stop_initial", "entry_stop", "initial_stop", "stop"):
        v = fnum(t.get(k))
        if v:
            return v
    return None


def state_of(day):
    return json.load(open(os.path.join(xlib.HERE, "state_%s.json" % day)))


def refs_at(bs, k, R):
    """Reference levels known at the close of bar k (no look-ahead)."""
    seen = bs[:k + 1]; out = []
    for key, nm in (("p_vah", "VAH-אתמול"), ("p_val", "VAL-אתמול"), ("p_poc", "POC-אתמול"), ("p_hi", "שיא-אתמול"), ("p_lo", "שפל-אתמול"),
                    ("on_hi", "שיא-לילה"), ("on_lo", "שפל-לילה"), ("open", "פתיחה")):
        if R.get(key) is not None:
            out.append((nm, float(R[key])))
    if k >= 11:
        out += [("IBH", max(x["h"] for x in bs[:12])), ("IBL", min(x["l"] for x in bs[:12]))]
    out += [("שיא-הסשן", max(x["h"] for x in seen)), ("שפל-הסשן", min(x["l"] for x in seen))]
    if len(seen) >= 6:
        va = xlib.value_area(xlib.tpo_profile(seen))
        out += [("POC-מתפתח", va["poc"]), ("VAH-מתפתח", va["vah"]), ("VAL-מתפתח", va["val"])]
    return out


def first_ref_ahead(refs, ep, short):
    sg = -1 if short else 1
    ah = sorted([(n, p, sg * (p - ep)) for n, p in refs if sg * (p - ep) >= 0.5], key=lambda x: x[2])
    return ah[0] if ah else None


def confirm_entry(bs, st, ev, sw, k, want):
    """Class ב: the first accepted state in the trade's direction after bar k; enter at the next bar's open, stop one tick
    beyond the last confirmed swing on the stop side (the level whose break would refute the read); +1R before the stop?"""
    e = next((e for e in ev if e["i"] > k and e["to"] == want), None)
    if e is None:
        return None
    j = e["i"]
    if j + 1 >= len(bs):
        return dict(hm=xlib.il_hm(bs[j]), px=e["px"], entry=None, note="אושר בבר האחרון")
    known = [s for s in sw if s["ci"] <= j]
    ep = bs[j + 1]["o"]
    if want == "UP":
        L = next((s for s in reversed(known) if s["type"] == "L"), None)
        stop = (L["px"] - 0.25) if L else None
    else:
        H = next((s for s in reversed(known) if s["type"] == "H"), None)
        stop = (H["px"] + 0.25) if H else None
    lab = None; when = None; R = None
    if stop is not None:
        R = abs(ep - stop)
        lab, when = xlib.label_candidate(bs, bs[j + 1]["t"] + dt.timedelta(seconds=5), "LONG" if want == "UP" else "SHORT", ep, stop)
    # tight variant: one tick beyond the extreme of the two accepting bars (the bars that proved the break)
    acc = bs[max(0, j - 1):j + 1]
    stop2 = (min(x["l"] for x in acc) - 0.25) if want == "UP" else (max(x["h"] for x in acc) + 0.25)
    R2 = abs(ep - stop2)
    lab2, when2 = xlib.label_candidate(bs, bs[j + 1]["t"] + dt.timedelta(seconds=5), "LONG" if want == "UP" else "SHORT", ep, stop2)
    return dict(hm=xlib.il_hm(bs[j]), px=e["px"], why=e["why"], entry=ep, entry_hm=xlib.il_hm(bs[j + 1]), stop=stop, R=R, label=lab, when=when,
                stop2=stop2, R2=R2, label2=lab2, when2=when2)


def shadow_cands(day):
    out = []
    for t in DATA["trades"]:
        if t["day"] != day or t["mode"] != "shadow":
            continue
        ts = dt.datetime.fromisoformat(t["entry_ts"])
        out.append(dict(id=t["id"], ts=ts, hm=ts.astimezone(xlib.IL).strftime("%H:%M"), pat=t["pattern_id_at_entry"], dir=t["direction"],
                        entry=fnum(t["entry_price"]), stop=init_stop(t), blocked=t.get("blocked_by"), outcome=t.get("outcome"),
                        pnl=t.get("pnl_usd")))
    return out


def dedupe(cs, mins=15):
    last = {}; out = []
    for c in sorted(cs, key=lambda c: c["ts"]):
        key = (c["pat"], c["dir"])
        if key in last and (c["ts"] - last[key]).total_seconds() < mins * 60:
            continue
        last[key] = c["ts"]; out.append(c)
    return out


def log_tree_for(day, ets, pat, direction, ep):
    if day not in ("2026-10-22", "2026-10-23"):
        return None
    best = None
    for ts, p, d, e, leaf, path in LOG["tree"]:
        t = dt.datetime.fromisoformat(ts.replace(" ", "T") + "+03:00")
        if p == pat and d == direction and abs((t - ets).total_seconds()) <= 120:
            if best is None or abs((t - ets).total_seconds()) < best[0]:
                best = (abs((t - ets).total_seconds()), leaf, path, e)
    return best


ROWS = []
trades = sorted([t for t in DATA["trades"] if t["mode"] in ("demo", "live")], key=lambda t: t["entry_ts"])
for t in trades:
    day = t["day"]; bs = D[day]; S = state_of(day)
    st, ev, sw, th, SR = S["state"], S["ev"], S["swings"], S["theta"], S["sys"]
    R0 = S["refs"]
    ets = dt.datetime.fromisoformat(t["entry_ts"]); short = t["direction"] == "SHORT"; want = "DOWN" if short else "UP"
    k = xlib.bar_index_at(bs, ets)
    ep = fnum(t["entry_price"]); s0 = init_stop(t); R = abs(ep - s0) if s0 else None
    sk = st[k] if k >= 0 else "BAL"
    nxt = next((e for e in ev if e["i"] > k and e["to"] in ("UP", "DOWN")), None)
    pos, pl = xlib.hour_pos(bs, k, ep, t["direction"]) if k >= 0 else (None, "-")
    seen = bs[:k + 1]
    # rule A — accepted extension against the trade (T-643 definition) and with it
    ruleA = with_acc = "ib_forming"
    if k >= 11:
        ibh = max(x["h"] for x in bs[:12]); ibl = min(x["l"] for x in bs[:12])
        last6 = seen[12:][-6:]
        beyond = [x for x in last6 if (x["c"] > ibh if short else x["c"] < ibl)]
        ds = sum((x["d"] or 0) for x in beyond)
        ruleA = "accepted_against" if (len(beyond) >= 3 and ((ds > 0) if short else (ds < 0))) else "no"
        w = [x for x in last6 if (x["c"] < ibl if short else x["c"] > ibh)]
        dw = sum((x["d"] or 0) for x in w)
        with_acc = "yes" if (len(w) >= 3 and ((dw < 0) if short else (dw > 0))) else "no"
    d3 = sum((x["d"] or 0) for x in seen[-3:]); eff = "with" if ((d3 < 0) if short else (d3 > 0)) else "against"
    tn = TS.detect_turn([dict(h=x["h"], l=x["l"], c=x["c"]) for x in seen]) if k >= 2 else {"turn": "none"}
    trel = TS.turn_rel(tn, t["direction"], ep)
    sig = bs[k] if k >= 0 else None
    climax = (sig["h"] - sig["l"]) >= 2.0 * th[k] if sig else False
    # edge of the DAY on the stop side: the outer quarter of the session range, or at/beyond the developing VA edge
    s_hi = max(x["h"] for x in seen); s_lo = min(x["l"] for x in seen); s_rg = max(s_hi - s_lo, 0.25)
    sess_edge = ((s_hi - ep) <= 0.25 * s_rg) if short else ((ep - s_lo) <= 0.25 * s_rg)
    dva = xlib.value_area(xlib.tpo_profile(seen)) if len(seen) >= 6 else None
    va_edge = None
    if dva:
        va_edge = (ep >= dva["vah"] - 0.5 * th[k]) if short else (ep <= dva["val"] + 0.5 * th[k])
    # opening reversal bar: the signal bar made the session extreme on the stop side and closed back through the open,
    # in its far third, in the trade's direction (Dalton ORR / test-drive through the open)
    o = bs[0]["o"]; rev_bar = False
    if sig is not None:
        rg = max(sig["h"] - sig["l"], 0.25)
        if short:
            rev_bar = sig["h"] >= s_hi - 0.01 and sig["c"] < o and (sig["h"] - sig["c"]) / rg >= 0.67
        else:
            rev_bar = sig["l"] <= s_lo + 0.01 and sig["c"] > o and (sig["c"] - sig["l"]) / rg >= 0.67
    md = sorted(abs(x["d"] or 0) for x in seen[-20:]); mdel = md[len(md) // 2] if md else 0
    hm_ = ets.astimezone(xlib.IL).strftime("%H:%M")
    phase = "A" if hm_ < "16:45" else "B" if hm_ < "17:30" else "C" if hm_ < "21:00" else "D"
    refs = refs_at(bs, k, R0) if k >= 0 else []
    fra = first_ref_ahead(refs, ep, short)
    sit = t.get("situation") or {}
    lt = log_tree_for(day, ets, t["pattern_id_at_entry"], t["direction"], ep)
    # outcome on the bars
    lab, lab_t = xlib.label_candidate(bs, ets, t["direction"], ep, s0) if s0 else (None, None)
    ver = VER.get(int(t["id"]), {})
    good = ver.get("v") == "correct"
    cls = None; conf = None
    if not good:
        if sk == OPP[want]:
            cls = "א"
        elif sk == "BAL":
            if nxt and nxt["to"] == want:
                cls = "ב"; conf = confirm_entry(bs, st, ev, sw, k, want)
            else:
                cls = "ד"
        else:
            cls = "ג"
    # alternatives: live shadow candidates −30..+60 min, deduped, labelled on the bars
    alts = []
    for c in dedupe([c for c in shadow_cands(day) if -1800 <= (c["ts"] - ets).total_seconds() <= 3600]):
        if c["entry"] is None or c["stop"] is None:
            continue
        lb, lw = xlib.label_candidate(bs, c["ts"], c["dir"], c["entry"], c["stop"])
        kc = xlib.bar_index_at(bs, c["ts"])
        alts.append(dict(c, ts=c["ts"].isoformat(), lab=lb, lab_t=lw, state=(st[kc] if kc >= 0 else "BAL"),
                         R=abs(c["entry"] - c["stop"])))
    row = dict(id=t["id"], mode=t["mode"], day=day, hm=ets.astimezone(xlib.IL).strftime("%H:%M"), pat=t["pattern_id_at_entry"],
               dir=t["direction"], entry=ep, stop0=s0, R=R, theta=th[k] if k >= 0 else None, R_theta=(R / th[k]) if (R and k >= 0) else None,
               t1=fnum(t["t1"]), t1_hit=bool(t.get("t1_hit_ts")), pnl=t.get("pnl_usd"), exit=t.get("exit_reason"), contracts=t.get("contracts"),
               verdict=ver, state=sk, last_closed=xlib.il_hm(bs[k]) if k >= 0 else None,
               next_state=(dict(hm=xlib.il_hm(bs[nxt["i"]]), to=nxt["to"], px=nxt["px"], why=nxt["why"]) if nxt else None),
               pos_hour=round(pos, 2) if pos is not None else None, pos_lab=pl, ruleA=ruleA, with_acc=with_acc, delta3=d3, effort=eff,
               turn=tn.get("turn"), turn_rel=trel, climax=climax, sig_range=(sig["h"] - sig["l"]) if sig else None,
               sess_edge=sess_edge, va_edge=va_edge, dva=dva, rev_bar=rev_bar, med_delta=mdel, phase=phase,
               first_ref=fra, sys=dict(ot=sit.get("opening_type"), daytype=sit.get("day_type") or t.get("day_type_at_entry"), phase=sit.get("phase"),
                                       zone=sit.get("zone"), dir_hint=sit.get("dir_hint"), ext=sit.get("extension"), ext_pts=sit.get("extension_pts"),
                                       prior_zone=sit.get("prior_zone"), bars_since_high=sit.get("bars_since_high"), bars_since_low=sit.get("bars_since_low")),
               sys_reads=SR[k] if k >= 0 else None, log_tree=lt, label=lab, label_t=lab_t, cls=cls, confirm=conf, alts=alts)
    ROWS.append(row)

json.dump(ROWS, open(os.path.join(xlib.HERE, "trades_exam.json"), "w"), ensure_ascii=False, default=str, indent=1)
for r in ROWS:
    v = r["verdict"]
    print("-" * 110)
    print("#%s %s %s %s %s %s @%s stop %s (R %.2f = %.1fθ) T1 %s%s · %s · %s $%s · פסק %s%s" % (
        r["id"], r["mode"], r["day"][5:], r["hm"], r["pat"], r["dir"], r["entry"], r["stop0"], r["R"] or 0, r["R_theta"] or 0, r["t1"],
        " (הושג)" if r["t1_hit"] else "", r["contracts"], r["exit"], r["pnl"], v.get("v"), ("/" + v["p"]) if v.get("p") else ""))
    print("  מצב בכניסה: %s (בר אחרון שנסגר %s) · הבא: %s · תווית-ברים %s %s" % (
        xlib.HE.get(r["state"], r["state"]), r["last_closed"], ("%s %s @%s (%s)" % (r["next_state"]["hm"], xlib.HE[r["next_state"]["to"]], r["next_state"]["px"], r["next_state"]["why"])) if r["next_state"] else "—",
        r["label"], r["label_t"] or ""))
    print("  מיקום בשעה %s (%s) · כלל-A %s · עם-הרחבה-מקובלת %s · דלתא-3 %+.0f (%s) · turn %s/%s · בר-סיגנל %.2f (%s) · ייחוס-ראשון-לפנים %s" % (
        r["pos_hour"], r["pos_lab"], r["ruleA"], r["with_acc"], r["delta3"], r["effort"], r["turn"], r["turn_rel"], r["sig_range"] or 0,
        "קליימקס" if r["climax"] else "רגיל", ("%s %.2f (%.2f נק׳ = %.2fR)" % (r["first_ref"][0], r["first_ref"][1], r["first_ref"][2], r["first_ref"][2] / r["R"])) if (r["first_ref"] and r["R"]) else "—"))
    s = r["sys"]; sr = r["sys_reads"] or {}
    print("  המערכת: פתיחה %s · יום %s · שלב %s · zone %s · dir_hint %s · הרחבה %s %s · עץ(לוג) %s · hint %s struct %s LSMA+CVD %s sustained %s" % (
        s["ot"], s["daytype"], s["phase"], s["zone"], s["dir_hint"], s["ext"], s["ext_pts"], (r["log_tree"][1] + " " + r["log_tree"][2]) if r["log_tree"] else "—",
        sr.get("hint"), sr.get("struct"), sr.get("lsma_cvd"), sr.get("sus")))
    if r["cls"]:
        print("  ⇒ סיווג %s" % r["cls"] + ((" · אישור %s @%s (%s) → כניסה %s @%s סטופ-מבני %s R %.2f → %s %s · סטופ-צמוד %s R %.2f → %s %s" % (
            r["confirm"]["hm"], r["confirm"]["px"], r["confirm"].get("why"), r["confirm"].get("entry_hm"), r["confirm"].get("entry"), r["confirm"].get("stop"),
            r["confirm"].get("R") or 0, r["confirm"].get("label"), r["confirm"].get("when") or "", r["confirm"].get("stop2"), r["confirm"].get("R2") or 0,
            r["confirm"].get("label2"), r["confirm"].get("when2") or "")) if r["confirm"] else ""))
    for a in r["alts"]:
        print("     alt %s %-22s %-5s @%-8s R %-5.2f %-24s state %-4s → %s %s (shadow %s $%s)" % (
            a["hm"], a["pat"], a["dir"], a["entry"], a["R"], a["blocked"], a["state"], a["lab"], a["lab_t"] or "", a["outcome"], a["pnl"]))
