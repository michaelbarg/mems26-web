# Unified Decision Pipeline — the "one brain" (volume+delta-driven) · 2026-06-22

**Owner:** Cowork (design) → CC (build). **Risk:** trading-surface. **Default:** flag-OFF, SHADOW-validate.
**Origin:** Michael 2026-06-22 — "make order: day-type + direction + patterns are 3 tools that overlap;
if each works we still lose — unify them into one brain, the most professional way, using volume + delta."

## The core idea — a CASCADE, not 3 parallel filters
Today the three mechanisms run independently and conflict, so bad trades slip through and the math
inverts (big losers / cut winners). The fix: **each layer CONFIGURES the next.** One coherent decision.

```
① DAY-TYPE (context)  →  configures ② and ④
② DIRECTION (arm/disarm) →  opens/closes the window, within ①'s frame
③ PATTERN (trigger)   →  fires ONLY inside ②'s window AND ①'s playbook
④ MANAGEMENT (close)  →  per ①'s template: small loser (tight stop) + big winner (runner)
DISARM (②) → close runner, stand aside
```

## Professional principle — volume + delta are CORE, not price-only
The simulated "device" used price only — that is amateur. Professional auction/order-flow trading
CONFIRMS every decision with **volume + cumulative delta (CVD)**. Current state (verified 2026-06-22):
CVD + vol_ratio are used COARSELY; the volume-profile is fresh but barely wired; **footprint (the deepest
tool — delta-per-price, absorption) is muted (`S3_MUTE=1`) and its data is dead since 06-05.** The
pipeline must make volume+delta first-class.

## The four layers

### ① DAY-TYPE — the context (BUILT: 7-type classifier, live)
- **Job:** classify the day → select the PLAYBOOK (fade / with-trend / range / stand-aside) AND the
  MANAGEMENT TEMPLATE (where targets/stop/runner go), per day-type.
- **Volume/delta:** `vol_ratio` (participation) + the **volume-profile value area** (POC/VAH/VAL/HVN/LVN)
  as the structural levels — prefer volume-profile over TPO for the levels (volume-at-price = real value).
- **Outputs:** `day_type`, `playbook`, `mgmt_template` (target/stop/runner rules), `levels`.
- **NEW:** wire the volume-profile value area as the canonical levels; expose `mgmt_template` per type.

### ② DIRECTION — when + which way (BUILT: direction_context; NEW: arm/disarm lifecycle)
- **Job:** read the auction each bar → ARM (a confirmed turn/break opens a trade window) / DISARM
  (exhaustion at the new place closes it). Parameterized by ① (Variation→reversal-break arm; Normal→edge arm).
- **Volume/delta (the professional confirmation):**
  - **ARM** = price-structure-break (rejected top / broke value) **+ DELTA confirms** (CVD turning =
    sellers/buyers in control) **+ VOLUME on the break bar** (real participation, not a thin fakeout).
  - **DISARM** = at the extreme: **VOLUME CLIMAX** (capitulation spike) **+ DELTA DIVERGENCE** (new price
    extreme but CVD does NOT confirm = absorption/exhaustion) **+** price stops making new extremes.
- **"Once" semantics (today's bug):** ARM on the **transition** (the fresh break), never on the persistent
  state; do not re-arm until a new structural extreme forms. (Prevented today's 11 chop-chase losers.)
- **Outputs:** `armed?`, `direction`, `window`, `confidence` (delta/volume strength).
- **NEW:** the arm/disarm state-machine + the delta/volume confirmation (currently CVD is a coarse 3-bar slope).

### ③ PATTERN — the trigger (BUILT: S2/S4 + the gates)
- **Job:** the specific entry signal. Fires ONLY if: inside ②'s armed window AND ①'s playbook permits
  this pattern AND location is good (the gates: opening, position, direction, nontrend — already built).
- **Volume/delta:** the pattern's own quality can be confirmed by delta at the entry (e.g. a reactive
  short confirmed by a selling-delta bar). Optional refinement.
- **Outputs:** `fire(entry, direction)` — only when all align.

### ④ MANAGEMENT — close per ① (BUILT: structural_targets + RUNNER_TRAIL_V1)
- **Job:** scale C1/C2 at the structural (volume-profile) targets; ride C3 runner to the new place
  (②'s DISARM); **tight structural stop** (above the broken level). This is where the MATH lives.
- **Volume/delta:** the runner exit = ②'s DISARM (volume-climax + delta-divergence at the extreme),
  not a fixed trail — exit at the new place, not on the bounce (today's runner gave back the move).
- **NEW:** wire the runner-exit to ②'s DISARM; the structural stop (today's trail was too tight/early).

## The math (why this is profitable, not "zero losers")
Profit = **small losers (tight structural stop) + big winners (runner to the new place), over many days.**
Not the absence of losers. Today's clean-day sim of the unified device: 1 trade, R=5.6, +$340, 0 chases.

## Build order
1. **Refactor direction_context into the arm/disarm STATE-MACHINE** (transition-based, "once" semantics)
   + add the **delta + volume confirmation** to ARM/DISARM (replace the coarse 3-bar CVD slope).
2. **Wire ① → ②/④ config** (day-type selects the arm rule + the mgmt template + the volume-profile levels).
3. **Wire ④ runner-exit to ②'s DISARM** (exit at the new place, not the bounce; structural stop).
4. **Make ③ fire inside the armed window** (the gates already exist — connect them to ②).
5. Flag `UNIFIED_PIPELINE` (default OFF). Anti-tautological tests per layer + the full-day SHADOW replay.

## Footprint — the pro upgrade (deferred, but name it)
The deepest order-flow (footprint: delta-per-price, absorption, stacked imbalances) is **muted + its data
is dead (06-05)**. The pipeline works on bar-level volume+CVD without it. To reach the HIGHEST professional
tier (absorption-based reversal/exhaustion), revive footprint — but that is **deferred pre-LIVE** (Michael's
standing decision). Flag it as the post-LIVE upgrade; do NOT un-defer without sign-off.

## NOT-DONE / discipline
Flag-gated default-OFF; each layer SHADOW-validated; volume/delta confirmation must be backtested (it
changes which trades fire). The unified pipeline is a trading-risk-surface change → Michael sign-off per layer.
