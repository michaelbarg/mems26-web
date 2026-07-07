# CC — URGENT: Sierra-sourced LIVE trade ledger (2026-07-07) · journal L8 + L2

**Michael (real money):** build a LIVE trade record that shows **only what Sierra actually
EXECUTED** — imported from Sierra's own data (real fills / stop moves / P&L). **What actually
happens, NOT what the backend records.** Today the monitor showed a stop moved to BE 7544.75 after
T1, but Sierra did NOT move it — records ≠ reality. We can't trust backend-synthesized records on
real money.

## Source of truth (authoritative — use ONLY these)
- Sierra's **fills** (`trade_fills.json`) — each ENTRY/T1/T2/T3/STOP/FLATTEN fill: actual price,
  order_id, side, contracts, account, ts.
- Sierra's **TradeActivityLog** (the record of every order/modify/fill Sierra performed).
- **NOT** the backend's calculated `entry_price`/`stop`/`pnl_usd` — those are what we WANT to verify,
  not the source.

## Build — `sierra_ledger` (LIVE only)
Reconstruct each LIVE trade from Sierra's fills alone:
- entry (from the ENTRY fill), each **stop MODIFY** Sierra actually accepted, each exit fill,
  contracts, **realized P&L from the fill prices**, account, timestamps.
- Key it by the Sierra order_id chain (per-contract IDs). Filter to the LIVE account 37138283 only
  (exclude demo/shadow — shadow = nice-to-have, not this).
- Surface it as the LIVE ledger the trader sees (separate from backend/shadow records).

## Protocol (orderly, permanent)
1. Sierra fills/activity-log = the source; the backend record is a claim to be checked.
2. For each live trade: build the Sierra ledger row; **reconcile** it against the backend's DB row
   → flag EVERY field that differs (stop, P&L, state, contracts) as a **divergence** = CRITICAL.
   This is exactly what catches L2 (stop shows moved / Sierra didn't) and L3 (monitor shows shadow
   as live).
3. The trader-facing LIVE list shows the **Sierra** numbers; divergences are flagged loudly.
4. Update `LIVE_FIX_JOURNAL.md` + `STATUS_BOARD.md` when a divergence is found/fixed.

## Fold in L2 (stop-move)
While building: verify whether `_emit_modify_stop` → `sc.ModifyOrder` actually reaches Sierra on a
live stop-move (paste the Sierra activity-log line for the modify). If the backend logged SMART_BE
but Sierra shows no modify → that's the bug. Also note the DESIGN change Michael wants: after T1 the
stop trails to **STRUCTURE** (nearest structural level), not to entry/BE — separate task, don't bundle.

## Guardrails
Read-only during an open live trade. No restart / code deploy with a position open — build + wire
when flat/EOD. Rule 5: paste the Sierra activity-log + fills as evidence, not backend claims.
