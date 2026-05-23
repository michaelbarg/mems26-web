# Woodies CCI Pipeline Audit — 22 May 2026
Author: Claude Code (Wave 0 · READ-ONLY)
Mode: Audit only — no files modified

## Field-by-field flow

| Sierra Field | DLL Export | Bridge → Redis/API | Backend Endpoint | Frontend Renders | Status |
|---|---|---|---|---|---|
| CCI 14 (yellow line in Sierra, **black** in ours) | ✅ `cci_14` (v9_woodies_export.h:471) | ✅ full payload forwarded | ✅ `/woodies/chart` → `cci_14` | ✅ black line #000000, 2.5px | 🟡 COLOR MISMATCH |
| CCI 6 / TCCI (black line in Sierra, **yellow** in ours) | ✅ `cci_6_tcci` (line 472) | ✅ forwarded | ✅ returned | ✅ yellow line #DDDD20, 2.5px | 🟡 COLOR SWAP |
| LSMA-25 | ✅ `lsma_value` (line 473) | ✅ forwarded | ✅ returned | ❌ NOT rendered on chart | 🟡 PARTIAL |
| EMA-34 | ✅ `ema_34` (line 477) | ✅ forwarded | ✅ returned | ❌ NOT rendered on chart | 🟡 PARTIAL |
| Histogram bars (trend color) | ✅ `trend_state` BLUE/RED/YELLOW/GRAY (line 478) | ✅ forwarded | ✅ returned + color hex | ✅ rendered with correct colors | 🟢 OK |
| TrendUp / TrendDown / TrendNeutral | ✅ implied by `trend_state` | ✅ forwarded | ✅ returned | ✅ title bar shows active trend | 🟢 OK |
| CCIDiff H | ✅ `ccidiff_h` (HUD fields) | ✅ forwarded | ✅ returned | ✅ green row at y=56 | 🟢 OK |
| CCIDiff Mid | ✅ `ccidiff` (computed cci_14-tcci) | ✅ forwarded | ✅ returned | ✅ white row at y=88 | 🟢 OK |
| CCIDiff L | ✅ `ccidiff_l` (HUD fields) | ✅ forwarded | ✅ returned | ✅ magenta row at y=120 | 🟢 OK |
| CCI Predictor (H / L) | ✅ `predictor_cci_high`, `predictor_cci_low` | ✅ forwarded | ✅ returned | ✅ row at y=318 | 🟢 OK |
| ZLR markers | ✅ `zlr_detected`, `zlr_direction` (lines 480-481) | ✅ forwarded | ✅ returned | ✅ red/green triangles at ±200 | 🟢 OK |
| HFE markers | ✅ `hfe_detected`, `hfe_direction` (lines 482-483) | ✅ forwarded | ✅ returned | ❌ NOT rendered on chart | 🔴 MISSING |
| TLB markers | ❌ not in DLL | ❌ | ❌ | ❌ | 🔴 MISSING |
| Sidewinder (SWI) | ✅ `swi_value` (line 475) | ✅ forwarded | ✅ returned | ❌ NOT rendered on chart | 🟡 PARTIAL (data present, no visual) |
| ChopZone (CZI) | ✅ `czi_value` (line 476) | ✅ forwarded | ✅ returned | ❌ NOT rendered on chart | 🟡 PARTIAL (data present, no visual) |
| ±200 dotted lines (green/red) | N/A (UI only) | N/A | N/A | ✅ alternating dot pattern | 🟢 OK |
| ±100 dotted lines (cyan) | N/A (UI only) | N/A | N/A | ✅ alternating dot pattern | 🟢 OK |
| 0 line (green) | N/A (UI only) | N/A | N/A | ✅ alternating dot pattern | 🟢 OK |
| ProjHigh / ProjLow | ✅ `proj_hi`, `proj_lo` (Sierra Study ID:9) | ✅ forwarded | ✅ returned (carry-forward for current bar) | ✅ cyan/magenta rows at y=262/290 | 🟡 VALUES DIFFER (per-bar pivot ≠ Sierra daily proj) |
| High / Low readouts | ✅ `ohlc.h`, `ohlc.l` + prev_ohlc | ✅ forwarded | ✅ returned | ✅ green/black rows at y=156/232 | 🟢 OK |
| Last price | ✅ `ohlc.c` | ✅ forwarded | ✅ returned | ✅ large black text at y=192 | 🟢 OK |
| Low Prev/Cur angle | ✅ `low_prev_angle` | ✅ forwarded | ✅ returned | ✅ row at y=346 | 🟢 OK |
| Trend badge ("9 L E") | ✅ `trend_state` + bar count | ✅ forwarded | ✅ returned | 🟡 title bar shows CCI + trend, not "9 L E" format | 🟡 FORMAT DIFF |

## Visual rendering diff

| Sierra Visual | Frontend Visual | Diff Severity |
|---|---|---|
| Yellow CCI 14 line (thick) | **Black** CCI 14 line (2.5px) | 🟡 COLOR SWAP — Sierra=yellow, ours=black |
| Black CCI 6 / TCCI line (thin) | **Yellow** CCI 6 / TCCI line (2.5px) | 🟡 COLOR SWAP — Sierra=black, ours=yellow |
| Blue/grey/gold histogram | Blue/red/yellow/grey histogram | 🟢 CLOSE (Sierra uses blue for trend, we match) |
| Cyan dotted ±100 lines | Cyan alternating dots ±100 | 🟢 OK |
| Green/red dotted ±200 lines | Red/green alternating dots ±200 | 🟢 OK |
| Green triangle ZLR markers below -200 | Green up / Red down at ±200 | 🟢 OK |
| Right-side: CCIDiff H/Mid/L | Right-side: diff-g/diff-w/diff-m | 🟢 OK |
| Right-side: "7811.00 Pr" / "7210.75 Pr" | Right-side: per-bar pivot proj (7511.25 / 7505.75) | 🟡 VALUES DIFFER — Sierra uses daily pivot, DLL history uses per-bar |
| Trend badge: "9 L E" | Title shows CCI value + trend state | 🟡 FORMAT DIFF |
| Y-axis: ±250 default | Y-axis: ±299 default | 🟡 SCALE DIFF |

## Summary

- Total Sierra fields: **22**
- ✅ Flowing 100%: **14** (histogram, trend, CCIDiff H/M/L, predictor, ZLR, ref lines, High/Low/Last, angle)
- 🟡 Partial (data present, visual gap): **6** (CCI14/TCCI color swap, LSMA not drawn, EMA not drawn, SWI/CZI not drawn, proj values differ, trend badge format, Y-scale)
- 🔴 Missing entirely: **2** (HFE markers not rendered, TLB markers not in DLL)

## Recommended fix order (P0 → P3)

**P0: CCI14/TCCI color swap (highest visual impact)**
- Sierra: CCI14 = yellow (thick), TCCI = black (thin)
- Ours: CCI14 = black, TCCI = yellow — **swapped**
- Fix: swap `COLORS.CCI_14` and `COLORS.TCCI` in `woodiesDesignerSpec.ts`
- LOC: 2 lines
- Impact: Immediate visual parity for the two main lines

**P1: proj_hi/proj_lo values (Sierra daily pivot vs per-bar pivot)**
- Sierra shows ~7811/7210 (daily range projections from Woodies Panel study)
- Our history bars compute per-bar pivots (7511/7505) — wrong
- current_bar gets Sierra values correctly (Study ID:9 SG1/SG2) but they're often null
- Fix: revert per-bar pivot formula in DLL history, rely on Sierra values via carry-forward
- LOC: ~5 lines (remove added code in v9_woodies_export.h)

**P2: HFE markers (data exists, just not rendered)**
- `hfe_detected` and `hfe_direction` flow through the entire pipeline
- Frontend has no visual rendering for them
- Fix: add HFE triangle/marker in `drawContentCanvas` similar to ZLR
- LOC: ~20 lines

**P3: Styling and polish**
- Y-axis default scale: ±299 → ±250 to match Sierra
- Trend badge format: show "N L E" (bar count + L/S + Entry) like Sierra
- Optionally render LSMA/EMA/SWI/CZI as subtle overlays (Sierra shows them in the panel but they're secondary)

## Notes

- **No WebSocket endpoint for Woodies** — panel polls at 15s (should be 5s per CLAUDE.md)
- **Polling interval discrepancy**: WoodiesCciPanel polls at 15000ms but CLAUDE.md "Frontend Polling Floors" table says 5000ms
- **Bridge forwards ALL fields** — no data loss between DLL and backend
- **D-074 locked**: Woodies 5-min is primary S4 source (not 30-min)
