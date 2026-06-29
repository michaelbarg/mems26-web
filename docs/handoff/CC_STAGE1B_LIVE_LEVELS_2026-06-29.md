# CC Handoff — Stage 1b: Live TPO Levels + VAH/VAL-Edge Gating for REACTIVE

**Date:** 2026-06-29 · **Owner:** Michael · **Prepared by:** Cowork
**Contract:** `docs/handoff/CC_HANDOFF_CONTRACT.md` (anti-tautological tests + NOT-DONE + paste raw output, Rule 5).
**Flag:** `DAYTYPE_PATTERN_AWARE_V1` (same as Stage 1 — this **completes** it). Default OFF · SHADOW.
**Why this is a prerequisite for clean SHADOW:** with stale levels, even the corrected pattern-aware gate mis-gates REACTIVE.

---

## Why (06-29, from Stage-1 handoff §43)
The position-gate **blocked `REACTIVE_SHORT`** at `entry 7463.25` because `POC 7466.25` and `_decide_normal` requires SHORT **above POC**. But:
- The TPO levels were **stale / degenerate** — VA width ≈ 6 pt vs IB ≈ 80 pt (a frozen/degenerate profile, same class as the `v9_bars_5min` 18:00 freeze).
- Price was actually **above VAH** — a **valid fade-short edge** — yet the strict POC threshold blocked it.

Two faults: **(a)** stale/invalid TPO levels reached the gate; **(b)** strict POC-threshold gating mis-blocks fades that sit between POC and the true edge.

---

## Scope — 2 changes (behind `DAYTYPE_PATTERN_AWARE_V1`, default OFF)

### Change A — fresh + valid TPO levels into the gate
- The `tpo_ctx` (POC/VAH/VAL) passed to `daytype_position_gate.decide` MUST be **live and valid**.
- Add a **validity/freshness guard**: if the profile is stale (session not current) **or degenerate** (VA width < a floor, e.g. `< 8 pt`, or VAH≈VAL≈POC) → **fail-open** (do NOT gate on bad levels; log `daytype_gate: stale/degenerate TPO → fail-open`). Never gate a fire on a frozen 6-pt VA.
- Source from the **live** TPO (`v9_tpo_sessions` CASH current row, or `cross_context.tpo_system`) — verify the row is recent (Rule 2). Ties to the `v9_bars_5min` feed-freeze (separate bug; this guard makes the gate robust to it).

### Change B — gate REACTIVE (REV) on the VA EDGE, not strict POC
In `_decide_normal` / `_decide_neutral` (and the Neutral variants), for **REV family** patterns:
- **SHORT** allowed when `entry ≥ VAH − tol` (at/above the upper edge) — fade the high.
- **LONG** allowed when `entry ≤ VAL + tol` (at/below the lower edge) — buy the low.
- `tol` small (e.g. 2 pt). This replaces the strict POC-side threshold for REV (which mis-blocks fades between POC and the edge).
- **CONT** family keeps the existing logic unchanged.
- Reuse the `_pattern_family` map (single source of truth).

---

## Flag registry
No new flag (extends `DAYTYPE_PATTERN_AWARE_V1`). If a value is added (`tol`, VA-width floor) → document in `FLAG_REGISTRY.yaml` or a config constant.

## Tests (anti-tautological)
1. **06-29 regression:** `REACTIVE_SHORT` @ entry above VAH, POC just above entry, **valid** levels → **ALLOW** (was BLOCKED).
2. **Mid-value:** `REACTIVE_SHORT` between POC and VAL (not at an edge) → **BLOCK**.
3. **Stale/degenerate TPO** (VA width 6 pt) → **fail-open** (not blocked on bad levels).
4. **CONT unchanged:** INITIATIVE gating identical to before.
5. Flag OFF → byte-identical to current.

## Verification (SHADOW · Rule 5)
- Enable in SHADOW; confirm REACTIVE fades at VA edges pass and mid-value fades are blocked; paste raw `blocked_by` / allow log lines.

## NOT-DONE (explicit)
- ❌ Fixing the `v9_bars_5min` feed-freeze itself (separate bar-feed bug; this only makes the gate robust to stale levels).
- ❌ Stage 2 (CVD in geometry detection), Stage 3 (single-fire), Stage 4 (REACTIVE tweaks), Stage 5 (HnS/Double).
- ❌ Do NOT enable the flag live — SHADOW + sign-off.
