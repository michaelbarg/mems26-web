# CC WORK ORDER — Sierra-sourced LIVE ledger + manual-intervention (2026-07-07) · journal L8/L2

**Michael (REAL MONEY):** the LIVE record must reflect **only what Sierra actually EXECUTED** —
imported from Sierra — *what actually happens, not what the backend records*. And **manual
interventions by Michael** (stop moved / trade closed in Sierra) must be detected, adopted, and
logged as MANUAL — for learning. Today the monitor showed a stop moved to BE 7544.75 after T1 but
Sierra did NOT move it → records ≠ reality. This work order = **tasks + tests + verification**, complete.

**Guardrails:** read-only during an open live trade; build/wire only when FLAT/EOD. No backend
restart with a position open. Rule 5: evidence = raw **Sierra** fills/activity-log, NOT backend claims.
Anti-tautological tests (must FAIL on the old code) + a NOT-DONE section. Update `LIVE_FIX_JOURNAL.md`
+ `STATUS_BOARD.md` at the end.

## Source of truth (use ONLY these)
`trade_fills.json` (per fill: kind ENTRY/T1/T2/T3/STOP/FLATTEN · price · order_id · side · contracts
· account · ts) + Sierra **TradeActivityLog** (every order/modify/fill/cancel Sierra performed).
Filter to the LIVE account **37138283** only (exclude demo/shadow). NEVER the backend's calculated
`entry_price`/`stop`/`pnl_usd` — those are the CLAIM being verified.

---
## TASKS (ordered — each unblocks the next)
- **T1 — Sierra reader.** Parse fills + TradeActivityLog → normalized event stream per live trade
  (keyed by the per-contract order_id chain). Pure/testable; no backend fields.
- **T2 — `sierra_ledger` builder.** Reconstruct each LIVE trade from its events ONLY: entry price,
  every stop MODIFY Sierra accepted (history), each exit fill, contracts, **realized P&L from the
  fill prices**, account, timestamps.
- **T3 — reconcile vs backend.** For each live trade, diff the Sierra ledger row against the backend
  DB row → flag EVERY differing field (stop · P&L · state · contracts) as a **CRITICAL divergence**
  (this is what catches L2 "stop recorded-moved but Sierra didn't" + L3 shadow-as-live).
- **T4 — manual-intervention detection.** A Sierra change the system did NOT initiate = MANUAL:
  · Sierra stop ≠ any stop the backend commanded → `MANUAL_STOP_MOVE from→to @ts`, adopt Sierra's stop.
  · Sierra flat but backend open → `MANUAL_CLOSE @price`, close the TM trade at Sierra's fill.
  Tag each event **MANUAL** vs **SYSTEM** in the trade audit + ledger. Never overwrite silently.
- **T5 — expose.** LIVE ledger endpoint/view = the Sierra numbers; divergences + MANUAL events
  flagged. The trader-facing live list reads THIS (not backend-synthesized).
- **T6 — L2 fold-in.** Verify `_emit_modify_stop`→`sc.ModifyOrder` actually reaches Sierra on a live
  stop-move (paste the Sierra modify line). (Separate design task, do NOT bundle: after-T1 stop
  trails to **STRUCTURE**, not BE.)

## TESTS (anti-tautological — each must FAIL on the current code)
1. **Ledger reconstruction** — fixture of Sierra fills (ENTRY 7536.25 → T1 7522 → STOP-modify → FLATTEN)
   → ledger reproduces entry, the stop-move history, exits, contracts **from fills alone**.
2. **P&L from Sierra fill** — ledger P&L uses fill prices; a test where fill ≠ intended level proves
   P&L follows the fill (fails if it reads the level).
3. **Reconcile divergence** — backend stop=7544.75, Sierra stop=7551 → CRITICAL divergence raised
   (fails on old = no reconcile).
4. **Manual stop-move** — Sierra stop at a price the backend never commanded → `MANUAL_STOP_MOVE`
   logged + record adopts Sierra's stop, tagged MANUAL.
5. **Manual close** — Sierra flat, backend PENDING/FILLED → `MANUAL_CLOSE` at Sierra fill + TM CLOSED,
   tagged MANUAL.
6. **MANUAL vs SYSTEM** — a system-initiated stop-move is tagged SYSTEM (fails if it mislabels a
   system move as manual).
7. **Live-account filter** — demo/shadow fills are excluded from the live ledger.

## VERIFICATION — ground-truth on the live/SIM system (raw Sierra evidence)
Copy each artifact into `docs/reports/evidence_2026-07-07/`; paste the command + output.
- **V1 round-trip** — one live/SIM trade: fire → paste the Sierra fills + the `sierra_ledger` row →
  they MATCH to the cent (entry · stop-history · exit · P&L).
- **V2 manual stop-move** — move the stop in Sierra by hand → within one cycle the system logs
  `MANUAL_STOP_MOVE` + the record shows Sierra's new stop. Paste the Sierra activity-log line + the log.
- **V3 manual close** — close/flatten in Sierra by hand → `MANUAL_CLOSE` at Sierra's price + TM CLOSED.
- **V4 reconcile** — aligned → MATCH; force a mismatch → CRITICAL divergence. Paste both.
- **V5 tagging** — the EOD ledger shows MANUAL vs SYSTEM events distinctly (learnable).

## Done = all 7 tests green + V1–V5 raw-verified on Sierra data + journal/board updated + NOT-DONE.
No real-money change beyond this without Michael's sign-off.
