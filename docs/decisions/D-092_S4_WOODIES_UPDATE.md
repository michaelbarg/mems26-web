# D-092 — S4 Woodies CCI Spec V1 LOCKED

**Status:** 🔒 LOCKED
**Date:** 2026-05-23
**Decided by:** Michael Barg (researcher report Claude · approved 23/5 17:55)
**Supersedes:** Master Index V2 §S4 audit ("9 patterns · 8 built · HFE missing · 39 ZLR fails")
**Related:** D-074 (Woodies 5-min) · D-091 (S2 LIVE scope) · Constitution V3 §T2

---

## Source of truth

| Doc | Status | Role |
|---|---|---|
| `docs/spec_authority/S4_WOODIES_PATTERN_TABLES_V1.xlsx` | 🔒 LOCKED | **canonical** — 3 sheets |
| `docs/spec_authority/S4_WOODIES_TABLE_A_Pattern_Setup.csv` | reference | Sheet A · 9 patterns × 13 cols (Entry/Stop/T1/T2/T3/Filters/etc) |
| `docs/spec_authority/S4_WOODIES_TABLE_B_DayType_Matrix.csv` | reference | Sheet B · 9 patterns × 7 day types = 63 cells |
| `docs/spec_authority/S4_WOODIES_TABLE_C_Strategy_Caveats.csv` | reference | Sheet C · stop strategy · trend states · 9 anti-patterns · 10 P-W open · 10 caveats |

---

## Scope · 9 Patterns

### CONT (Continuation) · 4 patterns

| # | Name | Group | Source | Stats | Wood-doctrine notes |
|---|---|---|---|---|---|
| 1 | **ZLR** Zero Line Reject | CONT | Wood (def) · Rensink · Liran | 🔴 NO_STATS | "could be the only Woodies trade for your career" (Gannon) · 39 test failures (P-W3) |
| 2 | **TLB** Trend Line Break | CONT | Wood · Liran | 🔴 NO_STATS | "rarely standalone, usually combined" (Liran) |
| 3 | **TT** Tony Trade / Turbo Touch | CONT | Wood · Rensink (>5 CCI gap) · Liran (3-9 bar) | 🔴 NO_STATS | BLUE/RED only · never GRAY/YELLOW (Wood) |
| 4 | **GB100** Ghost Bar at ±100 | CONT | Wood · Liran (CZI + 6-bar rule) | 🔴 NO_STATS | Deeper-pullback variant of ZLR |

### REV (Reversal) · 5 patterns

| # | Name | Group | Source | Stats | Wood-doctrine notes |
|---|---|---|---|---|---|
| 5 | **VEGAS** Divergence / Cup-and-Handle | REV | Wood · Liran · Bulkowski (analog) | 🔴 NO_STATS | Min bar 20 · NeuE/NeuC/Norm only |
| 6 | **GHOST** CCI Head-and-Shoulders | REV | Wood · Liran (head-size irrelevant) · Bulkowski (analog) | 🔴 NO_STATS | "you gotta love a Ghost" (Wood) |
| 7 | **FAMIR** Failed ZLR at ±200 | REV | Wood · Liran ("mentally hardest pattern") | 🔴 NO_STATS | LSMA agreement mandatory |
| 8 | **HTLB** Horizontal Trend Line Break | REV-ish | Wood · Liran (zone definition) | 🔴 NO_STATS | Long-line [−100,−200] · short-line [+100,+200] |
| 9 | **HFE** Hook From Extreme | REV | Community · MEMS26-internal · Liran (level-confluence) | 🔴 NO_STATS | NO Wood doctrine · ~50% success but R>>L (Gannon anecdote) |

---

## Stop Architecture · ATR-14 based (NOT today_typical · differs from S2)

| Layer | Rule | Notes |
|---|---|---|
| **א · Primary CONT** | 2-3 ticks beyond entry-bar low/high | Liran's "momentum trade" rule |
| **א · Primary REV** | Beyond last swing extreme | per-pattern anchor (cup low · right shoulder · failed-ZLR bar · horizontal bar · extreme bar) |
| **ב · ATR cap CONT** (ZLR/TLB/TT) | **1.0× ATR-14** ≈ 8-16 ticks | normal vol |
| **ב · ATR cap medium** (GB100/HTLB) | **1.2× ATR-14** ≈ 10-20 ticks | |
| **ב · ATR cap REV** (VEGAS/GHOST/FAMIR/HFE) | **1.5× ATR-14** ≈ 12-24 ticks | |
| **ג · Floor** | **4 ticks** (MES tick-noise floor) | 1T = 0.25pt = $1.25 |

**Trail logic:** After T1 → BE+1T · After T2 → trail last-bar low/high (Liran ladder) · Also trail when TCCI crosses CCI-14 against position.

---

## Target Strategy

| Scheme | Patterns | T1 | T2 | T3 | R |
|---|---|---|---|---|---|
| CCI-based scaffold | ZLR · GB100 · HFE | 1R (4T) | 2R | 4R or trail | 2.0-3.0 |
| CCI pattern-measure | VEGAS · GHOST | Measure × 0.5 | Measure × 0.6 (haircut) | trail to opposite | 1.6-3.5 |
| REV R-multiples | FAMIR · HTLB | 1R | opposite ±100 | ZL / ±200 | 1.4-2.8 |
| TLB (CONT) | TLB | 1R | next swing extreme | ZL opposite | 1.5-2.5 |
| TT (CONT) | TT | 1R | +200 cross | ZL opposite | 1.5-2.5 |

**Liran's exit ladder** (cross-pattern): T1 (4T or 5T if net-vol) → ±200 cross opposite → ±100 cross opposite → ZL cross opposite → SWI red → new opposing pattern → CCI flat 3+ → TCCI cross.

**Default split:** 50% T1 / 30% T2 / 20% trail (matches S2).

---

## Trend State Handling (4 states)

| State | Rule | CONT | REV |
|---|---|---|---|
| **BLUE** uptrend | CCI > 50 + prev > 0 + SWI > 20 · Liran: ≥6 bars above ZL with ≥1 bar >+100 | ✅ FIRE | ❌ BLOCK |
| **RED** downtrend | Mirror of BLUE | ✅ FIRE | ❌ BLOCK |
| **YELLOW** transition (5th opposite bar) | **P-W5 OPEN** — researcher rec: BLOCK ALL 9. Wood: WSI ("Wait, Sit, Inspect") | ❌ | ❌ |
| **GRAY** chop / no trend | BLOCK or require confidence > 0.55 (current code) | ❌ | ❌ |

---

## Day-Type Matrix Summary (Sheet B detail · 63 cells)

| Day Type | CONT (1-4) | REV (5-9) |
|---|---|---|
| **TN** Trend Normal | ✅ ZLR/TLB/TT/GB100 fire | ❌ trend persistence overwhelms |
| **TDD** Trend DD | ✅ at 2nd distribution | ❌ extension dominates |
| **NV** Normal Variation (~70%) | ⚠️ IB-extension direction only | ⚠️ late-session IB-exhaustion only |
| **NeuE** Neutral Extreme | ❌ CCI extremes clipped | ✅ fade IB-extreme (home) |
| **NeuC** Neutral Center | ⚠️ mini-trend in VA only | ✅ range edges = ideal |
| **Norm** Normal rotation | ⚠️ scalp only | ✅ fade VA edges |
| **NT** Non-Trend | ❌ no Stage-1 trend lock | ❌ no swing structure |

**Rule:** ALL 9 fail in NT (~6.81% of days). CONT fail in NeuE/NT. REV fail in TN/TDD.

---

## 9 Anti-patterns (do not fire)

| # | Trigger |
|---|---|
| AP1 | ZLR after >12-bar pullback (CCI memory fades · Rensink) |
| AP2 | GB100 in YELLOW state (fake breakout · Wood) |
| AP3 | VEGAS without 5+ bars between swings (noise · Liran) |
| AP4 | HTLB with <2 touches (single bounce ≠ level) |
| AP5 | HFE without bars_since_extreme ∈ [2,12] (MEMS26 constraint) |
| AP6 | GB100 where CCI stays >6 bars opposite ZL during pullback (trend flipped · Liran) |
| AP7 | TT with TCCI gap < 5 CCI (incomplete cross · Rensink) |
| AP8 | Any pattern when CCI flat (range < 50) ≥3 bars (Raschke) |
| AP9 | FAMIR without LSMA agreement (Wood + Liran) |

---

## 10 Open Questions (P-W series) — Michael decisions pending

| ID | Question | Researcher Recommendation | Status |
|---|---|---|---|
| **P-W1** | DTV1 verbatim paste | internal task | ⏳ open |
| **P-W2** | HFE dual-path · DLL-only canonical or keep Python fallback? | DLL=primary · Python=audit/fallback · log divergences for SHADOW | ⏳ open |
| **P-W3** | 39 ZLR test failures — root cause? | likely Stage-1 incomplete fixtures (BLUE declared but no >+200 touch) · audit fixtures BEFORE assuming regression | ⏳ open |
| **P-W4** | JSON 18s bug (gateway `_persist_trade` datetime) — fixed? | internal · no doctrine | ⏳ open |
| **P-W5** | Trend YELLOW — block fire or pass through? | **BLOCK ALL 9** (Wood WSI · Liran "next bar flip") · extend A1 gate | ⏳ open |
| **P-W6** | Priority Dispatcher when 2 patterns fire same bar — max(confidence) or DTV1-spec hierarchy? | DTV1-spec hierarchical · same-direction = max confidence · opposite-direction = Stage-1 gate breaks tie · CONT wins in BLUE/RED | ⏳ open |
| **P-W7** | 6th touch-point identity (Master Index says 6 · Canvas shows 5) | documentation reconciliation · internal | ⏳ open |
| **P-W8** | Confidence formulas — normalize before max()? | **YES NORMALIZE** all-9 to [0,1] via z-score or min-max · mixed dynamic+fixed creates dispatcher bias | ⏳ open |
| **P-W9** | YAML config loader for thresholds — V1 static or YAML? | YAML-driven · current defaults locked as "Liran baseline" profile | ⏳ open |
| **P-W10** | Keep all-9 (V1) vs SHADOW-data-driven drop? | Keep all-9 through V1 SHADOW · drop threshold: N≥500 AND E[R]<0 AND hit-rate T1<35% · promote 🔴→🟢: N≥500 AND E[R]>0 AND hit-rate T1>40% · data-driven, not doctrine-driven | ⏳ open |

---

## 10 Researcher Caveats — flag explicitly

| # | Caveat |
|---|---|
| 1 | Ken Wood's work is 1999-2008 chat-room transcripts — NOT peer-reviewed |
| 2 | NO Bulkowski-equivalent CCI stats — statistical backing weaker than S2 — do not invent stats |
| 3 | Woodies developed for forex/stocks daily · MES 5-min is regime shift · Wood uses CCI-20 not CCI-14 for daily+ |
| 4 | TCCI (CCI-6) is Wood addition not in Lambert's original CCI (1980) · TT is Wood-specific |
| 5 | HFE has NO Wood/Rensink documentation as MEMS26 codes it · MEMS26-internal variant |
| 6 | Sidewinder (SWI) thresholds (>20 / <−20) from Wood transcripts only · no non-Wood source |
| 7 | 39 ZLR test failures (Master Index 16/5) UNRESOLVED · don't assume "working perfectly" |
| 8 | Hebrew manual by Liran is INTERPRETATION of Wood · Liran/Zohar additions NOT original doctrine |
| 9 | Bulkowski analogies for GHOST/VEGAS are price-chart daily · NOT CCI 5-min futures |
| 10 | Day-type frequencies use Dalton's stock-index data · may not match MES 5-min RTH 2026 |

---

## Stage path (4 stages · per researcher §REC)

| Stage | When | Deliverable |
|---|---|---|
| 1 — NOW | this commit | xlsx + D-092 saved · spec locked |
| 2 — Next 2 weeks | post-Pipeline 2 Pkg 0 | SHADOW data extraction · per-pattern hit-rate · MFE/MAE · E[R] |
| 3 — Address P-W | per package gates | Fix P-W3 first (ZLR fixtures) · YELLOW gate (P-W5) · normalize confidence (P-W8) · YAML loader (P-W9) |
| 4 — Beyond V1 | post-SHADOW | re-run SHADOW after threshold change · decide P-W10 (keep vs drop) |

---

## Decision

✅ **S4 Woodies V1 LOCKED** with 9 patterns · ATR-14 stop architecture · day-type matrix · 9 anti-patterns · 10 P-W open · 10 caveats.

**Action items:**
1. Pipeline 2 (S4) build queue opens — see `docs/plans/PRE_LIVE_PIPELINE_2026-05-23.md` §Pipeline 2
2. 10 P-W open questions are pre-flight items for Pipeline 2 packages (each P-W maps to a package)
3. NO LIVE for S4 until SHADOW analysis closes promote/drop decision per P-W10

**Changes from previous state:**
- HFE no longer "missing" — defined as MEMS26-internal with Python fallback
- 39 ZLR test failures = P-W3 (now tracked, was floating)
- ATR-14 stop pipeline declared (was implicit · differs from S2's today_typical)
- YELLOW state explicitly BLOCK (was undefined)

---

*End of D-092 · 🔒 LOCKED · changes only via new D-XXX.*
