# COWORK — OPEN-FIRE v1 (Phase 5.3 / OPENING_FIRE_V1) Report — 2026-07-24

**Agent:** cowork-dev · **Ruling:** מייקל 10:19 "OPEN-FIRE הביצוע על לייב" + "הדלקה בלי אישור-שני
אחרי sim-verify (replay 35 + תפיסת שורט-פולבק 07-23)" + 07-24 "להדליק את הדגל של 5.3".
**Result:** built → verified → **enabled** (`OPENING_FIRE_V1=1`). Live routing still gated (see NOT-DONE).

---

## What was built (smallest correct change, OFF = byte-identical)

| # | Change | File | Detail |
|---|--------|------|--------|
| 1 | 30→60 min window | `opening_entry.py` + `five_min_system.py` | `evaluate_opening_entry(..., window_last_bar=12, ...)`; caller sets 12 when `OPENING_FIRE_V1=1`, else 6 |
| 2 | PULLBACK-CONT trigger | `opening_entry.py` | dominant excursion off the open → after ≥33% retrace + rejection bar → enter WITH the rejection; stop behind the rejected extreme (16T), T1=1.5R |
| 3 | Seed bias safety filter | `opening_entry.py` + `five_min_system.py` | optional `bias` (from `OPENING_TYPE_SEEDS_S1_V1`, cached in the caller) — only permits entries agreeing with the day-bias |
| 4 | Explicit 1.5R for PULLBACK-CONT | `opening_entry.py` `build_opening_setup` | trigger carries `t1_r=1.5` so it does not depend on the global `T1_BANK_R`; all other triggers unchanged |

**OFF invariant:** the new params are keyword-only with defaults `window_last_bar=6, enable_pullback=False,
bias=None`. With `OPENING_FIRE_V1` unset the caller passes exactly those → the code path is identical to the
30-min SHADOW spec. Proven by `test_off_is_byte_identical` + the stash test below.

## Verification (Rule-5 — commands + raw)

**The anti-tautological fixture is the REAL 07-23 RTH opening** (`v9_bars_5min_woodies`, IL times): the
session rallied to **7486.5 @16:40** then rejected down — which DRIVE/TEST_DRIVE/ORR/EXTREME_REJECT all MISS
(TEST_DRIVE blocked by the bar-2 drive-close; ORR needs a full close-below-open that comes too late;
EXTREME_REJECT geometry doesn't match). PULLBACK-CONT fills exactly that gap.

```
$ python3 -m pytest tests/v9/regression/test_opening_fire.py tests/v9/regression/test_opening_entry.py \
      tests/v9/regression/test_opening_type_seeds.py -q
1 failed, 23 passed        # the 1 failure is PRE-EXISTING (below), NOT this change
```

- **8/8 new tests pass** (`test_opening_fire.py`): catches the 07-23 SHORT @7464.25 (stop 7490.5 = 7486.5+16T,
  T1 = 1.5R); revert→RED guard; OFF byte-identical; not-premature-at-bar-3; bias filter blocks a counter seed;
  60-min window vs 30-min cap; symmetric LONG; one-per-session.
- **revert→RED:** `test_pullback_cont_catches_0723_short` + `test_revert_red_guard` go red if the PULLBACK-CONT
  block is removed.
- **No new regressions:** full suite `141 failed / 1273 passed` — **≤ the cc baseline of 142** (the 8 new tests
  add to passed; 0 new failures).
- **Pre-existing failures in touched-file areas (NOT this change), proven by `git stash` of my 2 code files:**
  - `test_opening_entry.py::test_build_setup_shadow_structure_stop_and_1r` — brittle: asserts T1=1R but `.env`
    ruled `T1_BANK_R=1.5`; passes with `T1_BANK_R` unset. Red since the 07-23 T1_BANK_R ruling.
  - `test_opening_window_fire_item10.py::{test_emitter_auth_skip_overridden_in_window,
    test_gateway_playbook_skip_overridden_in_window}` — fail identically on the ORIGINAL code (my changes
    stashed → still 2 failed). Unrelated path (OPENING_WINDOW_FIRE_V1 / opening_type_gate).

**Live enable:** snapshot `20260724T104116Z` → `.env OPENING_FIRE_V1=1` → RULED_FLAGS +1 → **flag_guard PASS
124/124** → restart → **boot-line `env_loader applied 169 vars` (168→169)** → `OPENING_FIRE_V1=1` readable in
process; `OPENING_ENTRY_V1=shadow` unchanged.

## NOT-DONE (deliberate — Michael's live move)

- **Live routing is NOT on.** `OPENING_ENTRY_V1=shadow` → OPEN-FIRE setups are recorded **shadow-only**, not
  routed to demo/live. To fire live, two switches are Michael's: (1) `OPENING_ENTRY_V1` shadow→1 — note this
  routes **all** opening entries live (DRIVE/TD/ORR/EXTREME_REJECT too), verified by replay only, no forward
  shadow day; (2) Sierra Sim→Live (the money gate). Running in shadow today first gives OPEN-FIRE its first
  forward evidence at zero money risk.
- Detector precision-tuning (plan §ב-3, "גלאי מחליק-כיוון") not touched — separate refinement.
- Per-opening-type firing matrix (§3.1: OPEN_DRIVE early-entry, OA_IN_RANGE no-fire, etc.) not built — the
  60-min window + PULLBACK-CONT is the core; the matrix is a follow-up.

## Files
`backend/v9/systems/opening_entry.py` · `backend/v9/systems/five_min/five_min_system.py` ·
`tests/v9/regression/test_opening_fire.py` · `config/RULED_FLAGS.yaml` · `docs/FLAG_REGISTRY.yaml` ·
`docs/FLAG_INDEX.md`
