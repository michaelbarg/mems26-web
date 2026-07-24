# CC — root fix: with-trend continuation on directional Variation days (2026-07-24)

**Ruling (Michael 2026-07-24 ~18:30, live):** "תיקון מהשורש" — on a Variation day that is
directionally trending, a with-trend pullback/reversal entry must be ALLOWED, not blocked. The
system missed a live LONG today for exactly this reason.

**Build flag-OFF. Verify. Do NOT enable — Michael signs off after sim + cowork verification.**
Follow `docs/handoff/CC_HANDOFF_CONTRACT.md` (anti-tautological tests · Rule-5 · NOT-DONE section).

## Live evidence (today, verified from the log + DB)
- Day classified `Variation`, `direction=with_trend`, `dir_bias UP`, "value migrating UP", trend BLUE, +58pt (7431→7489.5).
- **18:15:08 `[FiveMin] FIRE: REACTIVE LONG entry=7478`** (a real pullback: high 7489.5 @18:15 → pulled back, entry 7478).
- **BLOCKED:** `[Gateway] BLOCKED by day-type playbook: REACTIVE responsive LONG not at VAL (above_value) on Variation` → `blocked_by=daytype_playbook`.
- **Inversion proof:** 18:20 a counter-trend `REACTIVE SHORT` (id 509) went LIVE on the up-day while the with-trend LONG was blocked.

## Root cause (traced — `backend/v9/systems/daytype_playbook.py:210-262`)
Two halves, both in the `_RESPONSIVE_REV` branch of `decide()`:
1. **`NEVERFADE_TREND_ONLY_V1` forces `_wt_on = False` on every non-Trend day** (line ~222: `not str(day_type).startswith("Trend")`). Correct for ROTATIONAL Variation (ruling #3), wrong for TRENDING Variation → drops to location-only → responsive LONG requires VAL → `above_value` blocked.
2. **The chase proxy is value-location, not the session extreme** (`_chase = LONG and _loc_wt == "above_value"`, line ~238). On a day whose value is migrating up, a pullback entry above the OLD value area is normal continuation, not chasing — but it reads as "chasing."

`decide()`'s `levels` dict only carries `{vah, val, ib_width}` — it has NO session extremes, so a correct chase check needs `day_high`/`day_low` plumbed in.

## The fix — new flag `VARIATION_WITH_TREND_CONT_V1` (default OFF = byte-identical)

### 1. Plumb session extremes into the playbook `decide()` call
Find the `daytype_playbook.decide(...)` call site(s) (gateway + five_min). Add `day_high`/`day_low`
to the `levels` dict passed in — mirror the existing `_lg_day_levels` block at
`trading_gateway.py:893-900` (which already computes `day_high`/`day_low` from today's 16:30 session
bars). Reuse that same computation; do not add a second query if one is in scope.

### 2. `daytype_playbook.py` — allow with-trend continuation on directional Variation
In the `_RESPONSIVE_REV` branch, replace the unconditional `_wt_on = False` on non-Trend with a
`VARIATION_WITH_TREND_CONT_V1`-gated hybrid:
- When flag ON **and** `day_type` is a non-Trend directional day (Variation/Normal_Variation) **and**
  `day_direction (_dd)` is UP/DOWN: keep `_wt_on` semantics as a **hybrid** (`_variation_wt = True`):
  - **with-trend** (LONG on UP / SHORT on DOWN): ALLOW as continuation, **unless chasing** —
    where chasing = `day_high - entry < EXTREME_MIN_DIST_PTS` (LONG) / `entry - day_low < EXTREME_MIN_DIST_PTS` (SHORT), default 6.0, reuse the same env knob as the gateway guard. Fail-open (allow) if `day_high`/`day_low` missing.
  - **counter-trend**: DO NOT `SKIP` (never-fade); fall through to the existing location-fade
    (ruling #3: allow at the proper edge — long at VAL / short at VAH — else SKIP).
- Flag OFF → the existing `_wt_on = False` path runs unchanged → **byte-identical**.

### 3. REACTIVE chase coverage
`EXTREME_CHASE_GUARD_V1` currently EXEMPTS REACTIVE (it was "covered by" the responsive chasing
branch). Since this fix changes that branch, ensure REACTIVE keeps chase protection — either drop the
REACTIVE exemption in `trading_gateway.py:~1085` (so the gateway guard also covers REACTIVE) **or**
rely on the new day_high/day_low chase in the playbook. Pick one, state which, and test it.

## Tests (anti-tautological — real fixtures from today; `tests/v9/regression/test_variation_with_trend_cont.py`)
1. **Catch today's miss:** `decide(REACTIVE_LONG, "Variation", "LONG", day_direction="UP", location="above_value", entry_price=7478, levels={... day_high:7489.5, day_low:7431.25})` → **ALLOW** (FULL/REDUCED, not SKIP) when flag ON; **SKIP** ("not at VAL") when flag OFF. (revert→RED)
2. **Still block chasing:** same but `entry_price=7487` (day_high 7489.5, dist 2.5 < 6) → **SKIP** (chasing).
3. **Counter-trend fade preserved:** `LONG` on `dir=UP` at `location="below_value"` (VAL) → still ALLOW (ruling #3 two-sided fade); counter-trend NOT at edge → SKIP.
4. **Trend days unchanged:** on `Trend_Normal`, with-trend/counter-trend behaviour byte-identical to today (never-fade still applies).
5. **OFF = byte-identical:** flag unset → every case returns exactly today's verdict.

## Verify + report
`pytest tests/v9/regression -q` (failed count ≤ current 141) · flag OFF in `.env` · add to
`FLAG_REGISTRY.yaml` + `gen_flag_index.py` · report per contract part-C (phases + evidence +
revert→RED + NOT-DONE) → `docs/reports/`. **NOT-DONE until:** sim-verify + Michael sign-off to enable.
cowork verifies (Rule-5) before any enable.
