# MEMS26 — תוכנית-ביצוע מתוקנת לתשתית-מקסום (2026-08-24)

**מקור:** מנדט מייקל + `COWORK_REVIEW_CURSOR_PLAN.md` + ממצאי T-99/T-100.  
**מצב:** תוכנית לפני קוד. אין שינוי-ירי, `.env`, DB או שירותים מכוחה.

## פסק

הערות cowork מתקבלות:

1. Candidate Ledger ראשון.
2. סיבתיות TPO/CVD שנייה.
3. SCID הוא validator; DB נשאר מקור-הקריאה של live/replay ומתוקן אחרי RCA.
4. S1 בינארי shadow ≥10 סשנים לפני החלפה.
5. `CONTEXT_ENTRY_V1` pure function אחת ל-replay/shadow/live.
6. ranker חסום עד ≥300 outcomes נקיים.

**הסתייגות-בטיחות:** תיקון DB אינו אוטומטי. סדר מחייב:
validator → diff report → root cause → snapshot → migration/repair plan → פסיקה
אם ההתנהגות/מקור-המסחר משתנים → repair → four-axis verification. אין overlay קנוני.

---

## Task 0 · מנוע-רפליי אחד

### הבעיה

בריפו קיימים 31 קבצים בשם `*replay*.py` ו-52 כלי
replay/backtest/study/availability לפי inventory Stage 0A. הם חולקים חלקים,
אך שונים ב:

- מקור-ברים וזמן.
- candidate population.
- day-type/TPO availability.
- stops/targets/ladder.
- slot policy.
- commission/slippage.
- IS/OOS.

זו מחלקת-שורש למספרים סותרים.

### הפתרון

לבנות **Replay Kernel אחד**, לא “סקריפט 44”:

```text
ReplayDataSource
  ├─ ValidatedDBSource        (המקור היחיד לריצות רשמיות)
  └─ SCIDValidator            (השוואה בלבד, לעולם לא policy source)

ReplayCandidateEngine
  └─ imports live S1/S2/S4 detectors

ReplayPolicy
  ├─ current
  ├─ structural-binary
  ├─ context-entry
  └─ named challenger

ReplayExecutionModel
  ├─ size/split
  ├─ stops/targets
  ├─ slippage/commission
  └─ slot policy

ReplayReport
  └─ per-candidate/per-day/hash/manifest
```

הסקריפטים הקיימים הופכים ל-thin scenario adapters. לא מוחקים אותם עד parity.

### Acceptance

- manifest מחייב: data hash · code commit · policy id · feature schema · costs.
- אותה ריצה פעמיים ⇒ JSON hash זהה.
- 5 ימי-anchor: old tool מול kernel נותנים אותה candidate population כאשר
  ההגדרות זהות.
- כל הבדל מוצהר בשמו; אין default סמוי.
- kernel אינו מיובא ב-runtime live.

### בעלים

- Cursor: inventory, contract, parity fixtures, gate.
- cc-macbook: kernel implementation + adapters.
- cowork: independent reproduction + deprecation verdict.

---

## Task 1 · Candidate Ledger

### ADAPT, לא מקור שלישי

להרחיב את מסלול `v9_five_min_setups` + decision archive כך שכל candidate יירשם
**לפני** gateway:

- `candidate_id` דטרמיניסטי.
- `source` · `pid` · `mode` · `code_commit` · `policy_id`.
- system/pattern/direction.
- detected_at · confirmed_at · decision_at.
- day label/determined/phase/direction.
- location + levels + `level_available_at`.
- volume/CVD reading.
- stop/targets/size intent.
- gate outcome + blocker.
- MFE/MAE 3/6/12 bars + resolved outcome.

Ledger הוא תצפית בלבד; הוא אינו מסנן או מנתב.

### Acceptance

- candidate ידוע שנחסם מופיע עם blocker.
- revert של hook ⇒ הרשומה נעלמת (anti-tautology).
- pytest מייצר **0** שורות ב-production path.
- כל שורה כוללת source/pid/commit.
- candidate נרשם פעם אחת; dedup key מפורש.

### בעלים

- cc-macbook: schema/hook/EOD outcome.
- Cursor: contract + tests + coverage scorecard.
- cowork: live shadow verification.

---

## Task 2 · TPO causality + deterministic CVD

### TPO

- החלטה יכולה לקרוא level רק אם `available_at <= decision_at`.
- `ts` הוא market timestamp; `created_at` אינו תחליף קבוע ל-available_at.
- writer חייב לכתוב `market_ts` + `available_at` מפורשים.
- backfill מסומן `historical_backfill=true` ואסור לו להיראות live-causal.

### CVD

- מפתח יחיד: `(symbol, bar_ts, source_version)`.
- conflict policy דטרמיניסטי; לא `ORDER BY ts` בלבד.
- 5m delta/CVD נבנה מאותו writer שה-live צורך.
- SCID משמש validator; לא CVD-engine מקביל.

### Acceptance

- 0 TPO reads עם `available_at > decision_at`.
- 0 conflicting current-version CVD rows.
- rerun hash זהה.
- coverage מפורש; missing נשאר MISSING.

### בעלים

- cc-macbook: writer/schema/backfill/repair.
- Cursor: causal replay + conflict tests.
- cowork: DB/SCID comparison.

---

## Task 3 · DB↔SCID validator ואז DB repair

### Validator

פר-סשן:

- 78 RTH bars.
- exact timestamps/grid.
- OHLC/volume.
- delta/CVD.
- missing/duplicate/shifted/value-drift.
- Sierra-feature availability (CCI/LSMA/EMA/TPO) מדווח בנפרד.

### Repair

DB נשאר המקור היחיד שהמערכת והרפליי קוראים. SCID מוכיח drift; הוא לא עוקף DB.

סדר:

1. diff report.
2. RCA per drift class.
3. snapshot.
4. dry-run repair.
5. פסיקה אם מקור/התנהגות משתנים.
6. repair.
7. Quality/Recency/Cardinality/Latency.

### Acceptance

- 34/34 ×78 bars.
- 0 seams.
- 100% timestamp alignment.
- OHLC/volume tolerance מוגדר ומקודד.
- DB query ו-live replay צורכים אותה טבלה/reader.

### בעלים

- Cursor: validator + report.
- cc-macbook: ingest/root fix + migration.
- cowork: post-repair verification.

---

## Task 4 · S1 structural binary — shadow

- להשלים EOD ו-DD-neck-refill.
- `determined/label/direction/event`, בלי confidence לצרכנים.
- shadow מול classifier הקיים ≥10 סשנים.
- acceptance reference נשאר `daily_extremes_playbook`; לא משנים target תוך בדיקה.

### Acceptance

- convergence ≥80%.
- event transitions בלבד.
- restart parity.
- 0 consumer behavior change ב-shadow.

**החלפת התווית החיה = trading-surface ⇒ פסיקת מייקל.**

---

## Task 5 · `CONTEXT_ENTRY_V1`

Pure function אחת:

```text
ContextEntryInput
  candidate + structural_state + location + available levels + flow

ContextEntryOutput
  ALLOW/SKIP/WAIT/EXPIRE + reason + stop/target policy
```

- BALANCE: B/location + existing REACTIVE confirmation.
- DISCOVERY: D/context + with-direction continuation.
- `stop_anchors` נשאר authority.
- אין ranker בשלב זה.

### Acceptance מרכזי

**אותו serialized input ⇒ output זהה-בייט** ב:

- unit test
- replay adapter
- shadow live adapter

נוסף:

- flag OFF = byte-identical.
- replay §D חיובי בכל 4/6c×s0/s1/s2.
- shadow ≥10 סשנים.

**הדלקה = trading-surface ⇒ פסיקת מייקל.**

---

## Task 6 · Ranker — BLOCKED

אין קוד עד:

- ≥300 candidate outcomes מה-Ledger הנקי.
- forward OOS נפרד.
- session-block bootstrap.
- candidate/feature schema קפוא.

עד אז scheduler דטרמיניסטי ומוסבר.

---

## סדר-ביצוע

```text
0. Replay Kernel inventory/spec
1. Candidate Ledger
2. TPO/CVD causality
3. DB↔SCID validator + repair
4. S1 binary shadow ≥10 sessions
5. CONTEXT_ENTRY replay → shadow
6. Ranker only after ≥300 clean outcomes
```

Tasks 0–3 תשתית/מדידה בלבד. Tasks 4–5 נבנים flag-OFF/shadow.

---

## שער-עצירה

עוצרים אם:

- נוצר מקור-אמת שני.
- replay/live משתמשים בפונקציות שונות.
- מספר-$ נבנה מ-populations שונות.
- future-created level נכנס לרפליי.
- DB repair מתבצע בלי snapshot/dry-run.
- ranker מתחיל לפני שער-300.

