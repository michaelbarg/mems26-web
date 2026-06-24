# CC Handoff — Day-Type Source Unification + Corrupt-Bar Fix (2026-06-24)

_Author: Cowork · contract: `docs/handoff/CC_HANDOFF_CONTRACT.md`. Owner split: CC develops, Cowork verifies + fixes-to-index._
_Context: today we made the new 7-type classifier the authority and put DIRECTION_LSMA_VETO live. Several consumers still read the OLD/stale day-type, and the price chart reads corrupt bars. Cowork applied **frontend display patches** for the visible symptoms — these tasks fix the **sources** so the new classifier truly determines everywhere, and the corrupt bars are gone at the root._

## The 4 fixes

### 1. `/api/v9/key_levels` must serve the NEW classifier's day_type
**Symptom:** the top strip showed yesterday's `Trend_Normal` while the pill/lens showed `Normal`. **Root:** the `key_levels` endpoint returns `today.day_type` from the **latest `v9_day_type_state` row**, which lags to yesterday's EOD value until today promotes (post-IB-lock + 12 bars).
**Fix:** `today.day_type` (and `opening_type`) in the key_levels handler should come from the **new classifier** — `classify_replay`/`classifier_core.classify_session` for today (the same source `useLiveDayType` polls), or the promoted `day_type_machine.day_type`. Not the raw latest persisted row.
**Cowork already patched the display** (`KeyLevelsStrip.tsx` now reads `useLiveDayType`); this makes the **endpoint** correct so every consumer benefits.

### 2. S4 (woodies) fallback uses the OLD decision_matrix + hardcoded "Normal"
**File:** `backend/v9/systems/woodies/woodies_system.py:514-530`. When `self.current_state["day_type"]` is `UNKNOWN/None`, S4 falls back to the **old `DECISION_MATRIX`** (opening×IB) and then hardcoded `"Normal"` — NOT the 7-type authority. So S4's day_type can diverge from the determiner.
**Fix:** the fallback should read the authority — the promoted `v9_day_type_state` / `classify_session` — before any old-matrix/hardcoded default. (Source-of-Truth: `docs/SOURCE_OF_TRUTH.md` §Day-type.)

### 3. #11 — rehydrate `_cls_rth_bars` on restart (day-type starvation)
**File:** `backend/main.py:391` (the promotion needs `len(_cls_rth_bars) >= 12`). A mid-session restart wipes this in-memory buffer → the new classifier can't promote for ~the first hour → the old engine's value leaks (the #11 bug). Today's 08:36 restart only survived because it was near the open.
**Fix:** when IB is locked but the buffer is short, **rehydrate `_cls_rth_bars` from the DB** (`v9_bars_5min_woodies`, today's RTH) — mirror the existing `maybe_seed_ib_from_tpo` restart-seed. + regression test: post-restart persisted `day_type == classify_replay.final`. **Trading-surface → flag or fail-safe; Michael sign-off if it changes live gating.**

### 4. Corrupt bars in `v9_bars_5min` blow the price chart
**Symptom:** the candle chart scale jumped to 0–13000, squashing the real candles. **Root:** `/api/v9/chart/bars5min` (reads `v9_bars_5min`) returns bars with absurd `close` — **12693** (today ~09:00 CT, ts `2026-06-24 17:00:00+03:00`), **13456** (`2026-06-22 17:00:00+03:00`), and a **3745** min — vs real MES ~7450. They pass the existing sticky-H/L sanitizer (internally consistent) but are off-price. `v9_bars_5min_woodies` is **clean** (7442–7468) for the same window.
**Fix (investigate root):** why does `v9_bars_5min` carry these `17:00:00`-stamped bars with ~12k closes? (cumulative_delta/volume leaking into `close`? a session-boundary/wrong-contract export?) Either clean the ingest/export, **or point `/api/v9/chart/bars5min` at the clean `v9_bars_5min_woodies` for OHLC**.
**Cowork already added a frontend guard** (`ChartV5b.tsx` rejects bars >±30% off the median close, next to the existing corrupt-bar rejection) — keep it, but fix the source.

### 5. `cumulative_delta` column holds PER-BAR delta, not a running CVD → poisons the direction engine (ROOT FOUND)
**Root cause (confirmed from code + the live export):** the Sierra 5-min export `~/SierraChart_Data/v9_export/5min_continuous.json` carries a **per-bar `delta`** (ask−bid for THAT bar; there is NO `cumulative_delta` key in that file — the real running CVD is a SEPARATE export `cumulative_delta.json` / `CumulativeDeltaStream`, not joined to the 5-min bars). But the ingest **`backend/v9/services/bar_ingestion.py:114`** writes `bar_data.get("delta")` (the per-bar delta) into the **`cumulative_delta` column** of `v9_bars_5min`. So that column = per-bar delta, NOT a cumulative. (`sc_study/v9_types.h:36,53` shows the two are distinct fields.)
**Why it breaks the engine:** `direction_context.cvd_slope` = `sign(cum[-1] − cum[-1-3])` ASSUMES a running cumulative (the 3-bar change = net flow over 15 min). Fed per-bar deltas it compares one bar's delta to the bar-3-ago's delta = noise/wrong sign. **2026-06-24 evidence:** every stored value was POSITIVE (3773, 3423, 3629, 7013, … = buying every bar, matching the price rally to 7480), yet the slope read −1/0 (1992 now < 4662 three-ago → "selling") → spurious NEUTRAL veto → **let the counter-trend GHOST SHORT through at 09:40**. (06-23 only "worked" by luck — its per-bar deltas trended.)
**Fix — recommend (B):**
  - **(B, cleanest, uses the data we already have):** change `cvd_slope` (`backend/v9/systems/direction_context.py`) to the NET per-bar delta over the window: `sign(Σ delta over last N bars)` — directly measures recent buying/selling pressure. Update `tests/v9/regression/test_direction_lsma_cvd_veto.py` fixtures (cumulative-style today) to per-bar-delta semantics. Consider renaming the column/field to `bar_delta` to stop the lie, or document it.
  - **(A, alternative):** feed the column the TRUE running cumulative from the `cumulative_delta` export stream (join by ts) and keep the slope formula.
**Verify (Rule 5):** on a buying day (all per-bar deltas +), `cvd_slope == +1`; the sign matches `sign(Σ delta)` over the window. Re-run the GHOST-09:40 case: with the fix the engine reads LONG and would block the counter-trend short.

## Index + verification (Cowork will check)
- Update `docs/SOURCE_OF_TRUTH.md` if any source's role changes; run `gen_flag_index.py --check` if a flag is added; `gen_index.py` if files move.
- **Paste raw output (Rule 5):** for #1 — `curl /api/v9/key_levels` shows today's day_type == classify_replay; #2 — a unit/log line showing S4 reads the authority; #3 — `pytest` for the rehydrate test + a restart→direction_now showing the promoted type; #4 — `curl /api/v9/chart/bars5min` shows no >9000 closes (or the chart reads woodies).
- **NOT-DONE section** mandatory.

## Cowork's display patches today (do NOT revert — they're the safety net under the source fix)
`KeyLevelsStrip.tsx` (day_type from useLiveDayType) · `ChartV5b.tsx` (±30% corrupt-bar guard + LsmaLine wired) · `LsmaLine.tsx` (autoscaleInfoProvider null) · `DayTypeLabelTab.tsx` (conditions table).
