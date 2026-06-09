# CC — מגה-פרומפט חקירה (לא תיקון): נושא-הסטופ + 4 הבאגים (2026-06-08) [נפרד]

פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md` + `CC_VERIFICATION_PROTOCOL.md`. **קרא קודם:** `CLAUDE.md` (§Standing Decisions · §Chop Gates · §S2⟂S3).
**נפרד** מ-`CC_COMBINED_DETECTION_FIX_AND_SHADOW_2026-06-08.md`.

> ## ⛔ זה פרומפט-חקירה בלבד — אל תתקן עדיין
> Michael: "תן ל-CC לחקור את נושא-הסטופ ולהציג אסמכתאות → אז נתקן." **אסור לגעת בקוד.** התוצר = **חבילת-ראיות**
> (file:line · git-blame · לוגים גולמיים · ערכים מחושבים · ציטוט-spec) שתימסר ל-Cowork לביקורת. אחרי אישור-Cowork +
> Michael → נשלח פרומפט-תיקון נפרד. כל טענה = **אסמכתא גולמית**, לא הסקה. אל תדליק שום דגל default-off.

═══════════════════════════════════════════════════
## 🎯 חקירה ראשית — נושא-הסטופ (S4, באג #1 + מערכת-הסטופ כולה)
═══════════════════════════════════════════════════
רקע מאומת (Cowork): `woodies_system.py:320,332` (DLL-fallback ל-ZLR/HFE) מעבירים `stop=None`; `schemas.py:78` `stop: float`
(לא-Optional) → ValidationError → `process_bar` קורס → כל S4 מת. קורס בדיוק כש-`zlr_detected`/`hfe_detected` → 3 ה-ZLR.

**חקור והצג אסמכתאות (בלי לתקן):**
1. **כל מקורות-ה-stop ב-S4** — מַפֵּה כל מקום שבו נקבע `stop` ל-PatternResult: ה-DLL-fallback (`:317-332`) + כל detector
   (`patterns/*.py` — `compute_stop` / `compute_stop_v2`). טבלה: תבנית · קובץ:שורה · איך stop מחושב · מתי הוא None/0.
2. **למה `compute_stop_v2` עלול להחזיר None/להיכשל** — קרא `atr_stop.py` (`compute_stop`, `compute_stop_v2`) + `config/stop_anchors.yaml`
   + resolver. מתי ATR=0 / cfg=None / anchor חסר? הדבק את הקוד + תרחיש-הכשל. האם הוא נופל-חזרה ל-legacy או מחזיר None?
3. **מה ה-stop הנכון ל-DLL-ZLR לפי ה-spec** — צטט את ה-spec/SPEC-xlsx/`STOP_ANCHOR_DECISIONS` לסטופ של ZLR/HFE (anchor + offset).
   מה ה-stop **היה צריך** להיות ב-3 ה-ZLR של היום (חשב מהנתונים: entry=wb.close, CCI, ATR). הצג מספרים.
4. **היסטוריית ה-schema** — `git blame schemas.py:78` + `git log` סביב `9532205..2af98be` (V2): מתי `stop` הפך non-Optional,
   ומתי ה-`stop=None` ב-DLL-fallback נוסף (06-01?). קבע: האם V2 הפך None-רדום ל-crash, או שזה קדם ל-V2.
5. **הוכח את הקריסה בדאטה** — הדבק את שורת ה-ERROR הגולמית מהלוג (`process_bar error: ... PatternResult ... stop ... None`)
   + חותמת-הזמן, מול חותמות-ה-ZLR ב-`~/SierraChart_Data/v9_export/`.
6. **הצע (בלי לבצע)** 2-3 חלופות-תיקון עם trade-offs: (א) חישוב-stop אמיתי ל-DLL-fallback · (ב) `Optional[float]`+טיפול-צרכנים ·
   (ג) graceful-skip. ⚠️ הראה למה `stop=0.0` שגוי (stop במחיר 0 → R:R זבל → ייחסם ב-`r_t1_gate`).

═══════════════════════════════════════════════════
## חקירות משניות (אותו עיקרון — ראיות, לא תיקון)
═══════════════════════════════════════════════════
**באג #3 (S2 detection בר-חלקי):** הוכח עם **לוג-חי** ש-b4 חלקי ב-push-ראשון (OHLC+vol ב-detection מול הסופי).
מַפֵּה `five_min_system.py:874-886 → :917 → :532`. הצג את הפער engine↔inspector (`s2_pattern_probe:81`) על אותו בר בדאטה.
הצע את התיקון (`buffer[:-1]`) + 4 התנאים — **בלי לבצע**.

**באג #2 (S2 DB persist):** הדבק את שורת-השגיאה הגולמית + `five_min_system.py:1132` (`fromtimestamp(bar.get("ts"))`).
הצג איך `woodies_system.py:206-221` כבר מטפל ב-ts-string נכון (הפניה). הצע parse-עמיד — בלי לבצע.

**באג #4 (Woodies DB write ts):** הדבק שורת-השגיאה הגולמית (`safe_writer ... timestamp with time zone ... integer`).
מַפֵּה איפה epoch-int נכתב. בדוק אם `safe_writer` משרת טבלאות נוספות (סיכון-רוחבי). הצע — בלי לבצע.

## תוצר (חבילת-ראיות ל-Cowork)
מסמך אחד: `docs/reports/STOP_AND_BUGS_INVESTIGATION_2026-06-08.md` עם, לכל פריט: **שורש (file:line) · אסמכתא גולמית
(לוג/git-blame/ערך-מחושב/ציטוט-spec) · חלופות-תיקון + trade-offs**. בלי קוד-שונה. בלי דגלים.

## Acceptance (✓/✗) — חקירה בלבד
- [ ] טבלת מקורות-stop S4 + תרחיש-כשל compute_stop_v2 (קוד מודבק).
- [ ] ה-stop הנכון ל-3 ה-ZLR לפי spec + מספרים מחושבים.
- [ ] git-blame schemas.py:78 + ציר-זמן V2↔stop=None.
- [ ] ERROR גולמי לכל באג + חותמות-זמן מול Sierra export.
- [ ] לוג-b4 חי (#3). חלופות-תיקון לכל באג עם trade-offs.

## NOT-DONE + מה Cowork יבקר
**אסור קוד-שונה בסבב זה.** Cowork יצליב (Rule 5): שכל שורש מגובה אסמכתא-גולמית (לא הסקה) · שה-stop-הנכון תואם spec ·
שחלופות-התיקון לא כוללות `stop=0.0` תמים · ש-git-blame אכן מראה את מקור-ה-crash. אחרי אישור → פרומפט-תיקון נפרד.
