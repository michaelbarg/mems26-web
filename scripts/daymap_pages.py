#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""daymap_pages.py — DAYMAP («פירוק-יום») phone pages: one self-contained RTL Hebrew HTML per day + an index.

Reads harness_out/daymap/<version>/<D>.json (+ SUMMARY.json when present) and writes
  render_mobile_relay/static/docs/daymap/<D>.html   and   render_mobile_relay/static/docs/daymap/index.html
Mobile-first (≈390 px), light + dark (prefers-color-scheme), inline CSS/JS, no external requests. The CSS follows
render_mobile_relay/static/docs/days/*.html (cards, chips, pills, sticky header, ?key= link carry-over) with a light theme
added. Writes nothing else; does not deploy or push.

  python3 scripts/daymap_pages.py [--version base-20.10] [--dir harness_out/daymap/base-20.10] [--date 2026-10-19 ...] [--out DIR]
"""
import os, sys, json, glob, html, argparse, datetime as dt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import daymap_lib as L  # noqa: E402

E = lambda x: html.escape("" if x is None else str(x))
DOW_HEB = {"Mon": "שני", "Tue": "שלישי", "Wed": "רביעי", "Thu": "חמישי", "Fri": "שישי", "Sat": "שבת", "Sun": "ראשון"}
FAM_CLS = {"Trend": "ft", "Variation": "fv", "Normal": "fn", "Neutral": "fu", "Nontrend": "fx", None: "fq"}
VIEW_HEB = {"live": "לייב/דמו", "replay": "ריפליי"}
ALT_HEB = {"Up-ext": "הרחבה ↑", "Down-ext": "הרחבה ↓", "Trend": "מגמה", "Variation": "וריאציה", "Neutral": "ניטרלי"}
ACT_HEB = {"T0_HIT": "T0 מומש", "T1_HIT": "T1 מומש", "T2_HIT": "T2 מומש", "T3_HIT": "T3 מומש", "SMART_BE": "סטופ ל-BE", "TARGET_REALISM": "יעד קורב",
           "SWING_TRAIL": "טריילינג-סווינג", "STRUCT_TRAIL": "טריילינג-מבני", "TRAIL": "טריילינג", "STOP_HIT": "סטופ", "STOP_HIT_PARTIAL": "סטופ חלקי",
           "STOP_AFTER_T2": "סטופ אחרי T2", "BE_MOVED": "סטופ הוזז ל-BE"}

CSS = """
:root{color-scheme:light dark;--bg:#f6f8fa;--card:#ffffff;--card2:#f0f3f6;--line:#d0d7de;--fg:#1f2328;--dim:#59636e;--acc:#0969da;--up:#1a7f37;--dn:#cf222e;--am:#9a6700;
--ft:#0969da;--fv:#bf8700;--fn:#1a7f37;--fu:#8250df;--fx:#6e7781;--fq:#d0d7de;--hdr:#ffffffee}
@media (prefers-color-scheme:dark){:root{--bg:#0b0e14;--card:#161b22;--card2:#0d1117;--line:#30363d;--fg:#e6edf3;--dim:#8b949e;--acc:#58a6ff;--up:#3fb950;--dn:#f85149;--am:#d29922;
--ft:#388bfd;--fv:#d29922;--fn:#3fb950;--fu:#a371f7;--fx:#8b949e;--fq:#30363d;--hdr:#0d1117ee}}
*{box-sizing:border-box}html,body{max-width:100%;overflow-x:hidden}
body{margin:0;background:var(--bg);color:var(--fg);font-family:-apple-system,"Helvetica Neue",Arial,sans-serif;font-size:16px;line-height:1.5;padding:0 0 40px}
a{color:var(--acc);text-decoration:none}
.hdr{position:sticky;top:0;z-index:20;display:flex;align-items:center;gap:8px;background:var(--hdr);backdrop-filter:blur(6px);border-bottom:1px solid var(--line);padding:8px 12px;padding-top:calc(8px + env(safe-area-inset-top))}
.hdr .t{flex:1;min-width:0;font-weight:700;font-size:17px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hdr .sub{font-size:12px;color:var(--dim);font-weight:400;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ib{background:var(--card);border:1px solid var(--line);color:var(--fg);border-radius:10px;font-size:18px;min-width:40px;height:38px;display:inline-flex;align-items:center;justify-content:center;padding:0 10px}
.ib.dis{opacity:.35;pointer-events:none}
.wrap{padding:10px 12px 8px;max-width:760px;margin:0 auto}
h2{font-size:15px;margin:18px 0 8px;display:flex;align-items:center;gap:8px}
h2 .dim{font-weight:400}
.dim{color:var(--dim);font-size:13px}
.num{direction:ltr;unicode-bidi:embed;font-variant-numeric:tabular-nums}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 14px;margin:10px 0}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}
.chip{background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:999px;padding:5px 11px;font-size:13px}
.chip b{font-weight:700}
.vsw{display:flex;gap:6px;margin:10px 0}.vsw button{flex:1;background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:10px;padding:9px 4px;font-size:15px}
.vsw button.on{background:var(--acc);border-color:var(--acc);color:#fff}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;border:1px solid var(--line);background:var(--card2);margin:2px 0 2px 4px;white-space:nowrap}
.pill.ok{border-color:var(--up);color:var(--up)}.pill.bad{border-color:var(--dn);color:var(--dn)}.pill.warn{border-color:var(--am);color:var(--am)}
.pos{color:var(--up)}.neg{color:var(--dn)}
.notes{margin:0;padding:0 18px 0 0}.notes li{margin:4px 0;font-size:14px}
.kv{display:grid;grid-template-columns:repeat(3,1fr);gap:5px}
.kv.two{grid-template-columns:repeat(2,1fr)}
.kv div{background:var(--card2);border-radius:8px;padding:5px 7px;min-width:0}
.kv .l{font-size:11px;color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.kv .v{font-size:14px;font-weight:600;overflow-wrap:anywhere}
.strip{display:grid;grid-template-columns:repeat(5,1fr);gap:4px;margin:8px 0}
.ph{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:6px 5px;min-width:0;cursor:pointer;text-align:center}
.ph.on{border-color:var(--acc);box-shadow:0 0 0 1px var(--acc) inset}
.ph .p{font-weight:800;font-size:15px}.ph .m{font-size:11px;color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ph .f{font-size:12px;font-weight:600}
.phd{display:none}.phd.on{display:block}
.bar{position:relative;height:22px;border-radius:6px;overflow:hidden;background:var(--card2);border:1px solid var(--line);direction:ltr}
.bar span{position:absolute;top:0;bottom:0}
.bar i{position:absolute;top:-2px;bottom:-2px;width:2px;background:var(--fg);opacity:.85}
.ft{background:var(--ft)}.fv{background:var(--fv)}.fn{background:var(--fn)}.fu{background:var(--fu)}.fx{background:var(--fx)}.fq{background:var(--fq)}
.lg{display:inline-block;width:10px;height:10px;border-radius:3px;margin-left:4px;vertical-align:middle}
.axis{display:flex;justify-content:space-between;font-size:10.5px;color:var(--dim);direction:ltr;margin-top:2px}
table.plain{border-collapse:collapse;width:100%;font-size:13px}
table.plain th,table.plain td{padding:6px 5px;border-bottom:1px solid var(--line);text-align:right;vertical-align:top}
table.plain th{color:var(--dim);font-weight:600}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
.tr{border-right:5px solid var(--dim)}.tr.win{border-right-color:var(--up)}.tr.loss{border-right-color:var(--dn)}.tr.be{border-right-color:var(--am)}
.row{display:flex;align-items:center;gap:8px;cursor:pointer}.row .g{flex:1;min-width:0}
.row .hl{font-weight:600;overflow-wrap:break-word}
.chev{color:var(--dim);font-size:18px;transition:transform .15s}.card.open .chev{transform:rotate(-90deg)}
.body{display:none;margin-top:10px;border-top:1px solid var(--line);padding-top:10px}.card.open .body{display:block}
.tl{position:relative;padding-right:18px;margin:6px 0}.tl:before{content:"";position:absolute;right:6px;top:2px;bottom:2px;width:2px;background:var(--line)}
.tl .ev{position:relative;margin:0 0 8px;font-size:14px}.tl .ev:before{content:"";position:absolute;right:-16px;top:7px;width:8px;height:8px;border-radius:50%;background:var(--acc)}
.wi{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:6px 0}
.wi div{background:var(--card2);border-radius:8px;padding:6px;text-align:center}.wi .best{outline:2px solid var(--up)}
.wi .l{font-size:11px;color:var(--dim)}.wi .v{font-size:15px;font-weight:700}
.empty{color:var(--dim);text-align:center;padding:14px 0;font-size:14px}
.sec{margin-top:6px}
"""

JS = """
var Q=location.search||'';
function withKey(h){if(!h||/^https?:|^#|^mailto:/.test(h)||h.indexOf('key=')>=0||!Q)return h;var i=h.indexOf('#');var b=i>=0?h.slice(0,i):h,hs=i>=0?h.slice(i):'';return b+(b.indexOf('?')>=0?'&':'?')+Q.slice(1)+hs;}
document.querySelectorAll('a[href]').forEach(function(a){a.setAttribute('href',withKey(a.getAttribute('href')));});
function tog(el){el.classList.toggle('open');}
function view(v){document.querySelectorAll('[data-view]').forEach(function(e){e.style.display=(e.getAttribute('data-view')===v)?'':'none';});
 document.querySelectorAll('.vsw button').forEach(function(b){b.classList.toggle('on',b.getAttribute('data-v')===v);});
 try{localStorage.setItem('daymap_view',v);}catch(e){}}
function ph(v,p){document.querySelectorAll('[data-view="'+v+'"] .ph').forEach(function(e){e.classList.toggle('on',e.getAttribute('data-p')===p);});
 document.querySelectorAll('[data-view="'+v+'"] .phd').forEach(function(e){e.classList.toggle('on',e.getAttribute('data-p')===p);});}
(function(){var bs=document.querySelectorAll('.vsw button');if(!bs.length)return;var v=null;try{v=localStorage.getItem('daymap_view');}catch(e){}
 if(!v||!document.querySelector('[data-view="'+v+'"]'))v=bs[0].getAttribute('data-v');view(v);})();
"""


# ── small helpers ────────────────────────────────────────────────────────────────────────────────
def sg(x, nd=1, suffix=""):
    if x is None:
        return '<span class="dim">—</span>'
    cls = "pos" if x > 0 else ("neg" if x < 0 else "")
    return '<span class="num %s">%s%s</span>' % (cls, ("%+." + str(nd) + "f") % x, suffix)


def mark(ok):
    return '<span class="pill ok">✓</span>' if ok is True else ('<span class="pill bad">✗</span>' if ok is False else '<span class="pill">?</span>')


def dth(x):
    return E(L.dt_heb(x))


def ots(x):
    return E(L.ot_short(x))


def hm2min(s):
    try:
        h, m = str(s)[:5].split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return None


def date_heb(R):
    d = dt.date.fromisoformat(R["date"])
    return "%s %s" % (DOW_HEB.get(R.get("dow"), ""), d.strftime("%d.%m.%Y"))


def kv(items, two=False):
    return '<div class="kv%s">' % (" two" if two else "") + "".join('<div><div class="l">%s</div><div class="v">%s</div></div>' % (E(l), v) for l, v in items) + "</div>"


def nums(xs):
    """A left-to-right group of prices (targets etc.)."""
    xs = [x for x in xs if x is not None]
    return ('<span class="num">%s</span>' % " ".join(("%.2f" % x).rstrip("0").rstrip(".") for x in xs)) if xs else "—"


def px(x):
    return '<span class="num">%s</span>' % (("%.2f" % x).rstrip("0").rstrip(".") if isinstance(x, (int, float)) else "—")


# ── label bar: the S1 label through the session vs the truth ─────────────────────────────────────
def label_bar(R, V, kind="dt"):
    o = hm2min(R["bars"].get("first_il") or "16:30") or 990
    span = 390.0
    tl = [x for x in V["system"]["timeline"] if (V["system"].get("primary") != "s1" or x.get("src") != "dv")]
    segs, cur = [], None
    for x in tl:
        m = hm2min(x["t_il"])
        if m is None:
            continue
        val = x["dt"] if kind == "dt" else x["ot"]
        if m <= o:
            cur = (0.0, val)
            continue
        if cur is None:
            cur = (0.0, "UNKNOWN")
        if val != cur[1]:
            segs.append((cur[0], min(span, m - o), cur[1])); cur = (min(span, m - o), val)
    if cur is None:
        cur = (0.0, "UNKNOWN")
    end = span if not R.get("partial") else max(cur[0], (hm2min(R["bars"].get("last_il")) or (o + span)) - o)
    segs.append((cur[0], end, cur[1]))
    out = []
    for a, b, val in segs:
        if b <= a:
            continue
        cls = FAM_CLS.get(L.dt_family(val)) if kind == "dt" else ("ft" if L.norm_ot(val) == L.norm_ot(R["truth"]["opening"]) else ("fq" if L.norm_ot(val) == "UNKNOWN" else "fv"))
        out.append('<span class="%s" style="left:%.2f%%;width:%.2f%%" title="%s"></span>' % (cls, 100 * a / span, 100 * (b - a) / span, E(val)))
    for t in V["trades"]:
        m = hm2min(t["t_entry"])
        if m is not None and o <= m <= o + span:
            out.append('<i style="left:%.2f%%" title="%s"></i>' % (100 * (m - o) / span, E("%s %s" % (t["fam"], t["t_entry"]))))
    return '<div class="bar">%s</div>' % "".join(out)


def truth_bar(R):
    fam = L.dt_family(R["truth"]["day_type"])
    ib_end = 60.0
    return ('<div class="bar"><span class="fq" style="left:0;width:%.2f%%"></span><span class="%s" style="left:%.2f%%;width:%.2f%%"></span></div>'
            % (100 * ib_end / 390, FAM_CLS.get(fam), 100 * ib_end / 390, 100 * (390 - ib_end) / 390))


def axis(R):
    o = hm2min(R["bars"].get("first_il") or "16:30") or 990
    ticks = [o + k for k in (0, 60, 120, 210, 270, 390)]
    return '<div class="axis">' + "".join("<span>%02d:%02d</span>" % (t // 60, t % 60) for t in ticks) + "</div>"


LEGEND = ('<div class="dim" style="margin-top:6px">' + " ".join('<span class="lg %s"></span>%s' % (c, E(n)) for c, n in
          (("ft", "מגמה"), ("fv", "וריאציה"), ("fn", "נורמלי"), ("fu", "ניטרלי"), ("fx", "ללא-מגמה"), ("fq", "לא-ידוע"))) + " · קו = ירי</div>")


# ── one view ─────────────────────────────────────────────────────────────────────────────────────
def view_html(R, vk):
    V = R[vk]; S = V["summary"]; sy = V["system"]; h = V["hit"]; tr = R["truth"]
    o = []
    if not V.get("available"):
        o.append('<div class="card empty">אין נתוני-מערכת ליום הזה במבט %s — רק השוק והייחוס.</div>' % VIEW_HEB[vk])
    lk = sy.get("lock") or {}
    chips = [
        "פתיחה: <b>%s</b>%s %s" % (ots(lk.get("type") or h.get("sys_opening")), (" " + E(lk.get("t_il"))) if lk.get("t_il") else "", mark(h.get("opening_ok"))),
        "סוג-יום: <b>%s</b> %s" % (dth(h.get("sys_day_type")), mark(h.get("day_type_ok"))),
        "ירי <b>%d</b> · %s נק׳%s" % (S["n_fired"], sg(S.get("pts"), 2), (" · %s" % sg(S.get("usd"), 0, "$")) if S.get("usd") is not None else ""),
        "היה-יורה <b>%d</b> · %s" % (S["n_would"], sg(S.get("would_pts"))),
        "פוספס <b>%d</b> רגליים · %s נק׳" % (S["n_missed"], '<span class="num">%.0f</span>' % (S.get("missed_pts") or 0)),
    ]
    if vk == "replay" and S.get("harness_usd") is not None:
        chips.append("הרנס %s" % sg(S["harness_usd"], 0, "$"))
    o.append('<div class="chips">' + "".join('<span class="chip">%s</span>' % c for c in chips) + "</div>")
    if S.get("notes"):
        o.append('<div class="card"><ul class="notes">' + "".join("<li>%s</li>" % E(n) for n in S["notes"]) + "</ul></div>")
    # phase strip
    o.append("<h2>השלבים <span class='dim'>(הקש לפירוט)</span></h2><div class='strip'>")
    first = next((p for p in L.PHASES if V["phases"][p]["fired"]), None) or next(
        (p for p in L.PHASES if V["phases"][p]["would"]["n"] or V["phases"][p]["legs"]), "A")
    for p in L.PHASES:
        P = V["phases"][p]; M = R["mkt"].get(p) or {}
        nf = len(P["fired"]); fpts = sum((f.get("pts") or 0) for f in P["fired"])
        o.append('<div class="ph%s" data-p="%s" onclick="ph(\'%s\',\'%s\')"><div class="p">%s</div><div class="m">%s</div><div class="f">%s</div><div class="m">%s</div></div>' % (
            " on" if p == first else "", p, vk, p, p, ("נטו %+.0f" % M["net"]) if M.get("net") is not None else "—",
            ("ירי %d %+.0f" % (nf, fpts)) if nf else "ירי 0", ("חסום %d" % P["blocked"]["n"]) if P["blocked"]["n"] else "&nbsp;"))
    o.append("</div>")
    for p in L.PHASES:
        o.append('<div class="phd card%s" data-p="%s">%s</div>' % (" on" if p == first else "", p, phase_detail(R, V, p)))
    # labels vs truth
    o.append("<h2>תווית-היום לאורך היום מול האמת</h2><div class='card'>")
    o.append('<div class="dim">מערכת (%s)</div>%s<div class="dim" style="margin-top:6px">אמת: %s (%s)</div>%s%s%s' % (
        E(sy.get("primary") or "—"), label_bar(R, V, "dt"), dth(tr["day_type"]), "מייקל" if tr["day_type_src"] == "michael" else "ייחוס",
        truth_bar(R), axis(R), LEGEND))
    o.append('<div class="dim" style="margin-top:10px">סוג-הפתיחה במכונה (כחול = כמו האמת %s · כתום = אחר)</div>%s' % (ots(tr["opening"]), label_bar(R, V, "ot")))
    rows = []
    for lab, _ in L.CHECKPOINTS:
        ra = tr["ref_at"].get(lab) or {}; la = sy["labels_at"].get(lab) or {}
        fut = ra.get("future") or la.get("future")
        rows.append("<tr><td class='num'>%s</td><td>%s</td><td>%s%s</td><td>%s</td></tr>" % (
            E(lab), "—" if fut else dth(ra.get("dt")), "—" if fut else dth(la.get("dt")),
            (" <span class='dim'>(מ-%s)</span>" % E(la.get("t_il"))) if (la.get("t_il") and not fut) else "", "—" if fut else ots(la.get("ot"))))
    o.append('<table class="plain" style="margin-top:10px"><tr><th>שעה</th><th>ייחוס</th><th>מערכת</th><th>פתיחה (מערכת)</th></tr>%s</table>' % "".join(rows))
    hl = []
    if h.get("first_ok_t_il"):
        hl.append("תווית נכונה לראשונה %s (+%d דק׳)" % (h["first_ok_t_il"], int(h["first_ok_min"])))
    if h.get("stable_ok_t_il"):
        hl.append("יציבה מ-%s" % h["stable_ok_t_il"])
    if sy.get("flips"):
        hl.append("%d ריצודים" % sy["flips"])
    if sy.get("negs"):
        hl.append("ביטולי-נעילה: " + ", ".join("%s" % x["t_il"] for x in sy["negs"]))
    if sy.get("first_read"):
        hl.append("קריאה ראשונה %s %s" % (L.ot_short(sy["first_read"]["type"]), sy["first_read"]["t_il"]))
    for p_ in sy.get("prov") or []:
        hl.append("T-426 %s→%s (%s) %s" % (L.ot_short(p_["frm"]), L.ot_short(p_["to"]), p_["pattern"], p_["t_il"]))
    if hl:
        o.append('<div class="dim" style="margin-top:8px">%s</div>' % E(" · ".join(hl)))
    o.append("</div>")
    # trades
    o.append("<h2>העסקאות <span class='dim'>%d</span></h2>" % len(V["trades"]))
    if not V["trades"]:
        o.append('<div class="card empty">אין ירי</div>')
    for t in V["trades"]:
        o.append(trade_html(t))
    # would-fire
    if V["would"]:
        o.append("<h2>'היה-יורה' <span class='dim'>%d · עברו את כל השערים, לא נכנסו · סימולציה עד T1</span></h2>" % len(V["would"]))
        rows = "".join("<tr><td class='num'>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            E(w["t_il"]), E(w["phase"]), E(w["fam"]), "↑" if w["dir"] == "LONG" else "↓", sg(w.get("pts")), E(w.get("why_not") or w.get("how") or ""))
            for w in V["would"])
        o.append('<div class="card scroll"><table class="plain"><tr><th>שעה</th><th>שלב</th><th>משפחה</th><th>כיוון</th><th>נק׳</th><th>הערה</th></tr>%s</table></div>' % rows)
    return "".join(o)



def phase_detail(R, V, p):
    P = V["phases"][p]; M = R["mkt"].get(p) or {}
    o = ['<div style="font-weight:700">%s</div>' % E(L.PHASE_HEB.get(p, p))]
    if M.get("n"):
        o.append(kv([("פתיחה", px(M["o"])), ("גבוה", px(M["h"])), ("נמוך", px(M["l"])), ("סגירה", px(M["c"])), ("טווח", px(M["range"])), ("נטו", sg(M["net"], 2))]))
    else:
        o.append('<div class="empty">אין ברים בשלב הזה</div>')
    if M.get("ib_ev"):
        o.append('<div class="sec">' + " · ".join("%s %s @%s" % (E(e["heb"]), E(e["t_il"]), px(e["px"])) for e in M["ib_ev"]) + "</div>")
    o.append('<div class="sec dim">תוויות שנראו: %s</div>' % (" → ".join(dth(x) for x in P["labels"]) or "—"))
    if P["fired"]:
        o.append('<div class="sec">ירי: ' + " · ".join("%s %s %s %s %s" % (E(f["t_il"]), E(f["fam"]), "↑" if f["dir"] == "LONG" else "↓", E(f["outcome"]), sg(f.get("pts")))
                                                   for f in P["fired"]) + "</div>")
    if P["would"]["n"]:
        o.append('<div class="sec">היה-יורה: %d (%d רווחיות) · Σ %s נק׳</div>' % (P["would"]["n"], P["would"]["wins"], sg(P["would"]["pts"])))
    if P["blocked"]["n"]:
        o.append('<div class="sec">נחסמו %d: %s</div>' % (P["blocked"]["n"], E(" · ".join("%s ×%d" % (L.gate_heb(g), n) for g, n in P["blocked"]["top"]))))
    if P["legs"]:
        rows = []
        for lg in P["legs"]:
            cb = ", ".join("%s%s" % (x["id"], "" if x["k"] == "fired" else "ʷ") for x in lg["caught_by"])
            bl = ", ".join("%s/%s" % (x["fam"], x["gate"]) for x in lg.get("blocked") or [])
            rows.append("<tr><td>%s</td><td class='num'>%s–%s</td><td class='num'>%.1f</td><td>%s</td></tr>" % (
                "↑" if lg["dir"] == "LONG" else "↓", E(lg["t_from"]), E(lg["t_to"]), lg["pts"],
                ('<span class="pill ok">%s</span>' % E(cb)) if cb else (('<span class="pill">המערכת לא רצה</span>' if lg.get("covered") is False else '<span class="pill bad">פוספס</span>')
                                                                       + (" <span class='dim'>%s</span>" % E(bl) if bl else ""))))
        o.append('<div class="sec scroll"><table class="plain"><tr><th></th><th>רגל</th><th>נק׳</th><th>נתפסה ע״י (ʷ = היה-יורה)</th></tr>%s</table></div>' % "".join(rows))
    return "".join(o)


def trade_html(t):
    cls = {"WIN": "win", "LOSS": "loss", "BE": "be"}.get(t.get("outcome"), "")
    head = "%s %s %s · %s" % (E(t["t_entry"]), "↑" if t["dir"] == "LONG" else "↓", E(t["fam"]), E(t.get("outcome")))
    pnl = sg(t.get("pts"), 2, " נק׳") + ((" · " + sg(t["usd"], 2, "$")) if t.get("usd") is not None else "")
    if t.get("outcome") == "OPEN" and t.get("usd_open") is not None:
        pnl = "פתוחה · ממומש %s" % sg(t["usd_open"], 2, "$")
    o = ['<div class="card tr %s"><div class="row" onclick="tog(this.parentNode)"><div class="g"><div class="hl">%s</div>'
         '<div class="dim">#%s · %s · S%s · שלב %s · %s</div></div><div>%s</div><span class="chev">‹</span></div><div class="body">' % (
             cls, head, E(t["id"]), E(t["src"]), E(t.get("sys")), E(t["phase"]), E(t.get("pat")), pnl)]
    th, la = t.get("thesis") or {}, t.get("label_at_entry") or {}
    o.append(kv([("תזה בכניסה", "%s · %s" % (dth(th.get("dt")), ots(th.get("ot")))), ("S1 בכניסה", "%s · %s" % (dth(la.get("dt")), ots(la.get("ot"))))], two=True))
    o.append('<div style="height:5px"></div>' + kv([
        ("כניסה", px(t.get("entry"))), ("סטופ התחלתי", px(t.get("stop0"))), ("יעדים", nums(t.get("targets") or [])),
        ("יציאה", "%s %s" % (E(t.get("t_exit") or "—"), E(t.get("exit_reason") or ""))), ("MFE", px(t.get("mfe"))), ("MAE", px(t.get("mae"))),
        ("חוזים", E(t.get("n"))), ("מקור $", E(t.get("usd_src") or "—")), ("מחיר יציאה", px(t.get("exit_px")))]))
    if t.get("sys6") or t.get("be_rule"):
        o.append('<div class="sec" style="font-weight:600">מערכת 6 (ניהול)</div><div class="tl">')
        for a in t.get("sys6") or []:
            o.append('<div class="ev"><span class="num">%s</span> %s <span class="dim">%s</span></div>' % (E(a.get("t_il") or ""), E(ACT_HEB.get(a["action"], a["action"])), E(a.get("detail") or "")))
        if t.get("be_rule"):
            o.append('<div class="ev">כלל-BE: <span class="dim">%s</span></div>' % E(t["be_rule"]))
        o.append("</div>")
    w = t.get("what_if")
    if w:
        o.append('<div class="sec" style="font-weight:600">מה-אם: התווית התחלפה %s→%s ב-%s (בר %s, %s; %s)</div>' % (
            dth(w["frm"]) if w["kind"] == "day_type" else ots(w["frm"]), dth(w["to"]) if w["kind"] == "day_type" else ots(w["to"]), E(w["t_il"]), E(w["flip_bar"]),
            px(w["px"]), "חוזה פתוח אחד" if w["open_n"] == 1 else "%d חוזים פתוחים" % w["open_n"]))
        o.append('<div class="wi">' + "".join('<div class="%s"><div class="l">%s</div><div class="v">%s</div></div>' % ("best" if w["best"] == k else "", lab, sg(w[k.lower()], 2))
                                              for k, lab in (("EXIT", "לצאת"), ("BE", "סטופ ל-BE"), ("HOLD", "להחזיק" + (" (סימ׳)" if w.get("hold_src", "").startswith("sim") else ""))))
                 + "</div>" + ('<div class="dim">%s</div>' % E(w["be_note"]) if w.get("be_note") else ""))
    if t.get("wrong_if"):
        rows = []
        for x in t["wrong_if"]:
            when = ("<b>%s</b> @%s" % (E(x["t_il"]), px(x["px"]))) if x.get("t_il") else "לא קרה"
            if x.get("already"):
                when += " <span class='pill warn'>כבר לפני הכניסה</span>"
            elif x.get("t_il"):
                when += " " + ("<span class='pill bad'>העסקה פתוחה</span>" if x.get("open_then") else "<span class='pill'>אחרי היציאה</span>")
            rows.append("<tr><td>%s</td><td>%s</td><td>%s%s</td></tr>" % (E(ALT_HEB.get(x["alt"], L.dt_heb(x["alt"]))), E(x["rule"]), when,
                                                                       (" <span class='dim'>(S6: %s)</span>" % E(x["sys6_then"])) if x.get("sys6_then") else ""))
        o.append('<div class="sec" style="font-weight:600">אם התזה שגויה</div><div class="scroll"><table class="plain"><tr><th>חלופה</th><th>כלל-אישור</th><th>מתי</th></tr>%s</table></div>' % "".join(rows))
    if t.get("michael"):
        m = t["michael"]
        o.append('<div class="sec">מייקל: %s %s</div>' % (E(m.get("take")), E(" · ".join((m.get("why") or []) + (m.get("would") or [])) + (" — " + m["note"] if m.get("note") else ""))))
    o.append("</div></div>")
    return "".join(o)



# ── page + index ─────────────────────────────────────────────────────────────────────────────────
def page_html(R, prev_d, next_d):
    tr, rf = R["truth"], R["refs"]; pv = rf.get("prev") or {}; on = rf.get("overnight") or {}; ib = R.get("ib") or {}
    views = [v for v in R.get("views", []) if R.get(v)]
    sub = "פירוק-יום · %s · %s%s" % (E(R.get("v_heb") or R.get("v")), " + ".join(VIEW_HEB[v] for v in views) or "שוק בלבד", " · יום חלקי" if R.get("partial") else "")
    o = ['<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
         "<title>פירוק-יום %s</title><style>%s</style></head><body>" % (E(R["date"]), CSS),
         '<div class="hdr"><a class="ib" href="index.html" title="כל הימים">☰</a><div class="t">%s<div class="sub">%s</div></div>'
         '<a class="ib%s" href="%s" title="יום קודם">‹</a><a class="ib%s" href="%s" title="יום הבא">›</a></div><div class="wrap">' % (
             E(date_heb(R)), sub, "" if prev_d else " dis", (prev_d + ".html") if prev_d else "#", "" if next_d else " dis", (next_d + ".html") if next_d else "#")]
    o.append('<div class="chips"><span class="chip">אמת: <b>%s</b> · <b>%s</b> <span class="dim">(%s)</span></span><span class="chip">ייחוס: %s · %s</span></div>' % (
        ots(tr["opening"]), dth(tr["day_type"]), "מייקל" if tr["day_type_src"] == "michael" or tr["opening_src"] == "michael" else "ייחוס" + (" חלקי" if tr.get("partial") else ""),
        ots(tr["ref_opening"]), dth(tr["ref_day_type"])))
    if tr.get("note"):
        o.append('<div class="card">📝 %s</div>' % E(tr["note"]))
    ff = tr.get("ref_feats") or {}
    o.append('<div class="card"><div class="dim" style="margin-bottom:4px">אתמול (%s) · לילה · היום</div>' % E(pv.get("date") or "—") + kv([
        ("אתמול גבוה", px(pv.get("high"))), ("אתמול נמוך", px(pv.get("low"))), ("אתמול סגירה", px(pv.get("close"))),
        ("VAH", px(pv.get("vah"))), ("POC", px(pv.get("poc"))), ("VAL", px(pv.get("val"))),
        ("לילה גבוה", px(on.get("high"))), ("לילה נמוך", px(on.get("low"))), ("פתיחה", px(rf.get("open"))),
        ("IBH", px(ib.get("ibh"))), ("IBL", px(ib.get("ibl"))), ("רוחב IB", px(ib.get("width"))),
        ("ATR14", px(R.get("atr"))), ("טווח/IB (rib)", px(ff.get("rib"))), ("מיקום-סגירה", px(ff.get("close_pos"))),
    ]) + '<div class="dim" style="margin-top:6px">מיקום-הפתיחה: %s · פתיחה (ייחוס): %s</div></div>' % (
        E(L.OPEN_LOC_HEB.get(rf.get("open_loc"), rf.get("open_loc"))), E(tr.get("ref_opening_why") or "")))
    if len(views) > 1:
        o.append('<div class="vsw">' + "".join('<button data-v="%s" onclick="view(\'%s\')">%s</button>' % (v, v, VIEW_HEB[v]) for v in views) + "</div>")
    for v in views:
        o.append('<div data-view="%s">%s</div>' % (v, view_html(R, v)))
    if not views:
        o.append('<div class="card empty">אין מבט-מערכת (לא לייב ולא ריפליי) — רק השוק והייחוס.</div>')
    o.append('<div class="dim" style="margin:16px 0">נוצר %s ע״י scripts/day_dissect.py · בר-מקור %s · נקודות לחוזה אחד · סימולציה: סטופ-קודם בבר שנוגע בשניהם</div>' % (
        E(R.get("generated")), E(R["bars"].get("db"))))
    o.append("</div><script>%s</script></body></html>" % JS)
    return "".join(o)


def index_html(days, S):
    rows = []
    for R in sorted(days, key=lambda r: r["date"], reverse=True):
        vk = "live" if (R.get("live") and R["live"].get("available")) else ("replay" if R.get("replay") else None)
        V = R.get(vk) if vk else None
        tr = R["truth"]
        if V:
            h, sm = V["hit"], V["summary"]
            sysc = "%s · %s" % (ots(h.get("sys_opening")), dth(h.get("sys_day_type")))
            marks = mark(h.get("opening_ok")) + mark(h.get("day_type_ok"))
            fires = "%d" % sm["n_fired"]
            pnl = sg(sm.get("pts"), 1) + ((" " + sg(sm["usd"], 0, "$")) if sm.get("usd") is not None else "")
        else:
            sysc, marks, fires, pnl = "—", "", "—", "—"
        tag = {"live": "ל", "replay": "ר"}.get(vk, "—") + ("+ר" if (vk == "live" and R.get("replay")) else "")
        rows.append("<tr><td class='num'><a href='%s.html'>%s</a>%s</td><td>%s</td><td>%s · %s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            E(R["date"]), E(R["date"][5:]), " <span class='pill warn'>חלקי</span>" if R.get("partial") else "", E(tag),
            ots(tr["opening"]), dth(tr["day_type"]), sysc, marks, fires, pnl))
    hits = ""
    if S:
        parts = []
        for v, h in (S.get("hit") or {}).items():
            r = h["vs_ref"]
            pc = lambda x: ("%.0f%% (%d/%d)" % (x["rate"], x["ok"], x["n"])) if x.get("n") else "—"
            parts.append("%s: פתיחה %s · סוג-יום %s · זמן-לתווית חציון %s דק׳" % (VIEW_HEB.get(v, v), pc(r["opening"]), pc(r["day_type"]),
                                                                                 ("%.0f" % h["ttc"]["median"]) if h["ttc"].get("median") is not None else "—"))
        hits = '<div class="card dim">%s · %s</div>' % (E(" | ".join(parts)), E("עודכן " + S.get("generated", "")))
    return ('<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
            "<title>פירוק-יום · כל הימים</title><style>%s</style></head><body>" % CSS +
            '<div class="hdr"><a class="ib" href="../index.html" title="בית">🏠</a><div class="t">פירוק-יום · כל הימים<div class="sub">%s · %d ימים · ל = לייב/דמו · ר = ריפליי</div></div></div><div class="wrap">' % (
                E(L.VERSION_HEB), len(days)) + hits +
            '<div class="card scroll"><table class="plain"><tr><th>תאריך</th><th></th><th>אמת (פתיחה · יום)</th><th>מערכת</th><th>✓</th><th>ירי</th><th>נק׳ / $</th></tr>%s</table></div>' % "".join(rows) +
            '<div class="dim">אמת = תווית של מייקל כשקיימת, אחרת הייחוס החוקי. ✓ ראשון = פתיחה, שני = סוג-יום (משפחה).</div></div><script>%s</script></body></html>' % JS)


def main(argv=None):
    ap = argparse.ArgumentParser(description="DAYMAP pages (writes render_mobile_relay/static/docs/daymap/ only)")
    ap.add_argument("--version", default=L.VERSION_DEFAULT)
    ap.add_argument("--dir", default=None)
    ap.add_argument("--out", default=os.path.join(L.REPO, "render_mobile_relay", "static", "docs", "daymap"))
    ap.add_argument("--date", action="append", help="only these days (the index always lists every day file)")
    a = ap.parse_args(argv)
    d = a.dir or os.path.join(L.REPO, "harness_out", "daymap", a.version)
    if not os.path.isabs(d):
        d = os.path.join(L.REPO, d)
    days = []
    for p in sorted(glob.glob(os.path.join(d, "20??-??-??.json"))):
        try:
            with open(p, encoding="utf-8") as fh:
                days.append(json.load(fh))
        except Exception as e:
            print("skip %s: %s" % (p, e))
    S = None
    try:
        with open(os.path.join(d, "SUMMARY.json"), encoding="utf-8") as fh:
            S = json.load(fh)
    except Exception:
        pass
    want = set(x.strip() for s in (a.date or []) for x in s.split(",") if x.strip())
    os.makedirs(a.out, exist_ok=True)
    order = [R["date"] for R in days]
    n = 0
    for i, R in enumerate(days):
        if want and R["date"] not in want:
            continue
        html_ = page_html(R, order[i - 1] if i > 0 else None, order[i + 1] if i + 1 < len(order) else None)
        with open(os.path.join(a.out, "%s.html" % R["date"]), "w", encoding="utf-8") as fh:
            fh.write(html_)
        n += 1
    with open(os.path.join(a.out, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(index_html(days, S))
    print("DAYMAP pages: %d day pages + index → %s" % (n, os.path.relpath(a.out, L.REPO)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
