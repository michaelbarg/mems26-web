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

    log_path = os.getenv("MEMS26_LOG_FILE", DEFAULT_LOG_FILE)
    pids = _backend_pids()
    if not pids:
        check("T-61 שכבת-INFO בלוג", False,
              "לא נמצא תהליך backend רץ (pgrep 'uvicorn backend.main:app')")
        return

    best = None
    for pid in pids:
        res = find_boot_probe(log_path, pid=pid)
        if res.get("pid_match"):
            best = res
            break
        best = best or res

    if not best.get("found"):
        check("T-61 שכבת-INFO בלוג", False,
              best.get("reason") or f"אין שורת '{BOOT_PROBE_PREFIX}' ב-{log_path}")
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
    p = api("/api/v9/live_price")
    check("feed טרי (<30s)", bool(p and p.get("age_ms", 1e9) < 30000),
          f"age={p.get('age_ms')}ms" if p else "no price")
    g = api("/api/v9/gateway/status")
    if g:
        check("live_slot פנוי", g.get("live_slot") is None, f"slot={g.get('live_slot')}")
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-live", action="store_true", help="דלג על שלב D")
    args = ap.parse_args()
    print("🔫 FIRE DRILL — ירי-יבש של שרשרת ההחלטה\n")
    stage_a()
    stage_b()
    stage_c()
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
        return 1
    print("🟢 GO — כל שרשרת ההחלטה כשרה לירי.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
