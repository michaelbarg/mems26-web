# D-087 — Registry §18 Waiver for SHADOW Soak

**Status:** LOCKED  
**Date:** 2026-05-20  
**Decided by:** Michael Barg

## Context

- Source: `MEMS26_REGISTRY.yaml` — see `docs/reports/P30_REGISTRY_STATE.md`
- §18 gate: **20 CRITICAL SPECIFIED**, **23 HIGH SPECIFIED** → formal FAIL
- P0.5 gateway/journal fixes are complete (`P30_CURSOR_P05_REPORT.md`)
- **Does not cover** `cluster_guard` / GW-1 (separate — see D-088 draft below)

## Decision (Michael · 2026-05-20)

### SHADOW phase — §18 gate **WAIVED**

- Acknowledge **20 CRITICAL SPECIFIED** + **23 HIGH SPECIFIED**
- Proceed with SHADOW soak (**observation only**, no real money)
- Registry counts alone are **not** a phase-gate blocker for soak start

### LIVE phase — §18 gate **ENFORCED** (hard requirement)

Before **P-L1** (LIVE micro):

- All CRITICAL entries: **VERIFIED+** (per §18)
- HIGH SPECIFIED: **≤ 5** (per §18)
- Triage owner: **Michael + CC**

### Mid-SHADOW

- Optional Registry triage **in parallel**
- Does **not** block soak

## Scope

| In scope | Out of scope |
|----------|----------------|
| Registry §18 phase gate for SHADOW | `cluster_guard` blocking SHADOW writes |
| POST-SHADOW triage obligation | D-086 S3 firing policy |
| LIVE/DEMO/L5 promotion gates | Skipping L4/L5 |

## POST-SHADOW obligation

- Triage CRITICAL SPECIFIED → IMPLEMENTED/VERIFIED or owned DEFER with date
- Reduce HIGH SPECIFIED below 5 or update Drive §18 rule with Michael approval

## Evidence

- Registry scan: `docs/reports/P30_REGISTRY_STATE.md`
- CC Wave 0: `docs/reports/P30_WAVE_0_CC_VERIFY.md` — **GO-WITH-NOTES** (2026-05-20 16:06 ET)

---

## Related (not D-087) — cluster_guard

CC WARN #5: Woodies setups hit `blocked_by=cluster_guard` after 5 gated attempts in 60s (D-037).  
**D-087 does not waive this.** Needs **D-088** or Cursor gateway fix before soak produces S4 SHADOW rows.  
See `docs/reports/P30_WAVE_0_CC_VERIFY_ERRATA.md`.
