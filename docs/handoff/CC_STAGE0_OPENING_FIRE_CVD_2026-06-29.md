# CC Handoff — Stage 0: Opening-Type Fire + CVD Confirmation (S2)

**Date:** 2026-06-29 · **Owner:** Michael · **Prepared by:** Cowork
**Contract:** follow `docs/handoff/CC_HANDOFF_CONTRACT.md` (anti-tautological tests + mandatory NOT-DONE section + paste raw verification per Pre-LIVE Rule 5).
**Flag:** `OPENING_FIRE_CVD_V1` — **default OFF · SHADOW only.** Enabling later = trading-risk-surface change → Michael sign-off.

---

## Why (today's incident — verified)
2026-06-29: 4× `INITIATIVE_SHORT` fired 17:15–17:24 (ids 256–259), all −1.00R, ≈ **−$515**, all `STOP_HIT`.
Root causes (diagnosed, read-only):
1. **Pre-IB-lock day-type fallback.** `trade_context.extract_g1_entry_context` (≈L495–525): base day_type = OLD `day_type_machine` (3-type); when `S1_NEW_CLASSIFIER` on, it overrides with `classify_replay(today)` **unless FORMING/error → falls back to the OLD engine**. At 17:15 (before IB-lock ~17:30; history `LOCKED_LOW_CONF` at 17:35) the new classifier was FORMING → fell back to the OLD engine = premature **"Variation"** → INITIATIVE (continuation) selected. Canonical final = **Normal**. (The "Variation→Normal" is NOT a real reclass — it's the pre-lock fallback.)
2. **OPEN_DRIVE confirmation ignores CVD.** `opening_detector_v2.detect_opening_type` accepts `cvd_pos` but uses it **only** for `OPEN_REJECTION_REVERSE` (L136), **never** for `OPEN_DRIVE` (L98–111). And `opening_type_gate._detect_from_bars` (L106–115) calls the detector **without `cvd_pos`**. So today's OPEN_DRIVE-down was "confirmed" despite CVD **absorption (+3,403 delta buying at the 17:10 low)** = a failing drive.

The correct read (mode-1 vs mode-2 per Michael): **before day-type is locked, fire by OPENING-TYPE (mode 1); after lock, by day-type (mode 2).** Opening-type fire must be **CVD-confirmed** so a failing/absorbed drive does not fire with-drive.

---

## Scope — 3 focused changes (all behind `OPENING_FIRE_CVD_V1`, default OFF)

### Change 1 — pass CVD into the opening detector
`backend/v9/systems/opening_type_gate.py` → `_detect_from_bars` (L106–115):
- Compute `cvd_pos` for the opening window (0..1; >0.5 = buy-dominant, <0.5 = sell-dominant) from the **LIVE CVD stream** — `v9_bars_cumulative_delta` (verified live 06-29 19:19) and/or the woodies-derived CVD the frontend shows — **NOT** `v9_bars_5min.cumulative_delta` (the S2 5-min bar table, which **froze at 18:00 today**). Freshness-guard the chosen source (Rule 2).
- Pass `cvd_pos=...` into `detect_opening_type(...)`.
- ⚠️ **Two separate streams (verified 06-29 19:22):** CVD is **live** (`v9_bars_cumulative_delta` 19:19 · woodies 19:20). The **frozen one is `v9_bars_5min`** (last 18:00, 82 min stale) — that is S2's **5-min bar input** for detection, **not** the CVD. So S2 starvation = **bar-feed freeze**, independent of CVD. Two implications: (a) source CVD from the live stream (above), and (b) the `v9_bars_5min` freeze is a separate recurring bar-feed bug (06-22, 06-29) → `FEED_WATCHDOG` ON to block fires on a stale bar stream. Still keep the CVD-freshness fail-safe (stale CVD → OPEN_DRIVE not confirmed).

### Change 2 — CVD-confirm OPEN_DRIVE
`backend/v9/systems/day_type/opening_detector_v2.py` → OPEN_DRIVE block (L98–111):
- Require CVD **aligned with the drive**: up_drive → `cvd_pos ≥ 0.5`; dn_drive → `cvd_pos ≤ 0.5`.
- If the geometry is a drive **but CVD diverges** (absorption against the drive) → **do NOT return OPEN_DRIVE.** Fall through to `OPEN_REJECTION_REVERSE` (reversal direction) or lower confidence. Add reason `"CVD divergence — drive not confirmed"`.
- Only active when the flag is ON (param-gate inside, or caller passes a flag).

### Change 3 — pre-lock: no old-engine directional fallback for pattern selection
`backend/v9/services/trade_context.py` → `extract_g1_entry_context` (L495–525) **and/or** the gateway selection path:
- When `classify_replay` is **FORMING / not LOCKED** (pre-IB-lock), do **NOT** use the OLD `day_type_machine` directional value to drive **pattern selection** (REACTIVE vs INITIATIVE). Pre-lock selection = **mode-1 (opening-type)** only.
- Keep fail-safe: never *block* a fire on error; this only removes the premature directional bias. Post-lock behavior unchanged.

---

## Flag registry
Add `OPENING_FIRE_CVD_V1` to `docs/FLAG_REGISTRY.yaml` (category: S2/opening; status: SHADOW/default-OFF; what/why), run `python3 scripts/gen_flag_index.py`, commit refreshed `docs/FLAG_INDEX.md`.

## Tests (anti-tautological — both directions, realistic fixtures)
1. **Clean drive fires:** OPEN_DRIVE-down geometry + CVD aligned (`cvd_pos ≤ 0.5`) → detector = `OPEN_DRIVE` DOWN; gate ALLOWS with-drive SHORT.
2. **Absorbed drive blocked:** same geometry + CVD **divergence** (`cvd_pos > 0.5`, buying) → detector ≠ `OPEN_DRIVE` (→ REVERSE / downgraded); gate does NOT allow with-drive SHORT.
3. **Pre-lock no-fallback:** `classify_replay`=FORMING + old engine="Variation" → pattern selection does NOT pick INITIATIVE on the premature day-type.
4. **Regression (today):** replay 06-29 RTH bars (16:50→17:20, incl. the 17:10 +3,403 absorption) with flag ON → **no `INITIATIVE_SHORT` at 17:15** (and ideally mode-2 REACTIVE_LONG context recognized).
5. Flag OFF → behavior byte-identical to today (no change).

## Verification (live SHADOW · paste raw output, Rule 5)
- Enable in SHADOW; on the next OPEN_DRIVE-with-absorption open, confirm via logs/`S2_DETECTION_LOG` that the with-drive fire is suppressed. Paste the command + raw log lines.

## NOT-DONE (explicit — these are later stages, do NOT touch here)
- ❌ Stage 1: make `daytype_position_gate` pattern-aware (CASCADE_AUDIT R2).
- ❌ Stage 2: wire CVD into REACTIVE/INITIATIVE **geometry** detection (`_detect_reactive`/`_detect_initiative`).
- ❌ Stage 3: single-fire-per-setup guard + DEDUP_FIRE_GUARD fix (today's 4-fire / 256≡257).
- ❌ Stage 4: REACTIVE spec tweaks (B2 0.85 · 2T stop · HVN/POC targets · 2nd-test).
- ❌ Stage 5: why HnS×2 / Double×2 never fire.
- ❌ Full escalation-only enforcement in the classifier (this handoff only removes the pre-lock fallback; the Normal→Variation→Trend-only invariant is a separate fix).
- ❌ Do NOT enable the flag live. SHADOW + Michael sign-off only.
