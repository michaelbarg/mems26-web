#!/usr/bin/env python3
"""build_tree_page.py — turn tree_path_3days.jsonl (from tree_path_extract.py) into the artifact page.
Usage: build_tree_page.py IN.jsonl TEMPLATE.html OUT.html [stories.json]
"""
import json, sys, datetime

HE_DAYS = {"2026-10-19": "יום ב׳ 19.10", "2026-10-20": "יום ג׳ 20.10", "2026-10-21": "יום ד׳ 21.10"}
TAG_LABEL = {
    "mnxs": ("ריצה אחרי התיקון", "אותו עץ, T-612 + גארד T-627 + הדגלים שנפסקו (n2rsNx) — ללא תיקוני-הפתיחה המוצעים"),
    "mnxofs": ("ריצה + שני תיקוני-פתיחה", "כמו אחרי התיקון + OPENING_HALF_RANGE_GATE_V1 + EDGE_FAILED_EXT_LIVE_V1"),
    "mnxalls": ("ריצה + ארבעת תיקוני-הפתיחה", "כמו אחרי התיקון + ארבעת דגלי T-628 (חצי-טווח, קצה-חי, ELQ-skip, יעדים-מבניים)"),
    "mnxall": ("ריצה + ארבעת תיקוני-הפתיחה (ליל 21.10, בלי גארד T-627)", "העץ + n2rsNx + ארבעת דגלי T-628; הטרייל בלי הגארד — רגלי BE מחוץ לנר אפשריות (פאנטום)"),
}


def tsec(t):
    try:
        h, m, s = t.split(":"); return int(h) * 3600 + int(m) * 60 + int(float(s))
    except Exception:
        return None


def il_of_iso(ts):
    # '2026-10-21T13:30:03+00:00' → '16:30:03' (UTC+3 in October)
    try:
        dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        dt = dt + datetime.timedelta(hours=3)
        return dt.strftime("%H:%M:%S")
    except Exception:
        return ts or ""


def main():
    src, tpl, out = sys.argv[1], sys.argv[2], sys.argv[3]
    stories = json.load(open(sys.argv[4], encoding="utf-8")) if len(sys.argv) > 4 else {}
    tree = None; days = {}; harn = {}
    for line in open(src, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        if r["section"] == "tree":
            tree = r
        elif r["section"] == "day":
            days[r["date"]] = r
        elif r["section"] == "harness":
            harn.setdefault(r["date"], {})[r["tag"]] = r
    D = {"tree": {"version": tree.get("version"), "path": tree.get("path"), "tree": tree.get("tree")}, "days": [], "footer": ""}
    for d in sorted(days):
        day = days[d]
        bars = day.get("bars") or []
        first12 = [b for b in bars if b["t"] < "17:30"]
        s = {}
        if bars:
            s.update(open=bars[0]["o"], high=max(b["h"] for b in bars), low=min(b["l"] for b in bars), close=bars[-1]["c"])
        if first12:
            s.update(ib_high=max(b["h"] for b in first12), ib_low=min(b["l"] for b in first12))
        pv = next((t for t in day.get("tpo") or [] if str(t.get("trading_date")) == str(day.get("prev")) and t.get("session_type") == "CASH"), None)
        if pv:
            s["pv"] = {"vah": pv.get("vah_price"), "val": pv.get("val_price"), "poc": pv.get("poc_price")}
        tv = next((t for t in day.get("tpo") or [] if str(t.get("trading_date")) == d and t.get("session_type") == "CASH"), None)
        if tv:
            s["tv"] = {"vah": tv.get("vah_price"), "val": tv.get("val_price"), "poc": tv.get("poc_price")}
        # demo trades
        trades_demo = []
        for t in day.get("trades") or []:
            pnl = t.get("pnl")
            trades_demo.append({"t": t.get("entry_t"), "cls": t.get("cls"), "dir": t.get("dir"), "entry": t.get("entry"), "stop": t.get("stop"),
                                "contracts": t.get("contracts"), "t1": t.get("t1"), "exit_t": t.get("exit_t"), "exit": t.get("exit"),
                                "exit_desc": (t.get("exit_reason") or "") + ("" if t.get("exit") is None else " @ %s" % t.get("exit")),
                                "pnl": pnl, "note": (t.get("state") or "") + ((" · " + (t.get("outcome") or "")) if t.get("outcome") else ""), "id": t.get("id")})
        s["demo_pnl"] = round(sum((t.get("pnl") or 0) for t in trades_demo), 2) if trades_demo else 0.0
        # day-type timeline (from the DB state rows; ts naive UTC → +3h)
        tl = []
        for e in day.get("day_type") or []:
            ts = str(e.get("ts") or "")
            hhmm = ts[11:16]
            try:
                h = (int(hhmm[:2]) + 3) % 24; hhmm = "%02d:%s" % (h, hhmm[3:5])
            except Exception:
                pass
            lab = e.get("day_type") or e.get("label") or ""
            conf = e.get("confidence") or e.get("conf") or e.get("day_type_conf")
            ext = e.get("extension") or e.get("ext") or e.get("direction") or e.get("dir")
            ot = e.get("opening_type") or e.get("opening")
            txt = lab + (" (%.2f)" % float(conf) if conf not in (None, "") else "") + ((" · " + str(ext)) if ext else "") + ((" · " + str(ot)) if ot else "")
            if not tl or tl[-1]["label"] != txt:
                tl.append({"t": hhmm, "label": txt})
        # harness runs
        hs = []
        base = None
        for tag, h in (harn.get(d) or {}).items():
            label, desc = TAG_LABEL.get(tag, (tag, ""))
            tr = []
            for t in h.get("trades") or []:
                tr.append({"t": t.get("fired_il"), "cls": t.get("classification"), "dir": t.get("direction"), "entry": t.get("fill_price") or t.get("entry"),
                           "stop": t.get("stop_initial"), "contracts": t.get("contracts"), "t1": t.get("t1_target"), "legs": t.get("legs"),
                           "exit_t": t.get("exit_il"), "pnl": t.get("pnl_usd"), "note": (t.get("outcome") or "") + ((" · " + t.get("day_type_at_entry")) if t.get("day_type_at_entry") else "")})
            hs.append({"tag": tag, "label": label, "desc": desc, "daily_pnl": h.get("daily_pnl"), "trades": tr, "f5_trail": h.get("f5_trail")})
            if tag == "mnxs":
                base = h
        # opening type from the harness s1 timeline
        if base:
            for e in base.get("s1") or []:
                if e.get("ot_locked"):
                    s["opening_live"] = "%s @ %s" % (e.get("ot_locked"), e.get("il")); break
            for e in reversed(base.get("s1") or []):
                if e.get("canonical_opening") and "<3" not in str(e.get("canonical_opening")):
                    s["opening_bars"] = e.get("canonical_opening"); break
        # decisions: harness base decisions carry the path; join the demo DB rows
        dec = []
        db_rows = [r for r in (day.get("decisions") or []) if r.get("kind") == "DECISION"]
        used = set()
        src_rows = (base or {}).get("decisions") or []
        for e in src_rows:
            t = il_of_iso(e.get("ts"))
            best, bi = None, None
            for i, r in enumerate(db_rows):
                if i in used or r.get("cls") != e.get("pattern") or r.get("dir") != e.get("dir"):
                    continue
                dt = abs((tsec(r.get("t")) or 0) - (tsec(t) or 0))
                if dt <= 150 and (best is None or dt < best):
                    best, bi = dt, i
            demo = ""; demo_pnl = None; demo_trade = False
            if bi is not None:
                used.add(bi); r = db_rows[bi]
                if r.get("blocked"):
                    demo = "נחסם: " + str(r.get("blocked"))
                else:
                    tt = next((x for x in trades_demo if x.get("dir") == r.get("dir") and abs((tsec(x.get("t")) or 0) - (tsec(r.get("t")) or 0)) <= 180), None)
                    if tt:
                        demo = "בוצע #%s" % tt.get("id"); demo_pnl = tt.get("pnl"); demo_trade = True
                    else:
                        demo = "TAKE (ללא עסקה)"
            else:
                demo = "—"
            reason = e.get("reason") or ""
            dec.append({"t": t, "sys": e.get("sys"), "pattern": e.get("pattern"), "dir": e.get("dir"), "entry": e.get("entry"), "path": e.get("path"),
                        "leaf": e.get("leaf"), "id": e.get("id"), "blocked": e.get("blocked") if e.get("leaf") == "TAKE" else None,
                        "reason_short": reason[:110] if e.get("leaf") == "TAKE" and e.get("blocked") else "", "outcome": e.get("outcome"),
                        "trade_id": e.get("trade_id"), "pnl": next((x.get("pnl_usd") for x in (base.get("trades") or []) if x.get("trade_id") == e.get("trade_id")), None) if e.get("trade_id") else None,
                        "demo": demo, "demo_pnl": demo_pnl, "demo_trade": demo_trade})
        # DB decisions not matched (e.g. demo-only candidates)
        for i, r in enumerate(db_rows):
            if i in used:
                continue
            m = None
            rs = r.get("reason") or ""
            if "[" in rs and rs.endswith("]"):
                m = rs[rs.rfind("[") + 1:-1]
            dec.append({"t": r.get("t"), "sys": r.get("sys"), "pattern": r.get("cls"), "dir": r.get("dir"), "entry": r.get("entry"), "path": m,
                        "leaf": "SKIP" if str(r.get("blocked") or "").startswith("tree:") else ("TAKE" if not r.get("blocked") else "TAKE"),
                        "id": (r.get("blocked") or "").replace("tree:", "") if str(r.get("blocked") or "").startswith("tree:") else "",
                        "blocked": None if str(r.get("blocked") or "").startswith("tree:") else r.get("blocked"), "reason_short": "", "outcome": "דמו בלבד",
                        "trade_id": None, "pnl": None, "demo": "דמו בלבד", "demo_pnl": None, "demo_trade": False})
        dec.sort(key=lambda x: tsec(x.get("t") or "00:00:00") or 0)
        D["days"].append({"date": d, "label": HE_DAYS.get(d, d), "token": "d" + d.replace("-", ""), "title": HE_DAYS.get(d, d) + " — " + d,
                          "story": stories.get(d, ""), "summary": s, "day_type": tl, "bars": bars, "trades_demo": trades_demo, "harness": hs, "decisions": dec})
    D["footer"] = stories.get("_footer", "")
    html = open(tpl, encoding="utf-8").read().replace("/*DATA*/", json.dumps(D, ensure_ascii=False).replace("</", "<\\/"))
    open(out, "w", encoding="utf-8").write(html)
    print("wrote", out, len(html), "bytes; days", [ (x["date"], len(x["decisions"]), len(x["trades_demo"]), [h["tag"] for h in x["harness"]]) for x in D["days"]])


if __name__ == "__main__":
    main()
