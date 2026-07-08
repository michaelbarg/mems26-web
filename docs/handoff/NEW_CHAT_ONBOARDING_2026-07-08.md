# New-chat onboarding — MEMS26 · 2026-07-08 · LIVE-ready, 2 contracts, REAL MONEY

You are the new Cowork chat picking up MEMS26. This file onboards you; the **authoritative work order +
full task list** is `docs/handoff/MEGA_PROMPT_LIVE_READY_2026-07-08.md`. Read that next, then execute.

## Read first (in this order)
1. **This file** — state + role + rules.
2. **`docs/handoff/MEGA_PROMPT_LIVE_READY_2026-07-08.md`** — the mission, the 8-gate Definition-of-Done for
   "LIVE-ready, 2 contracts", the ordered tasks (execute-now / tomorrow / secondary), and PART A = the task
   review ledger (every task done today + what remains).
3. **`docs/plans/LIVE_FIX_JOURNAL.md`** — source of truth for the LIVE issues (L1–L8) + evidence.
4. **`docs/plans/WORK_PLAN_2026-07-08.md`** — the phased detail for each task.
5. **`/board`** (frontend) — the living, prioritized task board (`frontend/v9/public/task_board.json`).

## Mission
Make the system **LIVE-ready for today's session with 2 contracts**, done perfectly. Every task executed
**and verified (Rule 5)** before RTH open 08:30 CT / 16:30 IL. If any live-path gate is red → DEMO/SHADOW only.

## State (end of 2026-07-07 — verified)
- **Real money works** — 2 live trades executed yesterday, **BOTH succeeded**. BLOCKER-1 (`GENERAL_ERROR_OR_
  NOT_ENABLED`) was Sierra live-account **arming**, not our code.
- **Sierra is CLOSED → we are FLAT → the deploy window is OPEN.** Restarts/flag changes are safe now (they
  were not while a trade was open).
- **Built yesterday (Cowork, additive, flag-OFF, no restart):**
  - **L8 Sierra-sourced ledger** — `backend/v9/services/sierra_ledger.py` (reconstruct trades from Sierra
    fills, reconcile vs backend, detect MANUAL) · **7/7 tests** (`backend/v9/tests/services/test_sierra_ledger.py`)
    · endpoint `GET /api/v9/live_ledger` (wired `app.py`) · `/board` `LiveLedgerPanel.tsx`. Flag `LIVE_LEDGER_V1`
    (OFF).
  - **`/board`** — Live Ledger + **System 6 supervisor** panel (`GET /api/v9/system6/diagnose`) + the
    prioritized task board.
- **Shipped by CC:** `eb4bc6f` (L2 — MODIFY now reaches Sierra on live) · `ea868cc` (DB varchar(30) crash).
- **The gap Michael cares about (investor-critical):** the frontend shows backend records, not what Sierra
  executed. The Live Ledger (L8) closes it — it must show the 2 real trades, reconciled.

## Your role (Cowork)
Orchestrate + verify from the repo/DB + build code (with tests) + keep the journal/board current + prepare
CC handoffs. **Live Mac ops (Sierra, restart, live DB/logs, DLL) → route to CC** — the sandbox can't reach
the live system. Don't screen-scrape (read code/DB, not the screen). Be crisp, calm, organized.

## Rules (do not break)
- **Rule 5** — paste raw command + output, never "done".
- **Snapshot before any `.env` / DLL / LaunchAgent change** (`scripts/mems26_snapshot.sh "label"`).
- **Keep every safety ON** — −$400 halt (`RISK_HALT_V1`), R:R gate, entry-confirm, EOD flatten, System 6,
  and **2 contracts** (`FIXED_CONTRACTS_2=1`). Don't re-enable any disabled gate (CLAUDE.md standing decisions).
- **No restart while a live trade is OPEN** — currently FLAT, so deploys are OK; re-check before each restart.
- Verify flags via the `[env_loader]` boot-line, not `ps eww`. Restart via `launchctl kickstart -k
  gui/$UID/com.mems26.backend`.

## Immediate next steps (start here)
1. **Confirm state** — `git log --oneline -15`, read `task_board.json`, the journal, and check for anything
   CC did overnight (new commits/evidence). Classify each as WORKING/FAULTY from repo/DB (Rule 5).
2. **Confirm flat** — ask CC / check: 0 open live trades before any restart.
3. **Execute the mega-prompt §3 (now, flat):** deploy L8 (enable `LIVE_LEDGER_V1` + restart + feed the
   TradeActivityLog + verify V1–V5 vs the 2 real trades) · L2-residual · **L7 2-contract symmetry** · index
   refresh. Cowork builds/verifies; CC does the restart + Sierra evidence.
4. **Drive the 8-gate Definition-of-Done to all-green** (mega-prompt §2), updating `/board` + the journal as
   each item verifies. Strategic-stop + ask Michael at the final LIVE gate.

## The map (where everything is)
| Thing | Path |
|-------|------|
| Authoritative work order + task ledger | `docs/handoff/MEGA_PROMPT_LIVE_READY_2026-07-08.md` |
| Live issues (source of truth) | `docs/plans/LIVE_FIX_JOURNAL.md` |
| Phased plan | `docs/plans/WORK_PLAN_2026-07-08.md` |
| Living task board (both agents edit) | `/board` ← `frontend/v9/public/task_board.json` |
| L8 engine + tests | `backend/v9/services/sierra_ledger.py` · `backend/v9/tests/services/test_sierra_ledger.py` |
| L8 endpoint + UI | `backend/v9/api/v9/live_ledger_routes.py` · `frontend/v9/src/v9/components/board/LiveLedgerPanel.tsx` |
| System 6 | `GET /api/v9/system6/diagnose` · `.../board/System6SupervisorPanel.tsx` |
| L2 code | `manager.py` (`_is_demo_mode`:102 · `_emit_modify_stop`:119 · `_apply_smart_be_after_t1`:391) |
| A7 | `woodies/woodies_system.py:668` (stop fallback) · `woodies/stages/a7_universal_checks.py` |
| CC live handoffs | `docs/handoff/CC_CONTINUATION_2026-07-07.md` · `CC_SIERRA_LIVE_LEDGER_2026-07-07.md` |
| Guardrails | `CLAUDE.md` · `.cursor/rules/mems26-pre-live-protocol.mdc` |

**Definition of DONE for the day:** the 8 gates in the mega-prompt §2 are all green (arming holds ·
**L7 2-contract symmetry** · L2 live MODIFY · A7 route · L4 capture · L8 ledger reconciled · safety · health)
→ Michael arms 2-contract live. Nothing is "done" without raw verification. Keep the board honest.
