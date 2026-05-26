# CC Mega-Prompt · S2 Audit · POST-EOD 2026-05-25

**Owner:** Claude Code
**Trigger:** Run AFTER market close (16:00 ET / 23:00 IL) on 2026-05-25
**Mode:** READ-ONLY audit · NO code changes in this thread
**Deliverable:** `docs/reports/S2_AUDIT_2026-05-25.md` per spec below
**Estimated time:** 2-3 CC hours · checkpoint at 90min · hard-stop at 3h

---

## 0 · Strategic context (why we audit now)

**S2 (FiveMinSystem) is nearly dead in production.**

Live evidence collected 2026-05-25 18:30 IL:

| Metric | Value | Source |
|---|---|---|
| S2 fires last 7 days | **3** | `SELECT COUNT(*) FROM v9_trades WHERE firing_system=2 AND entry_ts >= date('now','-7 days')` |
| S4 Woodies fires same window | **2,635** | same query, firing_system=4 |
| S2 fires today (2026-05-25) | **0** | same query, entry_ts >= date('now') |
| Backend session | CASH_HOURS | `/api/v9/status` |
| S2 hydration | `reached_state DAY_TYPE_MODE` | `/api/v9/status.hydration.systems.five_min` |
| S2 UI cockpit display | `Opening type: pending · Pattern: none` | user screenshot 17:30 IL |
| bar_router | received 68,794 · dispatched 56,531 · **backlog 12,263 and growing** | `/api/v9/status.bar_router` |
| day_type API | `current_type=UNKNOWN · confidence=0.0` | `/api/v9/status.day_type` |
| day_type hydration | `reached_state PENDING · confidence=38.0` | `/api/v9/status.hydration.systems.day_type` |

**Two wiring bugs already identified** (documented in `docs/plans/STATUS_BOARD.md` amendment log 2026-05-25 17:50):

- **B1 (cosmetic)** · `_on_day_type_update` (`backend/v9/systems/five_min/five_min_system.py:252-264`) updates `self.current_day_type` but does NOT extract/update `self.opening_type` from event payload → S2 cockpit shows `pending` perpetually. Impact: UI only, not consumed in entry logic.
- **B2 (real)** · mode transition `FIRST_HOUR_TACTICAL → DAY_TYPE_MODE` (lines 244-246) is gated on `event.ts` from currently-processed bar. With bar_router backlog growing (+0.6/s), S2 processes morning bars whose `bar_time < 10:30 ET` and transition never triggers. **Impact: 3/5 detectors disabled (H&S Top/Inverse · Double Bottom/Top · Bull/Bear Flag).**

Pkg 6 (TrailEngine) is actively managing trade #3315 during writing of this prompt — **no S2 code changes during cash hours.**

---

## 1 · Your task

Run a **5-Layer S2 Audit** post-EOD. Produce `docs/reports/S2_AUDIT_2026-05-25.md` containing:

1. Bug catalog (verify B1 + B2 + discover any others)
2. Component classification table (KEEP / ADAPT / REPLACE / DEFER) for all 40 files under `backend/v9/systems/five_min/`
3. Recommended fix-package sequence with dependencies
4. Open questions Michael must answer before any fix is built

This is the **precursor** to a fix package. **Decisions on what to fix are Michael's.** Your job is evidence + classification, not "go fix it".

### Hard constraints

- READ-ONLY. Do not modify Python under `backend/v9/systems/five_min/` or anywhere else in `backend/v9/`.
- Smallest blast radius preferred. **Flag, do not fix.**
- If a finding contradicts D-091 spec — **strategic stop** · escalate to Michael · do NOT propose a fix.
- If 2× diagnostic attempts on the same layer fail — stop · escalate · do NOT thrash.
- If actual time exceeds 3 hours — checkpoint partial · stop · ping Michael.
- All four UAT axes must be reasoned about (Quality / Recency / Cardinality / Latency) for any data-touching finding.

---

## 2 · The 5-Layer Methodology

You produce a finding only when **≥3 layers** agree on the evidence. A finding in only 1 layer is a hypothesis, not a bug.

### Layer 1 · Spec-vs-Code Diff

Read **all** of these authority documents (in this order):

| Doc | Path | What to extract |
|---|---|---|
| D-091 S2 LIVE Scope | `docs/decisions/D-091_S2_LIVE_SCOPE.md` | 10 patterns table · 6 day-type coverage matrix · Adaptive Stop layers A/B/C · day-type T1/T2/T3 · T2 haircuts · contract split · trade management hooks |
| D-091.Q1/Q2/Q4 sub-decisions | same doc, end | NeuE/NeuC classification rule · NT NO_TRADE early-skip in `_check_setup` · Pkg 3a emit-only scope |
| D-091.Q5 Flag Path C | same doc, end | Day-type conditional T2 for Flag · NeuE/Norm scope expansion · inline implementation precedent |
| EXIT_V6 | `docs/spec_authority/S2_EXIT_DEFINITION_V6.md` | Time Stop windows per day type (TN: none · TDD: 90 · NV: 60 · NeuE: 45 · NeuC: 30 · Norm: 30 · NT: NO_TRADE) |
| Auth Table V1 | `docs/spec_authority/S2_AUTH_TABLE_V1.md` | OFA Reactive + Initiative entry signals · belly_ratio · 7 validators · cooldowns |
| TradeMgr Hooks V1 | `docs/spec_authority/S2_TRADEMGR_HOOKS_V1.md` | Pkg 6 hook interfaces · trail mode · BE+1T · T1/T2 trail rules |
| Registry §S2 | `docs/reports/MEMS26_SYSTEMS_DECISIONS_REGISTRY_2026-05-23.md` | locks history · amendments timeline · cross-system dependencies |
| STATUS_BOARD amendment 17:50 | `docs/plans/STATUS_BOARD.md` | B1 + B2 already-documented findings |

Then walk every file under `backend/v9/systems/five_min/` (40 files) and classify each component vs spec:

- **KEEP** — implementation matches spec verbatim · no change needed
- **ADAPT** — implementation exists but has spec drift · small change needed
- **REPLACE** — implementation contradicts spec or is broken · rewrite needed
- **DEFER** — out-of-scope for this audit · note and move on
- **MISSING** — spec demands this exists but file/function does not

Output one row per file in the deliverable's classification table.

### Layer 2 · Live Database Evidence

Query SQLite `data/mems26_local.db` (NOT `backend/v9/v9.db` — that's an empty stub). Capture into the report:

```sql
-- S2 fire rate (today / 7d / 30d)
SELECT date(entry_ts) AS day, COUNT(*) AS fires, ROUND(AVG(pnl_r),2) AS avg_r
FROM v9_trades WHERE firing_system=2 AND entry_ts >= date('now','-30 days')
GROUP BY day ORDER BY day DESC;

-- S2 fire rate by day_type (cross_context.day_type)
SELECT json_extract(cross_context, '$.day_type') AS dt, COUNT(*) AS n
FROM v9_trades WHERE firing_system=2 AND entry_ts >= date('now','-30 days')
GROUP BY dt;

-- S2 exit reason distribution
SELECT exit_reason, COUNT(*) AS n, ROUND(AVG(pnl_r),2) AS avg_r
FROM v9_trades WHERE firing_system=2 AND state='CLOSED' AND entry_ts >= date('now','-30 days')
GROUP BY exit_reason ORDER BY n DESC;

-- v9_five_min_setups (if exists · check schema first)
.schema v9_five_min_setups
SELECT * FROM v9_five_min_setups ORDER BY id DESC LIMIT 20;

-- v9_five_min_state (current state)
.schema v9_five_min_state
SELECT * FROM v9_five_min_state ORDER BY id DESC LIMIT 5;

-- bar recency
SELECT MAX(ts) AS latest_bar, COUNT(*) AS today_bars
FROM v9_bars_5min WHERE ts >= datetime('now','-1 day');

-- v9_day_type_history (today)
SELECT * FROM v9_day_type_history WHERE created_at >= date('now') ORDER BY id DESC LIMIT 20;
```

Compare what S2 **actually fires** (Layer 2) vs what spec says it **should fire** (Layer 1) per day-type / pattern / mode. A gap is a finding.

### Layer 3 · Runtime Logs (at the moment of "should have fired but didn't")

Grep these logs · capture matching lines · attribute to S2 state:

```bash
LOGS="/tmp/backend.err.log /tmp/backend.out.log /tmp/bridge.err.log"
KEYWORDS='five_min|FiveMin|S2 |_detect_reactive|_detect_initiative|_detect_h_n_s|_detect_double|_detect_flag|NT skip|mode=|DAY_TYPE_MODE|FIRST_HOUR_TACTICAL|opening_type|current_day_type|_on_day_type_update|_check_setup|setup_emitter'
rg -n "($KEYWORDS)" $LOGS | tail -200
```

For each detector found in logs:
- Was it called today?
- Did it return a setup?
- Was the setup filtered (cooldown · NT skip · validator failure)?
- Did the setup reach `setup_emitter`?

For each detector NOT found in logs:
- Verify it has a code path that could be invoked
- Identify the gate that blocks it (mode · day_type · feature flag)

### Layer 4 · Replay/Backtest (hypothesis verification)

Run today's `v9_bars_5min` (RTH) through `FiveMinSystem` in isolation with three scenarios:

| Scenario | Mode | opening_type | Expected vs current |
|---|---|---|---|
| A — current behavior | FIRST_HOUR_TACTICAL (stuck) | None | Reproduces 0 fires today |
| B — fix B1 only | FIRST_HOUR_TACTICAL (still stuck) | OPEN_AUCTION_OUT (or whatever S1 said) | UI repair only · still 0 chart-pattern fires |
| C — fix B1 + B2 | DAY_TYPE_MODE (mode unlocked) | OPEN_AUCTION_OUT | All 10 patterns enabled · count counterfactual fires |

Output: `fires_counterfactual_C - fires_actual_A` = "trades lost today due to B1+B2".

Implementation hint: write a tiny replay script under `/tmp/s2_replay_2026-05-25.py` · do NOT commit. Reuse the existing `FiveMinSystem` class via a fresh in-memory instance · feed bars chronologically · capture emitted setups. Reference test patterns in `backend/v9/systems/five_min/tests/test_first_hour_matrix.py`.

### Layer 5 · Cross-System Snapshot Consistency

For each cross-system field, verify the value is consistent across **all four** consumers:

| Field | Producer | Consumer(s) | API endpoint | Drift? |
|---|---|---|---|---|
| `day_type` | S1 (DayType) | S2 · UI cockpit · `/status` | `/api/v9/status` · `/api/v9/day-type/*` | Today: `/status.day_type.current_type=UNKNOWN` but `hydration.day_type.confidence=38` → **drift** |
| `opening_type` | S1 | S2 · UI | same | Today: S2 sees None despite S1 having classified |
| `mode` (FIRST_HOUR / DAY_TYPE) | S2 self | UI · hydration | same | Today: hydration says DAY_TYPE · UI says FIRST_HOUR → **drift** |
| `bar_router stats` | bar_router | S2 · footprint · tick_reversal · woodies | `/status.bar_router` | Today: backlog growing → **operational drift** |

Each drift is a finding. Trace it to a wiring bug or a hydration ordering bug.

---

## 3 · Starting hypotheses (verify or refute)

You start the audit with these **4 hypotheses** already collected. Confirm each with ≥3 layers of evidence, or refute.

| ID | Hypothesis | Severity | Evidence so far | Layers needed |
|---|---|---|---|---|
| **B1** | `_on_day_type_update` doesn't update `self.opening_type` | LOW (cosmetic) | Layer 1 (code read) + Layer 5 (UI drift) | Need Layer 2 (DB consumed value) + Layer 4 (replay confirms no behavior diff) |
| **B2** | mode stuck in FIRST_HOUR_TACTICAL because bar_router backlog | HIGH | Layer 1 + Layer 2 (3/2638 fires) + Layer 5 (drift) | Need Layer 4 (replay quantifies trades lost) + Layer 3 (logs confirm mode value over time) |
| **B3** | bar_router backlog grows because footprint stream stuck (pushes=0 · 5 days per stream_health) | MED-HIGH | Layer 5 | Need Layer 3 (logs prove footprint blocks dispatcher) + Layer 1 (architecture: is dispatcher per-subscriber or shared?) |
| **B4** | day_type API drift: `/status.day_type.current_type=UNKNOWN` vs hydration `PENDING/38%` | MED | Layer 5 | Need Layer 1 (which endpoint is canonical?) + Layer 3 (which one updates and when?) |

You may discover **B5+**. Document each new bug the same way: hypothesis · severity · evidence per layer · spec violated · proposed fix scope (without writing the fix).

---

## 4 · Deliverable structure · `docs/reports/S2_AUDIT_2026-05-25.md`

```markdown
# S2 Audit Report · 2026-05-25 (POST-EOD)

## Executive summary
- Status: **RED / YELLOW / GREEN** per axis (Functional / Spec-Compliance / Operational / Wiring)
- Top 3 findings (one line each · severity · proposed package)
- Recommended next action (single sentence)

## Layer 1 · Spec-vs-Code findings
[narrative · 1-2 pages]

## Layer 2 · Live DB findings
[narrative + tables · 1-2 pages]

## Layer 3 · Log findings
[narrative + log excerpts · 1 page]

## Layer 4 · Replay results
| Scenario | Fires | Stops | T1 hits | T2 hits | T3 hits | net R |
|---|---|---|---|---|---|---|
| A current | 0 | — | — | — | — | 0 |
| B fix B1 | 0 | — | — | — | — | 0 |
| C fix B1+B2 | ? | ? | ? | ? | ? | ? |

## Layer 5 · Snapshot drifts
[per-field drift table]

## Bug catalog
| ID | Title | Severity | Layers confirmed | Spec violated | File:line | Proposed fix scope |
|---|---|---|---|---|---|---|
| B1 | ... | LOW | 1, 2, 4, 5 | D-091 §Coverage Matrix | five_min_system.py:252-264 | 3 lines + 2 tests · ~15min CC |
| B2 | ... | HIGH | 1, 2, 3, 4, 5 | D-091 §Patterns 5-10 | five_min_system.py:244-246 | TBD root-cause-dependent |
| B3 | ... | ... | ... | ... | ... | ... |
| B4 | ... | ... | ... | ... | ... | ... |
| B5+ | new findings | ... | ... | ... | ... | ... |

## Component classification (40 files)
| File | LOC | Classification | Spec ref | Notes |
|---|---|---|---|---|
| five_min_system.py | ... | ADAPT | D-091 §all | core orchestrator · 4 bugs found |
| state_machine.py | ... | KEEP | D-091.Q1 Stream 1.5 | wired in commit cf6383e |
| ... | ... | ... | ... | ... |

## Recommended fix-package sequence
| # | Package | Depends on | Estimated time | Reasoning |
|---|---|---|---|---|
| FIX-1 | B1 opening_type wiring | — | 15min CC + 2 tests | safe · cosmetic · unblocks Layer 5 verification |
| FIX-2 | B2 mode transition + bar_router root cause | FIX-1 | TBD | unblocks 6/10 patterns |
| ... | ... | ... | ... | ... |

## Open questions for Michael
1. ...
2. ...
3. ...

## Stop conditions hit during audit
[record any layer that hard-stopped]

## Sign-off
CC · 2026-05-25 ~23:XX IL · audit took XX minutes · checkpoint at 90min ✓/✗
```

---

## 5 · Pre-LIVE protocol compliance (mandatory)

Before declaring a hypothesis confirmed:

- [ ] Diagnosed across ≥3 layers (per §2 above)
- [ ] Current code READ via Read tool (not from memory)
- [ ] Audited existing surface (KEEP/ADAPT/REPLACE/DEFER · §1 above)
- [ ] Evidence from data (DB query · log read · replay)
- [ ] Confirmed the fix is NOT already in code (avoid P27.5d Option A mistake — proposing a fix that already exists)
- [ ] Bounded blast radius (smallest correct change · no "while I'm here")

Before proposing a fix scope:

- [ ] Four UAT axes (Quality / Recency / Cardinality / Latency) considered for the proposed change
- [ ] Regression test under `backend/v9/systems/five_min/tests/` planned
- [ ] No silent-failure paths added (logger.warning, not logger.debug, on push/connect errors)

---

## 6 · Source-of-truth reminders

- Live values come from Sierra Chart exports via bridge → API → DB (per `CLAUDE.md` §"Sierra real-time data").
- Bridge is **local-only** · CLOUD_URL must be `http://localhost:8000` (per `.cursor/rules/mems26-stability.mdc`).
- Frontend polling floors are NOT to be raised (per `CLAUDE.md` §"Frontend Polling Floors").
- No `*.pyc` / `__pycache__/` commits.
- After audit completion → ask Michael for approval before drafting any fix.

---

## 7 · Reporting workflow

When the audit is complete:

1. Save `docs/reports/S2_AUDIT_2026-05-25.md` (no commit unless Michael asks).
2. Post a 3-bullet summary to the chat with: status / top finding / recommended next package.
3. Wait for Michael's approval before proceeding to FIX-1.

---

**End of mega-prompt · Cursor · 2026-05-25 18:42 IL.**
