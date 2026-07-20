# CURSOR — תדריך מלא: כל מה שנאמר בסשן הזה (מייקל 2026-07-20)

**קרא זאת ראשון.** זה מאחד את כל השיחה של היום למקום אחד. הפירוט-הפעיל בשלושת המסמכים הנלווים
(§10). מייקל: *"תכין לקורסור הסבר של כל מה שנאמר כאן."*

---

## 1. מה קרה היום (יום-לייב-אמת ראשון, שני)
- המערכת **כן סחרה**: **2 עסקאות לייב בבוקר** (#420, #424) — שתיהן נעצרו בסטופ. אלה היו הסטופים-הקרובים
  (בתוך-המבנה) מלפני התיקון.
- שני ההפסדים הרצופים הפעילו את חוק **STOP-DAY (2 הפסדים רצופים = עצירת-יום)** → כל 9 ה-setups שאחריהם
  נותבו ל-**shadow בלבד** (כולל מנצחים שהוחמצו: שורט-S4 ‎+57.50 ועוד).
- מייקל תוסכל: כל התיקונים וההכנות ליום-המסחר "נכשלו" בלייב, והחשש שלא יהיו שם מחר.

## 2. השורש למה "אין עסקאות" (אובחן עם נתונים, לא מהזיכרון)
1. ה-backend החי (PID 10107) עדיין אכף STOP-DAY — **התיקון שלי (`consec=0`) לא נטען בו**.
2. למה: קומיט התיקון `69ed87b4` ב-**13:54 ET**, אבל ה-restart האחרון היה ב-**13:51 ET** — 3 דק' *לפני*.
   התהליך רץ קוד/env ישן. (זה בדיוק כשל-ה"בוצע≠מאומת-בריצה" — ראה §8 מנוף 2.)

## 3. מה תוקן וחי עכשיו (מאומת — Rule 5)
- **restart בוצע באישור מייקל:** `launchctl kickstart -k … com.mems26.backend` → PID 10107→**37216**, health ok.
- **STOP-DAY כבוי** — אימות עם `.env` טעון: `CONSECUTIVE_LOSS_LIMIT=0 → STOP-DAY active? False`.
  `cap=800 · cutoff=15:00 ET · max=999`. יום=Variation שוחזר. **לייב חזר לנתב.**
- אין עסקה פתוחה במערכת (הכל CLOSED) בזמן ה-restart.

## 4. הכרעת-הדגלים + מקרא (מסמך `docs/FLAG_RULING_2026-07-20.md`)
- **`flag_guard.py` PASS — כל 101 הדגלים המוסדרים = `.env` החי.** ההכרעה קיימת ונאכפת.
- מקרא-קריא ב-6 קבוצות: לייב · נכונות-Dalton · שערי-סוג-יום · סיכון · שבור-אל-תיגע · פתוח-להכרעה.
- ⚠️ **ממצא:** `STOP_WINDOW_COMPLETED_V1=1` ב-`.env` אבל FLAG_INDEX מסמן **"not built"** → אולי **אינרטי**
  (אשליית-דגל). **אמת: נצרך-בקוד או מת-חיווט? אם מת — או לבנות או להסיר מ-`.env`.**

## 5. פער §0 — למה cursor ראה "10 passed" ו-cowork ראה "5 failed"
- **cursor הריץ בלי `.env`** (ברירות-מחדל-קוד) → cowork עם `.env` → **סדר-שערים שונה** → blocked_by שונה
  (`cont_trend_filter`≠`pattern_loss_breaker` · `zone_limit_late_entry`≠`duplicate_fire`).
- **המסקנה:** בלי `.env` בודקים **מערכת פיקטיבית**. **כל הטסטים חייבים לטעון את הסט המוסדר** (§4) או לנעול
  דגלים ב-fixture. הרץ מחדש → הדבק פלט-גולמי. אם עדיין נכשל = סדר-שערים אמיתי לתקן.

## 6. המנדט שלך (מסמך `CURSOR_TAKE_COMMAND_SYSTEM_VERIFY_2026-07-20.md`)
מייקל: *"אני לא מרוצה מ-cowork. cursor ייקח פיקוד, יעבור על כל המערכות, וביחד נעבור אחד-אחד ונראה
שהמערכת עובדת תקין. הרץ עם המודל החזק שלך."*
- **אתה מוביל.** cowork = תומך-מאמת בלבד (מריץ שאילתות/טסטים לבקשתך, מאמת טענותיך סימטרית).
- סדר: §0 (פער-הטסטים) → §1 מערכת-אחר-מערכת (פיד · סוג-יום · S2 · S4 · שערים · סיכון · ניתוב-לייב ·
  ביצוע · רקונסיליאציה · אורפנים · פרונטאנד).

## 6b. ⭐ מקור-האמת של כל מערכת (גש לכאן לפני אימות כל מערכת)
מייקל: *"אני רוצה שתפנה אותו למקור-האמת של כל אחת מהמערכות."* **המפות הקנוניות (קרא ראשון):**
`docs/SOURCE_OF_TRUTH.md` (איזה מקור-נתונים חי לכל אות) · `docs/spec_authority/S1_ACTIVE_CANONICAL.md`
(איזה מנוע-סוג-יום פעיל/מת) · `SYSTEM_INDEX.md`+`_INDEX.md` (איפה הקוד) · `docs/FLAG_INDEX.md` (מצב-דגלים) ·
`docs/SYSTEM_MANIFEST.md` (כל המשטחים כולל חוץ-git). **כלל-Rule-2: אמת שהשורה-האחרונה של מקור טרייה לפני
שסומכים עליו.**

| מערכת | קוד קנוני | נתון-חי קנוני | 🔴 מקור-מת (אל תיגע) |
|---|---|---|---|
| ברים 5-דק' / CVD | `direction_context_live._fetch_live_bars` | `v9_bars_5min_woodies` (רציף, live) · `v9_bars_5min` ל-delta (**עלול להיתקע/פער**) | `v9_bars_5min_continuous` (close=זבל) |
| סוג-יום (S1) | `systems/day_type/classifier_core.py::classify_session` | `GET /api/v9/day_type/classify_replay` (7-type, מאומת) · live-engine `app.state.day_type_machine`+`v9_day_type_state` (OLD 3-type) | `/api/v9/day_type/current` · `/v9/current` (מוחזר None) |
| כיוון | `direction_context_live.current()` | `GET /api/v9/day_type/direction_now` | — |
| רמות TPO (IB/VAH/POC/VAL) | — | `v9_tpo_sessions WHERE session_type='CASH'` (trading_date=VARCHAR→`.isoformat()`) | — |
| S2 (five-min) | `systems/five_min/five_min_system.py` | `v9_five_min_setups` | — |
| S4 (ZLR/HFE) | `gateway` + spec ZLR_V2 | `v9_bars_5min_woodies` (`zlr_detected`/`hfe_detected`) | — |
| שער/החלטות | `gateway/trading_gateway.py` | `blocked_by`+`reason` בהחלטה · `v9_trades` | — |
| סיכון | `gateway/risk_checks.py` | `docs/FLAG_RULING_2026-07-20.md` (flag_guard PASS) | — |
| ביצוע→Sierra | `services/sierra_command.py` (op=PLACE) | פקודות ל-Sierra | op=EXIT (שבור) |
| פוזיציה/רקונסיליאציה | `services/sierra_position_reconciler.py` | Sierra-חשבון-אמת (מקור-על) | — |
| P&L/fills (🔴 Task#6) | `services/sierra_ledger.py` · `api/v9/live_ledger_routes.py` | `trade_fills.json` (**ריק** → P&L מחושב לא-אמיתי) | P&L מחושב כ"אמת" |
| עסקאות | — | `v9_trades` (+`v9_trade_management_log`) | — |
| דגלים | `scripts/gen_flag_index.py` | `docs/FLAG_INDEX.md` · `config/RULED_FLAGS.yaml` | פרוזה/זיכרון ידני |
| פרונטאנד | — | `docs/handoff/FRONTEND_INDEX.md` | — |

**TZ:** חותמות נשמרות ב-**+03:00**; לזמן-מסחר `(ts AT TIME ZONE 'America/Chicago')`, RTH 08:30–15:00 CT.
(ה"+3 שעות" שראית ב-psql = תצוגת-TZ הזו, **לא** זיהום-נתונים.)

## 7. ארבע הכרעות פתוחות (קבוצה 6 — מייקל מכריע)
1. **`IB_BREAK_ANY_EXPANSION_V1`** → להדליק **מחר** (מסווג-יום-אוטומטי; מייתר override ידני שפג בחצות).
2. **`ORPHAN_AUTO_STOP_V1=0`** → **לולאת-האורפן**, התקלה המעגלית #1. ריפוי-אוטו או חסימה-קשיחה?
3. **`CONT_TREND_FILTER=1`** → דוקטרינה: מומנטום-רגעי מול כיוון-יום (שורט-עם-היום תוך באונס).
4. **`SYSTEM6_AUTOCORRECT=protective`** → מצב-הגנתי בלבד (מותר, פסיקת 07-15).

## 8. ⭐ איך שוברים את התקלות המעגליות (המטרה-העל של מייקל)
תקלות חוזרות באותם מקומות כי מתקנים **סימפטומים** ולא **סוגרים לולאות**. חמישה מנופים:
1. **מקור-אמת-יחיד נאכף** — רשומות↔Sierra כתנאי-ראשון. סטייה → חסימה-קשיחה או ריפוי, **לא** "מתריע+מחכה"
   (זה מבטיח חזרה — האורפן חזר 07-10/14/17/20). כולל P&L אמיתי מ-Sierra (Task#6, `trade_fills.json` ריק).
2. **"בוצע" = מאומת-בריצה, לא קומיט** — הוכחת-תהליך-חי (boot-line/probe עם env), לא hash. (כשל-היום.)
3. **טסט-נכונות על ברים-אמיתיים** — לא "נתונים זורמים". (הכנת-סופ"ש בדקה צינורות, לא Dalton-נכונות.)
4. **פחות חלקים-נעים** — שינוי-אחד-בסשן · אפס-wiring-חלקי · דיסציפלינת-restart (Task#8) · דגלים קפואים.
5. **שער-פתיחה קשיח** — אין ירוק (תיאום · פיד · סטופים · יום · flag_guard · iMac=Sim) → אין חימוש.

## 9. הכנות למחר
restart-בוקר **אחד נקי** שמדליק: מסווג-יום-אוטומטי (Task#5) + הידרציית-buffer (Task#8) + תצוגת-reason —
בלי override ידני. `snapshot` לפני · PRE_TRADE_PROTOCOL · iMac=Sim מאושר · אורפן-שטוח · flag_guard PASS.

## 10. מפת-המסמכים (נוצרו/עודכנו היום)
- `docs/handoff/CURSOR_SESSION_BRIEF_2026-07-20.md` — **המסמך הזה** (התמונה המלאה).
- `docs/handoff/CURSOR_TAKE_COMMAND_SYSTEM_VERIFY_2026-07-20.md` — המנדט + §0-§4 + פרוטוקול-אימות + הכנות-מחר.
- `docs/FLAG_RULING_2026-07-20.md` — מקרא-הדגלים + ההכרעה (flag_guard PASS).
- `docs/handoff/CURSOR_FRONTEND_INDEX_2026-07-20.md` — אינדקס-פרונטאנד + סיבת-מחסום מדויקת לכל שער.
- `docs/FLAG_INDEX.md` — הרישום המלא (175 דגלים) · `config/RULED_FLAGS.yaml` — הממשל הנאכף.

## 11. פרוטוקול-עבודה
מערכת-אחת-בכל-פעם · **Rule 5** (פקודה+פלט-גולמי, לא "אושר") · ממצא+תיקון+ראיה · דגל-OFF+טסט לכל
שינוי-התנהגות · **עצור + מייקל** לפני כל נגיעה בלוגיקת-מסחר/סיכון. cowork מאמת אותך סימטרית (כפי שנתפס ב-§0).
