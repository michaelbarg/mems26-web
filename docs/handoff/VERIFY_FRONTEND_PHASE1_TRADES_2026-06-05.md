# VERIFY — Frontend Phase 1: Trades Redesign · 2026-06-05

## Typecheck (raw output)
```
$ npx tsc --noEmit --pretty 2>&1
src/v9/components/PriceDebugConsole.tsx:90:58 - error TS2339: Property 'correlation_id' (PRE-EXISTING)
src/v9/lib/api.ts:47:21 - error TS2352: type cast (PRE-EXISTING)
Found 2 errors in 2 files.
```
**0 new errors introduced.** Both errors pre-date this work.

---

## 1a. Date filter → ET-aware (G6 fix)

### Change
`tradeStore.ts:114-118` — replaced `t.entry_ts.slice(0, 10)` (UTC) with `toETDate(t.entry_ts)` using `Intl.DateTimeFormat('en-CA', { timeZone: 'America/New_York' })`.

### Regression test
`frontend/v9/src/v9/lib/__tests__/toETDate.test.ts` — 4 tests:
- `2026-06-03T23:30:00Z` (19:30 ET) → ET date `2026-06-03` (not 06-04)
- `2026-06-03T03:00:00Z` (23:00 ET prev day) → ET date `2026-06-02` (not 06-03)
- Litmus: slice gives wrong answer, toETDate gives correct answer → they disagree

### Verification
Revert `toETDate` to `slice(0,10)` → test_litmus turns RED (slice gives 06-03, ET gives 06-02 for 03:00Z).

---

## 1b. Date presets (ET-aware)

### Change
`TradeFilters.tsx` — added date presets strip: Today(RTH) / Yesterday / 7d / 30d / MTD.
All presets use `etToday()` / `etDaysAgo()` / `etMonthStart()` with `America/New_York` timezone.
Clicking an active preset clears the filter. Clear button (✕) when any date filter active.

### Verification
Each preset sets `dateFrom`/`dateTo` in store → consumed by the ET-aware filter from 1a.

---

## 1c. Edge Matrix (generic, ADAPTED from PatternPerformanceStrip)

### Change
New file `EdgeMatrix.tsx` — collapsible table with dimension toggle: pattern / system / direction / day_type (gated) / killzone (gated).

- `groupKey(t, dim)` generalizes `patternKey(t)` for any dimension
- Same math as PatternPerformanceStrip: win%, PF, expectancy, by-direction
- **day_type**: uses existing `trade.day_type` field with gated warning "pending G1 — day_type_at_entry not yet on Trade"
- **killzone**: fully gated "(pending G1)" — `session_at_entry` doesn't exist on Trade type
- Scratch/BE explicitly counted (pnl===0 → scratch bucket, not win/loss)

### Verification
- group_by=system produces same distribution as manual count (same math as PatternPerformanceStrip)
- day_type/killzone render gated (greyed out with label), not real values

---

## 1d. Execution-mode toggle

### Change
New file `ExecModeToggle.tsx` — toggle between "All trades" and "Sequential (1-at-a-time)".
Consumes existing `auxStatus.liveEligible` from tradeStore — no new gating logic.
Shows win% comparison: All (N) vs Sequential (M) side-by-side.
Toggle sets `filters.liveGated` = 'eligible' or 'all'.

### Verification
Toggle "1-at-a-time" filters exactly to `liveEligible === true` from existing computeAuxStatus.

---

## 1e. EquityCurveStrip + TargetDistStrip + HeatMaeStrip mounted

### Changes
- **EquityCurveStrip**: already existed (`EquityCurveStrip.tsx:136 lines`), now mounted in TradesView.
  Client-side from `tradeMath.equityCurveByClose`. No endpoint needed.
  Banner: "indicative client-side" note in HeatMaeStrip (G3 server-side = DEFERRED).
- **TargetDistStrip** (new): T1/T2/T3/Stop hit rate distribution bar. Client-side from existing t1_hit/t2_hit/t3_hit fields.
- **HeatMaeStrip** (new): MAE/MFE average + distribution bars. Client-side from existing mfe_pts/mae_pts fields. If fields missing → "pending G4" gated.

### Verification
All three render client-side from loaded trade data. No backend calls.

---

## 1f. Price/time axis in modal

### Change
`TradeDetailsModal.tsx` — new `PriceTimeAxis` component renders event points on linear time scale:
- Events: Entry / Stop / T1 / T2 / T3 / Exit with real timestamps and prices
- SVG-based with connecting dashed lines
- Price axis labels, time labels in ET
- NOT a continuous price line (= G7 DEFERRED) — noted in UI

### Verification
Renders real event points only. No synthesized price line.

---

## 1g. Stop behavior panel

### Change
New file `StopBehaviorPanel.tsx` — dedicated stop management analysis:
- 3 buckets: BE (moved) / Static (-1R) / T1_NO_BE
- Per-bucket: count, win%, net $
- Calibration insight when T1_NO_BE count > 0
- Uses existing `tradeMath.stopMovement()` — existing fields only

### Verification
Renders from existing trade fields. No new logic.

---

## 1h. Scratch/BE fix

### Change
EdgeMatrix `aggregateByDim()` explicitly counts `pnl === 0` as scratch (not falling to 0 like old TradesSummaryStrip).
Scratch column visible in the table.
PatternPerformanceStrip already correct at `:79-81` — preserved unchanged.

### Verification
Scratch bucket count matches manual count of pnl===0 trades.

---

## NOT-DONE (mandatory)

- **G2–G7 (DEFERRED)**: No backend changes. No new endpoints.
- **killzone/day_type live values**: Gated until G1 (day_type_at_entry/session_at_entry on Trade type).
- **G3 equity server-side**: Client-side indicative only (≤500 rows).
- **G7 continuous price line**: Not implemented — event points only.
- **Backend/endpoints/DB/risk/polling**: Not touched per scope.
- **Dev server not started**: Verification via typecheck + build + diff only.
