# CC Prompt — Pattern Watcher (כל 15 דק' עד 22:00, "מה חסר לכל תבנית")

פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.

## מטרה (אחת)
לתת ל-Michael חיווי חוזר של **כל התבניות** (S2 + Woodies) כל 15 דקות עד **22:00 שעון-מקומי**,
ולכל תבנית **מה חסר לה** (אילו גייטים נכשלים). **לא** להמציא לוגיקה חדשה —
המידע כבר מחושב ב-endpoint הקיים `GET /api/v9/build/pattern-status`
(מחזיר לכל תבנית `status` + `blockers` + `reason`). המשימה = polling + פורמט + לוג.

**אסור לגעת** (risk surface): שום שינוי במנועים, ב-`s2_inspector`/`woodies_inspector`,
ב-gateway, או בכל decision-path. זה כלי-תצפית read-only בלבד.

## למה ככה (יעילות)
אל תריץ אותי (CC) כל 15 דק' — כל הרצה היא סשן חדש ויקר. במקום: סשן אחד שכותב סקריפט
שמסקר את עצמו ורושם ללוג. Michael עושה `tail -f` על הלוג. המקור היחיד = ה-endpoint.

## Phase 1 — צור `scripts/pattern_watch.py` בדיוק כך
```python
#!/usr/bin/env python3
"""pattern_watch.py — poll build/pattern-status, log per-pattern blockers.
Read-only: GETs the diagnostic endpoint only; never routes trades. Michael 2026-06-08.
Usage: python3 scripts/pattern_watch.py [--once]"""
import json, sys, time, urllib.request
from collections import Counter
from datetime import datetime

URL = "http://localhost:8000/api/v9/build/pattern-status?systems=five_min,woodies"
INTERVAL_MIN = 15
END_HHMM = "22:00"            # local wall-clock stop (machine TZ)
LOG = "docs/reports/pattern_watch_{date}.log".format(date=datetime.now().strftime("%Y-%m-%d"))

def fetch():
    with urllib.request.urlopen(URL, timeout=5) as r:
        return json.load(r)

def render(data):
    out = []
    ts = datetime.now().strftime("%H:%M:%S")
    verdict = (data.get("readiness") or {}).get("verdict", "?")
    out.append(f"=== {ts}  readiness={verdict} ===")
    counter = Counter(); n_armed = n_blocked = n_fired = 0
    for so in data.get("systems", []):
        if so.get("id") not in ("five_min", "woodies"):
            continue
        out.append(f"  [{so.get('name', so.get('id'))}]")
        for p in so.get("patterns", []):
            st = p.get("status"); blk = p.get("blockers") or []
            n_armed  += st == "armed"
            n_blocked += st == "blocked"
            n_fired  += st == "fired"
            for b in blk: counter[b] += 1
            out.append(f"    {str(p.get('id')):<16} {str(st):<9} missing: {', '.join(blk) if blk else '—'}")
    out.append(f"  SUMMARY armed={n_armed} blocked={n_blocked} fired={n_fired} "
               f"| top blockers: {counter.most_common(3)}")
    return "\n".join(out)

def main():
    once = "--once" in sys.argv
    print(f"# pattern_watch start {datetime.now():%Y-%m-%d %H:%M %Z} → until {END_HHMM} local, every {INTERVAL_MIN}m")
    while True:
        try:
            block = render(fetch())
        except Exception as e:
            block = f"=== {datetime.now():%H:%M:%S}  ENDPOINT ERROR: {e} ==="
        print(block, flush=True)
        with open(LOG, "a") as f:
            f.write(block + "\n")
        if once:
            break
        if datetime.now().strftime("%H:%M") >= END_HHMM:
            print(f"# reached {END_HHMM} local — stopping.")
            break
        time.sleep(INTERVAL_MIN * 60)

if __name__ == "__main__":
    main()
```

## Phase 2 — אימות מיידי (חובה, Rule 5)
הרץ פעם אחת והדבק **פלט גולמי** מלא:
```
python3 scripts/pattern_watch.py --once
```

## Phase 3 — הפעלה ברקע עד 22:00
```
nohup python3 scripts/pattern_watch.py >> docs/reports/pattern_watch_$(date +%F).log 2>&1 &
echo "PID $!"
```
מסור ל-Michael את נתיב-הלוג + ה-PID. הוא יעשה `tail -f`.

## Acceptance Criteria (בינארי — סמן ✓/✗)
- [ ] `scripts/pattern_watch.py` קיים, זהה לספק לעיל.
- [ ] `--once` רץ ומדפיס בלוק עם **שורה לכל 9 תבניות-Woodies + 10 תבניות-S2**, כל אחת עם `status` + `missing: [...]`.
- [ ] שורת `SUMMARY` מציגה armed/blocked/fired + top blockers.
- [ ] אם ה-backend למטה → שורת `ENDPOINT ERROR` נקייה (לא traceback/crash).
- [ ] התהליך-ברקע פעיל (PID חי) וכותב ל-`docs/reports/pattern_watch_<date>.log`.

## הערת anti-tautological
אין כאן "טסט" שמשכפל לוגיקה — האימות הוא הרצת `--once` מול ה-**endpoint האמיתי** והדבקת הפלט.
מבחן ליטמוס: אם ה-endpoint יחזיר אחרת/יפול → הפלט משתנה/מראה ERROR. אל תמציא נתונים אם הקריאה נכשלת.

## NOT-DONE (חובה למלא בדוח)
- מה לא נבדק / מה נשאר פתוח / כל סטייה מהספק.
- ⚠️ הערה ל-Michael: תבניות יכולות *לדרוך* רק בזמן RTH (09:30–16:00 ET ≈ 16:30–23:00 שעון-ישראל).
  אחרי סגירת-RTH הכל יראה `blocked` (rth_gate/feed). החלון המעניין הערב = עד ~23:00 IL.
  אם 22:00 שאתה מתכוון אליו אינו שעון-ישראל — תקן את `END_HHMM`.
```
```
