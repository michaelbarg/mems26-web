# Woodies (S4) Patterns — SOURCE vs CODE

**Scope:** Remaining Woodies patterns — **ZLR, TT, GB100, VEGAS, GHOST, FAMIR**.
(TLB, HTLB, HFE already done — skipped. **DBDT** is **not a Woodies pattern** — see note below.)

**Sources:**
- SOURCE spec = `docs/spec_authority/S4_WOODIES_TABLE_A_Pattern_Setup.csv` (Table A, 9 patterns, 2026-05-23) + narrative in `docs/research/S4_WOODIES_RESEARCH_DELIVERABLE_2026-05-23.md` and `docs/v9/MEMS26_WOODIES_SPEC_V1_DERIVED.md`.
- CODE = `backend/v9/systems/woodies/patterns/<name>.py` + shared `backend/v9/systems/woodies/anti_patterns.py`.

> **DBDT note:** "DBDT" does **not** exist in the S4 Woodies catalog. The Table-A CSV defines exactly **9** patterns: ZLR, TLB, TT, GB100, VEGAS, GHOST, FAMIR, HTLB, HFE. There is **no `dbdt.py`** detector. The only `DBDT` token in the repo is `backend/v9/systems/daytype_playbook.py:75`, where it is a **day-type** bucket code (`DOUBLE_BOTTOM`/`DOUBLE_TOP`/`DB_EE`/`DT_AA` → `"DBDT"`), i.e. an S1 day-type classification, not an S4 entry pattern. Nothing to compare.

---

## Summary table

| Pattern | Group | Code exists? | Biggest gap |
|---------|-------|--------------|-------------|
| **ZLR** | CONT | ✅ `zlr.py` | Stage-1 extreme floor is **±100 by default** (`ZLR_CCI_MIN`), but spec requires a bar past **±200** ("could be the only Woodies trade for your career"); no SWI/CZI/TCCI-leads confirmation; no trend-state / lunch / FOMC gate in detector |
| **TT** | CONT | ✅ `tt.py` | Confirms with **EMA-34 / Stage-1 / Stage-2-pause-3-9-bars** none enforced; uses `trend_state==BLUE/RED` + a hard-coded `cci6 vs cci14 +5` touch/bounce that is **not** the spec's "both above ZL + close above EMA-34" rule |
| **GB100** | CONT | ✅ `gb100.py` | **CZI light-blue/brown alignment is mandatory in spec, entirely absent in code**; uses 1.0×ATR group (`CONT_MED`) but spec wants **1.2×ATR** (deeper pullback) |
| **VEGAS** | REV | ✅ `vegas.py` | Detects only **double divergence** (price HH/CCI LH); the spec's defining structure — **±200 extreme → cup (recover to ±100) → handle (≥3-bar higher-low)** and entry on **swing-high break** — is not modeled; no day-type (NeuE/NeuC/Norm) gate; no min-bar-20 gate |
| **GHOST** | REV | ✅ `ghost.py` | No **diagonal neckline** and entry is on **CCI < right-shoulder**, not on **neckline break**; **right-shoulder ≤ first-shoulder** required by spec but code requires the opposite-ish (`p3 < p1`) so it is partially there but neckline + above/below-ZL containment missing; no min-bar-20 gate |
| **FAMIR** | REV | ✅ `famir.py` | **No "prior ZLR Stage-3 fire required" precondition** (the pattern's definition is a *failed ZLR*); LSMA gate present (AP9) but **±50-zone "strongest" rule and flip-stop-above-failed-ZLR-bar** not modeled; fires standalone on any near-±200 fade |

**Cross-cutting gaps (all 6):** none of the detectors enforce the **session/time filters** the spec lists per pattern — RTH-only, **skip 12:00–13:30 ET lunch**, **FOMC ±90 min skip**, **min-bar gates** (14 for CONT, 20 for REV), or the **day-type pairing** (CONT→TN/TDD, REV→NeuE/Norm, NT universally ❌). Those gates, if they exist, live **outside** the pattern detectors (gateway / day-type playbook), so each detector fires on geometry alone and relies on a downstream layer to apply discipline.

---

## ZLR

**Source** (CSV row "1 · ZLR | Zero Line Reject", group **CONT**):
- **Entry:** Buy-stop 1T above Stage-3 reversal-bar high. Long conditions: CCI **0–210** at close, prev-bar CCI in **(−100, +100)**, **SWI yellow/green**, **CZI light-blue last 3 bars**, **TCCI leads back up**. Mirror for short. Liran Stage-3: ≥1 bar must have gone past **±200** ("strong-extreme rule").
- **Stop:** 3T below signal-bar low · Cap 1.0×ATR-14 · Floor 4T. **T1** +4T ≈ 1.0R; **T2** ±200 cross opposite; **T3** ±100 cross opposite / trail.
- **Filters:** RTH only · skip 12:00–13:30 ET · FOMC ±90 min · **trend BLUE/RED only, NOT YELLOW/GRAY** · min bar 14.
- **Data needs:** CCI-14, TCCI-6, **SWI, CZI**, EMA-34, LSMA, trend_state.
- **Anti-patterns / failure:** CCI re-enters extreme zone within 3 bars · pullback >12 bars (CCI memory fades).
- Narrative: research deliverable flags 39 unresolved ZLR test failures (P-W3) and that a valid ZLR per Liran needs **≥1 bar past ±200**, not just ±100. YELLOW "should block all 9 patterns."

**Code (`backend/v9/systems/woodies/patterns/zlr.py`):**
- `detect()` (zlr.py:72) requires `len(bars) >= LOOKBACK+1` (LOOKBACK=12, zlr.py:16).
- Runs **AP8** universal CCI-flat (zlr.py:82) and **AP1** ZLR pullback-too-long (>12 bars since extreme, zlr.py:88, anti_patterns.py:44).
- **Stage 1 (LONG):** scans back up to 12 bars for `cci_history[i] >= _zlr_cci_min()` (zlr.py:99-100). `_zlr_cci_min()` (zlr.py:30) reads env `ZLR_CCI_MIN`, **default 100.0** — so the strong-extreme ±200 rule is **off by default**.
- **Stage 2:** `pulled = any(-100 < cci <= 100 ...)` between extreme and now (zlr.py:102-105) — pullback stayed inside the band.
- **Stage 3:** fires on `pulled and current > prev and 0 < current < 200` (zlr.py:107). Direction = LONG; mirror SHORT at zlr.py:166-173 (`cci <= -100`, `current < prev`, `-200 < current < 0`).
- Stop via ATR layers (`CONT_TIGHT`, 1.0×ATR, zlr.py:19) or `STOP_ANCHORS_V2`. Confidence `min(0.9, 0.5 + |cci|/400)`.

**Gaps:**
- **Stage-1 extreme floor is ±100, not ±200.** Default `ZLR_CCI_MIN=100` (zlr.py:37) contradicts the spec/Liran requirement that a valid ZLR have ≥1 bar past **±200**. Flag exists but is OFF, so the detector fires on weak ±100 pokes — exactly the class linked to the 39 unresolved failures.
- **No SWI / CZI / TCCI confirmation.** Spec mandates SWI yellow/green, CZI light-blue (last 3 bars), and "TCCI leads back up." Code uses only CCI-14 geometry — none of SWI/CZI/TCCI is read in `detect()`.
- **No trend-state gate.** Spec is BLUE/RED only, NOT YELLOW/GRAY; `detect()` never inspects `trend_state` for ZLR (unlike TT/GB100). A ZLR in YELLOW/GRAY is not blocked here.
- **No session/FOMC/min-bar-14 gate** inside the detector (RTH, lunch skip, FOMC ±90 min).
- **Upper bound is `< 200`, not the spec's `≤ 210` cap** on the signal bar (minor; Liran/Zohar +210 cap not modeled).

---

## TT

**Source** (CSV row "3 · TT | Tony Trade / Turbo Touch", group **CONT**):
- **Entry:** Buy-stop 1T above bar where **CCI-14 AND TCCI-6 both close above ZL** (long) **AND price bar closes above EMA-34**. **Stage-1 trend required.** Stage-2 pause: **3–9 bars below ZL, NOT crossing −100** (Liran). Mirror short.
- **Stop:** 3T below signal low · 1.0×ATR · floor 4T. T1 +4T; T2 +200 cross; T3 ZL opposite.
- **Filters:** RTH · lunch skip · FOMC skip · **BLUE/RED only (never GRAY/YELLOW)** · **TCCI gap >5 CCI (Rensink)** · min bar 14.
- **Data needs:** CCI-14, TCCI-6 (>5 gap), **EMA-34**, trend_state.
- **Failure:** TCCI cross <5 CCI gap = incomplete · Stage-2 pause >9 bars = different pattern.

**Code (`backend/v9/systems/woodies/patterns/tt.py`):**
- `detect()` (tt.py:52) requires `len(bars) >= 3`. Runs **AP8** (flat, tt.py:58) and **AP7** TCCI-gap-<5 block (tt.py:64, anti_patterns.py:175 — `|cci_14 − cci_6_tcci| < 5` → blocked, satisfying the Rensink >5 rule).
- **LONG** (tt.py:81): `trend == "BLUE" and cci14 > 0`, then `touched = cci6_prev <= cci14_prev + 5`, `bounced = cci6 > cci14 + 5 and cci6 > cci6_prev`, `was_above = cci6_prev2 > cci14_prev2 + 10`. SHORT mirror at tt.py:141.
- Confidence fixed **0.7** (tt.py:123). Stop `CONT_TIGHT` 1.0×ATR.

**Gaps:**
- **EMA-34 close-confirmation missing.** Spec requires the price bar to close above EMA-34 (long) / below (short). `detect()` never reads an EMA-34 field — only CCI-14/TCCI-6 and `trend_state`.
- **Stage-2 pause window (3–9 bars below ZL, not crossing −100) not modeled.** Code checks only a 3-bar touch/bounce of TCCI vs CCI-14; the spec's "pause 3–9 bars, NOT crossing ±100" duration/depth constraint is absent (so a pause >9 bars — "a different pattern" per spec — still fires).
- **"Both CCI-14 AND TCCI-6 close above ZL" is only partially enforced.** Code requires `cci14 > 0` and a TCCI bounce above `cci14+5`, which implies TCCI>0, but the rule is encoded as a CCI-vs-TCCI *touch/cross* (Turbo-Touch reading) rather than the spec's plain "both above ZL + EMA-34 close" arming. Direction logic is reasonable but not the spec's literal condition.
- **No session/FOMC/min-bar-14 gate** in the detector (GRAY/YELLOW is excluded only implicitly via `trend in {BLUE,RED}`).

---

## GB100

**Source** (CSV row "4 · GB100 | Ghost Bar at ±100", group **CONT**):
- **Entry:** Buy-stop 1T above bar that **crosses +100 back toward trend** (long). Like ZLR but **deeper/faster pullback that crossed ±100**. **CZI must be light-blue (long) / brown (short).** CCI must **NOT stay >6 bars opposite side of ZL**.
- **Stop:** 3T below signal low · **Cap 1.2×ATR-14 (deeper pullback)** · floor 4T. T1 +4T; T2 +200; T3 ZL opposite.
- **Filters:** RTH · lunch skip · FOMC skip · **BLUE/RED only (NOT YELLOW = fake breakout)** · **CZI alignment mandatory** · min bar 14.
- **Data needs:** CCI-14, **CZI**, trend_state.
- **Failure:** Pullback >6 bars opposite ZL → trend flipped, not pullback · YELLOW = fake breakout.

**Code (`backend/v9/systems/woodies/patterns/gb100.py`):**
- `detect()` (gb100.py:52) requires `>=3` bars. Runs **AP8** (flat), **AP2** GB100-in-YELLOW block (gb100.py:64, anti_patterns.py:85), and **AP6** pullback-depth block (gb100.py:69-79: counts consecutive recent bars on the opposite side of ZL; >6 → blocked, anti_patterns.py:155).
- **LONG** (gb100.py:91): `trend == "BLUE" and current > 100 and prev <= 100 and prev2 < 100` — a clean upward cross of +100. SHORT mirror (gb100.py:147).
- Stop group **`CONT_MED`** (gb100.py:18). Confidence `min(0.85, 0.5 + (|cci|−100)/200)`.

**Gaps:**
- **CZI alignment (light-blue long / brown short) is mandatory in the spec and entirely absent in code.** `detect()` reads only `cci_14` and `trend_state`. The single hard "Data needs" field the spec calls out for GB100 — CZI — is not consumed, so the "fake breakout" CZI filter never runs.
- **ATR cap is 1.0×, not the spec's 1.2×.** Pattern group is `CONT_MED` (gb100.py:18); the spec explicitly widens GB100's stop cap to **1.2×ATR-14** for the deeper pullback. (Confirm the multiplier behind `CONT_MED` in `atr_stop.py`; if it is 1.0× this is a real stop-sizing divergence.)
- **YELLOW handled, but lunch/FOMC/min-bar-14 not.** AP2 covers YELLOW; the other listed filters are not in the detector.

---

## VEGAS

**Source** (CSV row "5 · VEGAS | Divergence / Cup-and-Handle", group **REV**):
- **Entry (long):** CCI reaches **≤ −200** → reverses to **≥ −100 (cup)** → forms **higher-low or horizontal ≥3 bars (handle)** → **enter on break of the swing high between cup and handle**. Code-hint in CSV: "SHORT = price HH + CCI LH; swing min 2 bars."
- **Stop:** 3T beyond last swing extreme (REV rule) · **1.5×ATR** · floor 4T. **T1 = Measure × 0.5** (cup-height in CCI × ~1 MES pt / 25 CCI ≈ 16T for a 200-CCI cup); T2 = Measure × 0.6; T3 trail to ZL opposite.
- **Filters:** RTH · lunch skip · FOMC skip · **works in NeuE/NeuC/Norm only** · **min bar 20** (❌ before bar 20).
- **Data needs:** CCI-14, EMA-34, price swings, trend_state.
- **Failure:** Divergence in a strong trend = trap · swings <5 bars apart = noise.

**Code (`backend/v9/systems/woodies/patterns/vegas.py`):**
- `detect()` (vegas.py:71) requires `len(bars) >= 20` (LOOKBACK=20, vegas.py:16) — satisfies min-bar-20 implicitly. Runs **AP8** (flat).
- Finds price/CCI swings via `_find_swings(..., min_swing=2)` (vegas.py:87-88).
- **Bearish (SHORT)** (vegas.py:98): last-two price highs `p2 > p1` AND last-two CCI highs `c2 < c1` (price HH / CCI LH double divergence). **Bullish (LONG)** mirror (vegas.py:167): price LL / CCI HL.
- **AP3** VEGAS-swings-too-close (<5 bars apart → block, vegas.py:104/171, anti_patterns.py:111).
- Stop group `REV` (1.5×ATR per `_PATTERN_GROUP`). Confidence fixed 0.75. `measure_pts` computed from CCI-swing delta /25 (vegas.py:160) — matches the spec's CCI→pts coefficient, but is recorded as metadata, not used for the target.

**Gaps:**
- **Wrong structure: code is pure divergence, spec is cup-and-handle.** The defining VEGAS sequence — **±200 extreme → recover to ±100 (cup) → ≥3-bar higher-low/horizontal handle → entry on the swing-high break between cup and handle** — is **not** modeled. Code fires on any two-swing price-vs-CCI divergence over 20 bars. The ≤−200 trigger, the cup recovery, and the handle are all missing.
- **No day-type gate.** Spec restricts VEGAS to **NeuE/NeuC/Norm** and explicitly warns "divergence in a strong trend = trap." `detect()` reads `trend_state` for nothing here, so a VEGAS in a strong-trend day is not blocked at the detector.
- **Targets use fixed ticks, not the Measure rule.** Spec T1 = cup-height (CCI) × coefficient × 0.5; code uses `TARGET1_TICKS`/`TARGET2_TICKS` from `_pattern_ticks` (vegas.py:23-25) and only stores `measure_pts` as a detail — the measured-move target is computed but not applied.
- **Swing detector min_swing=2** (vegas.py:87) is looser than the spec's swing definition; AP3 then re-imposes a 5-bar gap, so the effective filter is split across two places.

---

## GHOST

**Source** (CSV row "6 · GHOST | CCI Head-and-Shoulders", group **REV**):
- **Entry:** **3 CCI peaks (short) / troughs (long)**. **Diagonal neckline** between shoulders, preferably sloping toward ZL. **Right-shoulder height ≤ first-shoulder.** Head size irrelevant (Liran). **Entire pattern above ZL (short) / below ZL (long).** **Enter on neckline break.**
- **Stop:** 3T beyond right-shoulder extreme · 1.5×ATR · floor 4T. **T1 = Measure × 0.5** (head-to-neckline CCI × coefficient ≈ 16T at 200 CCI head depth); T2 = Measure × 0.6; T3 trail to opposite extreme.
- **Filters:** RTH · lunch skip · FOMC skip · **NeuE/NeuC/Norm** · **min bar 20** (❌ before bar 20).
- **Data needs:** CCI-14, trend_state.
- **Failure:** Trend persistence steamrolls H&S · right-shoulder exceeds first = invalidated.

**Code (`backend/v9/systems/woodies/patterns/ghost.py`):**
- `detect()` (ghost.py:66) requires `len(bars) >= 20` (LOOKBACK=20). Runs **AP8** (flat). No GHOST-specific anti-pattern.
- `_find_extremes()` (ghost.py:53) finds local peaks/troughs over the 20-bar CCI window.
- **Bearish (SHORT)** (ghost.py:82): last three peaks `p1,p2,p3` with `p2 > p1` AND `p2 > p3` AND `p3 < p1` (head highest, right shoulder below left), and **enters only when `current < p3[1]`** (CCI now below the right shoulder). **Bullish (LONG)** mirror (ghost.py:142).
- Stop `REV` 1.5×ATR; `swing_anchor` = max high / min low over 20 bars. Confidence fixed 0.7. `measure_pts` from head-vs-nearest-shoulder /25 (ghost.py:137) stored as metadata.

**Gaps:**
- **No neckline; entry is "CCI past the right shoulder," not "neckline break."** Spec enters on the break of a **diagonal neckline** drawn between the two troughs/peaks flanking the head. Code uses `current < p3` (below the right-shoulder peak) as the trigger — a cruder proxy that fires earlier/differently than a true neckline break, and the "neckline slopes toward ZL" preference is absent.
- **"Entire pattern above ZL (short) / below ZL (long)" not enforced.** Spec requires all three peaks above the zero line (short) / troughs below (long). Code does not check that `p1,p2,p3 > 0` (or `< 0`), so an H&S straddling the ZL still qualifies.
- **Right-shoulder ≤ first-shoulder is enforced (`p3 < p1`), but no equality tolerance** and head-size-irrelevant is fine; however **no day-type gate (NeuE/NeuC/Norm)** and **no trend-persistence guard** ("trend steamrolls H&S" failure mode) — `detect()` reads `trend_state` for nothing.
- **Targets are fixed ticks, not the head-to-neckline Measure × 0.5/0.6** (ghost.py:24-25); `measure_pts` is computed but unused for the target.

---

## FAMIR

**Source** (CSV row "7 · FAMIR | Failed ZLR at ±200", group **REV**):
- **Entry:** **Right after a ZLR Stage-3**, the ZLR **fails** and CCI breaks **sharply opposite within the ±50 zone (strongest)**. Code-hint: "SHORT = max(5 bars) ∈ [170,210) + cur<prev + cur<max−20." **LSMA must support:** ZL green (long) / red (short).
- **Stop:** **Above the failed-ZLR signal-bar high (flip stop)** · 1.5×ATR · floor 4T. T1 +4T; T2 opposite ±100; T3 opposite ±200 / ZL re-cross.
- **Filters:** RTH · lunch skip · FOMC skip · **LSMA agreement mandatory** · **prior ZLR required** · min bar 14 (rare in first hour — needs a prior ZLR fire).
- **Data needs:** CCI-14, **LSMA, lsma_above_price**, trend_state.
- **Failure:** LSMA not aligned at entry · failure outside ±50 zone = weaker setup.
- Narrative: Liran calls FAMIR "mentally hardest pattern"; by definition it can **only fire AFTER a Stage-3 ZLR**.

**Code (`backend/v9/systems/woodies/patterns/famir.py`):**
- `detect()` (famir.py:53) requires `>=5` bars. Runs **AP8** (flat).
- **SHORT** (famir.py:72): `max_recent (last 5 CCI) >= 170 and < 210` AND `current < prev and current < max_recent − 20` → approached +200 and is fading. **LONG** mirror (famir.py:135) with `min_recent <= −170 and > −210`.
- **AP9** FAMIR-LSMA-mismatch (famir.py:75/138, anti_patterns.py:231): SHORT needs `lsma_above_price == True`, LONG needs `== False` — the spec's LSMA-agreement gate **is** enforced.
- `THRESHOLD=200`, `NEAR_THRESHOLD=170` (famir.py:15-16). Stop `REV` 1.5×ATR; `swing_anchor` = max high / min low over **last 5 bars** (famir.py:80). Confidence `min(0.8, 0.5 + (200−|peak|)/100)`.

**Gaps:**
- **No "prior ZLR Stage-3 fire required" precondition.** FAMIR is *by definition* a **failed ZLR** ("right after a ZLR Stage-3"). Code fires on **any** near-±200 fade with no link to a preceding ZLR detection — so it triggers in contexts the spec would not call FAMIR at all. This is the single largest divergence.
- **No ±50-zone "strongest" qualifier.** Spec says the sharp opposite break should occur **within ±50** of ZL for the strongest setup (failure outside ±50 = weaker). Code only checks the near-±200 fade (`max−20`) and never tests where the reversal lands relative to ±50.
- **Stop anchor is the 5-bar swing extreme, not the spec's flip-stop above the failed-ZLR signal bar.** Without a tracked "failed-ZLR signal bar," the code cannot place the flip stop the spec specifies; it substitutes the 5-bar high/low (famir.py:80,143).
- **Min-bar-14 / lunch / FOMC gates not in the detector** (LSMA agreement via AP9 is the only spec filter actually enforced).

---

## Bottom line

All six remaining detectors implement a **CCI-geometry core** with shared **AP8 flat-check** plus a couple of pattern-specific anti-patterns (AP1/ZLR, AP2+AP6/GB100, AP3/VEGAS, AP7/TT, AP9/FAMIR), and ATR-based stops. The consistent shortfalls versus the SOURCE spec are:

1. **Study-field confluence is mostly missing** — SWI/CZI/TCCI-leads (ZLR), CZI (GB100), EMA-34 (TT), LSMA (present only in FAMIR via AP9). The detectors lean on CCI-14 + `trend_state` and ignore the auxiliary studies the spec lists under "Data needs."
2. **Two REV patterns model the wrong shape** — VEGAS is coded as plain divergence, not cup-and-handle; GHOST enters on "past the right shoulder," not on a neckline break, and doesn't enforce above/below-ZL containment.
3. **FAMIR has no ZLR-failure precondition**, so it is not actually the spec's "failed ZLR" pattern.
4. **Day-type, session (RTH/lunch/FOMC), and min-bar gates are absent from the detectors** — they must be (and may be) applied downstream in the gateway / day-type playbook; verify there before trusting that the discipline is enforced.
5. **Measured-move targets** for VEGAS/GHOST are computed (`measure_pts`) but **not applied** — fixed tick targets are used instead.
