# S1 Day-Type — Handoff להמשך (2026-06-20)

המשך-עבודה לצ'אט הבא. קרא קודם את **`docs/spec_authority/S1_DAYTYPE_INDEX.md`** (האינדקס הקנוני) ואת **`docs/plans/STATUS_BOARD.md`** (06-20).

---

## TL;DR — איפה אנחנו
מערכת-1 (סוג-היום) **נבנתה מחדש, אומתה, וחיה — גם בתצוגה וגם בשער-המסחר.** מזהה נכון את **כל 7 הסוגים** (אומת: 17/06→Trend_DD · 10/06→Variation · 18/06→Normal). **הקידום-המלא בוצע והודלק (2026-06-20):** `S1_NEW_CLASSIFIER=1` → `day_type_at_entry` (תיוג-העסקה + הקלט ל-3 שערי-הסחר) מגיע מהמסווג **החדש**, לא מ-DECISION_MATRIX. **השלב הבא = S2/S4 — התאמת-ירי תבנית-תבנית (#68).**

## ✅ הקידום-המלא — בוצע 2026-06-20 (השלב שנסגר עכשיו)
- **נקודת-חיבור יחידה:** `backend/v9/services/trade_context.py::extract_g1_entry_context` (שורה ~500). כשהדגל דלוק, ה-`day_type` שמוחזר מחושב מהמסווג החדש (`classify_replay(today)`), ממופה לאנום-ה-playbook (`Normal_Variation→Variation`), מטמון ~30ש'. **fail-safe כפול** (try/except אצלי + ב-gate) → כל שגיאה/אין-ברים/FORMING ⇒ נשאר הערך של המנוע-הישן (לעולם לא חוסם ירי).
- **למה זו נקודה אחת שמכסה הכל:** `trading_gateway.py:153/173/188` — **שלושת השערים** (`DAYTYPE_PLAYBOOK` הדלוק · `TREND_DIRECTION_GATE` · `REACTIVE_LOCATION_GATE`) **וגם** תיוג-העסקה (`v9_trades.day_type_at_entry`) — כולם קוראים את `extract_g1_entry_context`. עקיפה אחת ⇒ מגיעה לכולם (אין חיווט-חלקי).
- **ה-playbook מכסה את כל 7 הסוגים** (`config/daytype_playbook.yaml`: Trend_Normal/Trend_DD/Normal/Variation/Neutral_Center/Neutral_Extreme/Nontrend) — תואם את פלט-המסווג אחרי המיפוי. `DAYTYPE_PLAYBOOK=1` כבר היה דלוק, אז ה-veto עכשיו פועל על התוויות **הנכונות**.
- **אומת (Rule 5):** `COMPILE_OK` · classify_replay live: 17/06→Trend_DD,10/06→Normal_Variation,18/06→Normal · 4 מקרי-עקיפה דטרמיניסטיים: `ON+Trend_DD→Trend_DD` · `ON+Normal_Variation→Variation` · `ON+FORMING→נשאר Normal` · `OFF→נשאר Normal` · backend restart נקי (health ok, אין traceback).
- **⚠️ ניטור יום-שני:** היום שבת (אין ברים → העקיפה no-op, נופלת למנוע-הישן). **הירי-החי-הראשון עם המסווג החדש הוא בפתיחת יום-שני.** לעקוב אחרי הלוג ב-`/tmp/backend.log` (`[Gateway] day-type playbook PASS/BLOCKED`) ואחרי `day_type_at_entry` בעסקאות.
- **מתג-כיבוי:** `.env` שורה 89 `S1_NEW_CLASSIFIER=1` → שנה ל-`0` + `launchctl kickstart -k gui/$(id -u)/com.mems26.backend`. חוזר מיד למנוע-הישן.

## 🔴 הקשר — שני מנועים (מה-עדיין-לא-מקודם)
| | מנוע **ישן** (`state_machine.py`) | מנוע **חדש** (`daytype_classifier.py`) |
|---|---|---|
| מזין | **S2/S4 per-bar event** (`main.py:188`→`current_day_type`) + `v9_day_type_history` (EOD) | **`day_type_at_entry`** → 3 השערים + תיוג-העסקה ✅ · **כל משטחי-תצוגת-S1** ✅ |
| סוגים | ~3 (Variation/Normal/Trend) | כל 7 ✓ |

**הפער שנשאר (= שלב S2/S4):** S2/S4 עדיין קוראים את ה-day-type של המנוע-**הישן** דרך האירוע-per-bar (`main.py`), לא דרך `day_type_at_entry`. כלומר התנאי-הפנימי-של-S2/S4-על-סוג-יום עוד לא על המסווג החדש. זה בדיוק **#68**.

## ✅ מה נבנה ואומת קודם (הצינור עצמו)
- **מכונת-מצבים** (`daytype_classifier.classify`): priority-0 **INVALIDATED** · **FORMING רק לפני נעילת-IB** (12 ברים) · **PROVISIONAL** + **EOD-resolution** · **Nontrend**=`sides==0∧vol≤0.5∧rib≤1.15` · זנבות+CVD=**מאשרים** · **Trend_Normal**=חתימה-מחמירה.
- **`relative_features.sides`**=פריצת-IB **עם ווליום-קבלה≥8%**,מוחזק≥2; **IB מסיארה**. **`dd_features`**=DD מהנרות (IB-צר+neck=2-POC+סגירה-בקצה).
- **45/45 טסטים** (`tests/v9/systems/day_type/`) + הרצת-11-ימים תואמת-אישור. מיפוי: Trend_Normal=06-05·Trend_DD=06-16,17·Variation=06-10,12,15,19·Neutral_Center=06-09,11·Neutral_Extreme=06-08·Normal=06-18.
- **דאשבורד (תצוגה):** `DayTypeConditionsTable` (Build Status) · `useLiveDayType` · **קידום-תצוגה** ב-`systemStateStore` (כל משטחי-S1). _(ניתוח-עסקאות פר-סוג-יום = עמוד-Trades הקיים; טאב "Day Trades" הוסר ככפילות.)_

## ▶️ השלב הבא — S2/S4 (משימה #68)
ניהול-3-החוזים פר-סוג-יום: **`docs/spec_authority/S1_TRADE_MANAGEMENT_3CONTRACTS.md`** (C1=BE·C2=יעד·C3=runner/trail). תשתית: `config/daytype_playbook.yaml`. דהה=Nontrend/Normal/Neutral · לך-עם=Variation/DD/Trend. לעבור **תבנית-תבנית** (REACTIVE/INITIATIVE/HFE/ZLR…), config→execution, flag-gated, backtest, אישור-Michael. **שקול לחבר גם את האירוע-per-bar של main.py למסווג החדש** כדי לסגור את הפער-לעיל (S2/S4 יקראו את אותו מסווג).

## ניקוי שנשאר (קבצים פעילים — זהיר)
- `backend/v9/systems/day_type/opening_detector.py` (v1) — רק טסט מייבא; הסר + הפנה ל-v2.
- `backend/v9/systems/day_type/api.py::_classify_v1_from_tpo()` + `_engine`/`_get_engine()`.
- REPLACE: `decision_matrix.py` (עדיין מזין S2/S4 — לפרוש רק אחרי #68) · `detector.detect_opening_type` · `shadow_reclass.py` · `open_type.py`.

## הגדרות + פקודות
- **DB:** local PG `postgresql://localhost/mems26`. **Backend python:** `/Library/Frameworks/Python.framework/Versions/3.9/bin/python3` (3.9 framework; uvicorn `backend.main:app`).
- **Restart** (שוק-סגור): `launchctl kickstart -k gui/$(id -u)/com.mems26.backend`. **Health:** `curl -s localhost:8000/api/v9/health`. **Endpoint:** `…/api/v9/day_type/classify_replay?date=YYYY-MM-DD` (Bearer `michael-mems26-2026`).
- **Frontend typecheck:** `cd frontend/v9 && npx tsc --noEmit` (4 שגיאות קיימות לא-קשורות).
- **דגלים פעילים (.env):** `S1_NEW_CLASSIFIER=1` (חדש·06-20) · `DAYTYPE_PLAYBOOK=1` · `TREND_DIRECTION_GATE` · ranאיתחל.

## כללי-ברזל
Local PG בלבד · bridge→localhost:8000 · Standing-OFF flags (S2 chop/COT) PERMANENT · Cowork לא עושה commit/push בלי הוראת-Michael (**הסניף לא-דחוף — להזכיר ל-Michael**) · Rule 1 (null>סינתזה) · Rule 5 (הדבק command+output) · סיארה=מקור-אמת · שינוי-trading-surface=סטופ+אישור.

## מסמכים קנוניים
`docs/spec_authority/S1_DAYTYPE_INDEX.md` (אינדקס·§6 קידום) · `S1_TRADE_MANAGEMENT_3CONTRACTS.md` · `docs/plans/STATUS_BOARD.md` (06-20) · `config/daytype_trading_plan.yaml` (זיהוי) · `config/daytype_playbook.yaml` (תבנית×יום).
