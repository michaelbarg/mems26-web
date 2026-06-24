# S1 — אינדקס מלא של סוג-היום (קנוני · 2026-06-20)

המקום היחיד להסתכל בו לכל דבר שקשור לסוג-היום. נבנה מסריקת-3-סוכנים (backend / frontend / data). מתעדכן אחרי כל שינוי מבני.

---

## 🔴 הממצא הקריטי — שני מנועים מקבילים

| | מנוע **חי** (סוחר!) | מנוע **חדש** (מאומת) |
|---|---|---|
| קובץ | `state_machine.py` (`DayTypeStateMachine`) | `daytype_classifier.py` (`classify`) |
| מחווט ע"י | `backend/main.py:188` → `app.state.day_type_machine`, מוזן כל בר | `daytype_classify_routes.py:204` בלבד (`/classify_replay`) |
| לוגיקה | `DECISION_MATRIX` (opening×IB) — **מגיע ל-~3 סוגים בלבד** | מכונת-מצבים יחסית — **כל 7 הסוגים** ✓ |
| config | thresholds מקודדים-קשיח | `config/daytype_trading_plan.yaml` |
| אנום | `Variation` · `Neutral` | `Normal_Variation` · `Neutral_Center/Extreme` |
| סטטוס | **חי — מזין S2/S4** (אירוע per-bar) + EOD-history | **חי — מזין `day_type_at_entry`** (3 שערים+תיוג, `S1_NEW_CLASSIFIER=1` 06-20) + כל תצוגת-S1 |

**עדכון 2026-06-20:** המסווג החדש **כבר מזין את שער-המסחר** (`day_type_at_entry` → 3 שערים+תיוג, `S1_NEW_CLASSIFIER=1`) **ואת כל תצוגת-S1**. נשאר: האירוע-per-bar שמזין **S2/S4** עדיין מהמנוע-הישן בן-3-הסוגים → נסגר בשלב #68 (התאמת-S2/S4), ואז `decision_matrix.py` נפרש. ראה §6.

---

## 1. צינור-הסיווג החדש (הקנוני) — `backend/v9/systems/day_type/`

| מודול | תפקיד | סטטוס |
|---|---|---|
| `relative_features.py` | rib · **sides** (פריצה+ווליום-קבלה≥8%) · one_tf · close_pos · returned_through_open | ✅ ליבה |
| `cvd_features.py` | cvd_pos יחסי + כיוון-קצה-אחרון (מאשר) | ✅ |
| `dd_features.py` | גלאי Double-Distribution מהנרות (IB-צר + 2 POC + neck + held) | ✅ |
| `context_features.py` | ib_width_percentile · open_location · poc_drift · ~~second_distribution~~ | ⚠️ `second_distribution` מת (הוסר) |
| `opening_detector_v2.py` | 5 סוגי-פתיחה (מתקן over-DRIVE) | ✅ |
| `daytype_classifier.py` | `classify()` מכונת-מצבים (INVALIDATED→FORMING→Nontrend→Neutral→DD→Trend→Variation→Normal) | ✅ replay-only |
| `daytype_classify_routes.py` | `GET /api/v9/day_type/classify_replay?date=` | ✅ ה-endpoint |

**הסיגנלים (כולם יחסיים):** IB=שעה-ראשונה(12 ברים,סיארה) · side=פריצה+ווליום≥8%,מוחזק≥2 · rib=טווח/IB · close_pos · one_tf · vol_ratio · ib_narrow≤0.7×חציון · neck=2-POC · cvd_pos(מאשר) · tails(מאשר).

## 2. מקורות-נתונים (סיארה → טבלה → סיגנל)

| טבלה | מה | בשימוש בצינור החדש? |
|---|---|---|
| `v9_tpo_sessions` | IB · POC/VAH/VAL · profile_shape | ✅ (IB·VA·DD·prior-day·חציון) |
| `v9_tpo_history` | POC פר-תקופה | ✅ (poc_drift) |
| `v9_bars_5min_woodies` | OHLCV + CCI + trend_state | ✅ (מקור-בר ראשי + ווליום) |
| `v9_bars_5min` | OHLC רציף + cum_delta | ✅ (fallback ברול-חוזה) |
| `v9_bars_cumulative_delta` | delta/cumulative | ⚠️ **לא בשימוש** — ה-cvd נלקח מ-cum_delta של הבר |
| `v9_bars_volume_profile` | ווליום-פר-מחיר | ❌ **יתום לסוג-יום** — לא נקרא בשום מקום |
| `v9_day_type_history` | סיווג-EOD (נכתב ע"י המנוע **החי**) | קריאה בלבד (היסטוריית-IB) |
| `v9_day_type_state` | snapshot פר-בר (המנוע החי) | לא בשימוש בחדש |
| `v9_trades.day_type_at_entry` | תג-יום בזמן-ירי (מהמנוע **החי**) | מקור day-type-trades |

## 3. נתיב חי-מול-replay + ה-gating

- **חי:** `main.py:188` → `DayTypeStateMachine` (ישן) → אירוע `day_type_classification` → S2/S4 (`current_day_type`); `trading_gateway.py:150` קורא `day_type_at_entry` (מהמנוע הישן) ל-veto.
- **playbook:** `config/daytype_playbook.yaml` → `daytype_playbook.decide()` → `trading_gateway.py:150-167`. flag `DAYTYPE_PLAYBOOK` (default OFF, fail-open FULL). **תאי-ה-config מפתחים על `Variation`** (אנום ישן) — אי-התאמה לאנום החדש `Normal_Variation`.
- **ניהול-3-חוזים:** `config/daytype_trading_plan.yaml` (`daytype_style`/`patterns`) + `S1_TRADE_MANAGEMENT_3CONTRACTS.md`.
- **EOD:** `v9_day_type_history` נכתב חי (DayTypeConsumer). `docs/reports/EOD_DAYTYPE_HISTORY.csv` — **אין כותב** (ידני, יתיישן).

## 4. חזית (frontend) — `frontend/v9/src/v9/`  ✅ מחווט · המסווג החדש חי בתצוגה (אחרי restart 2026-06-20)

**חדש (נבנה — מציג את המסווג החדש דרך `classify_replay?date=today`, תצוגה בלבד):**
| רכיב | תפקיד |
|---|---|
| `components/build_status/DayTypeConditionsTable.tsx` | **טבלת Build Status חיה** — 7 ימים + 5 פתיחות, תנאי ✓/✗ בזמן-אמת, מסמן את המזוהה (poll 30s) |
| `hooks/useLiveDayType.ts` | hook — מושך את ה-day-type של המסווג החדש להיום, לכל משטח-S1 (poll 30s, fallback ל-store) |

> _ניתוח W/L פר-סוג-יום: **עמוד Trades הקיים** (לא משטח נפרד). טאב "Day Trades" הוסר 2026-06-20 — כפילות._

**עודכנו למסווג החדש:**
| רכיב | שינוי |
|---|---|
| `components/systems/DayTypePill.tsx` | **ה-ריבוע של מערכת-1** — מעדיף `useLiveDayType` (המסווג החדש) על ה-store הישן · ABBREV עם השמות החדשים (FORM/NEUC/NEUX/…) |
| `components/day-type/DayTypeLabelTab.tsx` | סודר: sides/rib/close/1TF · DD(neck=2POC) · status×3 (CLASSIFIED/PROVISIONAL/FORMING) · מקרא-חדש |
| `components/build_status/BuildStatusTab.tsx` | מרנדר `DayTypeConditionsTable` מעל `BuildTreeView` |

**קיים (KEEP / רפרנס):** `build_tree/BuildTreeView.tsx` (build-tree S1–S6) · `systems/DayTypeLensContent.tsx` (lens חי — עדיין קורא **מנוע ישן**, לעדכן ל-`useLiveDayType` בהמשך) · `trades/EdgeMatrix.tsx`+`TargetDistStrip.tsx` (group-by-day_type) · **`trades/` עמוד-העסקאות הקיים** = כל ניתוח-העסקאות (כולל פר-סוג-יום).
**הוסרו ✅:** 5 יתומי `build_status/` + **`trades/DayTypeTradesView.tsx` + טאב "Day Trades"** (כפילות לעמוד-Trades, 2026-06-20).

## 5. 🧹 רשימת-ניקוי (KEEP/REMOVE/REPLACE)

**REMOVE (יתומים, אפס קוראים — בטוח):**
- `backend/v9/systems/day_type/opening_detector.py` (v1) — רק טסט מייבא; הוחלף ב-v2.
- `context_features.py::second_distribution()` + הייבוא המת — הוחלף ב-dd_features.
- `backend/v9/systems/day_type/api.py::_classify_v1_from_tpo()` + `_engine`/`_get_engine()` — מסווג-V1 מתחרה + instance מת (תמיד UNKNOWN).
- frontend `components/build_status/`: `SystemSection · ReadinessHeader · PatternRow · StatusPill · ComponentTable` — 5 רכיבים יתומים (BuildTreeView החליף).

**REPLACE (חי — אחרי חיווט המסווג החדש):**
- `decision_matrix.py` — המסווג-מטריצה בן-3-הסוגים. עדיין load-bearing (state_machine + fallback ב-five_min/woodies). לפרוש כשהחדש חי.
- `detector.detect_opening_type` (over-DRIVE) → `opening_detector_v2`.
- `shadow_reclass.py` — מסווג שלישי (shadow). לאחד עם החדש; raw sqlite3 → engine.
- `open_type.py` + `open_type_routes.py` — opener-4-סוגים legacy (endpoint-only).

**DEFER/לבדוק אם mounted:** frontend `sidebar/tabs/DayTab.tsx` · `panels/System1Panel.tsx`.

## 6. קידום המסווג החדש — תצוגה (בוצע) מול מסחר (השער)

**✅ קידום-תצוגה (בוצע 2026-06-20):** `store/systemStateStore.ts::fetchAllStates` → `overrideS1()` עוקף את מערכת-1 עם המסווג החדש (`classify_replay?date=today`), בשני המסלולים (snapshot/fallback). לכן **כל משטחי-S1 בדאשבורד** (ה-ריבוע · lens Now/Plan · DayTab · System1Panel) מציגים את המסווג החדש ממקור-אחד. fallback למנוע-הישן כשאין ברים (טרום-RTH/שוק-סגור) או offline. **תצוגה בלבד — לא נוגע בלוגיקת-המסחר.** (poll דרך `useSystemStatePolling`.)

**✅ קידום-מלא (בוצע + הודלק 2026-06-20, אישור-Michael) — המסווג החדש מזין את שער-המסחר:**
- **דגל `S1_NEW_CLASSIFIER=1`** (`.env` שורה 89). נקודה אחת: `trade_context.extract_g1_entry_context` — כשדלוק, `day_type_at_entry` מחושב מ-`classify_replay(today)`, ממופה `Normal_Variation→Variation`, מטמון 30ש', **fail-safe** (שגיאה/אין-ברים/FORMING→נשאר הישן).
- **מכסה את כל הצרכנים ממקור-אחד:** 3 השערים (`trading_gateway.py:153/173/188` — DAYTYPE_PLAYBOOK הדלוק·TREND_DIRECTION·REACTIVE_LOCATION) + תיוג-העסקה. אנום תואם את כל 7 מפתחות-ה-playbook.
- **אומת:** COMPILE_OK · 4 מקרי-עקיפה דטרמיניסטיים (ON→חדש·ON+Normal_Variation→Variation·FORMING/OFF→ישן) · restart נקי. **ניטור: ירי-חי-ראשון = פתיחת יום-שני** (שבת=no-op). **מתג-כיבוי:** `S1_NEW_CLASSIFIER=0`+restart.
- **🔒 נשאר (=שלב #68):** האירוע-per-bar של `main.py:188` שמזין את **S2/S4** עדיין מהמנוע-הישן. לחבר גם אותו למסווג החדש כחלק מהתאמת-S2/S4. `decision_matrix.py` נפרש רק אז.
