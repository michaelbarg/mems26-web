# -*- coding: utf-8 -*-
"""T-641/T-642 (23.10 night) — the week 19–23.10 on the harness, trade by trade, for Michael's doc.

usage: python3 harness_out/t640/week_report.py <ref_tag> <best_tag> [--json out.json]
Per day: actual demo (v9_trades) vs <ref_tag> (the current live config) vs <best_tag> (with the fixes),
and for every <best_tag> trade: execution · targets · location · management · exits · in-trade MFE/MAE · why.
Location uses the harness's own yesterday (prev_tpo / pd_ctx = the DB cash session the tree reads) and
the day's RTH bars from v9_bars_5min_woodies (IB = 16:30–17:25 IL).
"""
import json, subprocess, sys, collections

PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
DAYS = ["2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23"]
HE_DAY = {"2026-10-19": "יום ב׳ 19.10", "2026-10-20": "יום ג׳ 20.10", "2026-10-21": "יום ד׳ 21.10",
          "2026-10-22": "יום ה׳ 22.10", "2026-10-23": "יום ו׳ 23.10"}
MES = 5.0


def q(sql):
    out = subprocess.run([PSQL, "-d", "mems26", "-At", "-F", "|", "-c", sql], capture_output=True, text=True).stdout
    return [l.split("|") for l in out.strip().split("\n") if l.strip()]


def bars_of(day):
    rows = q("select to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), open, high, low, close, volume "
             "from v9_bars_5min_woodies where ts >= '%s 16:30+03' and ts < '%s 23:00+03' order by ts" % (day, day))
    return [{"t": r[0], "o": float(r[1]), "h": float(r[2]), "l": float(r[3]), "c": float(r[4]), "v": float(r[5])} for r in rows]


def actual_of(day):
    rows = q("select to_char(entry_ts at time zone 'Asia/Jerusalem','HH24:MI'), id, coalesce(pattern_id_at_entry,'?'), "
             "direction, coalesce(pnl_usd::text,''), coalesce(exit_reason,'') from v9_trades where mode='demo' "
             "and entry_ts >= '%s 00:00+03' and entry_ts < '%s 23:59+03' order by entry_ts" % (day, day))
    return [{"t": r[0], "id": int(r[1]), "pat": r[2], "dir": r[3], "pnl": (float(r[4]) if r[4] else None), "exit": r[5]} for r in rows]


def fmt(x, nd=2):
    return ("%.*f" % (nd, x)) if isinstance(x, (int, float)) else "—"


def loc_label(entry, t_il, prev, pd, ib, opn):
    parts = []
    vah, val, poc = prev.get("vah"), prev.get("val"), prev.get("poc")
    if vah and val:
        if entry > vah:
            parts.append("מעל VAH-אתמול (+%.1f)" % (entry - vah))
        elif entry < val:
            parts.append("מתחת VAL-אתמול (−%.1f)" % (val - entry))
        else:
            parts.append("בתוך ערך-אתמול, %s POC (%+.1f)" % ("מעל" if entry >= poc else "מתחת", entry - poc))
    hi, lo = pd.get("pd_high"), pd.get("pd_low")
    if hi and entry > hi:
        parts.append("מעל שיא-אתמול")
    elif lo and entry < lo:
        parts.append("מתחת שפל-אתמול")
    if t_il < "17:30":
        parts.append("IB בבנייה")
    elif ib:
        if entry > ib[0]:
            parts.append("מעל IBH %.2f" % ib[0])
        elif entry < ib[1]:
            parts.append("מתחת IBL %.2f" % ib[1])
        else:
            parts.append("בתוך IB")
    if opn:
        parts.append("%s לפתיחה" % ("מעל" if entry >= opn else "מתחת"))
    return " · ".join(parts)


def phase(t_il):
    return "A" if t_il < "17:00" else ("B" if t_il < "17:30" else ("C" if t_il < "21:00" else "D"))


def opening_at(s1, t_il):
    lab = None
    for x in s1 or []:
        if str(x.get("il", "")) <= t_il:
            lab = x.get("canonical_opening") or x.get("ot_locked") or lab
    return (lab or "?").split("/")[0]


def exits_summary(legs):
    c = collections.OrderedDict()
    for l in legs or []:
        k = (str(l.get("exit")), l.get("exit_price"), l.get("bar_il"))
        c[k] = c.get(k, 0) + 1
    out = []
    for (ex, px, t), n in c.items():
        name = {"STOP": "סטופ", "BE": "BE", "T4": "T3", "T5": "T3", "HOLD_STOP": "סטופ-מבנה"}.get(ex, ex)
        out.append("%s×%d %s @%s" % (name, n, t or "", fmt(px)))
    return " · ".join(out)


def trade_rows(j, bars, day):
    prev = j.get("prev_tpo") or {}
    pd = j.get("pd_ctx") or {}
    ib = None
    ibb = [b for b in bars if b["t"] < "17:30"]
    if len(ibb) >= 12:
        ib = (max(b["h"] for b in ibb), min(b["l"] for b in ibb))
    opn = bars[0]["o"] if bars else None
    rows = []
    for tr in j.get("trades", []):
        if not tr.get("filled"):
            continue
        t_il = str(tr.get("fired_il", ""))[:5]
        d = tr.get("direction")
        fill = float(tr.get("fill_price") or tr.get("entry"))
        st0 = float(tr.get("stop_initial") or tr.get("stop"))
        R = abs(fill - st0) or 0.25
        sgn = 1 if d == "LONG" else -1
        tg = [l.get("target") for l in (tr.get("legs") or []) if l.get("target")]
        tgu = []
        for x in tg:
            if x not in tgu:
                tgu.append(x)
        t1 = tr.get("t1_target") or (tgu[0] if tgu else None)
        ex_t = str(tr.get("exit_il") or "")[:5]
        seg = [b for b in bars if t_il <= b["t"] <= (ex_t or "23:00")]
        if seg:
            mfe = max((b["h"] - fill) if d == "LONG" else (fill - b["l"]) for b in seg)
            mae = max((fill - b["l"]) if d == "LONG" else (b["h"] - fill) for b in seg)
        else:
            mfe = mae = None
        t1d = abs(t1 - fill) if t1 else None
        pnl = float(tr.get("pnl_usd") or 0)
        legs = tr.get("legs") or []
        hit_t1 = any(str(l.get("exit")) == "T1" for l in legs) or bool(tr.get("t1_before_stop"))
        eb = [b for b in bars if b["t"] == t_il]
        same_bar_stop = (pnl <= 0 and not hit_t1 and (not ex_t or ex_t <= t_il))
        if same_bar_stop:
            rng = (eb[0]["h"] - eb[0]["l"]) if eb else None
            why = ("סטופ בתוך הרעש — נעצר בבר הכניסה (R %.2f נק׳ מול טווח-בר %.2f)" % (R, rng)) if rng else "נעצר בבר הכניסה"
        elif pnl > 0 and hit_t1:
            why = "✅ T1 מומש"
        elif pnl > 0:
            why = "✅ רווח (טרייל/BE)"
        elif hit_t1:
            why = "T1 מומש, השאר נעצר — ניהול"
        elif mfe is not None and t1d and mfe >= 0.6 * R:
            why = "T1 רחוק מדי — המחיר הגיע ל-%.1fR, T1 ב-%.1fR" % (mfe / R, t1d / R)
        elif mfe is not None:
            why = "כניסה/מיקום — המחיר לא התקדם (%.1fR)" % (mfe / R)
        else:
            why = "—"
        mg = []
        if tr.get("be_moved"):
            mg.append("BE אחרי T1")
        br = tr.get("be_rule") or {}
        if br.get("hold"):
            mg.append("החזקה על מבנה")
        for tt in tr.get("tightened") or []:
            mg.append("%s→%s (%s)" % (tt.get("il"), fmt(tt.get("to")), str(tt.get("reason", "")).split(" (")[0]))
        if tr.get("ambiguous_bars"):
            mg.append("⚠ %d ברים עמומים" % tr["ambiguous_bars"])
        rows.append({
            "day": day, "t": t_il, "pat": tr.get("classification"), "dir": d, "c": tr.get("contracts"),
            "fill": fill, "stop0": st0, "R": R, "t1": t1, "t1R": (t1d / R if t1d else None), "targets": tgu[:3],
            "loc": loc_label(fill, t_il, prev, pd, ib, opn), "opening": opening_at(j.get("s1"), t_il),
            "daytype": tr.get("day_type_at_entry"), "phase": phase(t_il),
            "mgmt": " · ".join(mg) or "—", "exits": exits_summary(legs), "exit_t": ex_t,
            "mfeR": (mfe / R if mfe is not None else None), "maeR": (mae / R if mae is not None else None),
            "pnl": pnl, "why": why, "key": (t_il, tr.get("classification"), d),
        })
    return rows, {"prev": prev, "pd": pd, "ib": ib, "open": opn, "close": bars[-1]["c"] if bars else None}


def match_actual(r, actual):
    for a in actual:
        if a["t"] == r["t"] and a["dir"] == r["dir"]:
            return a
    return None


def main():
    ref, best = sys.argv[1], sys.argv[2]
    out_json = None
    if "--json" in sys.argv:
        out_json = sys.argv[sys.argv.index("--json") + 1]
    report = {"ref": ref, "best": best, "days": []}
    for day in DAYS:
        bars = bars_of(day)
        actual = actual_of(day)
        jr = json.load(open("harness_out/t640/days/%s_%s.json" % (ref, day)))
        jb = json.load(open("harness_out/t640/days/%s_%s.json" % (best, day)))
        rr, ctx = trade_rows(jr, bars, day)
        br, _ = trade_rows(jb, bars, day)
        rkeys = {r["key"] for r in rr}
        bkeys = {r["key"] for r in br}
        for r in br:
            a = match_actual(r, actual)
            r["actual"] = ("#%d %s %s" % (a["id"], a["pat"], ("%+.2f" % a["pnl"]) if a["pnl"] is not None else "לא-מתומחר")) if a else "—"
            r["new"] = r["key"] not in rkeys
        removed = [r for r in rr if r["key"] not in bkeys]
        report["days"].append({
            "day": day, "he": HE_DAY[day], "ctx": ctx,
            "actual": {"n": len(actual), "pnl": sum(a["pnl"] or 0 for a in actual), "w": sum(1 for a in actual if (a["pnl"] or 0) > 0), "trades": actual},
            "ref": {"n": len(rr), "pnl": sum(r["pnl"] for r in rr), "w": sum(1 for r in rr if r["pnl"] > 0)},
            "best": {"n": len(br), "pnl": sum(r["pnl"] for r in br), "w": sum(1 for r in br if r["pnl"] > 0)},
            "rows": br, "removed": removed,
        })
    for d in report["days"]:
        print("%s  actual %d/%d %9.2f | %s %d/%d %9.2f | %s %d/%d %9.2f | removed %d" % (
            d["day"], d["actual"]["w"], d["actual"]["n"], d["actual"]["pnl"], ref, d["ref"]["w"], d["ref"]["n"], d["ref"]["pnl"],
            best, d["best"]["w"], d["best"]["n"], d["best"]["pnl"], len(d["removed"])))
        for r in d["rows"]:
            print("   %s %-22s %-5s c%s fill %.2f st %.2f R %.2f T1 %s(%sR) | %s | %s | %s | mfe %sR mae %sR | %+.2f | %s | live:%s%s" % (
                r["t"], r["pat"], r["dir"], r["c"], r["fill"], r["stop0"], r["R"], fmt(r["t1"]), fmt(r["t1R"], 1), r["loc"], r["mgmt"],
                r["exits"], fmt(r["mfeR"], 1), fmt(r["maeR"], 1), r["pnl"], r["why"], r["actual"], " NEW" if r["new"] else ""))
        for r in d["removed"]:
            print("   (removed by %s) %s %s %s %+.2f" % (best, r["t"], r["pat"], r["dir"], r["pnl"]))
    if out_json:
        def clean(o):
            if isinstance(o, dict):
                return {k: clean(v) for k, v in o.items() if k != "key"}
            if isinstance(o, list):
                return [clean(v) for v in o]
            if isinstance(o, tuple):
                return list(o)
            return o
        json.dump(clean(report), open(out_json, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
