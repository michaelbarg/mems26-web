# CC — GAP-5 hydrate_demo_slot broken: wrong column (`system_id` → `firing_system`) — 2026-07-02

**Owner:** Michael · **Prepared by:** Cowork (live diagnosis 13:1x IL) · **Contract:** `docs/handoff/CC_HANDOFF_CONTRACT.md` (Rule 5 raw output, anti-tautological tests, NOT-DONE section mandatory).
**Priority:** אחרי-שעות היום (לא חוסם 16:30 — ראה Impact) · **Risk surface:** none added (fixes an already-approved feature, fail-safe path stays).

## Evidence (raw, from today's 12:59:50 boot — /tmp/backend.err.log:885335+)
```
[env_loader] applied 50 vars ... DAYTYPE_POSITION_GATE=0 DAYTYPE_PLAYBOOK=1
INFO:     Started server process [53144]
[db.read] read_one failed: (psycopg2.errors.UndefinedColumn) column "system_id" does not exist
LINE 1: ... id, direction, entry_price, pattern_id_at_entry, system_id ...
[SQL: SELECT id, direction, entry_price, pattern_id_at_entry, system_id FROM v9_trades WHERE mode = 'demo' AND state NOT IN ('CLOSED', 'CANCELLED') ORDER BY id DESC LIMIT 1]
```
Schema truth (psql, information_schema): the column is **`firing_system`** — `system_id` does not exist.
Result: `read_one` returns None → `hydrate_demo_slot` (trading_gateway.py:88-116) logs nothing useful and **demo_slot stays None on every restart** → GAP-5 (faa1056/e72f7f7 intent) is inert.

## Impact
- **Today (07-02): none** — verified 0 open demo trades in PG at boot → slot=None is the correct state anyway.
- **Future intraday restart with an open demo trade: orphaned position** — exactly the failure GAP-5 was built to close (I-38/D35 class). Fix before relying on warm-start.

## Fix (smallest correct change)
1. In `backend/v9/gateway/trading_gateway.py:98-103` replace `system_id` with `firing_system` (keep alias if the dict key is consumed as `system_id` downstream — check `self.demo_slot` consumers first, per audit-before-build).
2. **Regression test (anti-tautological):** the existing tests passed while the query was broken — they must not mock the schema. Add a test that runs the actual hydration SQL against the real model/DB schema (e.g. create the ORM table in a scratch PG/SQLite from the model and execute the exact query, or assert every selected column ∈ model columns). It must FAIL on `system_id` and PASS on `firing_system`.
3. Boot-visibility: the failure was a silent `logger.warning` inside db.read only. Add the gateway-level warning path so a failed hydration logs `[Gateway] demo_slot hydration failed` explicitly (it currently returns None as "no open trade" — a lie per Rule 1). Distinguish "query errored" from "no rows".

## Related (separate commit, non-blocking, Michael sign-off for scope)
Known SQLite residuals still running against the dead `data/mems26_local.db` (CLAUDE.md §DB residual):
- `[Main] Startup hydration inventory` block (main.py:787-830) — fails "malformed" every boot; port to PG via `db.read` or delete.
- `[tpo_snapshotter] ... db=.../mems26_local.db` + HistoricalReplay `db_path` (main.py:834) — decide: port to PG or retire. If tpo_snapshotter feeds `v9_tpo_sessions_archive` (Y-IB), the archive has NOT been accumulating since the PG migration — verify row counts and report.

## Verification (paste raw output)
1. `pytest` the new regression test — paste FAIL-on-old/PASS-on-new proof.
2. After next restart: paste the boot log line `[Gateway] hydrated demo_slot ...` or `no open demo trade in DB — demo_slot=None (free)` (must appear; no `[db.read] read_one failed`).
3. Four UAT axes not applicable (no endpoint); Rule 5 applies to the boot-line proof.

## NOT-DONE (fill honestly)
- [ ] anything above not completed, with reason
