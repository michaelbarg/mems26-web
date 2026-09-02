# Post-Mortem: Trade #1

| Field | Value |
|-------|-------|
| Mode | demo |
| Direction | LONG |
| System | S<MagicMock name='mock.query().filter().first().firing_system' id='140317031665472'> |
| Entry | 7500.0 @ <MagicMock name='mock.query().filter().first().entry_ts' id='140317031115648'> |
| Exit | 7492.0 @ 2026-07-06 15:30:00+00:00 |
| Stop | 7493.0 |
| PnL | $-120.0 (-1.14R) |
| Exit Reason | STOP_HIT |

## Day Type
- At entry: **<MagicMock name='mock.query().filter().first().day_type_at_entry' id='140317031055120'>**
- EOD truth: **UNKNOWN**
- Mismatch: NO

## Excursion
- MAE: None pts
- MFE: None pts
- Range position: ?

## S7 Score (computed, flag OFF)
- Score: 30/100
- Sizing: ?
  - base: 30
  - day_align: 0
  - leg: 0
  - loc_pos: -1.43
  - location: 0
  - opening_conf: 0
  - delta: 0
  - noon_penalty: 0
  - late_zlr: 0
  - s2_s4_confluence: 0

## Root Verdict
**NORMAL_NOISE**: Acceptable loss — no structural issue detected

---
*Generated: 2026-09-01T20:43:30.247981+00:00 | POST_MORTEM_V1*
