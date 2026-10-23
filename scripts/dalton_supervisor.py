#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-639 — מפקח-דלתון: פיקוח קבוע לעץ ההחלטות — איך דלתון מיושם בכל עסקה (Michael 23.10 "מאשר").

READ-ONLY. For every closed demo/live trade of the window it scores nine Dalton principles from what the system
already records (trade_zoom.py dimensions + the opening type v2 replayed on the day's closed bars + the tree row of
the decision), then aggregates by tree row, by pattern and by principle, and names the rows to fix / to scrap.
Nothing here changes a flag, the tree or a trade — proposals go to Michael's ruling.

  python3 scripts/dalton_supervisor.py --days 20 [--mode demo] [--md docs/reports/dalton_supervisor/2026-10-23.md]
                                       [--html render_mobile_relay/static/docs/dalton.html] [--json path]

Principles (pass ✓ / fail ✗ / not scored ·):
  P1 פתיחה     the opening type v2 at the entry bar vs the trade (phases A/B only): with the holding side of a
               directional opening, or responsive at an edge inside an auction
  P2 שורת-עץ   the decision came through a doctrine row (not no_match / stand_down fallback)
  P3 מיקום     not a mid-value entry without (or long after) an edge test, not at the session extreme
  P4 הרחבה     with the accepted range extension, never against it (T-295)
  P5 יוזם/מגיב initiative with the direction hint on trend days; responsive at an edge on rotation days
  P6 מדרגה→מבחן not into a push (3-bar move ≥ 1.2 ATR in the trade direction) and not a micro-swing stop
  P7 סטופ      0.6–2.5 ATR from the entry (structural, not in the noise, not the whole range)
  P8 T1        T1 ≤ 2.5 R (realism) — and whether it was hit
  P9 ניהול     no runner given back after ≥ 1.5 R without T1 (S6_NO_T1_GIVEBACK), no stop moved against the market
"""
import os, sys, json, argparse, collections, datetime as dt, statistics, subprocess, tempfile, html
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "scripts"))
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all
from backend.v9.systems.opening_classifier_v2 import OpeningLock
import opening_v2_study as ovs
from zoneinfo import ZoneInfo

IL = ZoneInfo("Asia/Jerusalem")
PRINCIPLES = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9"]
P_HEB = {"P1": "פתיחה", "P2": "שורת-עץ", "P3": "מיקום", "P4": "הרחבה", "P5": "יוזם/מגיב", "P6": "מדרגה→מבחן", "P7": "סטופ", "P8": "T1", "P9": "ניהול"}
TREND_DAYS = ("Trend_Normal", "Trend_DD", "Variation", "Normal_Variation")
ROTATION_DAYS = ("Normal", "Neutral_Center", "Neutral_Extreme", "Nontrend")
EDGE_ZONES = ("near_val", "near_vah", "beyond_val", "beyond_vah", "above_vah", "below_val", "outside_above", "outside_below")


def zoom_dicts(since, until, mode):
    """run trade_zoom.py for the window and return its per-trade dimension dicts."""
    out = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    cmd = [sys.executable, os.path.join(ROOT, "scripts", "trade_zoom.py"), "--since", since, "--until", until, "--json", out]
    if mode:
        cmd += ["--mode", mode]
    env = dict(os.environ, LC_ALL="en_US.UTF-8", PYTHONIOENCODING="utf-8")
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=ROOT)
    if r.returncode != 0 and not os.path.exists(out):
        raise SystemExit("trade_zoom failed: %s" % (r.stderr or r.stdout)[-800:])
    try:
        return json.load(open(out, encoding="utf-8"))
    except Exception:
        return []


_DAY_CACHE = {}


def opening_v2_at(day, entry_ts):
    """replay the opening type v2 on the day's closed bars up to the entry (the label the gateway had)."""
    d = dt.date.fromisoformat(str(day)[:10])
    if d not in _DAY_CACHE:
        bars = ovs.rth_bars(d)
        prior = ovs.rth_dates(str(d - dt.timedelta(days=12)), str(d - dt.timedelta(days=1)))
        prev_bars, full = None, []
        for pd_ in prior:
            pb = ovs.rth_bars(pd_)
            if len(pb) >= 30:
                prev_bars = (pd_, pb)
            if len(pb) >= 60:
                full.append(statistics.mean(b["h"] - b["l"] for b in pb)); full = full[-3:]
        prev = ovs.profile(prev_bars[1]) if prev_bars else None
        if prev:
            oh, ol = ovs.overnight(d, prev_bars[0]); prev["on_high"], prev["on_low"] = oh, ol
        _DAY_CACHE[d] = (bars, prev, statistics.mean(full) if full else None)
    bars, prev, atr = _DAY_CACHE[d]
    if not bars or entry_ts is None:
        return None
    ets = entry_ts if isinstance(entry_ts, dt.datetime) else dt.datetime.fromisoformat(str(entry_ts))
    closed = [b for b in bars if b["ts"] + dt.timedelta(minutes=5) <= ets]
    L = OpeningLock(); res = None
    for k in range(1, min(len(closed), 12) + 1):
        res = L.update(closed[:k], prev, atr)
    return res


def score_trade(z):
    """nine verdicts for one trade_zoom dict → {"P1": (mark, note), …}, score, scored."""
    v = {}
    d = (z.get("dir") or "").upper()
    flags = set(z.get("flags") or [])
    atr = z.get("atr") or None
    ph = z.get("ph") or z.get("ph_sys") or ""
    # P1 opening (phases A/B)
    ot = z.get("_v2") or {}
    ott = ot.get("type") or ""
    hold = "LONG" if ot.get("direction") == "up" else ("SHORT" if ot.get("direction") == "down" else None)
    if ph in ("A", "B") and ott and ott != "UNKNOWN":
        if ott in ("OPEN_DRIVE", "OPEN_TEST_DRIVE", "OPEN_REJECTION_REVERSE"):
            v["P1"] = ("✓" if hold == d else "✗", "%s %s · %s" % (ott.replace("OPEN_", ""), ot.get("direction") or "", "עם הצד שמחזיק" if hold == d else "נגד הצד שמחזיק"))
        else:
            # an auction is traded RESPONSIVELY: fade the edge, never chase the session extreme in the trade direction
            chase = "OPENING_AT_EXTREME" in flags
            edge = (bool(z.get("edge_test")) or (str(z.get("zone_calc") or z.get("zone_sys") or "") in EDGE_ZONES)) and not chase
            v["P1"] = ("✓" if edge else "✗", "%s · %s" % (ott.replace("OPEN_", ""), "רודף את הקיצון" if chase else ("מגיב בקצה" if edge else "כניסה באמצע אוקשן")))
    else:
        v["P1"] = ("·", ("%s %s" % (ott.replace("OPEN_", ""), ot.get("direction") or "")).strip() if ott else "—")
    # P2 tree row
    row = str(z.get("tree_row") or "")
    rid = row.split("row=")[1].split()[0] if "row=" in row else "?"
    v["P2"] = ("✗" if rid in ("no_match", "stand_down", "?") else "✓", rid)
    # P3 location
    bad = flags & {"MID_NO_EDGE_TEST", "MID_LATE_AFTER_TEST", "OPENING_AT_EXTREME"}
    v["P3"] = ("✗" if bad else "✓", ", ".join(sorted(bad)) if bad else (str(z.get("zone_calc") or z.get("zone_sys") or "") or "—"))
    # P4 extension
    ext = str(z.get("ext") or "none")
    if ext in ("up", "down"):
        against = "COUNTER_ACCEPTED_EXT" in flags or (ext == "up" and d == "SHORT") or (ext == "down" and d == "LONG")
        v["P4"] = ("✗" if against else "✓", "הרחבה %s %s" % (ext, "נגד" if against else "עם"))
    else:
        v["P4"] = ("·", "אין הרחבה")
    # P5 kind vs day type
    dtp = str(z.get("day_type") or "")
    hint = str(z.get("dir_hint") or "")
    zone = str(z.get("zone_calc") or z.get("zone_sys") or "")
    if dtp in TREND_DAYS and hint in ("LONG", "SHORT"):
        v["P5"] = ("✓" if hint == d else "✗", "%s · %s" % (dtp, "עם הרמז" if hint == d else "נגד הרמז %s" % hint))
    elif dtp in ROTATION_DAYS:
        edge = bool(z.get("edge_test")) or zone in EDGE_ZONES
        v["P5"] = ("✓" if edge else "✗", "%s · %s" % (dtp, "מגיב בקצה" if edge else "יוזם באמצע"))
    else:
        v["P5"] = ("·", dtp or "FORMING")
    # P6 step→test
    m3 = z.get("move3")
    into = False
    try:
        if m3 is not None and atr:
            into = ((float(m3) if d == "LONG" else -float(m3)) >= 1.2 * float(atr))
    except (TypeError, ValueError):
        into = False
    micro = "STOP_IN_MICRO_SWING" in flags
    v["P6"] = ("✗" if (into or micro) else "✓", "; ".join(x for x in (("לתוך דחיפה (%.1f ATR)" % (abs(float(m3)) / float(atr)) if into else ""), ("סטופ במיקרו-סווינג" if micro else "")) if x) or "אחרי השהיה")
    # P7 stop
    try:
        risk_atr = float(z.get("risk") or 0) / float(atr) if atr else None
    except (TypeError, ValueError):
        risk_atr = None
    if risk_atr is None:
        v["P7"] = ("·", "—")
    else:
        v["P7"] = ("✓" if 0.6 <= risk_atr <= 2.5 else "✗", "%.1f ATR" % risk_atr)
    # P8 T1
    t1r = z.get("t1_r")
    try:
        t1r = float(t1r) if t1r is not None else None
    except (TypeError, ValueError):
        t1r = None
    hit = bool(z.get("t1_hit"))
    if t1r is None:
        v["P8"] = ("·", "T1 %s" % ("הושג" if hit else "לא"))
    else:
        v["P8"] = ("✓" if t1r <= 2.5 else "✗", "T1 %.1fR · %s" % (t1r, "הושג" if hit else "לא"))
    # P9 management
    acts = z.get("acts") or {}
    give = "S6_NO_T1_GIVEBACK" in flags
    v["P9"] = ("✗" if give else ("✓" if acts else "·"), ("≥1.5R בלי T1 הוחזר" if give else ", ".join("%s×%s" % (k, n) for k, n in sorted(acts.items())) or "—"))
    scored = [p for p in PRINCIPLES if v[p][0] in ("✓", "✗")]
    passed = [p for p in scored if v[p][0] == "✓"]
    return v, (len(passed), len(scored)), rid


def fmt(x, n=2):
    try:
        return ("%%.%df" % n) % float(x)
    except (TypeError, ValueError):
        return "—"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=20); ap.add_argument("--mode", default="demo")
    ap.add_argument("--since", default=None); ap.add_argument("--until", default=None)
    ap.add_argument("--md", default=None); ap.add_argument("--html", default=None); ap.add_argument("--json", default=None)
    a = ap.parse_args()
    today = dt.datetime.now(IL).date()
    until = a.until or str(today + dt.timedelta(days=1))
    since = a.since or str(today - dt.timedelta(days=a.days))
    zs = zoom_dicts(since, until, a.mode)
    zs = [z for z in zs if z.get("pnl") is not None]
    rows = []
    for z in zs:
        try:
            z["_v2"] = opening_v2_at(z.get("day"), _entry_ts(z))
        except Exception as _e:
            z["_v2"] = None
        v, (p, s), rid = score_trade(z)
        rows.append({"z": z, "v": v, "score": p, "scored": s, "rid": rid})
    rows.sort(key=lambda r: (str(r["z"].get("day")), str(r["z"].get("time"))))
    L = []
    P = L.append
    P("# מפקח-דלתון — %s · %s · %d עסקאות (%s → %s)" % (today, a.mode, len(rows), since, until))
    P("")
    P("**מה זה:** לכל עסקה סגורה — תשעה עקרונות של דלתון מהנתונים שהמערכת כבר רושמת (זום-אין, סוג-הפתיחה v2 כפי שהיה בבר-הכניסה, שורת-העץ). ✓ מקיים · ✗ מפר · · לא נמדד. "
      "קריאה-בלבד; ההצעות בסוף — לפסיקת מייקל.")
    P("")
    P("## 1. לפי עסקה")
    P("")
    P("| יום | # | תבנית | כיוון | שורת-עץ | " + " | ".join("%s %s" % (p, P_HEB[p]) for p in PRINCIPLES) + " | ציון | R | $ |")
    P("|---|---|---|---|---|" + "---|" * len(PRINCIPLES) + "---|---|---|")
    for r in rows:
        z = r["z"]
        P("| %s | %s | %s | %s | %s | %s | **%d/%d** | %s | %s |" % (
            str(z.get("day"))[5:], z.get("id"), z.get("pat"), z.get("dir"), r["rid"],
            " | ".join("%s %s" % (r["v"][p][0], r["v"][p][1]) for p in PRINCIPLES), r["score"], r["scored"], fmt(z.get("pnl_r"), 2), fmt(z.get("pnl"), 2)))
    # per principle: fail rate winners vs losers
    P("")
    P("## 2. לפי עקרון — שיעור-הפרה אצל המפסידות מול המנצחות")
    P("")
    P("| עקרון | נמדד | הפרה אצל מפסידות | הפרה אצל מנצחות | Σ$ כשמופר | Σ$ כשמקוים |")
    P("|---|---|---|---|---|---|")
    for p in PRINCIPLES:
        sc = [r for r in rows if r["v"][p][0] in ("✓", "✗")]
        los = [r for r in sc if float(r["z"].get("pnl") or 0) <= 0]; win = [r for r in sc if float(r["z"].get("pnl") or 0) > 0]
        fl = sum(1 for r in los if r["v"][p][0] == "✗"); fw = sum(1 for r in win if r["v"][p][0] == "✗")
        s_fail = sum(float(r["z"].get("pnl") or 0) for r in sc if r["v"][p][0] == "✗"); s_pass = sum(float(r["z"].get("pnl") or 0) for r in sc if r["v"][p][0] == "✓")
        P("| %s %s | %d | %d/%d | %d/%d | %+.2f | %+.2f |" % (p, P_HEB[p], len(sc), fl, len(los), fw, len(win), s_fail, s_pass))
    # per tree row
    P("")
    P("## 3. לוח-ניקוד לפי שורת-עץ")
    P("")
    P("| שורת-עץ | עסקאות | win% | Σ$ | T1 הושג | ציון-דלתון ממוצע | ההפרה הנפוצה | פסק |")
    P("|---|---|---|---|---|---|---|---|")
    byrow = collections.defaultdict(list)
    for r in rows:
        byrow[r["rid"]].append(r)
    verdicts = []
    for rid, rs in sorted(byrow.items(), key=lambda kv: sum(float(x["z"].get("pnl") or 0) for x in kv[1])):
        n = len(rs); w = sum(1 for x in rs if float(x["z"].get("pnl") or 0) > 0); net = sum(float(x["z"].get("pnl") or 0) for x in rs)
        t1 = sum(1 for x in rs if x["z"].get("t1_hit")); msc = statistics.mean((x["score"] / x["scored"]) if x["scored"] else 0 for x in rs)
        fails = collections.Counter(p for x in rs for p in PRINCIPLES if x["v"][p][0] == "✗")
        top = ", ".join("%s %s (%d)" % (p, P_HEB[p], c) for p, c in fails.most_common(2)) or "—"
        if n >= 3 and net < 0 and msc < 0.6:
            verdict = "🔧 לתקן/לגרוס"
        elif n >= 3 and net < 0:
            verdict = "⚠ מפסידה עם ציון סביר — לבדוק ניהול/מיקום"
        elif n >= 3 and net > 0:
            verdict = "✅ עובדת"
        else:
            verdict = "· מעט נתונים"
        verdicts.append((rid, n, net, msc, verdict, top))
        P("| %s | %d | %d%% | %+.2f | %d/%d | %.2f | %s | %s |" % (rid, n, round(100.0 * w / n) if n else 0, net, t1, n, msc, top, verdict))
    # per pattern
    P("")
    P("## 4. לפי תבנית")
    P("")
    P("| תבנית | עסקאות | win% | Σ$ | ציון ממוצע | ההפרה הנפוצה |")
    P("|---|---|---|---|---|---|")
    bypat = collections.defaultdict(list)
    for r in rows:
        bypat[str(r["z"].get("pat"))].append(r)
    for pat, rs in sorted(bypat.items(), key=lambda kv: sum(float(x["z"].get("pnl") or 0) for x in kv[1])):
        n = len(rs); w = sum(1 for x in rs if float(x["z"].get("pnl") or 0) > 0); net = sum(float(x["z"].get("pnl") or 0) for x in rs)
        msc = statistics.mean((x["score"] / x["scored"]) if x["scored"] else 0 for x in rs)
        fails = collections.Counter(p for x in rs for p in PRINCIPLES if x["v"][p][0] == "✗")
        P("| %s | %d | %d%% | %+.2f | %.2f | %s |" % (pat, n, round(100.0 * w / n) if n else 0, net, msc, ", ".join("%s (%d)" % (p, c) for p, c in fails.most_common(2)) or "—"))
    # verdict block
    P("")
    P("## 5. פסקי-דין להצעה (לפסיקת מייקל — אפס שינוי אוטומטי)")
    P("")
    bad = [x for x in verdicts if x[4].startswith("🔧")]
    if bad:
        for rid, n, net, msc, verdict, top in bad:
            P("- **%s** — %d עסקאות, %+.2f$, ציון %.2f, ההפרה הנפוצה: %s ⇒ %s" % (rid, n, net, msc, top, verdict))
    else:
        P("- אין שורה עם ≥ 3 עסקאות שגם מפסידה וגם מפרה את דלתון ברוב העסקאות.")
    tot = sum(float(r["z"].get("pnl") or 0) for r in rows)
    if rows:
        msc_all = statistics.mean((r["score"] / r["scored"]) if r["scored"] else 0 for r in rows)
        hi = [r for r in rows if r["scored"] and r["score"] / r["scored"] >= 0.75]; lo = [r for r in rows if r["scored"] and r["score"] / r["scored"] < 0.5]
        P("- **ציון-דלתון ≥ 0.75:** %d עסקאות, %+.2f$ · **ציון < 0.5:** %d עסקאות, %+.2f$ · כלל: %d עסקאות %+.2f$, ציון ממוצע %.2f" % (
            len(hi), sum(float(r["z"].get("pnl") or 0) for r in hi), len(lo), sum(float(r["z"].get("pnl") or 0) for r in lo), len(rows), tot, msc_all))
    text = "\n".join(L)
    print(text)
    if a.md:
        os.makedirs(os.path.dirname(os.path.join(ROOT, a.md)), exist_ok=True)
        open(os.path.join(ROOT, a.md), "w", encoding="utf-8").write(text + "\n")
        print("wrote", a.md)
    if a.json:
        json.dump([{"id": r["z"].get("id"), "day": str(r["z"].get("day")), "pat": r["z"].get("pat"), "dir": r["z"].get("dir"), "row": r["rid"],
                    "pnl": r["z"].get("pnl"), "score": r["score"], "scored": r["scored"], "v": {p: list(r["v"][p]) for p in PRINCIPLES}} for r in rows],
                  open(os.path.join(ROOT, a.json), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if a.html:
        write_html(os.path.join(ROOT, a.html), text, today)
        print("wrote", a.html)


def _entry_ts(z):
    """entry timestamp of a zoom dict (day + IL time)."""
    try:
        d = dt.date.fromisoformat(str(z.get("day"))[:10]); hh, mm = str(z.get("time"))[:5].split(":")
        return dt.datetime(d.year, d.month, d.day, int(hh), int(mm), tzinfo=IL)
    except Exception:
        return None


def write_html(path, md_text, today):
    """phone page: the Markdown rendered minimally (tables → <table>)."""
    out = ["<!doctype html><html lang='he' dir='rtl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
           "<title>מפקח-דלתון %s</title><style>body{font-family:-apple-system,Arial;background:#0d1117;color:#c9d1d9;margin:12px;font-size:13px}"
           "table{border-collapse:collapse;width:100%%;margin:6px 0;font-size:11px}td,th{border:1px solid #30363d;padding:3px 4px;vertical-align:top}th{background:#161b22}"
           "h1{font-size:18px}h2{font-size:15px;color:#79c0ff}code{color:#d2a8ff}</style></head><body>" % today]
    in_table = False
    for line in md_text.split("\n"):
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue
            if not in_table:
                out.append("<table>"); in_table = True
            tag = "th" if (out[-1] == "<table>") else "td"
            out.append("<tr>" + "".join("<%s>%s</%s>" % (tag, html.escape(c).replace("**", ""), tag) for c in cells) + "</tr>")
            continue
        if in_table:
            out.append("</table>"); in_table = False
        if line.startswith("# "):
            out.append("<h1>%s</h1>" % html.escape(line[2:]))
        elif line.startswith("## "):
            out.append("<h2>%s</h2>" % html.escape(line[3:]))
        elif line.startswith("- "):
            out.append("<div>• %s</div>" % html.escape(line[2:]).replace("**", ""))
        elif line.strip():
            out.append("<p>%s</p>" % html.escape(line).replace("**", ""))
    if in_table:
        out.append("</table>")
    out.append("</body></html>")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write("\n".join(out))


if __name__ == "__main__":
    main()
