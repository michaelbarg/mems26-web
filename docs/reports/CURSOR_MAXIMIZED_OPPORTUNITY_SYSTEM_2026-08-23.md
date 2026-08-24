# Cursor — מערכת-מקסום הזדמנויות + רפליי נגד-עובדתי (2026-08-23)

> **🔴 SUPERSEDED FOR MONEY CLAIMS — 2026-08-24:** שתי הנחות-אמת הופרכו:
> (1) 92.3% מבחירות ה-TPO "הסיבתיות" השתמשו ברמה ש-`created_at` שלה היה
> מאוחר מה-candidate; (2) DB OHLC תואם Sierra SCID ב-100% רק ב-20/34 ימים.
> אחרי תיקון TPO-availability, `MAX_CONTEXT 6c/s1` השתנה מ-**+$339** ל-**−$558.76**
> ו-`MAX_2SLOT` ל-**−$436.51**. לכן כל טבלאות-ההכנסה החיוביות בהמשך הן
> תיעוד של הריצה הישנה, **לא תחזית ולא ראיית-רווח**. הפסק הכספי הנוכחי: $0
> planning estimate עד SCID truth-overlay מלא + S4 parity + broker reconciliation.

**מנדט מייקל:** להמליץ איזה סוג מערכת/מודל צריך לעבוד מעל המערכות הקיימות, כיצד
למקסם זיהוי וכניסה בזמן, ולהריץ היסטוריה מהנרות+נפח — **לא** ממה שירה בפועל.

**תוצר-קוד מחקרי:** `scripts/replay_maximized_opportunity.py`  
**אוכלוסייה:** 34 סשני-RTH, 07-07→08-21 · `v9_bars_5min_woodies` · volume · CVD ·
snapshots סיבתיים מ-`v9_tpo_history` · **אפס קריאה ל-`v9_trades`,
`v9_five_min_setups` או `gateway_decisions` לצורך המועמדים/התוצאות.**

---

## 1 · פסק-העל

### המערכת הנכונה אינה "מודל אחד"

ההמלצה היא **מערכת היברידית מונעת-אירועים**:

1. **S1 בינארי-מבני = סמכות-המשטר** — BALANCE / DISCOVERY + סוג-יום + כיוון;
   ללא confidence בשרשרת-ההחלטה.
2. **S2/S4 = אנסמבל-גלאים** — כל גלאי מייצר Candidate, לא פקודת-מסחר.
3. **`CONTEXT_ENTRY_V1` דטרמיניסטי = שוער-הזדמנות** — ב-BALANCE: היפוך מאושר
   בקצה; ב-DISCOVERY: המשכיות עם-הכיוון / REACTIVE כפולבק.
4. **Opportunity Ranker סטטיסטי = סדר-עדיפויות בלבד**, בצל: בתחילה
   Logistic/GAM רגולריזי ומכויל; רק אחרי ≥100 סשנים — monotonic GBDT.
5. **Gateway/TM נשארים דטרמיניסטיים** — risk, account truth, bracket, stop,
   margin ו-feed לעולם אינם נעקפים ע"י מודל.

**לא מומלץ:** LLM, Reinforcement Learning או רשת-עמוקה בנתיב-ירי. יש 34 סשנים
ו-688 מועמדים — מעט מדי, תלויי-זמן מדי, וכסף-חי. LLM יכול לכתוב דוח; לא לפסוק
כניסה. RL ילמד לנצל את הסימולטור ואת פגמי-המדידה.

### למה

הרפליי החדש מוכיח ששני הקצוות שגויים:

- **פתיחת הכול:** 6.88 עסקאות/יום ⇒ **‎−$3,615**.
- **הקשר נכון, סלוט אחד:** 1.00 עסקה/יום ⇒ **+$339**, אך ב-2 ticks סליפג'
  רק **+$82** ו-pseudo-OOS **‎−$21**.

כלומר: **הגלאים מייצרים מספיק; הבעיה היא selection + timing.** מצד שני שכבת-הקשר
הנוכחית בררנית מדי כדי להגיע ל-2–3 עסקאות/יום. אסור לכפות מכסה. צריך לפתוח
עיניים בצורה סיבתית ולשפר אישור-הכניסה.

---

## 2 · קודם כל: מה בבריף v3 כבר נסגר ומה נשאר

### CLOSED מאז כתיבת הבריף

- CVD no-op + 12 עמודות-ts הומרו ל-`timestamptz`; CVD הועבר ל-**shadow**.
- P3 (1.5×ATR · ≥1.5R · avg-stop · edge-ban) + T-10 core.
- A3 pytest isolation · A4 Auth + הסרת HLST מהשרשרת · A5 restart hydration ·
  A7 log archive · C2 absorption field · D4 MFE-after-block.
- `TREND_STEP_ENTRY_V1=shadow`.
- `S1_STRUCTURAL_BINARY_V1=shadow`.
- `S2_DELTA_DBL_V1=shadow`.
- `DOUBLE_TOP_AA` תוקן בקוד הנוכחי: רפליי נוכחי מחזיר 32 candidates גם
  `as-is`; אין עוד פער Adam באוכלוסיית-היום.

**ראיה:**

```text
TASK_LOG 24.08:
CVD coverage 0%→65.3% · P3 done · A3/A4/A5/A7 done ·
structural_binary shadow · delta_double shadow · TREND_STEP shadow

dead_pattern_replay (קוד נוכחי):
DOUBLE_TOP_AA (adam-fix) fires=32, c6=-$427.13
DOUBLE_TOP_AA (as-is)    fires=32, c6=-$427.13
HNS_TOP fires=1 · INVERSE_HNS=0
RE_PULLBACK fires=26, c6=-$2,020.87
HLST fires=84, c6=-$4,551.00
OPENING_* fires=71, c6=-$4,739.26
```

### עדיין OPEN

- `CONTEXT_ENTRY_V1` **אינו קיים בקוד** — רק בשני מסמכי-מפרט.
- A6 חלקי: 43 MATCH · 21 DIVERGENT · 28 incomplete; ספר-הברוקר עדיין אינו
  אמת מלאה.
- `swallow_counter.py` קיים אך **אפס call-sites** משתמשים בו; 334 בליעות
  שנמדדו עדיין אינן נספרות ואינן חשופות בפועל ב-health.
- המסווג-הבינארי הוא shadow-wrapper חלקי: המסמך מבטיח EOD ו-DD-neck-refill,
  אבל `_detect_event()` אינו מממש אותם.
- `FLAG_INDEX` אינו עובר `--check`; `S1_STRUCTURAL_BINARY_V1`,
  `S2_DELTA_DBL_V1`, `SCALE_IN_P3_V1`, `DOUBLE_TOP_ADAM_FIX_V1` ועוד אינם
  רשומים ברג'יסטרי.
- 34 סשנים בלבד; אין true holdout ל-policy החדש.

---

## 3 · הגדרת הבדיקה — בלי הטיית "מה שירה"

### זרם מועמדים

הרפליי קורא את **פונקציות הגלאים החיות** ישירות, בר-אחר-בר:

- S2: REACTIVE · INITIATIVE · DBT/DT · HNS/iHNS · flags.
- S4: ZLR · TLB · TT · GB100 · VEGAS · GHOST · FAMIR · HTLB.
- OPENING.
- TREND_STEP ו-DELTA_DBL נמדדים כ-shadow ואינם לוקחים סלוט.

### אוכלוסיית-הזדמנויות העצמאית

- **REV:** B = rejection מ-VA מתפתח; C = failed IB extension; D = delta
  absorption.
- **CONT:** BREAK / STAIR / PB סיבתיים מ-`oracle_study.find_triggers`.

ההתאמה היא אותו כיוון+משפחה, בתוך 0–3 ברים אחרי האירוע.

### תיקון מתודולוגי לדוח-המקור

`EXTREME_DETECTION_AND_BIAS_AUDIT` כתב שכל B היא סיבתית, אך:

```text
extreme_detection_audit.py:258  tpo[d] = final CASH VAH/VAL
extreme_detection_audit.py:286  vah = tpo.get(d)
```

כלומר B השתמשה ב-VAH/VAL **הסופיים של אותו יום** — lookahead.
הרפליי החדש משתמש רק ב-snapshot האחרון ב-`v9_tpo_history` שחותמתו
`<= candidate_time`; אם אין — VA של היום הקודם. לכן אוכלוסיית 3-הימים ירדה
מ-98 ל-78 אירועים, אבל היא סיבתית.

### ניהול אחיד

- 4/6 חוזים.
- 0/1/2 ticks סליפג'.
- סולם MEMS האחיד מ-`oracle_study.sim_ladder`.
- סלוט אחד; 2 סלוטים = sensitivity בלבד.
- אין מכסת-כניסות ב-BALANCE: רוטציה חוזרת מותרת אחרי שהסלוט השתחרר.

`CURRENT_ALL` הוא **זרם candidates נגד-עובדתי ללא שערי-gateway**, לא P&L
של המערכת החיה. מטרתו להשוות את אותה אוכלוסייה ל-MAX. כל 34 הימים
רטרוספקטיביים; `pseudo-OOS` הוא split ישן של חלון-כיול TREND_STEP, לא holdout
אמיתי ל-policy החדש. הסולם האחיד מאפשר השוואת-זרועות, אך אינו משחזר כל
stop/target פר-תבנית.

---

## 4 · התוצאה המרכזית

### 6 חוזים, 1 tick

| זרוע | עסקאות | ליום | Win% | $ | חציון-יום | pseudo-OOS | יולי | אוגוסט | יום-גרוע |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **CURRENT_ALL** — כל candidates, בלי context | 234 | **6.88** | 41.9% | **‎−$3,615.40** | ‎−$82.12 | ‎−$1,020.76 | +$1,706.64 | **‎−$5,322.04** | ‎−$1,652.62 |
| **MAX_CONTEXT** — בינארי+מיקום+אישור, סלוט-1 | 34 | **1.00** | 41.2% | **+$339.00** | $0 | +$113.62 | ‎−$793.49 | +$1,132.49 | ‎−$627 |
| **MAX_EXPANDED** — בתוספת DT_AA repaired | 34 | 1.00 | 41.2% | **+$339.00** | $0 | +$113.62 | ‎−$793.49 | +$1,132.49 | ‎−$627 |
| **MAX_2SLOT** — מחקר בלבד | 43 | **1.26** | 46.5% | **+$824.25** | $0 | +$221.62 | ‎−$151.86 | +$976.11 | ‎−$627 |

**מסקנות:**

1. "יותר ירי" כשלעצמו הוא הפתרון הלא-נכון: CURRENT_ALL יורה כמעט 7/יום ומפסיד.
2. הקשר הופך את הסימן, אבל לא מגיע ליעד 2–3/יום.
3. DT_AA תוקן, אך אינו מוסיף עסקה או דולר לזרם-ה-MAX — פער-הכסף אינו עוד החיווט
   שלו אלא selection/slot.
4. 2 סלוטים מוסיפים רק 0.26 עסקה/יום; לא פותרים את פער-הכיסוי.

### 4/6 חוזים × 3 סליפג'

| זרוע | 4c s0 | 4c s1 | 4c s2 | 6c s0 | 6c s1 | 6c s2 |
|---|---:|---:|---:|---:|---:|---:|
| MAX_CONTEXT | +$669.75 | **+$226.00** | +$54.75 | +$1,004.62 | **+$339.00** | +$82.13 |
| MAX_2SLOT | +$1,079.50 | **+$549.50** | +$224.50 | +$1,619.25 | **+$824.25** | +$336.75 |

אבל ב-MAX_CONTEXT @s2 ה-pseudo-OOS = **‎−$21.38**, וב-2-slot @6c/s2 רק
**+$47.24**. זו **ראיית-SHADOW**, לא GO ללייב.

---

## 5 · כיסוי ותזמון

### 34 סשנים

```text
אוכלוסיית market opportunities = 712:
REV:D 194 · REV:B 120 · REV:C 96
CONT:BREAK 116 · CONT:PB 105 · CONT:STAIR 81

current detectors matched 218/712 = 30.6%
candidate rows = 688 · unmatched candidates = 500
REV coverage  = 90/410 = 22.0%
CONT coverage = 128/302 = 42.4%
median lag = 1 bar
```

### חלון-ה-3 ימים של הדוח הישן

```text
07-07..09: 78 causal opportunities · 18 matched = 23.1% · 62 candidates
```

זה גבוה מ-16%, משתי סיבות כנות:

1. אוכלוסיית-B תוקנה מ-final-VA ל-developing-VA (78 במקום 98).
2. הבדיקה החדשה מפעילה את כל הגלאים הנוכחיים מהברים; לא את setup-table הישן.

### פסק

- הצפון-הכוכב השתפר מ-16% מדווח ל-**30.6%** על כל התקופה.
- הפער המרכזי הוא **REV coverage = 22%**, לא CONT.
- 500/688 candidates אינם חופפים לאירוע-מבני מאותה משפחה בתוך 3 ברים — זו
  בעיית precision במקביל לבעיית recall.
- MAX_CONTEXT בוחר רק 47 candidates / 34 trades — selection טוב יותר, אך צר מדי.

---

## 6 · המודל המומלץ

### עכשיו: Logistic/GAM רגולריזי, לא GBDT

עם 688 candidates ו-34 ימים, מודל מורכב יזכור ימים. בנה שני מודלים קטנים
ונפרדים:

1. **REV ranker**
   - label: `T1_before_stop` וגם `MFE_12 / MAE_12`.
   - inputs: B/C/D · distance-to-VA/IB ב-ATR · REACTIVE stage · rejection depth ·
     relative volume · CVD reading {SUPPORTING/OPPOSING/ABSORPTION/MISSING} ·
     stop/ATR · time-from-structural-event.
2. **CONT ranker**
   - label זהה.
   - inputs: BREAK/STAIR/PB · direction-vs-discovery · pullback depth ·
     LSMA slope/ATR · trend_state · volume contraction/expansion ·
     distance-from-extreme/ATR.

פלט: `P(T1 before stop)` + expected-R. הוא משמש **רק**:

- לבחור בין candidates באותו בר/סלוט;
- להחזיק candidate בהמתנה לאישור;
- לרשום shadow recommendation.

הוא **אינו**:

- משנה סוג-יום;
- עוקף safety/risk/feed/account gates;
- מגדיל חוזים;
- יורה לבדו.

### אחרי ≥100 סשנים

אם Logistic/GAM חיובי ב-walk-forward: monotonic GBDT עם constraints
(למשל מרחק-סטופ גדול לא מעלה score בלי MFE מתאים). לא לפני.

### ולתזמון: state machine, לא ML

`DETECTED → REJECTED/ACCEPTED → CONFIRMED → ELIGIBLE → FIRED/EXPIRED`.

- B/C/D מזהים **איפה להסתכל**.
- REACTIVE / BREAK-RETEST מזהים **מתי**.
- Ranker מכריע רק **איזה** candidate מקבל את הסלוט.

---

## 7 · KEEP / ADAPT / REPLACE / DEFER

### KEEP

- `v9_bars_5min_woodies` + volume כמקור OHLC.
- CVD migrated, כרגע **shadow context**.
- `S1_STRUCTURAL_BINARY_V1` כרעיון וסמכות.
- REACTIVE כ-confirmation.
- S2/S4 detectors כ-candidate generators.
- stop_anchors / P3 / one-average-stop.
- gateway/TM hard safety.
- one-slot ברירת-מחדל.

### ADAPT

- `structural_binary_v1`: להוסיף EOD + DD-refill + חוזה phase/direction מלא.
- `CONTEXT_ENTRY_V1`: לבנות כחוט, לא כגלאי חדש.
- כל candidate חייב להירשם **לפני שערים** עם context+outcome.
- opening patterns: detection נשאר; eligibility רק דרך context (raw = ‎−$4,739).
- DT_AA: התיקון קיים; למדוד forward, לא לייחס לו $ שלא נוצר בזרם.
- HNS: צריך הגדרת 2-פסגות+neck או pivot-lookback; היום HNS_TOP=1, iHNS=0.
- RE_PULLBACK: החיווט קיים אך raw economics שלילי; להשתמש בו כ-confirmation
  ב-DISCOVERY, לא להדליק raw.

### REPLACE

- first-come-first-served בין candidates → scheduler מדורג.
- final-day VA ברפליי → developing snapshot.
- candidate confidence/day-type confidence → determined state + opportunity score
  נפרד.
- מדידה מ-`setup/trade/decision` survivors → candidate-event dataset מהברים.

### DEFER

- שני סלוטים בלייב.
- GBDT / RL / LLM decision-making.
- intrabar touch-entry בלי flow (נמדד שלילי).
- הפעלת כל dead pattern רק כדי להעלות count.

---

## 8 · רשימת-הפערים המדורגת

### P0 · אמת ובטיחות

1. **A6 broker truth חלקי** — 21 DIVERGENT + 28 incomplete.
2. **`swallow_counter` לא מחובר** — אפס imports/call-sites, ולכן חריגות שקטות
   נשארות שקטות.
3. **Flag registry drift** — `gen_flag_index.py --check` נכשל על דגלי-ליבה חדשים.
4. **Replay migration drift** — ts→timestamptz שבר `good_pattern_*`
   (`left(timestamp,10)`); תוקן עכשיו + 3 טסטי-regression.
5. **CONTEXT_ENTRY לא קיים** — המפרט אינו מוצר.
6. **Structural binary אינו שלם** — EOD/DD-refill כתובים בדוקס, לא בקוד.

### P0 · כיסוי/דיוק

6. **REV recall רק 22%**.
7. **500/688 candidates ללא match מבני** — precision נמוך.
8. **MAX משחרר רק 1.0/day** — רחוק מ-2–3.
9. **TPO snapshots כל 30 דקות וחלק מימים מקוצרים** — location lag.
10. **CVD רק 29/34 ימים** — D missing בחמישה.

### P1 · תזמון

11. אין Candidate Lifecycle מפורש.
12. אין `time_from_extreme` / `time_from_acceptance` בחוזה.
13. אין intrabar aggressor-confirm shadow מחובר ל-candidate.
14. אין מודל שמדרג candidate לפני תפיסת-הסלוט.

### P1 · תבניות

15. HNS/iHNS כמעט עיוורות.
16. RE_PULLBACK מזהה 26 אך raw ‎−$2,021 — timing/context שגויים.
17. OPENING 71/raw ‎−$4,739 — חייב context, לא הרחבה.
18. HLST נכון שהוסרה: 84/raw ‎−$4,551.

### P2 · מדידה

19. אין true holdout ל-policy החדש.
20. אין ייחוס-תרומה לכל candidate/feature.
21. אין EOD scorecard: coverage · precision · lag · MFE-after-reject ·
    selected-vs-not-selected · realized books.

---

## 9 · תוכנית-משימות

### Phase 0 — לנעול אמת (לפני כל ירי חדש)

1. לסיים A6 ולהוכיח 5 עסקאות חדשות רצופות MATCH.
2. לרשום 100% מה-candidates לפני השערים:
   `candidate_id, family, pattern, bar_ts, event_ts, regime, phase, location,
   volume_features, cvd_reading, stop, targets`.
3. לתקן Flag Registry + `gen_flag_index --check`.
4. להוסיף replay-preflight: bar cardinality/continuity · CVD coverage · TPO
   causality · no-final-VA.

### Phase 1 — `CONTEXT_ENTRY_V1` (default OFF → shadow)

5. להשלים Structural Binary (EOD, DD-refill, phase/direction).
6. לחווט B-in-BALANCE / D-in-DISCOVERY כ-**selector**.
7. לחייב existing confirmation:
   - REV: REACTIVE/neck break/rejection-confirm.
   - CONT: break-retest/pullback/stair confirmation.
8. stop beyond structural extreme; target opposite edge / structural trail.
9. רוטציות BALANCE ללא מכסת-יום, אבל סלוט אחד.

### Phase 2 — לתקן כיסוי-היפוכים

10. לפרק 320 REV misses לפי B/C/D × day-type × reason.
11. HNS_TOP: ניסוי 2-peaks+neck ב-replay בלבד.
12. RE_PULLBACK: לשלב רק אחרי DISCOVERY acceptance, לא raw.
13. להוסיף `event→candidate lag` ו-MFE/MAE לכל miss.

### Phase 3 — timing/ranking

14. `OpportunityDatasetV1` + grouped walk-forward by session.
15. Logistic/GAM REV+CONT בצל.
16. scheduler: rank same-bar candidates; candidate expires על invalidation.
17. 60-second aggressor flow כ-confirmation shadow — לא touch entry.

### Phase 4 — gate

18. ≥10 forward shadow sessions.
19. רק אם כל הקריטריונים למטה ירוקים — פסיקת מעבר.
20. 2-slot נשאר ניסוי shadow נפרד; אין קשר אוטומטי ל-live.

---

## 10 · קריטריוני-קבלה

### Data

- 5 עסקאות חדשות רצופות broker/books MATCH.
- 0 `incomplete` חדש.
- CVD aligned coverage ≥90% מהברים או `MISSING` כנה.
- 0 lookahead levels.

### Coverage/timing

- overall coverage **≥45%** (היום 30.6%).
- REV coverage **≥35%** (היום 22%).
- unmatched candidates <50% (היום 500/688 = 72.7%).
- median event→candidate ≤1 bar.
- ≥1.5 valid trades/day בשלב ראשון; **לא** מכסה כפויה 2–3.

### Money (§D)

- 4c ו-6c.
- s0/s1/s2 כולם חיוביים.
- chronological OOS חיובי.
- median day ≥0.
- worst day לא גרוע מ-current.
- אף יום בודד לא מסביר >35% מהרווח.

### Safety

- hard gates לעולם לא נעקפים.
- ranker advisory/shadow בלבד עד פסיקה.
- 2-slot לא live.

---

## 11 · Rule-5 — פקודות ופלט גולמי

```bash
python3 scripts/replay_maximized_opportunity.py \
  --json /tmp/maximized_opportunity_20260823.json
```

```text
[data] sessions=34 2026-07-07..2026-08-21 cvd_days=29 tpo_days=34
CURRENT_ALL n=234 t/day=6.88 win=41.9% $-3615.40 med/day=-82.12
MAX_CONTEXT n=34 t/day=1.00 win=41.2% $+339.00 med/day=0
MAX_EXPANDED n=34 t/day=1.00 win=41.2% $+339.00
MAX_2SLOT n=43 t/day=1.26 win=46.5% $+824.25
coverage current=218/712 (30.6%), candidates=688, unmatched=500
shadow: TREND_STEP=113, S2_DELTA_DBL=25
```

```bash
BRIDGE_TOKEN=test DATABASE_URL=postgresql://localhost/mems26 \
python3 -m pytest tests/v9/regression/test_replay_cvd_timestamptz.py -q
```

```text
3 passed, 2 warnings in 0.18s
```

```bash
python3 scripts/gen_flag_index.py --check
```

```text
exit 1 — undocumented:
DOUBLE_TOP_ADAM_FIX_V1 · S1_STRUCTURAL_BINARY_V1 · S2_DELTA_DBL_V1 ·
SCALE_IN_P3_V1 · TARGET_MIN_SPACING_V1 · ... (56 total)
```

---

## 12 · שורה-תחתונה למייקל

**המערכת שכדאי לבנות היא Contextual Opportunity Router, לא עוד detector ולא
"AI שיורה".** S1 אומר איפה ובאיזה משטר; S2/S4 אומרים שהגיאומטריה אושרה;
ranker קטן בוחר מי מקבל את הסלוט; gateway שומר על הכסף.

הבדיקה הנקייה מהירים בפועל אומרת:

- עיניים: **30.6% כיסוי**, לא 16%, אבל REV רק 22%.
- בלי מוח: 6.88/day ו-‎−$3,615.
- עם מוח: 1.0/day ו-+$339 — כיוון נכון, עדיין לא חזק מספיק ל-live.
- שני סלוטים: 1.26/day ו-+$824 — מעניין ל-shadow, לא פסק-לייב.

לכן סדר-הכסף הוא: **אמת-ספרים → Candidate Journal → CONTEXT_ENTRY shadow →
תיקון REV recall → ranker shadow → רק אז דיון ב-2–3 עסקאות/יום.**
