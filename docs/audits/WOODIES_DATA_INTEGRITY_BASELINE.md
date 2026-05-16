# Woodies §6.7 Data Integrity Baseline

## Audit Date
2026-05-16

## Scope
- backend/v9/systems/woodies/ (all .py files)
- sc_study/v9_woodies_export.h
- sc_study/MES_AI_DataExport.cpp (Woodies-related sections)

## Results
- Total matches: 6

### Approved (non-signal · logging/labeling only): 4

| File:Line | Match | Reason Approved |
|---|---|---|
| `hfe.py:108` | `"source": "Python_fallback"` | Label in details dict — identifies data source, not a fallback computation |
| `hfe.py:139` | `"source": "Python_fallback"` | Same — label only |
| `direction_change_detector.py:37` | `no fallback per §6.7` | Comment documenting §6.7 compliance — not a violation |
| `MES_AI_DataExport.cpp:96` | `uses fallback` | Comment about VAP storage change — describes DLL behavior, not Woodies signal |

### Attention (approximation in computation): 2

| File:Line | Match | Assessment |
|---|---|---|
| `v9_woodies_export.h:132` | `ATR approximation over 14 bars` | ChopZone uses simplified ATR (sum/count vs true Wilder smoothing). Non-signal — used for CZI indicator display. **ACCEPTED** — industry-standard simplification. |
| `v9_woodies_export.h:156` | `we approximate: CCI > 0 and rising` | Trend state BLUE/RED uses approximation of "6+ bars above/below zero". **ACCEPTED** — DLL can't easily track bar count history. Python side (cci_calc.py) has fuller logic. |

### Critical (fallback in signal-bearing): 0

## Status
🟢 CLEAN — 0 critical violations. 2 approximations in DLL are documented and accepted (non-signal display indicators). Python side has fuller implementations.
