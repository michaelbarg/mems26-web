# CC — ניקוי-מאסטר: תעשה את זה כמו שצריך (מייקל 2026-07-22 לילה)

**מייקל:** *"אפשר לטפל בקלוד-קוד ולנקות את המערכת כמו שצריך."* **cc-macbook הבעלים המלא של הניקוי.**
המערכת **בסים** (MEMS26_MODE=sim, is_sim=1) — מותר לירות/לתקן. cowork עבר לאימות-סימטרי בלבד (חוק-5). cursor מאמת.
**כלל-ברזל:** תחנה-אחת-בכל-פעם · לכל תיקון פקודה+פלט-גולמי · שינוי-התנהגות=דגל+טסט · **סעיף NOT-DONE** בסוף כל תחנה ·
שורת-LOG חתומה. **אין "סיימתי" בלי שהרצת את השער של אותה תחנה.** אל תעבור הלאה עד ירוק.

## מצב-פתיחה (אומת cowork עכשיו)
- רגרסיות: **12 failed / 136 passed** (parent 5614c035 = **145/0** — היעד).
- DB: **בריא** (0 blocked · 0 idle-in-txn · `pnl_sierra` קיים → migration 023 בוצעה בעקבות שחרור-ה-wedge של cowork).
- זיהום: 0 זוגות-רפאים כרגע (התיישנו בגלגול-יום) — **אבל המנגנון עדיין דלוק** (`WOODIES_TS_HOUR_FIX` לא =0 בתהליך הרץ).

---

## תחנה 1 — 🔴 רגרסיות → 145/145 (השער הראשון, שום דבר אחר עד שזה ירוק)
**השורש (cowork מצא, חוק-5):** כל 12 הכשלים מחזירים את אותו ערך — **"Trend_Normal"** (התווית-החיה של היום).
הטסטים מגיעים ל-`backend.main` **האמיתי-הרץ** `app.state.day_type_machine` במקום ל-mock שלהם. הוכחה: כל קובץ
**עובר לבד** (42 passed), נכשל רק בחבילה, וגם בלי קבצי-הטסט שלך → **קוד-פרודקשן** מזליג, לא הטסטים.
**המקור בקוד שלך (c556a5bf):** ה-demotion **מְשַׁנֶּה מכונה-משותפת** —
`day_type_machine.day_type = _dem_enum` + `_last_state.day_type = _dem_enum` (P6a), וה-boot-seed מייבא/נוגע
ב-`backend.main` בזמן-טסט. **התיקון (בידוד, לא פר-טסט):** (א) fixture autouse שמשחזר `day_type_machine` (או
מסיר `backend.main` מ-sys.modules) בין-טסטים · ו/או (ב) שה-demotion/boot-seed לא ייגעו במכונה-חיה תחת טסט
(הזרקה/דגל-בדיקה). **הרץ:** `BRIDGE_TOKEN=test pytest -k "boot or demotion or daytype or decisions or order_fail" -q`
→ **חייב 145 passed / 0 failed. הדבק את הפלט המלא.** (cowork ניסה import_module — לא עזר, הוחזר.)

## תחנה 2 — 🔴 זיהום-TS: שורש אמיתי, לא band-aid
**cursor+cowork אישרו:** הכפילות +1h נוצרת בקליטה (`_hour_shift_fix`, bars.py:~460). **אבל (הסתייגות-cowork,
חובה לסגור):** מדדתי חותמת-ייצוא-גולמית **‎−5h** מ-wall-clock. `WOODIES_TS_HOUR_FIX=0` מסיר כפילות **אבל
עלול להשאיר ברים ב-‎−1h**. **חובה בסים:** אחרי =0+restart, אמת ש**בר-טרי נוחת ב-ts הנכון (≈0), לא ‎−1h**
(`select max(ts), now()-max(ts) from v9_bars_5min_woodies`). אם ‎−1h → תקן את ה-offset בקליטה/bridge (‎+5h/TZ-נגזר)
ופרוש את hour-fix. אחרי-נקי: מחק זוגות-רפאים היסטוריים (גיבוי קודם, ודא שהבר-האמיתי קיים בסלוט).

## תחנה 3 — 🔴 VA מזוהם (cursor f5a087d5): backend מחשב TPO מחדש מברים-מזוהמים ומתעלם מ-Sierra
**התיקון (Rule 1):** קרא VA קנוני מ-`tpo.json`/`v9_tpo_sessions` **כמו שקוראים IB** — אל תחשב-מחדש בבקאנד.
אימות: VA היום ≈ 15-30pt (לא 3.5).

## תחנה 4 — 🔴 שורש-עמוק: ה-backend מדליף idle-in-transaction (גרם ל-wedge של 95 דק')
נתיבי-קריאה חייבים autocommit (`backend/v9/db/read.py`), לא `BEGIN;SELECT;<idle>`. זה חוסם-לייב אמיתי שיחזור.
מצא את הנתיב שמשאיר txn פתוחה ותקן. (cowork שחרר את ה-wedge; השורש שלך.)

## תחנה 5 — הדלקה + אימות-סים (רק אחרי 1-4 ירוקים)
`WOODIES_TS_HOUR_FIX=0` (RULED) · `DAYTYPE_ACCEPTANCE_DEMOTION_V1=1` · `DAYTYPE_BOOT_SEED_CANONICAL_V1=1`
ב-.env → flag_guard PASS → restart → **אימות-התנהגות בסים פר-דגל** (לא רק טסט-יחידה):
demotion על ברי-07-22 (Trend→Variation), counter על **07-16** (Trend אמיתי, לא-יורד — תיקון מייקל: 07-21 היה Variation),
boot-seed נותן תווית-קנונית אחרי restart, order_failed מוצג נכון, decisions שורד-restart.

## תחנה 6 — FAULTS_AND_FIXES: כל שורה → "✅ sim-verified" (לא "✅ code")
עדכן את `docs/reports/FAULTS_AND_FIXES_2026-07-22.md` — cowork מאמת כל שורה סימטרית לפני שהיא סגורה.

## מה **לא** עכשיו (אחרי הניקוי + פסיקת-מייקל)
ארכיטקטורת S1=מוח/S2+S4=זרועות + זיהוי-מודע-מיקום + opening-מניע-ירי — **מתועד** (`CURSOR_VERIFY_CONTAM_AND_S1_ARCH_REPORT`),
בנייה רק אחרי מערכת-נקייה + פסיקה.

## סדר: 1(שער) → 4 → 2 → 3 → 5 → 6. **כל-ירוק = חזרה-ללייב מיידית** (מייקל: בלי זמן-המתנה; הפסיקה נתונה).
