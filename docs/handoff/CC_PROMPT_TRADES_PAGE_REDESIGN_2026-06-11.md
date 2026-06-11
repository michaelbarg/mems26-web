# CC Prompt — Trades Page Redesign for Daily Workflow (2026-06-11)

**Contract:** `docs/handoff/CC_HANDOFF_CONTRACT.md` — NOT-DONE section mandatory, raw
evidence per claim, anti-tautological tests. Frontend only — NO trading-logic changes.
**Audit existing surfaces first** (CLAUDE.md): classify current components
KEEP / ADAPT / REPLACE before writing anything new. Reference report formats Michael
approved: `docs/reports/TRADES_VISUAL_2026-06-11.html` (per-trade chart) and
`docs/reports/MEMS26_TRADE_TRACKER_2026-06-11.xlsx` (per-trade audit columns).

## Goal (Michael)

The Trades page must answer, per trade, at a glance — without leaving the page:
1. **Price chart per trade** (candles or close-line) around the trade window with
   markers: entry, initial stop, final stop, T1/T2/T3 anchors, exit, and a vertical
   marker where SMART_BE moved the stop. Like `TRADES_VISUAL_2026-06-11.html` but live.
2. **Risk in points** (entry ↔ initial stop) — prominent column, color-scaled
   (green <10, yellow 10–25, red >25).
3. **Stop behavior**: did T1 hit, did stop move to BE (from `v9_trade_management_log`),
   final exit at BE vs full stop.
4. **Where the anchors were set**: T1 value + its R-multiple, T2/T3 (or "—" Option 1),
   stop anchor source if available.
5. **Capture quality**: MFE pts vs captured pts (what % of the move we kept).
6. **Spec flags** per trade: shared-anchor cluster (same initial stop as another trade
   same session), risk outside [2,60], re-entry after stop-out same pattern+direction.

## Current components (audit, then ADAPT — do not duplicate)

- `TradesView.tsx` — container; `TradeCardList.tsx` — rows; `TradePathVisual.tsx` —
  existing per-trade visual (likely ADAPT into the chart); `TradeRowExpand.tsx` /
  `SelectedTradePanel.tsx` — expansion panels; `tradeStore.ts` — filters.
- Data: `/api/v9/trades` already returns mfe_pts, mae_pts, stop_initial, contracts_pnl,
  bars_count. Mgmt log needs an endpoint or embedding (check if exists first; if a new
  endpoint is required — read-only, token-guarded like /trades).
- Bars for the chart: `/api/v9/bars/woodies` exists. Slice client-side by trade window.

## Requirements

- Keep polling floors (CLAUDE.md §Frontend Polling Floors) — no new aggressive polling.
- RTL-friendly Hebrew labels where the page already uses them.
- Default sort: newest first. Quick filters: today / pattern / system / wins / losses /
  open. Summary strip on top: N, Win%, PF, Net$, avg risk, biggest loss.
- Expanded row = chart + mgmt-log timeline (T1_HIT → SMART_BE → exit) + spec flags.
- Performance: lazy-render charts (only expanded rows), no chart for collapsed rows.
- Tests: component render test with a fixture trade incl. mgmt log; regression test that
  collapsed list doesn't fetch bars.

## NOT-DONE / Out of scope

- No changes to backend trading logic, gates, or trade_manager.
- No new write endpoints.
- Do not touch `sc_study/`, bridge, or market-data routes (§7a).

## Report

`docs/reports/TRADES_PAGE_REDESIGN_<date>.md` + screenshot-after (Rule: verify the fix
touches the culprit — paste the diff file list + screenshot). Update boards per protocol.
