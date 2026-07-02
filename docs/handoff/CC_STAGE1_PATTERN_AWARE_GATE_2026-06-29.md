# CC Handoff — Stage 1: Pattern-Aware Day-Type Gate (S2/S4)

**Date:** 2026-06-29 · **Owner:** Michael · **Prepared by:** Cowork
**Contract:** follow `docs/handoff/CC_HANDOFF_CONTRACT.md` (anti-tautological tests + NOT-DONE + paste raw verification, Rule 5).
**Flag:** `DAYTYPE_PATTERN_AWARE_V1` — **default OFF · SHADOW only.** Enable = trading-risk-surface change → Michael sign-off.
**Depends on:** Stage 0 (`OPENING_FIRE_CVD_V1`) for the pre-lock path; Stage 1 governs the **post-IB-lock** path.

---

## Why (CASCADE_AUDIT §5 R2 — verified)
`backend/v9/systems/daytype_position_gate.py` → `decide(*, pattern, direction, day_type, entry_price, tpo_ctx, trend_state)` **receives `pattern` but never references it** (gates only on `day_type` × `direction` × location). So it cannot tell a **continuation** pattern from a **reversal** pattern.

**Today (06-29):** on a **Normal** day, `_decide_normal` = "LONG below POC, SHORT above POC" (fade the edges). `INITIATIVE_SHORT` entered 7435 (> POC ≈ 7407) → gate ALLOWED it as if it were a fade-the-high short — but INITIATIVE is a **continuation**, which must NOT fire on a balanced day. Result: 4 wrong fires.

**The rule (Michael):** the day-type **selects the pattern family** — balanced day → REACTIVE (fade/REV); trend day → INITIATIVE (continuation/CONT).

---

## Scope — 2 changes (behind `DAYTYPE_PATTERN_AWARE_V1`, default OFF)

### Change 1 — pattern → family map (CONT / REV)
New small pure map (e.g. `daytype_position_gate.py` or a helper):
- **CONT:** `INITIATIVE_LONG/SHORT`, `BULL_FLAG_LONG`, `BEAR_FLAG_SHORT`; (S4) `ZLR`, `TLB`, `TT`, `GB100`.
- **REV:** `REACTIVE_LONG/SHORT`, `INVERSE_HNS_LONG`, `HNS_TOP_SHORT`, `DOUBLE_BOTTOM_EE_LONG`, `DOUBLE_TOP_AA_SHORT`; (S4) `VEGAS`, `GHOST`, `FAMIR`, `HTLB`.
- Unknown pattern → no family gate (fail-open, existing behavior).

### Change 2 — use the family in `decide`
At the top of `decide` (when flag ON, post-IB-lock), gate the **family by day-type** BEFORE the existing location logic:
- `Normal` / `Neutral_Center` / `Neutral_Extreme` (**balanced**) → **allow REV, block CONT** (`reason="balanced day → continuation blocked"`).
- `Trend_Normal` / `Trend_DD` (**trend**) → **allow CONT, block REV**.
- `Variation` → **allow CONT** (then existing with-expansion logic), **block REV**.
- `Nontrend` → block all (existing).
- Within the allowed family → fall through to the **existing** `_decide_normal/_decide_variation/_decide_trend` location logic unchanged.
- Flag OFF → byte-identical to today (pattern ignored).

---

### Change 3 — fix `CONT_TREND_FILTER` reversal classification (06-29 finding)
`backend/v9/gateway/trading_gateway.py` (CONT_TREND_FILTER, ~L318): its `REVERSAL_PATTERNS` set = Woodies-REV + Double/HnS **only — `REACTIVE` is MISSING** → REACTIVE is treated as CONTINUATION → counter-trend **fade-shorts get blocked** (log 06-29 16:55: `BLOCKED by cont-trend-filter: REACTIVE_SHORT setup DOWN vs sustained UP`). This is the **second** block on REACTIVE fades (alongside the pattern-blind position-gate).
- Add `REACTIVE_LONG` / `REACTIVE_SHORT` (+ any REV S2 patterns) to `REVERSAL_PATTERNS` so REACTIVE is **EXEMPT** from the with-trend requirement (REV fades against the trend by design).
- Use the **same CONT/REV map** as Change 1 (single source of truth — don't maintain two lists).

> ⚠️ Also surfaced 06-29: the position-gate blocked `REACTIVE_SHORT` on `entry 7463.25 < POC 7466.25` with **stale TPO levels** (6-pt VA vs 80-pt IB; price above VAH → frozen with `v9_bars_5min` 18:00). The pattern-aware gate (Change 2) must read **LIVE** POC/VAH/VAL and gate REACTIVE on **VAH** (the edge), not a strict POC threshold. Live-levels fix may be a prerequisite (see Stage 0 / feed-freeze).

## Flag registry
Add `DAYTYPE_PATTERN_AWARE_V1` to `docs/FLAG_REGISTRY.yaml`, run `scripts/gen_flag_index.py`, commit `docs/FLAG_INDEX.md`.

## Tests (anti-tautological — both allow & block, realistic)
1. **Normal + INITIATIVE_SHORT** (CONT) → **BLOCK** (the today bug). 
2. **Normal + REACTIVE_SHORT** (REV) above POC → **ALLOW** (existing location logic).
3. **Trend_Normal + INITIATIVE** (CONT) with-trend → **ALLOW**.
4. **Trend_Normal + REACTIVE** (REV) → **BLOCK**.
5. **Nontrend + anything** → BLOCK (unchanged).
6. **Regression (today):** day_type=Normal (post-lock) + `INITIATIVE_SHORT` @7435, POC 7407 → **BLOCK** under the flag (vs ALLOW today).
7. Flag OFF → identical to current behavior (pattern ignored), all existing gate tests pass.

## Verification (live SHADOW · Rule 5)
- Enable in SHADOW. Confirm via logs that on balanced-day fires, CONT patterns are blocked and only REV fire (and vice-versa on trend days). Paste raw `blocked_by="daytype_pattern_family"` log lines.

## NOT-DONE (explicit)
- ❌ Pre-IB-lock path (that is Stage 0 / mode-1 opening fire).
- ❌ CVD inside REACTIVE/INITIATIVE geometry detection (Stage 2).
- ❌ single-fire/DEDUP (Stage 3).
- ❌ REACTIVE spec tweaks — 0.85 / 2T / HVN-POC targets / 2nd-test (Stage 4).
- ❌ HnS/Double never-fire investigation (Stage 5).
- ❌ Do NOT change `Variation` with-expansion internals (only family-gate REV out).
- ❌ Do NOT enable the flag live — SHADOW + sign-off.
