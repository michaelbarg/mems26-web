# Pattern Definitions Index — STOP + PROFIT placement per pattern (source ↔ code)

_Created 2026-06-26 (Cowork). Agenda for a dedicated chat to finalize, for **every** pattern,
**where the stop goes and where the profit goes** — reconciling the source of truth against the code._

## How to use (new chat)
Open a new chat **in this project** (auto-loads CLAUDE.md + memory). Start with:
> "עבור איתי על `docs/spec_authority/PATTERN_DEFINITIONS_INDEX.md` — נסדר לכל תבנית איפה הסטופ ואיפה הרווח, מול המקור."

Work **one pattern at a time**. For each, decide the final **🛑 stop** and **🎯 T1/T2/T3** placement,
then write it into `config/stop_anchors.yaml` + `config/targets.yaml` and flip the State to ✅.

## The central finding (read first)
- **Source = per-pattern, structural.** `S4_WOODIES_TABLE_A` + `S4_WOODIES_TABLE_C §6.1/§6.2` define the
  stop and the targets **per pattern**: stop = N ticks beyond the pattern's own structure (signal bar /
  swing / shoulder / failed bar); targets = CCI-cross levels (±200 → ±100 → ZL) or pattern-measure
  (cup/H&S height), **not** flat R-multiples.
- **Code today = day-type R-multiples.** Live targets come from `targets_table.py` per **day-type**
  (Trend_Normal 1R/2R/4R, Variation 1R/2.5R/trail, …) — **not** per-pattern, **not** the source's
  CCI-cross/measure rule. (memory: "targets R-based not structural".)
- **The per-pattern STRUCTURAL stop already exists in `config/stop_anchors.yaml`** (Michael+research
  2026-06-07) — anchor type + window + risk-cap per pattern — **but it is flag-gated OFF**
  (`STOP_ANCHORS_V2`, SHADOW-only). So the source-correct stop is authored but not live.
- **So the job per pattern = pick the canonical stop + profit (source vs code), set it in the YAMLs,
  and decide whether to enable `STOP_ANCHORS_V2` / per-pattern targets.**

## Cross-cutting rules (Table C §6.1/§6.2 + stop_anchors.yaml — decide once, apply to all)
- **Stop anchor**: structural extreme **∓ 3 ticks** (`anchor_offset_ticks: 3`). Structural stop ALWAYS
  wins; ATR is only a **size gate** (`atr_cap_role: size_gate`). **Floor 4T.**
- **ATR cap (size gate)**: CONT (ZLR/TLB/TT) `1.0×ATR-14` · GB100/HTLB `1.2×` · REV (VEGAS/GHOST/FAMIR/HFE) `1.5×`.
- **Risk → contracts ladder**: ≤15pt → 3 · ≤25pt → 2 · >25pt → 1. Hard risk cap **25pt** ($125). Strategic≤3 / tactical≤2.
- **Profit scaffolds**: CONT = T1 1R / T2 2R / T3 4R-or-trail **OR** Liran ladder (±200 cross → ±100 cross
  → ZL cross). REV = pattern-measure (cup/H&S height × MES coef ≈ 1pt/25 CCI; T1 ×0.5, T2 ×0.6 haircut). Default split 50%T1 / 30%T2 / 20%trail.
- **Trail**: after T1 → BE+1T · after T2 → trail (or DYNAMIC_STRUCT_TRAIL re-anchor to each new consolidation).
- **Time stop (day-type)**: TN none · TDD 90m · NV 60m · NeuE 45m · NeuC 30m · Norm 30m · NT no-trade.

---

## S4 — Woodies (source: `S4_WOODIES_TABLE_A` rows · code: `stop_anchors.yaml` + `targets_table.py`)

### 1 · ZLR (CONT) — ✅ entry source-aligned (`ZLR_SPEC_V2`)
- 🛑 **Stop** — SOURCE: 3T below signal-bar low, cap 1.0×ATR, floor 4T. CODE: `cluster_low` window 4, −3T, max_risk 15pt (✅ Michael).
- 🎯 **Profit** — SOURCE: T1 +4T≈1R · T2 = ±200 cross opposite · T3 = ±100 cross opposite or trail (R≈2–3). CODE: day-type R (e.g. 1R/2R/4R).
- ❓ **Decide**: keep cluster_low stop? Targets = source CCI-cross (±200/±100) **or** day-type R? (this is the main fork for all CONT.)

### 2 · TLB (CONT) — 🟡 Stage 1 only (`TLB_SPEC_V2`); Stage 2 unbuilt
- 🛑 SOURCE: 3T below signal-bar low, cap 1.0×ATR. CODE: `since_trendline_peak` window 8 (🔬).
- 🎯 SOURCE: T1 1R · T2 = next CCI swing extreme (±200) · T3 = ZL cross (R 1.5–2.5). CODE: day-type R.
- ❓ Decide stop window (3–8) + targets; **+ define Stage 2** (toothed-line + break-near-0).

### 3 · TT (CONT) — ⚠️ 0 fires ever (touch-then-bounce ~0.23% of bars)
- 🛑 SOURCE: 3T below signal-bar low, cap 1.0×ATR. CODE: `zl_excursion` window 9 (🔬).
- 🎯 SOURCE: T1 1R · T2 = +200 cross · T3 = ZL (R 1.5–2.5). CODE: day-type R.
- ❓ Decide stop + targets; **+ is the source trigger stricter/looser?** (why 0 fires.)

### 4 · GB100 (CONT) — ⚠️ used as CONT partner; own def unconfirmed
- 🛑 SOURCE: 3T below signal-bar low, cap **1.2×ATR** (deeper pullback). CODE: `cluster_low` window 6 (🔬).
- 🎯 SOURCE: T1 1R · T2 = +200 cross · T3 = ZL (R 1.5–3.0). CODE: day-type R.
- ❓ Standalone entry def + stop/targets.

### 5 · VEGAS (REV) — ✅ entry source-aligned (`VEGAS_SPEC_V2` cup-and-handle)
- 🛑 SOURCE: 3T beyond cup low, cap 1.5×ATR. CODE: `swing_extreme`, max_risk 20pt (✅).
- 🎯 SOURCE: **pattern-measure** — T1 = cup-height×0.5 (~16T at 200-CCI), T2 = ×0.6, T3 = trail to ZL (R 1.8–3.5). CODE: `t1_measure_cap 0.75`, `t2_measure_mult 1.0` (✅ 2026-06-10) — measure-based ✓ but different coefficients vs source.
- ❓ Reconcile measure coefficients (source 0.5/0.6 vs code 0.75/1.0).

### 6 · GHOST (REV) — ⚠️ not vs source (CCI H&S)
- 🛑 SOURCE: 3T beyond right shoulder, cap 1.5×ATR. CODE: `shoulder`, max_risk 18pt (🔬).
- 🎯 SOURCE: measure T1 = head-to-neckline×0.5, T2 ×0.6, T3 trail (R 1.6–3.0). CODE: `t1_measure_cap 0.5` ✓.
- ❓ Full characterization + confirm measure.

### 7 · FAMIR (REV) — ⚠️ not vs source (failed ZLR at ±200)
- 🛑 SOURCE: above failed-ZLR signal-bar high (flip stop), cap 1.5×ATR. CODE: `failed_bar`, max_risk 12pt (🔬).
- 🎯 SOURCE: T1 1R · T2 = opposite ±100 · T3 = opposite ±200 or ZL re-cross (R 1.5–2.8). CODE: day-type R.
- ❓ Full characterization + stop/targets.

### 8 · HTLB (REV) — ✅ as direction signal (`HTLB_DIRECTION_GATE`)
- 🛑 SOURCE: 3T below horizontal-breakout bar low, cap 1.2×ATR. CODE: `consolidation_extreme` (🔬, widened — NOT the breakout bar).
- 🎯 SOURCE: T1 1R · T2 = opposite ±100 · T3 = ZL (R 1.4–2.8). CODE: day-type R.
- ❓ Is HTLB also a standalone ENTRY (with this stop/target), or only the bias signal? + reconcile stop anchor (source=breakout bar vs code=consolidation extreme).

### 9 · HFE (REV) — ❌ DISABLED (`HFE_DISABLED=1`, "not my pattern", −$2,987)
- 🛑 SOURCE: 3T beyond extreme bar, cap 1.5×ATR. CODE: `extreme_bar`, `t1_ladder_shift −1`, max_risk 20pt (🔬).
- 🎯 SOURCE: T1 1R · T2 = opposite ±100 · T3 = ZL (R 1.4–2.5). CODE: day-type R.
- ❓ **Stays off forever, or is there a real pattern to redefine?** (decide before touching stop/targets.)

---

## S2 — Five-Min (source: `S2_EXIT_DEFINITION_V6` + `S2_AUTH_TABLE_V1` · code: `stop_anchors.yaml`)
S2 exits are **thesis-based** (not price-based): stop is the mechanical safety net at the structural
anchor; the TradeManager exits earlier on Type-A thesis-break (close+volume / opposing belly / TCCI×CCI
cross / direction-change). Type-B (wick / throwback / low-vol spike) = stay. Type-C = day-type time-stop on DD.

### REACTIVE — ✅ defined + fires
- 🛑 Stop SOURCE: structural — below belly low (LONG) / above belly high. CODE: `support_zone` window 4, max_risk 15pt (🔬).
- 🎯 Profit: day-type R (targets_table) + Type-C time stop; exit early on Type-A (close<belly low+vol / new opposing belly / POC flip / TCCI cross).
- ❓ Confirm stop anchor + the daytype_position_gate Variation rule (SHORT only if IB broke down).

### INITIATIVE — ✅ defined + fires
- 🛑 Stop SOURCE: structural — the broken level / breakout bar. CODE: `breakout_bar` window 1 (TIGHT — ✅ Michael, measured tight wins +11%).
- 🎯 Profit: day-type R; exit early on Type-A (close back through broken level + volume = failed breakout).
- ❓ Confirm tight stop + targets.

### Double_BT · HnS · Flag (S2 reversal/continuation) — ⚠️ verify wired + defined
- 🛑 CODE anchors exist: Double_BT=`second_bottom_top` · HnS=`shoulder` (right shoulder, not neckline) · Flag=`breakout_bar` w1 (✅ Michael).
- 🎯 + Type-A exits per family (S2_EXIT_V6 §"per pattern family"). ❓ Confirm these fire + their stop/targets.

---

## Suggested order (new chat)
1. **Decide the cross-cutting fork**: CONT targets = source CCI-cross (±200/±100/ZL) **or** day-type R? This sets the pattern for all CONT.
2. **Confirm the ✅ ones** (ZLR, VEGAS, HTLB, REACTIVE, INITIATIVE) stop+profit.
3. **TT, GB100, GHOST, FAMIR** — characterize + set stop/profit.
4. **TLB Stage 2** + **HFE decision**.
5. **Decide `STOP_ANCHORS_V2`** on/off (per-pattern structural stops) — currently OFF.
6. Write every decision into `config/stop_anchors.yaml` + `config/targets.yaml`; update each State to ✅.

## Key files
- Source: `S4_WOODIES_TABLE_A_Pattern_Setup.csv` (per-pattern), `S4_WOODIES_TABLE_C_Strategy_Caveats.csv` (§6.1 stop / §6.2 target / §6.5 anti-patterns), `S2_EXIT_DEFINITION_V6.md`, `WOODIES_PATTERNS_SOURCE_VS_CODE_2026-06-23.md`.
- Code: `config/stop_anchors.yaml` (per-pattern stop, flag STOP_ANCHORS_V2), `config/targets.yaml` + `backend/v9/systems/day_type/targets_table.py` (day-type targets), `backend/v9/systems/woodies/atr_stop.py` (stop engine), `backend/v9/systems/five_min/atr_caps.py` (per-pattern trail overrides).
