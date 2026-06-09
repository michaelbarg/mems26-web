# CC ROUND-2 FIX PROMPT — Phase 0 gaps (Cowork independent verification, 2026-06-02)

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.** אוטונומי, ללא עצירה לאישור. הפק דוח בסוף.

**רקע:** Phase 0 (commit `9a5ed5d`) דווח "DONE/87-87" אך אימות Cowork בלתי-תלוי מצא **over-claim** ב-2 פריטים + טסט חסר. סגור את הפערים. אל תיגע במה שכבר תקין (A1 tick_reversal early-return — מאומת נכון).

---

## 🔴 FIX-1 (P0, פונקציונלי) — B1 partial-wiring: האתר השני לא קיבל bypass
**ראיה (grep):** `five_min_system.py` — bypass קיים רק ב-**536-537** (אחרי האתר הראשון, 531). האתר השני **625** (`lookback_quiet = (...) if b1_vol > 0 else False`) **אין** bypass אחריו, וה-gates ב-**631** ו-**645** עדיין דורשים `lookback_quiet` → נתיב-התבנית השני של S2 **עדיין חסום** כש-VSA ON.

**תיקון:** מיד אחרי ההשמה ב-625 (לפני ה-gates ב-631/645), הוסף את **אותו** bypass כמו ב-536-537:
```python
if S2_VSA_VOLUME:            # אותו דגל call-time כמו האתר הראשון (498)
    lookback_quiet = True    # B1: VSA gate sufficient — Michael approved 2026-06-02
```
ודא ש-`S2_VSA_VOLUME` זמין בסקופ הזה (אם החישוב ב-498 מקומי לפונקציה אחרת — חשב אותו שוב call-time: `_os.environ.get("S2_VSA_VOLUME","").lower() in ("1","true","yes")`, או עדיף `flag("S2_VSA_VOLUME")`).

**Acceptance:**
- [ ] grep `lookback_quiet = True` → **2** מופעים (אחרי 531 ואחרי 625). הדבק. ✓/✗
- [ ] טסט אנטי-טאוטולוגי שמכסה את **שני** הנתיבים (ראה FIX-3). ✓/✗

## 🔴 FIX-3 (P0, חוזה) — טסט ל-B1 (חסר לגמרי)
**ראיה:** diff של `9a5ed5d` נגע רק ב-3 טסטי S4 קיימים. אין טסט ל-bypass של B1.
**תיקון:** הוסף טסט שמייבא וקורא ל-`five_min_system` האמיתי (לא העתק לוגיקה), על נתוני ברים שבהם `lookback_quiet` הטבעי = False:
- `S2_VSA_VOLUME` OFF → ה-setup **נחסם** (lookback אוכף) בשני הנתיבים.
- `S2_VSA_VOLUME` ON → ה-setup **לא נחסם** בגלל lookback בשני הנתיבים.
- שורת ליטמוס חובה: *"if reverted (הסר את ה-bypass) → RED because setup blocked by strict lookback_quiet"*.

**Acceptance:**
- [ ] טסט ירוק; revert ה-bypass → RED (הדבק את שתי הריצות). ✓/✗

## 🟡 FIX-2 (P1, correctness + honesty) — D1 לא הושלם
**ראיה (grep):** רק `trend_relabel.py` משתמש ב-`flag()`. עדיין מיובאים כקבועים **קפואים ב-import**:
`S2_ATR_RELATIVE` (`five_min_system.py:40` + `patterns/head_shoulders,flags,double_bt`, `sr_proximity`, `adaptive_stop`, `quality_tier`) · `S3_RELATIVE` (`detectors.py:6`, `stacked_imbalance.py:24`) · `S3_MUTE` (`footprint_system.py:437`) · `FOOTPRINT_DISABLED` (`footprint_system.py:154`) · `S1_IB_WIDTH_ATR`,`S1_DAYTYPE_STAGING` (`day_type/detector.py:36`) · `S1_CVD_OPENING` (`detector.py:202`).
גם `atr.py:99,103` (`X = flag("X")` ברמת מודול) עדיין **קפוא ב-import** — הקריאה ל-`flag()` בזמן import לא פותרת כלום.

**תיקון (בחר אחד, ותעד מפורשות):**
- **(א) השלם:** המר את **כל** האתרים לעיל לקריאת `flag("NAME")` ב-call-time (בתוך הפונקציה/הענף, לא ברמת מודול). הסר/השאר את הקבועים ב-`atr.py` אך ודא שאף צרכן לא מסתמך על ערך-import קפוא.
- **(ב) דחה ביושר:** אם לא מבצע — **תקן את הדיווח**: שנה את הטענה ל-`A3/D1 = PARTIAL (רק trend_relabel + tick_reversal הומרו)`, ותעד שזה latent בלבד כי ה-plist מייצא את כל הדגלים לפני python (frozen value נכון בהפעלה), הסיכון רק ב-flip-בזמן-ריצה.

**Acceptance:**
- [ ] (א) grep → 0 ייבואי-דגל קפואים שנותרו, **או** (ב) הדיווח עודכן ל-PARTIAL עם הנימוק. הדבק. ✓/✗

---

## דוח (חלק C)
טבלת FIX · Status · Evidence(command+output) · *"if reverted → RED"* לכל טסט · NOT-DONE · האם זה משנה את מסקנת Phases 1-3 (אם כבר רצו עם B1 חלקי — לציין שצריך re-verify של S2 firing אחרי FIX-1).

## אסור לגעת
Invariants מהפרומפט הראשי (get_db lock · integrity backend-כבוי · Sierra SoT · B2/B3 · risk surface).
