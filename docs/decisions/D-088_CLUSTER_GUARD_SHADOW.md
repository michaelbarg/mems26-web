# D-088 — cluster_guard vs SHADOW Recording

**Status:** LOCKED (Option A)  
**Date:** 2026-05-20  
**Decided by:** Michael Barg (fix requested post Wave 0)  
**Related:** D-037, D-087, `P30_WAVE_0_CC_VERIFY_ERRATA.md`

## Problem

`ClusterGuard` (5 attempts / 60s → 5 min block) returned before `_execute_shadow()` → zero SHADOW rows during Woodies bursts.

## Decision — Option A

- After **cooldown / SSV / chop** pass: **SHADOW always records**
- When `cluster_guard.is_blocked()`: set `blocked_by=cluster_guard`, skip DEMO/LIVE, **do not** call `record_attempt()`
- When not cluster-blocked: GW-02 unchanged — `record_attempt()` after hard gates, before SHADOW

## Code

- `backend/v9/gateway/trading_gateway.py` — `route_setup`
- Tests: `tests/v9/gateway/test_d088_shadow_cluster_guard.py`

## Does NOT

- Change D-086 S3 policy
- Waive Registry §18 for LIVE (D-087)
- Skip cluster_guard for LIVE/DEMO paths
