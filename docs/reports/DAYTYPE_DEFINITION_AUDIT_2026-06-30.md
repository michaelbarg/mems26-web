# Day-Type Definition — Doc↔Code Reconciliation Audit

**Date:** 2026-06-30 · **Type:** READ-ONLY audit → report · **Owner:** Michael · **By:** Cowork
**Scope:** Pin the single canonical day-type definition ("when a day exits Normal") and find every
place that disagrees — code↔doc, doc↔doc, engine↔engine.
**Contract:** `docs/handoff/CC_HANDOFF_CONTRACT.md` (Rule 5 = paste the cite, not the claim).
**NOT-DONE / risk:** No code, threshold, config, or flag changed. All fixes below are **proposed,
not applied** (thresholds = trading-risk-surface → Michael sign-off). The gate/auth source-freshness
fix is out of scope (owned by `CC_DAYTYPE_SOURCE_CONSISTENCY_2026-06-30.md`).

---

## Phases table (per handoff contract §C)

| Phase | Status | Evidence (file:line) |
|---|---|---|
| Inventory authority docs (T1) | DONE | listed in §A below |
| Element-by-element reconciliation (T2) | DONE | §C verdict table |
| Resolve the 4 known deviations (T3) | DONE | §D1–D8 + §B engine map |
| Engine map per live path (T2c) | DONE | §B |
| Deliverable report | DONE | this file |

> This is a read-only audit (no tests written), so the contract's *"if reverted → RED"* test line is
> N/A. Every claim instead carries a `file:line` cite (Rule 5). **NOT-DONE / DEVIATIONS** section at §F.

---

## 0 · TL;DR verdict

The **canonical definition is correct and internally consistent in the live code path**
(`classify_session` → `classify`), and the live per-bar engine uses exactly that path. The problems are:

1. **One genuine code↔doc contradiction on timing** (🔴 D1 → ✅ **resolved §H**): the spec says a day
   commits at **30 min**; the code holds **FORMING until 60 min**. Longest-lever finding — it sizes the
   pre-lock window where the gate falls back to the OLD engine (06-29/06-30 surface). *Michael's ruling:
   staged classification — provisional type from the opening+prior-day, continuous re-eval post-lock.*
2. **An invariant the doc claims is enforced, but isn't** (🔴 D2 → ✅ **resolved §H, per Dalton**):
   "escalation-only, never reverse" lives only in a **dead, skipped** file, and per Dalton it's the wrong
   rule anyway — a Trend that doesn't *hold* reverts to NVD. *Ruling: acceptance-driven transitions + a
   confirm-bar anti-noise gate, not a hard never-downgrade clamp.*
3. **Four stale/under-implemented definition lines** (⚠️ D3–D6): `≥0.3×IB` extension, Nontrend rib
   `1.5` vs `1.15`, the rich MP "Normal" (P67/rotations) not implemented, Variation ceiling `2.5` vs `2.0`.
4. **Doc-hygiene** (⚠️ D7–D8): `S1_ACTIVE_CANONICAL.md §3` flag line went stale **today**; the YAML's
   cited source-of-record doesn't exist; 8 dead config keys; a few un-ratified calibration numbers.

The handoff's "Section 0" reading is **mostly right but repeats one wrong line**: it cites
`ext_min_frac=0.3` as the live extension rule — **the code declares that parameter and never uses it**
(see D3). Everything else in Section 0 matches the live code.

---

## A · Authority-doc inventory (T1)

| Doc | Role | Note |
|---|---|---|
| `config/daytype_trading_plan.yaml` | **The live table** the code reads (`load_plan()`) | Source of all `plan["classify"]` thresholds. Self-cites `S1_day_types_spec_closed.md` (L13) as its spec-of-record. |
| `backend/.../daytype_classifier.py` + `classifier_core.py` + `relative_features.py` | **The code definition** | `classify_session` (core L121) **calls** `classify` (daytype_classifier) — same definition, one orchestrator. |
| `docs/spec_authority/S1_ACTIVE_CANONICAL.md` | "read this FIRST" engine-of-record | **Untracked in git** (`git status` → `??`); mtime 06-30 11:54. §3 stale (D7). |
| `docs/spec_authority/S1_CLASSIFIER_AS_BUILT.md` | as-built table (06-20) | Carries stale `0.3×IB` + `30-min` + self-flags the `2.5/2.0` bug. |
| `docs/spec_authority/S1_IDENTIFICATION_TABLES.md` | as-built type/opening tables | Same stale lines as as-built. |
| `docs/spec_authority/DAYTYPE_CHARACTERIZATION_QUESTIONNAIRE.md` | **OPEN** questionnaire | Definitions NOT yet closed — A1/A2/A3/A5 thresholds are blank (`___`). Explains the un-sourced numbers in D8. |
| `backend/.../day_type/compliance_manifest.yaml` | Compliance for the **LEGACY** engine | Documents `MEMS26_DAY_TYPE_DECISION_TREE_V2` (5×3 matrix, IB 15/25pt, lock conf≥0.85). **Not** the canonical relative classifier. |
| `docs/SOURCE_OF_TRUTH.md` §Day-type | Source map | Confirms canonical = 7-type `classify_session`; OLD 3-type = fallback; `/current` DEAD. |
| `docs/FLAG_INDEX.md` | Canonical flag state | Used for all flag-state claims below. |
| **MISSING:** `S1_day_types_spec_closed.md` | cited spec-of-record | **Absent from repo** (`find` → none). The YAML points at a doc that isn't here (D8). |

---

## B · Engine map — which definition each path uses (T2c / T3.1)

| # | Path | Classification basis | Uses canonical def? | State |
|---|---|---|---|---|
| 1 | **CANONICAL** = `classify()` in `daytype_classifier.py`, orchestrated by `classify_session()` (`classifier_core.py:121`), features from `relative_features.py` | `rib` + `sides` + `close_pos` + `one_tf` + `cvd_pos` + `vol_ratio` + `dd_second_dist`; reaches all 7 types | — (is the reference) | LIVE |
| 2 | **Live per-bar engine** `_day_type_on_bar` (`backend/main.py:347–479`) | calls `classify_session` | ✅ **SAME def** | `S1_ENGINE_NEW_CLASSIFIER=1` ✅ (FLAG_INDEX L24) |
| 3 | **Replay/UI** `classify_replay` (`daytype_classify_routes.py:80,220,240`) | per-bar `classify`, `final = timeline[-1]` (is_eod on last) | ✅ **SAME def** | LIVE; `final` = EOD-committed last segment |
| 4 | **Trade gate** `extract_g1_entry_context` (`trade_context.py:487–552`) | with `S1_NEW_CLASSIFIER=1` ✅ overrides the OLD seed with #3's `final.day_type` | ✅ def-consistent, ⚠️ **freshness-split** | `DAYTYPE_GATE_LIVE_V1` 🔴 **OFF** (FLAG_INDEX L34) → reads `classify_replay` 30s cache, **not** the live promoted attr → this is the I-44/I-50 06-30 "stale Normal". Fix exists (L518–535), gated off. *(Deferred to the source-consistency prompt.)* |
| 5 | **OLD 3-type engine** `DayTypeStateMachine` (`state_machine.py`) + `DECISION_MATRIX` (`decision_matrix.py:30–71`) | **(opening_type × IB-width-class) lookup**, default `Normal` | 🔴 **DIFFERENT def** | Pre-IB-lock + fail-safe fallback ONLY. Its "Normal" = matrix default / INDETERMINATE / ORR×WIDE / OA_IN — **not** `rib≤1.30 + sides==0`. Source of the 06-29 premature `Variation`. |
| 6 | **`api.py` "V1"** `_classify_v1_from_tpo` (`api.py:136–243`) | `extension_ratio = max_ext / ib_range`; `>1.5→Trend_Normal`, `<0.3→Nontrend` (CAL-006/007) | 🔴 **DIFFERENT def** | Router mounted (`app.py:11`) **but** result always demoted to `classified=False` (`api.py:297–303`); `/current`+`/v9/current` DEAD (retired 06-22). Inert. |

**Bottom line:** the three live, authoritative paths (1, 2, 3) all use the **same** canonical definition.
The two engines with a *different* "Normal" definition (5, 6) are fallback/dead. The 06-30 stale-"Normal"
was a **freshness split between two reads of the same canonical engine** (path 4), not a definition
conflict — so the *definition* this audit pins is the right target for the source-consistency fix.

---

## C · Canonical definition + per-element verdict (T2)

**Canonical = `classify()` first-match-wins, post-IB-lock.** Verdict legend: ✅ doc==code · ⚠️ drift · 🔴 contradiction.

### C.1 — The 7 types (defining condition)

| Type | Code condition (`daytype_classifier.py`) | Authority doc | Verdict |
|---|---|---|---|
| **FORMING** (lifecycle) | `n_bars < 12` (60 min), not EOD — L86 | YAML "first 30 min (<6 bars)" L65; as-built L9 — **30 min** | 🔴 **D1** |
| **Nontrend** | `sides==0 & vol_ratio≤0.5 & rib≤1.15 & range≤18pt` — L97 | YAML precedence "vol≤0.5 + **rib≤1.5**" L66; ident. L29 | ⚠️ **D4** (rib ceiling) |
| **Normal** | `sides==0 & rib≤1.30 & normal_vol & not ib_narrow` — L136 | YAML adds `ib≥P67` + `inside_ib≥0.70` + `rotations≥2` L94 | ⚠️ **D5** (under-impl.) |
| **Normal_Variation** | `sides==1`, catch-all (rib up to Trend floor 2.5) — L127 | YAML `rib:[1.3, 2.0]` L106; ident. self-flags "should be <2.0" L28 | ⚠️ **D6** |
| **Trend_Normal** | `sides==1 & not oi & one_tf∈{UP,DOWN} & close≥0.85/≤0.15 & rib≥2.5` — L120 | YAML L69/L154; as-built L28 | ✅ (all four ANDed; CVD confirms, not gate) |
| **Trend_DD** | `sides==1 & dd_second_dist` — L116 | YAML L140; note: `dd_second_dist` is a POC-jump **proxy**, not a true single-print (as-built L50) | ✅ logic / ⚠️ proxy noted |
| **Neutral_Extreme** | `sides==2 & close≥0.85/≤0.15` — L104 | YAML L128 | ✅ |
| **Neutral_Center** | `sides==2 & 0.33≤close≤0.67` (else PROVISIONAL) — L106 | YAML L116 | ✅ |
| P0 **INVALIDATED** overlay | `returned_through_open` → blocks Trend (`not oi` L120), non-terminal — L66/L77 | YAML L72/L176 | ✅ |

### C.2 — Thresholds

| Threshold | Code | YAML | Verdict |
|---|---|---|---|
| `rib_normal_max` | `1.30` (L59) | `1.30` (L39) | ✅ |
| `rib_trend_min` | `2.50` (L57) | `2.50` (L42) | ✅ |
| `rib_nontrend_max` | `1.15` (L58) | `1.15` (L38) | ✅ (but used where doc prose says 1.5 — D4) |
| close-extreme hi/lo | `0.85 / 0.15` (L61) | `0.85 / 0.15` (L45-46) | ✅ |
| close-center | `0.33 / 0.67` (L62) | `[0.33, 0.67]` (L47) | ✅ |
| CVD long/short | `0.75 / 0.25` (L60) | `0.75 / 0.25` (L43-44) | ✅ |
| IB-lock | `60 min` → 12 bars (L64) | `ib_lock_minutes: 60` (L50) | ✅ **but** contradicts `forming_lock_minutes: 30` (L51) — D1 |
| IB-narrow | `ib_width ≤ 7.0pt` fallback (L134) **or** `≤0.7×median` (core L112) | `ib_narrow_pts: 7` (L36) | ✅ |
| Nontrend width-floor | `range > 18pt` disqualifies, flag ON (L92-97) | FLAG_INDEX `NONTREND_MAX_RANGE_PTS=18` L121 | ⚠️ un-sourced (D8) |
| `ext_min_frac` (≥0.3×IB) | **declared L100, NEVER used** | YAML day_types L106 + as-built L43 assert it | ⚠️ **D3** |
| real-extension rule (actual) | `≥2 consec closed bars beyond IB ± 2-tick buf` + `≥8% vol accepted` (L153-173) | YAML features.ext_hold L30 ("≥2 consec; **no 0.3×IB**") | ✅ vs features / 🔴 vs day_types table |
| `vol_accept_frac` (8%) | `0.08` (relative_features L102) | none (code comment only) | ⚠️ un-sourced (D8) |

---

## D · Deviation list (where · what · recommended resolution — **propose only**)

### D1 🔴 — FORMING/commit timing: code 60 min vs doc 30 min  *(highest lever)* — ✅ **RESOLVED (Michael 2026-06-30, see §H)**
- **Doc:** `daytype_trading_plan.yaml:51` `forming_lock_minutes: 30`; precedence `:65` "first 30 min
  (<6 bars) → FORMING (ONLY here; never after 30 min)"; `S1_CLASSIFIER_AS_BUILT.md:9`;
  `S1_IDENTIFICATION_TABLES.md:22`.
- **Code:** `daytype_classifier.py:64` `ib_lock_bars = int(ib_lock_minutes/5) = 12`; `:86`
  `if n < ib_lock_bars → FORMING` (= 60 min). `backend/main.py:424` only promotes at `≥12` bars.
  `forming_lock_minutes` has **0 references** in `backend/` (dead key).
- **Why it matters:** the FORMING window is exactly the interval where the gate falls back to the OLD
  3-type engine. 60-min code vs 30-min spec = a 30-minute-longer fallback exposure — the 06-29/06-30
  surface. Note `DAYTYPE_CHARACTERIZATION_QUESTIONNAIRE.md:32` (A5) lists this timing as still **OPEN**.
- **Resolve:** Michael ratifies the commit time. If 30 min → wire `forming_lock_minutes` (and reconcile
  with the 60-min IB lock — they are two different events). If 60 min → fix YAML `:51/:65` + the two
  as-built docs to say 60. Trading-risk-surface → sign-off + restart before any code change.

### D2 🔴 — Escalation-only invariant is NOT enforced in the live path — ✅ **RESOLVED per Dalton (Michael 2026-06-30, see §H)**
- **Doc:** `S1_ACTIVE_CANONICAL.md:98-110` (§5) "Within a session the day-type may only upgrade…
  Enforced in `shadow_reclass.py` (L85-88) via a monotonic rank."
- **Code:** the only `TYPE_ORDER` monotonic clamp is `shadow_reclass.py:86-88` — and that branch is
  **skipped** when `S1_ENGINE_NEW_CLASSIFIER=1` (`backend/main.py:481` is an `elif`). The live path
  (`classify_session`→`classify`; promotion `main.py:465-468`) overwrites with any new type, **no rank
  check**. `classify_replay` returns `final = timeline[-1]` with **no clamp** (`daytype_classify_routes.py:240`).
  `grep TYPE_ORDER|monotonic|escalat` across `backend/` (excl. shadow_reclass) → none. `shadow_reclass.py`
  is itself doubly-dead: `import sqlite3` + SQLite `DB_PATH` (`:19,:25`), pre-Postgres-migration.
- **Why it matters:** §4 of the *same doc* (L85) admits `shadow_transitions` is "STALE BY DESIGN" because
  the live engine skips that branch — so §5 points at code that does not run. Intraday downgrades are
  structurally possible (the classifier even labels `Normal_Variation` "PROVISIONAL… can still get
  side-2 → Neutral", L125-127).
- **Resolve:** decide whether escalation-only is still required. If **yes** → add a monotonic guard to
  the live promotion (`main.py`) / `classify_session`, reusing the `TYPE_ORDER` rank. If the
  PROVISIONAL/EOD-commit design **intentionally supersedes** it → rewrite §5 to say so and stop citing
  the dead `shadow_reclass.py`. Propose only.

### D3 ⚠️ — "≥0.3×IB" extension is stale; `ext_min_frac` is dead config
- **Asserts 0.3×IB:** handoff Section 0; `daytype_trading_plan.yaml:106` (`Normal_Variation.ext_hold: "≥0.3×IB"`);
  `S1_CLASSIFIER_AS_BUILT.md:43`; `S1_IDENTIFICATION_TABLES.md:34`.
- **Code:** `relative_features.py:100` `ext_min_frac=0.3` is a parameter that is **never applied** in the
  body. The real side test (`:153-173`): close beyond IB edge + 2-tick buffer, **hold ≥2 consecutive
  bars** (`ext_hold_bars=2`), **AND ≥8% session volume accepted** beyond the edge.
- **Agrees with code:** `daytype_trading_plan.yaml:30` features.ext_hold + `:24` features.sides — both
  say "≥2 CONSECUTIVE… **No '0.3×IB' magnitude** (it buried real breaks on wide IBs)."
- **So:** intra-YAML contradiction (features L30 ✅ vs day_types table L106 🔴) + two stale as-built docs
  + a dead param.
- **Resolve (doc-only, safe):** delete `ext_min_frac` (or wire it if intended); scrub "≥0.3×IB" from the
  day_types table + both as-built docs. Separately, **ratify** the real gates `ext_hold_bars=2` and
  `vol_accept_frac=0.08` into an authority doc (currently only a code comment).

### D4 ⚠️ — Nontrend low-participation rib ceiling: code 1.15 vs doc 1.5
- **Doc:** `daytype_trading_plan.yaml:66` "LOW participation (vol ≤0.5×median) + **rib≤1.5** → Nontrend";
  `S1_IDENTIFICATION_TABLES.md:29`; `S1_CLASSIFIER_AS_BUILT.md:35`.
- **Code:** `daytype_classifier.py:97` uses `rib ≤ rib_nt` where `rib_nt = rib_nontrend_max = 1.15`.
  There is **no 1.5 branch**, and the docs' second Nontrend rule ("IB≤7 + rib≤1.15", ident. L30) is **not**
  a Nontrend trigger in code (`ib_narrow_pts=7` is used only in the Normal fallback, `:134`). Also code
  requires `vol_ratio is not None` → if vol is unavailable, Nontrend is unreachable (day → Normal).
- **Resolve:** reconcile the ceiling (code→1.5 loosens to more SKIP days; or doc→1.15). Trading-risk-surface
  (changes the SKIP count) → sign-off. Propose only.

### D5 ⚠️ — "Normal" is under-implemented vs the MP spec
- **Doc:** `daytype_trading_plan.yaml:94` requires `ib: "≥P67"` (WIDE) + `inside_ib_pct ≥0.70` +
  `rotations ≥2 touches each VAH/VAL`; questionnaire §3 draft similar.
- **Code:** `daytype_classifier.py:136` Normal = `rib≤1.30 & normal_vol & not ib_narrow` only. No
  P67/WIDE gate (percentile keys are dead — D8), no `inside_ib_pct`, no `rotations`. `tails_both` /
  `close_at_poc` are soft reason-tags (`:138-141`), not gates.
- **Resolve:** annotate the doc that structural confirmations are aspirational, or implement post-LIVE.
  Low urgency. Propose only.

### D6 ⚠️ — Variation upper bound: code ~2.5 vs doc 2.0  *(already self-flagged)*
- **Doc:** `daytype_trading_plan.yaml:40` `rib_variation:[1.30, 2.00]` + `:106`; `S1_CLASSIFIER_AS_BUILT.md:29,56`
  and `S1_IDENTIFICATION_TABLES.md:28` both annotate "⚠ should be <2.0".
- **Code:** `Normal_Variation` is the `sides==1` catch-all (`:127`) covering rib up to the Trend floor
  2.5; `rib_variation` is **dead config** (0 refs). 1-sided days with `2.0 ≤ rib < 2.5` are labeled
  Variation though the doc band stops at 2.0 (the 2.0–2.5 band is undefined in the doc).
- **Resolve:** read `rib_variation[1]` as the ceiling (and define 2.0–2.5 handling), or widen the doc band
  to `[1.30, 2.50]`. Propose only.

### D7 ⚠️ (doc-only) — `S1_ACTIVE_CANONICAL.md §3` says `OPENING_FIRE_CVD_V1` is OFF; it is ON
- **Doc:** `S1_ACTIVE_CANONICAL.md:51,70-76` "that flag is OFF today… the fix exists but is not active."
- **Truth:** `.env:70` `OPENING_FIRE_CVD_V1=1`; `FLAG_INDEX.md:36` ✅ ON. So the pre-IB-lock
  `FORMING → day_type=None` fix (`trade_context.py:549-550`) **is active**. Doc mtime 11:54 < `.env` mtime
  12:32 → the flag flipped ~38 min after the doc's own 06-30 audit, so the line went stale same-day.
  §2 also omits the (OFF) `DAYTYPE_GATE_LIVE_V1` live-read path entirely.
- **Resolve (doc-only):** refresh §3 (flag ON; fix active) and §2 (mention the OFF live-read path).
  Apply only if Michael approves the doc edit.

### D8 ⚠️ (doc-only) — Missing source-of-record, un-ratified numbers, dead keys
- **Missing spec-of-record:** `daytype_trading_plan.yaml:13` cites `S1_day_types_spec_closed.md` —
  **absent from the repo**. The effective authority is the YAML + `S1_ACTIVE_CANONICAL.md` (untracked) +
  as-built docs (which carry the stale lines above).
- **Un-ratified live numbers** (no authority line; questionnaire still blank): `vol_accept_frac=0.08`,
  `NONTREND_MAX_RANGE_PTS=18`, the 60-vs-30 commit time (D1).
- **Dead config keys (0 refs in `backend/`):** `rib_variation`, `rib_neutral`, `ext_confirm_bars`,
  `trend_confirm_bars`, `forming_lock_minutes`, `ib_wide_pts`, `ib_narrow_pctile`, `ib_wide_pctile`.
- **Resolve:** commit a real source-of-record; close the questionnaire to ratify 8% / 18pt / commit-time;
  prune (or wire) the dead keys. Propose only.

---

## E · Direct answers to the handoff's T3 questions

1. **Two/three engines, which is authoritative?** Authoritative = the **7-type `classify_session`→
   `classify`** (paths 1–3, §B). `api.py::_classify_v1_from_tpo` is **mounted but demoted/dead**
   (`api.py:297-303`; endpoints retired 06-22). The OLD `state_machine.py`/`decision_matrix.py` is a
   **pre-lock/fail-safe fallback only**; its "Normal" is an (opening×IB-width) lookup default
   (`decision_matrix.py:30-71`) — **does not match** the canonical `rib≤1.30 + sides==0` boundary. That
   mismatch is the mechanism behind the OLD engine's bad labels when it leaks (06-29).
2. **Escalation-only location:** enforced **nowhere live** — only in the **skipped** `shadow_reclass.py:86-88`
   (D2). Currently an un-enforced gap.
3. **Stale §3 line:** confirmed stale — `OPENING_FIRE_CVD_V1` is **ON** (D7).
4. **Un-sourced thresholds:** `vol_accept_frac=0.08`, `NONTREND_MAX_RANGE_PTS=18`, the FORMING commit
   time, plus 8 dead keys (D8). The `≥0.3×IB` value is not just un-sourced — it's **contradicted** by the
   code and by the YAML's own features section (D3).

---

## F · NOT-DONE / DEVIATIONS (mandatory, handoff §B3)

- ❌ **No code / threshold / config / flag was changed** — by design (read-only audit). Every D-item is a
  *proposal* requiring Michael sign-off (thresholds = trading-risk-surface).
- ❌ **Did not touch** the gate/auth source-freshness fix — that's `CC_DAYTYPE_SOURCE_CONSISTENCY_2026-06-30.md`.
  This audit only pins the *definition* that fix must converge on.
- ❌ **Did not change** REACTIVE/INITIATIVE pattern work.
- ⚠️ **Not fully traced** (bounded the audit): the exact 06-30 mechanism that put "Normal" on the gate
  (30s `classify_replay` cache lag vs the OLD `day_type_machine` default seed at `trade_context.py:496-501`)
  — both are plausible; precise root-cause belongs to the source-consistency prompt. The *definition* on
  both reads is canonical, which is the point this audit establishes.
- ⚠️ **`dd_second_dist`** is a POC-jump proxy, not a true single-print neck (`S1_CLASSIFIER_AS_BUILT.md:50`)
  — noted, not audited deeply (the spec for "real DD" is itself still open).

## G · Open / what's next (for Michael)
- **D1 & D2 are now RESOLVED by Michael (§H).** Remaining open: **D4** (Nontrend rib 1.15 vs 1.5, a
  risk-surface) still needs a ruling; D3/D5/D6/D7/D8 are doc-hygiene (safe once approved).
- Doc-only fixes (D3 scrub, D5/D6 annotate, D7/D8 refresh) can land without touching trading code; the
  code-side items (D1, D2, D4) need sign-off + restart per Pre-LIVE Discipline.

---

## H · Michael's rulings — 2026-06-30 (grounded in `James_Dalton_Trading_Guide.xlsx`)

Michael's own Dalton reference (repo root, sheet **"סוגי ימים"**) is the tie-breaker. Two columns
decide it: **"איך מזהים: סיכום תוך 15 דק׳"** (identify within 15 min) → D1, and **"האם יכול להשתנות?"**
(can it change?) → D2.

### D1 — RESOLVED: **staged classification, not a 60-min FORMING/UNKNOWN hold**

**Michael:** *"הרצת הפתיחה קובעת לנו בשלב ראשון איזה סוג יום זה, יחד עם נתוני יום קודם. לאחר ש-IB נקבע
המערכת כל הזמן ערה לשינויים… כמו מעבר מיום נורמלי ליום אחר. המערכת גם צריכה להבדיל בין יום טרנדי לבין
יום וריאציה."*

**Dalton backing:** every day-type has a **15-minute** opening read + a **prior-day** relationship
(e.g. Trend-Up: `ID<15min = "High ברור מעל IB High, Low של IB לא חוצה, מחיר עולה"`; prev-day =
`"בד״כ Open Drive Up… Gap Up, או close גבוה"`). So Dalton classifies **provisionally from the opening**,
then the day develops.

**Decided canonical timing (supersedes the 60-min FORMING hold):**
1. **Stage-1 (opening):** an early provisional day-type from **opening_type + prior-day data** — first
   ~15 min (Dalton) / firmed ~30 min (MEMS26 staging). **Not** `UNKNOWN`/`FORMING` until 60 min.
2. **IB structural lock @ 60 min** stays — but only for **IB width/percentile**. It is a *different event*
   from the classification commit (the code currently conflates them).
3. **Post-lock:** continuous re-evaluation for transitions (Normal → other), with robust **Trend vs
   Variation** discrimination.

**Code deviation to fix (proposal — sign-off gated):** `daytype_classifier.py:64,86` gate FORMING on
`ib_lock_minutes(60)`. Rewire to commit a **provisional** type at ~30 min (wire the dead
`forming_lock_minutes:30` + an opening/prior-day seed), keeping 60-min only for IB width. This removes the
pre-lock window where the gate is forced to fall back to the OLD engine — the direct 06-29/06-30 surface.
**Blocker to watch:** as-built L37 — `OPEN_DRIVE` almost never fires → `Trend_Normal` nearly unreachable;
the staged design must fix opening-type detection so Dalton's OD→Trend path is reachable (this is exactly
Michael's "must distinguish Trend vs Variation").

### D2 — RESOLVED per Dalton: **acceptance-driven transitions, NOT a hard never-downgrade clamp**

**Dalton backing ("האם יכול להשתנות?"):**
- **Trend Day → "כן — אם יוצא טרנד ולא מחזיק, יכול להפוך ל-NVD"** (YES — a trend that does **not hold**
  reverts to NVD/opposite).
- **NVD → Trend** "אם יש breakout חדש ופריצה"; **Neutral → Trend** "אם Volume גובר והמחיר יוצא".

**Ruling:** day-types are **acceptance-driven, not strictly monotonic.** The doc's strict *"escalation-only,
never reverse"* (`S1_ACTIVE_CANONICAL.md §5`) is **not Dalton-faithful** — a Trend that fails to hold
**legitimately downgrades** to NVD. So the fix is **not** "port the dead `shadow_reclass` `TYPE_ORDER`
clamp into the live path."

**Decided transition rule:**
- **Upgrade** when a **new extension/breakout is ACCEPTED** (holds ≥ confirm-bars + volume): Normal→
  Variation→Trend, Neutral→Trend.
- **Downgrade** only when the **defining extension/trend FAILS to hold** (rejected; price accepted back
  inside IB/value) — Dalton's *"לא מחזיק"*. **Not** a free per-bar flip.
- **Anti-noise (questionnaire A7):** require **confirm-bars** before any transition so it can't whipsaw on
  a single bar; a genuine failed-hold still reverts.

**What's actually wrong today (both sides):** the **code** has *no* hold/confirm gate on transitions
(per-bar first-match-wins can flip on noise — `daytype_classifier.py` classifies each bar independently),
**and** the **doc** over-promises a monotonic clamp that (a) isn't enforced and (b) isn't Dalton-faithful.
Fix = (1) rewrite §5 to the acceptance-driven rule above with the Dalton citation; (2) gate the live
classifier's transitions on **structural acceptance (held `sides` + confirm-bars)** rather than
instantaneous `rib`/first-match. Code change → strategic-stop + Michael sign-off + restart.

> Both D1 and D2 fixes are **proposals**; no code was changed in this audit. Recommended next step: a
> flag-gated CC implementation prompt (per `CC_HANDOFF_CONTRACT.md`) that builds the staged classifier
> (D1) + acceptance-driven transitions (D2) in SHADOW, validated before any live enable.
