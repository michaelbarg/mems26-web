# Cursor P0.5 Report

**Date:** 2026-05-20 (updated with Task 5 Registry)  
**Authority:** Michael Barg strategic brief  
**Branch:** stabilize/mems26-local-truth-2026-05-16 (local; D-067 no push)  
**Goal:** SHADOW fixes + D-082 verify + Registry gate read

## Tasks (max 4 commits)

| # | Task | Status | Commit | Notes |
|---|------|--------|--------|-------|
| 1 | GW-02 | ✅ DONE | `8dd1ffb` | `record_attempt()` after cooldown/cluster/ssv/chop |
| 2 | GW-CHOP | ✅ DONE | *(in `8dd1ffb`)* | `get_chop_score()` — no self-HTTP |
| 3 | FP-SQL | ✅ DONE | `a9138ce` | `check_same_thread=False` on journal conn |
| 4 | S3-OBS-CHECK | ⚠️ VIOLATED · **D-086 TOLERATED** | N/A | Known issue; fix POST-SHADOW; SHADOW proceeds |
| 5 | Registry Check | ✅ DONE | N/A (read-only) | See `P30_REGISTRY_STATE.md` |

**Tests:** `pytest tests/v9/gateway/test_gw02_record_attempt.py` — 2 passed

## S2-PF Verify

- **Path:** `five_min_system.py` FIRE → `emit_t1_setup()` → `validate_fire()` (`setup_emitter.py:81`) → `route_setup` (`:556`)
- **pre_fire in path:** **YES**
- **P1 action:** **NO** — VERIFIED

Detail: `docs/reports/P30_S2_PF_VERIFY.md` (also `/tmp/p30_s2_pf_verify.md`)

## S3-OBS-CHECK (D-082)

| Check | Result |
|-------|--------|
| S3 in gateway routing (as caller) | **YES** — `footprint_system.py:426` `route_setup(..., 3)` |
| S3 emits firing events | **YES** — `_fire()` → pre_fire → gateway |
| `main.py` injects gateway to footprint | **YES** — `:393` (out of MODIFY scope) |
| **D-082 compliance** | **VIOLATED** (code vs V3 spec) |
| **D-086** | **TOLERATED in SHADOW** — fix deferred POST-SHADOW; revisit before LIVE |

**Action:** No P0.5 fix. SHADOW proceeds with S3 → gateway SHADOW records. See `P30_DECISION_D086_S3_FIRING.md`.

Detail: `docs/reports/P30_S3_OBS_CHECK.md` (also `/tmp/p30_s3_obs_check.md`)

## MEMS26_REGISTRY.yaml (Task 5)

| Field | Value |
|-------|------:|
| **Exists** | YES |
| **Total entries parsed** | 93 |
| **CRITICAL IMPLEMENTED+VERIFIED** | 18 |
| **CRITICAL SPECIFIED** | 20 |
| **HIGH SPECIFIED** | 23 |
| **§18 gate (CRITICAL all verified+)** | **FAIL** (20 SPECIFIED) |
| **§18 gate (HIGH SPECIFIED ≤ 5)** | **FAIL** (23 > 5) |

**Phase Gate:** Registry exists but **not enforceable as GREEN** for SHADOW on §18 counts alone — separate triage task.

Detail: `docs/reports/P30_REGISTRY_STATE.md` (also `/tmp/p30_registry_state.md`)

## Files Modified (P0.5)

- `backend/v9/gateway/trading_gateway.py`
- `backend/v9/systems/footprint/footprint_system.py` (journal only)
- `tests/v9/gateway/test_gw02_record_attempt.py`

## Files NOT Modified

| Path | Reason |
|------|--------|
| `footprint_system.py` `_fire` / gateway | D-082 VIOLATED — Michael decision |
| `backend/main.py` | DO NOT TOUCH |
| `MEMS26_REGISTRY.yaml` | Task 5 read-only |
| frontend, bridge, sc_study, .env | Out of scope |

## Open Questions for Michael

1. ~~D-082 S3 fix~~ — **closed by D-086** (defer POST-SHADOW; A vs B after soak).
2. **Registry §18:** Triage 20 CRITICAL / 23 HIGH SPECIFIED before formal SHADOW gate, or waive for soak?
3. **CC verify:** journal 0 errors + SHADOW fires (S2/S4 + S3 per D-086) + gateway latency post-GW-CHOP.
4. **Before LIVE:** D-086 revisit — Option A/B or V4 spec.
