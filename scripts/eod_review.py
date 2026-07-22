#!/usr/bin/env python3
"""EOD review for ONE trading day (Michael 2026-07-22): today's trades, how
fills came in FROM SIERRA (reconciliation), gate blocks, opening-trigger shadow
results, account/orphan state, flags — plus data-driven flags for the analyst.

RUN ON THE MAC (Desktop Commander), never the sandbox — it reads local Postgres,
the Sierra exports, and the live API. Writes docs/reports/EOD_REVIEW_<date>.md
and prints a summary. The scheduled EOD task runs this, then adds judgment-based
recommendations.

Ground-truth sources (per docs/SOURCE_OF_TRUTH.md + Task#6 findings):
  • v9_trades              — recorded trades; pnl_usd is CALCULATED (entry-exit×qty)
  • trade_activity_events.jsonl — SIERRA ACTUAL: POSITION_CHANGE + CLOSED_TRADE_PNL
                              (the real realized P&L per closed trade, account-tagged)
  • trade_fills.json        — the /live_ledger source; KNOWN EMPTY (Task#6)
  • sierra_state.json       — current net position / working orders
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

REPO = os.path.expanduser("~/Downloads/mems26_web_git")
EXP = os.path.expanduser("~/SierraChart_Data/v9_export")
ACCOUNT = "37138283"
_PSQL = next((p for p in (
    "/Applications/Postgres.app/Contents/Versions/18/bin/psql",
    "/opt/homebrew/bin/psql", "/usr/local/bin/psql", "psql") if os.path.exists(p) or p == "psql"), "psql")
DB = "postgresql://localhost/mems26"


def q(sql: str) -> list:
    try:
        out = subprocess.run([_PSQL, DB, "-tA", "-F", "\t", "-c", sql],
                             capture_output=True, text=True, timeout=20)
        return [line.split("\t") for line in out.stdout.strip().splitlines() if line]
    except Exception as e:
        return [["ERR", str(e)[:80]]]


def et_today() -> str:
    return datetime.now(ZoneInfo("America/New_York")).date().isoformat()


def load_activity(day: str) -> dict:
    """Parse the Sierra activity journal for today: real fills + realized P&L."""
    path = f"{EXP}/trade_activity_events.jsonl"
    pos_changes, closed_pnls, other = [], [], 0
    if not os.path.exists(path):
        return {"missing": True}
    for line in open(path, encoding="utf-8", errors="ignore"):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        ts = str(e.get("ts", ""))
        # ts date in ET
        try:
            d = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(
                ZoneInfo("America/New_York")).date().isoformat()
        except Exception:
            d = ts[:10]
        if d != day:
            continue
        if str(e.get("account", ACCOUNT)) != ACCOUNT and e.get("account"):
            continue
        t = e.get("type")
        if t == "POSITION_CHANGE":
            pos_changes.append(e)
        elif t == "CLOSED_TRADE_PNL":
            closed_pnls.append(e)
        else:
            other += 1
    return {"pos_changes": pos_changes, "closed_pnls": closed_pnls, "other": other,
            "sierra_realized": round(sum(float(c.get("pnl", 0)) for c in closed_pnls), 2)}


def sierra_state() -> dict:
    try:
        return json.loads(open(f"{EXP}/sierra_state.json").read() or "{}")
    except Exception:
        return {}


def api(path: str):
    try:
        import urllib.request
        with urllib.request.urlopen(f"http://localhost:8000{path}", timeout=6) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def main():
    day = sys.argv[1] if len(sys.argv) > 1 else et_today()
    L = []
    L.append(f"# ביקורת-יום MEMS26 — {day}")
    L.append(f"*נוצר {datetime.now(ZoneInfo('Asia/Jerusalem')).strftime('%Y-%m-%d %H:%M IL')} · scripts/eod_review.py*\n")

    # ── 1. Trades today ──
    L.append("## 1. עסקאות היום (v9_trades)")
    rows = q(f"""select id, to_char(entry_ts,'HH24:MI'), coalesce(firing_system::text,'?'),
        coalesce(pattern_id_at_entry,'?'), coalesce(direction,'?'), coalesce(mode,'?'),
        coalesce(state,'?'), coalesce(entry_price::text,'-'), coalesce(exit_price::text,'-'),
        coalesce(exit_reason,'-'), coalesce(round(pnl_usd::numeric,2)::text,'-'),
        coalesce(day_type_at_entry,'-')
        from v9_trades where entry_ts::date=date '{day}' order by entry_ts;""")
    if rows and rows[0][0] != "ERR":
        L.append("| id | t | sys | תבנית | כיוון | mode | state | כניסה | יציאה | סיבה | P&L(מחושב) | סוג-יום |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for r in rows:
            L.append("| " + " | ".join(r) + " |")
        live = [r for r in rows if r[5] == "live"]
        calc_live = sum(float(r[10]) for r in live if r[10] not in ("-", "None"))
        L.append(f"\n**לייב: {len(live)} עסקאות · P&L-מחושב סה\"כ: {calc_live:+.2f}$** · "
                 f"shadow: {sum(1 for r in rows if r[5]=='shadow')} · demo: {sum(1 for r in rows if r[5]=='demo')}")
    else:
        L.append("_אין עסקאות רשומות היום._")
        calc_live = 0.0

    # ── 2. Sierra reconciliation (how fills came in) ──
    L.append("\n## 2. ⭐ רקונסיליאציה מול Sierra — איך הדברים התקבלו בפועל")
    act = load_activity(day)
    st = sierra_state()
    fills_json_size = os.path.getsize(f"{EXP}/trade_fills.json") if os.path.exists(f"{EXP}/trade_fills.json") else -1
    if act.get("missing"):
        L.append("🔴 `trade_activity_events.jsonl` חסר — אין אמת-Sierra לרקונסיליאציה.")
        sierra_realized = None
    else:
        sierra_realized = act["sierra_realized"]
        L.append(f"- **P&L אמיתי מ-Sierra** (סכום `CLOSED_TRADE_PNL`): **{sierra_realized:+.2f}$** "
                 f"({len(act['closed_pnls'])} עסקאות-סגורות · {len(act['pos_changes'])} שינויי-פוזיציה).")
        L.append(f"- **P&L מחושב ברשומות** (v9_trades live): **{calc_live:+.2f}$**.")
        diff = round((sierra_realized or 0) - calc_live, 2)
        flag = "🟢 תואם" if abs(diff) < 1.0 else f"🔴 **פער {diff:+.2f}$** — P&L המחושב ≠ Sierra"
        L.append(f"- **הפרש רשומות↔Sierra: {flag}**")
        # per closed trade
        if act["closed_pnls"]:
            L.append("\n  סגירות-Sierra היום:")
            for c in act["closed_pnls"]:
                _t = str(c.get("ts", ""))[11:16]
                L.append(f"  - {_t} · {c.get('symbol','?')} · **{float(c.get('pnl',0)):+.2f}$**")
    # the Task#6 gap
    L.append(f"\n- `trade_fills.json` (מקור /live_ledger): **{fills_json_size}B** "
             f"{'🔴 ריק — הפער של Task#6 עדיין פתוח' if fills_json_size==0 else '🟢 מאוכלס' if fills_json_size>0 else 'חסר'}.")
    L.append(f"- מצב-חשבון-סגירה (`sierra_state.json`): qty={st.get('position_qty','?')} · "
             f"working={st.get('working_orders','?')} · is_sim={st.get('is_sim','?')}.")
    if st.get("position_qty") not in (0, "0", None):
        L.append(f"  🔴 **החשבון לא שטוח בסגירה** (qty={st.get('position_qty')}) — לוודא ידני/אורפן.")

    # ── 3. Gate decisions ──
    L.append("\n## 3. שערים — מה נחסם והאם מוצדק")
    dec = api("/api/v9/gateway/decisions?limit=100")
    if dec and isinstance(dec, dict):
        today = dec.get("today", {})
        L.append(f"- ניסיונות: {today.get('fired','?')} ירו · {today.get('blocked','?')} נחסמו · "
                 f"{today.get('shadow_only','?')} shadow.")
        by = today.get("by_gate", {})
        if by:
            L.append("- פירוק-חסימות: " + " · ".join(f"`{k}`×{v}" for k, v in by.items()))
        L.append("\n  (הביקורת בסוף חייבת לסמן לכל שער: מוצדק דוקטרינרית או מחסום-שווא)")
    else:
        L.append("_endpoint decisions לא זמין._")

    # ── 4. Opening triggers (shadow) ──
    L.append("\n## 4. טריגרי-פתיחה (צל) — הכלל של מייקל + דלתון")
    op = api("/api/v9/day_type/opening_panel")
    if op and op.get("opening_triggers"):
        ot = op["opening_triggers"]
        L.append(f"- מצב: {ot.get('mode')} · חלון: בר {ot.get('window_bars_seen')}/6 · "
                 f"ירו: {', '.join(ot.get('fired',[])) or 'אף אחד'}.")
        L.append(f"- סוג-פתיחה: {(op.get('opening') or {}).get('type','—')} · "
                 f"עמדה: {(op.get('opening') or {}).get('stance','—')}.")
        for d in ot.get("decisions", []):
            L.append(f"  - {str(d.get('ts',''))[11:16]} {d.get('pattern')} {d.get('direction','')} "
                     f"@{d.get('entry','?')} → {d.get('blocked_by') or d.get('outcome') or 'shadow'}")
        L.append("\n  (בסוף: להשוות ירי-הצל מול תנועת-המחיר בפועל — האם הכלל צדק?)")
    else:
        L.append("_אין נתוני טריגרי-פתיחה._")

    # ── 5. Flags / health ──
    L.append("\n## 5. דגלים ובריאות")
    try:
        fg = subprocess.run([sys.executable, "scripts/flag_guard.py"], cwd=REPO,
                            capture_output=True, text=True, timeout=30)
        last = fg.stdout.strip().splitlines()[-1] if fg.stdout.strip() else "?"
        L.append(f"- flag_guard: `{last}`")
    except Exception as e:
        L.append(f"- flag_guard: שגיאה {str(e)[:50]}")
    feed = q("select round(extract(epoch from (now()-max(ts)))/60) from v9_bars_5min_woodies;")
    if feed and feed[0][0] not in ("ERR", ""):
        L.append(f"- טריות-פיד (woodies): {feed[0][0]} דק' (בסגירה — צפוי שיעלה).")

    # ── 6. Recommendations placeholder (analyst fills at EOD) ──
    L.append("\n## 6. ממצאים והמלצות-תיקון (האנליסט ממלא בסוף-היום)")
    L.append("_לכל ממצא: שורש → תיקון מוצע → דגל/פסיקה נדרשת. סעיפים לבדיקה:_")
    L.append("- [ ] כל חסימת-שער — מוצדקת או מחסום-שווא?")
    L.append("- [ ] סטופים בפועל — על קצה-המבנה (C+D)? השווה stop רשום מול הבר.")
    L.append("- [ ] רקונסיליאציה — האם ה-P&L המחושב סטה מ-Sierra? (Task#6)")
    L.append("- [ ] טריגרי-הפתיחה בצל — צדקו מול המחיר? (ראיה לפסיקת-קידום)")
    L.append("- [ ] אורפנים / חשבון-לא-שטוח.")
    L.append("- [ ] תיקוני-הבוקר (T1-מבני · סטופ-מבנה · קצוות-REV · LSMA-flat) — פעלו כמצופה בלייב?")

    report = "\n".join(L)
    outdir = os.path.join(REPO, "docs", "reports")
    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, f"EOD_REVIEW_{day}.md")
    open(outpath, "w", encoding="utf-8").write(report + "\n")
    print(report)
    print(f"\n[eod_review] wrote {outpath}")
    if sierra_realized is not None and abs((sierra_realized or 0) - calc_live) >= 1.0:
        print(f"[eod_review] ⚠ RECON DIVERGENCE: sierra={sierra_realized} recorded={calc_live}")


if __name__ == "__main__":
    main()
