# CC Prompt — P5-0 Gateway Audit (read-only) · toward DEMO / Pipeline 5

**Mode:** read-only audit. **Zero code changes.** This is Stage 1 of
`docs/plans/PIPELINE5_ACTION_PLAN_2026-05-31.md` — produce the audit so Michael
can lock the 4 decisions; nothing in the order path changes before that.

Every claim = file:line + raw quote (Rule 5). Use `SYSTEM_INDEX.md` /
`backend/v9/gateway/_INDEX.md` / `backend/v9/services/trading_gateway/_INDEX.md`
to navigate — don't grep blind. Output: **`docs/reports/P5_0_GATEWAY_AUDIT.md`**.

## Context (verified by Cowork 2026-06-07)
Two gateway implementations coexist:
- **Legacy** `backend/v9/gateway/trading_gateway.py` (~20 KB, runs in production).
  Has the risk filters wired: `cooldown.py`, `suffering_side_veto.py` (D-049),
  `risk_checks.py`, `session_gate.py`, `trade_management.py`, `rr_score.py`.
  Executors `demo_executor.py` / `live_executor.py` are **stubs** ("logs intent
  but does not connect to Sierra"). Hardcodes dead Apex acct `PA-APEX-125218-01`.
- **New** `backend/v9/services/trading_gateway/gateway.py` (~8 KB, NOT wired).
  Clean structure + `executors/` (demo.py, live.py) + RiskValidator (W14), but
  **missing** cooldown / SSV / cluster / chop gates. Also references dead Apex.

Cowork's preliminary lean (for you to confirm or refute with evidence): a direct
cutover to New = **regression in risk filters** → favor **Merge** (New's
structure + RiskValidator, port Legacy's gates). The audit decides.

## Audit tasks (classify each KEEP / ADAPT / REPLACE / DEFER)
1. **Legacy gateway** — read `trading_gateway.py` in full. List every gate/filter
   it applies before an order, in order, with file:line. Which are risk-critical?
2. **New gateway** — read `services/trading_gateway/gateway.py` + `executors/*`.
   What does it do, what's the RiskValidator coverage, and which Legacy gates are
   absent? Confirm it does NOT call `sc.SubmitOrder` (executors are stubs).
3. **Executors** — for both demo + live executors: do they write a Sierra order
   command (e.g. `trade_command.json`) or just log? Quote the execute() body.
4. **Apex map** — list every occurrence of `PA-APEX-125218-01` (all 5 files seen:
   both gateways' `__init__`/`gateway`/executors) → these must become IronBeam
   `37138283` (D-093.Q2 locked). Produce the exact replace map (file:line).
5. **Heartbeat** — locate the current heartbeat/stale handling; report whether it
   is simple (`stale>30s`) or a ladder (5s emit / 30s WARN-if-flat / KILL-if-open
   / 120s critical), with file:line.
6. **Sierra routing reality** — confirm IronBeam `37138283`, whether a separate
   `[simulation]` path exists, and `sc.GlobalTradeSimulationIsOn()` behavior
   (from `docs/decisions/D-093_SIERRA_ORDER_ROUTING.md` + code).

## Deliverable: the 4 decisions Michael must lock (recommend each)
| # | Decision | Options | Blocks |
|---|----------|---------|--------|
| 1 | Canonical gateway | Legacy / New / **Merge** (Cowork lean) | all of P5 |
| 2 | Bracket order | `sc.BuyEntry/SellEntry`+Attached / `sc.SubmitOCOOrder` | P5-1 |
| 3 | Modify order | `sc.ModifyOrder` / Cancel+Submit | P5-5 |
| 4 | Heartbeat | simple 30s / ladder (KILL-if-open = risk decision) | P5-6 |
| ✅ | Account (D-093.Q2) | LOCKED: IronBeam 37138283 (Apex dead) | — |

For decisions 1–4, give a one-line **recommendation with the evidence** behind it.

## NOT-DONE / boundaries
- Read-only. Do **not** touch any order/risk code, do not remove Apex strings yet
  (that's Stage 3, post-lock) — just map them.
- The audit is the product. End with the recommendation per decision + the Apex
  replace-map, so Michael can lock Stage 2 in one pass.
- ⚠️ DEMO is gated behind SHADOW soak (≥10 RTH days / ≥20 trades) per the roadmap.
  This audit runs in parallel with the soak; it does not bypass the gate.
