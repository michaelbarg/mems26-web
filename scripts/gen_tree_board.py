#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_tree_board.py — the Dalton tree drawn as a board that grows (Michael 23.09 09:20: "האם יש לנו עץ?
האם יש לו צורה? האם אפשר שהעץ יהיה פרוס על board … וכל הזמן הוא יגדל").

The tree IS the playbook: root → phase (A 16:30–16:45 · B –17:30 · C –21:00 · D 21:00+) → condition
(opening type in A/B, day type in C/D; first match wins) → leaf = intent (bias · allowed entry kinds ·
stop/target rule). Around the live rows the board shows the growth rings:
  · solid boxes   = live rules (config/dalton_playbook.yaml) with what they DID in the last N sessions:
                    setups seen · blocked by this rule · fired live (+ broker P&L)
  · dashed boxes  = v2-draft rows measured in shadow (config/dalton_tree_v2_draft.yaml, TREE_SHADOW)
  · dotted "buds" = candidates the daily exam produced (data/review_report.json) — a bud that repeats
                    ≥3 days goes to replay; a replay that wins becomes a dashed row; a ruling makes it solid.
Regenerated at EOD after day_review + review_report. Read-only. Output: data/tree_board.json +
data/tree_board.html (SVG fragment wrapped by gen_phone_pages.py into tree_board.html).
"""
import os, sys, re, json, collections, datetime as dt
import yaml
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all
from zoneinfo import ZoneInfo
IL = ZoneInfo("Asia/Jerusalem")
OUT = os.path.join(ROOT, "render_mobile_relay", "static", "docs", "data")
EXPORT = os.path.expanduser("~/SierraChart_Data/v9_export")
N_DAYS = 10

PB = yaml.safe_load(open(os.path.join(ROOT, "config", "dalton_playbook.yaml"), encoding="utf-8"))
V2 = yaml.safe_load(open(os.path.join(ROOT, "config", "dalton_tree_v2_draft.yaml"), encoding="utf-8"))
RR = json.load(open(os.path.join(OUT, "review_report.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "review_report.json")) else {"top_fixes": []}
RV = json.load(open(os.path.join(OUT, "review.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "review.json")) else {"days": {}}
days = sorted(RV.get("days", {}))[-N_DAYS:]
dth = {str(r["date"]): r for r in read_all("select date, day_type, opening_type from v9_day_type_history where date >= :d", {"d": days[0] if days else "2026-09-01"})}

# ── decisions (final outcomes) for the window ─────────────────────────────────
def load_decisions(d):
    paths = [os.path.join(EXPORT, "decisions_archive", f"gateway_decisions.{d}.jsonl"), os.path.join(EXPORT, "gateway_decisions.jsonl")]
    rows = []
    for p in paths:
        if not os.path.exists(p): continue
        for line in open(p, encoding="utf-8"):
            try: r = json.loads(line)
            except Exception: continue
            if r.get("event_type") not in ("GATE_DECISION", "ROUTED") or not r.get("ts"): continue
            try: ts = dt.datetime.fromisoformat(r["ts"].replace("Z", "+00:00"))
            except Exception: continue
            if ts.astimezone(IL).date().isoformat() != d: continue
            r["_ts"] = ts; r["_day"] = d; rows.append(r)
        if rows: break
    sv = read_all("""select ts, classification, direction, phase, vector from v9_decision_vectors where kind='DECISION' and ts >= :a and ts < :b""",
                  {"a": dt.datetime.combine(dt.date.fromisoformat(d), dt.time(0, 0), IL), "b": dt.datetime.combine(dt.date.fromisoformat(d) + dt.timedelta(days=1), dt.time(0, 0), IL)})
    for r in rows:
        m = [s for s in sv if s["classification"] == r["pattern"] and s["direction"] == r["direction"] and abs((s["ts"] - r["_ts"]).total_seconds()) <= 3]
        r["_day_type"] = ((m[0]["vector"] or {}).get("day_type") if m else None) or (dth.get(d, {}).get("day_type") or "")
        r["_phase"] = (m[0]["phase"] if m else None) or phase_of(r["_ts"].astimezone(IL))
        r["_opening"] = dth.get(d, {}).get("opening_type") or "UNKNOWN"
    return rows

def phase_of(il):
    hm = il.hour * 60 + il.minute
    return "A" if hm < 16 * 60 + 45 else "B" if hm < 17 * 60 + 30 else "C" if hm < 21 * 60 else "D"

decisions = [r for d in days for r in load_decisions(d)]
trades = read_all("""select id, direction, entry_ts, pnl_usd, pnl_sierra, day_type_at_entry dt, pattern_id_at_entry pat, exit_reason
  from v9_trades where mode='live' and state='CLOSED' and entry_ts >= :s order by entry_ts""",
  {"s": dt.datetime.combine(dt.date.fromisoformat(days[0]), dt.time(0, 0), IL)}) if days else []

# ── rule matching (same semantics as the playbook: first match wins within the phase) ──
def cond_match(cond, opening, day_type):
    if cond == "default": return True
    m = re.match(r"(\w+) == (\w+)", cond)
    if m: return (opening if m.group(1) == "opening_type" else day_type) == m.group(2)
    m = re.match(r"(\w+) in \[(.+)\]", cond)
    if m:
        vals = [v.strip() for v in m.group(2).split(",")]
        return (opening if m.group(1) == "opening_type" else day_type) in vals
    return False

def row_for(phase, opening, day_type):
    for k, rule in enumerate(PB["phases"][phase]["rules"]):
        if cond_match(rule["condition"], opening, day_type): return k
    return None

stats = collections.defaultdict(lambda: dict(seen=0, blocked_here=0, blocked_other=0, shadow_only=0, live=0, live_pnl=0.0, live_n=0, live_w=0, pats=collections.Counter()))
for r in decisions:
    ph = r["_phase"]
    if ph not in PB["phases"]: continue
    k = None
    reason = r.get("reason") or ""
    m = re.search(r"phase=(\w) cond=(.+?) bias=", reason)
    if m and m.group(1) == ph:
        for kk, rule in enumerate(PB["phases"][ph]["rules"]):
            if rule["condition"] == m.group(2).strip(): k = kk; break
    if k is None: k = row_for(ph, r["_opening"], r["_day_type"])
    if k is None: continue
    s = stats[(ph, k)]; s["seen"] += 1; s["pats"][r.get("pattern") or "?"] += 1
    if r.get("outcome") == "blocked":
        if (r.get("blocked_by") or "").startswith("dalton_intent"): s["blocked_here"] += 1
        else: s["blocked_other"] += 1
    elif r.get("outcome") == "live": s["live"] += 1
    else: s["shadow_only"] += 1
for t in trades:
    il = t["entry_ts"].astimezone(IL); d = il.date().isoformat(); ph = phase_of(il)
    k = row_for(ph, dth.get(d, {}).get("opening_type") or "UNKNOWN", t["dt"] or dth.get(d, {}).get("day_type") or "")
    if k is None: continue
    s = stats[(ph, k)]; p = float(t["pnl_sierra"]) if t["pnl_sierra"] is not None else float(t["pnl_usd"] or 0)
    s["live_n"] += 1; s["live_pnl"] += p; s["live_w"] += 1 if p > 0 else 0

# ── nodes ─────────────────────────────────────────────────────────────────────
PH_HEB = {"A": "שלב A · 16:30–16:45", "B": "שלב B · 16:45–17:30", "C": "שלב C · 17:30–21:00", "D": "שלב D · 21:00+"}
BIAS_HEB = {"NONE": "אין כוונה (stand-down)", "BOTH": "שני הכיוונים", "drive_direction": "עם הדרייב", "reversal_direction": "עם ההיפוך", "trend_direction": "עם המגמה",
            "extension_direction": "עם ההרחבה", "extension_direction_once_then_BOTH": "עם ההרחבה הראשונה, אח״כ שניהם"}
KIND_HEB = {"WITH_DRIVE": "עם-הדרייב", "PULLBACK": "פולבק", "REVERSAL": "היפוך", "EDGE_FADE": "דחיית-קצה", "BREAK": "פריצה", "VALUE_RETURN": "חזרה-לערך"}
def cond_heb(c):
    if c == "default": return "כל השאר"
    c = c.replace("opening_type == ", "פתיחה = ").replace("opening_type in ", "פתיחה ∈ ").replace("day_type == ", "יום = ").replace("day_type in ", "יום ∈ ")
    return c.replace("[", "").replace("]", "")
nodes = []
for ph in "ABCD":
    for k, rule in enumerate(PB["phases"][ph]["rules"]):
        s = stats.get((ph, k)) or dict(seen=0, blocked_here=0, blocked_other=0, shadow_only=0, live=0, live_pnl=0.0, live_n=0, live_w=0, pats=collections.Counter())
        kinds = ", ".join(KIND_HEB.get(x, x) for x in rule.get("entry_kinds") or []) or "—"
        nodes.append(dict(kind="live", phase=ph, idx=k, cond=rule["condition"], cond_heb=cond_heb(rule["condition"]), bias=BIAS_HEB.get(rule["bias"], rule["bias"]),
                          kinds=kinds, stop=rule.get("stop_rule"), target=rule.get("target_rule"), seen=s["seen"], blocked_here=s["blocked_here"], blocked_other=s["blocked_other"],
                          shadow_only=s["shadow_only"], live=s["live"], live_n=s["live_n"], live_pnl=round(s["live_pnl"], 2), live_w=s["live_w"], pats=dict(s["pats"].most_common(4))))
for r in V2.get("rules", []):
    phs = r.get("phase") or ["A", "B", "C", "D"]
    nodes.append(dict(kind="shadow", phase=phs[0] if len(phs) == 1 else "C" if "C" in phs else phs[0], phases=phs, id=r["id"], decision=r.get("decision"), source=r.get("source"),
                      measured=str(r.get("measured", "UNMEASURED")), note=(r.get("note") or "").strip()[:140], cond=r.get("condition", "")))
KD = {"relax_gate": "שער לבדיקה", "slot_priority": "עדיפות-סלוט", "producer_not_live": "מפיק צל-בלבד", "shadow_only": "צל בלי שער", "no_producer": "אף מפיק לא רואה"}
for c in RR.get("top_fixes", []):
    nodes.append(dict(kind="bud", phase=c["phase"] if c["phase"] in "ABCD" else "C", label=KD.get(c["kind"], c["kind"]), kind_orig=c["kind"],
                      **{k: v for k, v in c.items() if k not in ("phase", "kind")}))

# ── SVG (top-down, RTL text; columns per phase) ───────────────────────────────
W = 1300; COL = W / 4; BOXW = 300; BH_LIVE = 76; BH_SH = 58; BH_BUD = 50; GAP = 10
def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
svg = []; y_max = 0; details = []
root_y = 26
svg.append(f'<rect x="{W/2-120:.0f}" y="{root_y-18}" width="240" height="36" rx="10" fill="#1f6feb"/>'
           f'<text x="{W/2:.0f}" y="{root_y+6}" text-anchor="middle" fill="#fff" font-size="15" font-weight="700">עץ-דלתון v1.2 · {len(days)} סשנים · {len(decisions)} סטאפים</text>')
for i, ph in enumerate("ABCD"):
    cx = W - (i + 0.5) * COL  # RTL: A on the right
    py = 96
    svg.append(f'<line x1="{W/2:.0f}" y1="{root_y+18}" x2="{cx:.0f}" y2="{py-18}" stroke="#30363d" stroke-width="2"/>')
    ph_nodes = [n for n in nodes if n["phase"] == ph]
    seen = sum(n.get("seen", 0) for n in ph_nodes if n["kind"] == "live"); blocked = sum(n.get("blocked_here", 0) for n in ph_nodes if n["kind"] == "live")
    live = sum(n.get("live_n", 0) for n in ph_nodes if n["kind"] == "live"); pnl = sum(n.get("live_pnl", 0) for n in ph_nodes if n["kind"] == "live")
    svg.append(f'<rect x="{cx-BOXW/2:.0f}" y="{py-18}" width="{BOXW}" height="40" rx="9" fill="#161b22" stroke="#58a6ff" stroke-width="2"/>'
               f'<text x="{cx:.0f}" y="{py-1}" text-anchor="middle" fill="#e6edf3" font-size="14" font-weight="700">{esc(PH_HEB[ph])}</text>'
               f'<text x="{cx:.0f}" y="{py+15}" text-anchor="middle" fill="#8b949e" font-size="11">ראה {seen} · חסם {blocked} · לייב {live} ({pnl:+.0f}$)</text>')
    y = py + 36
    for n in ph_nodes:
        h = BH_LIVE if n["kind"] == "live" else BH_SH if n["kind"] == "shadow" else BH_BUD
        svg.append(f'<line x1="{cx:.0f}" y1="{y-GAP}" x2="{cx:.0f}" y2="{y}" stroke="#30363d" stroke-width="2"/>')
        x0 = cx - BOXW / 2
        if n["kind"] == "live":
            hot = n["blocked_here"] >= 20
            stroke = "#3fb950" if n["live_n"] and n["live_pnl"] > 0 else "#f85149" if n["live_n"] and n["live_pnl"] < 0 else "#8b949e" if n["seen"] else "#30363d"
            svg.append(f'<rect x="{x0:.0f}" y="{y}" width="{BOXW}" height="{h}" rx="8" fill="#0d1117" stroke="{stroke}" stroke-width="2"/>'
                       f'<text x="{cx+BOXW/2-8:.0f}" y="{y+17}" text-anchor="start" fill="#e6edf3" font-size="12" font-weight="700">{esc(n["cond_heb"])}</text>'
                       f'<text x="{cx+BOXW/2-8:.0f}" y="{y+33}" text-anchor="start" fill="#c9d1d9" font-size="11">{esc(n["bias"])} → {esc(n["kinds"])}</text>'
                       f'<text x="{cx+BOXW/2-8:.0f}" y="{y+49}" text-anchor="start" fill="#8b949e" font-size="11">ראה {n["seen"]} · חסם כאן {n["blocked_here"]} · צל {n["shadow_only"]} · לייב {n["live"]}</text>'
                       f'<text x="{cx+BOXW/2-8:.0f}" y="{y+65}" text-anchor="start" fill="{"#3fb950" if n["live_pnl"]>0 else "#f85149" if n["live_pnl"]<0 else "#8b949e"}" font-size="11">עסקאות-לייב {n["live_n"]} · {n["live_w"]} ✓ · {n["live_pnl"]:+.2f}$</text>')
            if hot: svg.append(f'<circle cx="{x0+12:.0f}" cy="{y+12}" r="6" fill="#f85149"/><title>השער הזה חסם {n["blocked_here"]} סטאפים</title>')
            details.append(dict(phase=ph, kind="live", title=f'{PH_HEB[ph]} · {n["cond_heb"]}', body=f'כוונה: {n["bias"]} → {n["kinds"]} · סטופ {n["stop"] or "—"} · יעד {n["target"] or "—"} · ראה {n["seen"]} סטאפים (חסם כאן {n["blocked_here"]}, חסמו שערים אחרים {n["blocked_other"]}, צל-בלבד {n["shadow_only"]}, לייב {n["live"]}) · עסקאות-לייב {n["live_n"]} ({n["live_w"]} ✓, {n["live_pnl"]:+.2f}$) · תבניות: ' + ", ".join(f"{k} {v}" for k, v in n["pats"].items())))
        elif n["kind"] == "shadow":
            svg.append(f'<rect x="{x0:.0f}" y="{y}" width="{BOXW}" height="{h}" rx="8" fill="#0d1117" stroke="#79c0ff" stroke-width="1.5" stroke-dasharray="6,4"/>'
                       f'<text x="{cx+BOXW/2-8:.0f}" y="{y+17}" text-anchor="start" fill="#79c0ff" font-size="12" font-weight="700">צל v2 · {esc(n["id"])}</text>'
                       f'<text x="{cx+BOXW/2-8:.0f}" y="{y+33}" text-anchor="start" fill="#c9d1d9" font-size="11">{esc(n["decision"])} · {esc(n["source"])} · {esc(n["measured"][:22])}</text>'
                       f'<text x="{cx+BOXW/2-8:.0f}" y="{y+49}" text-anchor="start" fill="#8b949e" font-size="10">{esc(n["note"][:52])}</text>')
            details.append(dict(phase=ph, kind="shadow", title=f'צל v2 · {n["id"]} ({", ".join(n["phases"])})', body=f'{n["decision"]} · {n["source"]} · measured: {n["measured"]} · {n["note"]} · תנאי: {n["cond"]}'))
        else:
            zone = {"ABOVE_VA": "מעל הבטן", "BELOW_VA": "מתחת לבטן", "IN_VA": "בתוך הבטן", "AT_POC": "POC"}.get(n.get("zone"), n.get("zone"))
            svg.append(f'<rect x="{x0:.0f}" y="{y}" width="{BOXW}" height="{h}" rx="8" fill="#0d1117" stroke="#d29922" stroke-width="1.5" stroke-dasharray="2,3"/>'
                       f'<text x="{cx+BOXW/2-8:.0f}" y="{y+17}" text-anchor="start" fill="#d29922" font-size="12" font-weight="700">🌱 {esc(n.get("label",""))} · {n["days"]} ימים · {n["pts"]:.0f} נק׳</text>'
                       f'<text x="{cx+BOXW/2-8:.0f}" y="{y+33}" text-anchor="start" fill="#c9d1d9" font-size="11">{esc(n["day_type"])} · {esc(zone)} · {"לונג" if n["dir"]=="LONG" else "שורט"}' + (f' · {esc(n["gate"].split(":")[-1])}' if n.get("gate") else "") + '</text>'
                       f'<text x="{cx+BOXW/2-8:.0f}" y="{y+45}" text-anchor="start" fill="#8b949e" font-size="10">{esc(", ".join(n.get("pats", [])[:3]))}</text>')
            details.append(dict(phase=ph, kind="bud", title=f'🌱 ניצן · {n.get("label","")} · שלב {ph} · {n["day_type"]} · {zone} · {"לונג" if n["dir"]=="LONG" else "שורט"}', body=f'{n["days"]} ימים ({n["n"]} מהלכים) · {n["pts"]:.0f} נק׳' + (f' · שער: {n["gate"]}' if n.get("gate") else "") + (f' · מפיקים: {", ".join(n["pats"])}' if n.get("pats") else "") + (" · ⇒ מוכן לריפליי" if n["days"] >= 3 else f" · עוד {3-n['days']} ימים לריפליי")))
        y += h + GAP
    y_max = max(y_max, y)
H = y_max + 20
frag = (f'<div class="board" style="overflow-x:auto;-webkit-overflow-scrolling:touch"><svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" direction="rtl" style="font-family:-apple-system,Helvetica,Arial,sans-serif">'
        + "".join(svg) + '</svg></div>')
json.dump(dict(generated=dt.datetime.now(IL).isoformat(timespec="minutes"), days=days, n_decisions=len(decisions), nodes=nodes, details=details,
               counts=dict(live=sum(1 for n in nodes if n["kind"] == "live"), shadow=sum(1 for n in nodes if n["kind"] == "shadow"), bud=sum(1 for n in nodes if n["kind"] == "bud"))),
          open(os.path.join(OUT, "tree_board.json"), "w"), ensure_ascii=False, indent=0, default=str)
open(os.path.join(OUT, "tree_board.html"), "w", encoding="utf-8").write(frag)
print(f"tree board: {sum(1 for n in nodes if n['kind']=='live')} live rows · {sum(1 for n in nodes if n['kind']=='shadow')} shadow rows · {sum(1 for n in nodes if n['kind']=='bud')} buds · {len(decisions)} decisions over {len(days)} days → data/tree_board.html ({W}x{H})")
