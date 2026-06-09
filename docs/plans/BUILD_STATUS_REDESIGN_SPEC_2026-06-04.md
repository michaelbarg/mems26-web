# Build Status — מפרט עיצוב-מחדש (מוכן-ליישום) · 2026-06-04

> מצב: **מומש** ב-`frontend/v9/src/v9/components/build_tree/BuildTreeView.tsx` (route `/build`).
> typecheck נקי (0 שגיאות בקובץ). Read-only מול ה-backend — שום שינוי ב-endpoint/risk-logic.
> מקורות: `BUILD_STATUS_REDESIGN_MOCKUP_V2_2026-06-04.html` · `BUILD_STATUS_COMPONENT_AUDIT.md`.
> נלווים: `BUILD_STATUS_BACKEND_GAP_LIST_2026-06-04.md` (gap-list) · `BUILD_STATUS_CULL_RECOMMENDATION_2026-06-04.md` (cull).

## 1. עיקרון-העל (source-of-truth Rule 1)

העמוד מציג **רק שדות שה-backend פולט** דרך `GET /api/v9/build/pattern-status`. כל שדה
שעדיין לא נפלט מסומן `⧗ ממתין ל-backend` ולעולם לא מסונתז ב-frontend. שפת-הסימון
היחידה בעמוד:

| תג | משמעות | מקור |
|---|---|---|
| `● חי` | נפלט מה-endpoint כעת | `pattern-status` |
| `⧗ ממתין ל-backend` | האפיון דורש, ה-backend לא פולט עדיין | gap-list |
| `📖 אפיון` | קונפיג סטטי (ספר-חוקים) שמותר להציג verbatim | `targets_table.py` / `atr_caps.py` |

חריג יחיד מותר: **טבלאות האפיון** (§5) הן קונפיג סטטי ולא ערך חי — מותר verbatim, מסומנות `📖`.

## 2. נתונים ורענון

- Hook: `useBuildStatus` → `fetch(${API}/api/v9/build/pattern-status)`. **רענון ידני בלבד**
  (הוראת מייקל 2026-05-26 מוטמעת ב-hook). **אין auto-poll** — לא להוסיף בלי אישור.
- סכמת התגובה: `frontend/.../build_status/types.ts` (מראה את ה-Pydantic של ה-backend).
- ה-day-type הפעיל נגזר מהנתון החי (`currentDayType()`): קודם מ-`day_type` system
  (`interpretations`/`live_inputs` field `day_type`), נפילה ל-`readiness.checks` detail.

## 3. מבנה-קומפוננטות

| קומפוננטה | מציגה | מקור-נתונים | live/pending |
|---|---|---|---|
| `Legend` | הגדרת `● חי` / `⧗ ממתין` | סטטי | — |
| `Blocker` | למה לא נכנסנו (חסם block יחיד + degraded) | `readiness.checks` | ● חי |
| `GlobalFirewall` | `pre_fire_validator` (7) + `risk_checks` (LIVE caps) | placeholder | ⧗ ממתין · P0 |
| `SourcesStrip` | רעננות לכל מקור (שכבה 0) | `systems[].data_freshness` | ● חי |
| `SystemBranch` | עץ 6-שלבים פר-מערכת | `systems[]` | מעורב (ראה §4) |
| `TargetsStopPending` | סכמת TARGETS/STOP (בלי מספרים) | placeholder | ⧗ ממתין · P0 |
| `ObserverCards` | S1 (live) · S5/S6 (לא-מחווט) | `systems[]` + placeholder | מעורב |
| `IntegrityTab` | שדה→ערך→מקור→קנוני | `live_inputs` + `components[].freshness.source` | ● חי |
| `DayTypeTables` | טבלאות החלטה פר-יום + ATR + time-stop | קונפיג ממורקר | 📖 אפיון |
| `MissingTab` | 12 פערי-backend (P0→P2) | סטטי (מהאודיט) | — |
| `FixRef` / `Path` | "↳ לתיקון:" עם נתיב-קוד/runbook | סטטי | — |

## 4. מיפוי שלב→שדה (פר-מערכת יורה · 5 שלבים קנוניים + פסיקה)

לכל `SystemBranch` של מערכת יורה (S2/S3/S4):

| שלב | שדות מהתגובה (חי) | חסר (⧗ ממתין) |
|---|---|---|
| **1 · מקור** | `data_freshness{last_bar_ts, lag_seconds, fresh, threshold_seconds}` | freshness ל-3 קובצי Sierra של S2 (cumulative_delta/tpo/volume_profile JSON) |
| **2 · קלט** | `live_inputs[]{field, value, source, age_s, fresh}` | S2: atr_14, COT/AMT · S3: bid/ask_vol, imbalance, delta |
| **3 · פרשנות** | `interpretations[]{key, value, from_input, detail}` | — |
| **4 · שערים** | `global_gates[]{key, present, live, freshness.source}` | pre_fire_validator · risk_checks · S6 Killzone · S/R · COT>AMT · S4 Matrix/A7/anti-patterns |
| **5 · פסיקה** | `patterns[]{status, label, reason, fired_today, last_fire_ts}` + `components[]` | S4 dispatch (winning_pattern לפי r_t1) |
| **6 · TARGETS/STOP** | — | **כל השלב** — מסונכרן עם `CC_PROMPT_P0_2`: S2 `stop_price`/`risk_1R`/`t1-t3_price`/`r_t1`/`time_stop`/`sizing`/`variant_tag` · S4 `stop_price`/`atr_14_ticks`/`r_t1`/`t1-t2_price`/`entry_price`/Day-Type Matrix |

ה-drill-down של כל תבנית מציג `components[]{stage, key, required, live, present, freshness.source}`
דרך `ComponentTable` (קיים בתגובה).

### 4.1 · כלל עקביות — שערים תלויי-TARGETS/STOP (מאושר מייקל 2026-06-04)

**כל שער שהשער האמיתי שלו תלוי בנתוני TARGETS/STOP שעדיין לא נחשפים (`r_t1` / 1R / pre_fire R:R)
מוצג כ-`⧗ ממתין ל-backend` — לעולם לא כפרוקסי "ירוק".** הנימוק: המנוע החי מחליט לפי
`r_t1 ≥ min_r_t1_threshold` + `pre_fire_validator (R:R≥1.0)`; פרוקסי כמו `confidence≥0.5` הוא קירוב
שעלול לסתור את המציאות (ירוק-שקרי). "ממתין" אמין עדיף על "ירוק" מטעה — זהו עיקרון ה-source-of-truth.

חל על (ידוע נכון להיום):
- **S4 (Woodies):** `confidence_score` (`woodies_inspector.py:344-352`) → ⧗ ממתין עד `r_t1`.
- **S2 (five_min):** כל שער-ירי תלוי-`r_t1` → ⧗ ממתין (ל-`s2_inspector` אין כיום פרוקסי confidence,
  אבל אם ייווסף — אותו כלל).
- **S3 (footprint):** שערי-ירי תלויי-stop → ⧗ ממתין (ממילא מושבת).

זיהוי בצד-frontend (עד שה-backend יתקן את המקור): רכיב/שער עם `key`/`spec` שמכיל `confidence`
המשמש כשער-ירי מוצג כ-⧗ ממתין (de-trust), לא present-ירוק. התיקון הנכון הוא בצד ה-backend
(לפלוט `present=false` עד `r_t1`) — ראה gap-list P0-2.

## 5. טבלאות אפיון (טאב "טבלאות אפיון")

מקור: `backend/v9/systems/day_type/targets_table.py` (`_TARGETS`) + `five_min/atr_caps.py`.
שלוש טבלאות, **verbatim**:

1. **טבלת-על** — 7 סוגי יום × (T1/T2/T3/trail/time-stop/חוזים/sizing). היום החי מודגש.
2. **מרחק סטופ** — `1R = ATR14 × מכפיל-משפחה` (Reactive ×1.0 … Triangle ×2.0).
3. **time-stop פר-תבנית** — Layer-3 backstop, בפועל `min(day, pattern)`.

תת-טאבים פר-יום; ברירת-המחדל = היום החי. כולל ה-override (`Trend_DD` + `OFA_Initiative` → 6R+trail)
ו-`Nontrend = NO TRADE`.

> **חוב טכני (מודע):** הטבלאות ממורקרות ב-frontend (`DAY_TARGETS`/`ATR_MULTIPLIERS`/`PATTERN_TIME_STOPS`).
> זה duplication של קונפיג-backend → סיכון drift. הוקטן בהערות-sync בקובץ. **תיקון נכון:**
> שה-endpoint יחשוף אותן (gap-list P2). עד אז — לשמור מסונכרן ידנית מול שני הקבצים.

## 6. ההקרנה החסרה (הקשר ל-P0)

הטבלאות נותנות R-multiples ו-time-stops. ה**הקרנה** למחירים חיים (entry/stop/T1‑T3 ב-$)
דורשת את ה-1R החי ממנוע-הסטופ — וזהו בדיוק שלב TARGETS/STOP ש-`⧗ ממתין ל-backend`.
לכן הלוח "מוכן לירי" עם מספרים (כפי שהופיע במוקאפ הישן) **לא ממומש** עד שה-backend יחשוף את 1R.

## 7. דריפטים — הוכרעו ע"י מייקל (2026-06-04)

1. **S3 = מערכת יורה (`firing`).** הדריפט נפתר לטובת הקוד החי (לא הרגיסטרי). S3 מסווג `firing`
   ומוצג ככזה (עם שלב TARGETS/STOP). כרגע **מושבת** (`FOOTPRINT_DISABLED`) ולכן לא יורה בפועל —
   יוצג עם **באנר "מושבת"** עד שייפתח, ואז חוזר לירות. (חשיפת הדגל = gap-list P2-3.)
2. **Killzone = `zones.py` (11 אזורים) — קנוני.** ה-`killzone_inspector` יקרא משם, ויחליף את
   ה-RTH הגנרי בשער ה-killzone האמיתי. **הערה:** הגדרת ה-11 עצמה צפויה להתעדכן בהמשך —
   לסמן "קנוני-לעת-עתה, נתון לעדכון". (gap-list P1-1.)
3. **שער ה-`confidence≥0.5` = `⧗ ממתין ל-backend` מלא.** **תיקון:** הפרוקסי הזה ב-**S4 (Woodies)**,
   לא S2 — `woodies_inspector.py:344-352` (stage `sizing`/`confidence_score`, לפי
   `BUILD_STATUS_ENDPOINT_DESIGN.md §4.2`). ב-`s2_inspector` אין פרוקסי כזה. מסתירים אותו לגמרי —
   ה-inspector קורא `confidence` כי זה השדה היחיד הזמין על אובייקט-התבנית; ה-`r_t1` האמיתי דורש את
   מרחק-הסטופ החי שמחושב בנתיב ה-dispatch ולא נחשף ל-read-path. כשה-TARGETS/STOP (P0-2) + dispatch
   (P1-5) יחשפו `r_t1` → השער יוצג כ-`r_t1≥min_r_t1_threshold` האמיתי. עד אז — ⧗ ממתין, לא שער "ירוק".
