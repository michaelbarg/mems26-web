#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eod_journal.py — the end-of-day exam + the living trading journal (Michael 19.10.2026, items 1 and 5:
"בסוף כל יום תרוץ בדיקה לאיך היו הביצועים ולהכין המלצות לתיקונים … יומן מסחר מתעדכן שיכלול את התיקונים המומלצים ויציף אותם").

Read-only on the databases. Writes three files only:
  docs/journal/TRADING_JOURNAL.md                 — one entry per session, newest first
  docs/journal/FIX_LEDGER.md                      — the living list of recommended fixes (upsert by key; status column is
                                                    edited by hand: proposed → measuring → ruled → live → closed)
  render_mobile_relay/static/docs/journal.html    — the phone page (last entries + the open fixes)
and prints a last line `PHONE: …` (≤ 500 chars) — the ONE daily trades summary the scheduled agent sends (Michael 20.10:
"תוסיף לאפליקציה של אייפון סיכום יומי של העסקאות"; AGENT_BRIEF §6's single day-summary slot, so the 14.09 phone rule
still holds: no other periodic message). The measurement detail stays in the journal page (journal.html), not the phone.

Per session it records: live trades at BROKER price (pnl_sierra; books only when the broker price is missing, flagged),
Σ of the session / last 10 sessions / since 07.07; the opening — what S1 locked (backend log + decision vectors) vs the
bar reference (first 30 min + prior profile; the super-agent's reading of Dalton pp. 63–74); the day type — the system's
label at 17:30/18:30/21:00/last vs the EOD bar reference (IB / range extension with acceptance / close position, pp.
19–29); decisions and tree blocks; health (backend pid, feed age, gap_backfill, battery); and rule-based recommendations.

usage: python3 scripts/eod_journal.py [--day=YYYY-MM-DD] [--quiet] [--dry]
"""
import sys, os, re, json, html, subprocess, collections, datetime as dt
from zoneinfo import ZoneInfo

REPO = "/Users/michael/Downloads/mems26_web_git"
PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
LOG = "/tmp/backend.err.log"
ET, IL = ZoneInfo("America/New_York"), ZoneInfo("Asia/Jerusalem")
TICK = 0.25
opt = {a.split("=")[0][2:]: (a.split("=", 1)[1] if "=" in a else "1") for a in sys.argv[1:] if a.startswith("--")}
QUIET, DRY = "quiet" in opt, "dry" in opt
J_MD, J_LEDGER, J_HTML = f"{REPO}/docs/journal/TRADING_JOURNAL.md", f"{REPO}/docs/journal/FIX_LEDGER.md", f"{REPO}/render_mobile_relay/static/docs/journal.html"


def say(*a):
    if not QUIET:
        print(*a, flush=True)


def q(sql, db="mems26"):
    r = subprocess.run([PSQL, "-d", db, "-Atc", sql], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:300])
    return [l.split("|") for l in r.stdout.strip().splitlines() if l != ""]


def f(x, nd=2):
    try:
        return ("%+.*f" % (nd, float(x))) if x not in (None, "") else "—"
    except Exception:
        return "—"


# ── session pick ─────────────────────────────────────────────────────────────────────────────────
def pick_day():
    if "day" in opt:
        return dt.date.fromisoformat(opt["day"])
    now = dt.datetime.now(IL)
    rows = q("select (ts at time zone 'America/New_York')::date from v9_bars_5min_woodies where symbol='MES' and "
             "(ts at time zone 'America/New_York')::time between '09:30' and '15:55' group by 1 having count(*)>=60 order by 1 desc limit 1")
    last = dt.date.fromisoformat(rows[0][0]) if rows else now.date()
    return last


DAY = pick_day()
D = DAY.isoformat()


# ── bars + references (copied from harness_out/t586/hist/opening_type_30d.py / doctrine_audit.py — the super-agent's
#    rule-based reading of Dalton; thresholds are not Michael's) ──────────────────────────────────────────────────────
def rth_bars(d):
    rows = q(f"select to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), open, high, low, close, volume from v9_bars_5min_woodies where symbol='MES' "
             f"and (ts at time zone 'America/New_York')::date='{d}' and (ts at time zone 'America/New_York')::time between '09:30' and '15:55' order by ts")
    return [(r[0], *map(float, r[1:6])) for r in rows]


def prev_session_profile(d):
    rows = q(f"select (ts at time zone 'America/New_York')::date from v9_bars_5min_woodies where symbol='MES' and (ts at time zone 'America/New_York')::date < '{d}' "
             f"and (ts at time zone 'America/New_York')::time between '09:30' and '15:55' group by 1 having count(*)>=30 order by 1 desc limit 1")
    if not rows:
        return None
    pd_ = rows[0][0]; bars = rth_bars(pd_)
    prof = collections.defaultdict(set)
    for i, b in enumerate(bars):
        letter = i // 6; p = b[3]
        while p <= b[2] + 1e-9:
            prof[round(p / TICK) * TICK].add(letter); p += TICK
    counts = {p: len(v) for p, v in prof.items()}; total = sum(counts.values())
    poc = max(counts, key=lambda p: (counts[p], -abs(p - (max(counts) + min(counts)) / 2)))
    lo = hi = poc; acc = counts[poc]
    while acc < 0.7 * total:
        up, dn = counts.get(round((hi + TICK) / TICK) * TICK, 0), counts.get(round((lo - TICK) / TICK) * TICK, 0)
        if up >= dn and up > 0: hi = round((hi + TICK) / TICK) * TICK; acc += up
        elif dn > 0: lo = round((lo - TICK) / TICK) * TICK; acc += dn
        else: break
    return dict(date=pd_, poc=poc, vah=hi, val=lo, high=max(b[2] for b in bars), low=min(b[3] for b in bars), close=bars[-1][4])


def ref_opening(bars, prev):
    if len(bars) < 6: return "UNKNOWN", "פחות מ-6 ברים"
    o = bars[0][1]
    highs = [b[2] for b in bars[:6]]; lows = [b[3] for b in bars[:6]]; closes = [b[4] for b in bars[:6]]
    up_drive = all(c > o for c in closes[1:]) and min(lows[1:]) >= o - 2 * TICK
    dn_drive = all(c < o for c in closes[1:]) and max(highs[1:]) <= o + 2 * TICK
    if up_drive or dn_drive: return "OPEN_DRIVE", "אין חזרה לפתיחה בברים 2–6 (%s)" % ("↑" if up_drive else "↓")
    refs = [prev["high"], prev["low"], prev["vah"], prev["val"]] if prev else []
    probe_up = max(highs[:2]) > max([r for r in refs if r > o], default=1e9) if refs else False
    probe_dn = min(lows[:2]) < min([r for r in refs if r < o], default=-1e9) if refs else False
    if probe_up and all(c < o for c in closes[3:]): return "OPEN_TEST_DRIVE", "בדיקה מעל רפרנס, דרייב למטה"
    if probe_dn and all(c > o for c in closes[3:]): return "OPEN_TEST_DRIVE", "בדיקה מתחת לרפרנס, דרייב למעלה"
    if (max(highs[:3]) - o >= 4 and min(lows[3:]) < o) or (o - min(lows[:3]) >= 4 and max(highs[3:]) > o): return "OPEN_REJECTION_REVERSE", "דרייב ואז חזרה דרך הפתיחה"
    if prev and prev["low"] <= o <= prev["high"]: return "OPEN_AUCTION_IN", "סיבוב סביב הפתיחה בתוך הטווח הקודם"
    return "OPEN_AUCTION_OUT", "סיבוב סביב הפתיחה מחוץ לטווח הקודם" if prev else "אין רפרנס קודם"


def ref_daytype(bars):
    """Dalton pp.19-29 at EOD: IB = first 60 min; range extension with acceptance = >= 2 consecutive closes beyond the edge."""
    if len(bars) < 24: return "UNKNOWN", {}
    ibh, ibl = max(b[2] for b in bars[:12]), min(b[3] for b in bars[:12])
    hi, lo, close = max(b[2] for b in bars), min(b[3] for b in bars), bars[-1][4]
    closes = [b[4] for b in bars[12:]]
    up = any(closes[i] > ibh and closes[i + 1] > ibh for i in range(len(closes) - 1))
    dn = any(closes[i] < ibl and closes[i + 1] < ibl for i in range(len(closes) - 1))
    sides = int(up) + int(dn); rib = (hi - lo) / max(ibh - ibl, TICK); close_pos = (close - lo) / max(hi - lo, TICK)
    feats = dict(ibh=ibh, ibl=ibl, hi=hi, lo=lo, close=close, rib=round(rib, 2), close_pos=round(close_pos, 2), ext_up=up, ext_dn=dn)
    if sides == 0: return ("Nontrend" if rib <= 1.15 else "Normal"), feats
    if sides == 2: return ("Neutral_Extreme" if (close_pos >= 0.85 or close_pos <= 0.15) else "Neutral_Center"), feats
    if rib >= 2.0 and (close_pos >= 0.85 or close_pos <= 0.15): return "Trend_Normal", feats
    return "Normal_Variation", feats


# ── what the system saw ──────────────────────────────────────────────────────────────────────────
def system_opening():
    lock, negs = None, 0
    try:
        with open(LOG, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.startswith(D):
                    continue
                if "T-314: locked opening=" in line and lock is None:
                    m = re.search(r"(\d\d:\d\d):\d\d .*locked opening=(\S+) dir=(\S+) (at .*?)(?:\s*$|\()", line)
                    if m: lock = dict(t=m.group(1), type=m.group(2), dir=m.group(3), how=m.group(4).strip())
                elif "T-314: NEGATED" in line:
                    negs += 1
    except FileNotFoundError:
        pass
    vec = q(f"select coalesce(vector->>'opening_type','?'), count(*) from v9_decision_vectors where kind='DECISION' and (ts at time zone 'Asia/Jerusalem')::date='{D}' group by 1 order by 2 desc")
    hist = q(f"select opening_type, day_type from v9_day_type_history where date='{D}' order by id desc limit 1")
    return lock, negs, [(v[0], int(v[1])) for v in vec], (hist[0] if hist else None)


def system_daytype_timeline():
    rows = q(f"select to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), coalesce(vector->>'day_type',''), coalesce(vector->>'phase',''), coalesce(vector->>'extension','') "
             f"from v9_decision_vectors where kind='DECISION' and (ts at time zone 'Asia/Jerusalem')::date='{D}' order by ts")
    at = {}
    for t, lab, ph, ext in rows:
        for mark in ("17:30", "18:30", "21:00"):
            if t <= mark: at[mark] = lab or "—"
    last = (rows[-1][1] or "—") if rows else "—"
    flips = sum(1 for i in range(1, len(rows)) if rows[i][1] != rows[i - 1][1] and rows[i][1])
    return at, last, flips, len(rows)


# ── trades / decisions / health ──────────────────────────────────────────────────────────────────
def trades(day_from, day_to):
    return q("select id, to_char(coalesce(entry_ts,created_at) at time zone 'Asia/Jerusalem','YYYY-MM-DD HH24:MI'), firing_system, direction, "
             "coalesce(pattern_id_at_entry, quality->>'pattern_name'), coalesce(day_type_at_entry,'?'), coalesce(quality->>'contracts','?'), coalesce(exit_reason,''), "
             "coalesce(pnl_sierra, pnl_usd, 0), (pnl_sierra is not null) from v9_trades where mode='live' and state='CLOSED' "
             f"and (coalesce(entry_ts,created_at) at time zone 'Asia/Jerusalem')::date between '{day_from}' and '{day_to}' order by 2")


def demo_trades(day):
    """20.10: every demo trade of the session (all states) — $ = Sierra when reconciled, else books; unpriced stays None."""
    return q("select id, to_char(coalesce(entry_ts,created_at) at time zone 'Asia/Jerusalem','HH24:MI'), firing_system, direction, "
             "coalesce(pattern_id_at_entry, quality->>'pattern_name', quality->>'classification', '?'), coalesce(quality->>'contracts','?'), "
             "coalesce(exit_reason, state), coalesce(pnl_sierra::text, pnl_usd::text, ''), (pnl_sierra is not null), state from v9_trades "
             f"where mode='demo' and (coalesce(entry_ts,created_at) at time zone 'Asia/Jerusalem')::date = '{day}' order by 2, 1")


def sierra_day():
    """(account, daily_pnl) from sierra_state.json when it was written today, else (None, None)."""
    try:
        p = os.path.expanduser('~/SierraChart_Data/v9_export/sierra_state.json')
        st = json.load(open(p))
        if dt.datetime.fromtimestamp(os.path.getmtime(p), IL).date().isoformat() != D:
            return None, None
        return st.get('trade_account'), (float(st['daily_pnl']) if st.get('daily_pnl') is not None else None)
    except Exception:
        return None, None


def decisions():
    tot = q(f"select count(*), count(*) filter (where blocked_by is null) from v9_decision_vectors where kind='DECISION' and (ts at time zone 'Asia/Jerusalem')::date='{D}'")
    blk = q(f"select blocked_by, count(*) from v9_decision_vectors where kind='DECISION' and (ts at time zone 'Asia/Jerusalem')::date='{D}' and blocked_by is not null group by 1 order by 2 desc limit 6")
    return (int(tot[0][0]), int(tot[0][1])) if tot else (0, 0), [(b[0], int(b[1])) for b in blk]


def health():
    h = {}
    try:
        h["pid"] = subprocess.run("lsof -nP -iTCP:8000 -sTCP:LISTEN | tail -1 | awk '{print $2}'", shell=True, capture_output=True, text=True).stdout.strip() or "—"
    except Exception:
        h["pid"] = "?"
    r = q("select round(extract(epoch from (now() - max(ts)))/60) from v9_bars_5min_woodies where symbol='MES'")
    h["feed_age_min"] = r[0][0] if r else "?"
    try:
        gb = [l for l in open("/tmp/gap_backfill.log", encoding="utf-8", errors="replace").read().splitlines() if l.strip()]
        h["gap_backfill"] = gb[-1][:90] if gb else "no run logged"
    except Exception:
        h["gap_backfill"] = "no log"
    try:
        out = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
        pct = re.search(r"(\d+)%", out); h["power"] = ("AC" if "AC Power" in out else "סוללה") + (f" {pct.group(1)}%" if pct else "")
    except Exception:
        h["power"] = "?"
    h["agents"] = subprocess.run("launchctl list | grep -c mems26", shell=True, capture_output=True, text=True).stdout.strip()
    return h


# ── ledger (upsert by key) ───────────────────────────────────────────────────────────────────────
LEDGER_HDR = ("# יומן-תיקונים חי — MEMS26 (נוצר אוטומטית ע״י `scripts/eod_journal.py`; עמודת **סטטוס** נערכת ביד: "
              "proposed → measuring → ruled → live → closed)\n\n| מפתח | נראה לראשונה | נראה לאחרונה | פעמים | סטטוס | ההמלצה | ראיה אחרונה |\n|---|---|---|---|---|---|---|\n")


def load_ledger():
    rows = {}
    if os.path.exists(J_LEDGER):
        for line in open(J_LEDGER, encoding="utf-8"):
            if line.startswith("| ") and not line.startswith("| מפתח") and not line.startswith("|---"):
                c = [x.strip() for x in line.strip().strip("|").split("|")]
                if len(c) >= 7: rows[c[0]] = dict(key=c[0], first=c[1], last=c[2], n=int(c[3] or 0), status=c[4], text=c[5], ev=c[6])
    return rows


def upsert(rows, key, text, ev):
    r = rows.get(key)
    if r: r.update(last=D, n=r["n"] + 1, text=text, ev=ev)
    else: rows[key] = dict(key=key, first=D, last=D, n=1, status="proposed", text=text, ev=ev)


def write_ledger(rows):
    order = {"live": 0, "ruled": 1, "measuring": 2, "proposed": 3, "closed": 9}
    body = "".join("| %s | %s | %s | %d | %s | %s | %s |\n" % (r["key"], r["first"], r["last"], r["n"], r["status"], r["text"], r["ev"])
                   for r in sorted(rows.values(), key=lambda r: (order.get(r["status"], 5), -r["n"], r["key"])))
    open(J_LEDGER, "w", encoding="utf-8").write(LEDGER_HDR + body)


# ── main ─────────────────────────────────────────────────────────────────────────────────────────
def main():
    bars = rth_bars(D)
    if len(bars) < 24:
        print(f"{D}: only {len(bars)} RTH bars — not a session (or feed gap; see gap_backfill)"); return 2
    prev = prev_session_profile(D)
    o = bars[0][1]; h6, l6, c6 = max(b[2] for b in bars[:6]), min(b[3] for b in bars[:6]), bars[5][4]
    ref_ot, ref_note = ref_opening(bars, prev)
    ref_dt, feats = ref_daytype(bars)
    where = ("בתוך-ערך" if prev and prev["val"] <= o <= prev["vah"] else "בתוך-טווח" if prev and prev["low"] <= o <= prev["high"] else
             ("מחוץ-לטווח מעל" if prev and o > prev["high"] else "מחוץ-לטווח מתחת" if prev else "—"))
    lock, negs, vec, hist = system_opening()
    sys_ot = lock["type"] if lock else (vec[0][0] if vec and vec[0][0] not in ("?", "UNKNOWN") else (hist[0] if hist else "—"))
    at, last_lab, flips, nvec = system_daytype_timeline()
    sys_dt_eod = hist[1] if hist else "—"
    tr_day = trades(D, D)
    d10 = q(f"select distinct (ts at time zone 'America/New_York')::date from v9_bars_5min_woodies where symbol='MES' and (ts at time zone 'America/New_York')::date<='{D}' "
            "and (ts at time zone 'America/New_York')::time between '09:30' and '15:55' group by 1 having count(*)>=60 order by 1 desc limit 10")
    d10_from = d10[-1][0] if d10 else D
    tr_10 = trades(d10_from, D); tr_all = trades("2026-07-01", D)
    s_day = sum(float(t[8]) for t in tr_day); s_10 = sum(float(t[8]) for t in tr_10); s_all = sum(float(t[8]) for t in tr_all)
    unver_day = sum(1 for t in tr_day if t[9] != "t")
    dm = demo_trades(D)
    dm_px = [float(t[7]) for t in dm if t[7] not in (None, '') and t[9] == 'CLOSED']
    dm_sum = sum(dm_px); dm_w = sum(1 for v in dm_px if v > 0); dm_l = sum(1 for v in dm_px if v < 0)
    dm_unpriced = sum(1 for t in dm if t[9] == 'CLOSED' and t[7] in (None, '')); dm_open = sum(1 for t in dm if t[9] != 'CLOSED')
    s_acct, s_daily = sierra_day()
    (n_dec, n_pass), blocks = decisions()
    hl = health()
    # per-pattern over the last 10 sessions
    pat = collections.defaultdict(lambda: [0, 0, 0.0])
    for t in tr_10:
        p = pat[t[4] or "?"]; p[0] += 1; p[1] += float(t[8]) > 0; p[2] += float(t[8])
    # ── recommendations (rules) ──
    recs = []   # (key, text, evidence)
    if sys_ot != ref_ot and ref_ot != "UNKNOWN":
        recs.append(("S1-opening-lock", "S1 נעל סוג-פתיחה שונה מקריאת-הברים — שורש T-594 (נעילה בלי רפרנסים-קודמים) / T-595 (מכונה על בר שטוח); המדידה: hist_o / hist_p / hist_po",
                     f"{D}: מערכת {sys_ot} ({lock['t'] + ' ' + lock['how'] if lock else 'EOD'}) · ברים {ref_ot} ({ref_note}; 30 דק׳ נטו {c6 - o:+.2f}, {where})"))
    if sys_dt_eod not in ("—", None) and ref_dt != "UNKNOWN" and sys_dt_eod.replace("Variation", "Normal_Variation").replace("Trend_DD", "Trend_Normal") != ref_dt:
        recs.append(("S1-daytype-eod", "תווית-היום של המערכת בסוף-היום שונה מקריאת-הברים (IB / הרחבה-עם-קבלה / מיקום-הסגירה) — לבדוק את מכונת-המצבים מול הדוקטרינה (pp. 19–29)",
                     f"{D}: מערכת {sys_dt_eod} (17:30 {at.get('17:30','—')} · 18:30 {at.get('18:30','—')} · 21:00 {at.get('21:00','—')} · אחרון {last_lab}, {flips} ריצודים) · ברים {ref_dt} (rib {feats.get('rib')}, close_pos {feats.get('close_pos')}, ext ↑{int(bool(feats.get('ext_up')))} ↓{int(bool(feats.get('ext_dn')))})"))
    losers = [(k, v) for k, v in pat.items() if v[0] >= 3 and v[2] < 0]
    for k, v in sorted(losers, key=lambda kv: kv[1][2])[:3]:
        recs.append((f"pattern-{k}", f"התבנית {k} מפסידה ב-10 הסשנים האחרונים — מועמדת ל-SKIP בעץ עד שתימדד בהרנס (כלל-הקבלה ≥ 0 בשלושת המשטרים)",
                     f"עד {D}: n={v[0]} · wins {int(v[1])} · Σ {v[2]:+.2f}$ (מחיר-ברוקר)"))
    winners = [(k, v) for k, v in pat.items() if v[0] >= 3 and v[2] > 0]
    for k, v in sorted(winners, key=lambda kv: -kv[1][2])[:2]:
        recs.append((f"keep-{k}", f"התבנית {k} מרוויחה ב-10 הסשנים האחרונים — להשאיר; לא להרחיב גודל לפני מדידה", f"עד {D}: n={v[0]} · wins {int(v[1])} · Σ {v[2]:+.2f}$"))
    if unver_day:
        recs.append(("books-unpriced", "עסקאות בלי מחיר-ברוקר (pnl_sierra ריק) — להשלים את ה-reconcile (T-10) לפני שמסתמכים על Σ", f"{D}: {unver_day} מתוך {len(tr_day)}"))
    for b, n in blocks[:1]:
        if n_dec and n / n_dec > 0.5:
            recs.append(("tree-block-dominant", f"שער אחד ({b}) חוסם יותר מחצי מההחלטות — לבדוק שהחסימה דוקטרינרית ולא ארטיפקט (T-593 תווית-ראשונה, T-588 מצב-סיווג ישן)", f"{D}: {b} {n}/{n_dec}"))
    if hl.get("power", "").startswith("סוללה"):
        recs.append(("mac-on-battery", "המק-בוק על סוללה — השבוע 12–16.10 אבד ב-Low Power Sleep; לחבר לחשמל", f"{D}: {hl['power']}"))
    try:
        if float(hl["feed_age_min"]) > 60 and dt.datetime.now(IL).time() < dt.time(23, 30) and dt.datetime.now(IL).weekday() < 5 and dt.time(16, 40) <= dt.datetime.now(IL).time():
            recs.append(("feed-stale", "הפיד ישן בתוך RTH", f"{D}: {hl['feed_age_min']} דק׳"))
    except Exception:
        pass
    # ── journal entry ──
    L = [f"## {D} ({DAY.strftime('%a')}) — נכתב {dt.datetime.now(IL):%Y-%m-%d %H:%M} IL", ""]
    L.append(f"**לייב היום:** {len(tr_day)} עסקאות · Σ **{s_day:+.2f}$** (מחיר-ברוקר{'' if not unver_day else f'; {unver_day} לפי ספרים'}) · 10 סשנים אחרונים Σ {s_10:+.2f}$ ({len(tr_10)}) · מאז 07.07 Σ {s_all:+.2f}$ ({len(tr_all)})")
    if tr_day:
        L.append("\n| שעה | מערכת | תבנית | כיוון | סוג-יום בכניסה | חוזים | יציאה | $ | ברוקר |\n|---|---|---|---|---|---|---|---|---|")
        for t in tr_day:
            L.append(f"| {t[1][11:]} | S{t[2]} | {t[4]} | {t[3]} | {t[5]} | {t[6]} | {t[7]} | {float(t[8]):+.2f} | {'✓' if t[9]=='t' else '✗ ספרים'} |")
    if dm:
        L.append(f"**דמו היום:** {len(dm)} עסקאות · {dm_w}W/{dm_l}L · Σ **{dm_sum:+.2f}$** (ספרים; Sierra כשתומחר)"
                 + (f" · {dm_unpriced} לא-מתומחרות" if dm_unpriced else "") + (f" · {dm_open} פתוחות" if dm_open else "")
                 + (f" · לפי סיירה ({s_acct}) {s_daily:+.2f}$" if s_daily is not None else ""))
        L.append("\n| שעה | מערכת | תבנית | כיוון | חוזים | יציאה | $ | מקור |\n|---|---|---|---|---|---|---|---|")
        for t in dm:
            L.append(f"| {t[1]} | S{t[2]} | {t[4]} | {t[3]} | {t[5]} | {t[6]} | {(format(float(t[7]), '+.2f') if t[7] not in (None, '') else '—')} | "
                     + ("✓ סיירה" if t[8] == 't' else ("ספרים" if t[7] not in (None, '') else "לא-מתומחר")) + " |")
    L.append(f"\n**פתיחה:** מערכת **{sys_ot}**" + (f" (נעילה {lock['t']} {lock['how']}, dir {lock['dir']}, {negs} ביטולים)" if lock else " (אין שורת-נעילה בלוג; לפי " + ("וקטורים" if vec else "EOD") + ")")
             + f" · ברים **{ref_ot}** — {ref_note}; פתיחה {o} {where}" + (f" (אתמול H/L {prev['high']}/{prev['low']}, VAH/VAL/POC {prev['vah']}/{prev['val']}/{prev['poc']})" if prev else "")
             + f"; 30 דק׳ H/L {h6}/{l6}, נטו {c6 - o:+.2f} · {'✓ תואם' if sys_ot == ref_ot else '✗ לא תואם'}")
    L.append(f"**סוג-יום:** מערכת 17:30 {at.get('17:30','—')} · 18:30 {at.get('18:30','—')} · 21:00 {at.get('21:00','—')} · אחרון {last_lab} · EOD {sys_dt_eod} · {flips} ריצודים ({nvec} וקטורים) · "
             f"ברים **{ref_dt}** (IB {feats.get('ibh')}/{feats.get('ibl')} · טווח {feats.get('lo')}–{feats.get('hi')} · rib {feats.get('rib')} · סגירה {feats.get('close')} pos {feats.get('close_pos')} · הרחבה ↑{'כן' if feats.get('ext_up') else 'לא'} ↓{'כן' if feats.get('ext_dn') else 'לא'}) · סגירה−פתיחה {feats.get('close', o) - o:+.2f}")
    L.append(f"**החלטות:** {n_dec} (עברו את העץ {n_pass}) · חסימות: " + (" · ".join(f"{b} {n}" for b, n in blocks) or "—"))
    L.append(f"**בריאות:** backend pid {hl['pid']} · feed {hl['feed_age_min']} דק׳ · סוכנים {hl['agents']} · {hl['power']} · gap_backfill: {hl['gap_backfill']}")
    if pat:
        L.append("\n**10 סשנים אחרונים לפי תבנית (מחיר-ברוקר):** " + " · ".join(f"{k} n={v[0]} {v[2]:+.0f}$" for k, v in sorted(pat.items(), key=lambda kv: -kv[1][2])))
    L.append("\n**המלצות (כללים אוטומטיים — מדידה לפני הדלקה):**")
    for i, (k, text, ev) in enumerate(recs, 1):
        L.append(f"{i}. `{k}` — {text}. *ראיה:* {ev}")
    if not recs:
        L.append("— אין המלצה אוטומטית היום.")
    L.append("\n**שיקול-דעת (הסוכן/מייקל):** _—_\n")
    entry = "\n".join(L) + "\n"
    _base = (os.getenv('RENDER_MOBILE_URL') or 'https://mems26-mobile.onrender.com').rstrip('/')
    _head = (f"סיכום יומי {D}: " + (f"דמו {len(dm)} עסקאות {dm_w}W/{dm_l}L Σ {dm_sum:+.2f}$" if dm else "דמו 0 עסקאות")
             + (f" ({dm_unpriced} לא-מתומחרות)" if dm_unpriced else "")
             + (f" · סיירה {s_acct} {s_daily:+.2f}$" if s_daily is not None else "")
             + f" · לייב {len(tr_day)} Σ {s_day:+.2f}$")
    _rows = [f"{t[1]} {'לונג' if t[3] == 'LONG' else 'שורט'} {t[4]} {t[5]}ח׳ " + (f"{float(t[7]):+.0f}$" if t[7] not in (None, '') else "?")
             for t in dm] + [f"{t[1][11:]} לייב {t[4]} {float(t[8]):+.0f}$" for t in tr_day]
    _tail = f" · עמוד-היום: {_base}/doc/days/{D}.html"
    phone = _head
    for _r in _rows:
        if len(phone) + len(_r) + 3 + len(_tail) > 500:
            phone += " …"; break
        phone += (" — " if phone == _head else "; ") + _r
    phone = (phone + _tail)[:500]
    if DRY:
        print(entry); print("PHONE:", phone); return 0
    os.makedirs(f"{REPO}/docs/journal", exist_ok=True)
    old = open(J_MD, encoding="utf-8").read() if os.path.exists(J_MD) else ""
    hdr = "# יומן-מסחר חי — MEMS26 (נוצר אוטומטית בסוף כל יום ע״י `scripts/eod_journal.py`; מחיר-ברוקר; הכללים: `docs/journal/FIX_LEDGER.md`)\n\n"
    if old.startswith("# "):
        hdr, old = old.split("\n\n", 1)[0] + "\n\n", old.split("\n\n", 1)[1]
    # replace an existing entry of the same day (re-run) instead of duplicating it
    old = re.sub(rf"## {re.escape(D)} \(.*?(?=\n## |\Z)", "", old, flags=re.S).lstrip("\n")
    open(J_MD, "w", encoding="utf-8").write(hdr + entry + "\n" + old)
    rows = load_ledger()
    for k, text, ev in recs: upsert(rows, k, text, ev)
    write_ledger(rows)
    # phone page: last 5 entries + open fixes
    entries = re.findall(r"(## \d{4}-\d\d-\d\d.*?)(?=\n## |\Z)", hdr + entry + "\n" + old, flags=re.S)[:5]
    def md2html(s):
        out = []
        for line in s.splitlines():
            if line.startswith("## "): out.append(f"<h2>{html.escape(line[3:])}</h2>")
            elif line.startswith("| ") and not line.startswith("|---"):
                cells = [html.escape(c.strip()) for c in line.strip().strip("|").split("|")]
                out.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
            elif line.startswith("|---"): continue
            elif re.match(r"^\d+\. ", line): out.append(f"<li>{html.escape(line.split('. ', 1)[1]).replace('`', '')}</li>")
            elif line.strip(): out.append(f"<p>{html.escape(line).replace('**', '')}</p>")
        s2 = "\n".join(out)
        s2 = re.sub(r"((?:<tr>.*?</tr>\n?)+)", r"<table>\1</table>", s2, flags=re.S)
        s2 = re.sub(r"((?:<li>.*?</li>\n?)+)", r"<ol>\1</ol>", s2, flags=re.S)
        return s2
    open_fixes = [r for r in rows.values() if r["status"] != "closed"]
    fx = "".join(f"<tr><td>{html.escape(r['key'])}</td><td>{html.escape(r['status'])}</td><td>{r['n']}</td><td>{html.escape(r['text'])}</td></tr>"
                 for r in sorted(open_fixes, key=lambda r: -r["n"]))
    page = """<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>יומן-מסחר · MEMS26</title><style>body{font-family:-apple-system,Segoe UI,Arial;background:#0b0f14;color:#e6edf3;margin:0;padding:12px}
h1{font-size:18px;margin:0 0 6px}h2{font-size:15px;margin:16px 0 6px;color:#9fd3ff}table{border-collapse:collapse;width:100%%;font-size:12px;margin:6px 0}td,th{border-bottom:1px solid #223;padding:4px 5px;text-align:right}
p{margin:5px 0;font-size:13px}li{margin:6px 0;font-size:13px}.k{color:#9fb3c8;font-size:12px}.box{background:#121a24;border-radius:10px;padding:10px;margin:8px 0}</style></head><body>
<h1>📒 יומן-מסחר</h1><div class="k">נוצר %s · <a style="color:#9fd3ff" href="index.html">← תפריט</a></div>
<div class="box"><h2>תיקונים פתוחים (%d)</h2><table><tr><th>מפתח</th><th>סטטוס</th><th>פעמים</th><th>ההמלצה</th></tr>%s</table></div>
%s</body></html>""" % (html.escape(dt.datetime.now(IL).strftime("%Y-%m-%d %H:%M")), len(open_fixes), fx, "".join(f"<div class='box'>{md2html(e)}</div>" for e in entries))
    os.makedirs(os.path.dirname(J_HTML), exist_ok=True)
    open(J_HTML, "w", encoding="utf-8").write(page)
    say(entry)
    print("PHONE:", phone)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("eod_journal ERROR:", e); sys.exit(1)
