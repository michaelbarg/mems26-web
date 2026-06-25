# S2 Non-Firing Patterns — Root-Cause Diagnosis (2026-06-24)

**Scope:** Why several System-2 (`five_min`) patterns produced **zero** trades in
shadow history (2026-06-05 → 06-24). READ-ONLY diagnosis — no code/flag/env
changes made.

**Evidence base:**
- `outputs/s2_trades_dump.csv` — 78 S2 shadow trades, full window.
- `backend/main.py` entrypoint → `FiveMinSystem.process_bar`
  (`backend/v9/systems/five_min/five_min_system.py`).
- Detectors: `patterns/head_shoulders.py`, `patterns/double_bt.py`,
  `patterns/flags.py`.
- Gating: `quality_tier.py`, `auth_table_v1.py`, `setup_emitter.py`,
  `docs/FLAG_INDEX.md`, `.env`.

---

## 1. What actually fired (ground truth from the dump)

`pattern_id_at_entry` distribution over the 78 rows:

| pattern_id_at_entry | count | system |
|---|---|---|
| `REACTIVE_SHORT`   | 32 | S2 |
| `REACTIVE_LONG`    | 18 | S2 |
| `INITIATIVE_SHORT` | 14 | S2 |
| `INITIATIVE_LONG`  |  4 | S2 |
| `BULL_FLAG_LONG`   |  3 | S2 |
| `BEAR_FLAG_SHORT`  |  2 | S2 |
| `ZLR`              |  2 | **S4/Woodies** (not S2) |
| `VEGAS`            |  1 | **S4/Woodies** (not S2) |
| *(blank)*          |  2 | S2 (early Reactive/Initiative, pattern_id not stamped) |

`ZLR` / `VEGAS` are **not** S2 chart patterns — they are S4/Woodies
(`backend/v9/systems/woodies/patterns/zlr.py:33` `PATTERN_ID = "ZLR"`). They
leaked into a `firing_system=2`-loose dump; ignore for the S2 question.

**Day-types that occurred in the entire shadow window** (across all 78 fires):
`Variation` (39), `Trend_Normal` (26), `Normal` (8), blank (5).
**`Neutral_Extreme`, `Neutral_Center`, and `Trend_DD` NEVER occurred.** This
single fact dominates several rows below.

### The genuine S2 zero-fire set (the targets)

The task's shorthand maps to the canonical `pattern_name` constants as follows
(see `auth_table_v1.py:62-89`, `output_schema.py` `PatternName`):

| task shorthand | canonical pattern_name | detector |
|---|---|---|
| HNS_LONG | `INVERSE_HNS_LONG` | `detect_inverse_hns` |
| TOP_SHORT | `HNS_TOP_SHORT` | `detect_hns_top` |
| DOUBLE_BOTTOM / EE_LONG | `DOUBLE_BOTTOM_EE_LONG` | `detect_double_bottom_ee` |
| DOUBLE_TOP / AA_SHORT | `DOUBLE_TOP_AA_SHORT` | `detect_double_top_aa` |
| VSA | *(not a pattern)* — volume-gate **variant inside REACTIVE** | — |
| EXPANSION | *(not a pattern)* — **gate inside INITIATIVE** | — |

---

## 2. Root-cause table

| Pattern | Root cause | Evidence (file:line) | Fixable / should it fire? |
|---|---|---|---|
| **INVERSE_HNS_LONG** (HNS_LONG) | **(c) Conditions unreachable** — shoulder-symmetry gate is ~1-tick tight; effective search window capped at ~19 bars; ATR-relax helper is dead-wired. | `head_shoulders.py:103` `asymmetry = abs(left-right)/head_to_avg ≤ 0.05`; `five_min_system.py:972` buffer cap 20 → `_det_buf=buffer[:-1]`; `head_shoulders.py:39-44` `get_head_min_ext_ticks` **never called** (raw `HEAD_MIN_EXT_TICKS` used at `:174`). | **BUG — should fire occasionally.** Loosen `SHOULDER_SYM_PCT` and/or wire the ATR helper; widen buffer. Calibration, not redesign. |
| **HNS_TOP_SHORT** (TOP_SHORT) | **(c) Conditions unreachable** — same symmetry gate mirrored; plus auth SKIP on Trend_Normal removes 26 of the candidate bars. | `head_shoulders.py:103,239` (mirror); auth `HNS_TOP_SHORT/Trend_Normal = SKIP` `auth_table_v1.py:69`; emit short-circuit `setup_emitter.py:62-67`. | **BUG — should fire occasionally** (Variation/Normal would emit). Same fix as Inverse H&S. |
| **DOUBLE_BOTTOM_EE_LONG** (EE_LONG / DOUBLE_BOTTOM) | **(c) Conditions unreachable** — "Eve" width≥3 gate vs strict local-min pivot; short window. Symmetry gate is NOT the blocker (it is a price-level ratio ≈ ±199pt). | `double_bt.py:192` `w1<3 or w2<3 → continue`; width counts bars within `0.75×ATR` of an exact strict-min low `double_bt.py:96-111`; symmetry `:137` `abs(t1-t2)/min ≤ 0.03`. | **BUG — should fire rarely.** "Eve rounded ≥3 bars" + strict pivot rarely co-occur. Relax `TROUGH_MIN_WIDTH_BARS` or pivot definition. |
| **DOUBLE_TOP_AA_SHORT** (AA_SHORT / DOUBLE_TOP) | **(c) Conditions unreachable** + auth SKIP on Trend_Normal. "Adam" peak width≤2 is easier than Eve, but still needs 2 symmetric swing-high pivots + clean neckline + breakdown inside ~19 bars. | `double_bt.py:258` `w1>2 or w2>2 → continue`; auth `DOUBLE_TOP_AA_SHORT/Trend_Normal = SKIP` `auth_table_v1.py:83`. | **BUG — should fire rarely.** Closest to firing of the four; verify with a detector probe before relaxing. |
| **VSA** | **Not a pattern (mislabeled).** It is volume-gate **Variant A** inside the Reactive detector, selected by `S2_VSA_VOLUME=1`. It DID participate in every Reactive fire (50 of them). | `five_min_system.py:621` `_vsa_pass`; `:630-638` variant selector; flag ON `docs/FLAG_INDEX.md` `S2_VSA_VOLUME`. | **Not a bug.** Working as designed; it has no own `pattern_id`. |
| **EXPANSION** | **Not a pattern (mislabeled).** It is the bar-1 range gate **inside Initiative**. INITIATIVE fired 18×. | `five_min_system.py:759` `b1_expansion = _exp_min ≤ b1_range ≤ _exp_max`; `get_expansion_range` `:115-129`. | **Not a bug.** Working as designed; no own `pattern_id`. |

---

## 3. Why the H&S / Double detectors never trigger (the load-bearing detail)

The day-type gate is **NOT** the cause. `S2_CHART_ALL_DAYTYPES=1` is set in
`.env` (confirmed `docs/FLAG_INDEX.md` → **ON**), so
`chart_patterns_allowed()` returns `True` for every day_type except
`UNKNOWN`/`Nontrend` (`five_min_system.py:107-108`). The chart-pattern branch
(`:1037`, `:1049`) ran on all of Variation/Trend_Normal/Normal — proven by the
5 Flag fires from the same branch. So the four reversal detectors were *called
on real bars and returned `(None, 0, {})` every time.*

Three compounding strictness sources:

1. **H&S shoulder symmetry is ~1 tick** (`head_shoulders.py:102-103`).
   `asymmetry = |LS − RS| / head_depth ≤ 0.05`. For a typical 5-pt-deep head the
   two shoulders must be within `0.05 × 5 = 0.25pt = 1 tick`; for a 3-pt head,
   within **0.6 tick** — unsatisfiable on the 0.25 grid. Real swing highs/lows
   almost never align this tightly. This alone explains zero H&S across 3 weeks.

2. **Effective search window ≈ 19 bars, not 30.** `_bar_buffer` is hard-capped
   at 20 (`:971-972`) and detection uses `buffer[:-1]`. The detectors advertise
   `SEARCH_WINDOW=30` (`head_shoulders.py:27`, `double_bt.py:31`) but can never
   see it. H&S (`MIN_BARS_REQUIRED=12`, needs 3 swing lows each ±2 bars) and
   Double (`=10`, 2 swing lows) are squeezed into the short end of their
   Bulkowski ranges, collapsing the multi-pivot match probability.

3. **ATR-relaxation is partially dead-wired.** With `S2_ATR_RELATIVE=true`:
   - `get_trough_tolerance()` **is** used (Double widths, `double_bt.py:99,117`).
   - `get_head_min_ext_ticks()` (`head_shoulders.py:39`),
     `get_pole_min_height_ticks()` / `get_flag_max_height_ticks()`
     (`flags.py:49,56`) are **defined but never called** — the detectors use the
     fixed constants (`head_shoulders.py:174,244`; `flags.py:93,125`). And
     `SHOULDER_SYM_PCT` has no ATR path at all. So the tightest H&S gates run at
     fixed strict values regardless of the flag.

**Auth-table interaction (secondary, only on Trend_Normal):** even if geometry
triggered, all four reversal patterns are `SKIP` on `Trend_Normal`
(`auth_table_v1.py:62,69,76,83`), so `emit_t1_setup` short-circuits
(`setup_emitter.py:62-67`) for the 26 Trend_Normal bars. On `Variation`/`Normal`
(47 fire-bars) they would emit — INVERSE_HNS/HNS_TOP `REDUCED/FULL`, both
Doubles `FULL` — so the auth table is **not** the binding constraint; geometry
is.

---

## 4. Distinguishing "wired but never triggers" vs "not wired"

| | INVERSE_HNS | HNS_TOP | DOUBLE_BOTTOM_EE | DOUBLE_TOP_AA |
|---|---|---|---|---|
| Imported | ✅ `:20-21` | ✅ | ✅ | ✅ |
| Called in active loop | ✅ `:1038` | ✅ `:1040` | ✅ `:1043` | ✅ `:1045` |
| Day-type-gated open | ✅ (flag ON) | ✅ | ✅ | ✅ |
| **Geometry ever matched** | ❌ | ❌ | ❌ | ❌ |

All four are **fully wired and reachable** — the failure is geometric
non-triggering, category **(c)**, not (a) wiring.

---

## 5. Verdict summary

- **BUGS (should fire, but geometry/window/dead-wiring blocks them):**
  `INVERSE_HNS_LONG`, `HNS_TOP_SHORT`, `DOUBLE_BOTTOM_EE_LONG`,
  `DOUBLE_TOP_AA_SHORT`. Primary lever: relax H&S `SHOULDER_SYM_PCT` (or wire
  the ATR helpers), raise the 20-bar buffer cap, relax the Eve width gate.
- **Mislabeled non-patterns (working as designed, no own pattern_id):** `VSA`
  (Reactive volume variant), `EXPANSION` (Initiative range gate). Not bugs.
- **Legitimately rare vs intentionally-off:** none of the four are
  intentionally disabled. They are *unreachable-in-practice* under current
  thresholds — i.e. the design produced near-zero fire probability, which on a
  3-week window reads as "never". Recommend a **detector probe** (replay shadow
  bars through each detector with logging) before any threshold change, per
  Pre-LIVE "diagnose first" — do not relax blind.

**Caveat (Source-of-Truth):** this diagnosis reads code + the provided dump. It
does **not** prove the detectors were *evaluated* on every bar (e.g. if
`current_day_type` was `None`/`UNKNOWN` in `DAY_TYPE_MODE`, the 5a branch is
silently skipped — `five_min_system.py:1027-1036`). The fact that BULL/BEAR
Flag fired confirms the branch executed on ≥5 occasions, but a probe over the
full bar history is the authoritative next step to separate "evaluated and
no-match" from "branch skipped".
