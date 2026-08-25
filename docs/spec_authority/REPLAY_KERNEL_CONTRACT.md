# MEMS26 Replay Kernel Contract

**Status:** DRAFT — Stage 0A, no implementation authority yet.  
**Ruling boundary:** this contract governs research/replay consistency. It does
not change live trading behavior, flags, data writers, or source-of-truth.

## 1. Purpose

One replay kernel must answer:

> Given the same market data available at decision time, the same detector
> code, the same policy and the same execution assumptions, what candidates,
> decisions and outcomes result?

Scenario scripts may choose inputs/policies. They may not implement their own
loader, detector mirror, cost model, slot semantics or implicit defaults.

## 2. Non-negotiable invariants

1. **No second source-of-truth.** Official replay reads the validated DB path
   used by live. SCID validates/repairs DB; it is not a parallel policy source.
2. **No lookahead.** A datum is visible only when `available_at <= decision_at`.
3. **Live code reuse.** Candidate geometry imports live pure detector functions.
   Mirrors are forbidden unless a parity test proves byte-equivalence and the
   mirror is marked temporary.
4. **Every default is explicit in the manifest.**
5. **Same input is deterministic.** Two runs produce the same canonical JSON
   hash.
6. **Oracle is a ceiling, never a candidate/outcome label for GO.**
7. **Research cannot mutate DB, `.env`, services, orders or live files.**

## 3. Kernel pipeline

```text
ReplayDataSource
    ↓ ReplaySession
ReplayCandidateEngine
    ↓ CandidateEvent[]
ReplayPolicy
    ↓ PolicyDecision[]
ReplayExecutionModel
    ↓ SimulatedTrade[]
ReplayReport
    ↓ canonical JSON + manifest + hash
```

## 4. Data contracts

### 4.1 `ReplayManifest`

Required fields:

```text
schema_version
run_id
created_at
git_commit
dirty_tree_hash
machine_tag
data_source_id
data_snapshot_hash
date_start/date_end/session_dates
timezone_policy
rth_window
rth_end_inclusive
candidate_engine_id
candidate_source = redetect_live | setups | decisions | trades | oracle | mixed | validation_only
policy_id
execution_model_id
contracts
contract_split
commission_round_turn
slippage_ticks_entry/exit
slot_count
entry_budget_policy
feature_flags
detector_flags_hash
daytype_mode
daytype_flags_set_id
cvd_source
cvd_alignment_rule
cvd_min_coverage
tpo_source
same_bar_ranking
entry_cutoff
max_entries_per_day
mae_scratch_mode
intrabar_event_order
is_window/oos_window
lookahead_layers
random_seed (or NONE)
```

Missing required field = replay refuses to run.

### 4.2 `ReplaySession`

```text
session_date
symbol/contract
bars_5m[]
woodies_features[]
cvd_5m[]
tpo_events[]
prior_day_levels
quality_report
source_hashes
```

Every time-varying record contains:

```text
market_ts
available_at
source
source_version
quality
```

### 4.3 `CandidateEvent`

```text
candidate_id
system
pattern
family
direction
detected_at
confirmed_at
decision_at
entry_reference
structural_anchor
features
source_pid/source_mode/code_commit
```

`candidate_id` is a deterministic hash of stable identity fields. It does not
contain database row IDs.

### 4.4 `PolicyDecision`

```text
candidate_id
verdict = ALLOW | SKIP | WAIT | EXPIRE
reason_code
reason_detail
size_intent
stop_policy
target_policy
policy_id
decided_at
```

### 4.5 `SimulatedTrade`

```text
candidate_id
entry_ts/price
stop/targets/split
fills[]
exit_ts/price/reason
gross_pnl
commission
slippage
net_pnl
mfe/mae
bars_held
```

## 5. Canonical interfaces (conceptual)

```python
class ReplayDataSource:
    def load_sessions(self, request: ReplayRequest) -> list[ReplaySession]: ...

class ReplayCandidateEngine:
    def generate(self, session: ReplaySession) -> list[CandidateEvent]: ...

class ReplayPolicy:
    def decide(
        self, candidate: CandidateEvent, state: ReplayState
    ) -> PolicyDecision: ...

class ReplayExecutionModel:
    def execute(
        self, session: ReplaySession, decisions: list[PolicyDecision]
    ) -> list[SimulatedTrade]: ...

class ReplayReport:
    def build(
        self, manifest: ReplayManifest, candidates, decisions, trades
    ) -> CanonicalReplayOutput: ...
```

The implementation may use dataclasses/Pydantic, but field semantics may not
change without a schema-version bump.

## 6. Data-source rules

### Validated DB source

Official reports use a DB snapshot that passed:

- 78 RTH bars/session (normal session).
- no missing/duplicate timestamps.
- no seams.
- DB↔SCID validator.
- deterministic CVD uniqueness.
- TPO availability causality.

### SCID validator

SCID may:

- prove missing/wrong bars;
- rebuild expected OHLCV/delta for a diff;
- supply checksums and repair input.

SCID may not silently replace DB bars in an official replay. A repair follows
snapshot + migration protocol.

## 7. Candidate-engine rules

- Import live S1/S2/S4 detector functions.
- Preserve detector order only when order is part of the named scenario.
- Record all candidates before gateway policy.
- Shadow-only producers are marked; they do not become live candidates unless
  the scenario explicitly states research-only.
- Any duck shim or mirror is listed in the manifest and requires parity tests.

## 8. Policy rules

- `current` means current code+flags as captured in manifest.
- Challengers have immutable `policy_id`.
- Policy cannot call future bars or final-day levels.
- Policy does not alter candidate geometry.
- `CONTEXT_ENTRY` will implement this interface; replay/live adapters serialize
  the exact same input.

## 9. Execution-model rules

Mandatory explicit dimensions:

- contract count and split;
- stop/target producer;
- target/stop collision precedence;
- T0/T1/T2/T3/T4 behavior;
- BE/trail/MAE/T-10/P3 switches;
- entry/exit slippage;
- commission;
- one/two/unlimited slots;
- same-bar candidate priority;
- session close handling.

No execution dimension may default from ambient `.env` without being copied to
the manifest.

## 10. Output and determinism

Canonical JSON:

```text
manifest
session_quality
candidates
decisions
trades
per_day
summary
warnings
not_modeled
```

Hash procedure:

1. sort map keys;
2. sort candidates by `(decision_at, candidate_id)`;
3. normalize floats to declared precision;
4. exclude `created_at/run_id`;
5. SHA-256 canonical JSON.

Same data+commit+scenario must yield the same hash.

Additional hashes:

- `bar_data_hash`: canonical sorted pre-filter DB pull.
- `candidate_population_hash`: IDs + decision timestamps before policy.
- `detector_flags_hash`: sorted effective env snapshot after loader.
- `per_day_hash`: canonical candidates/decisions/trades per session.

Cross-tool dollar comparison is forbidden unless candidate-source, bar hash,
policy, execution model, contract split, intrabar order and costs match.

## 11. Parity gates

### Five anchor sessions

| Date | Role | Required assertion |
|---|---|---|
| `2026-08-18` | clean BALANCE control (`Variation`, no discovery event) | 78 bars; 15 current / 1 max candidates; hashes pinned |
| `2026-08-17` | clean `Trend_DD`, profitable-book day | discovery direction + CONT policy + runner semantics |
| `2026-08-20` | clean `Neutral_Extreme`, dual-side structure | structural event transition / balance re-entry parity |
| `2026-07-15` | deliberate DB/SCID failure | `NOT_JUDGEABLE`; DB 60 vs SCID 78, close-match 1/78 |
| `2026-07-14` | deliberate TPO/CVD causality failure | 0 future TPO; fail `CVD_CONFLICTS` until repaired |

The first three must pass parity. The last two must fail closed until T-99/T-100
repair; turning either green by silently excluding/replacing bars is a test
failure. Full hashes and expected outputs:
`docs/spec_authority/REPLAY_PARITY_ANCHORS.md`.

### Live/replay candidate parity

For a frozen fixture:

```text
live detector adapter output == replay candidate output
```

### Context parity

```text
serialize(ContextEntryInput) once
replay_output = decide(input)
shadow_output = decide(input)
assert canonical_bytes(replay_output) == canonical_bytes(shadow_output)
```

### Old-tool adapter parity

For each retained scenario, five anchors compare:

- candidate IDs;
- decisions/reasons;
- entries/stops/targets;
- trade exits and net P&L;
- manifest assumptions.

Differences require an explicit migration note; “close enough” is not parity.

## 12. Failure policy

Replay is **NOT-JUDGEABLE** when:

- session quality fails;
- TPO level was unavailable at decision time;
- conflicting CVD rows are unresolved;
- required Sierra features are missing;
- source/commit/policy identity is absent;
- hidden ambient default is detected.

NOT-JUDGEABLE sessions are reported, never silently dropped from a headline.

## 13. Migration policy

1. Inventory every existing tool.
2. Classify `KEEP_PRIMITIVE / THIN_ADAPTER / RETIRE_AFTER_PARITY /
   OUT_OF_SCOPE`.
3. Implement kernel.
4. Convert one scenario at a time.
5. Prove parity on anchors.
6. Mark old script deprecated.
7. Retire only after its reports/consumers are migrated.

No bulk deletion.

## 14. Approval boundary

Stage 0A approves only this contract and inventory. Kernel implementation is a
separate stage requiring Michael's approval after independent review.
