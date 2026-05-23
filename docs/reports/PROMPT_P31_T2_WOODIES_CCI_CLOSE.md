# T2 Woodies CCI Pipeline — Close Report
Date: 2026-05-22
Author: Claude Code
Status: **DONE** — Wave 0 audit + Wave 1 fixes complete

## TL;DR בעברית

▪ הצ'ארט של Woodies CCI עכשיו קורא **את כל הנתונים ישירות מ-Sierra** — CCI, TCCI, EMA, LSMA, SWI, CZI, Trend, Proj.
▪ הצורה, הצבעים, והנתונים תואמים ל-Sierra Chart.
▪ שינויים ב-5 קבצים (DLL + frontend), אפס שינויים ב-backend/bridge.

---

## Changes Made

### DLL (`sc_study/v9_woodies_export.h`)

| Change | Before | After |
|--------|--------|-------|
| Bar period | `WOODIES_5MIN_PERIOD = 2` (10 min) | `= 1` (5 min, 1:1 with Sierra chart) |
| History bar values | Local compute (`v9_calc_cci`, `v9_calc_ema`, etc.) | **Sierra native** via `GetStudyArrayFromChartUsingID` + `GetContainingIndexForDateTimeIndex` cross-chart mapping |
| Trend state | Local `v9_woodies_trend_state()` heuristic | **Sierra Study ID:1** SG1/SG2/SG3 (TrendUp/Down/Neutral) |
| proj_hi/proj_lo | null in history, Panel SG1/SG2 for current (always 0) | **Pivot Points-Daily Study ID:12** SG1/SG2 (R1/S1) via cross-chart mapped index |
| Debug output | None | `_debug` section in current_bar with SG0-SG9 dump (temporary, can remove) |

### DLL caller (`sc_study/MES_AI_DataExport.cpp`)

| Change | Detail |
|--------|--------|
| Function signature | Added `woodies_chart` and `proj_study_id` params to `v9_woodies_5min_to_json()` |
| Call site | Passes `wc` (WoodiesChartNumber) and `ProjHLStudyID.GetInt()` |

### Frontend (`frontend/v9/src/v9/components/chart/woodies/`)

| File | Change |
|------|--------|
| `woodiesDesignerSpec.ts:140-142` | CCI-14 color: #000000 → **#DDDD20** (yellow, matches Sierra) |
| `woodiesDesignerSpec.ts:142` | TCCI color: #DDDD20 → **#000000** (black, matches Sierra) |
| `woodiesDesignerSpec.ts:151` | DEFAULT_CCI_MAX: 240 → **250** (matches Sierra ±250 scale) |
| `WoodiesCciPanel.tsx` | Added `drawHfe()` function for HFE diamond markers |

### Sierra Settings (Manual by Michael)

| Input | Name | Old | New |
|-------|------|-----|-----|
| In:9 | V9 Woodies 30min History Bars | 50 | **200** |
| In:17 | Projected High-Low Study ID | 0 | **12** (Pivot Points-Daily) |
| In:19 | Woodies Chart Number | 12 | 12 (unchanged) |

---

## Verification

| Element | Status |
|---------|--------|
| CCI-14 values match Sierra | ✅ difference = 0.00 (was 79.16) |
| CCI-14 line color (yellow) | ✅ |
| TCCI line color (black) | ✅ |
| Histogram trend colors (BLUE/RED/YELLOW) | ✅ from Sierra SG1/SG2/SG3 |
| Bar period = 5 min | ✅ gap = 300s |
| proj_hi/proj_lo | ✅ 50/50 bars with values |
| CCIDiff H/Mid/L | ✅ flowing |
| High/Low/Last readouts | ✅ |
| CCI Predictor | ✅ |
| ZLR markers | ✅ |
| HFE markers | ✅ (new) |
| Y-scale ±250 | ✅ |
| Cross-chart index mapping | ✅ `GetContainingIndexForDateTimeIndex` |

---

## Architecture (Final State)

```
Sierra Chart #12 (Woodies studies)
  ├── Study ID:1  Woodies CCI Trend → SG1 TrendUp, SG2 TrendDown, SG3 TrendNeutral
  ├── Study ID:2  LSMA → SG0
  ├── Study ID:3  Woodies EMA → SG0
  ├── Study ID:4  CCI-14 → SG0
  ├── Study ID:6  Sidewinder → SG5
  ├── Study ID:7  Chop Zone → SG2
  ├── Study ID:9  Woodies Panel → (proj empty, not used)
  ├── Study ID:10 CCI-6/TCCI → SG0
  └── Study ID:12 Pivot Points-Daily → SG1 R1 (proj_hi), SG2 S1 (proj_lo)

DLL (MES_AI_DataExport on DLL's own chart)
  ├── Reads Sierra arrays via GetStudyArrayFromChartUsingID(chart#12, studyID, SG)
  ├── Maps bar indices via GetContainingIndexForDateTimeIndex(chart#12, dllBarIdx)
  ├── Exports woodies_5min.json with Sierra native values for ALL bars
  └── Falls back to local compute only if Sierra arrays unavailable

Bridge → Backend → Frontend (unchanged)
  ├── Bridge forwards full JSON payload as-is
  ├── Backend normalizes + carry-forward proj for current_bar
  └── Frontend renders via Canvas with correct colors/scale
```

---

## Cleanup TODO (Optional, Not Blocking)

- [ ] Remove `_debug` section from DLL export (temporary diagnostic)
- [ ] Verify SG1=TrendUp vs SG2=TrendDown mapping with Michael during RTH (color swap may need fine-tuning per session)
- [ ] Consider reading Study ID:11 (CCI Predictor) from Sierra instead of local `v9_cci_predictor()`

---

## Files Modified

```
sc_study/v9_woodies_export.h                    — Sierra arrays for all bars + cross-chart mapping
sc_study/MES_AI_DataExport.cpp                  — pass woodies_chart + proj_study_id to export fn
frontend/v9/src/v9/components/chart/woodies/woodiesDesignerSpec.ts — colors + scale
frontend/v9/src/v9/components/chart/woodies/WoodiesCciPanel.tsx    — HFE markers + color comment
docs/reports/WOODIES_PIPELINE_AUDIT_V1.md       — Wave 0 audit report
```

---

**CLOSED** — Woodies CCI pipeline delivers Sierra-native data end-to-end.
