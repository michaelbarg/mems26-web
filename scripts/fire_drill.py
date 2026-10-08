#!/usr/bin/env python3
"""fire_drill — ירי-יבש של שרשרת ההחלטה לפני פתיחה (מייקל 2026-07-08).

GO/NO-GO אמיתי: לא בודק רק צנרת אלא שהמערכת מסוגלת לייצר ירי כשר.
נולד מ-07-08: "הכל תקין" אבל הסטופים (1pt) נפסלו ב-A7 כל היום — הדריל הזה
היה תופס את זה ב-16:00 במקום 18:30.

שלבים:
  A  flag_guard — דגלים שנפסקו לא זזו.
  B  שרשרת הסטופ: compute_stop_v2 (עוגן צמוד + עוגן מבני, שני כיוונים, ATR
     של היום מה-DB/API או סינתטי 12pt) → validate_fire חייב לקבל.
  C  חוזים: effective_contracts()==2 · בר-אישור עם סובלנות ATR.
  D  (עם באקנד חי) feed טרי · day_type · slots פנויים · live_enabled [2,4].
  E  אופציונלי (FIRE_DRILL_STAGE_E=1): setups אמיתיים מה-RTH האחרון דרך
     fire_readiness_real; ברירת-מחדל OFF.

הרצה: python3 scripts/fire_drill.py [--no-live] (ללא שלב D)
Exit 0=GO, 1=NO-GO (עם הסיבות).
"""
import argparse
import json
import math
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# הדריל בוחן את המערכת כפי שהיא רצה: טוען את .env (כמו env_loader בבוט) —
# בלי זה effective_contracts/סובלנות-האישור נבדקים בסביבה ריקה (נתפס בהרצה
# הראשונה: החזיר 3 חוזים כי FIXED_CONTRACTS_2 לא היה בתהליך).
# GUARDED: only load .env when running as a script, NOT when imported by tests
# (importing this module at test-collection time poisoned 83+ tests with .env vars).
if __name__ == "__main__" or os.getenv("FIRE_DRILL_LOAD_ENV", "0") == "1":
    from scripts.flag_guard import parse_env  # noqa: E402
    for _k, _v in parse_env(os.path.join(ROOT, ".env")).items():
        os.environ.setdefault(_k, _v)

FAILS = []


def check(name, ok, detail=""):
    print(f"  {'✓' if ok else '✗'} {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILS.append(f"{name}: {detail}")
    return ok


def api(path, timeout=4):
    try:
        with urllib.request.urlopen(f"http://localhost:8000{path}", timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def cme_globex_open(now_et) -> bool:
    """T-265/T-532 (BRIEF §3.3, fix-agent 09.10): is the CME Globex session for MES open at this ET
    instant? Sun 18:00 ET → Fri 17:00 ET, minus the daily 17:00–18:00 ET maintenance break.
    One predicate for both stage-D feed checks (price export AND newest DB bar), so the drill never
    declares "feed stale" on a closed market (Saturday restart window, Friday evening, the daily
    break) — on a closed market both lines are informational. Exchange holidays are NOT modelled on
    purpose: Globex trades most of them on reduced hours, and the drill would rather ask for a fresh
    feed on such a day than go quiet on it. Pure, so the test pins every edge."""
    wd, hm = now_et.weekday(), now_et.hour * 60 + now_et.minute
    if wd == 5:                      # Saturday
        return False
    if wd == 6:                      # Sunday: opens 18:00 ET
        return hm >= 18 * 60
    if wd == 4 and hm >= 17 * 60:    # Friday: weekly close 17:00 ET
        return False
    return not (17 * 60 <= hm < 18 * 60)   # Mon–Thu: daily break 17:00–18:00 ET


def feed_price_line(p, market_open: bool) -> bool:
    """Stage-D line 1: the price export's age. A hard check only while Globex is open; on a closed
    market it is printed as information and never reaches FAILS (T-265/T-532: no "feed ישן" NO-GO
    on a Saturday restart window). Returns the freshness verdict either way."""
    fresh = bool(p and p.get("age_ms", 1e9) < 30000)
    detail = f"age={p.get('age_ms')}ms" if p else "no price"
    if market_open:
        return check("feed טרי (<30s)", fresh, detail)
    print(f"  ℹ feed (live_price): {detail} — השוק סגור (Globex), מידע בלבד")
    return fresh


def stage_a():
    print("— שלב A · דגלים שנפסקו —")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "flag_guard.py")],
                       capture_output=True, text=True)
    tail = (r.stdout.strip().splitlines() or [""])[-1]
    check("flag_guard", r.returncode == 0, tail)


def _atr_ticks_today():
    """ATR-14 בטיקים מהברים החיים; נפילה → סינתטי 12pt (יום-מגמה)."""
    d = api("/api/v9/chart/bars5min?limit=15")
    rows = d if isinstance(d, list) else (d or {}).get("bars", []) if d else []
    rngs = []
    for b in rows:
        h, l = b.get("high", b.get("h")), b.get("low", b.get("l"))
        if h is not None and l is not None:
            rngs.append(float(h) - float(l))
    if len(rngs) >= 5:
        return (sum(rngs) / len(rngs)) / 0.25, "live"
    return 48.0, "synthetic-12pt"


def stage_b():
    print("— שלב B · שרשרת הסטופ (הבאג של 07-08) —")
    from backend.v9.systems.woodies.atr_stop import PatternGroup, compute_stop_v2
    from backend.v9.shared.pre_fire_validator import FireRequest, validate_fire

    atr, src = _atr_ticks_today()
    print(f"    ATR-14 ≈ {atr*0.25:.1f} נק' ({src})")
    entry = 7500.0
    for direction, sign in (("LONG", -1), ("SHORT", 1)):
        for label, anchor_ticks in (("עוגן-צמוד(1pt)", 4), ("עוגן-מבני(0.8×ATR)", int(0.8 * atr))):
            struct = entry + sign * anchor_ticks * 0.25
            v2 = compute_stop_v2(direction, entry, struct, PatternGroup.CONT_TIGHT, atr)
            risk = v2.risk_ticks * 0.25
            t1 = entry + (-sign) * risk  # 1R fallback כמו הנתיב האמיתי
            resp = validate_fire(FireRequest(
                system_id="T2_WOODIES", direction=direction, entry_price=entry,
                stop_price=v2.stop_price, t1_price=t1, time_stop_minutes=90, confidence=70))
            check(f"{direction} {label} → סטופ {risk:.1f} נק' עובר וולידציה",
                  resp.valid, resp.fail_reason or "")


def stage_c():
    print("— שלב C · חוזים + בר-אישור —")
    from backend.v9.services.sierra_command import effective_contracts
    from backend.v9.systems.entry_confirm import entry_confirmed
    # The expected count comes from the SAME resolver the trade path uses.
    # It used to be re-derived here from a hand-written if-chain that stopped at
    # FIXED_CONTRACTS_4, so the day the 5-contract ruling was enabled the drill
    # went NO-GO on a correct system: it was measuring the drill's own stale
    # copy of the ruling, not the ruling. One source (2026-08-18).
    from backend.v9.services.contract_size import ruled_contracts
    _want = ruled_contracts() or 1
    # S-4 (cc-imac 07-14): send a REALISTIC full-size setup, not a bare {"contracts":1}.
    # Under SIZE_CAP_OVER_FIXED_V1=1 an explicit "1" is read as a size-CUT → min(fixed,1)=1
    # → false NO-GO. A real fire sends a size string; "full" → the ruled count.
    n = effective_contracts({"size": "full"})
    # Michael 2026-08-19: "אם אין מספיק מרגין לסחור על 4 לא לשאול לבצע" — when
    # the LIVE account cannot carry the ruled size, the resolver falls back to
    # MARGIN_FALLBACK_CONTRACTS by ruling. That is correct behavior, not a
    # broken chain; the drill must not NO-GO a system that is following the
    # ruling. Accept either, and SAY which one is in effect right now.
    try:
        from backend.v9.services.margin_sizing import MARGIN_FALLBACK_CONTRACTS, enabled as _ms_on
        _accept = {_want} | ({MARGIN_FALLBACK_CONTRACTS} if _ms_on() else set())
    except Exception:
        _accept = {_want}
    _label = (f"effective_contracts == {_want} (לפי דגלי הפסיקה)" if n == _want
              else f"effective_contracts == {n} (נפילת-מרג'ין מהפסיקה 08-19; הפסוק {_want})")
    check(_label, n in _accept, f"got {n}")
    atr, _ = _atr_ticks_today()
    tol = 0.10 * atr * 0.25
    ok, why = entry_confirmed(direction="SHORT", bars=[{"o": 7500.0, "c": 7500.0 + tol * 0.7}],
                              tol_points=tol)
    check(f"בר-אישור: סגירה-נגד של 70% מהסובלנות ({tol:.2f} נק') עוברת", ok, why)


def _backend_pids():
    """PIDs של ה-uvicorn שמריץ את backend.main (יכולים להיות כמה בזמן ריסטארט)."""
    try:
        r = subprocess.run(["pgrep", "-f", "uvicorn backend.main:app"],
                           capture_output=True, text=True, timeout=10)
        return [int(p) for p in r.stdout.split() if p.strip().isdigit()]
    except Exception:
        return []


def check_logging_layer():
    """T-61 · שכבת-ה-INFO חיה בתהליך שרץ **עכשיו** — או NO-GO רועש.

    נולד מ-19.08: אחרי ריסטארט-16:09 הלוג כתב רק WARNING+ בלי חותמת (חתימת
    `logging.lastResort` — הקונפיג לא נטען), ולכן 22 עסקאות-צל ישבו בספרים מול
    **0** שורות `SHADOW trade TM`, ו-`[ExitVerify]`/`OPENING_DIR_FUSION` (שניהם
    INFO) היו בלתי-נראים. "0 שורות" באותו יום היה עיוורון, לא ממצא. הבדיקה הזו
    היא מה שהופך את זה לבלתי-אפשרי-בשקט: שורת-הבוט חייבת להימצא בלוג **עם ה-PID
    שרץ כרגע**.
    """
    from backend.logging_setup import BOOT_PROBE_PREFIX, DEFAULT_LOG_FILE, find_boot_probe

    # T-505 (28.09, cowork-dev) · **איזה** קובץ-לוג — לא רק איזה PID.
    # `DEFAULT_LOG_FILE=/tmp/backend.err.log` נכון ל-LaunchAgent, אבל
    # `scripts/start_all.sh:76` מריץ את הבקאנד ב-screen עם `2>&1 | tee
    # /tmp/backend.log` — ואז שורת-הבוט של התהליך שרץ יושבת ב-`backend.log`
    # ו-`backend.err.log` מכיל רק את שורות-הבוט של תהליכי-הבדיקה החולפים
    # (fire_drill/pytest מייבאים את האפליקציה). נמדד 28.09 15:41: הבדיקה
    # החזירה "newest boot probe is pid=15052 but the running backend is
    # pid=14900" ⇒ NO-GO, בזמן ש-`backend.log` הכיל
    # `pid=14904 … level=INFO` + 126 שורות INFO אחריה — כלומר שכבת-ה-INFO
    # הייתה חיה וה-NO-GO היה של **נתיב-המדידה**, לא של המערכת.
    # false-NO-GO מסוכן כמו false-GO: הוא עוצר יום-מסחר כשר, או מאמן סוכנים
    # להתעלם משער אדום. לכן סורקים את כל הנרות שהאפליקציה יכולה לכתוב אליהם
    # ומקבלים את הראשון שיש בו את ה-PID שרץ. קריאה-בלבד, אפס שינוי-התנהגות.
    _env_log = os.getenv("MEMS26_LOG_FILE")
    log_candidates = ([_env_log] if _env_log else
                      [DEFAULT_LOG_FILE, "/tmp/backend.log"])
    pids = _backend_pids()
    if not pids:
        check("T-61 שכבת-INFO בלוג", False,
              "לא נמצא תהליך backend רץ (pgrep 'uvicorn backend.main:app')")
        return

    best, log_path = None, log_candidates[0]
    for cand in log_candidates:
        for pid in pids:
            res = find_boot_probe(cand, pid=pid)
            if res.get("pid_match"):
                best, log_path = res, cand
                break
            if best is None or (res.get("found") and not best.get("found")):
                best, log_path = res, cand
        if best is not None and best.get("pid_match"):
            break

    if not best.get("found"):
        check("T-61 שכבת-INFO בלוג", False,
              best.get("reason")
              or f"אין שורת '{BOOT_PROBE_PREFIX}' ב-{' / '.join(log_candidates)}")
        return
    if not best.get("pid_match"):
        check("T-61 שכבת-INFO בלוג", False, best.get("reason") or "PID לא תואם")
        return

    # השורה קיימת — אבל גם לוודא שהרמה באמת INFO בפועל ולא רק בשורה הזו.
    check(f"T-61 שכבת-INFO בלוג ({os.path.basename(log_path)})", True,
          f"{best['line'][:110]} · {best['info_after']} שורות INFO אחריה")
    _flowing = best["info_after"] > 0
    check("T-61 רמת-INFO זורמת בפועל (לא רק שורת-הבוט)", _flowing,
          "" if _flowing else "שורת-הבוט קיימת אבל אין אף INFO אחריה — הרמה הועלתה אחרי הבוט")


def stage_d():
    # wire_guard — האם כל אתר-קריאה של פקודה/יציאה/התראה בכלל ניתן-לקריאה.
    # זה הבודק שהיה תופס את #682 (TypeError לפני שנכתב בייט) — ו-6 טסטים
    # ירוקים לא תפסו, כי הם בדקו מחרוזות ולא הריצו כלום.
    try:
        _wg = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "wire_guard.py")],
                             capture_output=True, text=True, timeout=60)
        _line = (_wg.stdout.strip().splitlines() or [""])[0]
        check("wire_guard — כל אתרי-הקריאה ניתנים-לקריאה",
              _wg.returncode == 0,
              _line if _wg.returncode == 0 else _wg.stdout.strip()[-300:])
    except Exception as _e:
        check("wire_guard רץ", False, str(_e))

    # לוג-המשימות — מקור-אמת אחד, שנכשל אם הוא מתיישן.
    # אותה צורה כמו flag_guard: לא מזכיר, נכשל.
    try:
        _tl = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "task_log_guard.py")],
                             capture_output=True, text=True, timeout=30)
        _l = (_tl.stdout.strip().splitlines() or [""])[0]
        check("לוג-המשימות עדכני ומובנה", _tl.returncode == 0,
              _l if _tl.returncode == 0 else _tl.stdout.strip()[-300:])
    except Exception as _e:
        check("task_log_guard רץ", False, str(_e))

    print("— שלב D · מצב חי —")
    h = api("/api/v9/health")
    check("backend health", bool(h and h.get("status") == "ok"))
    # T-61 — לפני כל בדיקה שנשענת על הלוג: האם הלוג בכלל רואה?
    try:
        check_logging_layer()
    except Exception as _lg_e:
        check("T-61 שכבת-INFO בלוג", False, f"{type(_lg_e).__name__}: {_lg_e}")
    # T-265/T-532 (BRIEF §3.3, fix-agent 09.10): one market predicate for both feed lines. On a
    # closed market (Saturday window, Friday evening, the 17:00–18:00 ET break) a stale price
    # export is not a fault — the drill used to say "feed ישן" and go NO-GO on it.
    from datetime import timezone as _fd_tz0
    _fd_open = cme_globex_open(datetime.now(_fd_tz0.utc).astimezone(ZoneInfo("America/New_York")))
    feed_price_line(api("/api/v9/live_price"), _fd_open)
    # T-430 (20.09): the export files are rewritten every ~3s by the DLL even
    # when Sierra's DATA feed is dead, so mtime/`live_price.age_ms` can read
    # "fresh" while the newest BAR is days old. The truth is the newest BAR,
    # and it must be young whenever the CME is open (Sun 18:00 ET → Fri 17:00
    # ET, 17:00-18:00 ET daily break excluded). Closed market → informational.
    #
    # NB (corrected 20.09 21:20, cowork-daily — raw output in LIVE_CHANNEL):
    # the original T-430 write-up justified this guard with "Friday 19.09 had
    # 0 bars and 0 trades". That premise is FALSE and must not be re-cited:
    # 19.09 is a SATURDAY. Friday 18.09 traded a full session — 204 ET-day
    # bars 00:00→16:55 ET, zero gaps, 78 RTH, 95 trades (1 live + 94 shadow).
    # The freeze at Fri 16:55 ET is the CME weekly close, and it is identical
    # on the six preceding Fridays (each 00:00→16:55 ET, n=204 to the bar).
    # The guard below is right on its own merits; the anecdote was not.
    try:
        from datetime import datetime as _fd_dt, timezone as _fd_tz
        from zoneinfo import ZoneInfo as _fd_ZI
        from backend.v9.db.read import read_scalar as _fd_rs
        _fd_max = _fd_rs("SELECT max(ts) FROM v9_bars_5min_woodies WHERE symbol='MES'", {})
        # market predicate: cme_globex_open (same instant as the price-export line above —
        # T-265/T-532: the inline weekday arithmetic that lived here moved into one tested function)
        _fd_age_min = None
        if _fd_max is not None:
            _fd_mx = _fd_max if getattr(_fd_max, "tzinfo", None) else _fd_max.replace(tzinfo=_fd_tz.utc)
            _fd_age_min = (_fd_dt.now(_fd_tz.utc) - _fd_mx).total_seconds() / 60.0
        _fd_detail = (f"last bar {_fd_max} · age {_fd_age_min:.0f} min · market "
                      f"{'OPEN' if _fd_open else 'closed'}") if _fd_age_min is not None else "no bars"
        if _fd_open:
            check("נתוני-ברים חיים (DB, <10 דק' כשהשוק פתוח)", _fd_age_min is not None and _fd_age_min < 10, _fd_detail)
        else:
            print(f"  ℹ נתוני-ברים (DB): {_fd_detail} — השוק סגור, מידע בלבד")
    except Exception as _fd_e:
        check("נתוני-ברים חיים (DB)", False, f"{type(_fd_e).__name__}: {_fd_e}")
    g = api("/api/v9/gateway/status")
    if g:
        check("live_slot פנוי", g.get("live_slot") is None, f"slot={g.get('live_slot')}")
        # T-551 (Michael 07.10 15:1x "תמשיך בדמו"): the ruled mode decides which registration the
        # drill demands — MEMS26_MODE=demo ⇒ demo_enabled [2,4] and live_enabled [] (orders go to
        # Sierra's sim account and the books say demo); any other mode ⇒ live_enabled [2,4] as before.
        if (os.getenv("MEMS26_MODE") or "").strip().lower() == "demo":
            check("demo_enabled == [2,4] (MEMS26_MODE=demo)",
                  sorted(g.get("demo_enabled_systems") or []) == [2, 4], str(g.get("demo_enabled_systems")))
            check("live_enabled == [] (MEMS26_MODE=demo)", not (g.get("live_enabled_systems") or []),
                  str(g.get("live_enabled_systems")))
        else:
            check("live_enabled == [2,4]", sorted(g.get("live_enabled_systems") or []) == [2, 4],
                  str(g.get("live_enabled_systems")))
    else:
        check("gateway/status", False, "no response")
    dt = api("/api/v9/day_type/state")
    st = (dt or {}).get("state") or {}
    check("day_type קיים", bool(st.get("day_type")),
          f"{st.get('day_type')} conf={st.get('confidence')}")


def _previous_rth_date():
    day = datetime.now(ZoneInfo("America/New_York")).date() - timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day.isoformat()


def stage_e(no_live=False):
    """Optional real-setup replay. Default OFF; never calls the gateway."""
    print("— שלב E · מוכנות-ירי אמיתית —")
    cmd = [
        sys.executable,
        os.path.join(ROOT, "scripts", "fire_readiness_real.py"),
        "--date",
        _previous_rth_date(),
    ]
    if no_live:
        cmd.append("--no-live")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.rstrip())
    detail = (result.stderr.strip().splitlines() or [f"exit={result.returncode}"])[-1]
    check("fire_readiness_real", result.returncode == 0, detail)


def stage_yaml():
    """T-168ב: verify RULED_FLAGS.yaml is valid YAML (yaml.safe_load).

    flag_guard uses a regex parser that tolerates broken YAML. But every
    other tool (gen_flag_index, editors, CI) needs valid YAML. This
    catches regressions before they reach production.
    """
    print("— שלב Y · RULED_FLAGS YAML תקין —")
    try:
        import yaml
        path = os.path.join(ROOT, "config", "RULED_FLAGS.yaml")
        data = yaml.safe_load(open(path))
        n = len(data.get("ruled", {}))
        check("yaml_valid", True, f"RULED_FLAGS.yaml: {n} ruled flags")
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        detail = f"line {mark.line + 1}: {e.problem}" if mark else str(e)[:100]
        check("yaml_valid", False, detail)
    except Exception as e:
        check("yaml_valid", False, str(e)[:100])


def stage_guards():
    """Run the trading-behaviour guard tests (guard_tests.sh).

    These are the named regression tests that protect live behaviour —
    sizing, entry_stop immutability, VA sanity, entry quality, slot.
    A failure here means a live behaviour changed underneath us.
    Wired here so they run before every session, not just in CI.
    """
    print("— שלב G · שומרי-התנהגות (guard_tests.sh) —")
    script = os.path.join(ROOT, "scripts", "guard_tests.sh")
    if not os.path.exists(script):
        check("guard_tests", False, "guard_tests.sh missing")
        return
    result = subprocess.run(["bash", script], capture_output=True, text=True)
    if result.stdout:
        # Print just the last few lines (summary)
        lines = result.stdout.strip().splitlines()
        for line in lines[-5:]:
            print(f"  {line}")
    detail = (result.stdout.strip().splitlines() or ["no output"])[-1]
    check("guard_tests", result.returncode == 0, detail)


def report_awareness():
    """ציון-המודעות של הסשן האחרון שהושלם — **דיווח-בלבד** (T-159).

    מדד, לא שער. נקרא *אחרי* שה-GO/NO-GO הוכרע והודפס, אינו נוגע ב-FAILS,
    ואינו יכול לשנות את קוד-היציאה — גם לא דרך חריגה (הכל עטוף). ציון נמוך
    הוא ממצא-למדידה, לא עילה לחסום סשן; וכשל-DB בכלי-מדידה בוודאי לא.
    """
    try:
        from scripts.awareness_score import _connect, last_completed_session, measure, render
        cn = _connect()
        try:
            day = last_completed_session(cn.cursor())
        finally:
            cn.close()
        if day is None:
            print("— ציון-המודעות (דיווח-בלבד · T-159) — לא-נמדד: אין סשן שהושלם ב-DB")
            return
        res = measure(day)
        print("— ציון-המודעות (דיווח-בלבד · T-159) —")
        print(render(res) if res else f"  לא-נמדד: אפס ברי-RTH ל-{day}")
    except Exception as exc:  # כלי-מדידה לעולם לא מפיל את הדריל
        print(f"— ציון-המודעות (דיווח-בלבד · T-159) — לא-נמדד: "
              f"{type(exc).__name__}: {str(exc)[:120]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-live", action="store_true", help="דלג על שלב D")
    args = ap.parse_args()
    print("🔫 FIRE DRILL — ירי-יבש של שרשרת ההחלטה\n")
    stage_a()
    stage_b()
    stage_c()
    stage_yaml()
    stage_guards()
    if not args.no_live:
        stage_d()
    if os.getenv("FIRE_DRILL_STAGE_E", "0").lower() in ("1", "true", "yes"):
        stage_e(no_live=args.no_live)
    print()
    if FAILS:
        print(f"🔴 NO-GO — {len(FAILS)} כשלים:")
        for f in FAILS:
            print(f"   · {f}")
        rc = 1
    else:
        print("🟢 GO — כל שרשרת ההחלטה כשרה לירי.")
        rc = 0
    print()
    report_awareness()   # אחרי ההכרעה בכוונה — מדד, לא שער (T-159)
    return rc


if __name__ == "__main__":
    sys.exit(main())
