# Cascade Audit — S1 → S2/S4 → Targets (2026-06-23)

**Mode:** DIAGNOSIS-ONLY (read-only). No code, `.env`, DB, or services changed.
**Question (Michael):** S2 (5-min) and S4 (Woodies) fire out of accordance with (a) their
own decision trees and (b) the day-type characterization. Intended cascade: **S1 sets the
day-type AND defines HOW to trade it → S2/S4 fire ONLY in accordance with the day-type →
patterns set profit/loss targets per day-type + the trade's opportunity.** Find WHY the
cascade isn't respected, grounded in code + the 06-22 fires.

**Evidence base:** `tools/replay_data_2026-06-22.json` (19 fires), `docs/reports/TRADES_TODAY_2026-06-22.md`
(per-trade narrative + patterns), `.env` (flag state), and the live code surfaces below. All
file:line refs are to the repo as of 2026-06-23.

---

## TL;DR — the cascade is broken at the JOINT, not the parts

S1 classifies fine. S2/S4 fire on pure geometry (by design — they never consult day-type in
their own logic). **The alignment layer that is supposed to translate "day-type → which
patterns may fire" is the gateway, and the specific gate Michael approved to do that job
(`DAYTYPE_PLAYBOOK`, the pattern×day-type SKIP matrix) is SHORT-CIRCUITED to a no-op the moment
`DAYTYPE_POSITION_GATE=1` is set — which it is.** The position gate that runs instead is
**pattern-blind**: it only checks `direction × price-vs-POC/IB`. So "HFE is a reversal, SKIP it
on a Variation/Trend day", "ZLR SKIP on Nontrend", "REACTIVE only with-trend on a trend day" —
none of those rules execute. That is the root hole. On top of it, on **06-22 the three new
gates (`OPENING_TYPE_GATE`, `DEDUP_FIRE_GUARD`, `NONTREND_WIDTH_FLOOR`) were only flipped ON
mid-session (evening `.env` edit), so they were OFF for the entire 08:30–10:20 fire window** —
the day ran effectively gate-light.

---

## 1. THE 06-22 FIRES (data)

Day-type for 06-22 = **`Normal_Variation`** (canonical 7-type, per-bar) → maps to **`Variation`**
for the playbook/gates (`day_type_timeline.final.day_type` in the replay JSON;
`trade_context.py:524` maps `Normal_Variation`→`Variation`). Opening type = **`OPEN_DRIVE`**
(replay JSON `opening_type`). Levels: **IBH 7599.25 · IBL 7560.5 · POC 7544.25 · VAH 7548.25 ·
VAL 7543.25** (replay JSON `levels`). Early bars classified **FORMING** (before IB lock) then
**Normal**, settling **Normal_Variation** with `direction: with_extension`.

**Critical timing caveat — gates were OFF when these fired.** `.env` mtime is 2026-06-22 **17:22**
(evening). `OPENING_TYPE_GATE=1`, `DEDUP_FIRE_GUARD=1`, `NONTREND_WIDTH_FLOOR=1`, and
`S1_ENGINE_NEW_CLASSIFIER=1` carry the comment "Michael approved 2026-06-22, mid-session". The
fire window was 08:30–10:20 CT (morning). So for the actual trades, the only alignment gate live
was `DAYTYPE_POSITION_GATE` (+ the now-superseded legacy gates) — and that gate is pattern-blind
(§5). Every fire in the export shows **`blocked_by=None`** (replay JSON) — nothing was vetoed.

**Per-fire table** (system + pattern + day_type from `TRADES_TODAY_2026-06-22.md` §1, which read
the real DB column; the replay JSON's `pattern_id`/`day_type` came back `None` because the export
pulled the nested null copy — see §3 of that report, the *column* is correct):

| id | Time CT | Sys | Pattern | Dir | Entry | Loc vs structure | day_type col | blocked_by | Outcome / PnL |
|----|---------|-----|---------|-----|-------|------------------|--------------|------------|---------------|
| 188 | 08:30 | S4 | TLB | SHORT | 7572.50 | mid-IB (pre-break, into BLUE up-bar) | Nontrend | None | LOSS −108.75 |
| 190 | 08:35 | S4 | TLB | SHORT | 7577.50 | mid/upper-IB (into up-thrust) | Nontrend | None | LOSS −202.50 |
| 191 | 08:50 | S4 | HFE | SHORT | 7591.50 | upper-IB | Nontrend | None | WIN +39.00 |
| 193 | 08:55 | S4 | HFE | SHORT | 7586.00 | upper-IB (re-test highs) | Nontrend | None | LOSS −172.50 |
| 194 | 09:05 | S4 | HFE | SHORT | 7593.50 | top-IB (at the highs) | Nontrend | None | LOSS −71.25 |
| 195 | 09:40 | S2 | INITIATIVE_SHORT | SHORT | 7551.00 | below-IB (breakdown, trend→RED) | Variation | None | WIN +94.38 |
| 196 | 09:45 | S2 | INITIATIVE_SHORT | SHORT | 7550.50 | below-IB (2nd breakdown) | Variation | None | WIN +141.88 |
| 197 | 10:10 | S2 | REACTIVE_SHORT (B_RVOL) | SHORT | 7538.50 | far-below-IB, at VAH-edge (fade) | Variation | None | LOSS −138.75 |
| 199 | 10:20:03 | S2 | REACTIVE_SHORT (B_RVOL) | SHORT | 7537.75 | far-below-IB | Variation | None | LOSS −127.50 |
| 200 | 10:20:05 | S2 | REACTIVE_SHORT (B_RVOL) | SHORT | 7537.75 | **dup of 199 (2s apart)** | Variation | None | LOSS −127.50 |
| 201 | 10:20:05 | S4 | ZLR | SHORT | 7538.00 | far-below-IB (same bar as cluster) | Variation | None | LOSS −146.25 |
| 202 | 10:30 | S2 | REACTIVE_SHORT | SHORT | 7539.75 | far-below-IB | Variation | None | LOSS −120.00 |
| 203 | 10:50 | S2 | REACTIVE_SHORT | SHORT | 7540.50 | far-below-IB | Variation | None | WIN +51.25 |
| 205 | 11:05 | S2 | REACTIVE_SHORT | SHORT | 7533.75 | below POC | Variation | None | LOSS −172.50 |
| 206 | 11:25 | S4 | (woodies) | SHORT | 7541.25 | — | Variation | None | +3.12 |
| 208 | 11:25 | S2 | REACTIVE_SHORT | SHORT | 7541.75 | — | Variation | None | +5.62 |
| 209 | 13:00 | S2 | REACTIVE_SHORT | SHORT | 7542.75 | — | Variation | None | +10.62 |
| 211 | 14:00 | S2 | REACTIVE_SHORT | SHORT | 7532.75 | below POC | Variation | None | LOSS −191.25 |
| 212 | 14:45 | S2 | REACTIVE_SHORT | SHORT | 7529.50 | below POC | Variation | None | LOSS −78.75 |

**Fires that look OUT OF ACCORDANCE with the day-type:**

1. **188 / 190 (S4 TLB SHORT, 08:30–08:35)** — shorting INTO an `OPEN_DRIVE UP` before any
   breakdown, mid-IB. Counter-drive. Per the intended cascade these should never fire in the
   opening window against the drive. (`OPENING_TYPE_GATE` would block them — but it was OFF.)
   `TRADES_TODAY` §3a/4.1 confirms: "four counter-drive shorts −$555". *Root: opening-type gate
   not live; nothing else inspects opening drive.*
2. **191 / 193 / 194 (S4 HFE SHORT)** — HFE is a **reversal** pattern (playbook `group: REV`,
   `config/daytype_playbook.yaml:` HFE row). On a **Variation/Trend** day the playbook says
   **SKIP** (HFE cells: Trend_Normal SKIP, Trend_DD SKIP, Variation REDUCED). The early batch was
   *stamped* Nontrend (where HFE is also SKIP), so under the playbook **all of 191/193/194 should
   be SKIP or REDUCED**. They fired full. *Root: the playbook matrix is bypassed under the
   position gate (§5); the position gate doesn't know HFE is a reversal.*
3. **197/199/200/201/202/203/205/208/209/211/212 (S2 REACTIVE_SHORT + 201 ZLR)** — a wall of
   **REACTIVE** (mean-reversion fade) shorts on a `with_extension` Variation day. REACTIVE on a
   directional day should be `require_with_trend` (playbook REACTIVE row). They are with the
   downtrend so direction is defensible, **but** the fade-the-bounce thesis on an extension day is
   exactly what the playbook's REV-pattern discipline is meant to throttle, and **the position
   gate lets them all through** because entry is below POC = "correct side" for a SHORT (§5).
4. **199 = 200 (exact double-fire)** + **four shorts stacked on the 10:20 bar (197/199/200/201)** —
   not a day-type misalignment per se, but the same un-gated firing surface: no dedup, no
   already-positioned guard at fire time (DEDUP was OFF). `TRADES_TODAY` §3d.

**Net (closed, morning):** ~−$280; the day's edge was the two post-break INITIATIVE shorts
(195/196, +$236); the pre-break S4 top-picking (188/190/193/194, −$555) was the drag.

---

## 2. S1 — DAY-TYPE (the conductor) — **KEEP** (classification) / the "HOW to trade" output is **incomplete**

**What S1 outputs.** The validated 7-type classifier is canonical:
`GET /api/v9/day_type/classify_replay` → `classifier_core.classify_session(...)`
(`docs/SOURCE_OF_TRUTH.md` §Day-type). The live per-bar engine (`app.state.day_type_machine`)
historically only emitted 3 types (Trend_Normal/Variation/Normal) until `S1_ENGINE_NEW_CLASSIFIER`
went live (it's now `=1`, flipped 06-22 mid-session). 06-22's classification is **trustworthy**
(replay timeline shows clean FORMING→Normal→Normal_Variation progression; IB from `sierra_tpo`,
not synthesized) — the known `v9_bars_5min` feed-gap (09:00–09:35) did **not** recur per
`TRADES_TODAY` §2 correction.

**Does S1 expose a machine-readable "HOW to trade today" mode the others consume? PARTIALLY — and
the part that matters for firing is NOT consumed.**
- The replay timeline carries a `direction` field per segment (`fade_both` / `with_extension`) —
  a "how to trade" hint — but this is a **display/replay artifact**, not something the firing path
  reads.
- The real "how to trade per day-type" rulebook lives in **`config/daytype_playbook.yaml`**
  (`daytype_style` block: target style, ref_points, bias, contracts, runner per day-type) +
  the `patterns` SKIP/REDUCED matrix. **But the gateway only consults the matrix via
  `daytype_playbook.decide()`, which is short-circuited (§5/§6).** The `daytype_style` block is
  consumed ONLY by `structural_targets.py` for *targets*, never for *firing permission*.
- At fire-time the gates receive a **single string** `day_type_at_entry`
  (`trade_context.extract_g1_entry_context`, `backend/v9/services/trade_context.py:487`,
  promoted via `S1_NEW_CLASSIFIER` block at `:511-525`). There is **no "mode/playbook object"**
  threaded through — just the label. The conductor hands over a one-word cue, not a score.

**Classification = KEEP.** "HOW to trade" exists as config but is **not wired to firing**
(only to targets). That disconnect is the spine of the problem.

---

## 3. S2 DECISION TREE — **KEEP as detector** (by-design geometry; no day-type awareness)

`backend/v9/systems/five_min/five_min_system.py`:
- `_detect_reactive` (`:580-720`) and `_detect_initiative` (`:722-826`) fire on **pure price/volume
  geometry**: 4-bar VSA/RVOL structure, expansion ranges, belly/POC confirms. **Neither function
  references `self.current_day_type`.** Grep of both bodies: the only env checks are
  `S2_REQUIRE_COT_AMT` (S3 independence) and `S2_VSA_VOLUME` (variant). No day-type term.
- The class DOES hold `self.current_day_type` (`:206`, hydrated `:261-289`, updated `:415-426`),
  and the **chart-pattern** path (Pkg 5a/5c, `chart_patterns_allowed`, `:98-109`, `:996-1049`)
  *does* gate on day-type — but that governs the **chart-pattern family (FLAGS/HnS/etc.)**, NOT the
  core REACTIVE/INITIATIVE OFA fires that produced 06-22's trades.
- **Conclusion (answers Michael's Q3):** S2's REACTIVE/INITIATIVE logic fires on geometry and
  **relies entirely on the EXTERNAL gateway gates for day-type alignment.** This is the intended
  separation-of-concerns; the detector is not the bug. The bug is that the external gate doesn't
  enforce the pattern×day-type rule.

**KEEP** the detector. (The alignment must come from the gateway, not from bolting day-type into S2.)

---

## 4. S4 DECISION TREE (Woodies ZLR/HFE/TLB) — **KEEP detector / ADAPT its day-type touch-point**

- Pattern detectors `backend/v9/systems/woodies/patterns/zlr.py` (`detect`, `:72`) and
  `hfe.py` (`detect`, `:189`) take a `context` dict but **do not branch on day-type** (no
  `day_type` reference in either).
- S4's **only native alignment** is the **trend_state (CCI color) A1 gate**, and it is weak:
  `decision_tree.py:_a1_trend_gate (:175-189)` — **YELLOW** blocks all 9 patterns; **GRAY** blocks
  only if best confidence `< 0.55`; **BLUE/RED** always pass. So on 06-22, ZLR/TLB/HFE could fire
  in GRAY as long as confidence ≥ 0.55, and freely in colored trend. This is the "GRAY = mostly
  no-fire" behavior `TRADES_TODAY` §3a describes (the 09:15–09:35 gap), but it is a **trend-color**
  gate, not a **day-type** gate.
- The **day-type touch-point** exists but is explicitly **advisory**:
  `backend/v9/systems/woodies/stages/a2_day_type_query.py:1-9` — *"Touch-Point (advisory only ·
  NEVER vetoes) · terminal is always None"*. There is a full **63-cell day-type×pattern matrix**
  (`woodies/day_type_gate.py`, `DayTypeGate`/`MatrixVerdict`) but A2 emits it as advisory verdicts
  that never block. So S4, like S2, **does not gate its own fires on day-type.**
- **Conclusion (answers Q4):** S4 does NOT consider day-type in its firing decision; its
  self-alignment is trend-color only (and lenient). Day-type alignment must come from the gateway.

**KEEP** the detectors; **ADAPT** A2 — there is already a 63-cell day-type matrix computed and
thrown away as advisory. (Diagnosis only; not proposing the fix.)

---

## 5. THE GATEWAY GATES (alignment layer) — `backend/v9/gateway/trading_gateway.py`

Gates run in `route_setup` in this order. Flag state read from `.env`.

| Gate | file:line | Applies to | Blocks what | Flag in .env | Verdict |
|------|-----------|-----------|-------------|--------------|---------|
| Session window | `trading_gateway.py:112` | S2+S4 | fires outside 08:30–15:00 CT | always on | KEEP |
| Cooldown / SSV | `:119-126` | S2+S4 | post-2-stop cooldown; suffering-side | always on | KEEP |
| **DEDUP_FIRE_GUARD** | `:132-147` | S2+S4 (all modes) | identical sys+dir+pattern+entry(±0.5pt) within 30s | **`=1` (set 06-22 PM — OFF during fires)** | KEEP (was off when 199/200 fired) |
| Layer-0 chop | `:155-161` | S2+S4 | `chop_state==SEARCHING` | unset = OFF (standing) | DEFER (standing-OFF) |
| **OPENING_TYPE_GATE** | `:167-191` → `opening_type_gate.decide` | S2+S4 | counter-drive fires in opening window (pre-IB-lock) | **`=1` (set 06-22 PM — OFF during fires)** | KEEP/ADAPT (would block 188/190) |
| **DAYTYPE_PLAYBOOK** | `:200-217` → `daytype_playbook.decide` | S2+S4 | pattern×day-type SKIP/REDUCED + REACTIVE/HnS with-trend | `=1` | **REPLACE/ADAPT — NO-OP under position gate (root hole)** |
| TREND_DIRECTION_GATE (legacy) | `:223-235` | S2+S4 | counter-trend (CCI) | `=1` but **skipped** when position gate on (`:222-223`) | DEFER (superseded) |
| REACTIVE_LOCATION_GATE (legacy) | `:238-252` | S2+S4 | REACTIVE_LONG above / SHORT below POC | `=1` but **skipped** when position gate on | DEFER (superseded) |
| **DAYTYPE_POSITION_GATE** | `:257-277` → `daytype_position_gate.decide` | S2+S4 | direction × price-vs-POC/IB per day-type | `=1` | KEEP-but-INSUFFICIENT (pattern-blind) |
| DIRECTION_CONTEXT | `:284-297` | S2+S4 | fires against live CVD/breakout direction | unset = OFF (needs backtest #18) | DEFER (flag-OFF) |
| DAYTYPE_TARGETS_STRUCTURAL | `:303-332` → `structural_targets` | S2+S4 (targets, not veto) | overrides t1/t2/t3 with structural levels | `=1` | KEEP (see §7) |

### The root short-circuit (the single most important finding)

`backend/v9/systems/daytype_playbook.py:104-106`:
```python
# #68: position gate supersedes pattern suppression
if os.environ.get("DAYTYPE_POSITION_GATE", "0").lower() in ("1", "true", "yes"):
    return Decision("FULL", cap, f"position-gate-active (all-patterns-fire)")
```
When `DAYTYPE_POSITION_GATE=1` (it is), **`decide()` returns FULL for every pattern on every
day-type before it ever reads the YAML matrix.** The gateway block at `:200-217` calls this and
gets `allow=True` every time. **So the entire `config/daytype_playbook.yaml` `patterns:` matrix —
HFE/ZLR/TLB/REACTIVE SKIP/REDUCED per day-type, and the `require_with_trend` discipline — is dead
code in the live path.** The design intent ("position gate handles direction; playbook handles
pattern-suppression") was only half-built: the position gate that replaced it does **direction**,
but **nothing replaced the pattern-suppression** half.

### Why the position gate doesn't cover the hole

`backend/v9/systems/daytype_position_gate.py` `decide(...)` takes a `pattern` arg (`:36`) but
**never references it** in any branch (`_decide_normal`, `_decide_variation`, `_decide_trend`,
and the Neutral path all key off `direction` + `entry` vs `POC`/`IB` only). Grep: `pattern`
appears once (the signature), zero times in logic. So:
- It **cannot** distinguish a **continuation** pattern (ZLR/TLB/INITIATIVE — should fire WITH the
  move) from a **reversal** pattern (HFE/REACTIVE/VEGAS — should be throttled on directional days).
- For a **Variation** day (06-22) it allows **any SHORT below IBL** and **any LONG above IBH**
  (`_decide_variation`, `:110-149`). That passed every one of 06-22's below-IB REACTIVE shorts —
  correct *direction*, but it never asked "is a fade pattern appropriate on an extension day?"
- The HFE shorts (191/193/194) at the IB top were stamped *Nontrend* at fire time; the position
  gate's Nontrend branch is `return (True, "Nontrend (playbook handles SKIP)")` (`:57-58`) — it
  **explicitly defers Nontrend SKIP to the playbook** — but the playbook is the no-op above. **So
  Nontrend SKIP is enforced by NOBODY.** This is `SYSTEM_FAULT_AUDIT` fault 3.1 ("Nontrend allows
  ALL fires") seen from the code side.

### Coverage of the position gate (the direction half) — has its own holes
- **Trend / Variation "neither IB edge broken yet" → fail-open** (`_decide_trend:199`,
  `_decide_variation:148`): before the break, ALL directions pass. That is exactly when 188/190
  fired (mid-IB, pre-break) — the position gate could not have blocked them.
- **`session_high/low` for the trend branch** come from `tpo_ctx` (`:168-169`); if absent →
  fail-open. Bar-derived approximations per `PNL_BY_DAYTYPE` caveats.

**Bottom line for §5:** the playbook gate does **NOT** currently encode "fire only in accordance
with day-type" — it is disabled by the position-gate check. The position gate encodes only the
**direction/location** slice and is **pattern-blind**, so the pattern×day-type matrix has a
**100% hole** in the live path (every cell defaults to allow).

---

## 6. PLAYBOOK COVERAGE — the (day_type × pattern) matrix & its live status

`config/daytype_playbook.yaml` **does** define a full matrix (good coverage *on paper*). The
problem is not gaps in the YAML — it is that **the whole YAML is bypassed at runtime** (§5). For
the record, here is the authored matrix (E=FULL, D=REDUCED, S=SKIP) and the live-enforcement status.

**Continuation patterns (S4: ZLR/TLB/TT/GB100/HTLB/FLAGS · S2: INITIATIVE):**

| pattern | Trend_Normal | Trend_DD | Normal | Variation | Neutral_Center | Neutral_Extreme | Nontrend |
|---------|----|----|----|----|----|----|----|
| ZLR | FULL | FULL | RED | FULL | SKIP | SKIP | **SKIP** |
| TLB | FULL | FULL | RED | FULL | SKIP | RED | **SKIP** |
| INITIATIVE | FULL | FULL | RED | FULL | SKIP | SKIP | **SKIP** |
| HTLB / FLAGS | FULL | FULL | RED | FULL | RED/SKIP | RED | SKIP |

**Reversal patterns (S4: HFE/VEGAS/GHOST/FAMIR/DBDT · S2: REACTIVE/HNS):**

| pattern | Trend_Normal | Trend_DD | Normal | Variation | Neutral_Center | Neutral_Extreme | Nontrend |
|---------|----|----|----|----|----|----|----|
| **HFE** | **SKIP** | **SKIP** | RED | **RED** | FULL | FULL | **SKIP** |
| VEGAS/GHOST/FAMIR | SKIP | SKIP | FULL | RED | FULL | FULL | SKIP |
| DBDT | SKIP | RED | FULL | RED | FULL | FULL | SKIP |
| **REACTIVE** | FULL* | FULL* | FULL | FULL | FULL | FULL | **SKIP** | (*require_with_trend) |
| HNS | RED* | RED* | FULL | FULL | FULL | FULL | SKIP | (*require_with_trend) |

**THE GAPS (live root-cause), in priority order:**

- **GAP-A (the big one): the matrix is enforced in 0 of its cells at runtime.**
  `daytype_playbook.py:104-106` returns FULL whenever `DAYTYPE_POSITION_GATE=1`. Every cell above
  → default-allow. *This is why 191/193/194 (HFE on a Variation/Nontrend day = SKIP/RED cells)
  fired full, and why the REACTIVE wall fired on a Variation day.*
- **GAP-B: Nontrend SKIP is owned by nobody.** Position gate defers Nontrend to the playbook
  (`daytype_position_gate.py:57`); playbook no-ops. So Nontrend (where the whole column is SKIP)
  allows everything. *188/190/191/193/194 were stamped Nontrend and fired.*
- **GAP-C: continuation-vs-reversal is invisible to the live gate.** The position gate can't tell
  ZLR (CONT, should fire with-trend) from HFE (REV, should SKIP on trend). The only thing carrying
  the CONT/REV `group` is the YAML — which is bypassed.
- **GAP-D: `require_with_trend` (REACTIVE/HNS with-trend-only on trend days) is dead.** It lives in
  `daytype_playbook.decide` (`:117-122`), reached only after the no-op return — never runs under
  the position gate. On a true Trend day a counter-trend REACTIVE would pass the position gate's
  location check yet violate the intended discipline.
- **GAP-E (sequencing, not a matrix cell): pre-IB-lock fires have no day-structure gate.** Both the
  opening gate (was OFF) and the position gate (fail-open when neither IB edge broken) let
  pre-break fires through. *188/190.*

---

## 7. TARGETS PER DAY-TYPE + OPPORTUNITY — partially per-day-type, **NOT per-opportunity**

Two target systems exist:

1. **R-based per day-type** (`backend/v9/systems/day_type/targets_table.py` + `day_type_targets.py`).
   `get_targets(day_type)` returns fixed **R-multiples** (T1=1R, T2=2.5R for Variation, etc.) +
   contract counts + time stops. This is **per-day-type but generic** — T1 is always 1R regardless
   of *where* the entry sits relative to structure or how much room exists to the next level. No
   opportunity/location input.
2. **Structural per day-type** (`backend/v9/systems/structural_targets.py`,
   `DAYTYPE_TARGETS_STRUCTURAL=1`, applied in gateway `:303-332`). For location-style day-types
   (Normal/Variation/Neutral_*/Trend_*) it overrides t1/t2/t3 with **actual structural prices**
   (IB-center, VAL/VAH, IBL/IBH, IB-extensions). This IS per-day-type AND somewhat
   per-opportunity (targets are anchored to the live IB/VA/POC geometry). **Fail-safe:** missing
   levels → returns `None` → falls back to the generic R-based table (`structural_targets.py:84-89`,
   `_build_result` side-check `:320-329`).

**Where it matches the intent and where the gap is:**
- ✅ Targets *are* day-type-specific, and when `DAYTYPE_TARGETS_STRUCTURAL` is on (it is) they are
  *structural* (Normal SHORT → C1=IB-center, C2=VAL, C3=IBL — `structural_targets.py:117-143`).
  `PNL_BY_DAYTYPE` confirms 98 of 104 sim trades resolved structural, 6 fail-safe to R.
- ❌ **No "opportunity quality" dimension.** The intended "targets per day-type + the trade's
  opportunity (location/structure)" implies targets should scale with the *specific* setup's
  room/edge (e.g. a fade right at VAH on a Normal day vs a breakout-pullback on a Variation day get
  different ladders even within the same day-type). Today the resolver branches **only on
  (day_type, direction)** and reads the same `daytype_style` block — the entry's *position within*
  the structure isn't a parameter beyond the side-of-entry sanity check.
- ❌ **STOP is not part of either system.** `targets_table`/`structural_targets` set *targets*;
  the **initial stop** comes from the detector/anchor logic (`stop_anchors.yaml`, `STOP_ANCHORS_V2`,
  giant-bar caps) — it is **not** chosen per-day-type×opportunity in these modules. 06-22's stops
  ranged 1.5–13.5 pts with no day-type rationale visible (`TRADES_TODAY` §1: the 13.5-pt stop on
  190 made it the costliest loss). So "loss targets per day-type + opportunity" is **largely
  unmet** — stops are anchor/volatility-driven, not day-type/opportunity-driven.
- ❌ **`daytype_style.contracts` vs `targets_table.contracts` disagree** (e.g. Variation: playbook
  `contracts: 3` but `targets_table` Variation `contracts: 2`; Normal: style implies 3, table says
  1). Two sources of truth for sizing per day-type — a latent inconsistency.

---

## KEEP / ADAPT / REPLACE / DEFER — surface table

| Surface | file | Role | Verdict | One-liner |
|---------|------|------|---------|-----------|
| S1 classifier (7-type) | `daytype_classify_routes.classify_replay` / `classifier_core` | sets day-type | **KEEP** | Canonical & correct; 06-22 trustworthy. |
| S1 "how to trade" output | (none as firing input) | mode/playbook cue | **ADAPT** | Only a label is threaded to gates; the playbook "mode" isn't consumed for firing. |
| S2 `_detect_reactive/_detect_initiative` | `five_min_system.py:580/722` | detector | **KEEP** | Geometry-only by design; no day-type self-gate (correct separation). |
| S2 chart-pattern day-type gate | `five_min_system.py:98,996` | sub-gate | KEEP | Gates Pkg-5a/5c chart patterns only — not the core OFA fires. |
| S4 ZLR/HFE/TLB detectors | `woodies/patterns/*.py` | detector | **KEEP** | No day-type branch; fire on CCI geometry. |
| S4 A1 trend-color gate | `woodies/decision_tree.py:175` | weak gate | KEEP | Blocks YELLOW + low-conf GRAY only; trend-color, not day-type. |
| S4 A2 day-type touch-point + 63-cell matrix | `woodies/stages/a2_day_type_query.py`, `day_type_gate.py` | advisory | **ADAPT** | Full day-type×pattern matrix computed then discarded ("NEVER vetoes"). |
| **DAYTYPE_PLAYBOOK decide()** | `daytype_playbook.py:104` | pattern×day-type SKIP | **REPLACE / ADAPT** | **No-op under position gate → the whole pattern matrix is dead. Root hole.** |
| **DAYTYPE_POSITION_GATE** | `daytype_position_gate.py` | direction×location | **KEEP-but-EXTEND** | Correct for direction; pattern-blind — doesn't cover CONT/REV suppression. |
| OPENING_TYPE_GATE | `opening_type_gate.py` | opening-drive gate | KEEP/ADAPT | Sound logic; was OFF during 06-22 fires. |
| DEDUP_FIRE_GUARD | `trading_gateway.py:132` | dedup | KEEP | Sound; was OFF when 199/200 double-fired. |
| TREND_DIRECTION_GATE / REACTIVE_LOCATION_GATE | `trend_direction_gate.py` / `reactive_location_gate.py` | legacy | **DEFER** | Superseded & runtime-skipped under position gate. |
| DIRECTION_CONTEXT | `direction_context_live.py` | CVD direction veto | **DEFER** | Flag-OFF; needs backtest #18 before enable. |
| Targets — R-based | `day_type_targets.py` / `targets_table.py` | targets | KEEP (fallback) | Per-day-type but generic R; no opportunity dimension. |
| Targets — structural | `structural_targets.py` | targets | **KEEP** | Per-day-type structural prices; live. Missing per-opportunity scaling. |
| Stop anchoring | `stop_anchors.yaml` / `STOP_ANCHORS_V2` | stops | **ADAPT** | Stops are volatility/anchor-driven, NOT per-day-type×opportunity → intent unmet. |
| Sizing source split | `daytype_style.contracts` vs `targets_table.contracts` | sizing | ADAPT | Two disagreeing per-day-type contract counts. |

---

## ROOT-CAUSE GAPS (the diagnosis, no fixes)

- **R1 — Playbook matrix is dead in the live path.** `daytype_playbook.py:104-106` returns FULL
  for everything when `DAYTYPE_POSITION_GATE=1` (it is). The pattern×day-type SKIP/REDUCED matrix
  + `require_with_trend` never execute. *Direct cause of HFE 191/193/194 and the REACTIVE wall.*
- **R2 — Position gate is pattern-blind.** `daytype_position_gate.decide` ignores its `pattern`
  arg; checks only direction×price-vs-POC/IB. Cannot suppress reversal patterns on directional
  days. *No surface enforces continuation-vs-reversal alignment.*
- **R3 — Nontrend SKIP is owned by nobody.** Position gate defers Nontrend to the playbook
  (`daytype_position_gate.py:57`); playbook no-ops → Nontrend allows all. *188/190/191/193/194.*
- **R4 — Opening-drive & pre-IB-lock fires un-gated for the live day.** `OPENING_TYPE_GATE` and
  `DEDUP_FIRE_GUARD` were flipped ON only 06-22 evening (`.env` mtime 17:22), so OFF for the
  08:30–10:20 fire window; position gate fail-opens before any IB edge breaks. *188/190 counter-
  drive; 199/200 double-fire.*
- **R5 — S1 hands gates a label, not a "how-to-trade" object.** The `daytype_style` playbook
  (target style/bias/contracts/runner per day-type) is consumed only by `structural_targets`, never
  by the firing gates. The conductor's score isn't on the firing musicians' stands.
- **R6 — Targets/stops lack a per-opportunity dimension (and stops lack a per-day-type one).**
  Targets are per-day-type (structural when levels exist) but don't scale with the specific setup's
  location/room; stops are anchor/volatility-driven, not day-type/opportunity-driven. Sizing has
  two disagreeing per-day-type sources.

*Generated read-only. No code, `.env`, DB, or services modified.*
