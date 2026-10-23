# -*- coding: utf-8 -*-
"""Render week_report.py --json output as one markdown section per day (Michael's doc). usage: week_md.py report.json outdir"""
import json, sys, os

ref_he = "מערכת נוכחית"
best_he = "עם התיקונים"


def m(x):
    return ("%+.2f" % x) if isinstance(x, (int, float)) else "—"


def f2(x):
    return ("%.2f" % x) if isinstance(x, (int, float)) else "—"


def r1(x):
    return ("%.1f" % x) if isinstance(x, (int, float)) else "—"


def he_dir(d):
    return "לונג" if d == "LONG" else "שורט"


def main():
    rep = json.load(open(sys.argv[1]))
    outdir = sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    for d in rep["days"]:
        a, rf, b, ctx = d["actual"], d["ref"], d["best"], d["ctx"]
        prev, pd, ib = ctx.get("prev") or {}, ctx.get("pd") or {}, ctx.get("ib")
        green = "ירוק" if b["pnl"] > 0 else "אדום"
        lines = ["## %s — %s: %s עם התיקונים (בפועל %s)" % (d["he"], green, m(b["pnl"]), m(a["pnl"])), ""]
        lines.append("בפועל בדמו: %d עסקאות, %d ירוקות, %s. %s (סימולציה): %d עסקאות, %s. %s: %d עסקאות, %d ירוקות, %s (דולר)." % (
            a["n"], a["w"], m(a["pnl"]), ref_he, rf["n"], m(rf["pnl"]), best_he, b["n"], b["w"], m(b["pnl"])))
        lines.append("")
        ctxs = []
        if ctx.get("open"):
            ctxs.append("פתיחה %s" % f2(ctx["open"]))
        if prev.get("vah"):
            ctxs.append("ערך-אתמול VAH %s / POC %s / VAL %s" % (f2(prev.get("vah")), f2(prev.get("poc")), f2(prev.get("val"))))
        if pd.get("pd_high"):
            ctxs.append("טווח-אתמול %s–%s" % (f2(pd.get("pd_low")), f2(pd.get("pd_high"))))
        if ib:
            ctxs.append("IB %s–%s" % (f2(ib[1]), f2(ib[0])))
        if ctx.get("close"):
            ctxs.append("סגירה %s" % f2(ctx["close"]))
        lines.append("**השוק:** " + " · ".join(ctxs))
        lines.append("")
        if d["rows"]:
            lines.append("| שעה | עסקה | ביצוע: כניסה / סטופ · R · חוזים | יעדים | מיקום | ניהול | מימושים | MFE / MAE | דולר | בפועל | למה |")
            lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
            for r in d["rows"]:
                tg = " / ".join(f2(x) for x in (r.get("targets") or [])) or f2(r.get("t1"))
                pos = "%s · %s · %s · שלב %s" % (r["loc"], r.get("opening") or "—", r.get("daytype") or "—", r.get("phase"))
                new = " (חדשה)" if r.get("new") else ""
                lines.append("| %s | %s %s%s | %s / %s · R %s · %sח׳ | %s (T1 %sR) | %s | %s | %s | %sR / %sR | %s | %s | %s |" % (
                    r["t"], r["pat"], he_dir(r["dir"]), new, f2(r["fill"]), f2(r["stop0"]), f2(r["R"]), r.get("c"),
                    tg, r1(r.get("t1R")), pos, r["mgmt"], r["exits"], r1(r.get("mfeR")), r1(r.get("maeR")), m(r["pnl"]),
                    r.get("actual") or "—", r["why"]))
            lines.append("")
        else:
            lines.append("המערכת המעודכנת לא נכנסה לאף עסקה ביום הזה.")
            lines.append("")
        if d["removed"]:
            lines.append("**נחסמו ע״י התיקונים:** " + " · ".join(
                "%s %s %s (%s)" % (r["t"], r["pat"], he_dir(r["dir"]), m(r["pnl"])) for r in d["removed"]))
            lines.append("")
        taken = {r.get("actual", "").split(" ")[0] for r in d["rows"] if r.get("actual") and r["actual"] != "—"}
        miss = [t for t in a["trades"] if ("#%d" % t["id"]) not in taken]
        if miss:
            lines.append("**עסקאות הדמו שבפועל, שהמערכת המעודכנת לא לוקחת:** " + " · ".join(
                "#%d %s %s %s (%s)" % (t["id"], t["t"], t["pat"], he_dir(t["dir"]), m(t["pnl"]) if t["pnl"] is not None else "לא-מתומחר")
                for t in miss))
            lines.append("")
        open(os.path.join(outdir, "%s.md" % d["day"]), "w").write("\n".join(lines))
        print(d["day"], len(lines), "lines")


if __name__ == "__main__":
    main()
