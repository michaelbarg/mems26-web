# V9 DLL Changes — MES_AI_DataExport

## Version: v3.0 → v9.0.0

## New Files
- `sc_study/v9_types.h` — Shared types, ACSIL-safe helpers (v9_max/min/abs), JSON helpers
- `sc_study/v9_exports.h` — All 7 new export functions

## New Exports (7)

| # | Export | File | Description |
|---|--------|------|-------------|
| 1 | Tick Reversal 15-tick | `tick_reversal_15.json` | Reversal bars built from chart data, 15-tick reversal threshold |
| 2 | Tick Reversal 12-tick | `tick_reversal_12.json` | Same logic, 12-tick threshold |
| 3 | Footprint | `footprint.json` | Bid×Ask per price level per bar, uses VolumeAtPriceForBars |
| 4 | Volume Profile | `volume_profile.json` | POC/VAH/VAL per bar with level breakdown |
| 5 | Imbalance Flags | `imbalance_flags.json` | All levels with 250%+ bid/ask ratio |
| 6 | Stacked Imbalances | `stacked_imbalances.json` | Bars with 3+ consecutive imbalances |
| 7 | Cumulative Delta | `cumulative_delta.json` | Running delta with divergence detection |

## Output Directory
`C:\SierraChart_Data\v9_export\` (configurable via Input[4])

## New Inputs

| Input | Name | Default | Description |
|-------|------|---------|-------------|
| Input[4] | V9 Export Directory | `C:\SierraChart_Data\v9_export\` | Output path for v9 files |
| Input[5] | V9 Tick Reversal 15-tick | 1 (on) | Enable/disable 15-tick reversal export |
| Input[6] | V9 Tick Reversal 12-tick | 1 (on) | Enable/disable 12-tick reversal export |
| Input[7] | V9 Lookback Bars | 200 | How many chart bars to analyze for reversal/delta |

## ACSIL Compliance
- `std::max/min` replaced with `v9_max/v9_min` (Sierra macros conflict)
- `std::abs` replaced with `v9_abs`
- `sc.MaintainVolumeAtPriceData = 1` set in defaults for footprint support
- `@idempotent` not applicable (no SC order mutations)
- Uses `s_VolumeAtPriceV2` API for real per-level data when available

## Existing Exports (unchanged)
All v3.0 exports remain identical:
- MTF (3/15/30/60 min bars)
- CVD + divergence
- VWAP + pullback
- Market Profile (POC/VAH/VAL)
- Woodi Pivots
- Session levels (72H/Weekly/PrevDay)
- Imbalance detection (bar-level)
- Absorption + Liquidity Sweep

## JSON Schema Samples

### tick_reversal_15.json
```json
{
  "type": "tick_reversal",
  "tick_count": 15,
  "version": "v9.0.0",
  "bar_count": 42,
  "bars": [
    {"idx":0,"o":5412.50,"h":5415.00,"l":5410.25,"c":5411.00,
     "vol":1234,"ask_vol":700,"bid_vol":534,"delta":166,"dir":1,"ts":1746806400}
  ]
}
```

### footprint.json
```json
{
  "type": "footprint",
  "version": "v9.0.0",
  "bar_count": 30,
  "cumulative_delta": 4521.00,
  "bars": [
    {"idx":170,"o":5412.50,"h":5413.25,"l":5411.75,"c":5412.75,
     "vol":856,"delta":122,"poc_price":5412.50,"poc_vol":234,
     "stacked_buy":0,"stacked_sell":0,
     "levels": [
       {"p":5411.75,"bid":45,"ask":120,"d":75,"ib":true,"is":false}
     ]}
  ]
}
```

### imbalance_flags.json
```json
{
  "type": "imbalance_flags",
  "version": "v9.0.0",
  "total_buy_imbalances": 12,
  "total_sell_imbalances": 8,
  "bars_with_imbalances": 15,
  "bars": [
    {"bar_idx":175,"price":5412.75,"stacked_buy":3,"stacked_sell":0,
     "levels": [
       {"p":5412.50,"bid":30,"ask":250,"ratio":8.33,"side":"BUY"}
     ]}
  ]
}
```
