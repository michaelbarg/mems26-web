# External Research Brief — Structural Profit-Target Resolver (tool-constrained)

**For:** an external research agent with **no access to our system or data** — pure research from trading literature + practitioner consensus.
**Deliverable:** a precise, tool-constrained specification for placing profit targets (C1/C2/C3) that are structural, sensibly-distanced, consistent across patterns, and correct per day-type.
**Hard rule:** every rule must be expressible using ONLY the §2 tools we have (below). Where best practice needs a capability we lack, re-express it as a §2 proxy or drop it and say so.
**Tagging:** **[C]** = broad practitioner/AMT consensus (keep regardless) · **[K]** = calibration-dependent (we settle on live data). **All numbers are PRIORS to calibrate, not facts.**

---

## 1 · System context
MEMS26 is an autonomous MES (Micro E-mini S&P) **5-minute RTH futures** system. It classifies each session into one of **7 Market-Profile day-types** — `Trend_Normal`, `Trend_DD` (double-distribution), `Variation`, `Normal`, `Neutral_Center`, `Neutral_Extreme`, `Nontrend` — and trades **3 contracts** (C1/C2/C3) per fire, scaling out at three targets with a trailing runner. Patterns are continuation (ZLR, TLB, TT, GB100, INITIATIVE, Flags) and reversal (REACTIVE, GHOST, VEGAS, FAMIR, HTLB, Doubles, HnS).

## 2 · The tools/data we actually have (the hard constraint)
- **5-min OHLCV bars**, RTH + overnight (continuous).
- **Developing value area:** VAH / VAL / POC from TPO (updates ~30-min; the initial balance / IB locks ~60 min into RTH).
- **Initial Balance:** IB high / low / width (first 60 min).
- **Prior-day** VAH/VAL/POC, **PDH/PDL**, overnight high/low.
- **One CVD line** (per-bar delta + running cumulative) + volume.
- **Swing highs/lows** — computable from bars (pivot/fractal, lookback K).
- LSMA, Woodies CCI studies, ATR.
- **We do NOT have:** footprint, per-cell absorption, order-book depth, stacked-imbalance detection.

## 3 · The problem to solve (real, observed 2026-07-01)
Current targets are **wildly inconsistent and often broken**:
- **Too close:** ZLR LONG → T1 **+4.75pt**, T2 +9.5 (R-multiples off a tight stop; realizes tiny profit).
- **Crazy far / unreachable:** HTLB SHORT → T1 **−92pt**, T2 −116, T3 −140; REACTIVE SHORT → −88/−112/−136; INITIATIVE LONG → +26/+49/+72. (Reversal-pattern "measured move" targets explode to 90–140 points — effectively no reachable target.)
- **Inconsistent across patterns** on the same day.

We want to replace this with a **structural resolver** that reads the real levels + candle geometry and places sensible, consistent targets.

## 4 · What to research (the questions)
**Q1 · T1 as a swing-completion (the priority).** Best practice for a **near, high-probability first target** = the **completion of the first new structural swing** in the trade's direction (first higher-high for longs / lower-low for shorts). Research: how is "the first swing completion" defined on 5-min bars (pivot lookback K; confirmation)? How near should T1 be (min/max points or ATR fraction) so it's fast but not noise? This is the fix for BOTH the too-close and the too-far problems — T1 is always the **first structural step**, never a fixed R or a 90-pt measured move.

**Q2 · T2 / T3 as structural lines + measured moves.** Which lines to prefer, and the precedence, per day-type: VA edges (VAH/VAL), POC, IB edges, PDH/PDL, measured moves (IB-width extensions), the next distribution/single-print. When multiple are available, which wins? How to trail C3 (swing-based step / chandelier ATR) so a real trend-day runner still runs?

**Q3 · Sanity distance caps.** A formula to bound target distance (ATR-multiple? IB-multiple? nearest-structure?) that **prevents the 90–140pt garbage** for reversal patterns, WITHOUT capping a legitimate Trend_Normal runner. What is the max sane T1 distance vs the max sane runner distance?

**Q4 · Per day-type target logic (all 7).** For each day-type, the C1/C2/C3 structural rule grounded in Dalton / Market-Profile / practitioner consensus. Our current per-day-type intent (to validate/refine):
| Day-type | style | C1 | C2 | C3 |
|---|---|---|---|---|
| Trend_Normal | movement | remote checkpoint | measured extension | hold to close (trail) |
| Trend_DD | movement | 2nd-distribution POC | measured move | trail behind structure |
| Variation | movement | half IB-extension | one IB-extension | measured move |
| Normal | location | IB-center | opposite VA edge | opposite IB edge |
| Neutral_Extreme | location | POC | opposite VA edge | winning extreme |
| Neutral_Center | location | POC | opposite IB edge | — (no runner) |
| Nontrend | location | POC | — | skip |
**Michael's preference:** on trend days (esp. Trend_DD) use **new-swing-high/low completion stages** to take T1 (near, not far); prefer **important lines** for T2/T3 when available.

**Q5 · The reversal-pattern target explosion.** Why do "measured move" targets for reversal patterns (HTLB, REACTIVE, VEGAS, GHOST) reach 90–140pt on 5-min MES, and how should reversal targets be structured instead (nearest opposing structure / mean-reversion to POC, capped)?

## 5 · Required output
1. **Per-day-type target-placement table** — C1/C2/C3 rule (line or geometry) + trail + the one-line "why", for all 7 day-types, long and short.
2. **T1 swing-completion definition** — pivot params (lookback K, confirmation), near/far bounds. [C] vs [K].
3. **Sanity-cap formula** — the distance bound(s), with the reasoning.
4. **Tunable-parameter list** — every threshold with a prior value + [C]/[K] tag + one-line note.
5. **A worked example per day-type** (plausible MES ~7,550 regime): entry, the levels used, C1/C2/C3 in points, why.
6. **Keep-regardless vs fit-and-validate** split (which rules are theory [C], which need our data [K]).

## 6 · Constraints & anti-goals
- Express every rule with §2 tools only; footprint-dependent ideas → §2 proxy or dropped (say which).
- Priors, not measured facts. Distinguish [C] / [K].
- Do NOT propose targets that require order-flow/footprint we lack.
- The output must let our engineers implement the resolver + a follow-up calibration on live bars — so be concrete about the geometry and the numbers.
