# CC Handoff — Day-Type Definition: Doc↔Code Reconciliation Audit ("when a day exits Normal")

**Date:** 2026-06-30 · **Owner:** Michael · **Prepared by:** Cowork
**Contract:** `docs/handoff/CC_HANDOFF_CONTRACT.md` — **paste doc:line + code:line for every claim (Rule 5)**, anti-tautological, mandatory NOT-DONE.
**Type:** **READ-ONLY AUDIT → report.** No code/threshold/flag change. Output = a reconciliation report: is the live day-type definition CORRECT per our authority documents, and **exactly where does it deviate** (code↔doc, doc↔doc, engine↔engine).
**Why now:** the 06-30 I-44/I-50 block (gate read a stale "Normal" on a real Trend_Normal day) means we must pin the **single canonical** day-type definition and find every place that disagrees with it.

---

## 0 · The canonical definition AS COWORK READ IT FROM CODE (verify this against the docs)
Source: `backend/v9/systems/day_type/daytype_classifier.py::classify` (L44-148), docstring *"Locked S1 table (Michael 2026-06-20), first-match-wins"*; thresholds from `plan["classify"]` (`load_plan()`); features from `relative_features.py`.

- **`rib`** = session_range ÷ IB_width ("master regime signal"). **`sides`** = # of IB edges with a *real accepted* range extension. **Real extension** = a 5-min bar **closes ≥ 0.3×IB beyond** the IB edge (`ext_min_frac=0.3`, `relative_features.py`).
- **Normal** (Priority 7): `sides==0` **and** `rib ≤ 1.30` (`rib_normal_max`) + normal vol + IB-not-narrow.
- **Exits Normal** (higher-priority matches):
  - `sides==1` → **Normal_Variation** (→"Variation"); **+** `one_tf∈{UP,DOWN}` **+** close at opposite extreme (`≥0.85/≤0.15`) **+** `rib ≥ 2.5` (`rib_trend_min`) → **Trend_Normal**; **+** double-distribution → **Trend_DD**.
  - `sides==2` → **Neutral_Extreme** / **Neutral_Center**.
  - `sides==0` **and** `rib ≤ 1.15` (`rib_nontrend_max`) + low vol → **Nontrend**.
- **FORMING** before IB lock (60 min / 12 bars); **escalation-only** (Normal→Variation→Trend, never reverse — `S1_ACTIVE_CANONICAL.md §5`); **INVALIDATED** overlay if price returns through the opening range.

**Confirm every value/rule above is what the authority documents specify — or report the delta.**

---

## 1 · Tasks
**T1 — Inventory the authority docs.** Find ALL documents that define the day-type characterization and list them with paths: `docs/spec_authority/S1_ACTIVE_CANONICAL.md`, the **"Michael 2026-06-20 locked S1 table"** (locate the doc of record it refers to), the ratified **Market-Profile rules** (memory: "extension = post-B period breaks first-hour A+B IB; Nontrend-first; 6+1 type map; classify on VALUE migration not geometry"), the **`DAYTYPE_CHARACTERIZATION_QUESTIONNAIRE.md`** (if present), `backend/v9/systems/day_type/compliance_manifest.yaml`, `docs/SOURCE_OF_TRUTH.md`, and any S1 spec under `docs/spec_authority/`.

**T2 — Element-by-element reconciliation (the core).** For EACH item, map **authority-doc value ↔ code value → MATCH / DEVIATION** (cite doc:line + code:line):
- Each of the 7 types' defining condition (Normal, Variation, Trend_Normal, Trend_DD, Neutral_Center, Neutral_Extreme, Nontrend).
- Every threshold: `rib_normal_max=1.30`, `rib_trend_min=2.5`, `rib_nontrend_max=1.15`, close-extreme `0.85/0.15`, close-center `0.33/0.67`, CVD `0.25/0.75`, `ext_min_frac=0.3`, IB-lock `60 min`, IB-narrow `≤0.7×median`/`≤7.0pt`, Nontrend width-floor.
- The structural rules: `sides`, `one_tf`, double-distribution, the INVALIDATED-through-open overlay, escalation-only.

**T3 — Confirm/resolve the KNOWN deviations Cowork already spotted:**
1. **Two engines, two definitions.** `daytype_classifier.py` (canonical: rib `1.30/2.5/1.15` + `sides`) vs `backend/v9/systems/day_type/api.py` (L200-242: `extension_ratio>1.5→Trend_Normal`, `<0.3→Nontrend`, else `Variation`). **Different thresholds and a different feature (extension_ratio vs rib/sides).** Which is authoritative? Is `api.py` referenced anywhere live, or dead? Same question for the OLD 3-type `state_machine.py`/`decision_matrix.py` (the pre-lock fallback that produced today's "Normal") — does its "Normal" boundary match the canonical?
2. **Escalation-only enforcement location.** `S1_ACTIVE_CANONICAL.md §5` says it's enforced in `shadow_reclass.py` (L85-88) — but §4 says that file is **DEAD/skipped** since `S1_ENGINE_NEW_CLASSIFIER`. **So is escalation-only actually enforced in the live canonical path, or is it currently un-enforced (a gap)?** Verify with code + `v9_day_type_history` transitions.
3. **Stale doc line.** `S1_ACTIVE_CANONICAL.md §3` states `OPENING_FIRE_CVD_V1` is OFF — it was **enabled today** (45-var boot-line). Flag for refresh.
4. **Un-sourced thresholds.** Flag any threshold in `plan["classify"]` / config that has **no authority-doc backing** (a calibration value that drifted in without a spec line / Michael sign-off).

## 2 · Deliverable
`docs/reports/DAYTYPE_DEFINITION_AUDIT_2026-06-30.md`:
(a) **ONE canonical day-type definition table** (the agreed source of truth, doc-cited);
(b) a **DEVIATION list** — each: where (doc:line / code:line), what disagrees, and a **recommended resolution** (update the doc, or align the code — *propose, do not apply*);
(c) the **engine map** — which definition each live path uses (trade-gate / per-bar engine / api.py / old state-machine), and whether they agree;
(d) explicit verdict per element: ✅ doc==code, ⚠️ drift, 🔴 contradiction.

## 3 · NOT-DONE (explicit)
- ❌ No code, threshold, config, or flag changes — **report only** (thresholds = trading-risk-surface → Michael sign-off before any align).
- ❌ Do not "fix" a deviation by editing the live classifier or `plan` config.
- ❌ Do not touch the gate/auth source-consistency fix (that's `CC_DAYTYPE_SOURCE_CONSISTENCY_2026-06-30.md`) — this audit only pins the DEFINITION the fix must converge on.
- ❌ Do not change REACTIVE/INITIATIVE pattern work.
- Minor doc refreshes (e.g., the stale §3 flag line) are OK to propose in the report; apply only if Michael says so.
