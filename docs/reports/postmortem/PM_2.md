# Post-Mortem: Trade #2

| Field | Value |
|-------|-------|
| Mode | demo |
| Direction | LONG |
| System | S<MagicMock name='mock.query().filter().first().firing_system' id='140595414240128'> |
| Entry | 7500.0 @ <MagicMock name='mock.query().filter().first().entry_ts' id='140595428154096'> |
| Exit | 7493.0 @ 2026-08-16 19:09:47.475168+00:00 |
| Stop | 7493.0 |
| PnL | $-37600.0 (-268.57R) |
| Exit Reason | STOP_HIT |

## Day Type
- At entry: **<MagicMock name='mock.query().filter().first().day_type_at_entry' id='140595428265600'>**
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
  - location: 0
  - opening_conf: 0
  - cvd_directionality: 0.137
  - delta: 0
  - noon_penalty: 0
  - late_zlr: 0
  - s2_s4_confluence: 0

## Root Verdict
**NORMAL_NOISE**: Acceptable loss — no structural issue detected

---
*Generated: 2026-08-16T19:09:47.487046+00:00 | POST_MORTEM_V1*
