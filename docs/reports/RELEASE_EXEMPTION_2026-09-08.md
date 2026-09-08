# RELEASE-GATE EXEMPTION — is there a mechanical bar that deserves to pass?

**Date:** 2026-09-08 · **Author:** cowork-dev · read-only (no code, service, flag, order touched)
**Question:** not "should `awaiting_release` be looser" — that was already answered (ratio 0.83,
`docs/reports/ASYMMETRY_17D_2026-09-08.md`). **Is there a predicate, computable at a bar's close,
that releases the handful of blocks worth releasing and leaves the rest held?**

---

## 1 · What the gate actually requires

`backend/v9/systems/release_gate.py` · consumed at `backend/v9/gateway/trading_gateway.py:2675-2681`
(`result["blocked_by"] = "awaiting_release"`, then `return` — **the chain stops here**, so nothing
below was ever evaluated). Live parameters (`.env`, `RELEASE_ENTRY_GATE_V1=1`):

| env | value | used at |
|---|---|---|
| `RELEASE_MIN_HIGHER_LOWS` | **2** | `release_gate.py:152` |
| `RELEASE_VOL_WINDOW` | **3** | `:153` |
| `RELEASE_VOL_RATIO` | **0.75** | `:154` |
| `RELEASE_ZONE_POINTS` | **8** | `:155` |
| `RELEASE_MAX_BARS` | **24** | `:156` |
| `RELEASE_STOP_BUFFER_POINTS` | **1** | `:239` |
| `RELEASE_TREND_BYPASS_PTS` | **12** | `:265` `trend_bypass` |
| `RELEASE_LEG_EXEMPT_V1` | **1** | `trading_gateway.py:2629` |
| `DELTA_BREAKOUT_RELEASE_V1` | **shadow** (logs, never releases — `:126-135`) | `release_gate.py:84` |

Three conditions on closed 5-min bars, **all required**: (1) STRUCTURE — ≥2 consecutive higher lows
(lower highs short) since the window extreme (`:186-191`); (2) EXHAUSTION — mean volume of the last
3 bars ≤ 0.75 × the extreme bar's volume (`:193-205`); (3) RELEASE — the last bar CLOSES beyond the
8-pt rotation zone **on volume above that contracted mean** (`:228-236`). A V-reversal path
(`:203-225`) substitutes conviction for contraction: structure turned **and** close ≥ 1.5 zone-widths
past the edge. Two upstream exemptions fire before any of it: `trend_bypass` (|last − session open| ≥ 12
with the move) and `_live_leg` (`trading_gateway.py:112-139`).

**Why each refusal string fires** — 1,145 raw `awaiting_release` records in the archive:

| reason (`release_gate.py` line) | raw n | deduped n | meaning |
|---|---|---|---|
| `structure not turning (h/2 higher lows)` `:190` | 373 | 53 | the market is still probing the extreme |
| `still active in the zone (vol r > 0.75)` `:226` | 270 | 16 | volume has not dried up |
| `not enough bars (n)` `:159` | 185 | 0 | fewer than `min_hl+vol_window` = 5 bars in the 30-bar pull |
| `only n bars since the extreme` `:181` | 155 | 16 | the extreme is too recent |
| `left the zone without volume` `:236` | 130 | 25 | closed out, but on ≤ the contracted mean |
| `has not left the zone` `:231` | 32 | 6 | close still inside ±8 pt |

---

## 2 · Population (`/tmp/relx/build.py`)

`~/SierraChart_Data/v9_export/decisions_archive/gateway_decisions.*.jsonl`, 20 files whose records
span **2026-07-28 → 2026-09-04**. 1,145 `blocked_by="awaiting_release"` → 818 inside RTH
(ET 09:30–15:59) with bars → **705 carry `mfe_track{stop,t1}`**, i.e. the system's own structural
stop and first target; those exist only on **10 sessions, 08-24 → 09-04**. The other **189 in-RTH
blocks across 18 earlier sessions (07-28 → 08-21) are excluded, not scored with a synthesized stop**
(Rule 1 — honest missing).

**De-duplication.** Key = `candidate_id`, else `(day, system, pattern, direction, entry)`; then
collapsed to one per `(day, system, pattern, direction, signal-bar)`, keeping the earliest.
705 → 181 (candidate_id alone) → **116 candidates**. The published 150 sits between the two, on a
9-session slice; this population is a superset under a stricter collapse.

**Forward scoring** (`/tmp/relx/score.py`). Bars = `v9_bars_5min_woodies`, RTH only, `ts` = bar OPEN.
Walk starts at the first bar opening **strictly after** the block, so no bar containing the decision
is used. Stop-first / T1-first / still-open-at-15:55 (marked at that close). Same-bar stop+T1 →
**STOP** (conservative). **$ at 2 contracts = pts × $10** (MES $5/pt). Shorts: pts = entry − exit;
asserted in code — every STOP row is negative, every T1 row positive (`score.py` assertions).

**Base rate — read this before any predicate below: T1-first 60 / STOP-first 39 / OPEN 17 →
`precision = 0.517`, n = 116.** Σ realised = **+$1,780.20**; Σ max-favourable-excursion = $10,665.00.
Robustness: including the containing bar → identical (0.517 / $1,780.20); resolving same-bar ties as
T1 → 0.543 / $2,307.70. The same population under the published *saved-vs-blocked* metric gives
saved $4,451 / blocked $5,931 = **ratio 0.75**, consistent with the published 0.83 at a different N.

---

## 3 · Predicates — all seven fixed in writing before any outcome was joined

**a ACCEPTANCE** — the repo's own fingerprint (`backend/v9/systems/re_acceptance.py:38-160`) on the
signal bar: |delta| ≥ 0.7 × session max of the same sign, volume ≥ 0.7 × session max, close in the
extreme quarter, close crosses IB edge / prior VA edge / session open, direction consistent with the
gap. Delta from `v9_bars_cumulative_delta`, **RTH window only** — that filter removes the ~3h-early
duplication; inside RTH only **08-25** has duplicated grid minutes (77), where the last-written row is
used. · **b0 LEG (base)** — `leg_state.detect_leg` on the last 10 closed bars returns a leg agreeing
with the direction. · **b LEG (strict)** — b0 **and** age ≥ 5 **and** |LSMA slope over 4 bars| ≥ 0.25
pt/bar (the `lsma_flat` threshold). · **c REFERENCE** — entry within **2.0 pt** of IB high/low (after
10:30 ET), prior-day VAH/VAL/POC, or the session extreme so far. · **d DISPLACEMENT BAR (mine, stated
before measuring)** — signal-bar range ≥ 1.25 × the median range of that session's prior RTH bars
(≥6 needed) **and** close in the extreme quarter **and** close beyond the *previous* bar's extreme;
rationale: the gate models rotation, and a wide bar closing at its extreme through the prior bar is
the mechanical opposite of rotation. Uses no delta. · **e NEAR-MISS** — the block's reason shows the
structure leg already passed (`still active` / `has not left` / `left without volume`). · **d∧e**.

| # | predicate | exempts n | T1/ST/OP | **precision** | Σ$ released | Σ$ still blocked |
|---|---|---|---|---|---|---|
| — | *(population base rate)* | 116 | 60/39/17 | **0.517** | +1,780.20 | — |
| a | ACCEPTANCE (re_acceptance) | **0** | — | — | 0.00 | +1,780.20 |
| b0 | LEG agrees (base) | **0** | — | — | 0.00 | +1,780.20 |
| b | LEG strict (age ≥5, slope ≥0.25) | **0** | — | — | 0.00 | +1,780.20 |
| c | entry ≤2 pt from a named reference | 20 | 6/8/6 | **0.300** | **−371.70** | +2,151.90 |
| d | DISPLACEMENT BAR (mine) | **4** | 4/0/0 | **1.000** | +505.85 | +1,274.35 |
| e | gate near-miss (structure passed) | 47 | 22/14/11 | **0.468** | +739.40 | +1,040.80 |
| d∧e | both | 2 | 2/0/0 | 1.000 | +301.25 | +1,478.95 |

---

## 4 · Verdict

**No exemption clears the bar on this data.** The test was n ≥ 10 **and** precision meaningfully above
0.517 **and** Σ$ released > 0. Of the seven, only **d** beats the base rate at all (4/4, +$505.85) and
it fails n ≥ 10 by six. **a, b0 and b release nothing.** **c and e reach n but their precision is
below the base rate** — releasing on them is worse than releasing at random from the same pool.

Two findings are worth more than the null result:

* **c is an argument for the gate, not against it.** Candidates whose entry is glued to a named
  reference reach T1 first only 30% of the time and lose **$371.70**; the complement (n=96, entry not
  near any reference) runs 0.562 / **+$2,151.90**. "Price stuck at a level" is exactly what the gate
  was built to hold, and on this data it holds it correctly. If anything moves, it is a *tightening*.
* **b0 = 0 is structural, not a null.** `RELEASE_LEG_EXEMPT_V1` shipped in `5a8047cb` (2026-08-14) —
  before every session in this population — so a with-leg candidate is exempted at
  `trading_gateway.py:2629` and can never appear as a block. Nine `release-gate LEG EXEMPT` lines in
  `/tmp/backend.err.log` (09-07 16:55 → 19:55) prove the path fires live. **A leg-based exemption has
  nothing left to release**; a stricter one is strictly emptier.

**Failed, and why.** **a** — the funnel over 116: 13 have no closed signal bar, 6 no delta on the
grid, 23 delta on the wrong side, **62 fail `delta_frac ≥ 0.7`**, 6 volume, 5 close-position; exactly
1 survives to the edge test and fails it. A bar the gate calls "still rotating" is almost never a
session-max-delta bar — the two detectors are near-disjoint by construction. **b/b0** — above.
**e** — the gate's own refusal string carries no forward information: precision by reason runs
0.438 (`still active`) · 0.480 (`left without volume`) · 0.500 (`has not left`) · 0.547
(`structure not turning`) · 0.562 (`bars since the extreme`) — a 12-point spread around a 51.7%
base, on cells of 6–53. **d∧e** — n=2.

**On d, and the temptation.** Its parameter curve is monotone and it does not vanish: 1.10×/0.75 gives
n=10, precision 0.700, +$721.05; 1.00×/0.60 gives n=15, 0.600, +$692.15. Dropping the prior-bar-break
leg collapses it (n=15, 0.533) — the *break*, not the width, is what carries. **But 1.25× was the
pre-registered threshold and it returns n=4. Any looser threshold quoted above was chosen after seeing
the outcomes and is hindsight; it does not license a flag.** The honest next step is `RE_ACCEPTANCE`'s
own protocol — shadow the predicate for 20 sessions, then measure, then rule. d also catches 2 of the
six-day moments (08-28 10:21 ET ZLR LONG and 08-28 11:40 ET DOUBLE_TOP_AA_SHORT), which is why it is
worth shadowing rather than discarding.

**What must not be concluded.** The chain returns at the first blocker, so ~20 gates downstream never
saw these 116. Every "Σ$ released" above is *what the bars did after the block*, at 2 contracts and one
slot per candidate — never "it would have entered".

---

### Reproduce
```bash
cd ~/Downloads/mems26_web_git && set -a && . ./.env && set +a
python3 /tmp/relx/build.py    # population: archive → RTH → mfe_track → dedup (116)
python3 /tmp/relx/score.py    # forward walk + the 7 predicates (table in §3)
python3 /tmp/relx/sweep.py    # base rate by reason + the exploratory d/c sweeps
python3 /tmp/relx/checks.py   # dedup + scoring-convention robustness, worked examples
python3 /tmp/relx/verify.py   # bar-by-bar walk for individual candidates
```
Sources: `~/SierraChart_Data/v9_export/decisions_archive/gateway_decisions.*.jsonl` ·
`v9_bars_5min_woodies` · `v9_bars_cumulative_delta` · `v9_tpo_sessions WHERE session_type='CASH'`
(`trading_date` is VARCHAR — pass ISO text). Scripts are ephemeral under `/tmp/relx/`; the queries and
predicate bodies they run are the ones written out above.
