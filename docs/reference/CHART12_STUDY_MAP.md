# Chart #12 Study Map — MESM26_FUT_CME[M] 5 Min #12

**Source:** Michael's Sierra screenshots, verified 2026-06-02.
**Purpose:** Definitive subgraph mapping for DLL `GetStudyArrayFromChartUsingID(12, studyID, subgraphIdx, arr)`.

ACSIL subgraph index = Sierra UI SG# minus 1.

---

## Study List (Chart #12)

| # | ID | Name | Latency | CalcOrder | S_ID |
|---|-----|------|---------|-----------|------|
| 1 | ID:1 | Woodies CCI Trend | 4 ms | 1 | 203 |
| 2 | ID:2 | Moving Average - Linear Regression | 1 ms | 2 | — |
| 3 | ID:3 | Woodies EMA | 0 ms | 3 | 145 |
| 4 | ID:4 | Commodity Channel Index | 1 ms | 4 | — |
| 5 | ID:5 | LSMA Above/Below Last | 1 ms | 5 | — |
| 6 | ID:6 | Sidewinder | 3 ms | 6 | 144 |
| 7 | ID:7 | Chop Zone | 1 ms | 7 | 143 |
| 8 | ID:9 | Woodies Panel | 0 ms | 12 | 202 |
| 9 | ID:8 | CountDown Timer | 0 ms | 8 | 201 |
| 10 | ID:10 | Commodity Channel Index | 0 ms | 9 | — |
| 11 | ID:11 | CCI Predictor | 1 ms | 10 | 206 |
| 12 | ID:12 | Pivot Points-Daily | 4 ms | 11 | 87 |
| 13 | ID:13 | Woodies ZLR System | 2 ms | 13 | — |

---

## Study ID:1 — Woodies CCI Trend (S_ID: 203)

| Sierra SG | ACSIL idx | Name | Draw Style | DLL reads? | Notes |
|-----------|-----------|------|------------|------------|-------|
| SG1 | 0 | CCI | Bar | — | Raw CCI value |
| SG2 | 1 | TrendDown | Bar | ✅ `(wc, 1, 1, s_trend_down_arr)` | Non-zero when downtrend (RED) |
| SG3 | 2 | TrendNeutral | Bar | ✅ `(wc, 1, 2, s_trend_neutral_arr)` | Non-zero when neutral (GRAY) |
| SG4 | **3** | **TrendUp** | Bar | ✅ `(wc, 1, 3, s_trend_up_arr)` | Non-zero when uptrend (BLUE) |
| SG5 | 4 | Hi Level | Ignore | — | +100/+200 reference line |
| SG6 | 5 | Low Level | Ignore | — | -100/-200 reference line |
| SG9 | 8 | Spreadsheet Output | Ignore | — | — |
| SG10 | 9 | ZLR Output | — | — | — |

**FIXED v9.4.5:** TrendUp moved from ACSIL 0 (was CCI value) → ACSIL 3 (correct TrendUp).

---

## Study ID:2 — Moving Average - Linear Regression (LSMA)

| Sierra SG | ACSIL idx | Name | Draw Style | DLL reads? | Notes |
|-----------|-----------|------|------------|------------|-------|
| SG1 | 0 | Avg | Line | ✅ `(wc, 2, 0, s_lsma25_arr)` | LSMA-25 value |

DLL reads: `sc.GetStudyArrayFromChartUsingID(wc, 2, 0, s_lsma25_arr)` — **correct** (SG1 = ACSIL 0).

---

## Study ID:3 — Woodies EMA (S_ID: 145)

| Sierra SG | ACSIL idx | Name | Draw Style | DLL reads? | Notes |
|-----------|-----------|------|------------|------------|-------|
| SG1 | 0 | EMA | Point | ✅ `(wc, 3, 0, s_ema34_arr)` | EMA-34 value |
| SG2 | 1 | Up / Down Color | Ignore | — | Color indicator |

DLL reads: `sc.GetStudyArrayFromChartUsingID(wc, 3, 0, s_ema34_arr)` — **correct** (SG1 = ACSIL 0).

---

## Study ID:4 — Commodity Channel Index (CCI-14)

| Sierra SG | ACSIL idx | Name | Draw Style | DLL reads? | Notes |
|-----------|-----------|------|------------|------------|-------|
| SG1 | 0 | CCI | Line | ✅ `(wc, 4, 0, s_cci14_arr)` | CCI-14 value |
| SG2 | 1 | Line 1 | Hidden | — | Reference line |
| SG3 | 2 | Line 2 | Line | — | Reference line |
| SG4 | 3 | Line 3 | Line | — | Reference line |

DLL reads: `sc.GetStudyArrayFromChartUsingID(wc, 4, 0, s_cci14_arr)` — **correct** (SG1 = ACSIL 0).

---

## Study ID:5 — LSMA Above/Below Last

| Sierra SG | ACSIL idx | Name | Draw Style | DLL reads? | Notes |
|-----------|-----------|------|------------|------------|-------|
| SG1 | 0 | Above/Below | Square | — | Visual indicator (green/red) |
| SG3 | 2 | Spreadsheet Output | Ignore | — | — |

DLL does NOT read this study directly. LSMA value comes from Study ID:2.

---

## Study ID:6 — Sidewinder (S_ID: 144)

| Sierra SG | ACSIL idx | Name | Draw Style | DLL reads? | Notes |
|-----------|-----------|------|------------|------------|-------|
| SG1 | 0 | SW Top | Square | — | Upper boundary |
| SG2 | 1 | SW Bottom | Square | — | Lower boundary |
| SG3 | 2 | Flat Color | Ignore | — | Visual color indicator |
| SG4 | 3 | Output for Spreadsheets | Ignore | — | Possibly the actual SWI value |

**BUG:** DLL reads `(wc, 6, 5, s_swi_arr)` — ACSIL idx 5 does NOT exist (only 0-3).
Debug dump showed SG4=100.0, SG5=-100.0 from Study ID:1 — those are Hi/Low Level lines, not SWI.
**FIX NEEDED:** Determine which SG holds the actual Sidewinder value (likely SG4/ACSIL 3 = Spreadsheets output, or SG1/ACSIL 0 = SW Top).

---

## Study ID:7 — Chop Zone (S_ID: 143)

| Sierra SG | ACSIL idx | Name | Draw Style | DLL reads? | Notes |
|-----------|-----------|------|------------|------------|-------|
| SG1 | 0 | CZI Top | Square | — | Upper boundary |
| SG2 | 1 | CZI Bottom | Square | — | Lower boundary |
| SG3 | 2 | Output for Spreadsheets | Ignore | ✅ `(wc, 7, 2, s_czi_arr)` | Numeric CZI value |
| SG5 | 4 | Down Colors 1 & 2 | Ignore | — | Visual |
| SG6 | 5 | Down Color 3 | Ignore | — | Visual |

DLL reads: `sc.GetStudyArrayFromChartUsingID(wc, 7, 2, s_czi_arr)` — ACSIL idx 2 = Spreadsheet Output. Likely correct (numeric value).

---

## Study ID:8 — CountDown Timer (S_ID: 201)

| Sierra SG | ACSIL idx | Name | Draw Style | DLL reads? | Notes |
|-----------|-----------|------|------------|------------|-------|
| SG1 | 0 | CountDown | Custom Text | — | Not read by DLL |

---

## Study ID:9 — Woodies Panel (S_ID: 202)

| Sierra SG | ACSIL idx | Name | Draw Style | DLL reads? | Notes |
|-----------|-----------|------|------------|------------|-------|
| SG1 | 0 | CCIDiff | Custom Text | — | CCI14 - TCCI difference |
| SG2 | 1 | Projected Buy | Custom Text | ✅ `(wc, 9, 1, s_proj_hi_arr)` | Projected entry (long) |
| SG3 | 2 | Projected Sell | Custom Text | ✅ `(wc, 9, 2, s_proj_lo_arr)` | Projected entry (short) |
| SG4 | 3 | CCI Pred. H/L | Custom Text | — | Predictor high/low |
| SG5 | 4 | Background Colors | Custom Text | — | Visual |
| SG6 | 5 | CCIDiff H | Custom Text | — | CCIDiff high |
| SG7 | 6 | CCIDiff L | Custom Text | — | CCIDiff low |
| SG8 | 7 | High Prev/Cur | Custom Text | — | Previous/Current high |
| SG9 | 8 | Last Prev/Cur | Custom Text | — | Previous/Current last |
| SG10 | 9 | Low Prev/Cur | Custom Text | — | Previous/Current low |
| SG11 | 10 | EMA Angle | Custom Text | — | EMA angle value |

DLL reads: `(wc, 9, 1)` = Projected Buy, `(wc, 9, 2)` = Projected Sell. Mapped to proj_hi / proj_lo. Semantically correct (Buy=high target, Sell=low target).

---

## Study ID:10 — Commodity Channel Index (CCI-6 / TCCI)

| Sierra SG | ACSIL idx | Name | Draw Style | DLL reads? | Notes |
|-----------|-----------|------|------------|------------|-------|
| SG1 | 0 | CCI | Line | ✅ `(wc, 10, 0, s_cci6_arr)` | TCCI / CCI-6 value |
| SG2 | 1 | Line 1 | Hidden | — | Reference line |
| SG3 | 2 | Line 2 | Hidden | — | Reference line |
| SG4 | 3 | Line 3 | Hidden | — | Reference line |

DLL reads: `sc.GetStudyArrayFromChartUsingID(wc, 10, 0, s_cci6_arr)` — **correct** (SG1 = ACSIL 0).

---

## Study ID:11 — CCI Predictor (S_ID: 206)

| Sierra SG | ACSIL idx | Name | Draw Style | DLL reads? | Notes |
|-----------|-----------|------|------------|------------|-------|
| SG1 | 0 | CCI Proj High | Arrow Down | ✅ `(wc, 11, 0, s_pred_hi_arr)` | Projected CCI high |
| SG2 | 1 | CCI Proj Low | Arrow Up | ✅ `(wc, 11, 1, s_pred_lo_arr)` | Projected CCI low |

DLL reads: `(wc, 11, 0)` and `(wc, 11, 1)` — **correct**.

---

## Study ID:12 — Pivot Points-Daily (S_ID: 87)

33 subgraphs total. Key ones:

| Sierra SG | ACSIL idx | Name | Draw Style | Notes |
|-----------|-----------|------|------------|-------|
| SG1 | 0 | R1 | Dash/Solid | Resistance 1 |
| SG2 | 1 | R2 | Dash/Solid | Resistance 2 |
| SG3 | 2 | S1 | Dash/Solid | Support 1 |
| SG4 | 3 | S2 | Dash/Solid | Support 2 |
| SG5 | 4 | R.5 | Hidden | — |
| SG6 | 5 | R1.5 | Hidden | — |
| SG7 | 6 | R2.5 | Hidden | — |
| SG8 | 7 | R3 | Dash/Solid | Resistance 3 |
| SG9 | 8 | S.5 | Hidden | — |
| SG10 | 9 | S1.5 | Hidden | — |
| SG11 | 10 | S2.5 | Hidden | — |
| SG12 | 11 | S3 | Dash/Solid | Support 3 |
| SG13 | 12 | **PP** | Dash/Solid | Pivot Point |
| SG14 | 13 | **PP High** | Hidden | Daily projected high |
| SG15 | 14 | **PP Low** | Hidden | Daily projected low |
| SG16 | 15 | R4 | Ignore | — |
| SG17 | 16 | S4 | Line | — |
| SG18-33 | 17-32 | R3.5, S3.5, R5-R10, S5-S10, R4_5, S4_5 | Line | Extended levels |

DLL reads in debug dump only. Production proj_hi/proj_lo come from Study ID:9 (Woodies Panel SG2/SG3).
Pivot Points also available via `ProjHLStudyID` input if configured.

---

## Study ID:13 — Woodies ZLR System

| Sierra SG | ACSIL idx | Name | Draw Style | DLL reads? | Notes |
|-----------|-----------|------|------------|------------|-------|
| SG1 | 0 | Long Trade | Arrow Up | — | ZLR long signal |
| SG2 | 1 | Short Trade | Arrow Down | — | ZLR short signal |
| SG3 | 2 | Chopzone Average | Ignore | — | CZI average |

DLL does NOT read this study. ZLR detection is computed locally in `v9_detect_zlr()`.

---

## DLL Code Reference

File: `sc_study/v9_woodies_export.h`

### Current bar (MES_AI_DataExport.cpp lines 588-632)
Uses `W_LAST(arr)` — reads LAST element of chart 12's arrays. Correct for live value.

### History bars (v9_woodies_export.h lines 436-455)
Uses `mapIdx(bars[bi].chart_bar_start)` — cross-chart datetime mapping.

### Debug dump (v9_woodies_export.h lines 684-720)
⚠️ Uses raw `bars[ci].chart_bar_start` (HOST index) — reads WRONG position in chart 12 arrays.
Must fix to use W_LAST or mapped index.
