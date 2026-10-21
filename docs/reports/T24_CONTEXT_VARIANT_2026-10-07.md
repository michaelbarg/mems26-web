# T24_CONTEXT — tree VARIANT `3.4.0-t24_context`: phase C/D re-rooted on structure → hour → kind

**Written:** 2026-10-07 15:40 IL by cursor, on Michael's 15:14 order ("start implementing the NEXT calibration step. Do not touch the live tree").
**Scope:** AGENT_BRIEF_FABLE §2.4 = CC_ORDER_2026-10-05_DAILY_DALTON §3 stage 5 (T-543): *after the IB lock the decision root is IB structure + hour bucket + entry kind; day_type stays a recorded field.*
**Status:** YAML written · structurally verified · **MEASURED 07.10 15:50–16:35 IL on Michael's 15:48 override of the night wait — לא עולה** (§7). The live tree stays.
**Not touched:** `config/decision_tree_v3.yaml` (`git diff --quiet` ⇒ clean, md5 `cc8f5080debdc296f9bbdbd401821c19`), `.env`, no restart, no `fwd_harness` / `run_variant.sh`. Nothing committed (CC_ORDER stage files are committed only on Michael's request — CURSOR_README §6.4). TASK_LOG / STATUS_BOARD / LIVE_CHANNEL rows are cowork's (CURSOR_README §4); a pointer message was put atop `CURSOR_COWORK_THREAD.md`.

---

## 1 · What was built

`config/decision_tree_v3.t24_context.yaml` — a copy of the live 3.4.0 with exactly these changes:

| | live 3.4.0 | variant `3.4.0-t24_context` |
|---|---|---|
| `version` | `"3.4.0"` | `"3.4.0-t24_context"` (+ `variant_of:` line; loader ignores extra keys) |
| root `hour` cutoff (`>21` ⇒ SKIP `time_cutoff`) | — | **identical** (asserted: same leaf dict) |
| `opening_type` → `phase` → **A**, **B** subtrees (5 opening-type groups) | — | **identical** (asserted deep-equal per group) |
| `phase` → **C** | `*phase_C` = `split: day_type` → trend_row / variation_row / normal_by_structure / responsive_neutral / stand_down | `*ctx_CD` = `split: structure` → `split: hour` → `split: kind` → (rel_bias · edge · direction · zone) |
| `phase` → **D** | `*phase_D` = `split: day_type` → trend_row / d_with_extension / Normal→structure / stand_down | `*ctx_CD` (same anchor; the `hour > 20` bucket is the old phase D) |
| `day_type` | asked in C and D | **never asked** in C/D (stays in the vector / `tree_v3.vec`, recorded) |

The new library section (`ctx_CD` and its parts) sits after the live `phase_D` anchor; the live `phase_C` / `phase_D` / `trend_row` / `variation_row` / `normal_by_structure` / `responsive_*` anchors are left in the library for reference but are **unreachable** from `root`.

### The C/D routing (anchor `ctx_CD`)

```
structure
├─ up|down ──── hour ─┬─ <=17 · <=19 · <=20 → ctx_ext_C   (Variation template = live variation_row, kind first)
│                     ├─ >20              → d_with_extension (live S1 leaf: with the extension → TAKE, else stand_down)
│                     └─ *                → stand_down
├─ none ─────── hour ─┬─ <=17 · <=19 · <=20 → ctx_none_C  (Normal/responsive template = live responsive_normal, kind first)
│                     └─ >20 · *          → stand_down
├─ two_sided ── hour ─┬─ <=17 · <=19 · <=20 → ctx_two_sided_C (Neutral template = live responsive_neutral, kind first)
│                     └─ >20 · *          → stand_down
└─ * (unknown) ────────────────────────── → stand_down        (0 such candidates in t529b; forming cannot occur in C/D)
```

Inside each C template `kind` is the first question, then the live circumstance splits unchanged:

- `ctx_ext_C` — `kind ∈ BREAK|VALUE_RETURN` → rel_bias {with: take_with_hint · against: against_fallback (edge → take_failed_ext) · none: the live kinds_variation TAKE leaf (exit 1.5R/2.5R, S7)}; other kinds → rel_bias {with: take_with_hint · against: against_fallback · none: kind_fallback}.
- `ctx_none_C` — `kind ∈ EDGE_FADE|VALUE_RETURN` → direction → zone {near_val|below_value / near_vah|above_value: take_location (T-319b) · unknown: the live kinds_normal TAKE leaf · *: location_fallback (T-529 edge → take_failed_ext_responsive, else skip_location)}; other kinds → same, with `unknown` → kind_fallback.
- `ctx_two_sided_C` — as `ctx_none_C` with `kind = EDGE_FADE` only and the live kinds_neutral leaf.

**Hour buckets within C route identically on purpose.** The bucket is in the root so that a later *measured* ruling can change one bucket's leaf without restructuring (reference table: `WALK_FORWARD_2026-10-05.md` §6). Choosing different leaves per bucket now would be fitting on the sample — not done.

### Leaf discipline (no invented leaves)

```
$ python3 /tmp/t24ctx_verify.py
  distinct TAKE leaf contents: live=17 variant=14 NEW-in-variant=0
  NEW SKIP/SHADOW leaf contents in variant: 0
  live TAKE leaf contents NOT reachable in the variant: 3
   GONE: id=None note='trend day: pullback / break (with the trend when hinted)'          # kinds_trend (only under the Trend_* label split)
   GONE: id=None note='the IB is extended one-sidedly — … with the extension any kind is taken'   # take_with_extension (only under the Normal label split)
   GONE: id=None note='VAR_CONT: structural pullback-continuation with the extension'      # variation_row pattern node; producer VAR_CONT_V1 OFF, 0 candidates
ALL STRUCTURAL ASSERTIONS PASSED
```

Every leaf in the variant is a live 3.4.0 leaf with the same content (the three `take_kind_*` anchors are the TAKE leaves that sat inside the live `kinds_variation` / `kinds_normal` / `kinds_neutral` nodes, lifted out so `kind` can be asked first). No new TAKE, no new SKIP.

---

## 2 · Structural diff summary (nodes that differ)

```
== per opening type: A/B identical? C/D differ? node counts ==
  OPEN_DRIVE                               A_same=True B_same=True C_diff=True D_diff=True  C+D nodes live(split,leaf)=(51, 73) var=(202, 310)
  OPEN_TEST_DRIVE                          A_same=True B_same=True C_diff=True D_diff=True  C+D nodes live(split,leaf)=(51, 73) var=(202, 310)
  OPEN_REJECTION_REVERSE                   A_same=True B_same=True C_diff=True D_diff=True  C+D nodes live(split,leaf)=(51, 73) var=(202, 310)
  OPEN_AUCTION_IN|OPEN_AUCTION_OUT         A_same=True B_same=True C_diff=True D_diff=True  C+D nodes live(split,leaf)=(51, 73) var=(202, 310)
  *                                        A_same=True B_same=True C_diff=True D_diff=True  C+D nodes live(split,leaf)=(51, 73) var=(202, 310)
  C/D subtrees total: live splits+leaves=(255, 365) (620)  variant=(1010, 1550) (2560)
  whole tree: live splits=375 leaves=536 total=911 · variant splits=1130 leaves=1721 total=2851
  variant ctx_CD (one shared subtree) nodes: (101, 155)
== splits asked in the variant's C/D subtree, in order of first appearance ==
   structure → hour → kind → rel_bias → edge → direction → zone
```

- **Branch points that differ:** 10 (the `C:` and `D:` branch of each of the 5 opening-type groups). Everything above/beside them (root cutoff, opening_type node, 5 phase nodes, all A/B subtrees) is byte-identical.
- **Anchors:** 2 live anchors (`phase_C`, `phase_D`; 124 reachable nodes per opening type = 51 splits + 73 leaves) replaced by 1 anchor (`ctx_CD`; 256 nodes = 101 splits + 155 leaves). The expansion is from asking `kind` before direction/zone/rel_bias (each template body is written twice: listed kinds / other kinds).
- **Reachable nodes (anchors expanded):** live 911 → variant 2851; the C/D part 620 → 2560. Live leaves 536 → variant 1721.
- `tests/v9/regression/test_decision_tree_v3.py::TestTreeShape` run against the variant via `DECISION_TREE_V3_PATH`: `test_every_leaf_is_an_action`, `test_walk_never_falls_through`, `test_numeric_and_list_keys` **pass**; `test_root_order_is_michaels` **fails by design** (it asserts `phase C` splits on `day_type` — exactly what this variant removes). The live file still passes all 25.

---

## 3 · What became unreachable / changed because it lived only under the `day_type` split

Required by the order ("keep failed_extension and T-319b location where the live tree has them, unless they only exist under a day_type split you removed — then say so"):

1. **Phase D `failed_extension` — LOST.** In the live tree the only D route to `take_failed_ext` is `trend_row.against_fallback`, reached via `day_type ∈ Trend_Normal|Trend_DD|Neutral_Extreme`. `d_with_extension` (the S1 leaf, the only label-free D row) asks no `edge`. Without the label the variant has no D failed-extension path. In t529b: **32 D candidates with `edge=failed_extension` flip TAKE→SKIP** (Trend_Normal/up 12 · Neutral_Extreme/up 6 · Neutral_Extreme/two_sided 5 · Trend_Normal/down 5 · Trend_DD/down 4). A one-line follow-up variant (`>20` on up|down → rel_bias {with: d_with_extension leaf · against: against_fallback · *: stand_down}) would restore it — **not added here** because it would be a new TAKE path in D that the live tree has only under the label; it is a separate measurement if Michael wants it.
2. **Phase C `failed_extension` — KEPT.** `against_fallback` (extension template) and `location_fallback` (responsive templates, T-529) are where the live tree has them. 0 C candidates with `edge=failed_extension` flip TAKE→SKIP (3 flip SKIP→TAKE on the Nontrend label, which stood down in live).
3. **T-319b location rule — KEPT** on structure `none` and `two_sided` (the live tree applies it on the Normal/Neutral labels with those structures). It is **not** applied on `up|down` (the live tree does not apply it on Variation / Normal-by-structure up|down either); the Neutral labels with an up|down IB (live: location rule) now get the extension template — 29 live `location` SKIPs become TAKE (see §4).
4. **`take_with_extension` (ruled 25.09, `skip_gates: [entry_location_quality]`) — not reachable.** It existed only under `day_type=Normal` → structure up|down. The variant's up|down with-hint leaf is `take_with_hint` (the Variation-row leaf, which is what 1,373 of the 1,690 live up|down C candidates — the Variation label — already got). Verdict stays TAKE on all 46 live uses; the **ELQ gate now applies to them** (policy change, not a verdict change). Alternative (one line: `ctx_ext_*.with: *take_with_extension`) would instead remove the ELQ gate from the ~1,370 Variation-label up|down candidates — larger blast radius, not chosen.
5. **`kinds_trend` PULLBACK|BREAK (no-hint) leaf — not reachable.** Only under the Trend_* labels. BREAK with no hint is still admitted on up|down via the kinds_variation leaf (BREAK|VALUE_RETURN); PULLBACK with no hint is not (4 PULLBACK candidates in all of C/D in t529b).
6. **`trend_row` on a Trend label with structure `none`** (31 C candidates, 18 TAKE→SKIP): the IB was not extended ⇒ the variant applies the responsive template. This is the doctrine's point (Dalton: a day the IB contains is not a trend day by price), reported as a label-vs-structure disagreement to watch.
7. **`d_with_extension` on a Variation label with structure `none` / `two_sided` in D** (live: TAKE with the hint; 23 TAKE→SKIP): the live row trusted the label; the variant stands down when the IB is not one-sidedly extended.
8. **`VAR_CONT` pattern node** — omitted (producer flag `VAR_CONT_V1` OFF; 0 candidates in 65 sessions). Inert.
9. **Phase D asks no `kind`.** The live D rows ask it only inside `trend_row` (label-only); the surviving label-free row (`d_with_extension`) never did. So in `>20` the order is structure → hour → rel_bias. Said explicitly so nobody reads it as "kind forgotten".

---

## 4 · Route preview on the recorded t529b vectors (counts only — NOT the measurement)

Every `tree_v3.vec` in `harness_out/t466/t529b_*.json` (65 sessions, pre-22:00-cutoff run) walked through both trees with `decision_tree.walk` (pure function; no harness, no DB). Candidate-level verdict flips only; **no $ computed on purpose** — the number comes from the walk-forward harness tomorrow, not from in-sample Σ.

```
  phase A/B vectors: 854 · leaf-or-id changed: 0
  phase C/D vectors: 3544 · SKIP→SKIP: 1759 · SKIP→TAKE: 75 · TAKE→SKIP: 146 · TAKE→TAKE: 1564
  verdict flips by train/holdout(last-10 sessions of t529/sessions.txt): {('train','TAKE→SKIP'): 113, ('train','SKIP→TAKE'): 66, ('holdout','TAKE→SKIP'): 33, ('holdout','SKIP→TAKE'): 9}
```

By live label × structure (top rows):

```
    53  ('C', 'Variation', 'none', 'TAKE→SKIP')      27  ('C', 'Variation', 'none', 'SKIP→TAKE')
    18  ('C', 'Trend_Normal', 'none', 'TAKE→SKIP')   17  ('D', 'Neutral_Extreme', 'two_sided', 'TAKE→SKIP')
    16  ('D', 'Variation', 'none', 'TAKE→SKIP')      13  ('C', 'Neutral_Center', 'up', 'SKIP→TAKE')
    12  ('D', 'Trend_Normal', 'up', 'TAKE→SKIP')      7  ('C', 'Neutral_Center', 'down', 'SKIP→TAKE')
     7  ('C', 'Neutral_Extreme', 'up', 'SKIP→TAKE')   7  ('C', 'Nontrend', 'down', 'SKIP→TAKE')
     7  ('C', 'Trend_Normal', 'none', 'SKIP→TAKE')    7  ('D', 'Variation', 'two_sided', 'TAKE→SKIP')
```

TAKE→TAKE with a different exit / gate policy (verdict unchanged, leaf policy changed):

```
    46  take_with_extension → take_with_hint        skip_gates [entry_location_quality] → []      (§3.4)
    16  take_location → kinds_variation leaf        exit None → {t1_r 1.5, t2_r 2.5}             (Neutral label, up|down IB)
    12  trend_row path leaf → take_with_hint        exit {1.5, 2.5} → None                       (Trend label, kinds_trend → with-hint)
     2  take_failed_ext_responsive → take_with_hint exit {1.5, 2.5} → None
     1  path leaf → kinds_variation leaf            exit None → {1.5, 2.5}
```

Hour values reaching the `ctx_CD` hour node: C 17h 332 · 18h 685 · 19h 681 · 20h 703 · D 21h 598 (22h is cut at the root by both trees under 3.4.0; t529b itself predates the cutoff).

Net at candidate level the variant is **tighter** (146 TAKE→SKIP vs 75 SKIP→TAKE; 221 of 3,544 C/D verdicts change, 6.2%). Whether that is money is the harness's question.

---

## 5 · Harness — tomorrow morning (outside 16:00–23:05 IL; ≤ 2 in parallel)

Reference = same-night live config (brief §2 protocol (א)); variant = same env + `DECISION_TREE_V3_PATH`. Both on the 65 sessions of `harness_out/t529/sessions.txt`.

```bash
cd /Users/michael/Downloads/mems26_web_git
bash harness_out/t466/run_variant.sh t24ref "DECISION_TREE_V3=1 T1_REALISM_FLOOR_R_V1=1.5 IB_RETURN_HINT_RELEASE_V1=returning TREE_EDGE_FAMILIES=CEILING_FLIP,DOUBLE_TOP,DOUBLE_BOTTOM" harness_out/t529/sessions.txt
bash harness_out/t466/run_variant.sh t24ctx "DECISION_TREE_V3=1 T1_REALISM_FLOOR_R_V1=1.5 IB_RETURN_HINT_RELEASE_V1=returning TREE_EDGE_FAMILIES=CEILING_FLIP,DOUBLE_TOP,DOUBLE_BOTTOM DECISION_TREE_V3_PATH=/Users/michael/Downloads/mems26_web_git/config/decision_tree_v3.t24_context.yaml" harness_out/t529/sessions.txt
python3 harness_out/t494/cmp_vs_live.py t24ctx t24ref
python3 harness_out/t515/report.py --ref t24ref t24ctx
```

(`run_variant.sh` runs the two sessions in parallel internally — run the two commands **sequentially**, not side by side, to respect "≤ 2 in parallel". It skips sessions whose output JSON already exists; use fresh tags.)

**Acceptance (brief §2 (ד), walk-forward):** holdout = last 10 sessions of `sessions.txt` (2026-09-21 → 2026-10-02) Σ ≥ 0 **AND** Δnet > 0 on all 65 **AND** every month ≥ 0 — else **לא עולה** and the live tree stays. The rule was *not* chosen on the holdout: the variant contains no leaf chosen by number (every leaf is a live leaf; the only decisions were structural and are listed in §3).

Report the result as one line for the 08:30 inbox: `t24ctx vs t24ref (65): Δ gross … / net … · holdout-10 … · months … · better/worse …` plus the §3.1 / §3.4 caveats (D failed-extension lost; ELQ gate back on 46).

---

## 7 · Measurement (07.10, Michael 15:48 "do NOT wait for tonight") — **לא עולה**

Ran exactly §5, sequentially (t24ref 15:50→16:24, t24ctx 16:24→16:35 IL; never two `run_variant.sh` at once); full stdout in `harness_out/t24/run.out` (ends `ALL DONE`). Raw cmp lines:

```
$ PYTHONIOENCODING=utf-8 python3 harness_out/t494/cmp_vs_live.py t24ctx t24ref
t24ctx vs t24ref: 65 sessions · t24ref Σ+2633.65$ · t24ctx Σ+2513.00$ · Δ -120.65$ gross, ≈-99.85$ net of -8 round-trips · better 3 / worse 9 / same 53
by month Δ: 2026-06 +0 (8d) · 2026-07 -46 (17d) · 2026-08 -2 (19d) · 2026-09 -72 (19d) · 2026-10 +0 (2d)
trades: added 6 (wins 3, Σ+15.00$) · removed 14 (Σ+120.00$) · the rest of Δ is changed exits/targets of the same trades
```

`--days` (only the 12 sessions that moved): 07-08 −46.25 · 08-03 +41.25 · 08-13 −23.75 · 08-20 −56.25 · 08-21 −12.50 · 08-24 +48.75 · 09-01 −45.00 · 09-08 +0.00 (7→3 trades) · 09-09 −21.25 · 09-11 +47.50 · 09-14 −30.65 · 09-21 −1.25 · 09-23 −21.25.

| Acceptance axis (brief §2 (ד)) | Required | Measured | |
|---|---|---|---|
| Holdout — last 10 sessions of `t529/sessions.txt` (09-21 → 10-02) | ≥ 0 | **Δ −22.50$ gross / −25.10$ net** (09-21 −1.25 · 09-23 −21.25 · 8 sessions unchanged); absolute t24ctx Σ+510.60$ (31) vs t24ref Σ+533.10$ (30) — `harness_out/t24/holdout_abs.py` | ✗ (Δ) / ✓ (absolute) |
| Full set (65) | Δnet > 0 | **−99.85$ net** (−120.65$ gross, 8 fewer round-trips) | ✗ |
| Every month | ≥ 0 | 06 +0 · **07 −46 · 08 −2 · 09 −72** · 10 +0 | ✗ |

Verdict: **לא עולה** — Δnet and the months fail outright; the holdout passes only on the absolute reading (the variant did not lose money there) and fails on Δ. The context re-root (structure → hour → kind instead of the day_type label) removed 14 trades worth +120$ and added 6 worth +15$; the surviving trades' exits changed by about −15$ net. Consistent with the candidate-level walk-forward of `T543_STAGE5_CONTEXT_ROOT_2026-10-07.md` (Δ −304$, months 07/09 negative): the label carries information the IB structure alone does not. The live `config/decision_tree_v3.yaml` 3.4.0 was not touched (`git diff --quiet config/decision_tree_v3.yaml` ⇒ clean), nothing restarted, nothing committed.

Not done in this measurement (would need a second variant each): the §3.1 D `failed_extension` restoration and the §3.4 `take_with_extension` ELQ-skip alternative. Neither is queued — §2.4 is closed as measured-and-failed twice (candidate level 07.10 morning, harness level 07.10 afternoon); the brief moves on to the next item.

## 6 · Files

- `config/decision_tree_v3.t24_context.yaml` — the variant (uncommitted; kept for reference, unreachable from anything live).
- `docs/reports/T24_CONTEXT_VARIANT_2026-10-07.md` — this report.
- `harness_out/t466/t24ref_*.json` + `t24ctx_*.json` (65 + 65) · `harness_out/t24/run.out` — the measurement.
- Verification one-shots (outside the repo, reproducible): `/tmp/t24ctx_verify.py` → `/tmp/t24ctx_verify.out`; `/tmp/t24ctx_taketake.out`; `/tmp/t24ctx_bylabel.out`.
- Live tree untouched: `git diff --quiet config/decision_tree_v3.yaml && echo live-untouched` ⇒ `live-untouched`.
