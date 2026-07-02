# CC Unified Handoff — make S2/S4 fire correctly + robust (post 2026-06-30 live session)

**Date:** 2026-06-30 · **Owner:** Michael · **Prepared by:** Cowork
**Contract:** `docs/handoff/CC_HANDOFF_CONTRACT.md` — paste command + raw output (Rule 5), anti-tautological tests, mandatory NOT-DONE.
**Context:** a full live session on 06-30 found **why no pattern fired all day** (15 detections, 0 trades). The day-type plumbing + two S4 bugs + a stop-anchor + the day-type *calibration* were the chain. Some are already fixed/patched live (noted); this consolidates the rest into one queue. Run-book for verifying any of this: `docs/runbooks/FIRING_READINESS_PROTOCOL.md`.

**Already done live (verify, don't redo):**
- `DAYTYPE_GATE_LIVE_V1=1` + `bc1a1fd` — gate **and** S2 Auth Table read the single live S1 (`app.state.day_type_machine`). Loaded in the 18:24 restart.
- `v9_woodies_signals.is_synthetic` — **column DEFAULT 0** added live (was NOT NULL, no default → every woodies signal write failed).
- `config/stop_anchors.yaml` — ZLR anchor `cluster_low/4 → breakout_bar/1` (stop on the breakout bar). `_load_yaml` is not cached → live per-fire.

---

## 1 · `is_synthetic` — root code fix (HIGH; it aborted the woodies→gateway route)
**Finding (raw):** every woodies fire logged `[safe_writer] execute failed: NotNullViolation is_synthetic of v9_woodies_signals`. The failed write meant the pattern **did not reach `ctx.patterns`** → `ready_to_route=False` (with `failed_stages=[] pending_stages=[]`) → **no route to the gateway → no trade**. Column default 0 patched it live, but the INSERT should provide the value.
**Do:** make the `v9_woodies_signals` INSERT pass `is_synthetic` explicitly (0 for real, 1 for synthetic). Confirm the write no longer raises, and that a woodies fire now routes (`route_setup`/gateway line appears). Regression test: a woodies signal persists with `is_synthetic=0` and routes.

## 2 · Woodies patterns FIRE but never ROUTE — A7 fail / `fire_setup=None` (HIGH; the real 0-trades root) → `CC_WOODIES_ROUTE_A7_FIRE_SETUP_2026-06-30.md`
**CORRECTION:** this section previously blamed the mid-RTH restart / `lock_state=PENDING`. **Both were wrong** — the no-route repeats **23 min after a CLEAN restart** (GHOST SHORT 20:40/20:45 + ZLR LONG 19:40/19:45: fired + V2-sized, **no route_setup/gateway**, 0 trades). Structural in the woodies decision-tree, not the restart.
**Root (pinned):** `ready_to_route = not failed and not pending and patterns and sizing≠reject` (`decision_tree.py:434`). A1–A6 PASS; **A7 (`_a7_universal`, `decision_tree.py:351`) FAILS** when `ctx.fire_setup is None` for a routable pattern. `fire_setup` (`woodies_system.py:614-823`) is gated on `best.entry_price and best.stop` (L616) — suspect **`best.stop is None`** (V2 sizing computes the stop separately) → fire_setup never built → A7 FAIL → no route.
**Do:** **instrument** the A7 reason on a non-routing fire (one line), then **build `fire_setup` for any routable pattern** (use the V2/effective stop, don't gate on `best.stop`). Full spec + tests in the dedicated handoff `docs/handoff/CC_WOODIES_ROUTE_A7_FIRE_SETUP_2026-06-30.md`. *(Pre-open-restart is still good hygiene, but it is NOT the cause.)*

## 3 · Day-type calibration — OPEN_DRIVE under-called as Variation (HIGH; Michael's call)
**Finding (Michael, 06-30):** today **opened OPEN_DRIVE** (strongest trend-day signal) and Michael reads it as a **Trend day** — but the classifier returned **`Normal_Variation` / LOW_CONF** because it weights range-extension (`rib=1.2185`, price only ~8 pt above the IB) over the opening-drive + directional persistence. *(Firing impact = none — both Trend and Variation are CONT days, so INITIATIVE/ZLR are allowed identically; the harm is **management**: Variation manages structural/short, Trend lets runners run.)*
**Do:** recalibrate `classifier_core.classify_session` / `daytype_classifier.classify` so that **OPEN_DRIVE (+ value migrating with the drive)** weights toward **Trend_Normal** even when the range extension is modest; re-examine the `rib_trend_min`/extension thresholds vs Michael's definitions. This composes with `CC_DAYTYPE_DEFINITION_DOC_AUDIT_2026-06-30.md` (the doc↔code audit) and the existing day-type recalibration thread. **Trading-risk → flag-gated + Michael sign-off + the questionnaire (`DAYTYPE_CHARACTERIZATION_QUESTIONNAIRE.md`).**

## 4 · ZLR breakout-bar stop — validate + generalize (MED)
**Done live:** ZLR `cluster_low/4 → breakout_bar/1`. The old window-4 reached a **stale pre-rejection dip** (06-30 18:15: low 7516.5 four bars back → 16.5 pt stop > 15 cap → RISK_CAP SKIP). Breakout-bar = the signal bar low − 3T (~7 pt).
**Do:** add a regression test on the 06-30 16.5 pt case (breakout-bar gives ≤ cap → no SKIP). Evaluate the same `cluster_low` reach-back risk for **GB100 (window 6)**. Confirm `breakout_bar/1` resolves to the signal-bar low for S4 in `stop_anchors/resolver.py`.

## 5 · (lower) INITIATIVE pre-IB-lock opening-type auth
Genuinely-UNKNOWN pre-lock + OPEN_DRIVE should authorize via opening-type instead of `Neutral_Center → SKIP` (today's 14:00 INITIATIVE_LONG). Covered in `CC_DAYTYPE_AUTHTABLE_LIVE_2026-06-30.md` §3 — keep on the queue.

---

## Verification (Rule 5 · SHADOW/DEMO)
Run `docs/runbooks/FIRING_READINESS_PROTOCOL.md` end-to-end on the next trend/CONT day: a CONT pattern must pass steps 3→10 and create a demo trade + a Sierra PLACE. Paste the raw chain (fire → write OK → route_setup → gateway allow → demo trade → v9_export command).

## NOT-DONE
- ❌ Do not revert `DAYTYPE_GATE_LIVE_V1` / Stage-1 family gate (correct; only their inputs were stale).
- ❌ Do not enable any new flag live without Michael sign-off (trading-risk surface).
- ❌ Do not re-enable S3/footprint.
- ❌ Do not "fix" #3 by hard-coding today as Trend — recalibrate the classifier, don't override the input.
