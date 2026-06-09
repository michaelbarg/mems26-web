# CC AUDIT PROMPT — Daily Reset, Archive, Demo Readiness

**Date:** 2026-05-29
**Mode:** 🔴 AUDIT-ONLY · NO CODE CHANGES · NO MIGRATIONS · NO COMMITS
**Output:** `docs/reports/CC_AUDIT_DAILY_RESET_2026-05-29.md` (single file)
**Reference:** `docs/plans/DAILY_RESET_AND_ARCHIVE_DESIGN.md` (read first)
**Estimated work:** 90–120 minutes

---

## §0 · TL;DR for CC

Cursor designed a 5-phase plan to fix the "yesterday's day_type lingering
into pre-RTH today" bug + add archive + add demo-readiness panel. **Before
ANY implementation**, Michael wants you to audit the codebase against the
design and produce a consultation report.

The report Cursor needs from you tells us:
1. Is what the design assumes about the codebase actually true?
2. What changed since the design was written (if anything)?
3. What surfaces does the design fail to cover?
4. What's the *minimum correct* path to fix the root cause (not the
   symptom)?

Michael's exact words (translated):
> "I want to solve the root, not patch symptoms. Before changing anything,
> tell me what's there. After your audit, we'll decide together what to
> fix and what to keep."

You will be told later, in a separate prompt, what to implement. **This
prompt asks for nothing else but the report.**

---

## §1 · What this prompt is NOT

- ❌ Not implementation. **Zero code edits.**
- ❌ Not migrations. **Do not run `sqlite3 ... < migration.sql`.**
- ❌ Not commits. **`git status` should show no changes when you finish.**
- ❌ Not "while I'm here" tweaks. If you spot a bug in passing, write it
  in §6 of the report — do not fix it.
- ❌ Not the design doc. The design lives in
  `docs/plans/DAILY_RESET_AND_ARCHIVE_DESIGN.md` — your job is to
  audit it, not rewrite it.
- ❌ Not the V3 constitution. Do not touch
  `docs/spec_authority/MEMS26_CONSTITUTION_V3_FINAL.txt`,
  `CLAUDE.md`, `.cursor/rules/*`, or `frontend/v9/`. Audit-only.

---

## §2 · The 8 questions you must answer

Each question requires **raw command output pasted verbatim** in the
report. No paraphrasing, no "should be", no "appears to". Output or it
didn't happen (CLAUDE.md Rule 5).

### §2.1 — TZ-naive datetime audit (Bug B blast radius)

Run:
```bash
rg "date\.today\(\)|datetime\.now\(\s*\)" backend/v9 -n
```

For each match, classify in a table:

| File:line | Snippet | TZ used by Python at this line | Used in | Risk |
|-----------|---------|--------------------------------|---------|------|
| `backend/v9/api/v9/day_type_v9_routes.py:30` | `date.today().isoformat()` | machine TZ (Israel) | `WHERE date = ?` | 🔴 22:00 ET writes wrong row for "tomorrow" |
| ... | ... | ... | ... | ... |

For each 🔴 entry, propose the **smallest correct fix** (not "introduce a
helper module" — name the exact replacement, e.g.
`datetime.now(ZoneInfo("America/New_York")).date()`).

### §2.2 — Bug A root-cause hunt (THE critical question)

A row was written to `v9_day_type_history` with `date='2026-05-29'` at
**`last_updated_at = 2026-05-29 05:00:03 IL` (= 22:00 ET 28/5)**, before
the trading day even started. The `DayTypeConsumer._extract_session_date`
already converts to ET. So a different call-path is responsible.

Find it. Required:
1. `rg "v9_day_type_history|DayTypeHistory" backend/v9 -n` — paste output.
2. `rg "session.add\\(V9DayTypeHistory|session.merge.*V9DayTypeHistory|UPDATE v9_day_type_history|INSERT.*v9_day_type_history" backend/v9 -n` — paste output.
3. For every writer found, trace upward: who calls it? With what
   `timestamp` value? Paste 10 lines of context per call site.
4. Specifically identify the path that fired around `22:00 ET` on
   2026-05-28. Likely candidates:
   - `state_machine.to_classification()` invoked by a recurrent loop
   - `hydration.py` rebuilding history at startup or interval
   - `DayTypeConsumer.consume()` called with a non-ET timestamp
   - A test/fixture leaking into prod path
5. Write the verdict in **one paragraph**: "The 29/5 row was written by
   `<file>:<line>` because `<reason>`. Smallest fix: `<exact change>`."

If you **cannot** identify the call-path with confidence, say so plainly
("inconclusive after 30 minutes — recommend X further investigation").
Do NOT guess.

### §2.3 — Existing `/current` endpoint inventory

For each of the 4 endpoints below, paste the current source + describe
its TZ behavior + describe what it returns when no row exists for "today":

```bash
rg -A 30 "def get_current|@router.get.*current" backend/v9/api/v9/day_type_v9_routes.py
rg -A 30 "def get_key_levels|@router.get.*key_levels" backend/v9/api/v9/key_levels_routes.py
rg -A 30 "def.*tpo.*current" backend/v9/api/v9/tpo_routes.py
rg -A 30 "def.*woodies.*current" backend/v9/api/v9/woodies_chart_routes.py
```

Build this table:

| Endpoint | Source file | TZ for "today" | No-row behavior | Returns yesterday? |
|---|---|---|---|---|
| `/api/v9/day_type/v9/current` | day_type_v9_routes.py | machine | `{classified: false, data: null}` | No (good) |
| `/api/v9/key_levels` | key_levels_routes.py | ? | ? | ? |
| `/api/v9/tpo/current` | tpo_routes.py | ? | ? | ? |
| `/api/v9/woodies/current` | woodies_chart_routes.py | ? | ? | ? |

Mark each row 🟢 / 🟡 / 🔴 based on whether it correctly handles pre-RTH.

### §2.4 — Schema audit for migration 019

Paste output of:
```bash
sqlite3 data/mems26_local.db "PRAGMA table_info(v9_bars_5min);"
sqlite3 data/mems26_local.db "PRAGMA table_info(v9_woodies_signals);"
sqlite3 data/mems26_local.db "PRAGMA table_info(v9_trades);"
sqlite3 data/mems26_local.db "PRAGMA table_info(v9_audit_events);"
sqlite3 data/mems26_local.db "PRAGMA table_info(v9_five_min_setups);"
sqlite3 data/mems26_local.db "PRAGMA table_info(v9_day_type_history);"
sqlite3 data/mems26_local.db "PRAGMA table_info(v9_account_status);"
sqlite3 data/mems26_local.db "PRAGMA index_list(v9_day_type_history);"
ls backend/v9/db/migrations/versions/ | sort | tail -5
```

For each of the 5 tables that need `is_synthetic` (per design §11):
- Confirm `id INTEGER PRIMARY KEY` exists (else `ALTER ADD` is unsafe)
- Confirm no existing column named `is_synthetic`
- Confirm no UNIQUE constraint that would conflict
- Estimate ROW count via `SELECT COUNT(*) FROM <t>`

For `v9_day_type_history`:
- Does the existing `status` column have a `CHECK constraint`? If yes,
  paste the constraint definition.
- Will adding new enum values (`DEVELOPING`, `ROLLED_OVER`) break the check?

For `v9_account_status`:
- Current row count
- Schema (the design assumes a `mode` column exists)
- If `mode` doesn't exist, propose where it should live

### §2.5 — Existing rollover / scheduled-task surface

Paste output of:
```bash
launchctl list | grep -i "mems26\|day_type\|rollover\|reset"
crontab -l 2>/dev/null
ls ~/Library/LaunchAgents/ | grep -i mems26
rg "session.boundary|rollover|daily_reset|@app.on_event" backend/v9 -n
rg "asyncio.create_task|asyncio.sleep" backend/v9/main.py backend/v9/app.py -n
```

Verdict: is anything currently doing daily reset? If yes, describe it +
why we can or cannot reuse it. If no, confirm the design's `Phase 2.2
SessionBoundaryManager` is greenfield work.

### §2.6 — `is_synthetic` flag impact survey

For each of these 5 tables, find every `SELECT` (not `INSERT`):
```bash
rg "FROM v9_bars_5min|FROM v9_woodies_signals|FROM v9_trades|FROM v9_audit_events|FROM v9_five_min_setups" backend/v9 frontend/v9/src -n
```

Count by file. Build:

| Table | Total queries | Files affected | Hardest update |
|---|---|---|---|
| `v9_bars_5min` | NN | 7 | `path/to/file.py` (joined query, multiple WHERE) |
| ... | ... | ... | ... |

Mark each query 🟢 (trivial — single WHERE add) / 🟡 (medium — needs
test) / 🔴 (hard — joins, dynamic SQL).

### §2.7 — Compliance manifest enum check

```bash
rg "PENDING|LOCKED|LOCKED_LOW_CONF|DEVELOPING|ROLLED_OVER" backend/v9/systems/day_type/compliance_manifest.yaml
rg "compliance_manifest" backend/v9 -n
rg "lifecycle_phase|lifecycle_status" backend/v9 -n
```

Question to answer: if migration 019 adds new enum values
(`DEVELOPING`, `ROLLED_OVER`), what test enforces the manifest still
validates them? Is there a validator function we'd need to update?

### §2.8 — Open trades at rollover boundary

```bash
sqlite3 data/mems26_local.db "SELECT id, state, entry_ts, mode, direction FROM v9_trades WHERE state IN ('OPEN', 'ARMED', 'PENDING') ORDER BY entry_ts DESC LIMIT 20;"
rg "TIME_STOP|time_stop_minutes" backend/v9/systems/woodies -n
```

For each open trade, compute: at the next 18:00 ET boundary, what
happens?
- Will W-10 close it before then? (90 min from entry = ?)
- Does any code currently force-close at 16:00 ET?
- Does any code reference `account.mode` to refuse new positions?

This is the rare-case Michael wanted documented.

---

## §3 · STOP conditions (pause + ask Michael, do NOT proceed)

If any of these occur, write the report up to that point, save it, and
**stop**:

- §2.5 returns any LaunchAgent / cron beyond `com.mems26.bridge`
- §2.4 finds a `CHECK constraint` on `v9_day_type_history.status`
  (means new enum values would fail validation)
- §2.4 finds any of the 5 tables missing `id INTEGER PRIMARY KEY`
- §2.2 git-blame is inconclusive after 30 minutes
- You catch yourself wanting to "fix it real quick" — STOP. Audit only.

When you stop, the report's last line says:
```
STOPPED at §X.Y because: <reason>. Awaiting Michael / Cursor decision
before continuing.
```

---

## §4 · Required report format

`docs/reports/CC_AUDIT_DAILY_RESET_2026-05-29.md`:

```markdown
# CC Audit — Daily Reset / Archive / Demo Readiness
**Date:** 2026-05-29 HH:MM IL
**Branch:** <git rev-parse --abbrev-ref HEAD>
**HEAD:** <git rev-parse --short HEAD>
**Reference:** docs/plans/DAILY_RESET_AND_ARCHIVE_DESIGN.md

## §1 · TZ-naive datetime audit (answers §2.1)
[table + raw rg output]

## §2 · Bug A root-cause (answers §2.2)
[evidence + verdict in one paragraph]

## §3 · /current endpoint inventory (answers §2.3)
[table + per-endpoint analysis]

## §4 · Schema audit (answers §2.4)
[raw PRAGMA output + analysis]

## §5 · Existing rollover surface (answers §2.5)
[raw output + verdict]

## §6 · is_synthetic impact (answers §2.6)
[table + per-table count]

## §7 · Compliance manifest enum (answers §2.7)
[raw output + verdict]

## §8 · Open trades at boundary (answers §2.8)
[raw SQL + per-trade timeline]

## §9 · Findings beyond design scope
Anything you noticed that is NOT in the design doc but should be in
Phase 2. Examples:
- Hidden cache that holds yesterday's day_type
- A code path that calls /current and assumes never-null
- A missing test that should exist

## §10 · STOP conditions hit
List of any §3 conditions that triggered + which sub-task you stopped
at.

## §11 · Recommended fix priority (root → symptom)

Build a small ordered list:
1. <fix> — addresses <root> — without this, <symptom> recurs
2. <fix> — depends on #1
3. ...

## §12 · Acknowledgement

I read:
- [x] CLAUDE.md
- [x] .cursor/rules/mems26-pre-live-protocol.mdc
- [x] docs/plans/DAILY_RESET_AND_ARCHIVE_DESIGN.md (whole file, 749 lines)
- [x] This prompt

I confirm:
- [x] Zero file edits made during this audit
- [x] git status shows no changes
- [x] I did NOT touch V3, CLAUDE.md, .cursor/rules, frontend, bridge, sc_study
- [x] I did NOT run any migration / DDL
- [x] I cited every claim with raw command output (no "should be" / "appears to")
```

---

## §5 · Cite-by-symbol rule (line numbers drift fast)

Do not cite line numbers in the report. Cite by symbol:

❌ Wrong: "the bug is at `consumer.py:138`"
✅ Right: "the bug is in `DayTypeConsumer._extract_session_date()` in `backend/v9/systems/day_type/consumer.py`"

If a snippet must show line context, paste 5 lines around the symbol +
include the symbol name in the prose.

---

## §6 · Verification loop (what happens after your report)

1. You finish the report and stop.
2. Cursor reads it, validates each claim against the codebase.
3. Cursor cross-references your findings with `DAILY_RESET_AND_ARCHIVE_DESIGN.md`
   §7 (blast radius) — updates the design if you found gaps.
4. Cursor asks Michael: "design holds / design needs revision X / design
   is wrong about Y".
5. After Michael's go-ahead, Cursor writes a **separate** prompt for you:
   `CC_IMPLEMENT_PROMPT_DAILY_RESET_PHASE2_2026-05-29.md` — that's when
   code changes happen.

You will not implement Phase 2 from this prompt. Don't try.

---

## §7 · One-paragraph self-summary

Before submitting the report, write a 3–5 line self-summary at the top.
Example:
> Audited 8 questions. Bug A traced to `state_machine.to_classification()`
> being invoked by an overnight hydration loop with timestamp from
> `datetime.now(tz=UTC)` — which converts correctly to ET, but the
> consumer's UPSERT-keyed-on-date logic doesn't refuse "future" dates.
> 13 occurrences of TZ-naive datetime found, 4 are in production
> hot-paths. is_synthetic flag is safely addable to all 5 tables.
> No existing rollover code. STOP conditions: none hit.

This summary lets Cursor understand the audit in 30 seconds.

---

## §8 · Time budget + escape valve

If you hit 2 hours of audit work and §2.2 is still inconclusive: write
what you have, mark §2.2 as "inconclusive after 2h", and stop. Cursor
+ Michael will pick up the trace.

If you finish in 60 minutes: still pause, re-read the report once for
contradiction, and submit. Don't pad.

---

## §9 · Acknowledgement template (paste at top of your report)

Reply with this exact template before starting:

```
ACK — CC AUDIT PROMPT 2026-05-29

- I will create only docs/reports/CC_AUDIT_DAILY_RESET_2026-05-29.md
- I will not edit any other file
- I will not run migrations / DDL / git commits
- I will paste raw output for every claim
- I will stop at any §3 STOP condition
- Estimated time: <NN> minutes

Starting now.
```
