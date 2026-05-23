# CC — Update `P31_TASK_BOARD.md` for 2026-05-22 morning + early-afternoon session

**Issued:** 2026-05-22 09:25 IL (06:25 UTC) · **Updated:** 2026-05-22 10:35 IL (07:35 UTC) — B1 implementation shipped by Cursor (see §"B1 IMPLEMENTATION COMPLETE" at bottom).
**For:** Claude Code · **Mode:** documentation only — no code changes, no service restarts, no git commits.

This morning's session produced three completed work items + one approved-but-not-implemented recommendation. **B1 was then implemented by Cursor in the early afternoon** (10:00–10:30 IL) — see the addendum section at the bottom of this prompt. Update `docs/handoff/P31_TASK_BOARD.md` §0 (and §1 if relevant) so the next agent (or Michael at the next return) sees current reality, not yesterday's snapshot.

---

## What changed (factual — do not editorialize)

### 1. Issue B frontend fix — **DONE** (Cursor, 08:51 IL)

- Pink today POC/VAH/VAL spec from Michael: stepped lines from RTH open → RTH close, updating every 30 min as Sierra Study ID:3 developing TPO does. Reference doc: `docs/handoff/SIERRA_STUDIES_CONFIG_2026-05-19.md`.
- Cursor shipped 3 frontend changes:
  - `frontend/v9/src/v9/components/chart/v5b/tpoLevels.ts` — new `parseSierraTsToMs()` exported helper handles `+00:00`/`Z`/`-04:00` suffixes (P31-FE-TPO-1 fix). `periodOpenedMs` + `sessionOpenedMs` delegate. `syncTpoPriceLines` skips flat fallback when today periods exist (`todayPeriods.length >= 1`).
  - `frontend/v9/src/v9/components/chart/v5b/TpoContinuityOverlay.tsx` — `periodToUnix` uses shared `parseSierraTsToMs`.
  - `tests/v9/frontend/test_tpo_stepped_lines.py` — **5 new regression tests, 5/5 PASS**.
- TS compile: clean for the two modified files (no new errors; 16 pre-existing errors in 8 unrelated files unchanged).
- `test_tpo_overlay_six_lines.py` still 3/4 pass — the 1 failure (`assert "createPriceLine" in lv`) is pre-existing in the `??` untracked test from a prior speculative refactor, unrelated to this session.

### 2. P31-DT-CURRENT-DEADLOCK mitigation — Polling floors **DONE** (CC #1, 09:11 IL)

- Backend stalled this morning after 12h 43m uptime. 5/5 `/api/v9/health` pings returned `HTTP 000` (timeout). Cursor restarted backend (old PID 57984 → new PID 36191 at 08:30 IL; restart per `P31_NEXT_CHAT_2026-05-21_EVE.md` §4). Root cause traced to aggressive frontend polling stacking on single-worker uvicorn.
- CC #1 applied the **P30 Forensics polling floors** (Michael-approved):

| File | Before | After | Reduction |
|------|--------|-------|-----------|
| `frontend/v9/src/v9/components/layout/V9Dashboard.tsx` (`useSystemStatePolling`) | 2000 ms | 5000 ms | 2.5× |
| `frontend/v9/src/v9/components/sounds/SoundProvider.tsx` (fire detection) | 5000 ms | 10000 ms | 2× |
| `CLAUDE.md` — new "Frontend Polling Floors" section + 8-row table | (none) | full guard | anti-regression |

- The other 6 components in the CLAUDE.md table (`useLivePricePoll`, `WoodiesCciPanel`, `StreamHealthPanel`, `Layer0Strip`, `TopBar`, `TradeHistoryStrip`) were already at the floor values per CC #1's audit — no code change needed for them.

### 3. TPO stepped-periods investigation — **DONE** (CC #2, 09:15 ET deliverable)

CC #2 graded the three candidate paths Cursor outlined in `docs/handoff/CC_INVESTIGATE_TPO_STEPPED_PERIODS.md`:

| Path | LOC | Risk | Fidelity | Effort |
|------|-----|------|----------|--------|
| **B1 backend snapshot job** (read `tpo.json::session` every 30-min RTH boundary → write `v9_tpo_history`) | ~105 | **LOW** | **HIGH** | **~3 h** |
| B2 TPOSystem letter hook (in-process) | ~70 | MEDIUM | MEDIUM | ~4 h |
| B3 DLL per-letter `periods[]` | ~125 | MEDIUM | PERFECT | ~6 h |

**Recommendation: B1** — Sierra's authoritative POC/VAH/VAL from `tpo.json` snapshotted at 30-min boundaries. Highest fidelity without touching the DLL, targets the empty `v9_tpo_history` table whose schema already matches (`ts, poc, vah, val, ib_high, ib_low, profile_shape, poc_migration_direction`), and the reader is a single SELECT swap in `_load_tpo_periods`. Zero touches to the consumer hot path.

**Confirmed by CC #2:**
- `tpo.json` keys: `[type, version, export_ts, session, ib, prior_day, previous_session]` — **no periods/history key**.
- `v9_tpo_history` rows: **0** (table exists, no writer).
- `v9_tpo_journal` rows: 12,861 — per-letter bar **price ranges** (price_low/price_high), **NOT** per-letter cumulative POC/VAH/VAL. Letter A has 1,327 rows / Letter Q has 2,088 rows (restart resets `current_letter_idx=0` → duplicate early letters). **Cannot reconstruct stepped levels from journal without full profile replay + dedup.**
- `v9_tpo_sessions` writer:
  - INSERT (open): `tpo_system.py:467 _open_session()`
  - UPDATE (levels): `tpo_system.py:527 _persist_session()`
  - opened_ts format: three formats in DB — ISO `-04:00`, naive `+00:00`, bare unix epoch — bridge passes through without normalization.

**Edge cases B1 must handle (CC #2's list):**
- RTH guard 09:30–16:00 ET (13 letters A=09:30 … M=15:30).
- `trading_date` logic (not calendar date) — pre-18:00 ET snapshots belong to the correct session.
- DST transitions via `zoneinfo("America/New_York")` — no hardcoded UTC offset.
- Restart mid-RTH → immediate catch-up snapshot from current `tpo.json` so chart isn't empty until next boundary.
- Skip snapshot when `tpo.json` `export_ts` is older than 120 s (no live data flowing — market holiday / half-day / DLL paused).
- New `v9_tpo_history.ts` rows use single format: naive ET wall-clock `"YYYY-MM-DD HH:MM:SS"` (matches the bar-ts convention).
- Frontend ready: `TpoContinuityOverlay.tsx` already handles `LineType.WithSteps` + `periods[]` with ≥ 2 entries + `nowUnix` extension. No further frontend change needed beyond pointing `_load_tpo_periods` at `v9_tpo_history` for the today/developing view.

**Status:** **awaiting Michael's go-ahead** to implement. Until then, today's pink lines render as the flat fallback (current behavior — `session.poc` horizontal across RTH window).

### 4. Backend restart — Bridge unchanged

- Backend: PID 57984 (stalled, 12h43m uptime, 57% CPU) → PID 36191 (08:30 IL, healthy, /health 246ms).
- Bridge: unchanged (PID 55100, since ~19:31 IL yesterday).
- Frontend: PID 26120 (changed from 90313 in last handoff — independent Next dev restart, not by us).

---

## What you need to update in `P31_TASK_BOARD.md`

### §0 — Greeting + current position

Replace the existing §0 table with this morning's state:

| field | value |
|-------|-------|
| **ברכה אחרונה** | 🌅 **בוקר טוב** — 2026-05-22 09:25 IL |
| **נקודת ציון** | **Issue B frontend fix shipped** (Cursor 08:51) · **P31-DT-CURRENT-DEADLOCK mitigated** via polling floors (CC #1 09:11) · **TPO stepped-periods B1 recommended** (CC #2 09:15) — pending Michael approval |
| **אחוז גס ל-LIVE** | ~**62%** (Issue B frontend done + deadlock mitigated; B1 backend job still open; SHADOW soak still 0%) |
| **הצעד הבא** | 🟡 **Michael: approve B1?** → Cursor implements B1 backend snapshot job (~3 h, LOW risk) → live UAT after RTH 17:30 IL today. **בלי B1**: pink lines stay flat until DLL exposes per-letter (Michael rejected DLL path). |

Update the service status table to reflect new PIDs:

- Backend `:8000` 🟢 PID **36191** (Cursor restart 08:30 IL — see §6 P31-DT-CURRENT-DEADLOCK note).
- Bridge 🟢 PID **55100** unchanged (since 19:31 IL yesterday).
- Frontend `:3000` 🟢 PID **26120** (independent restart between sessions, no action).

### §1 — Gantt — add rows under "NowP31"

| P30 Road (Phase) | gantt row | P31 (daily) | סטטוס |
|------------------|-----------|-------------|-------|
| לפני P-S0 | NowP31 | **P31-FE-TPO-1** Issue B frontend stepped lines | ✅ 2026-05-22 08:51 (Cursor) |
| לפני P-S0 | NowP31 | **P31-DT-CURRENT-DEADLOCK** polling floors | ✅ 2026-05-22 09:11 (CC #1) |
| לפני P-S0 | NowP31 | **P31-TPO-B1** backend snapshot job → v9_tpo_history | 🟡 awaiting approval — 2026-05-22 09:15 (CC #2 spec) |

### Add a new section §12 — TPO stepped periods (B1 spec)

Below §11 (Confluence bug), add `§12 — TPO stepped periods — B1 spec (pending approval)` with:

- One-paragraph problem statement (chart needs stepped POC/VAH/VAL matching Sierra Study ID:3, current data has no per-letter history).
- The path-grade table from this prompt.
- The edge-case list from this prompt.
- A pointer to `docs/handoff/CC_INVESTIGATE_TPO_STEPPED_PERIODS.md` (the original Cursor prompt) for full context.
- An "Acceptance criteria" subsection echoing the 4 UAT axes from CC #2:
  - Quality: after 10:30 ET, `/api/v9/tpo/current.periods` has ≥ 2 today rows.
  - Recency: snapshot rows arrive within 30 s of the 30-min boundary.
  - Cardinality: by 16:00 ET, exactly 13 today rows (A …M) in `v9_tpo_history`.
  - Latency: `_load_tpo_periods` SELECT < 50 ms.

### Update §0's "סטטוס מהיר (עדכון שירותים)" table — flip the polling row

Add a new row (or update existing if present):

| רכיב | סטטוס | הערה |
|------|--------|------|
| **Frontend polling load** | 🟢 | floors applied 2026-05-22 09:11 (CC #1): V9Dashboard 2s→5s, SoundProvider 5s→10s, others unchanged at floor. Documented in `CLAUDE.md` "Frontend Polling Floors" section. **Anti-regression: do not raise without Michael.** |

### Update §0 — add Issue B status row

| רכיב | סטטוס | הערה |
|------|--------|------|
| **Issue B — Pink stepped POC** | 🟡 | Frontend done (Cursor 08:51 — `tpoLevels.ts`, `TpoContinuityOverlay.tsx`, +5 regression tests). Backend B1 spec done (CC #2 09:15, ~3 h, LOW risk). **Awaiting Michael go-ahead on B1.** Until then, pink lines render flat (current developing POC) across RTH window — no stepping. |

---

## Files referenced (read-only for CC during this doc update)

- `docs/handoff/P31_TASK_BOARD.md` (target — write changes here only)
- `docs/handoff/CC_INVESTIGATE_TPO_STEPPED_PERIODS.md` (Cursor's prompt to CC #2)
- `docs/handoff/SIERRA_STUDIES_CONFIG_2026-05-19.md` (Study ID:3 spec)
- `docs/handoff/P31_NEXT_CHAT_2026-05-21_EVE.md` (yesterday's handoff for §3 follow-ups context)
- `CLAUDE.md` (newly-added "Frontend Polling Floors" section)
- `frontend/v9/src/v9/components/chart/v5b/tpoLevels.ts` (Cursor's morning fix)
- `frontend/v9/src/v9/components/chart/v5b/TpoContinuityOverlay.tsx` (Cursor's morning fix)
- `tests/v9/frontend/test_tpo_stepped_lines.py` (new regression tests)

---

## Guardrails

- **No code changes.** Only edit `docs/handoff/P31_TASK_BOARD.md`. No other file touch.
- No service restarts, no `kill`, no `launchctl`, no `screen`.
- No git commits. Working tree stays dirty for Michael to review.
- Keep Hebrew style consistent with the existing `P31_TASK_BOARD.md` voice. Tables in Hebrew when the existing section uses Hebrew; English where the existing section is English.
- If something in this prompt contradicts what you find on disk, **stop and report to Michael** — do not assume one source over the other.

---

## After you finish

Reply with:

```
P31_TASK_BOARD UPDATE — 2026-05-22 ??:?? IL

CHANGES MADE:
  §0 greeting:        <old → new>
  §0 service table:   <rows updated>
  §0 status table:    <rows added/modified>
  §1 Gantt:           <rows added>
  §12 new section:    <yes/no, summary>

CONSISTENCY CHECK:
  - all PIDs match `lsof -i :8000`: <yes/no>
  - all file paths exist: <yes/no>
  - all timestamps in IL: <yes/no>

NO CODE CHANGES. NO COMMITS.
```

---

# B1 IMPLEMENTATION COMPLETE — Addendum (Cursor, 2026-05-22 10:30 IL)

**Status change since the original (09:25 IL) version of this prompt:** B1 (TPO snapshot job → `v9_tpo_history`) is **no longer "awaiting Michael's go-ahead"** — Cursor implemented it after Michael approved at 09:51 IL with "אני יוצא לפעולה - אי מאשר". When you update the task board, reflect the **new** state.

## Files shipped (Cursor)

| File | Status | Purpose |
|------|--------|---------|
| `backend/v9/db/migrations/versions/017_v9_tpo_history_unique_ts.sql` | **NEW + applied** | UNIQUE INDEX `ux_v9_tpo_history_ts` so the snapshotter can `INSERT OR REPLACE` idempotently |
| `backend/v9/services/tpo_history_snapshotter.py` | **NEW** | `TPOHistorySnapshotter` — async task, 30-min ET boundary scheduler, RTH gate via `market_clock.is_rth_open`, 120 s staleness gate, startup catch-up. Module-level singleton + `get_snapshotter()` |
| `backend/main.py` | **MODIFIED** | Startup hook starts the snapshotter task; `V9_DISABLE_TPO_SNAPSHOTTER=1` kill-switch |
| `backend/v9/api/v9/tpo_routes.py` | **MODIFIED** | New `_load_periods_from_history` (per-30-min from `v9_tpo_history`); `_load_tpo_periods` prefers history, falls back to `_load_periods_from_sessions` (legacy daily); defensive schema-mismatch handling so a shared mock can't crash the endpoint |
| `tests/v9/services/test_tpo_history_snapshotter.py` | **NEW** | 18 regression tests — slot math, RTH gating (5 skip paths), idempotency, IB-found edge case, fallback safety |
| `scripts/uat_tpo_stepped_lines.sh` | **NEW** | Four-axis UAT probe (Quality / Recency / Cardinality / Latency); `--watch` flag for 60-second poll |
| `docs/handoff/CC_INVESTIGATE_UNIFIED_HISTORY_ARCHITECTURE.md` | **NEW** | Next-step CC investigation prompt — broader uniform-history architecture across all 14 streams (Michael's expanded vision: gap-fill on startup, no full reload, manual replay) |

## Verification (Cursor, 10:30 IL)

- Backend restart: old PID 74381 → new PID 77057 at 10:25 IL.
- `/api/v9/health` HTTP 200, < 5 ms warm.
- Snapshotter alive — `grep tpo_snapshotter /tmp/backend.log`:
  > `[tpo_snapshotter] task started — tpo.json=/Users/michael/SierraChart_Data/v9_export/tpo.json db=/Users/michael/Downloads/mems26_web_git/data/mems26_local.db interval=30min`
- `v9_tpo_history` rows = 0 (correct — RTH has not opened yet; first snapshot scheduled for 17:30:05 IL).
- `/api/v9/tpo/current.periods` still serves the legacy daily rows from `v9_tpo_sessions` as the pre-RTH fallback (4 rows from May 20–21).
- 18/18 new tests pass. 96/97 of the combined P31 regression sweep pass (the 1 pre-existing rotting test `test_load_tpo_periods_normalizes_unix_ts` is unaffected by this change — its 48 h cutoff has slid past the test's hardcoded 2026-05-18 timestamp, separate from B1).

## What the task board should now say

In §0:

- Replace "Awaiting Michael go-ahead on B1" with **"B1 shipped, awaiting live UAT at RTH 17:30 IL"** in the Issue B status row.
- Update backend PID to **77057** (changed during B1 deploy at 10:25 IL).
- Add a new row under "סטטוס מהיר": **TPOHistorySnapshotter 🟢 PID 77057 (task started 10:25 IL · v9_tpo_history empty pre-RTH)**.

In §1 (Gantt), flip:

| P-ID | sטאטוס |
|------|---------|
| **P31-TPO-B1** backend snapshot job → v9_tpo_history | **✅ 2026-05-22 10:30 (Cursor)** — was 🟡 awaiting approval |

Add a new pending row:

| **P31-UNIFORM-HISTORY** unified history architecture across all streams | 🟡 awaiting CC investigation — 2026-05-22 10:30 (Cursor wrote prompt at `docs/handoff/CC_INVESTIGATE_UNIFIED_HISTORY_ARCHITECTURE.md`) |

If you created §12 "TPO stepped periods (B1 spec)" per the original instruction, **flip its status to DONE** and link to:

- `backend/v9/services/tpo_history_snapshotter.py` (implementation)
- `tests/v9/services/test_tpo_history_snapshotter.py` (tests)
- `scripts/uat_tpo_stepped_lines.sh` (UAT)

Add a new §13 "Unified history architecture (Michael 2026-05-22 expanded vision)" with the one-paragraph problem statement from `CC_INVESTIGATE_UNIFIED_HISTORY_ARCHITECTURE.md` and link to that prompt for full context.
