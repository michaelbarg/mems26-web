# CC work order — 2026-07-08 · deploy + live proofs for "LIVE-ready, 2 contracts"

**Contract:** per `docs/handoff/CC_HANDOFF_CONTRACT.md` — Rule 5 (paste raw command + output, never
"done"), anti-tautological tests, mandatory NOT-DONE section in your report. Master work order:
`docs/handoff/MEGA_PROMPT_LIVE_READY_2026-07-08.md` (§2 = the 8-gate Definition-of-Done).

## What Cowork already did today (committed — do NOT rebuild)
| Commit | What |
|--------|------|
| `6bb25ce` + `9f0a64a` | The 07-07 L8 build committed: `sierra_ledger.py` (7/7 tests) · `/api/v9/live_ledger` · `/board` components · task board · mega-prompt/onboarding/work-plan |
| `d999698` | **N3** L2-residual: order-ids mapped+persisted at the `ORDER_SUBMITTED` ack (`_register_submitted_order`); skipped MODIFY/EXIT emits now WARN (rate-limited). **N4/L7**: `effective_contracts()` single source → `quality.contracts` persisted; 2c trade **closes at T2**; P&L legs `[:n]` + R `n×`; `/trades` shows "N/n hit"; slot freed on T1/T2 close; setup_emitter floor honors `FIXED_CONTRACTS_2`. Tests: `backend/v9/tests/services/test_fill_order_map.py` 5/5 · `test_l7_two_contract_symmetry.py` 6/6 (old code: 4/5 and 5/6 FAIL). Regression `tests/v9/regression`: 830 passed / 12 failed == the identical pre-existing fixture set |
| `b275165` | **N5** index refresh (762 files) + FLAG_REGISTRY: `EOD_FLATTEN_V1`/`RECONCILE_LIVE_V1`/`LIVE_LEDGER_V1`/`TRADE_FILLS_PATH` documented → 99 flags, `--check` PASS |

**⚠ The N3/N4 code is NOT live until the backend restarts.** One restart (below) ships everything.

## Execute in order (all Rule 5 — paste raw evidence into `docs/reports/evidence_2026-07-08/`)

### 0 · Confirm FLAT (gate for everything)
Sierra closed yesterday flat; re-verify now: gateway slot + TM actives + DB open rows + Sierra position.
No restart while a live trade is open.

### 1 · N1 — snapshot + health
```
scripts/mems26_snapshot.sh "pre-0708-deploy"
scripts/mems26_verify.sh
```
Paste: services · DLL↔repo · feed fresh · DB lag.

### 2 · N2 — deploy (ONE restart covers L8 flag + N3 + L7)
1. `.env`: set `LIVE_LEDGER_V1=1` (snapshot already taken).
2. `launchctl kickstart -k gui/$UID/com.mems26.backend` → verify via the `[env_loader]` boot-line
   (NOT `ps eww`) that `LIVE_LEDGER_V1=1` and the safety set is intact:
   `RISK_HALT_V1=1 · CAP=400 · FIXED_CONTRACTS_2=1 · EOD_FLATTEN_V1=1 · RECONCILE_LIVE_V1=1 ·
   SYSTEM6_SUPERVISOR=1 · CONT_TREND_FILTER=1 · LIVE_EXECUTION_V1=1`.
3. `curl -s localhost:8000/api/v9/live_ledger | python3 -m json.tool` → must return the **2 real live
   trades** from Sierra fills.
4. **Feed the Sierra TradeActivityLog** into the reconcile (`sierra_stop` + stop-move history) — fills
   alone give entry/exits/P&L; stop-MODIFY history and manual-STOP detection need the activity log.
   Spec: `docs/handoff/CC_SIERRA_LIVE_LEDGER_2026-07-07.md`.
5. **Verify V1–V5** vs the 2 real trades: V1 round-trip-to-the-cent · V2 manual stop-move → MANUAL_STOP_MOVE ·
   V3 manual close → MANUAL_CLOSE · V4 reconcile MATCH↔mismatch · V5 MANUAL vs SYSTEM tagging.
6. `/board` on :3000 shows the ledger reconciled (start :3000 if down).

### 3 · N3 verification (live path)
- On the next placement: log shows `[FillPoller] registered order <id> → trade <id>` at the
  `ORDER_SUBMITTED` ack, and the trade row's `quality.sierra_order_id` is set **before** the ENTRY fill.
- Negative check: no `"MODIFY_STOP SKIPPED"` warnings during a normal live stop-move; if one appears —
  that IS the bug surfacing loudly, investigate before firing.

### 4 · L7 verification — one SIM 2c fire (mega-prompt §2.2, the headline gate)
Fire a 2-contract SIM trade → paste:
- `trade_command.json` `contracts: 2` · bracket in Sierra = 2 OCO groups (no group 3).
- `/api/v9/trades/active` → exactly **2** contract rows, `summary "0/2 hit"→"1/2"…`.
- T1 then T2 fill → trade state **CLOSED**, `exit_reason=T2_HIT`, slot freed
  (`[FillPoller] notified gateway: trade N closed (T2)`), P&L = 2 legs.

### 5 · T1–T5 pre-open gates (before 16:30 IL — mega-prompt §4)
- **T1 arming** — one small live/SIM order submits + fills after the restart (`ORDER_SUBMITTED` error=0).
- **T2 L2 live MODIFY** — fire → T1 → paste the Sierra `sc.ModifyOrder` line from the message log.
- **T3 A7** — a live ZLR/GHOST routes; no `failed_stages=['A7']`.
- **T4 ledger** — today's trades appear + reconcile == backend on `/board`.
- **T5 2c live** — the live bracket reads 2, P&L/R per 2 contracts.

### FINAL GATE
All 8 boxes of mega-prompt §2 green → **strategic stop → Michael arms 2-contract live.** Any red →
DEMO/SHADOW only. Update `task_board.json` + `LIVE_FIX_JOURNAL.md` + `STATUS_BOARD.md` as each item
verifies (keep the board honest).

## NOT-DONE / open after this order
- L2(b) structure-trail after T1 (design, flag-OFF + backtest) · L5 day-type lag (#22) · L6 T1/T2 P&L
  from fill (#17) · L3 monitor shadow-as-live · retire the `INSERT OR REPLACE` shim (pre-LIVE residual).
- DLL does not echo `trade_id` in `trade_result.json` — the submit-ack map uses the most-recent-PENDING
  heuristic (same as ORDER_FAILED). Future hardening: echo `trade_id` in the DLL ack (DLL change + rebuild).
