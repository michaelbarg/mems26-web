# Replay Kernel Stage 0B — Implementation Report (2026-08-24)

**Approval:** Michael approved Stage 0B after Stage 0A.  
**Scope:** kernel skeleton + manifest/hash + read-only DB source + SCID validator
+ validation report/CLI.  
**Explicitly excluded:** CandidateEngine, policy migration, execution model,
Ledger, live/runtime wiring, DB repair.

## Files

```text
backend/v9/replay/__init__.py
backend/v9/replay/types.py
backend/v9/replay/manifest.py
backend/v9/replay/data_source.py
backend/v9/replay/scid_validator.py
backend/v9/replay/report.py
backend/v9/replay/kernel.py
tests/v9/regression/test_replay_kernel_stage0b.py
```

## What works

- required manifest fields validate; contract split must equal contracts.
- canonical JSON + SHA-256 result/manifest/data/flag hashes.
- git HEAD + staged/unstaged/untracked dirty-tree hash captured read-only.
- Postgres is local-only, `readonly=True`, one repeatable-read transaction.
- RTH cardinality/grid/duplicates/seams/volume quality gates.
- deterministic CVD: identical duplicate collapse; conflicting values fail.
- exact-bar CVD coverage threshold is explicit (default 50%); zero coverage fails.
- SCID validator compares DB delta and cumulative on every overlapping bar.
- TPO records carry market timestamp and availability timestamp.
- SCID binary-search validator compares timestamp + OHLC + volume.
- fail-closed CLI returns status `NOT_JUDGEABLE` and exit code 2.
- runtime entrypoints contain no `backend.v9.replay` imports.

## CLI

```bash
BRIDGE_TOKEN=test DATABASE_URL=postgresql://localhost/mems26 \
python3 -m backend.v9.replay.kernel validate \
  --session 2026-08-18 \
  --scid-validator ~/SierraChart/Data/MESU26_FUT_CME.scid \
  --contracts 4 --contract-split 1,1,1,1 \
  --json /tmp/kernel-2026-08-18.json
```

## Five-anchor result

```text
2026-08-18 rc=0 PASS []
  bars=78 · scid=78 · OHLC mismatch=0 · volume mismatch=0 · CVD conflict=0

2026-08-17 rc=0 PASS []
  bars=78 · scid=78 · OHLC mismatch=0 · volume mismatch=0 · CVD conflict=0

2026-08-20 rc=0 PASS []
  bars=78 · scid=78 · OHLC mismatch=0 · volume mismatch=0
  CVD rows=178 → 89 unique, identical duplicates collapse, conflicts=0

2026-07-15 rc=2 NOT_JUDGEABLE
  RTH_CARDINALITY · RTH_GRID_MISMATCH · CVD_CONFLICTS
  SCID_TIMESTAMP_MISMATCH · SCID_OHLC_MISMATCH · SCID_VOLUME_MISMATCH
  SCID_DELTA_MISMATCH · SCID_CUMULATIVE_MISMATCH
  DB=60 · SCID=78 · missing=18 · close-match=1

2026-07-14 rc=2 NOT_JUDGEABLE
  CVD_CONFLICTS · SCID_OHLC_MISMATCH · SCID_VOLUME_MISMATCH
  SCID_DELTA_MISMATCH · SCID_CUMULATIVE_MISMATCH
  CVD conflict timestamps=24 · one OHLC/volume mismatch

2026-08-12 rc=2 NOT_JUDGEABLE
  CVD_COVERAGE (0/78) · SCID_OHLC_MISMATCH · SCID_VOLUME_MISMATCH
```

The 07-14 result strengthens the Stage-0A caveat: 78/78 close-match is not
full OHLCV parity.

## Determinism

```text
same unchanged worktree:
manifest_hash identical = True
result_hash identical   = True
```

Run-instance `run_id` and `created_at` are excluded from stable identities.
Staged, unstaged and untracked changes all feed `dirty_tree_hash`.
Exact golden hashes will be pinned only on a committed Stage-0B tree; embedding
a pre-commit dirty-tree hash in this changing report would make it stale.

## Tests

```bash
BRIDGE_TOKEN=test DATABASE_URL=postgresql://localhost/mems26 \
python3 -m pytest tests/v9/regression/test_replay_kernel_stage0b.py -q
```

```text
29 passed, 2 warnings in 12.81s
```

IDE diagnostics: 0 errors in `backend/v9/replay` and Stage-0B tests.

## Safety proof

- no INSERT/UPDATE/DELETE/DDL path;
- no `.env` write;
- no service/order call;
- no runtime import;
- no existing replay script changed or retired;
- outputs only stdout / caller-selected JSON.

## NOT DONE

- CandidateEngine.
- Current-policy adapter.
- ExecutionModel.
- canonical candidate/trade output.
- parity against Stage-0A candidate hashes.
- causal TPO level selection (events carry `available_at`; no policy consumes
  them in 0B).
- secret-free pinned detector-flag fixture for Stage 0C.
- conversion of 52 tools.
- Candidate Ledger.
- DB repair.

## Gate

**GO — Stage 0B closed.** Independent review:
`docs/reports/CC_REVIEW_REPLAY_KERNEL_STAGE0B_2026-08-24.md`
(commit `cd0fda6c`). Stage 0C remains separate and requires explanation +
Michael approval.

## Independent anchor-review qualification

The five top-level statuses and repeated hash were independently reproduced.
Full parity is intentionally unproven in 0B:

- green anchors prove DB/SCID/CVD quality only;
- red anchors may emit multiple honest failure reasons;
- candidate/context/execution hashes belong to Stage 0C;
- full `.env` hash is not used as a safe fixture.

Stage 0B records an empty effective detector-flag set because it executes no
detectors. Stage 0C will require an explicit secret-free effective-flags
snapshot; it will not infer behavior from raw `.env` alone.

## Independent code-review NO-GO and remediation

The first code review correctly returned **NO-GO**. Remediated:

1. SCID validator is mandatory in the official CLI.
2. the CVD-conflict bypass was removed.
3. minimum exact-bar CVD coverage is explicit; zero coverage fails.
4. SCID delta/cumulative parity is checked; injected corruption fails.
5. a later NULL duplicate cannot overwrite a usable CVD row.
6. manifest now includes run/date/intrabar/CVD-coverage identity and rejects
   invalid candidate source, negative split/cost/slippage.
7. TPO source is honestly named
   `v9_tpo_history.created_at_as_observed_availability`; no 0B policy consumes it.
8. validation-only executes no detectors, so effective detector flags are
   explicitly empty; Stage 0C requires a safe snapshot.
9. dirty hash includes staged changes.
10. DB source rejects remote hosts and uses one read-only repeatable snapshot.

The second review found four remaining API-level bypasses. Also fixed:

11. public `ReplayRequest` no longer exposes a CVD-clean bypass;
    `min_cvd_coverage` must be >0.
12. local DSN parsing rejects URL-query host, libpq service, `PGHOST` and
    `PGSERVICE` remote indirection.
13. every required manifest identity string and numeric boundary is validated.
14. hash stripping is path-specific; domain `created_at` remains
    hash-significant.

15. explicit/query/env `hostaddr` remote routing is rejected in addition to
    `host` and service indirection.

Added anti-tautological tests for every class above. Final targeted suite:
**29 passed**. Final adversarial review: **GO**.
