# MEMS26 Candidate Ledger Contract

**Status:** implementation in progress (writer + hooks, flag default OFF).
JSONL events ship first; migration 024 is written but not applied to live DB.
cc-macbook still owns EOD RESOLVED. Cursor tests cover writer/hooks.
**Behavior:** observability only. Ledger failure must never alter detection,
gateway verdict, size, order, stop or target.

## 1. Existing surfaces — ADAPT, not a third source

- Append-only event stream:
  `GATEWAY_DECISIONS_PATH` / `gateway_decisions.jsonl` + decisions archive.
- S2 detection index:
  `v9_five_min_setups`.

No `v9_candidate_events` table and no second JSONL.

## 2. Lifecycle

```text
DETECTED
  → EMIT_DECISION (ALLOW | REJECT)
  → GATE_DECISION (blocked)  |  ROUTED (not blocked)
  → RESOLVED
```

`GATE_DECISION` and `ROUTED` are **mutually exclusive** on a single row
(`trading_gateway.py:814`): a candidate is either blocked (GATE_DECISION) or
routed (ROUTED), never both. They are not two sequential stages — a funnel
that expects to see both will show "0% routed" for every blocked candidate.

Not every candidate reaches every stage. Missing stages are meaningful.

## 3. Candidate identity

`candidate_id = SHA256(canonical identity JSON)`

Identity fields:

```text
schema_version
system_id
pattern
direction
signal_bar_ts (UTC, floored to canonical 5m)
variant_tag (or "")
```

Do not include pid, commit, DB row ID, ingestion time or policy verdict.
The same market candidate must retain the same ID across restart/replay.

`event_id = SHA256(candidate_id + event_type + stage_key)`.

Readers deduplicate by `event_id`. Same-bar re-push must not create a second
event.

## 4. Event schema

Required on every event:

```text
schema = "candidate_ledger.v1"
event_id
candidate_id
event_type
observed_at
signal_bar_ts
system
pattern
family
direction
source:
  pid
  machine_tag
  code_commit
  mode
policy_id
```

When available:

```text
prices:
  entry
  stop
  t1/t2/t3/t4
context:
  day_type
  determined
  phase
  day_direction
  location
  opening_type
  volume_features
  cvd_reading
decision:
  stage
  verdict
  blocked_by
  reason
  trade_id
outcome:
  mfe_3/mae_3
  mfe_6/mae_6
  mfe_12/mae_12
  t1_before_stop
  resolved_at
```

Missing field remains null/absent. Never synthesize a value.

## 5. Producer hooks (live file:line)

ADAPT the three existing persist sites. Do not add a fourth table, do not
route through `missed_trade_detector`, and do not treat `context_radar.py`
(hardcoded live JSONL path) as ledger truth.

### S2 — `five_min_system.py`

Today a detection row is written only after sizing, before emit:

- persist site: `five_min_system.py:2238-2273` (`V9FiveMinSetup`, warning-only
  on failure, does not block emit/gateway)
- emitter: `setup_emitter.py:36-234`
- gateway call: `five_min_system.py:2533`

**Ledger hooks:**

1. When a pattern has `direction` set and is about to be persisted (`:2238`):
   compute `candidate_id`, write `DETECTED` to JSONL, store `candidate_id` on
   the setup ORM row and on the in-memory setup dict.
2. If `direction` was set then cleared by dedup (`:1885-1894`) or FHB
   (`:1896-1905`): still write `DETECTED` + `EMIT_DECISION=REJECT` with
   `blocked_by=dedup|fhb`. These are real candidates that currently vanish.
3. Inside `emit_t1_setup`, before every `return None` (NO_TRADE `:56-73`,
   Auth SKIP `:83-143`, pre_fire_validator `:226-228`) and before successful
   return: append `EMIT_DECISION`. Optional `candidate_id` argument only;
   flag-off behavior must stay byte-identical.
4. ANTI-PHANTOM skip (`:2470-2511`) is log-only today and never reaches
   `route_setup`. Write `EMIT_DECISION=REJECT blocked_by=anti_phantom`.

Do not evaluate detectors the live priority chain did not evaluate.
Counterfactual candidates belong to replay, not the live ledger.

### S4 — `woodies_system.py`

Today every detected pattern is persisted in LIVE mode regardless of
`ready_to_route`; gateway is called only when the decision tree is ready:

- pattern list from `pattern_engine.detect_all_patterns`
- in-memory `ready_to_route` / `failed_stages`: `:1201-1205`
- `route_setup` only if ready: `:1209-1277`
- duplicate-bar skip: `:1222-1229` (no JSONL)
- sizing reject: `:1239` (no gateway call)
- persist: `_persist_pattern` `:1371-1400` via `safe_execute`

**Ledger hooks:**

1. For each item in `patterns` (`:1339-1340`): write `DETECTED` and stamp
   `candidate_id` onto `v9_woodies_signals` (nullable column, see §7).
2. Selected `best` carries `candidate_id` into the gateway setup dict.
3. Non-selected detected patterns remain ledger-only (`DETECTED`, no gate).
4. If `ready_to_route=False`, sizing=`reject`, or `duplicate_bar_ts`: write
   `EMIT_DECISION=REJECT` with the in-memory reason. This is the main hole —
   those candidates never reach `gateway_decisions.jsonl` today.

### Gateway — `trading_gateway.py:678-818`

At `route_setup` after `_route_setup_inner` (`:746-776`):

- preserve `candidate_id` from setup metadata;
- append `GATE_DECISION` and `ROUTED` to the same JSONL;
- keep backward-compatible fields (`blocked_by`, `outcome`, `reason`,
  `trade_id`, `live_blocked_by`);
- widen `mfe_track` (`:765-774`) to every blocked gate, not only
  `awaiting_release` / `daytype_playbook`. Computation of MFE stays EOD.

Wrap exactly like `_persist_decision`: never raise into `process_bar` /
`route_setup` / the gate chain.

## 6. JSONL compatibility

All new events use the existing decisions file.

Existing readers must explicitly choose:

- `/api/v9/gateway/decisions`: `event_type in {GATE_DECISION, ROUTED}` plus
  legacy rows without event_type.
- context radar/gate audits: same decision filter unless studying candidates.
- hydration: hydrate UI decision rows, not DETECTED/RESOLVED events.
- EOD/archive: archive all event types.

No reader may silently count DETECTED as a block/fire.

## 7. Migration 024

Full design: `docs/spec_authority/CANDIDATE_LEDGER_MIGRATION_024.md`.

Summary: additive nullable columns on `v9_five_min_setups` and
`v9_woodies_signals`. No new table. No backfill. No archive-schema change
(`session_boundary` copies woodies via an explicit column list, so extra live
columns are ignored). Local Postgres only. Snapshot first.

Also add the already-existing DB column `v9_five_min_setups.is_synthetic` to
the ORM model (019 added it; the model still omits it). Do not invent values.

## 8. Writer safety

- one central writer module for S2/S4/gateway JSONL events.
- process-local lock around append.
- `PYTEST_CURRENT_TEST` + `GATEWAY_DECISIONS_PATH` tmp fixture. New ORM
  writes must also no-op or use the test session — today's S2 persist uses
  live `SessionLocal()` and can hit production Postgres from tests.
- serialization/IO exceptions:
  - warning rate-limited;
  - `swallowed("candidate_ledger:<stage>")` if that helper is wired (T-98);
    if not, warning-only is enough;
  - return false;
  - never raise into trading path.
- no DB transaction shared with order routing.
- flag `CANDIDATE_LEDGER_V1` default OFF; it wraps writes only, never
  detection or routing.

## 9. RESOLVED event

EOD resolver:

1. reads DETECTED events for session;
2. loads validated canonical bars;
3. computes MFE/MAE from candidate decision time, direction and entry;
4. appends one idempotent RESOLVED event;
5. never changes historical DETECTED/GATE rows.

Sessions failing Replay Kernel data quality become:

```text
RESOLVED outcome_status = NOT_JUDGEABLE
reason_codes = [...]
```

They are never dropped.

## 10. Acceptance tests

1. Known candidate blocked at gateway:
   DETECTED → EMIT_ALLOW → GATE_BLOCK with same candidate_id.
2. Emitter-rejected candidate has DETECTED + EMIT_REJECT and no gate event.
3. S4 two detected patterns: two DETECTED events, one selected route.
4. S4 `ready_to_route=False` (or sizing reject): DETECTED + EMIT_REJECT, zero
   `route_setup` calls, zero legacy-shaped decision rows.
5. S2 FHB/dedup clear after `direction` was set: DETECTED + EMIT_REJECT.
6. Same-bar re-push: event count unchanged.
7. Restart/replay: candidate_id unchanged.
8. pytest writes zero production JSONL lines and zero production ORM rows
   (`v9_five_min_setups` / `v9_woodies_signals`).
9. writer exception: gateway verdict/result byte-identical.
10. legacy gateway API counts unchanged on same fixtures.
11. migration rerun idempotent; historical `candidate_id` remains NULL.
12. RESOLVED rerun appends zero duplicates.
13. Flag OFF: zero new event_type values in the live JSONL.

## 11. Rollout

1. snapshot before migration;
2. migration dry-run;
3. code default OFF (`CANDIDATE_LEDGER_V1=0`);
4. tests + baseline parity;
5. enable shadow-observability only under existing Stage-1 approval;
6. restart outside forbidden window;
7. verify one live candidate lifecycle + API count parity;
8. independent review GO.

Ledger flag controls writes only. It must not wrap or gate detection/routing.
