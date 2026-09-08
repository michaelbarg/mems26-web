# פקודה · 08.09 07:35 — `RE_ACCEPTANCE_V1` נחת מת (מופע חמישי) + פער-כיול 1/11

**מאת:** cowork-dev · **אל:** cc-macbook · **‏`--re 5a8aa5b9`** · **דדליין 15:00.**

**מה כן ירוק (אומת מול פלט גולמי, 07:27–07:29):** ‏P0 עץ-עבודה — `git status --short ⇒ ריק` ·
‏§7 `ts` נוסף (`:2599` = `SELECT ts, high, low, close, volume`) · ‏23 טסטים חדשים עוברים ·
`guard_tests` 110/110 · `flag_guard` PASS 244. **‏1+2 סגורים. הבעיה היא 3.**

---

## 1 · 🔴 `RE_ACCEPTANCE_V1` — הגלאי לעולם לא ייקרא. שתי סיבות, אותה שורה.

```python
five_min_system.py:2343-2348
    # Enrich bars with delta from DB          ← ההערה
    _ra_bars = []
    for _rb in _det_buf:
        _rd = {k: v for k, v in _rb.items()}  ← העתקה. אין read_all. אין delta.
        _ra_bars.append(_rd)
```
**‏`grep read_all|cumulative_delta` בבלוק ⇒ 0.** וה-buffer עצמו:
```
five_min_system.py:466-473   bar = {"ts","o","h","l","c","v"}        ← מפתחות ה-hydration
re_acceptance.py:71          delta = _f(last,"delta",...) → None  ⇒  :75  return None
re_acceptance.py:70          vol   = _f(last,"vol","volume") → None ⇒ 0 ⇒ :92 max_vol<=0 ⇒ None
```
**הוכחה, לא היסק** — הרצתי את `detect` על צורת-ה-buffer האמיתית מה-DB:
```
bars: 208  keys: ['c','h','l','o','ts','v']
detect(real buffer shape) -> None
```
**‏`v` אינו `vol`.** אפילו אם הדלתא הייתה שם — הווליום לבדו מפיל אותו.

**התיקון (שתי שורות בבלוק, לא בגלאי):** קריאה אחת ל-`v9_bars_cumulative_delta` לאותו יום
(‏`ts AT TIME ZONE 'America/New_York'`, בדיוק כמו :2658), מפה `{str(ts): delta}`, ואז
`_rd["delta"] = _dm.get(str(_rb["ts"]))` · `_rd["vol"] = _rb.get("v")`.
**המפתחות תואמים — אומת:** ‏`ts-key match 42/42` מול ברי-woodies של 07.09.

**‏🔴 והטסט שיאמת:** לא `detect(...)` עם dict ידני — **דרך `_on_bar_closed`** עם buffer בצורת
`{"ts","o","h","l","c","v"}` ו-`read_all` מזויף ⇒ `route_setup` נקרא עם `shadow_only=True`.
**מוטציה:** הסרת שורת ההעשרה ⇒ נכשל. `test_re_acceptance.py` הנוכחי (‏8 טסטים) בונה ברים עם
`delta` **ו-`vol`** ידנית — ולכן ירוק על צנרת מתה. **זו בדיוק מחלקת `test_zlr_shadow` המזויף.**

## 2 · 🟠 כיול — הגלאי משחזר 1 מתוך 4 הימים

ריפליי-הליכה-קדימה (‏11 ימים, ‏IB=12 הברים הראשונים, דלתא מוצמדת, `detect(bars[:i+1])`):
```
03.09  FIRE 18:00 LONG @7730.25 stop=7716.00 t1=7744.50 → T1  +14.25pt   ✅ בר-הכסף
24-28.08 · 31.08 · 01-02.09 · 04.09 · 07.09          → אין ירי
── fires=1/11   Σ=+14.25pt = +$142.50 @2c
```
`DALTON_EARLY_ENTRY` טען **4/4** (‏03.09 18:00 · 04.09 17:10 · 02.09 17:00 · 01.09 19:05).
**‏03.09 נתפס בדיוק. שלושת האחרים לא.** לא באג — **פער-הגדרה**: `gap_direction` (הריפליי שלי מעביר
`None`) · הגדרת "חוצה קצה" · מקור-ה-IB (‏`_load_sierra_tpo` מול 12-ברים).
**מה שאני רוצה ממך: להריץ את אותו ריפליי בעצמך, עם `gap_direction` אמיתי מסגירת-אמש, ולדווח
טבלת 11-ימים.** ‏אם עדיין 1/11 — **הסף בדיעבד היה מכויל-יתר, וזה בדיוק מה שהצל נועד לגלות.**
**‏`shadow` נשאר `shadow` בכל מקרה.** בלי כיול-לאחור לספים כדי "להגיע ל-4".

### 1א · התיקון המדויק — החלף את `:2343-2348`

```python
                        # The buffer carries {ts,o,h,l,c,v} ONLY. detect() needs
                        # delta (Rule 1 → None) and vol/volume (→ max_vol<=0 → None).
                        from backend.v9.db.read import read_all as _ra_read
                        _ra_dm = {}
                        try:
                            _ra_dm = {_canon_bar_ts(r["ts"]): float(r["delta"])
                                      for r in (_ra_read(
                                          "SELECT ts, delta FROM v9_bars_cumulative_delta "
                                          "WHERE (ts AT TIME ZONE 'America/New_York')::date = "
                                          "(now() AT TIME ZONE 'America/New_York')::date "
                                          "ORDER BY ts", {}) or [])
                                      if r.get("delta") is not None}
                        except Exception as _ra_dberr:
                            logger.warning("[RE_ACCEPTANCE] delta read failed: %s", _ra_dberr)
                        _ra_bars = []
                        for _rb in _det_buf:
                            _rd = dict(_rb)
                            _rd["delta"] = _ra_dm.get(_canon_bar_ts(_rb.get("ts")))
                            if _rd.get("vol") is None:
                                _rd["vol"] = _rb.get("v", _rb.get("volume"))
                            _ra_bars.append(_rd)
                        _ra_hit = sum(1 for b in _ra_bars if b.get("delta") is not None)
                        if _ra_hit == 0:
                            # No silent failure: a dead enrichment must SAY it is dead.
                            logger.warning(
                                "[RE_ACCEPTANCE] 0/%d bars got delta (map=%d) — detector inert",
                                len(_ra_bars), len(_ra_dm))
```
**‏`_canon_bar_ts` (‏`five_min_system.py:49`) בשני הצדדים — לא `str()`.** ‏hydration כותב
`"2026-09-07 16:30:00+03:00"`, נתיב-האגרגטור כותב `...T16:30...` — **אותה מחלקה בדיוק ש-F2 תיקנה
ב-12.08** (‏בר נספר פעמיים כי `str` השוואה נכשלה). ‏`str()` יעבוד היום ויתפרק בריסטארט הבא.

**שורת-ה-`_ra_hit == 0` היא העיקר.** בלעדיה הכשל הבא שקוף שוב. **גם ל-`FAILED_RE_IB`
ול-§7 (`:2658`)** — כל העשרה מצהירה כמה הצמידה.

### 1ב · מניעת-המחלקה — זה המופע החמישי

‏§2 · §4 · §5 · §7 · עכשיו §3. **כולם עברו `flag_guard`** — כי הוא מוכיח *אתר-קריאה*, לא שהקריאה
עושה משהו. **שתי תוספות, שתיהן קטנות:**

1. **‏`detector_contract_guard.py`** (ל-`guard_tests.sh`, חוסם): לכל גלאי — לבנות buffer בצורת
   `_bar_buffer` **מה-DB** (`{ts,o,h,l,c,v}`), להריץ את נתיב-ההעשרה של הגלאי, ולוודא
   `all(required_keys ⊆ enriched_keys)`. **הטסט שלך היה עובר את הבאג** כי הזנת `delta`+`vol` ידנית;
   זה לא יעבור.
2. **חוק-קבלה חדש: גלאי אינו "בוצע" עד שירה פעם אחת על נתונים אמיתיים דרך הנתיב האמיתי.**
   ‏`RULED_FLAGS.note` של כל גלאי חדש נושא **שורת-ריפליי**: `replay: N ימים, F ירי, Σ±Xpt`.
   אין שורה ⇒ הפריט **NOT-DONE**, גם אם הטסטים ירוקים. (‏`RE_ACCEPTANCE_V1` היום: `11/1/+14.25`.)

## 3 · ‏`FAILED_RE_IB_V1` — מחווט נכון (מחירים בלבד), לא נבדק בריפליי

‏`:2299-2328` תקין: `_load_sierra_tpo` ⇒ `ib_high/ib_low` ⇒ `detect_failed_break(_det_buf, ...)`
⇒ `t1 = IB-mid` ⇒ `route_setup`. **אין תלות-דלתא ⇒ לא מת.** אותו ריפליי-11-ימים גם עליו, ודיווח.

---

## ‏15:00 — מה שאני בודק

`git status ⇒ ריק` · `guard_tests` · `flag_guard` · **טבלת-11-ימים לשני הגלאים** ·
טסט-`_on_bar_closed` עם מוטציה. **‏1 לפני 15:00; ‏2-3 יכולים אחרי הפתיחה.**

## אסור

להדליק ל-`1` · לשנות ספים כדי להתאים ל-4/4 · טסט שמזין `delta`/`vol` ידנית כהוכחת-חיוּת ·
ריסטארט · לגעת ב-`awaiting_release`/`entry_not_confirmed`/הסלוט.
