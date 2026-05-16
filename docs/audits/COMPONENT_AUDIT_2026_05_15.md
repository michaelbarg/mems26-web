# MEMS26 V9 — Component Audit
Date: 2026-05-15 EOD
Branch: feature/v9_architecture_rebuild (86 commits ahead of origin)
Type: READ-ONLY audit

## Summary

- Total backend .py files: 286
- Total frontend .tsx files: 84
- Total API endpoints: 90
- Total tests: 1371 passed, 39 failed, 3 skipped
- Sierra DLL: 654 LOC (main) + 1705 LOC (merged), 11 JSON exports

## Per-System Table

| System | Files | LOC | Tests | Endpoints | Sierra Inputs | Spec |
|--------|-------|-----|-------|-----------|---------------|------|
| S1 Day Type | 15 | 2152 | 9 files (58 tests) | 9 (V1+V9) | 5min (via BarRouter) + TPO cross-read | :green_circle: |
| S2 5-Min | 2 | 416 | 0 files | 4 | cumulative_delta (wrappers.py) | :yellow_circle: |
| S3 Footprint | 8 | 823 | 1 file | 3 | tick_reversal_15/12 + footprint (wrappers.py) | :yellow_circle: |
| S4 Woodies | 18 | 1737 | 3 files (39 fail) | 3 | woodies_30min | :yellow_circle: |
| S5 TPO | 8 | 1154 | 2 files | 4 | volume_profile (wrappers.py) | :yellow_circle: |
| S6 Killzone | 9 | 586 | 2 files | 1 | none (time-based) | :yellow_circle: |

Notes:
- S1 Day Type is the only system with V9 architecture (triggers, zohar, extensions, consumer, E2E tests)
- S2-S6 have working code but no V9 enhancement layer
- S4 Woodies has 39 test failures (pre-existing, mostly ZLR pattern issues)

## Sierra DLL

| Item | Status |
|---|---|
| MES_AI_DataExport.cpp | 654 LOC, last commit c2d9429 (2026-05-11) |
| MES_AI_DataExport_merged.cpp | 1705 LOC |
| MaintainVolumeAtPriceData | Set to 0 (OFF) at line 98 |
| JSON exports (11) | cumulative_delta, footprint, imbalance_flags, live_price, mes_ai_data, reversal_cluster, stacked_imbalances, tick_reversal_12, tick_reversal_15, volume_profile, woodies_30min |

## Sierra Input Mapping

| Sierra JSON | Bridge Stream | Subscribed Systems |
|---|---|---|
| tick_reversal_15.json | tick_reversal_15 | S3 Footprint |
| tick_reversal_12.json | tick_reversal_12 | S3 Footprint |
| cumulative_delta.json | cumulative_delta | S1 Day Type (wrappers), S2 5-Min |
| volume_profile.json | volume_profile | S1 Day Type (wrappers), S5 TPO |
| woodies_30min.json | woodies_30min | S4 Woodies |
| footprint.json | footprint | S3 Footprint |
| live_price.json | live_price | /api/v9/live_price (direct read) |
| mes_ai_data.json | (direct read) | CVD, POC, VWAP, pivots (not piped to Day Type) |
| stacked_imbalances.json | stacked_imbalances | S3 Footprint area |
| imbalance_flags.json | imbalance_flags | S3 Footprint area |
| reversal_cluster.json | (direct read) | Reversal enrichment |

## Shared Services

| Service | Exists | Used By |
|---|---|---|
| market_clock.py | :green_circle: | S1 Day Type (session_min), open_type, clock_routes |
| bar_router.py | :green_circle: | All 6 systems via main.py subscriptions |
| event_dispatcher/ | :green_circle: | All 6 systems via wrappers.py |
| stream_health/ | :green_circle: | Monitoring (health.py) |
| historical_replay.py | :green_circle: | Startup warm-up (DB replay) |
| pre_fire_validator.py | :red_circle: MISSING | Spec requires for S2/S3/S4 firing validation |
| clock_routes.py | :green_circle: | /api/v9/clock/now |

## Integration Surface

| Component | Exists | Notes |
|---|---|---|
| services/layer3/ | :green_circle: | Entry execution |
| services/layer4/ | :green_circle: | Don't-give-back rules |
| gateway/trading_gateway.py | :green_circle: | Mode routing (SHADOW/LIVE) |
| systems/layer0/ | :green_circle: | Chop score gating |

## Frontend Components (Cockpit)

| Component | Exists | Files |
|---|---|---|
| chart/v5b (ChartV5b) | :green_circle: | 1 tsx |
| chart/ (all chart components) | :green_circle: | 9 tsx |
| layout/ (TopBar, etc) | :green_circle: | 6 tsx |
| sidebar/ (tabs) | :green_circle: | 16 tsx |
| sidepanel/ (lens panels) | :green_circle: | 7 tsx |
| systems/ (per-system lens) | :green_circle: | 12 tsx |
| strips/ | :green_circle: | 2 tsx |
| panels/ | :green_circle: | 8 tsx |
| trades/ | :green_circle: | 4 tsx |
| ActiveTradeCard | :green_circle: | sidepanel/ActiveTradeCard.tsx |
| SessionTimeStrip | :red_circle: MISSING | Cockpit V6 SS2 |
| IBLifecycleOverlay | :red_circle: MISSING | Cockpit V6 SS3 |
| RiskWidget | :red_circle: MISSING | Cockpit V6 SS4 (LIVE only) |
| EmergencyKill | :red_circle: MISSING | Cockpit V6 (LIVE only) |
| PreFlightModal | :red_circle: MISSING | Cockpit V6 SS8 |

## Critical Gaps (blocking SHADOW)

1. **pre_fire_validator.py** — MISSING. Required for S2/S3/S4 firing validation before trade entry.
2. **S1 Day Type dead wiring** — 5 V9 methods exist but have no production callers (triggers, extensions, zohar, volume_spike, cvd_context). State machine works via process_bar only.
3. **S1 Previous Day Loader** — MISSING. pd_high/pd_low/pd_close never populated. Stage A1 (pre-open context) always skips.
4. **S4 Woodies test failures** — 39 failures in broader suite (ZLR pattern + others).
5. **V1 fallback not removed** — Both old api.py and new day_type_v9_routes.py coexist.

## Nice-to-Have Gaps (defer to Phase 4)

1. SessionTimeStrip (Cockpit V6)
2. IBLifecycleOverlay (Cockpit V6)
3. RiskWidget (LIVE mode only)
4. EmergencyKill (LIVE mode only)
5. PreFlightModal (Cockpit V6)
6. S2/S3/S5/S6 V9 enhancement (triggers, zohar-equivalent refinement rules)
