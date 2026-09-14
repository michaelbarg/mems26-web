# T-366 — חוסם-קיצון-טרי עובר לשער ויחול על כל המפיקים. דחוף.

**מייקל, 14.09 18:30: "אני רוצה שזה יתוקן עכשיו."** בצע מיד, בלי שאלות, בלי ריפליי מקדים.
**זה כלל-דוקטרינה פסוק ולא שאלה אמפירית** — הריפליי אחר-כך מכוונן את `K`, הוא לא מחליט אם.

## הכלל, במשפט
**אין להיכנס נגד קיצון-סשן שנקבע לפני פחות מ-`K` ברים.** לונג לא קונה שפל שזה עתה נוצר;
שורט לא מוכר שיא שזה עתה נוצר. **חל על כל תבנית, כל מערכת, כל שלב.**

## למה עכשיו — שתי עסקאות היום
```
17:20  שפל-הסשן היה 7668.00 מ-16:35
17:25  שפל חדש 7665.25 נקבע כאן
17:25  FLOOR_TOUCH2 LONG 7671.25  גיל-השפל=0  → נכנסה   → סטופ 17:30   -$56.25
17:30  DALTON_EDGE  LONG 7671.25  גיל-השפל=1  → נכנסה   → סטופ 17:55  -$200.00
מופעי "extreme too fresh" בין 17:20 ל-17:39:  אפס
```
שתי סיבות, ושתיהן מתוקנות כאן: החוסם יושב **בתוך `detect_touch2`** ולכן לא ראה את
`DALTON_EDGE`; וגם על touch-2 הוא מדד על **חלון-120-ברים** (כולל לילי) ולא על ה-RTH.

## מה לבנות — בדיוק זה

### 1. להוציא את הכלל מהגלאי
ב-`backend/v9/systems/ceiling_touch2.py`: **למחוק** את בלוק `TOUCH2_EXTREME_AGE_V1`
(שורות ~254-280, כולל ה-`logger.info` שלו). הגלאי חוזר להיות גלאי בלבד.

### 2. להכניס אותו לשער, כשער אחד לכולם
ב-`backend/v9/gateway/trading_gateway.py`, בתוך `_route_setup_inner`, **אחרי** בלוק-דלתון
(‏אחרי T-355, לפני `§5a`):

```python
# ── T-366: fresh-extreme gate — one rule, every producer ──────────────
# Michael 14.09: "לא להיכנס בסוף העלייה ואז ככה נכשלת". Doctrine, not a
# tuned edge. Superseded the per-detector TOUCH2_EXTREME_AGE_V1.
if os.getenv("FRESH_EXTREME_GATE_V1", "1").lower() in ("1", "true", "yes"):
    try:
        _fx_min = int(os.getenv("FRESH_EXTREME_MIN_BARS", "3") or "3")
        _fx_dir = (setup.get("direction") or "").upper()
        # RTH bars of TODAY only, closed strictly before the current bar.
        _fx_rows = _fx_read_rth_bars_today()      # ↓ סעיף 3
        if len(_fx_rows) >= _fx_min + 1:
            _fx_prev = _fx_rows[:-1]              # בלי הבר הנוכחי — אפס מבט-קדימה
            if _fx_dir == "LONG":
                _fx_ext = min(r["low"] for r in _fx_prev)
                _fx_idx = max(i for i, r in enumerate(_fx_prev) if r["low"] == _fx_ext)
            else:
                _fx_ext = max(r["high"] for r in _fx_prev)
                _fx_idx = max(i for i, r in enumerate(_fx_prev) if r["high"] == _fx_ext)
            _fx_age = (len(_fx_prev) - 1) - _fx_idx
            if _fx_age < _fx_min:
                result["blocked_by"] = "fresh_extreme"
                result["reason"] = (
                    f"{_fx_dir} against a session extreme set {_fx_age} bars ago "
                    f"(min {_fx_min}); extreme={_fx_ext:.2f}")
                logger.warning(
                    "[Gateway] T-366 BLOCKED fresh_extreme: %s %s entry=%s "
                    "extreme=%.2f age=%d < %d",
                    setup.get("classification"), _fx_dir,
                    setup.get("entry_price"), _fx_ext, _fx_age, _fx_min)
                return result
    except Exception as _fx_err:
        logger.warning("[Gateway] T-366 fresh-extreme gate errored (fail-OPEN): %s", _fx_err)
```

**‏`fail-OPEN` בכוונה:** שער-בטיחות שקורס לא יַשבית מסחר. זה ההפך מ-`dalton_intent`
שהוא fail-closed, ומותר — כי הכלל הזה **רק חוסם**, הוא לעולם לא מאשר.

### 3. קורא-הברים
פונקציית-עזר באותו קובץ, RTH של **היום** בלבד, ממוינת עולה:
```sql
SELECT high, low FROM v9_bars_5min_woodies
WHERE (ts AT TIME ZONE 'Asia/Jerusalem')::date = (now() AT TIME ZONE 'Asia/Jerusalem')::date
  AND (ts AT TIME ZONE 'Asia/Jerusalem')::time >= '16:30'
ORDER BY ts
```
ב-`fwd_harness` השעון מוקפא ולכן `now()` שגוי — **לקחת את התאריך/שעה מ-`cross_context`
אם קיים שם `bar_ts`/שעון-הרנס, ואחרת מ-`now()`.** אם אי-אפשר לקבוע את היום ⇒ fail-OPEN.

### 4. דגל
`FRESH_EXTREME_GATE_V1` — **ברירת-מחדל `1` בקוד** (דלוק). `FRESH_EXTREME_MIN_BARS=3`.
ב-`RULED_FLAGS.yaml`: `expected: "unset_or_1"` אם הערך נתמך, ואחרת `'1'` **ולהוסיף ל-`.env`**
`FRESH_EXTREME_GATE_V1=1` + `FRESH_EXTREME_MIN_BARS=3` (זו התוספת היחידה ל-`.env`).
**למחוק מ-`.env` את `TOUCH2_EXTREME_AGE_V1` ו-`TOUCH2_MIN_EXTREME_AGE_BARS`** ואת
שורותיהם ב-`RULED_FLAGS.yaml` — הם הוחלפו.
**לפני עריכת `.env`: `bash scripts/mems26_snapshot.sh "t366-fresh-extreme"`.**

## golden (שורות גולמיות בדיווח)
- **ט1 · היום:** ריפליי על `2026-09-14` ⇒ `17:25 FLOOR_TOUCH2 LONG 7671.25` **וגם**
  `17:30 DALTON_EDGE_LONG 7671.25` מקבלים `blocked_by=fresh_extreme`. להדביק את שתי שורות-השער.
- **ט2 · הכלל חל על מפיקים שונים:** למנות כמה `blocked_by=fresh_extreme` יש ב-5 סשני-הבסיס,
  **מפולח לפי `classification`** — חייבים להופיע לפחות **שלושה שמות-תבנית שונים**. אם רק אחד ⇒
  השער לא באמת כללי ⇒ **NOT-DONE**.
- **ט3 · 08-03:** ששת השורטים שנכנסו מיד אחרי שיא חדש נחסמים.
- **ט4 · אפס מבט-קדימה:** מבחן שמזין סדרה שבה הקיצון האמיתי נמצא **אחרי** בר-ההחלטה
  ומוודא שהוא לא נספר.
- **ט5 · כתיבות:** הרנס ×5 + `--restart-at 18:29`. **מותר** שכתיבות ייעלמו (זה שער חוסם);
  **אסור** שתיווסף כתיבה. לפרט כל כתיבה שנעלמה עם השרשרת שלה.
- **ט6 · `T-335`=0 · `Traceback`=0 · `flag_guard` rc=0 · `guard_tests` rc=0.**
- **ט7 · מבחן `test_fresh_extreme_gate.py`:** לונג בשפל-טרי ⇒ חסום · לונג בשפל-ישן ⇒ עובר ·
  שורט בשיא-טרי ⇒ חסום · פחות מ-`K+1` ברים ⇒ עובר (fail-open) · חריגה בקריאת-DB ⇒ עובר.

## דיווח
קומיט אחד · `TASK_LOG` (T-366) + `STATUS_BOARD` באותו קומיט · LOG חתום עם ט1–ט7 ·
ואז **"סיים T-366"**. **אל תריץ ריסטארט** — מייקל ואני מחליטים מתי.
