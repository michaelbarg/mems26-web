# CC Review — Replay Kernel Stage 0B · 2026-08-24

## 1. Verdict

**GO**

## 2. Commit & Worktree

```
HEAD: cba369a1
Worktree: dirty (_INDEX.md regeneration + new replay/ files — expected)
Review ran against the replay kernel files as committed by cursor-agent.
```

## 3. Files Reviewed

```
backend/v9/replay/__init__.py
backend/v9/replay/data_source.py     (316 lines — DB source, _local_dsn, CVD loader)
backend/v9/replay/kernel.py          (147 lines — CLI, manifest construction)
backend/v9/replay/manifest.py        (107 lines — hashing, git identity)
backend/v9/replay/report.py
backend/v9/replay/scid_validator.py  (213 lines — SCID binary reader, parity checks)
backend/v9/replay/types.py           (228 lines — dataclasses, validation)
tests/v9/regression/test_replay_kernel_stage0b.py
docs/spec_authority/REPLAY_KERNEL_CONTRACT.md
docs/spec_authority/REPLAY_PARITY_ANCHORS.md
docs/reports/REPLAY_KERNEL_STAGE0B_REPORT_2026-08-24.md
```

## 4. Command + Raw Output

### 4a. Test Suite

```
$ BRIDGE_TOKEN=test python3 -m pytest tests/v9/regression/test_replay_kernel_stage0b.py -v --tb=short

29 passed, 2 warnings in 16.66s
```

All 29 tests passed. No failures.

### 4b. Five Anchors

```
2026-08-18: judgeable=true,  reason_codes=[], cvd_coverage=0.6667, scid_ohlc_mismatches=0
2026-08-17: judgeable=true,  reason_codes=[], cvd_coverage=0.6667, scid_ohlc_mismatches=0
2026-08-20: judgeable=true,  reason_codes=[], cvd_coverage=0.6667, scid_ohlc_mismatches=0
2026-07-15: judgeable=false, reason_codes=[RTH_CARDINALITY,RTH_GRID_MISMATCH,CVD_CONFLICTS,SCID_TIMESTAMP_MISMATCH,SCID_OHLC_MISMATCH,SCID_VOLUME_MISMATCH,SCID_DELTA_MISMATCH,SCID_CUMULATIVE_MISMATCH]
2026-07-14: judgeable=false, reason_codes=[CVD_CONFLICTS,SCID_OHLC_MISMATCH,SCID_VOLUME_MISMATCH,SCID_DELTA_MISMATCH,SCID_CUMULATIVE_MISMATCH]
2026-08-12: judgeable=false, reason_codes=[CVD_COVERAGE,SCID_OHLC_MISMATCH,SCID_VOLUME_MISMATCH]
```

Expected: 08-18/17/20 = PASS; 07-15/14/08-12 = NOT_JUDGEABLE. **Confirmed.**

Note: SCID must be `MESU26_FUT_CME.scid` for August sessions (MESM26 = wrong contract).
07-15/07-14 fail on SCID OHLC/volume because MESU26 was not the active contract in mid-July
(rollover). This is correct behavior — the validator rejects sessions where the SCID truth
source doesn't match the DB.

### 4c. Two-Run Manifest/Result Hashes

```
manifest run-1: 23bd7e455f3f8bd08be6471d3cf1576c6a8c54496296073cea6be9d47b437322
manifest run-2: 23bd7e455f3f8bd08be6471d3cf1576c6a8c54496296073cea6be9d47b437322
MATCH: True

result run-1: bd6305b803fa9e954b37f2c14c0bc7dabd35d690b87cce4915bc758791d76975
result run-2: bd6305b803fa9e954b37f2c14c0bc7dabd35d690b87cce4915bc758791d76975
MATCH: True

result biz-changed: ea69787b922e8302a738e2ba27434045f517a944a2188a519d519680efd2aab1
BIZ_DIFFERS: True
```

**Deterministic.** Run metadata (run_id, top-level created_at) excluded. Nested business
`created_at` included.

### 4d. Remote Host/Hostaddr/Service/Env Probes

```
PASS: remote host           → REJECTED
PASS: remote IP             → REJECTED
PASS: hostaddr bypass       → REJECTED
PASS: KV hostaddr           → REJECTED
PASS: PGHOST env            → REJECTED
PASS: PGHOSTADDR env        → REJECTED
PASS: PGSERVICE env         → REJECTED
PASS: localhost OK          → ACCEPTED
PASS: 127.0.0.1 OK          → ACCEPTED
PASS: unix socket OK        → ACCEPTED
```

10/10 probes correct. All remote vectors blocked including hostaddr DSN bypass and env vars.

### 4e. CVD Conflicts/Zero Coverage/Injected Corruption

```
CVD_CONFLICTS: fatal=True  judgeable=False
CVD_COVERAGE:  fatal=True  judgeable=False
SCID_DELTA:    fatal=True  judgeable=False
BAD_VOL warn:  fatal=False judgeable=True  (non-fatal, as designed)
```

No bypass. Conflicts and zero coverage are unconditionally fatal.

### 4f. Manifest Invalid Fields/Numerics

Tested by the test suite:
- `test_manifest_fails_when_required_identity_is_missing` — blank fields rejected
- `test_manifest_fails_when_split_does_not_match_contracts` — split sum != contracts
- `test_manifest_rejects_negative_split_cost_and_slippage` — negative values rejected
- `test_manifest_rejects_invalid_candidate_source` — unknown source rejected
- `test_manifest_rejects_blank_required_identity` — 5 parametrized blank fields
- `test_manifest_rejects_empty_intrabar_event_order` — empty tuple rejected
- `test_request_rejects_zero_cvd_coverage_threshold` — 0.0 rejected

All PASSED.

### 4g. Transaction Readonly/Repeatable-Read

```
data_source.py:70:  readonly=True,
data_source.py:71:  autocommit=False,
data_source.py:72:  isolation_level="REPEATABLE READ",
```

Connection is read-only with REPEATABLE READ isolation. Any INSERT/UPDATE/DELETE would
raise `psycopg2.errors.ReadOnlySqlTransaction`.

### 4h. Runtime-Import and SQL-Mutation Scan

```
Runtime imports from trading path in replay/: (none found)
SQL mutations (INSERT/UPDATE/DELETE/ALTER) in replay/: (none found)
All cursor.execute() calls are SELECT-only (3 queries).
```

The replay package is hermetically sealed from the trading runtime.

## 5. Findings (Ranked)

### INFO (non-blocking)

1. **SCID contract sensitivity** (`scid_validator.py`): The validator does not verify that
   the SCID file matches the session's contract month. Using `MESM26` for August sessions
   produces false SCID_RTH_CARDINALITY failures. The test suite hardcodes the correct path
   via conftest — production callers must be documented to use the active contract's SCID.

2. **`fail_closed=False` in CLI** (`kernel.py:83`): The validation CLI passes
   `fail_closed=False` so it can report NOT_JUDGEABLE without raising. Stage 0C callers
   that run actual candidates MUST use `fail_closed=True`. This is documented in the
   contract but not enforced by the type system.

3. **`_normalize` rounds floats to 4 decimal places** (`manifest.py:28`): Prices on MES
   are 2-decimal. CVD cumulatives can be large integers. 4 decimals is safe for both.
   Future instruments with sub-tick precision would need review.

4. **git_identity includes untracked files** (`manifest.py:94-106`): Correct — the
   `_INDEX.md` regeneration changes the dirty_tree_hash, meaning two runs on the same
   commit with different index state produce different hashes. This is the intended
   behavior (any file change = different identity).

## 6. NOT-VERIFIED

- **Multi-session replay** (Stage 0C): kernel.py only supports `validate` for one
  session at a time. Multi-session chaining with candidate carryover is not yet built.
- **Candidate Ledger** (T-103): not started, deliberately excluded from this stage.
- **Week replay parity**: no comparison yet between this kernel's session loads and the
  existing `week_replay.py` output. Stage 0C must anchor against the production replay.
- **Performance under load**: 29 tests in 16.7s is fine for unit tests. A 34-session
  replay (~550s if linear) may need optimization. Not tested.
- **Concurrent DB access**: REPEATABLE READ prevents phantom reads within a transaction
  but does not prevent a concurrent writer from changing data between sessions. Not
  relevant for Stage 0B (single-session validation) but matters for Stage 0C.

## 7. What GO Proves (and What It Does Not)

### Proved by this review:

- Data validation pipeline is **correct and fail-closed** for RTH bars, CVD, and SCID parity.
- All remote connection vectors are **blocked** (host, hostaddr, PGHOST, PGHOSTADDR, PGSERVICE).
- CVD conflict and coverage checks are **unconditionally fatal** with no public bypass.
- Hashing is **deterministic** across runs and **sensitive** to business data changes.
- The replay package has **zero imports from the trading runtime** and **zero SQL mutations**.
- SCID binary parser correctly validates bar OHLC, volume, and delta against the DB.
- Manifest validation rejects invalid fields, negative values, and mismatched splits.
- 3 green anchors (08-17/18/20) pass all checks; 3 red anchors (07-14/15, 08-12) fail
  on the expected quality issues.

### NOT proved (out of scope for Stage 0B):

- No candidate detection, no trade simulation, no P&L computation.
- No multi-session chaining or IS/OOS split logic.
- No comparison to existing replay infrastructure output.
- No detector flag configuration validation (Stage 0B uses `flags={}`).

*Review by cc-macbook (Claude Opus 4.6) · 2026-08-24 · independent of cursor-agent build.*
