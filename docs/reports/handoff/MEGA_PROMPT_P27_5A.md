**Status:** ready-to-execute prompt for Claude Code
**Last updated:** 2026-05-16
**Author:** Cursor handoff (prompt-only; do **not** treat as a decision document)
**Companion docs:** [`NEXT_CHAT_PROMPT.md`](./NEXT_CHAT_PROMPT.md) · [`PROMPT_LIST_TO_LIVE.md`](./PROMPT_LIST_TO_LIVE.md) · [`GANTT_TO_LIVE.md`](./GANTT_TO_LIVE.md) · [`SESSION_LOG_2026-05-16.md`](./SESSION_LOG_2026-05-16.md)

# MEGA PROMPT — P27.5a (Backend bad-bar fix in `/api/v9/chart/bars5min`)

> Paste the block below verbatim into a fresh Claude Code session. It is self-contained.

---

## ╭──────────────── PASTE FROM HERE ────────────────╮

You are Claude Code working on the **MEMS26** autonomous trading system at `/Users/michael/Downloads/mems26_web_git`. Today's task is **P27.5a — Backend bad-bar fix in `/api/v9/chart/bars5min`**, the first of three pipeline-integrity prompts (P27.5a → P27.5b → P27.5c) that gate SHADOW activation. Branch: `stabilize/mems26-local-truth-2026-05-16` (HEAD = `419f4cc`).

Before you touch anything, read these in order:

1. `docs/reports/handoff/NEXT_CHAT_PROMPT.md` (project context, hard rules, three blocking bugs)
2. `docs/reports/handoff/SESSION_LOG_2026-05-16.md` (what was done 2026-05-16 and why)
3. `docs/reports/handoff/PROMPT_LIST_TO_LIVE.md` (P27.5a spec)
4. `MEMS26_REGISTRY.yaml` → `REQ-W5.4` (UPSERT contract already declared IMPLEMENTED)
5. `docs/reports/SYSTEM_COMPLETION_CONTROL_BOARD.md` (pre-SHADOW blocker list)

### Hard rules (do not break, regardless of reasoning)

1. **No SHADOW / DEMO / LIVE activation.** Do not flip `MEMS26_MODE`, do not set any per-system `enable_shadow=true`, do not write to `trade_command.json`.
2. **Backend-only scope.** Do **not** modify `bridge/`, the DLL, or any frontend code. The frontend `looksOk` filter in `frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx` **must remain in place** as defense-in-depth (it will simply log 0 filtered rows once the backend is clean).
3. **Do not regress D-074** (5-min Woodies migration); leave `v9_bars_5min_woodies` paths alone.
4. **`lightweight-charts` is the approved chart library** (not the TradingView widget). Do not propose alternatives.
5. **Resource caps stay in place**: `ulimit -n 10240`, `V9_DISABLE_WATCHDOG=1`, `WATCHPACK_POLLING=true`, `CHOKIDAR_USEPOLLING=true`, `CHOKIDAR_INTERVAL=1000`, `next dev -H 127.0.0.1`, `turbopack.root=cwd`.
6. **No new D-### decisions.** This work is a *completion* of the already-IMPLEMENTED `REQ-W5.4`, not a new architectural choice.
7. **No commit, no push** until UAT is green and Michael gives explicit go in chat. Stage all changes, run the report, then summarize and stop.
8. **No subagent fan-out for trivial steps.** One focused worker, sequential commits.

### Concrete evidence you can trust (already gathered)

A read-only investigation against the live DB and `/api/v9/chart/bars5min?limit=120` produced these facts. Re-verify them before patching; do not assume they are still true if the DB has been touched in the meantime.

**Three confirmed bad rows in `v9_bars_5min`:**

```text
id=1197 ts=2026-05-16 05:05:00.000000  O=7462.25 H=7463.00 L=7180.25 C=7180.25 V=890,003       created_at=2026-05-16 09:10:01
id=1207 ts=2026-05-16 09:05:00.000000  O=7430.75 H=7463.00 L=7172.50 C=7461.00 V=55,871,343    created_at=2026-05-16 09:11:33
id=1208 ts=2026-05-16 09:10:00.000000  O=7264.75 H=7462.75 L=7172.50 C=7460.00 V=40,580,682    created_at=2026-05-16 09:11:35
```

Neighbors (`ts = 08:55–09:30`) all have `low ≈ 7405.75`, `high ≈ 7463–7473`, so the 290-pt downwicks are not real market action. Per-bar OHLC ordering (`low ≤ open,close ≤ high`) is preserved — the violation is structural, not arithmetic.

**Architectural defects you must fix:**

1. **`POST /api/v9/bars/5min` in `backend/v9/api/v9/bars.py` (lines 195–225)** does `db.add(row)` per incoming bar. **No validation, no UPSERT, no dedupe.** This is the path the bridge actually uses.
2. **`backend/v9/services/bar_ingestion.py::ingest_bar()`** already implements Python-level UPSERT on `(ts, symbol)` per `REQ-W5.4` — but it is **only called by the in-process aggregator**, never by the HTTP push path. So the bridge bypasses it.
3. **Schema (`backend/v9/db/models/bars_5min.py`)** has only a non-unique index on `ts`. No `UNIQUE (ts, symbol)` constraint exists in the live SQLite DB (`data/mems26_local.db`). The Python-level UPSERT is therefore race-prone and not enforced.
4. **`GET /api/v9/chart/bars5min` in `backend/v9/api/v9/bars_5min_history.py`** reflects raw DB rows with no integrity gate.

**Source of truth for the integrity heuristic** (mirror the frontend exactly):

```ts
// frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx, function looksOk(b)
function looksOk(b: any): boolean {
  const o = b.open ?? b.o, h = b.high ?? b.h, l = b.low ?? b.l, c = b.close ?? b.c;
  if (o == null || h == null || l == null || c == null) return false;
  if (o <= 0 || h <= 0 || l <= 0 || c <= 0) return false;
  if (l > h) return false;
  const body = Math.min(o, c);
  if (body > 0 && (body - l) / body > 0.02) return false;       // low wick > 2% of body → bad
  const bodyTop = Math.max(o, c);
  if (bodyTop > 0 && (h - bodyTop) / bodyTop > 0.02) return false; // high wick > 2% of body → bad
  return true;
}
```

The Python equivalent **must use the identical heuristic** so client and server agree on what "good" means.

### Goal (verbatim from `PROMPT_LIST_TO_LIVE.md`)

Eliminate outlier rows returned by `/api/v9/chart/bars5min` (observed: bars with `low≈7172.5`/`7180.25` while surrounding window is `~7440–7476`, a ~300-point cliff). Client-side `looksOk` filter must become defense-in-depth, not the source of truth.

### Deliverables

1. **Source changes** (backend-only, surgical):
   - `backend/v9/api/v9/bars.py` — refactor `post_bars_5min` to delegate to `bar_ingestion_service.ingest_bar()` plus a new `_bar_is_valid()` gate. Reject invalid bars with HTTP 422 carrying `{ "rejected": [...], "accepted": N }` and a structured log line `[bars_5min] REJECTED ts=... reason=...`. Keep the existing `_dispatch` / `_record_push` / `_route_bar` side effects on accepted bars only.
   - `backend/v9/services/bar_ingestion.py` — add the same `_bar_is_valid()` gate at the top of `ingest_bar()` (defense in depth for the aggregator path). Add a `bars_rejected` counter alongside `_bars_ingested`. Expose both via `bars_in_db` peer properties (e.g., `bars_rejected_total`).
   - `backend/v9/db/models/bars_5min.py` — declare `UniqueConstraint("ts", "symbol", name="uq_v9_bars_5min_ts_symbol")` on the model.
   - `backend/v9/api/v9/bars_5min_history.py` — apply `_bar_is_valid()` in `_fetch_bars_5min` as a final filter; log filtered count per request. Expose the same helper from a small shared module (e.g., `backend/v9/services/bar_integrity.py`) so the validator is defined in **one place** and imported by ingestion + history + tests.

2. **Database migration**:
   - New `schema/v9_migrations/V9_010_bars_5min_unique.sql` (PostgreSQL grammar to match the existing migration style):
     ```sql
     -- V9_010: enforce per-bar uniqueness on v9_bars_5min (REQ-W5.4 completion)
     -- Idempotent. Safe to run on a DB that already has the constraint.
     CREATE UNIQUE INDEX IF NOT EXISTS uq_v9_bars_5min_ts_symbol
         ON v9_bars_5min (ts, symbol);
     ```
   - New `scripts/db/p275a_apply_migration.sh` — applies the migration to the live SQLite at `data/mems26_local.db` using SQLite-compatible DDL (translate `IF NOT EXISTS` accordingly), after taking a backup to `data/backups/mems26_local.db.YYYYMMDD-HHMMSS.bak`.
   - New `scripts/db/p275a_cleanup_bad_bars.sql` — explicitly lists the three ids (1197, 1207, 1208) plus a defensive sweep:
     ```sql
     -- Backup first (handled by p275a_apply_migration.sh)
     DELETE FROM v9_bars_5min WHERE id IN (1197, 1207, 1208);
     -- Defensive sweep: any row violating the body-cliff rule
     DELETE FROM v9_bars_5min
      WHERE (CASE WHEN MIN(open, close) > 0 THEN (MIN(open, close) - low) / MIN(open, close) END) > 0.02
         OR (CASE WHEN MAX(open, close) > 0 THEN (high - MAX(open, close)) / MAX(open, close) END) > 0.02
         OR low > high OR low <= 0 OR high <= 0 OR open <= 0 OR close <= 0;
     ```
     If the defensive sweep would remove **more than 10 rows**, abort and produce a report instead of deleting — print the candidate set so a human can review.

3. **Tests** — `tests/v9/api/test_chart_bars5min_integrity.py` (new), failing-first then green:
   - `test_post_rejects_body_cliff_bar` — POST a bar with `low=7172.5, open=7430.75, close=7461.0` returns 422 and DB row count is unchanged.
   - `test_post_rejects_invalid_ohlc_ordering` — POST a bar with `low > high` returns 422.
   - `test_post_accepts_normal_bar` — POST a valid bar returns 200 and DB row appears exactly once.
   - `test_post_upsert_same_ts_updates_instead_of_appending` — POST the same `(ts, symbol)` twice with different OHLC; expect 1 row whose values match the second POST.
   - `test_get_filters_legacy_bad_rows` — Seed DB with a body-cliff row directly via SQL (bypass POST), call `GET /api/v9/chart/bars5min`, expect the row absent from the response and a log line counting it as filtered.
   - `test_unique_constraint_on_ts_symbol` — Attempt to insert two rows with same `(ts, symbol)` via raw SQL; expect `IntegrityError`.
   - All tests use the existing `tests/v9/conftest.py` `BRIDGE_TOKEN` setup and the existing DB fixture pattern; do not create a new conftest.

4. **Report** — `docs/reports/PROMPT_27_5A_BAD_BAR_FIX.md` with:
   - Root cause (the two ingestion paths + missing UNIQUE) explained with file/line refs
   - Diff summary (`git diff --stat HEAD`) at end of work
   - Before payload (the three bad rows from the bad-bar trio above) and after payload (same `ts` window returning clean bars)
   - Test output (`pytest tests/v9/api/test_chart_bars5min_integrity.py -v`)
   - SCB ticket update note: "P27.5a closes pre-SHADOW blocker #1" (do **not** flip SHADOW status; just record)
   - Cross-link to `MEMS26_REGISTRY.yaml::REQ-W5.4` saying this prompt **completes** the previously-declared UPSERT contract (no new D-### needed; reasoning: the registry says "UPSERT on (ts,symbol)" was implemented; this prompt enforces it at the schema layer and on the HTTP push path that was bypassing it).

### Pre-flight

```bash
cd /Users/michael/Downloads/mems26_web_git

# 1) Confirm the world looks like the handoff expected
git status -sb
git rev-parse HEAD                                      # expect 419f4cc
bash scripts/check_status.sh                            # bridge/frontend may be down — that's ok for the fix work; backend must be up for endpoint verification at the end

# 2) Stash the prior session's intentional hardening so P27.5a lands on a clean tree
git stash push -u -m "pre-P27.5a: 2026-05-16 frontend + scripts hardening (carry-forward)" \
  -- frontend/v9/next.config.ts \
     frontend/v9/package.json \
     frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx \
     frontend/v9/src/v9/components/layout/V9Dashboard.tsx \
     scripts/start_all.sh \
     bridge/v9_streams/__pycache__/__init__.cpython-39.pyc \
     bridge/v9_streams/__pycache__/base_stream.cpython-39.pyc
git status -sb                                          # only handoff/ untracked should remain

# 3) Snapshot DB before any write
mkdir -p data/backups
cp data/mems26_local.db "data/backups/mems26_local.db.$(date +%Y%m%d-%H%M%S).pre-P27.5a.bak"
ls -lh data/backups/
```

### Execution order (do not reorder)

1. Add `backend/v9/services/bar_integrity.py` with the single `bar_is_valid()` helper (Python mirror of frontend `looksOk`). Unit-test it directly under `tests/v9/services/test_bar_integrity.py` — pure-function tests, no DB.
2. Add `UniqueConstraint` to `V9Bar5Min` model. Write `schema/v9_migrations/V9_010_bars_5min_unique.sql` + `scripts/db/p275a_apply_migration.sh`. Apply migration to the live DB.
3. Wire `bar_integrity.bar_is_valid()` into `bar_ingestion_service.ingest_bar()`. Add `bars_rejected` counter.
4. Refactor `post_bars_5min` in `backend/v9/api/v9/bars.py` to: (a) validate each incoming bar with `bar_integrity.bar_is_valid()`, (b) for valid bars, call `bar_ingestion_service.ingest_bar()`, (c) return `{ "ok": True, "inserted": N, "rejected": [list of {ts,reason}] }` and HTTP 422 when **all** input bars were rejected (otherwise 200 with partial accept; log the rejections). Preserve `_dispatch` / `_record_push` / `_route_bar` only for accepted bars.
5. Add `bar_integrity.bar_is_valid()` as a final filter in `_fetch_bars_5min` (`backend/v9/api/v9/bars_5min_history.py`). Log `[bars5min] filtered=N` per request when N>0.
6. Write `tests/v9/api/test_chart_bars5min_integrity.py`. Run it — expect failures at step 6, fixes in steps 1–5 should already pass. Do **not** edit tests to make them pass; if a test fails for the wrong reason, fix the production code.
7. Apply the cleanup SQL: `sqlite3 data/mems26_local.db < scripts/db/p275a_cleanup_bad_bars.sql`. Verify row deletion count = 3 (or stop and report if defensive sweep would exceed 10).
8. Restart backend (`screen -S mems26_backend -X quit ; bash scripts/start_all.sh` per the canonical hardened script) and re-probe (see Verification below).
9. Write `docs/reports/PROMPT_27_5A_BAD_BAR_FIX.md`. Append a "DONE" marker to the P27.5a entry in `docs/reports/handoff/PROMPT_LIST_TO_LIVE.md` and the matching row in `docs/reports/handoff/GANTT_TO_LIVE.md` Phase 0 block.
10. `git stash pop` to restore the carry-forward frontend/scripts hardening. Verify `git status` shows your P27.5a edits **plus** the prior hardening, with no surprise files.
11. **STOP.** Do not commit. Do not push. Print the proposed commit message and ask Michael for go.

### Acceptance criteria (every one must be GREEN before stop)

- [ ] `curl -s "http://127.0.0.1:8000/api/v9/chart/bars5min?limit=600"` returns **zero** rows where `(min(o,c) - low) / min(o,c) > 0.02` or `(high - max(o,c)) / max(o,c) > 0.02` or `low > high` or any OHLC ≤ 0.
- [ ] Re-POST of an existing `(ts, symbol)` with new OHLC updates in place (row count unchanged; values match latest POST).
- [ ] POSTing the original bad-bar trio (the three rows above) returns 422 for each, with the rejection reason logged structurally.
- [ ] `pytest tests/v9/api/test_chart_bars5min_integrity.py tests/v9/services/test_bar_integrity.py -v` is green.
- [ ] `pytest tests/v9/compliance/v1_generated/test_system5_v1.py` is green (S5 regression check; TPO must not depend on rows we just deleted — if it does, stop and report; do **not** patch S5 in this prompt).
- [ ] `bash scripts/check_status.sh` shows backend `[OK]`.
- [ ] The frontend `ChartV5b.tsx` `looksOk` filter still exists unchanged. (Read the file; do not edit it; just confirm.)
- [ ] `docs/reports/PROMPT_27_5A_BAD_BAR_FIX.md` exists and includes before/after payload + diff stat + test output.
- [ ] `docs/reports/handoff/PROMPT_LIST_TO_LIVE.md` P27.5a entry has `**Status:** DONE (commit-pending, report `docs/reports/PROMPT_27_5A_BAD_BAR_FIX.md`)` once Michael confirms the commit.
- [ ] `docs/reports/handoff/GANTT_TO_LIVE.md` Phase 0 row shows `IN PROGRESS → P27.5a DONE` and the mermaid block adds the actual completion span.

### Verification commands (safe, read-only — run after step 8)

```bash
cd /Users/michael/Downloads/mems26_web_git

curl -s http://127.0.0.1:8000/api/v9/health | jq .
curl -s "http://127.0.0.1:8000/api/v9/chart/bars5min?limit=600" > /tmp/p275a_after.json
python3 -c "
import json
b = json.load(open('/tmp/p275a_after.json'))
print('rows:', len(b))
bad = [r for r in b if r['low'] > r['high'] or
       r['open'] <= 0 or r['high'] <= 0 or r['low'] <= 0 or r['close'] <= 0 or
       (min(r['open'], r['close']) > 0 and (min(r['open'], r['close']) - r['low']) / min(r['open'], r['close']) > 0.02) or
       (max(r['open'], r['close']) > 0 and (r['high'] - max(r['open'], r['close'])) / max(r['open'], r['close']) > 0.02)]
print('bad after fix:', len(bad))
assert len(bad) == 0, bad[:3]
print('OK: clean.')
"
```

### Rollback plan (if anything goes wrong)

1. Restore DB: `cp data/backups/mems26_local.db.<ts>.pre-P27.5a.bak data/mems26_local.db && screen -S mems26_backend -X quit && bash scripts/start_all.sh`.
2. Revert code: `git checkout backend/v9/api/v9/bars.py backend/v9/api/v9/bars_5min_history.py backend/v9/services/bar_ingestion.py backend/v9/db/models/bars_5min.py`. Delete added files: `rm backend/v9/services/bar_integrity.py tests/v9/api/test_chart_bars5min_integrity.py tests/v9/services/test_bar_integrity.py schema/v9_migrations/V9_010_bars_5min_unique.sql scripts/db/p275a_apply_migration.sh scripts/db/p275a_cleanup_bad_bars.sql docs/reports/PROMPT_27_5A_BAD_BAR_FIX.md`.
3. `git stash pop` to restore the prior hardening.
4. Confirm `git status` matches the pre-P27.5a state in `SESSION_LOG_2026-05-16.md` "Files touched" table.
5. Report the failure mode in `docs/reports/handoff/SESSION_LOG_2026-05-16.md` under a new "P27.5a abort" section so the next session has the trail.

### Definition of DONE

You may declare DONE only when:

- All "Acceptance criteria" checkboxes above are green.
- `docs/reports/PROMPT_27_5A_BAD_BAR_FIX.md` is written and self-consistent.
- You have **printed the proposed commit message** and stopped, waiting for Michael's `go` to commit. **Do not commit on your own.**

Proposed commit message format:

```
fix(p27.5a): enforce v9_bars_5min integrity (UPSERT + UNIQUE + cliff validator)

- Route POST /api/v9/bars/5min through bar_ingestion_service (REQ-W5.4)
- Add bar_integrity.bar_is_valid() mirroring frontend looksOk (2% body-cliff)
- Reject invalid bars at insert (HTTP 422) and filter at query (defense in depth)
- Add UNIQUE (ts, symbol) on v9_bars_5min via V9_010 migration
- Cleanup 3 known bad rows (ids 1197, 1207, 1208) after DB backup
- Tests: tests/v9/api/test_chart_bars5min_integrity.py + tests/v9/services/test_bar_integrity.py
- Report: docs/reports/PROMPT_27_5A_BAD_BAR_FIX.md
- No DLL / bridge / frontend changes
```

If you have any ambiguity, **stop and ask Michael in chat**. Do not improvise.

## ╰──────────────── PASTE TO HERE ────────────────╯

---

## Why this prompt is safe to paste as-is (Cursor-side notes, do not include when sending)

- All hard rules from `NEXT_CHAT_PROMPT.md` are restated verbatim.
- The bad-bar trio is named explicitly so CC can verify the exact reproduction.
- The validator is defined in **one shared module** (`bar_integrity.py`) so client and server stay in sync.
- The schema migration completes REQ-W5.4 (already IMPLEMENTED per registry) rather than introducing a new D-### decision.
- Defensive sweep is bounded (>10 rows → abort + report) to prevent silent data loss.
- DB backup is mandatory before any DELETE.
- Frontend `looksOk` filter is explicitly preserved.
- CC must stop before committing; Michael holds the final go.
- Rollback plan restores both the DB and code, and re-pops the carry-forward stash.

*If P27.5a lands cleanly, the next mega prompt to draft is P27.5b (live-price freshness fix). It is **not** included here — keep prompts surgical, one at a time.*
