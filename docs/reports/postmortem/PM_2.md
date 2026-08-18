# Post-Mortem: Trade #2

| Field | Value |
|-------|-------|
| Mode | demo |
| Direction | LONG |
| System | S<MagicMock name='mock.query().filter().first().firing_system' id='140610621937888'> |
| Entry | 7500.0 @ <MagicMock name='mock.query().filter().first().entry_ts' id='140610621016384'> |
| Exit | 7493.0 @ 2026-08-18 07:37:48.285967+00:00 |
| Stop | 7493.0 |
| PnL | $-37600.0 (-268.57R) |
| Exit Reason | STOP_HIT |

## Day Type
- At entry: **<MagicMock name='mock.query().filter().first().day_type_at_entry' id='140610620964048'>**
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
  - loc_pos: -12.61
  - location: 0
  - opening_conf: 0
  - cvd_directionality: 0.281
  - delta: 0
  - noon_penalty: 0
  - late_zlr: 0
  - s2_s4_confluence: 0

## Root Verdict
**NORMAL_NOISE**: Acceptable loss — no structural issue detected

---
*Generated: 2026-08-18T07:37:48.347257+00:00 | POST_MORTEM_V1*
