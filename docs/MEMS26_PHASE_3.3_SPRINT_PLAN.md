# MEMS26 — Phase 3.3 Sprint Plan
## Backend Implementation Sprint (8-10 May 2026)

**Sprint dates:** Friday 8 May → Sunday 10 May 2026 (3 days)
**Sprint goal:** Deploy V3 Day Type Classifier + Status Layer + Smart Entry
**LIVE target:** 21 May 2026 (T+11 days from sprint end)
**Pure Observation ends:** 7 May EOD

---

## 📑 Table of Contents

1. [Sprint Goals](#1-goals)
2. [Pre-Sprint Checklist (7/5 EOD)](#2-pre-sprint)
3. [Day 1 (8/5) — Universal Filters + Migration](#3-day-1)
4. [Day 2 (9/5) — Day Type Classifier + Smart Entry](#4-day-2)
5. [Day 3 (10/5) — Status Layer + A/B Validation](#5-day-3)
6. [CC Prompts (ready to paste)](#6-cc-prompts)
7. [Acceptance Criteria](#7-acceptance)
8. [Risk Register](#8-risk)
9. [Demo-to-LIVE Checklist (11-21/5)](#9-demo-live)

---

<a name="1-goals"></a>
## 1. Sprint Goals

### Must Hit (LIVE 21/5 Blockers)

```
[ ] V3 Day Type Classifier in production (6 types + hysteresis)
[ ] Time Phase Filter (skip DEVELOPING + OFF_HOURS)
[ ] Special Days protocol (with rollover June 11-18)
[ ] News Calendar 3-tier integration
[ ] Smart Entry (POC + imbalance + Patch 3 timeout)
[ ] Tier R-Multiple sizing (3/2/0 contracts)
[ ] System Status Layer (banner + panel + auto-dim)
[ ] Daily $200 cap enforced
[ ] Manual kill switch tested
```

### Should Hit (LIVE Day 1 ready)

```
[ ] CFG-α + DEVELOPING skip filter validated on Phase 3.2 data
[ ] Per-day-type playbooks deployed in day_config.py
[ ] Hybrid targets (Fixed/Structural/Trail) in /trade/execute
[ ] 30+ DEMO trades validated by 10/5 EOD
[ ] Daily journal PDF auto-generated at EOD
```

### Nice-to-Have (defer if blocked)

```
[ ] TPO Levels Panel UI (Sierra-style vertical price-sorted table)
[ ] Dynamic dashed chart lines (TPO POC/VAH/VAL move with price)
[ ] Cumulative delta histogram
[ ] Single-screen 100% zoom layout (currently 75%)
```

---

<a name="2-pre-sprint"></a>
## 2. Pre-Sprint Checklist (7/5 EOD)

Before Day 1 of sprint can start, must have:

### Code & Specs

- [x] V3 Day Type Spec V3.1 locked (`docs/MEMS26_DAY_TYPE_SPEC_V3.1.md`)
- [x] Playbooks V1 locked (`docs/MEMS26_PLAYBOOKS_V1.md`)
- [x] Status Layer Spec V1 locked (`docs/MEMS26_SYSTEM_STATUS_LAYER_SPEC.md`)
- [x] Tier R-Multiple Spec locked (`docs/TIER_R_MULTIPLE_SPEC.md`)
- [x] V3 Migration ran successfully (4,996 setups → V3)
- [ ] Phase 3.2 Day 5 closeout report (after 7/5)
- [ ] All open theories in `MEMS26_OPEN_THEORIES.md` reviewed

### Environment

- [ ] Branch `feature/mds-v1-viz` merged to `develop` after Day 5 review
- [ ] New branch `sprint3-phase33` created from `develop`
- [ ] Render Backend `mems26-web.onrender.com` health 🟢
- [ ] Netlify Frontend `blasttt.com` health 🟢
- [ ] Bridge running, last 24h uptime 100%
- [ ] Database backup taken (pre-sprint snapshot)

### Communication

- [ ] Day 1 morning standup ready (template below)
- [ ] CC prompts pre-staged (this document, §6)
- [ ] Time-blocked calendar 08:00-18:00 IDT each sprint day

---

<a name="3-day-1"></a>
## 3. Day 1 (Friday 8 May) — Universal Filters + Migration

### 3.1 Day Goal

Deploy the **filter layer** to production: time phases, special days, news, then run V3 migration on the live database.

### 3.2 Morning Standup (08:00 IDT)

```
[Day 1 Standup Template]

Status check:
  Bridge:   🟢 / 🟡 / 🔴
  Backend:  🟢 / 🟡 / 🔴
  Frontend: 🟢 / 🟡 / 🔴

Today's commits target: 4
  Commit 1: time_phase.py + tests
  Commit 2: special_days.py + tests + ROLLOVER constants
  Commit 3: news_calendar.py + ForexFactory fetcher
  Commit 4: prod migration of 4,996 setups + audit log

Blockers: [list any]
```

### 3.3 Tasks

#### Task 1.1 — Time Phase Filter (3h)

```
Goal: Add time_phase classification to every setup
Files (NEW):
  - backend/app/filters/time_phase.py
  - backend/tests/test_time_phase.py
Files (MODIFY):
  - backend/app/main.py (wire filter to setup pipeline)

Logic: 5 phases (PREMARKET/DEVELOPING/RTH/LATE_DAY/OFF_HOURS)
Tests:
  - 09:29 ET → PREMARKET
  - 09:30 ET → DEVELOPING
  - 10:30 ET → DEVELOPING
  - 11:00 ET → RTH
  - 14:30 ET → LATE_DAY
  - 16:00 ET → OFF_HOURS
  - DST transition handling
  
Acceptance:
  - 100% coverage on phase boundaries
  - Setups in PREMARKET/OFF_HOURS rejected with reason="off_hours"
  - Setups in DEVELOPING rejected with reason="developing_phase"
```

→ See CC Prompt #1 in §6

#### Task 1.2 — Special Days Protocol (2h)

```
Goal: Block trading on rollover, holidays, year-end; half-size on Friday PM
Files (NEW):
  - backend/app/filters/special_days.py
  - backend/tests/test_special_days.py

Constants:
  - ROLLOVER_PERIODS_2026 (verbatim from V3 Spec §8.4)
  - YEAR_END_WINDOW
  - CME_EARLY_CLOSE_2026 (placeholder, can be empty initially)

Tests:
  - 2026-06-12 → BLOCKED (rollover)
  - 2026-06-19 → ALLOWED (post-rollover)
  - 2026-12-25 → BLOCKED (year-end)
  - Friday 14:01 ET → half_size flag
  - Friday 13:59 ET → normal
  
Acceptance:
  - Rollover periods enforced
  - Friday PM correctly half-sized (returns flag, not block)
```

→ See CC Prompt #2 in §6

#### Task 1.3 — News Calendar 3-Tier (2.5h)

```
Goal: Fetch ForexFactory calendar daily; block trades around high-impact events
Files (NEW):
  - backend/app/filters/news_calendar.py
  - backend/scripts/fetch_news_daily.py (cron job)
  - backend/tests/test_news_calendar.py

Logic:
  Tier 1 (FOMC/NFP/CPI): block ±15 min
  Tier 2 (GDP/PPI/Retail): block ±5 min
  Tier 3 (Housing/Sentiment): log only

Storage:
  data/news_calendar_<YYYY-MM-DD>.json

Cron: 00:00 IDT daily fetch + cache

Tests:
  - Mock FOMC at 14:00 → block 13:45-14:15
  - Mock GDP at 08:30 → block 08:25-08:35
  - Mock housing at 10:00 → no block, but log
  - Cache hit on same-day repeated calls
  
Acceptance:
  - Cron runs without errors
  - News tier correctly assigned to setups
```

→ See CC Prompt #3 in §6

#### Task 1.4 — V3 Migration on Production DB (1.5h)

```
Goal: Apply V3 day type classification to 4,996+ existing setups
Files (NEW):
  - backend/scripts/migrate_v3_day_types.py
  - backend/migrations/004_add_v3_columns.sql

Procedure:
  1. ALTER TABLE setups ADD day_type_v3, day_type_v3_confidence,
                            time_phase_v3, news_tier_v3,
                            special_day_block_v3 columns
  2. Run reclassify_day_types_v3.py (from Phase 3.2 Day 2 work)
  3. Backfill V3 columns
  4. Validate: 100% non-null

Pre-conditions:
  - DB backup taken
  - Read-only mode for 5 min during migration
  
Acceptance:
  - All existing setups have day_type_v3 populated
  - V2 vs V3 distribution report generated
  - No production downtime > 5 min
```

→ See CC Prompt #4 in §6

### 3.4 Day 1 EOD Wrap-up

- [ ] All 4 commits pushed to `sprint3-phase33`
- [ ] Tests pass: `pytest backend/tests -k "filter or migration"` → 100% pass
- [ ] Manual smoke test: visit dashboard, check 1 setup has new V3 fields
- [ ] Daily report: `docs/SPRINT_3.3_DAY1_REPORT.md`

---

<a name="4-day-2"></a>
## 4. Day 2 (Saturday 9 May) — Day Type Classifier + Smart Entry

### 4.1 Day Goal

Deploy the **classification engine** and the **entry mechanism**: live day-type detection with hysteresis, then Smart Entry POC + imbalance check.

### 4.2 Morning Standup (08:00 IDT)

```
[Day 2 Standup Template]

Day 1 review:
  All 4 commits deployed: ✓ / ✗
  Production smoke test passed: ✓ / ✗
  Any production errors overnight: [list]

Today's target: 5 commits
  Commit 5: day_classifier.py + 6 detectors
  Commit 6: hysteresis state machine + Patch 1
  Commit 7: smart_entry.py (POC + imbalance)
  Commit 8: tier_sizing.py (3/2/0 by score and day type)
  Commit 9: integration test E2E

Blockers: [list any]
```

### 4.3 Tasks

#### Task 2.1 — Day Type Classifier (4h)

```
Goal: Live classification of trading day (6 types)
Files (NEW):
  - backend/app/classifier/day_classifier.py
  - backend/app/classifier/detectors.py (6 detector functions)
  - backend/app/classifier/hysteresis.py
  - backend/tests/test_day_classifier.py

Implementation: Copy from V3 Spec §4 (full pseudocode provided)

Tests:
  - Synthetic TREND_DAY scenario → classifies TREND_DAY
  - Synthetic V-shape → classifies REVERSAL_DAY
  - Synthetic gap > 20pt → classifies GAP_FILL
  - Patch 1 bypass: TREND→REVERSAL at conf 0.65 → switches immediately
  - Hysteresis: switch BLOCKED when new_conf < current_conf + 15
  - Cooldown: switch BLOCKED when last_switch < 30 min ago

Acceptance:
  - All 6 day types detected on synthetic data
  - Hysteresis prevents flip-flopping
  - Patch 1 bypass works as specified
```

→ See CC Prompt #5 in §6

#### Task 2.2 — Smart Entry Mechanism (2.5h)

```
Goal: Replace fixed limit with POC of footprint + imbalance check
Files (NEW):
  - backend/app/entry/smart_entry.py
  - backend/tests/test_smart_entry.py
Files (MODIFY):
  - backend/app/main.py (wire smart_entry to /trade/execute)
  - sc_study/MES_AI_DataExport.cpp (output last footprint POC + imbalance)

Logic:
  1. Read last_footprint_poc from DLL JSON
  2. Read bid/ask imbalance at POC level
  3. Calculate imbalance ratio
  4. If ratio < 200% in setup direction → REJECT
  5. Else: place limit order at POC ± 0.25pt
  6. Timeout: 90s (TREND/GAP/REVERSAL) or 60s (BROAD/RANGE)
  7. On timeout: status = MISSED_TIMEOUT (Patch 3)

Tests:
  - Imbalance 250%, valid → entry placed
  - Imbalance 150% → setup rejected
  - Limit timeout → status MISSED_TIMEOUT (NOT CHASED)
  - DLL: verify POC field present in JSON

Acceptance:
  - Fill rate ≥ 70% in demo
  - Zero "market chase" events logged (Patch 3 enforcement)
```

→ See CC Prompt #6 in §6

#### Task 2.3 — Tier R-Multiple Sizing (1.5h)

```
Goal: Apply 3/2/0 contract sizing per day type and score
Files (NEW):
  - backend/app/sizing/tier_calculator.py
  - backend/tests/test_tier_calculator.py
Files (MODIFY):
  - backend/app/main.py (compute_position uses tier_calculator)

Logic:
  Match (day_type, score) → contracts:
    TREND_DAY + score>=70    → 3
    GAP_FILL + score>=70     → 3
    BROAD_CHANNEL + score>=70 → 2
    RANGE + score>=70         → 2
    REVERSAL_DAY + score>=70  → 2
    NEUTRAL → 0 (LIVE) or 1 (Shadow if score>=80)
    Anything below 70 → 0 (REJECT)

Friday late override:
    If special_day_block_v3 == "friday_late": cap at 2 contracts

Tests:
  - All 6 day types × score 70/80/90 grids
  - Friday cap applies correctly
  - Score 65 → 0 (rejected)

Acceptance:
  - Sizing matches spec for all combinations
  - REJECT logged with reason
```

→ See CC Prompt #7 in §6

#### Task 2.4 — Integration Test E2E (1.5h)

```
Goal: Verify full pipeline: signal → filter → classify → entry → execute
Files (NEW):
  - backend/tests/test_e2e_v3_pipeline.py

Test scenarios:
  Scenario A: TREND_DAY, 09:30 ET, score 75 → REJECTED (DEVELOPING)
  Scenario B: TREND_DAY, 11:30 ET, score 75 → APPROVED, 3 ctr
  Scenario C: NEUTRAL, RTH, score 75 → SKIPPED (LIVE neutral)
  Scenario D: GAP_FILL, 11:00 ET, score 80 → APPROVED, 3 ctr, T2=PDC
  Scenario E: REVERSAL emerging at 14:00 → Patch 1 bypass fires
  Scenario F: News blackout 13:55 → all REJECTED
  Scenario G: Friday 14:30 → APPROVED but capped at 2 ctr

Acceptance:
  - All 7 scenarios pass
  - Each scenario fully traced in logs (filter→classify→size→target→exit)
```

→ See CC Prompt #8 in §6

### 4.4 Day 2 EOD Wrap-up

- [ ] 5 commits to `sprint3-phase33`
- [ ] E2E test 7/7 pass
- [ ] Manual demo trade: full lifecycle verified
- [ ] `docs/SPRINT_3.3_DAY2_REPORT.md` written

---

<a name="5-day-3"></a>
## 5. Day 3 (Sunday 10 May) — Status Layer + A/B Validation

### 5.1 Day Goal

Deploy the **System Status Layer** UI/backend, then run **first end-to-end validation** with V3 logic on demo data.

### 5.2 Morning Standup (08:00 IDT)

```
[Day 3 Standup Template]

Days 1-2 review:
  Total commits deployed: 9 (target: 9)
  Production smoke test passed: ✓ / ✗
  Any errors caught Friday/Saturday: [list]

Today's target: 4 commits + validation report
  Commit 10: backend /system/status endpoint
  Commit 11: frontend StatusBanner + ComponentsPanel
  Commit 12: AutoDimWrapper integration
  Commit 13: kill_switch endpoint + manual override
  Validation: SPRINT_3.3_VALIDATION_REPORT.md

Blockers: [list any]
```

### 5.3 Tasks

#### Task 3.1 — Backend `/system/status` Endpoint (2h)

```
Goal: Aggregate health endpoint with 5 component checks
Files (NEW):
  - backend/app/system/status.py
  - backend/app/system/heartbeat.py (Bridge writes here)
  - backend/tests/test_system_status.py

Implementation: Copy from System Status Layer Spec §6

Tests:
  - All components GREEN → overall GREEN
  - Bridge stale 35s → overall RED
  - DB latency 1500ms → component YELLOW, overall YELLOW
  - Override flow: write key to Redis, status returns "overridden_until X"

Acceptance:
  - Endpoint p95 < 200ms
  - Override expires correctly after 5 min
```

→ See CC Prompt #9 in §6

#### Task 3.2 — Frontend Status Components (3h)

```
Goal: Sticky banner + components panel + auto-dim
Files (NEW):
  - frontend/src/hooks/useSystemStatus.ts
  - frontend/src/components/StatusLayer/StatusBanner.tsx
  - frontend/src/components/StatusLayer/ComponentsPanel.tsx
  - frontend/src/components/StatusLayer/AutoDimWrapper.tsx
  - frontend/src/components/StatusLayer/DegradedModal.tsx
Files (MODIFY):
  - frontend/src/components/Dashboard.tsx (wrap signal area in AutoDim)
  - frontend/src/app/layout.tsx (add StatusBanner sticky)

Implementation: Copy from System Status Layer Spec §8

Tests:
  - Manual: kill Bridge → banner turns RED in <5s
  - Manual: restore Bridge → banner returns GREEN
  - Manual: components panel updates correctly
  - Manual: signals area dims appropriately

Acceptance:
  - Polling every 5s confirmed in DevTools
  - No memory leaks after 1h continuous polling
```

→ See CC Prompt #10 in §6

#### Task 3.3 — Manual Kill Switch (1h)

```
Goal: Big red button to halt all trading
Files (NEW):
  - backend/app/system/kill_switch.py
  - frontend/src/components/StatusLayer/KillSwitchButton.tsx
Files (MODIFY):
  - backend/app/main.py (check kill switch before /trade/execute)

Logic:
  - User clicks "KILL SWITCH" button (top right)
  - Modal: "Type STOP to halt all trading"
  - Sets Redis key mems26:kill_switch:active = true
  - Backend rejects all /trade/execute with 503
  - Visible status banner change to RED with kill switch reason
  - To resume: type RESUME in same modal

Acceptance:
  - Kill switch halts within 1s
  - All open positions left alone (manual close required — by design)
  - Resume requires explicit confirmation
```

→ See CC Prompt #11 in §6

#### Task 3.4 — Sprint Validation Report (2h)

```
Goal: First validation run on V3-classified production demo data

Procedure:
  1. Run demo for 4-6 hours (during RTH)
  2. Verify:
     - Setups classified to V3 day types
     - DEVELOPING phase setups rejected
     - News blackouts blocked correctly (synthetic if no real news)
     - Smart Entry POC fills > 70%
     - Tier sizing correct per day type
  3. Generate report:
     - All 6 day types observed? (likely 1-3 in 1 day)
     - Filter rejection breakdown
     - Smart Entry fill rate
     - Status Layer color transitions logged
     - Any production errors?

Output: docs/SPRINT_3.3_VALIDATION_REPORT.md
```

→ See CC Prompt #12 in §6

### 5.4 Day 3 EOD Wrap-up — Sprint Closeout

- [ ] All 13 commits deployed
- [ ] Validation report committed
- [ ] Tag: `git tag -a sprint-3.3-complete -m "Phase 3.3 complete"`
- [ ] PR `sprint3-phase33` → `develop` → `main` after review
- [ ] LIVE 21/5 readiness: 80%+ checklist green

---

<a name="6-cc-prompts"></a>
## 6. CC Prompts (Ready to Paste)

Each prompt below is **complete and self-contained**. Copy-paste to CC at the start of the relevant task.

### 6.1 CC Prompt #1 — Time Phase Filter

```
Version: V8.5.0-PHASE33-D1-T1 — Time Phase Filter
Date:    8 May 2026
Branch:  sprint3-phase33
Push:    Yes after acceptance tests pass
Commit:  feat(filters): time phase filter (5 phases + DST handling)

CONTEXT:
Implement time-of-day phase classification. V3 Spec §6 is the authoritative
reference. Reject setups in PREMARKET/OFF_HOURS/DEVELOPING phases.

ALLOWED FILES:
- backend/app/filters/time_phase.py (NEW)
- backend/tests/test_time_phase.py (NEW)
- backend/app/main.py (MODIFY — wire filter to setup pipeline)

DO NOT TOUCH: bridge/, frontend/, sc_study/, DB schema, Redis keys

TASK:
Implement TimePhase enum + classify_phase(timestamp, timezone="ET") function.

Phases:
  PREMARKET   = before 09:30 ET
  DEVELOPING  = 09:30 - 11:00 ET
  RTH         = 11:00 - 14:30 ET
  LATE_DAY    = 14:30 - 16:00 ET
  OFF_HOURS   = after 16:00 ET, weekends

Use pytz for timezone handling. Handle DST transitions correctly.

Wire into setup pipeline:
  In setup_pipeline(setup):
    phase = classify_phase(setup.timestamp)
    setup.time_phase_v3 = phase.value
    if phase in (PREMARKET, OFF_HOURS, DEVELOPING):
        setup.rejection_reason = f"phase_{phase.value.lower()}"
        return None  # reject

TESTS (test_time_phase.py):
  - 09:29 ET → PREMARKET
  - 09:30 ET → DEVELOPING
  - 10:30 ET → DEVELOPING (boundary)
  - 11:00 ET → RTH (boundary)
  - 14:30 ET → LATE_DAY (boundary)
  - 16:00 ET → OFF_HOURS (boundary)
  - DST forward (2026-03-08): 02:00 → 03:00 jump handled
  - DST backward (2026-11-01): 02:00 → 01:00 handled
  - Weekend → OFF_HOURS

ACCEPTANCE:
- pytest backend/tests/test_time_phase.py → 100% pass
- 100% line coverage on time_phase.py
- Manual: paste current time, classify_phase returns expected
```

### 6.2 CC Prompt #2 — Special Days Protocol

```
Version: V8.5.0-PHASE33-D1-T2 — Special Days Protocol
Date:    8 May 2026
Branch:  sprint3-phase33
Push:    Yes after tests pass
Commit:  feat(filters): special days (Friday PM + rollover + year-end)

CONTEXT:
Block trading on rollover periods, year-end, and pre-holiday early close days.
Half-size on Friday PM. V3 Spec §8 + Patch 2 are authoritative.

ALLOWED FILES:
- backend/app/filters/special_days.py (NEW)
- backend/tests/test_special_days.py (NEW)

DO NOT TOUCH: anything outside backend/app/filters/

CONSTANTS (verbatim from V3 Spec §8.4):
ROLLOVER_PERIODS_2026 = [
    {"start": "2026-03-12", "end": "2026-03-19"},
    {"start": "2026-06-11", "end": "2026-06-18"},  # CRITICAL: post-LIVE
    {"start": "2026-09-10", "end": "2026-09-17"},
    {"start": "2026-12-10", "end": "2026-12-17"},
]

YEAR_END = ((12, 22, 31), (1, 1, 2))  # Dec 22-31, Jan 1-2

CME_EARLY_CLOSE_2026 = []  # placeholder, populate later

FUNCTION:
def is_special_day_block(today: date) -> Tuple[bool, str]:
    # Rollover
    for window in ROLLOVER_PERIODS_2026:
        if date.fromisoformat(window['start']) <= today <= date.fromisoformat(window['end']):
            return (True, "rollover")
    # Year-end
    if (today.month == 12 and today.day >= 22) or (today.month == 1 and today.day <= 2):
        return (True, "year_end")
    # Friday late (handled separately — return half_size flag)
    if today.weekday() == 4:
        # only after 14:00 ET — caller checks time
        return (True, "friday_late")
    return (False, "")

def is_friday_late(timestamp_et: datetime) -> bool:
    return timestamp_et.weekday() == 4 and timestamp_et.time() >= time(14, 0)

TESTS:
- 2026-06-12 → BLOCKED reason="rollover"
- 2026-06-19 → ALLOWED
- 2026-12-25 → BLOCKED reason="year_end"
- Friday 14:01 ET → is_friday_late=True
- Friday 13:59 ET → is_friday_late=False
- Saturday/Sunday handled by caller (already OFF_HOURS via time_phase)

ACCEPTANCE:
- pytest test_special_days.py → 100%
- All 4 rollover windows correctly enforced
```

### 6.3 CC Prompt #3 — News Calendar 3-Tier

```
Version: V8.5.0-PHASE33-D1-T3 — News Calendar 3-Tier
Date:    8 May 2026
Branch:  sprint3-phase33
Push:    Yes after tests pass
Commit:  feat(filters): news calendar 3-tier with ForexFactory daily fetch

CONTEXT:
Block trades around high-impact news events. 3 tiers per V3 Spec §7.

ALLOWED FILES:
- backend/app/filters/news_calendar.py (NEW)
- backend/scripts/fetch_news_daily.py (NEW)
- backend/tests/test_news_calendar.py (NEW)
- requirements.txt (MODIFY — add 'requests' if not pinned)

DO NOT TOUCH: rest of backend, frontend, bridge

TIER MAPPING:
TIER_1 = ['FOMC', 'NFP', 'CPI', 'Non-Farm Payrolls', 'Federal Funds Rate']  # ±15min
TIER_2 = ['GDP', 'PPI', 'Retail Sales', 'Industrial Production']             # ±5min
TIER_3 = ['Housing', 'Sentiment', 'Consumer Confidence']                     # log only

DATA SOURCE:
- ForexFactory weekly JSON: https://www.forexfactory.com/calendar
- Filter to USD events only
- Cache to: data/news_calendar_<YYYY-MM-DD>.json

CRON (fetch_news_daily.py):
- Run at 00:00 IDT daily via cron or Render Cron Job
- Fetch this week's events
- Filter USD only
- Categorize into tier
- Save to data/news_calendar_<today>.json

FUNCTION:
def is_news_blackout(timestamp, calendar_path=None) -> Tuple[bool, int]:
    """Returns (is_blocked, tier_int)"""
    today = timestamp.date()
    cal_file = calendar_path or f"data/news_calendar_{today}.json"
    if not os.path.exists(cal_file):
        return (False, 0)  # no calendar → no block
    
    calendar = json.load(open(cal_file))
    for event in calendar.get('events', []):
        event_time = datetime.fromisoformat(event['time'])
        delta_min = abs((timestamp - event_time).total_seconds()) / 60
        
        if event['tier'] == 1 and delta_min <= 15:
            return (True, 1)
        if event['tier'] == 2 and delta_min <= 5:
            return (True, 2)
        if event['tier'] == 3 and delta_min <= 30:
            return (False, 3)  # log only
    return (False, 0)

TESTS:
- Mock FOMC at 14:00, query 13:50 → BLOCKED, tier 1
- Mock FOMC at 14:00, query 14:20 → ALLOWED
- Mock GDP at 08:30, query 08:33 → BLOCKED, tier 2
- Mock GDP at 08:30, query 08:40 → ALLOWED
- Mock Housing at 10:00, query 10:00 → ALLOWED, tier 3 (log only)
- No calendar file → ALLOWED, tier 0

ACCEPTANCE:
- pytest test_news_calendar.py → 100%
- Manual: run fetch_news_daily.py → file created
- All 3 tiers correctly classified
```

### 6.4 CC Prompt #4 — V3 Migration on Production DB

```
Version: V8.5.0-PHASE33-D1-T4 — V3 Migration on Production DB
Date:    8 May 2026
Branch:  sprint3-phase33
Push:    AFTER manual verification (BACKUP REQUIRED FIRST!)
Commit:  feat(migrations): V3 day types backfill on production DB

CRITICAL PRE-CONDITION:
1. Run: pg_dump $DATABASE_URL > backup_pre_v3_migration_2026-05-08.sql
2. Verify backup file size > 0
3. Test restore on local: psql -d test_db < backup_pre_v3_migration_2026-05-08.sql
4. Only then proceed.

ALLOWED FILES:
- backend/migrations/004_add_v3_columns.sql (NEW)
- backend/scripts/migrate_v3_day_types.py (NEW — ports Phase 3.2 Day 2 work)

DO NOT TOUCH: production code paths, frontend

SQL MIGRATION (004_add_v3_columns.sql):
ALTER TABLE setups
  ADD COLUMN IF NOT EXISTS day_type_v3            VARCHAR(20),
  ADD COLUMN IF NOT EXISTS day_type_v3_confidence FLOAT,
  ADD COLUMN IF NOT EXISTS time_phase_v3          VARCHAR(20),
  ADD COLUMN IF NOT EXISTS news_tier_v3           SMALLINT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS special_day_block_v3   VARCHAR(20),
  ADD COLUMN IF NOT EXISTS v3_migration_version   VARCHAR(20);

CREATE INDEX IF NOT EXISTS idx_setups_day_type_v3 ON setups(day_type_v3);

PYTHON SCRIPT (migrate_v3_day_types.py):
- Connect to production DB
- For each setup row WHERE day_type_v3 IS NULL:
  - Build DayMetrics from setup fields (use V3 §4 logic)
  - classify_day(metrics) → day_type_v3, confidence
  - Compute time_phase_v3, news_tier_v3, special_day_block_v3
  - UPDATE setups SET ... WHERE id = ?
- Batch in chunks of 1,000 to avoid timeout
- Print progress every 1,000 rows
- Final report:
  - Rows updated
  - V2 vs V3 distribution
  - Mean confidence
  - Special day blocks encountered

ACCEPTANCE:
- All existing setups have day_type_v3 populated (zero NULL)
- Production DB downtime < 5 minutes (use pg_advisory_lock)
- Distribution report logged
- Backup verified before run
```

### 6.5 CC Prompt #5 — Day Type Classifier

```
Version: V8.5.0-PHASE33-D2-T1 — Day Type Classifier (live)
Date:    9 May 2026
Branch:  sprint3-phase33
Push:    Yes after E2E tests
Commit:  feat(classifier): live V3 day type classifier with hysteresis + Patch 1

CONTEXT:
Live in-memory classification of trading day. 6 detectors + hysteresis.
Reference: V3 Spec §3 + §4 + §5 (full pseudocode provided).

ALLOWED FILES:
- backend/app/classifier/day_classifier.py (NEW)
- backend/app/classifier/detectors.py (NEW)
- backend/app/classifier/hysteresis.py (NEW)
- backend/app/classifier/__init__.py (NEW)
- backend/tests/test_day_classifier.py (NEW)

DO NOT TOUCH: filters/, sizing/, entry/

IMPLEMENTATION:
Copy V3 Spec §4 verbatim. Pure Python + dataclasses.

Singleton pattern:
- Single DayClassifier instance per process
- Reset at midnight ET (cron or scheduled task)
- Persist current_type to Redis for restart resilience

REDIS KEYS:
- mems26:classifier:current_type
- mems26:classifier:current_confidence
- mems26:classifier:last_switch_ts

INTEGRATION:
In main.py setup pipeline, after time_phase filter:
  market_data = build_market_snapshot()
  day_type, conf = classifier.update(market_data)
  setup.day_type_v3_live = day_type.value
  setup.day_type_v3_confidence_live = conf

TESTS (test_day_classifier.py):
- Synthetic TREND scenario (12 ticks, narrow IB, range>0.7×ATR) → TREND_DAY
- Synthetic V-shape (rise then reverse + open cross + vol burst) → REVERSAL_DAY
- Synthetic gap 25pt + reversal → GAP_FILL
- Synthetic chop (vegas_flips=8, range=0.5×ATR) → NEUTRAL
- Patch 1 bypass: TREND active, REVERSAL @ 0.65 conf → switches without +15
- Hysteresis: TREND @ 0.85, BROAD_CHANNEL @ 0.70 → blocked (delta<15)
- Cooldown: switch @ t=0, attempt switch @ t=20min → blocked

ACCEPTANCE:
- All 7 test scenarios pass
- 100% coverage on day_classifier.py
- Redis persistence verified (kill process, restart, classification continues)
```

### 6.6 CC Prompt #6 — Smart Entry Mechanism

```
Version: V8.5.0-PHASE33-D2-T2 — Smart Entry (POC + imbalance)
Date:    9 May 2026
Branch:  sprint3-phase33
Push:    After E2E + DLL re-test
Commit:  feat(entry): Smart Entry POC + 200% imbalance check + Patch 3 timeout

CONTEXT:
Replace fixed limit with Smart Entry: POC of last footprint bar at trigger,
with imbalance check ≥ 200%. Patch 3: NEVER market chase on timeout.

ALLOWED FILES:
- backend/app/entry/smart_entry.py (NEW)
- backend/tests/test_smart_entry.py (NEW)
- backend/app/main.py (MODIFY — wire to /trade/execute)
- sc_study/MES_AI_DataExport.cpp (MODIFY — add last_footprint_poc field)

DO NOT TOUCH: classifier/, filters/, sizing/

DLL CHANGES (sc_study):
Add to JSON output:
  "footprint": {
    "last_bar_poc": float,
    "last_bar_imbalance_at_poc_pct": int,  // -500 to +500, signed
    "last_bar_timestamp": ISO timestamp
  }

Sierra: re-add Study after build.

BACKEND IMPLEMENTATION:
def compute_smart_entry(setup, market_data):
    poc = market_data['footprint']['last_bar_poc']
    imbal = market_data['footprint']['last_bar_imbalance_at_poc_pct']
    direction = setup.direction
    
    # Imbalance check — must be in setup direction at ≥200%
    if direction == 'LONG' and imbal < 200:
        return None  # reject
    if direction == 'SHORT' and imbal > -200:
        return None  # reject
    
    # Entry price = POC (with 0.25pt offset toward direction)
    offset = 0.25 if direction == 'LONG' else -0.25
    entry_price = poc + offset
    
    timeout_sec = 90 if setup.day_type in ('TREND_DAY', 'GAP_FILL', 'REVERSAL_DAY') else 60
    return {'entry_price': entry_price, 'timeout_sec': timeout_sec}

TIMEOUT HANDLER (Patch 3):
async def monitor_order_timeout(order_id, timeout_sec):
    await asyncio.sleep(timeout_sec)
    order = await get_order(order_id)
    if order.status == 'PENDING':
        # MISSED — never market chase
        order.status = 'MISSED_TIMEOUT'
        await update_order(order)
        log_event('order_missed_timeout', order_id=order_id)

TESTS:
- Imbalance 250% LONG → entry placed at POC+0.25
- Imbalance -250% SHORT → entry placed at POC-0.25
- Imbalance 150% LONG → REJECTED
- Imbalance 250% but SHORT → REJECTED
- Mock 90s timeout → status = MISSED_TIMEOUT (NOT CHASED)
- DLL JSON contains footprint.last_bar_poc field

ACCEPTANCE:
- All tests pass
- Demo: 10 trades, fill rate ≥ 70%
- Zero "market chase" or "MARKET" status entries in logs
```

### 6.7 CC Prompt #7 — Tier R-Multiple Sizing

```
Version: V8.5.0-PHASE33-D2-T3 — Tier R-Multiple Sizing
Date:    9 May 2026
Branch:  sprint3-phase33
Push:    After tests pass
Commit:  feat(sizing): Tier R-Multiple — 3/2/0 contracts by day type and score

CONTEXT:
Apply per-day-type sizing per V3 Playbooks Reference Card §8.6.

ALLOWED FILES:
- backend/app/sizing/tier_calculator.py (NEW)
- backend/tests/test_tier_calculator.py (NEW)
- backend/app/main.py (MODIFY — replace fixed qty with tier_calculator)

DO NOT TOUCH: classifier/, filters/, entry/

LOGIC:
TIER_TABLE = {
    'TREND_DAY':     {'70+': 3, '50-69': 0, '<50': 0},
    'GAP_FILL':      {'70+': 3, '50-69': 0, '<50': 0},
    'BROAD_CHANNEL': {'70+': 2, '50-69': 0, '<50': 0},
    'RANGE':         {'70+': 2, '50-69': 0, '<50': 0},
    'REVERSAL_DAY':  {'70+': 2, '50-69': 0, '<50': 0},
    'NEUTRAL':       {'70+': 0, '50-69': 0, '<50': 0},  # Shadow handled separately
}

def compute_size(day_type, score, special_day_block=None) -> Tuple[int, str]:
    """Returns (contracts, reason)"""
    if score < 50:
        return (0, 'score_below_50')
    
    bucket = '70+' if score >= 70 else '50-69'
    base_qty = TIER_TABLE.get(day_type, {}).get(bucket, 0)
    
    if base_qty == 0:
        return (0, f'tier_skip_{day_type}_{bucket}')
    
    # Friday late override
    if special_day_block == 'friday_late':
        base_qty = min(base_qty, 2)
    
    return (base_qty, 'approved')

TESTS:
- TREND_DAY + score 75 → (3, 'approved')
- TREND_DAY + score 60 → (0, 'tier_skip_TREND_DAY_50-69')
- BROAD_CHANNEL + score 80 → (2, 'approved')
- NEUTRAL + score 90 → (0, ...)
- Friday late + TREND + score 80 → (2, 'approved') [capped]
- Score 45 → (0, 'score_below_50')

ACCEPTANCE:
- All combinations match playbook spec
- Friday cap applies correctly
- pytest 100% pass
```

### 6.8 CC Prompts #8-#12 (abbreviated)

```
#8 Integration E2E test (full pipeline 7 scenarios)
#9 Backend /system/status endpoint (per Status Layer Spec §6)
#10 Frontend StatusBanner + ComponentsPanel (per §8)
#11 Manual kill switch endpoint + UI button
#12 Sprint validation report (run demo, write findings)

Full prompts will be expanded inline at sprint start (Day 3 morning).
For now, references are sufficient — Status Layer Spec has full code samples.
```

---

<a name="7-acceptance"></a>
## 7. Acceptance Criteria (End of Sprint)

By 10 May EOD:

### Code

- [ ] 13+ commits on `sprint3-phase33` branch
- [ ] All E2E tests pass (7+ scenarios)
- [ ] V3 Day Type Classifier deployed and live-classifying
- [ ] All 5 universal filters operational (score, time_phase, special_day, news, daily_cap)
- [ ] Smart Entry POC + imbalance + Patch 3 timeout enforced
- [ ] Tier R-Multiple sizing per playbook deployed
- [ ] Status Layer banner + panel + auto-dim deployed
- [ ] Manual kill switch tested

### Data

- [ ] V3 migration on production DB complete (zero NULL day_type_v3)
- [ ] News calendar fetcher cron running
- [ ] At least 30 demo trades executed under V3 logic

### Validation

- [ ] Sprint validation report committed
- [ ] All 6 day types observed in some demo session (REVERSAL may be 0-1)
- [ ] CFG-α + DEVELOPING skip filter shows expected improvement
- [ ] Zero production downtime > 5 minutes

---

<a name="8-risk"></a>
## 8. Risk Register

| # | Risk | Probability | Impact | Mitigation |
|---|------|-------------|--------|-----------|
| 1 | DLL re-add Study breaks live data flow | Med | High | Test in non-RTH; have rollback plan |
| 2 | DB migration takes > 5 min downtime | Low | Med | Pre-tested on backup, batch in 1k chunks |
| 3 | News calendar fetcher fails silently | Med | Med | Cron with healthcheck; default to log-only if missing |
| 4 | Smart Entry fill rate < 70% | Med | High | Fall back to fixed limit; tune imbalance threshold |
| 5 | Patch 1 hysteresis bypass mis-fires | Low | Med | Only triggers TREND→REVERSAL @ ≥0.60 (high bar) |
| 6 | Status Layer adds latency to dashboard | Low | Low | Cache 2s on backend; lazy load components panel |
| 7 | June rollover surprises post-LIVE | Low | High | Calendar pre-loaded; will halt automatically |

---

<a name="9-demo-live"></a>
## 9. Demo-to-LIVE Checklist (11-21 May)

After Phase 3.3 sprint ends, 11 days of demo before LIVE 21/5:

### Week 1 (11-17 May): Demo Hardening

- [ ] Daily demo execution (30+ trades total)
- [ ] Review every losing trade for spec compliance
- [ ] Track: fill rate, classification accuracy, hysteresis switches
- [ ] Adjust thresholds if needed (open questions §12 of V3 Spec)

### Week 2 (18-21 May): LIVE Preparation

- [ ] 18/5: Final demo audit — 50+ trades reviewed
- [ ] 19/5: Switch to LIVE mode in staging environment
- [ ] 20/5: LIVE rehearsal — 1 contract Tier-S, manual confirmation per trade
- [ ] 21/5: LIVE Day 1 — see DAY1_LIVE_PROTOCOL (separate doc)

---

## Document History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 5 May 2026 EOD | Initial sprint plan |

---

**Maintained by:** Michael (with Claude assistance)
**Status:** READY for execution starting 8 May 08:00 IDT
**Sprint kickoff:** 8 May 2026, 08:00 IDT
**Sprint end:** 10 May 2026, 18:00 IDT
**LIVE target:** 21 May 2026
