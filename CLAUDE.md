# MEMS26 Agent Guardrails

This repository controls the local MEMS26 trading stack. Treat post-reboot
stability settings as production safety controls.

## Sierra real-time data (**DONE** — Michael 2026-05-20)

Sierra DLL + time-axis fixes are **already shipped** (see inbox §2). §7a is
**anti-regression**: do not change `sc_study/`, bridge, or market-data routes
without reading `docs/handoff/P30_AGENT_INBOX_PRE_LIVE.md` §7a and verifying
live exports under `~/SierraChart_Data/v9_export/`.

**Source of truth:** live values come from **Sierra Chart exports**, through
the bridge into the API/DB — not from backend or frontend synthesizing OHLC,
TPO, CVD, or Woodies study fields. Allowed: normalize, dedup, display TZ,
trading logic on ingested bars. Forbidden without explicit approval: inventing
`proj_*`, synthetic time grids, or rolling-window price levels when the DLL
omits them.

## Pre-LIVE Discipline (mandatory)

We are heading to LIVE futures trading. Apply minimum-mistakes discipline:

- **Diagnose first, fix second.** Verify the hypothesis with data
  (DB query, log read, probe) BEFORE touching code. Don't repeat
  P27.5d Option A — proposing a fix already in the code.
- **Read the current code** before proposing any change. No edits from
  memory.
- **Audit existing surfaces before building.** Before adding a component,
  endpoint, schema, report, or UI surface, search/read what already exists and
  classify it as KEEP / ADAPT / REPLACE / DEFER. Do not work blind or create a
  duplicate implementation when existing code can be adapted.
- **Smallest correct change.** No "while I'm here" refactors. Add a
  regression test for every bug fix.
- **Verify the four UAT axes** for any data/chart endpoint:
  1. Quality — the bad-data condition is gone (`bad_count=0`).
  2. Recency — `endpoint.latest_ts == MAX(ts) FROM DB`.
  3. Cardinality — `len(rows) == requested_limit`.
  4. Latency — response time under documented threshold.
  P27.5a shipped with only Quality verified and silently truncated
  the 20 newest bars. Never again.
- **No silent failures.** Replace `logger.debug` on push/connect
  errors with `logger.warning` (rate-limited). Surface drift early.
- **One thread at a time.** Finish + report before opening the next
  P-ID.
- **Update reports immediately** when state changes — do not let
  `docs/reports/PROMPT_*.md` lag behind reality.
- **Strategic stop and ask Michael** at phase gates, on plan
  contradictions, or before any change that affects trading logic
  or risk surface.

The Cursor agent's full protocol is in
`.cursor/rules/mems26-pre-live-protocol.mdc`. Same rules apply here.

## Standing Decisions — PERMANENT until Michael revokes (every agent: CC, Cursor, Cowork)

**All gate-disable / gate-bypass decisions below are PERMANENT and default-ON-in-code
until Michael explicitly revokes them in writing.** They are deliberate, not bugs.

- **Do NOT re-enable, re-require, "restore", or revert** any default-OFF flag — not in
  code, config, `.env`, a refactor, a "fix", a merge, or a migration. The disabled
  behavior is the **code default** (no env var needed), so a restart/clone keeps it off;
  do not "helpfully" turn it back on.
- **Do NOT treat a disabled gate as a regression.** If a gate looks "missing", check this
  section first — it was turned off on purpose.
- **Re-enabling ANY of them is a trading-risk-surface change** → strategic stop + explicit
  Michael sign-off. Setting the re-enable env flag (e.g. `S2_REQUIRE_COT_AMT=1`) without
  that sign-off is forbidden.
- The flags do not "expire" or auto-reset. "Until further notice" = until Michael says so.

Current standing decisions (2026-06-08): S2 `choppiness_ok` OFF · Layer-0 chop veto OFF ·
`tick_reversal_15`/`tpo` non-critical for readiness · **S2 ⟂ S3 (COT/AMT not required)**.
See the per-item sections below for the exact flag + file.

## Chop Gates (DISABLED — Michael approval required to re-enable, 2026-06-08)

Both chop gates are turned **OFF by default** per Michael's explicit instruction
(2026-06-08). They must stay off until Michael **explicitly** approves
re-enabling. Do NOT re-enable either — in code, config, or `.env` — without that
approval. These are two **different** metrics; disabling one does not affect the
other:

1. **S2 `choppiness_ok`** (`backend/v9/systems/build_status/s2_inspector.py`) —
   the S2 arming/display gate `choppiness_score < 70` (5-bar candle geometry).
   Inspector/build-status surface only; it never vetoed real S2 fires (the
   engine computes `choppiness_score` but does not gate fires on it). Now
   default-pass. Re-enable ONLY via env `S2_CHOPPINESS_GATE=1` **+ Michael
   approval**.
2. **Layer-0 chop fire-veto** (`backend/v9/gateway/trading_gateway.py`) —
   `chop_state == "SEARCHING"` (Layer-0 composite `chop_score`, 6 indicators
   over 30–60min). System-wide gateway fire-veto for **both S2 and S4**. Now
   default-bypass (still computed + logged for observability). Re-enable ONLY via
   env `LAYER0_CHOP_GATE=1` **+ Michael approval**.

Both flags read `os.getenv(...)` at call/route time; a backend **restart** is
required for the code change to take effect. When either flag is unset (default),
the gate is disabled. Re-enabling is a trading-risk-surface change → strategic
stop + Michael sign-off, per Pre-LIVE Discipline.

## S2 ⟂ S3 — COT/AMT gate disabled (Michael 2026-06-08, approval to re-require)

S2 (five-min Reactive/Initiative) is **independent of S3 (footprint) by default**.
S3 is muted/broken at this stage (`S3_MUTE` / I-11), so the footprint **COT/AMT**
order-flow confirmation is **NOT required** for S2 fires. In
`backend/v9/systems/five_min/five_min_system.py` (`_detect_reactive` +
`_detect_initiative`): the `cur_cot/cur_amt is None → return None` guard and the
`cot_above_amt`/`cot_below_amt` conditions are bypassed unless env
`S2_REQUIRE_COT_AMT=1`. When unset (default), S2 fires on price-geometry + volume
alone. `belly`/`belly_ratio`/`poc_*` were already graceful (None passes), so this
makes S2 fully S3-independent.

Re-requiring COT/AMT is a **trading-risk-surface change** (re-adds the order-flow
filter, fewer fires) → set `S2_REQUIRE_COT_AMT=1` **+ Michael approval** +
backend restart. Verified: with COT/AMT unavailable, flag-unset → Reactive fires;
flag=1 → no fire (`tests/v9/regression/test_s2_independent_of_s3.py`).

## Source-of-Truth Discipline (added 2026-05-28)

Today's IB ground-truth investigation surfaced 5 new permanent rules.
These apply to **every** data path — not just IB. Full mistakes log
+ rationale lives in `.cursor/rules/mems26-pre-live-protocol.mdc` §
*Concrete Mistakes Log (2026-05-28)* and § *Source-of-Truth Discipline*.

### Rule 1 — Honest failure > synthetic value
When the canonical source (Sierra DLL, Sierra Study, ingested bar) is
silent or missing a field, propagate `None` / `"missing"` to the
consumer. **Never** synthesize from a different source and mark the
synthesis with the canonical-source's "found" flag. Example
anti-pattern (forbidden):
```python
if not sierra.get("found"):
    derived = compute_from_bars(...)
    return {"found": True, "value": derived, "source": "derived"}
                # ^^^^^^^^^^^^ the lie
```
Correct: `return {"found": False, "value": None}` and let the UI render
"missing". CLAUDE.md's existing rule (§ Sierra real-time data) already
forbids inventing `proj_*`, synthetic time grids, or rolling-window
levels when the DLL omits them — this rule makes that prohibition
universal across all sources.

### Rule 2 — Verify before you trust
Before treating any numeric "ground truth" claim as authoritative — UI
screenshot, spec doc, user assertion, CC report — run the equivalent
DB / bar-math query and confirm the number is reachable from raw data
in the expected window. If it isn't, stop and ask before patching.

### Rule 3 — `min`/`max` aggregators are amplifiers
Treat every `min`/`max` (and `sum`/`Counter`/`append`) over a stream
as a regression risk for any upstream synthesis bug. When auditing a
synthesis fix, walk one hop downstream and verify the aggregator's
input invariants still hold. A single bad value injected into a
`min`/`max` is forever.

### Rule 4 — TZ ambiguity is forbidden in spec inputs
Any `HH:MM:SS` spec value (Sierra Inputs, YAML config, code constant,
SQL window) MUST carry its TZ either in the value itself, in an
adjacent comment, or via an explicit conversion at the boundary. No
"assumed UTC" / "assumed local".

### Rule 5 — Verification quote, not assertion
When CC (or any subagent) claims something is "fixed" / "should work" /
"passes the four UAT axes", the response is *"paste the command + raw
output"*, not *"confirmed, moving on"*. This applies symmetrically:
when Cursor reports a fix to CC for audit, Cursor must also paste raw
verification, not just claim status.

## DB — local Postgres (root fix — 2026-06-03, supersedes SQLite era)

The local stack runs on **local Postgres** (`DATABASE_URL=postgresql://localhost/mems26`),
NOT SQLite. SQLite corrupted repeatedly because many writers (backend threadpool +
bridge process + the unserialized footprint ORM commit) hit one file; Postgres' MVCC
handles concurrent writes natively, so **the entire corruption class is gone**. Migrated
in 6 phases (`3fbb71f`→`28dda30`) + constraint fix (`2742e4c`); verified GO (soak 21,807
pushes / 0 errors / 0 deadlocks; all upsert `ON CONFLICT` targets matched). Past data was
disposable — started fresh.

**Hard rules — do NOT regress:**
- **Local Postgres ONLY (`localhost`/`127.0.0.1`).** NEVER the Render/Upstash/prod-Postgres
  cloud deployment (separate/older; see §Bridge Local-Only). A new local write path uses
  normal ORM `db.commit()` (safe on PG) — no lock needed; do NOT re-add a lock to `get_db`.
- `safe_writer.py` is now an **engine-based** shim (`engine.connect()`; no raw `sqlite3`;
  `nullcontext` on PG, lock kept only on the SQLite fallback). It still translates
  `INSERT OR REPLACE/IGNORE` → `ON CONFLICT` at runtime by guessing the conflict column —
  every such target MUST have a matching UNIQUE/PK in the model, or the write fails silently.
- New raw SQL reads go through `backend/v9/db/read.py` (`read_all`/`read_one`/`read_scalar`,
  engine-based, `:named` params) — not `sqlite3.connect`.

**Verification rule (mandatory) for PG:** declare a DB change "GO" only on a **concurrent
soak with 0 errors / 0 deadlocks** (multiple write paths in parallel, ≥10 min) — this
replaces SQLite's `integrity_check backend-down=ok` (PG has no malformed-image failure mode).
Still per Rule 5: paste the command + raw output, never "confirmed".

**Residual (non-blocking, close before LIVE):** retire the runtime `INSERT OR REPLACE`→
`ON CONFLICT` shim in favor of explicit per-table `ON CONFLICT`; green the fixture-only
failing tests; remove the SQLite hydration fallback in `main.py`. `footprint`/`tick_reversal`
are no longer a corruption risk on PG — re-enabling is now a product decision, not a safety one.

## Bridge Local-Only Rule

- The bridge MUST push only to `http://localhost:8000`. Never to
  `mems26-web.onrender.com` or any other remote host.
- `CLOUD_URL` defaults to `http://localhost:8000` in
  `bridge/v9_streams/base_stream.py`, and the bridge **refuses to start** if
  `CLOUD_URL` is not `localhost` or `127.0.0.1`.
- The LaunchAgent (`~/Library/LaunchAgents/com.mems26.bridge.plist`) and
  `scripts/start_all.sh` both hard-export `CLOUD_URL=http://localhost:8000`.
  Do not change either back to a render/cloud URL.
- If you ever see `[<stream>] API push FAILED to https://...` in
  `/tmp/bridge.err.log`, stop the bridge and ask Michael — that means a
  config drift slipped through.

## LaunchAgent Stability

- Do not change `~/Library/LaunchAgents/com.mems26.bridge.plist` back to
  `KeepAlive=true`.
- The bridge LaunchAgent must use conditional KeepAlive:

```xml
<key>KeepAlive</key>
<dict>
    <key>SuccessfulExit</key>
    <false/>
</dict>
```

- The bridge LaunchAgent command must export:

```bash
export V9_DISABLE_WATCHDOG="${V9_DISABLE_WATCHDOG:-1}"
```

## Frontend Polling Floors (P30 Forensics — Michael approved)

Do NOT increase these intervals without Michael's explicit approval.
The backend is single-worker uvicorn; aggressive polling chokes it.
These values are the tested safe floor — fast enough for trading,
slow enough to keep health <100ms.

| Component | File | Interval | Reason |
|-----------|------|----------|--------|
| `useSystemStatePolling` | `V9Dashboard.tsx` | **5000ms** | Fires/ZLR need <5s visibility |
| `SoundProvider` | `SoundProvider.tsx` | **10000ms** | Fire ding must reach trader <10s |
| `useLivePricePoll` | `useLivePricePoll.ts` | **5000ms** | WS fallback only — skips when WS connected |
| `WoodiesCciPanel` | `WoodiesCciPanel.tsx` | **5000ms** | CCI chart updates on 5-min bars |
| `StreamHealthPanel` | `StreamHealthPanel.tsx` | **15000ms** | Diagnostic only |
| `Layer0Strip` | `Layer0Strip.tsx` | **15000ms** | Chop score changes slowly |
| `TopBar` heartbeat | `TopBar.tsx` | **15000ms** | Health indicator |
| `TradeHistoryStrip` | `TradeHistoryStrip.tsx` | **30000ms** | History, not real-time |

## Service Bring-Up

- Do not start MEMS26 services unless explicitly asked.
- Do not run `npm run dev`, `next dev`, or `scripts/start_all.sh` during a
  stability audit.
- Before starting services, check for existing listeners on `127.0.0.1:3000`
  and `127.0.0.1:8000` to avoid duplicate frontend/backend instances.

## Codebase Index Protocol (added 2026-06-05 — Michael)

A living index maps every code directory: root `SYSTEM_INDEX.md` + `_INDEX.md`
per directory, generated by `scripts/gen_index.py` (one-line purpose + usage
flag + orphan detection per file).

- **Every agent (Cowork, Claude Code, Cursor) consults the index FIRST** when
  locating a file/function/system — before grepping blind. The index is the
  canonical file-locator. *Known failure it prevents:* `backend/main.py` is the
  real entrypoint (5min → `_day_type_on_bar` → `day_type_machine`), **NOT**
  `backend/v9/main.py` — diagnosing from the wrong file caused a false
  "S1 not wired" conclusion (2026-06-05).
- **Source-of-Truth map — `docs/SOURCE_OF_TRUTH.md` (consult BEFORE querying/wiring any
  signal).** The index maps WHERE code is; the SoT map maps WHICH data source is the
  canonical LIVE truth per signal (bars, day-type, levels, trades) and which are
  stale/legacy/dead. *Known failure it prevents (2026-06-22):* querying the stalled/gapped
  `v9_bars_5min` instead of the live `v9_bars_5min_woodies`, and reading the OLD 3-type
  engine instead of the validated 7-type `classify_replay`. Verify a source's last row is
  recent before trusting it (Rule 2). Keep the map current when a source's role changes.
- **Flag index — `docs/FLAG_INDEX.md` (consult BEFORE asking/claiming whether a flag is
  on/off).** Canonical registry of every behavior/trading flag: state (ON/OFF/inert/param),
  code default, what it does + why, and file:line. Generated by `scripts/gen_flag_index.py`
  from the live code + `.env` + hand-authored semantics in `docs/FLAG_REGISTRY.yaml`, so it
  cannot go stale. *Known failure it prevents (2026-06-23):* answering flag state from the
  hand-maintained SoT list (which had drifted — 4 flags listed OFF were actually ON) or from
  memory. To add/change a flag: edit `FLAG_REGISTRY.yaml` → run the generator; `--check`
  fails on undocumented drift.
- **Regenerate after any structural change** (new/moved/renamed files, new
  system, new endpoint): `python3 scripts/gen_index.py` → commit the refreshed
  `_INDEX.md` + `SYSTEM_INDEX.md`. A stale index is a bug — do not let it lag the code.
  Likewise run `python3 scripts/gen_flag_index.py` whenever a behavior flag is added/changed.
- Do not diagnose runtime state from a single endpoint without cross-checking
  the real path + DB (e.g. `/api/v9/day_type/state` reads a dead wrapper
  instance → misleading `UNKNOWN`; the real classification lives in
  `app.state.day_type_machine` + `v9_day_type_state`).

## Generated Files

- Do not commit Python bytecode (`*.pyc`) or `__pycache__/` files.
- If bytecode appears in git status, treat it as generated state unless the
  user explicitly asks to preserve it.

## Sierra DLL (CC maintenance)

- Canonical ops log: `docs/runbooks/SIERRA_DLL_OPS.md`
- Before editing: cross-check `docs/PROMPT_1_HOTFIX_REPORT.md`, `docs/ENVIRONMENT.md`, `docs/reports/PROMPT30_8_5MIN_JSON_EXPORT.md`, this handoff’s P30 sections.
- Deploy path: `sc_study/` → `./scripts/build_monolithic_cpp.sh --deploy` → `~/SierraChart/ACS_Source/MES_AI_DataExport.cpp` → Remote Build → reload study.
- Study **Input 4** (`V9 Export Directory`) persists per chart in Sierra UI — Mac path `/Users/michael/SierraChart_Data/v9_export/`.

## Reporting Workflow

- For every completed prompt, bug fix, UAT, or phase gate, ask Claude Code to
  prepare or update the relevant report before moving to the next task.
- Prefer Claude Code for structured reports because it is efficient at turning
  test output, diffs, and UAT evidence into concise handoff docs.
- The working agent should focus on implementation, verification, and deciding
  when to stop for strategic questions; report writing should be delegated to
  Claude Code whenever practical.
- Do not advance to the next P-ID until the report exists or Claude Code has
  explicitly said what is missing.

### Roadmap auto-update (mandatory, every task)

After completing any P-ID, bug fix, UAT, or phase gate, and before moving on,
update the living roadmap so it never lags reality:

1. **`docs/plans/ROADMAP_TO_LIVE.html`** — mark finished items done, add any
   newly-surfaced open items into the correct section (blockers / SHADOW /
   Pipeline 5 / DEMO / LIVE), and refresh the "אתה כאן" phase marker + the
   dated "עודכן" line in the header.
2. **`docs/plans/STATUS_BOARD.md`** — fold the same change into the
   `OPEN FOR SUNDAY` priority buckets and add a one-line dated log entry.
3. **Record finding + solution, not just status.** For every item closed or
   newly-surfaced, the STATUS_BOARD log line must capture three things: the
   root-cause/finding (what was actually wrong), the fix that was applied (or
   the proposed solution if deferred), and the verification evidence (the
   command + raw output, or a one-line "verified by …" per Pre-LIVE Rule 5).
   A "done" entry with no finding and no verification is not allowed — it must
   read like `[2026-05-29] P30 future-ts bars: root=aggregator wrote ET not
   UTC → fixed (UTC + ingest guard) → verified 0 future rows in DB`. Items
   deferred to a follow-up keep an OPEN line with the proposed solution so the
   fix is never lost between sessions.

This applies to every agent (Cowork, Cursor, Claude Code). Keep edits the
smallest correct change; do not duplicate an item that already exists. The
roadmap HTML is the at-a-glance view; STATUS_BOARD is the source of record.
