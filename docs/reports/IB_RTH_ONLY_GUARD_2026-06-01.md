# IB RTH-Only Guard — Diagnosis · 2026-06-01

**Date:** 2026-06-01 14:10 IL (07:10 ET) · **Author:** CC
**Concern:** Michael — does chart #5 (24h) contaminate IB or other RTH-bound calculations?

---

## Finding: NO CONTAMINATION — IB is safe

### 3 layers of protection

**Layer 1 — Data path isolation:**
Chart #5 continuous bars are ingested via `POST /api/v9/bars/5min_continuous` which calls `bar_ingestion_service.ingest_bar()` **only** — writing to DB for chart display. It does **NOT** call `_route_bar("5min", ...)` and does **NOT** publish through BarRouter.

The DayTypeStateMachine, FiveMinSystem, WoodiesSystem, and TPOSystem subscribe to BarRouter topics. They **never see** chart #5 bars.

```
Chart #12 (RTH) → POST /bars/5min → bar_ingestion + _route_bar("5min") → DayType/IB/etc.
Chart #5 (24h)  → POST /bars/5min_continuous → bar_ingestion ONLY → DB for display
                                                 ↑
                                    NO BarRouter publish = systems never see these bars
```

**Layer 2 — `is_rth` guard in state machine:**
Even if chart #5 bars somehow reached the DayType machine, `_stage_a3` (line 497) has:
```python
if not bar.is_rth:
    return  # Pre-RTH (Globex) bars must not contaminate the RTH IB
```
Same guard exists in `_stage_a2` (line 460): `if not bar.is_rth: return`.

**Layer 3 — IB source is Sierra Study, not bars:**
IB values come from **Sierra Study ID:6** (Initial Balance study on chart #12), read via the `tpo.json` export. The state machine's `_stage_a3` reads `bar.ib_high`/`bar.ib_low` which are populated from the Sierra study, not computed from bar OHLC.

### IB=0 is expected (pre-RTH)
```
/api/v9/key_levels:
  ib_high: None
  ib_low: None  
  ib_source: sierra.tpo.ib (Study ID:6, live)
```
Current time: 07:10 ET — RTH hasn't opened (09:30). IB correctly shows None.

### Systems that are RTH-bound (all protected)
| System | Guard | Location |
|--------|-------|----------|
| IB tracking | `if not bar.is_rth: return` | `state_machine.py:497` |
| Opening type | `if not bar.is_rth: return` | `state_machine.py:460` |
| RTH session range | `if bar.is_rth: ...` | `state_machine.py:316-321` |
| TPO session | Sierra Study (chart #12 only) | `tpo.json` export |
| FiveMinSystem | `OVERNIGHT_MODE → return` | `five_min_system.py:727` |
| WoodiesSystem | `_is_rth_bar()` 09:30-16:00 ET | `woodies_system.py:280` |

## Conclusion

**No fix needed.** Chart #5 bars flow to DB only (display). They don't reach any RTH-bound system. IB remains Sierra Study-sourced from chart #12 RTH.

---

*Phase B (fix) not needed — no leak found. Phase C (RTH verification) deferred to RTH open.*
