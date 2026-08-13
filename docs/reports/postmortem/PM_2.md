# Post-Mortem: Trade #2

| Field | Value |
|-------|-------|
| Mode | demo |
| Direction | LONG |
| System | S<MagicMock name='mock.query().filter().first().firing_system' id='140339801116096'> |
| Entry | 7500.0 @ <MagicMock name='mock.query().filter().first().entry_ts' id='140339805871216'> |
| Exit | 7493.0 @ 2026-08-12 04:03:19.377436+00:00 |
| Stop | 7493.0 |
| PnL | $-105.0 (-1.0R) |
| Exit Reason | STOP_HIT |

## Day Type
- At entry: **<MagicMock name='mock.query().filter().first().day_type_at_entry' id='140339806023744'>**
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
  - delta: 0
  - noon_penalty: 0
  - late_zlr: 0
  - s2_s4_confluence: 0

## Root Verdict
**NORMAL_NOISE**: Acceptable loss — no structural issue detected

---
*Generated: 2026-08-12T04:03:19.389567+00:00 | POST_MORTEM_V1*
