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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# הדריל בוחן את המערכת כפי שהיא רצה: טוען את .env (כמו env_loader בבוט) —
# בלי זה effective_contracts/סובלנות-האישור נבדקים בסביבה ריקה (נתפס בהרצה
# הראשונה: החזיר 3 חוזים כי FIXED_CONTRACTS_2 לא היה בתהליך).
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
    # הספירה הצפויה נגזרת מהפסיקה החיה ב-env (07-09: ‏3 חוזים; _2 גובר כשדלוק)
    _want = 2 if os.getenv("FIXED_CONTRACTS_2", "0").lower() in ("1", "true", "yes") \
        else (3 if os.getenv("FIXED_CONTRACTS_3", "0").lower() in ("1", "true", "yes") else 1)
    n = effective_contracts({"contracts": 1})
    check(f"effective_contracts == {_want} (לפי דגלי הפסיקה)", n == _want, f"got {n}")
    atr, _ = _atr_ticks_today()
    tol = 0.10 * atr * 0.25
    ok, why = entry_confirmed(direction="SHORT", bars=[{"o": 7500.0, "c": 7500.0 + tol * 0.7}],
                              tol_points=tol)
    check(f"בר-אישור: סגירה-נגד של 70% מהסובלנות ({tol:.2f} נק') עוברת", ok, why)


def stage_d():
    print("— שלב D · מצב חי —")
    h = api("/api/v9/health")
    check("backend health", bool(h and h.get("status") == "ok"))
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-live", action="store_true", help="דלג על שלב D")
    args = ap.parse_args()
    print("🔫 FIRE DRILL — ירי-יבש של שרשרת ההחלטה\n")
    stage_a()
    stage_b()
    stage_c()
    if not args.no_live:
        stage_d()
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
