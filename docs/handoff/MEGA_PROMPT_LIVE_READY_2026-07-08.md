# 🚀 MEGA-PROMPT — LIVE-ready for 2026-07-08 · 2 contracts · REAL MONEY

**How to use:** this is the single authoritative work order to make MEMS26 LIVE-ready for tomorrow with
**2 contracts**, done perfectly. CC executes on the Mac (Sierra/DB/restart/DLL); Cowork verifies from
repo/DB + builds code + keeps docs current. Work top-to-bottom. Nothing is "done" without **raw
verification (Rule 5)**. Companion detail: `docs/plans/WORK_PLAN_2026-07-08.md`. Live view: `/board`.

---

## 0 · Context (where we are, end of 2026-07-07)
- **Real money works.** 2 live trades executed today, **BOTH succeeded** → the order path to Sierra is
  proven. BLOCKER-1 (`GENERAL_ERROR_OR_NOT_ENABLED`) was live-account **arming**, not our code.
- **Sierra is CLOSED now → we are FLAT → the deploy window is OPEN** (restarts/flag changes are safe).
- Built today (Cowork, additive, flag-OFF, no restart): **L8 Sierra-sourced ledger** engine + endpoint +
  `/board` UI; the **System 6 supervisor** panel; a prioritized **task board**. **L2 fix** shipped by CC
  (`eb4bc6f`), **DB-crash fix** (`ea868cc`).
- **The gap Michael cares about:** the frontend shows backend records, not what Sierra executed. The Live
  Ledger (L8) closes that — it must show the 2 real trades, reconciled.

## 1 · Standing rules (do NOT break)
- **Rule 5** — paste the raw command + output, never relay "done".
- **Snapshot before any `.env` / DLL / LaunchAgent change** — `scripts/mems26_snapshot.sh "label"`.
- **Keep every safety ON** — −$400 daily halt (`RISK_HALT_V1`), R:R gate, entry-confirm, EOD flatten,
  System 6 supervisor, and **2 contracts** (`FIXED_CONTRACTS_2=1`). Do **not** re-enable any disabled gate
  (standing decisions in CLAUDE.md) without Michael.
- **One thread at a time** — finish + verify + report before the next. Update the journal/board as you go.
- Restart the backend only via `launchctl kickstart -k gui/$UID/com.mems26.backend`; verify flags via the
  `[env_loader]` boot-line, not `ps eww`.

## 2 · ✅ Definition of DONE — "LIVE-ready, 2 contracts" (ALL must be green before Michael arms)
1. **Arming holds** — after a restart, a small live order still `ORDER_SUBMITTED` error=0 + fills.
2. **2-contract symmetry (L7)** — bracket, targets, per-contract P&L, R, Sierra command **and** display all
   read **2** — no phantom 3rd target ("1/3"). This is the headline for 2-contract readiness.
3. **L2 live** — BE/stop-move actually reaches Sierra (paste `sc.ModifyOrder`), not just the DB.
4. **A7 (L1)** — a live ZLR/GHOST **routes**, no `failed_stages=['A7']`.
5. **Live fill capture (L4)** — real fill → tracked trade + Sierra P&L, order_id **mapped** (no I-58 fallback).
6. **Live Ledger (L8)** — `/board` shows the 2 real trades from Sierra fills, reconciled == backend (no
   CRITICAL divergence), manual events tagged.
7. **Safety verified live** — −$400 halt, EOD auto-flatten, System 6 supervisor all active + observable.
8. **Health + traceability** — `:3000` + `:8000` up, feed fresh, DB lag ok, index refreshed (A7 traceable).

## 3 · EXECUTE NOW (flat = safe) — ordered, each with verify
- **N1 · Snapshot + health** — `scripts/mems26_snapshot.sh "pre-0708-deploy"` → `scripts/mems26_verify.sh`.
  Paste: services, DLL↔repo, feed, DB lag.
- **N2 · Deploy L8 ledger** — set `LIVE_LEDGER_V1=1` in `.env` → restart → `curl :8000/api/v9/live_ledger`
  returns the 2 live trades. **Feed the Sierra TradeActivityLog** into the reconcile (`sierra_stop` +
  stop-move history — fills alone give entry/exits/P&L; the stop-MODIFY history needs the log). **Verify
  V1–V5** (round-trip to the cent · manual stop-move · manual close · reconcile MATCH↔mismatch · MANUAL vs
  SYSTEM) against the 2 real trades. Paste raw Sierra evidence into `docs/reports/evidence_2026-07-08/`.
- **N3 · L2-residual** — in the I-58 fallback (`fill_poller.py`) also call `set_sierra_order_ids`, and turn
  the two silent `return`s in `_emit_modify_stop` (`manager.py:121-125`) into rate-limited warnings.
  Anti-tautological test (fallback trade → order_id stored → MODIFY emitted). Verify.
- **N4 · L7 2-contract symmetry** — audit + fix the bracket/targets/P&L/R/command/display to read `2`
  everywhere. Add a test that a 2-contract trade shows exactly 2 targets. Verify on one SIM 2c fire.
- **N5 · Index refresh** — `python3 scripts/gen_index.py` + `python3 scripts/gen_flag_index.py --check` →
  commit `SYSTEM_INDEX.md` / `_INDEX.md` / `FLAG_INDEX.md` (so A7 and every component are traceable on the board).

## 4 · TOMORROW pre-open (before 16:30 IL) — verify on the live/SIM path
- **T1 · Re-verify arming** (§2.1) — one small live/SIM order submits+fills after the morning restart.
- **T2 · L2 live MODIFY** (§2.3) — fire → T1 → paste the Sierra modify line.
- **T3 · A7 route** (§2.4) — one live ZLR/GHOST routes, no `failed_stages=['A7']`.
- **T4 · Live Ledger** (§2.6) — the trades appear + reconcile == backend on `/board`.
- **T5 · 2-contract** (§2.2) — confirm the live bracket shows 2, P&L/R per 2 contracts.
- **FINAL GATE** — all §2 boxes green → Michael arms 2-contract live. If any red → DEMO/SHADOW only.

## 5 · Secondary / backtest (do NOT block the LIVE gate)
- L5 day-type lag (task #22, flag-OFF + backtest) · L6 T1/T2 P&L from fill (task #17) · L2(b) after-T1
  trail to **STRUCTURE** not BE (design, flag-OFF, backtest) · L3 monitor shadow-as-live fix.

---

## PART A — Task review ledger (go over each one)

**✅ Done today (2026-07-07) — verify where noted**

| ID | Task | Done today | Remaining / verify | Owner |
|----|------|-----------|--------------------|-------|
| B1 | Live order path / arming | **2 live trades succeeded** (real money) | re-verify arming holds post-restart | CC |
| — | Order path 2c to Sierra | DLL `9d314d0`, SIM 8418 error=0 | — | CC |
| L2 | Stop-move reaches Sierra on live | fix `eb4bc6f` (`_is_demo_mode` live) | verify live MODIFY (Rule 5); do L2-residual (N3) | CC |
| — | DB crash on 42-char exit_reason | fix `ea868cc` (varchar 30) | add overflow guard/test | CC |
| L8 | Sierra-sourced ledger + manual detect | **engine+endpoint+UI built, 7/7 tests** (Cowork) | deploy N2 + verify V1–V5 vs 2 real trades | CC+Cowork |
| — | `/board`: Live Ledger + System 6 + task board | built (Cowork, no restart) | needs `:3000` up + LIVE_LEDGER_V1 for the ledger | Cowork |
| — | Safety net P1.1/P1.2/P1.3/P2.4 | built + 18 tests (flag-gated) | verify live (open position + EOD clock) | CC |
| — | CC-evidence verification (L1–L7) | done (WORKING/FAULTY, repo+DB) | — | Cowork |
| — | Tomorrow work plan + this mega-prompt | done | execute | both |

**🔴 To execute for LIVE-ready 2 contracts**

| ID | Task | Action | Verify (Rule 5) | Owner |
|----|------|--------|-----------------|-------|
| L7 | **2-contract symmetry** | bracket/targets/P&L/R/command/display read 2 | 2c SIM fire shows exactly 2 targets | CC |
| L1 | A7 route | verify fallback works live | live ZLR/GHOST routes, no `failed_stages=['A7']` | CC |
| L2r | L2 residual | order_id in I-58 fallback + warn | fallback trade emits MODIFY | CC |
| L4 | Live fill capture | map order_id (no fallback) | real fill → tracked + Sierra P&L | CC |
| L8d | Deploy L8 | enable flag + restart + feed activity log | V1–V5 green vs 2 real trades | CC+Cowork |
| IDX | Index refresh | gen_index + gen_flag_index --check | committed, 0 drift | CC/Cowork |

**🟡 Secondary (non-blocking):** L5 day-type · L6 T1/T2 P&L · L2(b) structure-trail · L3 monitor.

---
_The board (`/board`, `frontend/v9/public/task_board.json`) is the living version of this list — both
Cowork and CC keep it in lockstep with `LIVE_FIX_JOURNAL.md`. Update status as each item verifies._
