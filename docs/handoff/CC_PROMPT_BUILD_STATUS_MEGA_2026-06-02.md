# CC PROMPT — Build Status MEGA Upgrade (UX + Bridge-Field Inventory + D-RDY)

פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.

**תאריך:** 2026-06-02 · **מקור:** Cowork (Michael) · **מצב:** SHADOW · Rule 5 ·
**אפס שינוי order/risk/sizing** · Build Status = observability + readiness verdict בלבד
(לא חישוב מסחר). **strategic-stop** לפני כל שינוי שנוגע ב-decision/auth-table/firing.

> Reconcile, do NOT duplicate: prompt קודם
> `docs/handoff/CC_PROMPT_RELATIVE_IN_PATTERNS_BRIDGE_INVENTORY_2026-06-01.md` §2
> ביקש "Bridge Data Inventory" panel. הדליברבל
> `docs/reports/RELATIVE_IN_PATTERNS_BRIDGE_INVENTORY_2026-06-01.md` **לא קיים** בריפו
> (אומת ב-Glob — no file). פרומפט זה הוא ה-superset: אם נעשתה עבודה חלקית, להרחיב אותה,
> לא לבנות מחדש. אם נבנה panel — לאמת מול הטבלה ב-Phase 2 ולסגור פערים.

---

## רקע ועובדות שאומתו (file:line — VERIFY-BEFORE-TRUST)

מצב נוכחי של ה-Build Status (קוד שנקרא 2026-06-02):

1. **Backend מייצר 5 systems** — `aggregator.py:113`
   (`bridge, five_min, footprint, woodies, day_type`). כל inspector מחזיר `SystemStatus`.
2. **bridge_inspector ממלא `global_gates`** (8 streams) ב-`bridge_inspector.py:137-145`
   עם `key/spec/present/value/live/required/freshness`.
3. **🔴 BUG מרכזי — ה-`global_gates` לא מרונדרים בכלל בפרונט.**
   `SystemSection.tsx` מרנדר רק `live_inputs` (167-195) + `interpretations` + `patterns` table
   (198-249). אין שום `system.global_gates.map(...)` בקוד הפרונט (אומת ב-Grep:
   `global_gates` ב-`**/*.tsx` → No matches). לכן section ה-Bridge מציג
   header בלבד + טבלת patterns **ריקה** (`bridge_inspector.py:191` `patterns=[]`) —
   כל ה-stream freshness שה-inspector טרח לחשב **בלתי-נראה למשתמש**. זהו ה-finding מס' 1.
4. **D-RDY readiness verdict — לא ממומש.** `BuildStatusResponse` (`types.py:123-129`)
   אין בו שדה `readiness`. Grep ל-`readiness|READY|DEGRADED|BLOCKED` תחת `build_status/`
   → No files. ה-PRE_TRADE_PROTOCOL קיים (`docs/runbooks/PRE_TRADE_PROTOCOL.md`) אך
   אף שלב שלו לא רץ אוטומטית בתוך ה-endpoint.
5. **Refresh ידני בלבד** — `useBuildStatus.ts:15-19` ("manual refresh only, no auto-poll",
   Michael 2026-05-26). אין auto-poll. שמור את ההחלטה הזו (אל תפר את ה-polling floors).
6. **streams ב-bridge_inspector** (`bridge_inspector.py:30-39`): `woodies_5min, footprint,
   cumulative_delta, volume_profile, tick_reversal, imbalance, tpo_bars, 5min_bars`.
   חסרים מ-Build Status (קיימים כ-streams ב-`bridge/v9_streams/`): **`live_price`**
   (`live_price_stream.py` — price/bid/ask/vol, push 200ms),
   **`5min_continuous`** (`bars_5min_continuous_stream.py`),
   **`cvd_continuous`** (`cvd_continuous_stream.py`),
   **`stacked_imbalances`** (`stacked_imbalances_stream.py`),
   **`woodies_30min`** (legacy, replay בלבד — לדלג).
7. **שדות per-stream שלא נחשפים אטומית** — ה-bridge_inspector בודק רק `MAX(ts)` freshness
   per-table, לא את **השדות בתוך הבר**. דוגמה מאומתת: stream `woodies_5min`
   (`woodies_5min_stream.py:8-12`) נושא 15 שדות:
   `cci_14, cci_6_tcci, lsma_value, swi_value, czi_value, ema_34, trend_state,
   predictor_next_cci, zlr_detected, zlr_direction` + OHLCV. כרגע ה-Build Status מציג
   את ה-stream כ-"FRESH 3s ago" אבל **לא** אומר אם `trend_state` תקוע GRAY או
   `predictor_next_cci` null — בדיוק הכשל מ-PRE_TRADE_PROTOCOL שורה 68
   (trend תקוע GRAY → A1 חוסם 9 תבניות).

---

## מטרה אחת

לשדרג את ה-Build Status מ-"per-system pattern debug" ל-**at-a-glance operator readiness
board**: (A) UX/UI שמראה ARMED/BLOCKED ברורות + מרנדר את ה-bridge streams שכבר נאספים;
(B) **Bridge Field Inventory** מלא — כל שדה חי → ערך → מערכת צורכת → תבנית → freshness;
(C) **D-RDY readiness verdict** (READY/DEGRADED/BLOCKED) שמריץ את PRE_TRADE_PROTOCOL Phase 0-4.

חלוקה ל-phases אטומיים. לכל phase: Acceptance בינארי + פקודת אימות + "if reverted → RED".

---

## Phase A · UX/UI — render bridge gates + readiness hierarchy

### A1 — render `global_gates` (ה-bug המרכזי)
- **קובץ:** `frontend/v9/src/v9/components/build_status/SystemSection.tsx`.
- הוסף בלוק רינדור ל-`system.global_gates` (קיים ב-`types.ts:97` `SystemGate[]` —
  לא צריך שינוי טייפ). מתחת ל-header, מעל טבלת ה-patterns. כל gate:
  `key · live · required · present(✓/✕) · FreshnessPill`. השתמש מחדש ב-`FreshnessPill`
  מ-`ComponentTable.tsx:11` (export אותו או extract למודול משותף — smallest change).
- **קוד צבע סטטוס** לכל gate: FRESH=ירוק (`COLORS.bull`), STALE=ענבר (`COLORS.warning`),
  DEAD/ERROR=אדום (`COLORS.bear`). כרגע ה-`value` כבר נושא `[FRESH]/[STALE]/[DEAD]`
  (`bridge_inspector.py:126`) — לפרסר את הסטטוס מ-`live`/`value` או (עדיף) להוסיף שדה
  `status` מפורש ב-backend (ראה A3).
- **Acceptance:** עם payload שבו ל-`bridge` יש `global_gates` לא-ריק, ה-section מציג
  N שורות gate עם pill freshness. ל-section עם `global_gates=[]` (S2 כיום) אין רגרסיה.
- **אימות:** snapshot/RTL test שמרנדר `SystemSection` עם fixture בו
  `global_gates=[{key:"woodies_5min",present:true,live:"3s",required:"< 90s",...}]`
  ומאשר `getByText("woodies_5min")` + pill ירוק. **if reverted → RED because**
  הסרת בלוק הרינדור → ה-gate לא מופיע → `getByText` נכשל.

### A2 — readiness banner בראש הטאב
- **קובץ:** `BuildStatusTab.tsx` (header ב-22-94).
- מעל ה-systems, באנר בודד גדול: `READY` (ירוק) / `DEGRADED` (ענבר) / `BLOCKED` (אדום)
  + שורת סיבה אחת (`readiness.reason`) + רשימת הבדיקות שנכשלו. זה ה-at-a-glance
  שהאופרטור רואה ראשון. תלוי ב-Phase C (backend verdict).
- **Acceptance:** payload עם `readiness.verdict="BLOCKED"` → באנר אדום + הסיבות.
  payload בלי `readiness` (backward-compat) → הבאנר לא נשבר (מציג "readiness: n/a").
- **אימות:** RTL test, fixture `verdict="DEGRADED"` → `getByText(/DEGRADED/)`.
  **if reverted → RED:** הסרת הבאנר → assertion נכשל.

### A3 — information hierarchy + צבע/סטטוס סמנטיקה
- היום ה-freshness של ה-**system** מוצג כ-"lag {n}s" בלבד (`SystemSection.tsx:12-30`)
  ללא ספי STALE/DEAD ברמת המערכת (ColorTable יש רק ב-component-level). יישר:
  הוסף ל-`FreshnessIndicator` סף צבע זהה ל-`FreshnessPill` (fresh<60s ירוק /
  stale ענבר / dead אדום), לא רק boolean `fresh`.
- **הוסף ל-`DataFreshness`** (backend `types.py:47`) שדה אופציונלי `status:
  Literal["FRESH","STALE","DEAD"]` כדי שהפרונט לא ינחש מסף. additive — ברירת מחדל None.
- **Acceptance:** section עם `lag_seconds=400, threshold=360` מציג אדום, לא ירוק.
  **אימות:** RTL fixture; **if reverted → RED.**

### A4 — collapse/scan ergonomics (קטן)
- ה-"Show only blockers" (`BuildStatusTab.tsx:20`) ברירת מחדל `true` — שמור.
- הוסף ל-system header באדג' `READY/DEGRADED/BLOCKED` per-system (מצרף את ה-gates שלו)
  כדי שאופרטור יראה איזו מערכת חוסמת בלי לפתוח. **אימות:** RTL.

> ⚠️ **אל תיגע** ב-polling floors / `useBuildStatus` manual-refresh decision
> (`useBuildStatus.ts:15-19`, CLAUDE.md "Frontend Polling Floors"). אם תרצה auto-poll —
> **strategic-stop + אישור Michael**.

---

## Phase B · Bridge Field Inventory (ה-deliverable המרכזי)

צור פאנל/section **"Bridge Field Inventory"** (אפשר כ-system נוסף `id="bridge_fields"`
מ-aggregator, או הרחבת ה-bridge section עם sub-rows per field). המקור הוא ה-streams
ב-`bridge/v9_streams/` + ה-DB sink tables. לכל **שדה** (לא רק stream):
`field · live value · freshness(age/FRESH/STALE/DEAD) · source(stream/chart) ·
consuming system(S1-S6) · pattern(s) שצורכות אותו`.

**B0 — strategic-stop:** הצג ל-Michael את הטבלה המלאה (להלן, השלם ערכי live מ-DB/state)
**לפני** מימוש מלא, לאישור היקף. זו observability — אבל היקף ה-fields גדול ומיפוי
field→pattern נוגע ב-decision wiring (קריאה בלבד, אך לאשר שהמיפוי נכון).

**B1 — מקור אמת:** השדות מ-`woodies_5min_stream.py:8-12` (15 שדות), VAP/footprint
מ-`footprint_stream.py` + `vap_recompute.py`, volume_profile (POC/VAH/VAL),
cumulative_delta (`cvd_continuous_stream.py`), live_price (`live_price_stream.py:185-191`:
price/ts/bid/ask/vol), day_type מ-`v9_day_type_history`. **אסור לסנתז** — אם השדה null
ב-DLL/DB, להציג `missing`/`—` (CLAUDE.md Rule 1). freshness לכל שדה מ-`row_helpers.make_freshness`.

### טבלת Bridge Field Inventory (להשלים `live` בזמן ריצה; consumer/pattern אומתו מהקוד)

| # | Field | Stream / source | DB table | Consuming system | Pattern(s) | Freshness anchor |
|---|-------|-----------------|----------|------------------|-----------|------------------|
| 1 | `price` | live_price.json | (in-mem / WS) | all / TopBar | — (context) | live_price.ts (200ms) |
| 2 | `bid` / `ask` | live_price.json | — | spread/exec | — | live_price.ts |
| 3 | `vol` (tick size) | live_price.json | — | — | — | live_price.ts |
| 4 | OHLCV 5min (`o/h/l/c/vol`) | bars_5min | `v9_bars_5min` | S2 | all 10 S2 patterns | ts |
| 5 | `cci_14` | woodies_5min | `v9_bars_5min_woodies` | S4 + S2 (CCI hist) | ZLR,TLB,TT,GB100,Vegas,Ghost,FaMir,HTLB,HFE | ts / in-mem |
| 6 | `cci_6_tcci` (TCCI) | woodies_5min | ↑ | S4 | TT, ZLR, FaMir | ts |
| 7 | `lsma_value` | woodies_5min | ↑ | S4 | TLB, HTLB | ts |
| 8 | `swi_value` | woodies_5min | ↑ | S4 | trend confirm | ts |
| 9 | `czi_value` | woodies_5min | ↑ | S4 | trend confirm | ts |
| 10 | `ema_34` | woodies_5min | ↑ | S4 | TLB, HFE | ts |
| 11 | `trend_state` (BLUE/RED/GRAY/YELLOW) | woodies_5min | ↑ | S4 **A1 gate** | **all 9 (veto)** | ts — 🚩 stuck-GRAY |
| 12 | `predictor_next_cci` | woodies_5min | ↑ | S4 | informational | ts |
| 13 | `zlr_detected` / `zlr_direction` | woodies_5min | ↑ | S4 | ZLR, FaMir | ts |
| 14 | `POC` | volume_profile | `v9_bars_volume_profile` | S1/S5 | day-type context, SR | ts |
| 15 | `VAH` / `VAL` | volume_profile | ↑ | S1/S5 | value-area patterns | ts |
| 16 | `ib_high` / `ib_low` / width | tpo / day_type machine | `v9_day_type_history` | **S1 (lock)** | day_type classification | last_updated_at |
| 17 | `opening_type` (OPEN_DRIVE…) | day_type machine | `v9_day_type_history` | **S1 → S2 gate** | S2 reactive/initiative | last_updated_at |
| 18 | `day_type` (Neutral_Center…) | day_type machine | `v9_day_type_history` | **S2 auth-table + S4 matrix** | all S2 + S4 gating | last_updated_at |
| 19 | footprint bid×ask / delta per level | footprint (VAP) | `v9_bars_footprint` | S3 | absorption, stacked_imb, sweep_return, exhaustion | ts |
| 20 | `cumulative_delta` / divergence | cumulative_delta | `v9_bars_cumulative_delta` | S3 / S1 CVD-opening | exhaustion, opening shadow | ts (CVD points `t`) |
| 21 | `tick_reversal` bars | tick_reversal_12/15 | `v9_bars_tick_reversal` | S3 | reversal detection | ts |
| 22 | `imbalance` flags | imbalance_flags | `v9_bars_imbalance` | S3 | stacked_imbalance | ts |
| 23 | `stacked_imbalances` | stacked_imbalances | (verify table) | S3 | stacked_imbalance | ts |
| 24 | TPO letters / period | tpo | `v9_tpo_bars` | S5 | TPO structure | ts |
| 25 | 5min_continuous (24h OHLC) | bars_5min_continuous | (verify table) | charting / overnight | — | ts |

> **CC: לכל שורה אמת את ה-DB table ואת ה-consuming system בקוד** (grep למי קורא את השדה
> ב-`backend/v9/systems/`), אל תעתיק מהטבלה בעיוורון — זו טבלת התחלה מ-Cowork, חלק
> מהמיפויים (23,25 `verify table`) טעונים אימות. כל שורה שלא ניתן לאמת consumer → סמן
> `consumer=unknown`, אל תמציא (Rule 1).

### B2 — stale-awareness per field
לכל שדה: אם `freshness.lag_s > stream_threshold` → סמן STALE; אם null/missing → `missing`.
במיוחד שדה 11 `trend_state`: הוסף **interpretation** מפורש "trend_state=GRAY → A1 blocks all
9 Woodies patterns" (זה כבר חצי-קיים ב-`woodies_inspector.py:165-169` כ-`trend_meaning`,
אבל לא מסומן כ-readiness blocker). חבר ל-Phase C.

**Acceptance Phase B:** Build Status מציג ≥ 20 שדות (לא רק 8 streams) עם
field/value/system/pattern/freshness. שדה null מ-DB מוצג `missing` (לא ערך מסונתז).
**אימות:** (1) `curl -s localhost:8000/api/v9/build/pattern-status | python3 -c "import
sys,json; d=json.load(sys.stdin); print([g['key'] for s in d['systems'] if
s['id'].startswith('bridge') for g in s.get('global_gates',[])])"` → ≥20 keys.
(2) טסט backend שמזריק row עם `cci_14=None` ומאשר שה-field row מחזיר `live="missing"`/
`null` ולא ערך מחושב. **if reverted → RED because** אם מחזירים synthetic → הטסט רואה
ערך מספרי במקום `missing`.

---

## Phase C · D-RDY readiness gate (verdict חדש)

### C1 — schema additive
- **קובץ:** `backend/v9/systems/build_status/types.py`.
- הוסף:
  ```python
  ReadinessVerdict = Literal["READY", "DEGRADED", "BLOCKED"]
  class ReadinessCheck(BaseModel):
      key: str            # e.g. "bridge_streams_fresh", "s1_day_type_classified"
      passed: bool
      severity: Literal["block", "degrade", "info"]
      detail: Optional[str] = None
  class Readiness(BaseModel):
      verdict: ReadinessVerdict = "BLOCKED"
      reason: str = ""
      checks: List[ReadinessCheck] = Field(default_factory=list)
  ```
- ל-`BuildStatusResponse` הוסף `readiness: Readiness = Field(default_factory=Readiness)`.
  **additive** — צרכנים ישנים לא נשברים.

### C2 — aggregator מריץ את ה-checks
- **קובץ:** `aggregator.py` (`get_status`, אחרי בניית `result_systems`, לפני `return` ב-225).
- מימוש מיפוי PRE_TRADE_PROTOCOL Phase 0-4 → checks (קריאה בלבד, אפס side-effects):
  - `bridge_streams_fresh` (block) — כל ה-STREAM_CHECKS ב-FRESH/STALE, אף DEAD ב-RTH.
  - `s1_day_type_classified` (degrade) — `day_type_str not in (None,UNKNOWN)` (כבר נקרא ב-`aggregator.py:119`).
  - `s1_ib_locked` (degrade) — מ-day_type inspector `ib_locked`.
  - `s4_trend_not_stuck_gray` (degrade) — `trend_state in {BLUE,RED}` (PRE_TRADE שורה 68).
  - `s2_opening_type_set` (degrade) — `opening_type != NA` (PRE_TRADE שורה 69).
  - `in_rth` (info) — מ-`_compute_rtb_session`.
- **verdict:** BLOCKED אם נכשל check severity=block; DEGRADED אם רק degrade נכשל;
  READY אם הכל עבר. `reason` = ה-check הראשון שחוסם.
- **RTH-aware:** מחוץ ל-RTH "bridge DEAD" לא חוסם (badge "overnight"), בהתאם ל-PRE_TRADE
  שורות 34,49. תעד את ה-TZ של החלון במפורש (CLAUDE.md Rule 4 — ET, לא "assumed").

**Acceptance Phase C:**
- `curl -s …/build/pattern-status | python3 -c "import sys,json;
  print(json.load(sys.stdin)['readiness']['verdict'])"` מחזיר אחד מ-READY/DEGRADED/BLOCKED.
- כשמזריקים day_type=UNKNOWN → verdict לא READY ו-`checks` כולל
  `s1_day_type_classified passed=false`.
**אימות (anti-tautological):** טסט שמייבא `BuildStatusAggregator`, מזריק
`day_type_machine`/DB stub עם `trend_state="GRAY"`, קורא `agg.get_status()` האמיתי,
ומאשר `result.readiness.verdict != "READY"` ו-check `s4_trend_not_stuck_gray.passed
== False`. **if reverted → RED because** אם מסירים את לוגיקת ה-verdict (מחזירים תמיד
READY) → ה-assert על `!= READY` נכשל. אסור להעתיק את לוגיקת ה-verdict לטסט — להריץ
את ה-aggregator האמיתי.

### C3 — frontend באנר (תלוי A2)
- חבר את `data.readiness` לבאנר מ-A2. הוסף `readiness?: Readiness` ל-
  `BuildStatusResponse` ב-`types.ts:113`.

---

## risk surface — אסור לגעת
- אפס שינוי ב-`order/risk/sizing` או ב-firing/auth-table/decision-tree logic.
- אל תשנה `STREAM_CHECKS` thresholds בלי לתעד מקור (כרגע: woodies/footprint/tick/imb=90s,
  cvd/vap/tpo/5min=360s — `bridge_inspector.py:30-39`).
- אל תיגע ב-`useBuildStatus` manual-refresh ולא ב-polling floors (CLAUDE.md).
- D-RDY = קריאה בלבד. **אל יחסום מסחר בפועל** — verdict זה תצוגה לאופרטור, לא gate
  שמונע fire. (אם Michael ירצה gate אמיתי שמונע fire — strategic-stop נפרד.)
- כל ts spec (חלון RTH 09:30-16:00) — לתעד ET מפורש (Rule 4).

---

## ADDITIONS FROM SYSTEM AGENTS

קופל מחמשת דוחות האבחון (2026-06-02). כל שדה כאן חייב לבוא מהצרכן האמיתי
(source-of-truth) — לא לסנתז. אם המקור `None`/חסר → להציג "missing" (Rule 1).

### מ-S1 (Day-Type) — `s1_inspector` / `day_type_inspector`
- להציג את ה-`interpretations` החיים שכרגע **נבלעים** בגלל באג `ib_class.width`
  (AttributeError ב-`day_type_inspector.py:76`, נבלע ב-`except: pass:78`) — לתקן
  השם ל-`ib_width` ולחשוף: `day_type`, `opening_type`, `behavior`, `ib_width_class`.
- `atr_daily` עם דגל null/source (כרגע תמיד None — `main.py:230-244`; חשוב שהאופרטור
  יראה שהקלט מת ולא יסמוך על EXTREME מזויף).
- `shadow_day_type` מול ה-live (סטיית D-S1DYN) + `session_min` + `re_eval_armed` (bool).
- `bar_count` אמיתי **אחרי dedup** (כרגע מנופח מ-double process_bar, `main.py:191-194`).

### מ-S2 (Five-Min/Reactive) — `s2_inspector`
- בלוק `reactive_variants` לכל וריאציה A/B/C: `armed` (האם הגייט-לבד עבר היום),
  `blocked_reason` ∈ {`volume_gate_unreachable`,`cot_amt_missing`,`nt_no_trade`,
  `day_type_skip`,null}, `last_eval_ts` (proof-of-life של הדיטקטור), `fired_today`,
  `fires_count`, `last_fire_ts`. צבע: ירוק=fired / צהוב=armed / אפור=blocked + tooltip.

### מ-S4 (Woodies) — `woodies_inspector`
- `trend_state` **אחרי relabel** (להבטיח שמקור התצוגה הוא `studies` הפוסט-relabel,
  לא ה-current_state התקוע — ראה דוח S4 פער #1).
- `bar_count` — להוסיף את `self._bar_count` ל-update ב-`woodies_system.py:425` (חסר היום).
- per-pattern `blocked_reason` — למפות מ-`dt_summary["failed_stages"]/["pending_stages"]`
  (מ-`StageResult.message`, לא להמציא).

> ⚠️ כל התוספות האלו **read-only/observability**. אל תשנה לוגיקת מסחר. תיקוני המקור
> עצמם (atr_daily, dedup, dispatcher single-source, reactive wiring) הם **פרומפטים נפרדים**
> (S1/S2/S4 audit 2026-06-02) — כאן רק לחשוף את מה שכבר קיים + מה שאותם תיקונים יספקו.

---

## דוח חובה (חלק C של החוזה)
1. טבלת phases: `Phase · Status(DONE/PARTIAL/NOT-DONE) · Evidence(command+output) · Deviation`.
2. לכל טסט שורת "if reverted → RED because ___".
3. סעיף **NOT DONE / DEVIATIONS** (גם אם "none").
4. **Open / מה נשאר.**
5. עדכן `docs/plans/ROADMAP_TO_LIVE.html` + `docs/plans/STATUS_BOARD.md`
   (root→fix→verification, CLAUDE.md Reporting Workflow).

## שערים (strategic-stop)
- **B0** — הצג Bridge Field Inventory table לאישור היקף לפני מימוש מלא.
- **C2** — אם תרצה ש-D-RDY יחסום fire בפועל (לא רק תצוגה) — עצור ושאל.
- **A** — אם תרצה auto-poll במקום manual refresh — עצור ושאל.
