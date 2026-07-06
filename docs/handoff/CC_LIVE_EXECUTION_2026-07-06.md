# CC handoff — REAL live execution + P&L-from-Sierra (2026-07-06)

Owner: Claude Code (real-money live path — must be built + tested on the Mac in a
Sierra SIM account before a single real order). Michael decided to go LIVE
(2 contracts, −$400 daily halt, stop 22:15 IL). This is the gate.

## Findings (Rule 2 — verified in code, not assumed)
1. **`_execute_live` is a STUB.** `backend/v9/gateway/trading_gateway.py:1192`:
   `"""LIVE: log intent, persist — no Sierra connection yet."""` … logs
   `"LIVE trade (stub): … — NOT sent to Sierra"`. So LIVE creates a DB row + sets
   `live_slot` but sends ZERO orders → the system would "manage" phantom
   positions Sierra never opened. LIVE cannot trade today.
2. **P&L is a calculation, not Sierra-realized.** `manager.py:776`
   (`close_on_stop`) and `close_trade` set `trade.exit_price = trade.stop`
   (the intended level), then `_calculate_pnl` computes from that. With slippage
   the real fill ≠ the stop level → the recorded P&L is theoretical. Michael's
   requirement: **P&L must come ONLY from Sierra's actual fills.**

Template that WORKS: `_execute_demo` (gateway:1109) already writes to Sierra via
`sierra_command.write_trade_command(..., mode=...)` → `trade_command.json`, and
FillPoller reads `trade_fills.json` back. Mirror it.

## Build A — real `_execute_live` (flag `LIVE_EXECUTION_V1`, default-OFF)
Mirror `_execute_demo` but `mode="live"` so `trade_command.json` carries
`mode:"live"` and Sierra routes to the LIVE account. Same per-contract order-id
mapping, same FillPoller path (it already accepts `"live"`). Under the flag OFF,
`_execute_live` stays the stub (zero behavior change).

## Build B — P&L + exit price from Sierra ONLY (applies to demo AND live)
- On close, set `exit_price` = the **actual Sierra fill price** from the
  FillPoller fill event (`trade_fills.json`) / `trade_result.json` — NOT
  `trade.stop`. `_calculate_pnl` then uses real fills.
- Realized P&L = Σ per-contract (entry_fill − exit_fill)·dir·$5. Entry fill
  already comes from Sierra (`manager.on_fill` sets `entry_price = fill_price`);
  do the SAME for the exit. No "dumb calculation" anywhere on close.
- Keep the I-62 rule: demo/live close ONLY on a Sierra fill event, never on
  BarLevelDetector bar-price inference.

## Mandatory safety gates BEFORE a real order
1. **Sierra SIM first:** point `mode:"live"` at a SIM account, fire a trade, and
   prove: order appears in Sierra, fill comes back via `trade_fills.json`, and
   the recorded P&L matches Sierra's realized P&L to the cent. Paste evidence.
2. **RISK_HALT_V1=1 + RISK_DAILY_LOSS_CAP=400** live (−$400 daily halt).
3. **item-20 reconcile** running for live (orphan / naked-stop early warning).
4. **Contracts = 2** for live (change from FIXED_CONTRACTS_3 → a 2-contract
   setting; confirm Sierra qty = 2 in `trade_command.json`).
5. **22:15 IL hard stop:** no new entries after, flatten open at 22:15 (wire the
   existing EOD/killzone or a scheduled flatten).
6. Snapshot before any `.env`/mode change; restart via `launchctl kickstart`.

## Tests (anti-tautological, fail-on-old)
- Live fire writes `trade_command.json` with `mode:"live"` (stub wrote nothing).
- P&L uses the FILL price, not the stop level: a fill at a price ≠ the stop →
  recorded pnl reflects the fill (fails on current `exit_price = trade.stop`).
- Reconcile flags a live position with no matching slot/DB (orphan).

## NOT in scope
The System-6 timer-button (press / auto-decide after 2 min) is a SEPARATE
follow-up that depends on this + SYSTEM6_AUTOCORRECT. Deferred package items
(12/13/16/17/7/8) stay deferred. Do NOT flip `LIVE_EXECUTION_V1` on real money
until the SIM proof + all six gates are green + Michael signs off.

## Verification to return (Rule 5)
git log + push · pytest (incl. the fail-on-old P&L test) · the Sierra-SIM
evidence (order out, fill in, P&L == Sierra) · confirmation all six gates green ·
NOT-DONE section.
