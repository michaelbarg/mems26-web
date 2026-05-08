# MEMS26 Sprint 4 Schema Lock

**Version:** V1.0
**Date:** 9 May 2026
**Status:** LOCKED for Sprint 4 duration
**Sprint dates:** 9–28 May 2026
**LIVE target:** 28 May 2026 — 1 contract, $200 daily cap (D-061)

---

## Locked Decisions Referenced

| Decision | Title |
|----------|-------|
| D-046 | Source Methodology Architecture (7 layers) |
| D-049 | Suffering Side Veto |
| D-051 | Day Type V4 (6 MP types) |
| D-052 | 5 Decision Gates |
| D-053 | G-Point Validator |
| D-055 | Trade Manager — Smart BE on T2 |
| D-061 | LIVE 28/5, 1 contract, $200 cap |
| D-062 | Layered QC Strategy |
| D-063 | IB Width thresholds: <10 NARROW / 10-25 MEDIUM / >25 WIDE |
| D-064 | Opening Type Detection: 30-minute window |
| D-065 | Suffering Side No-Trade Zone: ±2 points around day_poc |
| D-066 | V1 keeps history, V4 starts fresh |
| D-067 | Reactive Pattern requires 3 confirmations (COT + Belly + POC) |
| D-068 | QC Dashboard per-layer panel format |

---

## Section 1: Layer 1 — Primitives (Redis Schema)

New Redis fields populated by DLL and enriched by Backend/Bridge.

**Redis namespace:** `mems26:primitives`

### PRIMITIVE 1 — Initial Balance (IB)

| Field | Type | Range / Values | Source | Notes |
|-------|------|---------------|--------|-------|
| `ib.high` | FLOAT | points | DLL | Highest price in first 60 min of RTH |
| `ib.low` | FLOAT | points | DLL | Lowest price in first 60 min of RTH |
| `ib.width_pts` | FLOAT | points | DLL | `high - low` |
| `ib.width_class` | STRING | `NARROW` \| `MEDIUM` \| `WIDE` | DLL | Per D-063: <10 = NARROW, 10–25 = MEDIUM, >25 = WIDE |
| `ib.locked` | BOOLEAN | true/false | DLL | True after 60 min from RTH open (09:30 ET) |
| `ib.minutes_into_session` | INT | 0–390 | DLL | Minutes since RTH open |

**D-063 thresholds:**
```
width_pts < 10   → NARROW
10 ≤ width_pts ≤ 25 → MEDIUM
width_pts > 25   → WIDE
```

### PRIMITIVE 2 — Day POC

| Field | Type | Range / Values | Source | Notes |
|-------|------|---------------|--------|-------|
| `day_poc.price` | FLOAT | points | DLL | Current day POC (price with most volume) |
| `day_poc.last_update` | TIMESTAMP | ISO-8601 | DLL | When POC was last recomputed |
| `day_poc.confidence` | STRING | `LOW` \| `MED` \| `HIGH` | Backend | Based on session elapsed time |

**Confidence logic:**
```
First 30 min of session     → LOW
30–90 min into session      → MED
>90 min into session        → HIGH
```

### PRIMITIVE 3 — Opening Type

| Field | Type | Range / Values | Source | Notes |
|-------|------|---------------|--------|-------|
| `opening.type` | STRING | `OPEN_DRIVE` \| `OPEN_TEST_DRIVE` \| `ORR` \| `OPEN_AUCTION_INSIDE` \| `OPEN_AUCTION_OUTSIDE` | DLL | Per D-064, determined within 30-min window |
| `opening.decided_at` | TIMESTAMP | ISO-8601 | DLL | When type was determined |
| `opening.confidence` | STRING | `LOW` \| `MED` \| `HIGH` | DLL | Increases as window progresses |
| `opening.tested_level` | STRING | `PDH` \| `PDL` \| `VAH` \| `VAL` \| null | DLL | Which level was tested (for test drive / ORR) |
| `opening.window_minutes` | INT | 30 | DLL | Always 30 per D-064 |

**Opening types (Mind Over Markets):**
- **OPEN_DRIVE** — Strong directional move from open, conviction buying/selling
- **OPEN_TEST_DRIVE** — Tests prior reference level, rejects, then drives away
- **ORR** (Open Rejection Reverse) — Opens beyond range, reverses back inside
- **OPEN_AUCTION_INSIDE** — Opens inside prior range, auctions within
- **OPEN_AUCTION_OUTSIDE** — Opens outside prior range, continues exploring

### PRIMITIVE 4 — POC Migration

| Field | Type | Range / Values | Source | Notes |
|-------|------|---------------|--------|-------|
| `poc_migration.direction` | STRING | `UP` \| `DOWN` \| `STUCK` | Backend | Direction POC is migrating |
| `poc_migration.points` | FLOAT | points | Backend | Magnitude of migration |
| `poc_migration.duration_min` | INT | minutes | Backend | How long current migration trend |
| `poc_migration.last_step` | STRING | `step_N_of_8` | Backend | Phase 5 step tracking |

---

## Section 2: Layer 1 — DB Schema Additions

New columns on `setup_attempts` table to persist primitives at time of each setup attempt.

```sql
-- Day POC tracking
ALTER TABLE setup_attempts
  ADD COLUMN IF NOT EXISTS day_poc               FLOAT,
  ADD COLUMN IF NOT EXISTS day_poc_confidence     VARCHAR(10);

-- IB tracking
ALTER TABLE setup_attempts
  ADD COLUMN IF NOT EXISTS ib_width_pts           FLOAT,
  ADD COLUMN IF NOT EXISTS ib_width_class         VARCHAR(10),
  ADD COLUMN IF NOT EXISTS ib_locked              BOOLEAN;

-- Opening Type
ALTER TABLE setup_attempts
  ADD COLUMN IF NOT EXISTS opening_type           VARCHAR(30),
  ADD COLUMN IF NOT EXISTS opening_confidence     VARCHAR(10);

-- POC Migration
ALTER TABLE setup_attempts
  ADD COLUMN IF NOT EXISTS poc_migration_direction VARCHAR(10),
  ADD COLUMN IF NOT EXISTS poc_migration_points    FLOAT;

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_setup_attempts_day_poc
  ON setup_attempts(day_poc);
CREATE INDEX IF NOT EXISTS idx_setup_attempts_opening_type
  ON setup_attempts(opening_type);
CREATE INDEX IF NOT EXISTS idx_setup_attempts_ib_width_class
  ON setup_attempts(ib_width_class);
```

**Migration file:** `backend/migrations/005_sprint4_layer1.sql`

**Column inventory (9 new columns):**

| Column | Type | Nullable | Index | Decision |
|--------|------|----------|-------|----------|
| `day_poc` | FLOAT | YES | YES | D-049, D-065 |
| `day_poc_confidence` | VARCHAR(10) | YES | NO | D-049 |
| `ib_width_pts` | FLOAT | YES | NO | D-063 |
| `ib_width_class` | VARCHAR(10) | YES | YES | D-063 |
| `ib_locked` | BOOLEAN | YES | NO | D-063 |
| `opening_type` | VARCHAR(30) | YES | YES | D-064 |
| `opening_confidence` | VARCHAR(10) | YES | NO | D-064 |
| `poc_migration_direction` | VARCHAR(10) | YES | NO | D-049 |
| `poc_migration_points` | FLOAT | YES | NO | D-049 |

---

## Section 3: Layer 3 — Suffering Side Gate (Day 2 deploy)

API contract for the Suffering Side Veto per D-049 + D-065.

### Endpoint

```
GET /gates/suffering-side
```

### Query Parameters

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `direction` | STRING | YES | `LONG` or `SHORT` |
| `price` | FLOAT | YES | Current price to evaluate |

### Response

```json
{
  "gate": "suffering_side",
  "result": "PASS | BLOCK",
  "reason": "above_zone | below_zone | inside_zone | passed",
  "details": {
    "direction": "LONG",
    "price": 5732.25,
    "day_poc": 5730.00,
    "distance_pts": 2.25,
    "no_trade_zone_pts": 2.0,
    "decision_logic": "price > day_poc + 2pt → LONG OK"
  },
  "source_decision": "D-049, D-065",
  "source_quote": "אנחנו אף פעם לא מצטרפים לצד הסובל"
}
```

### Decision Logic (D-065)

```
NO_TRADE_ZONE_PT = 2.0

if abs(price - day_poc) <= NO_TRADE_ZONE_PT:
    BLOCK("inside POC no-trade zone")
elif direction == LONG and price < day_poc - NO_TRADE_ZONE_PT:
    BLOCK("below POC — buyers suffer")
elif direction == SHORT and price > day_poc + NO_TRADE_ZONE_PT:
    BLOCK("above POC — sellers suffer")
else:
    PASS("clear of POC zone")
```

### Visual Diagram

```
            BLOCK SHORT
            ↑
  ──────────┤ day_poc + 2pt
            │ NO-TRADE ZONE (BLOCK ALL)
  ──────────┤ day_poc - 2pt
            ↓
            BLOCK LONG
```

---

## Section 4: Future Layer Schemas (Placeholders)

These schemas will be locked in subsequent sprint days. Included here for parallel team awareness.

### Layer 2 (Days 8–14) — State Classifiers

| Field | Type | Values | Decision |
|-------|------|--------|----------|
| `day_type_v4` | STRING | Normal, Trend, Expanded Normal, Neutral, Non-Trend, Running Profile | D-051, D-066 |
| `otf_clarity` | STRING | CLEAR_OTF_UP, CLEAR_OTF_DOWN, MIXED, NO_SIGNAL | D-050 |
| `market_state` | STRING | respects, extends, searches, found | D-046 |

### Layer 3 (Days 15+) — Decision Gates

5 gates per D-052:

1. **Suffering Side** — Documented above (Day 2 deploy)
2. **OTF Clarity** — Requires clear OTF signal for directional trades
3. **Vegas Strategic** — Alignment with Vegas session context
4. **Day Type Risk** — Risk scaling per day type classification
5. **Killzone** — Time-based trade windows

### Layer 4 (Days 16–17) — Patterns

| Pattern | Confirmations Required | Decision |
|---------|----------------------|----------|
| Reactive Long | COT + Belly + POC (3 required per D-067) | D-067 |
| Reactive Short | COT + Belly + POC (3 required per D-067) | D-067 |
| Initiative | DEFERRED to Phase 3 | — |

### Layer 5 (Day 18) — G-Point Validator

Per D-053: validates Location AND Timing AND Quality. All three must pass.

### Layer 6 (Day 18) — Trade Manager

Per D-055: Smart breakeven on T2. Auto-manages C1/C2/C3 exit sequence.

### Layer 7 — Frontend QC Dashboard

Per D-068: Per-layer panels showing real-time QC status for each layer.

---

## Section 5: Schema Versioning Rules

1. This schema is **LOCKED** for Sprint 4 (9–28 May 2026)
2. New fields **CAN** be added (additive changes OK)
3. Existing fields **CANNOT** be removed or renamed
4. Field types **CANNOT** change once locked
5. If a breaking change is needed → strategic chat decision required (טראמפ channel)
6. All additive changes require a new migration file (sequential numbering: 006, 007, ...)
7. Redis field additions do not require migration — just documentation update here

**Compatibility guarantee:** Any code written against this schema during Sprint 4 will not break due to schema changes. Only additive extensions are permitted.

---

## Section 6: Source Traceability

Every field maps to a decision and source document.

| Field | Decision | Source Document | Source Quote / Concept |
|-------|----------|----------------|----------------------|
| `ib.high`, `ib.low`, `ib.width_pts` | D-063 | Mind Over Markets (Ch. 4) | "Initial Balance defines the first hour's range" |
| `ib.width_class` | D-063 | Mind Over Markets | "IB width classifies expected day type behavior" |
| `ib.locked` | D-063 | Mind Over Markets | IB is set after first 60 minutes of RTH |
| `day_poc.price` | D-049, D-065 | חוזים.docx | "אנחנו אף פעם לא מצטרפים לצד הסובל" |
| `day_poc.confidence` | D-049 | Implementation decision | Confidence increases with session time |
| `opening.type` | D-064 | Mind Over Markets (Ch. 5) | "4 opening types determined in first 30 minutes" |
| `opening.tested_level` | D-064 | Mind Over Markets | Test drive / ORR test prior reference levels |
| `opening.window_minutes` | D-064 | D-064 | Fixed at 30 minutes per decision lock |
| `poc_migration.direction` | D-049 | Mind Over Markets | POC migration indicates value area shift |
| `poc_migration.last_step` | D-049 | Phase 5 design | 8-step POC migration tracking |
| `day_type_v4` | D-051, D-066 | Mind Over Markets (Ch. 3) | "6 Market Profile day types" |
| `otf_clarity` | D-050 | Mind Over Markets | OTF (One-Timeframe) directional clarity |
| `reactive_pattern` | D-067 | Mind Over Markets | "Reactive requires 3 confirmations: COT + Belly + POC" |
| `suffering_side_gate` | D-049, D-065 | חוזים.docx | No-trade zone ±2pt around day POC |

---

## Appendix: Redis Key Structure

```
mems26:primitives         ← Layer 1 hash (IB, POC, Opening, Migration)
mems26:latest             ← Existing: current market snapshot
mems26:candles            ← Existing: 960 × 3min bars
mems26:gates:suffering    ← Layer 3: last suffering side evaluation
```

All primitives are stored as a single Redis hash (`mems26:primitives`) with dot-notation keys flattened:
```
HSET mems26:primitives
  ib.high           5735.50
  ib.low            5728.00
  ib.width_pts      7.50
  ib.width_class    NARROW
  ib.locked         true
  ib.minutes_into_session  45
  day_poc.price     5731.25
  day_poc.last_update  2026-05-09T15:30:00Z
  day_poc.confidence   MED
  opening.type      OPEN_TEST_DRIVE
  opening.decided_at   2026-05-09T10:00:00Z
  opening.confidence   HIGH
  opening.tested_level PDH
  opening.window_minutes  30
  poc_migration.direction  UP
  poc_migration.points     1.25
  poc_migration.duration_min  15
  poc_migration.last_step  step_3_of_8
```
