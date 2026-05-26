# MEMS26 V9 — S4 Woodies CCI Pattern Tables (`s4_woodies_pattern_tables.xlsx`)

## Research Deliverable · Tel Aviv · 2026-05-23 · Owner: Michael Barg

**Provenance:** Researcher's narrative wrapper feeding D-092 + Sheets A/B/C. Recovered into repo 2026-05-25 IL by Cursor after Michael paste (paste was full document including TL;DR · Key Findings · Details · Recommendations · Caveats). Sheets A/B/C structured content already exists under `docs/spec_authority/`; this file is the narrative + source citations that motivate them.

**Status:** 📚 reference · informs D-092 LOCKED · sources cited for audit trail

---

## TL;DR

- **Build the file with honest 🔴 NO_STATS flags on all 9 Woodies CCI patterns** — no peer-reviewed CCI-pattern statistics exist anywhere in the public literature; the only defensible quantitative backing for S4 will come from MEMS26's own SHADOW database (2,467 S4 trades). Thomas Bulkowski's price-chart statistics (Head-and-Shoulders Top: 19% break-even failure rate / 16% average decline / 68% pullback rate / 51% meeting target / rank 9 of 36 / >2,800 perfect trades, per thepatternsite.com/hst.html stats updated 8/26/2020; Eve & Eve Double Bottom: 12% failure / 50% rise / 65% throwback / 65% meeting target / rank 5 of 39 / 952 perfect trades, per thepatternsite.com/eedb.html updated 8/4/25) anchor GHOST and VEGAS only as **clearly-flagged analogies**, not direct measurements.
- **Best/worst day-type pairings are systematic, not pattern-specific**: all 4 CONT patterns (ZLR/TLB/TT/GB100) get ✅ in TN/TDD and ❌ in NeuE/NT; all 5 REV patterns (VEGAS/GHOST/FAMIR/HTLB/HFE) get ✅ in NeuE/Norm and ❌ in TN/NT. **NT is universally ❌** (all 9 cells ❌). This follows directly from Liran's Stage-1 trend requirement (≥6 bars above ZL with at least one bar past ±100) and Dalton's auction-balance day-type taxonomy from *Mind Over Markets*.
- **Stop/target framework is universal**: CONT stop = entry-bar ±3 ticks (Liran's "momentum trade" rule) capped at 1.0×ATR-14 (5-min) and floored at 4 ticks; REV stop = last swing ± 3 ticks capped at 1.5×ATR-14. Target ladder per Liran: T1 = 4 ticks → ±200 cross opposite → ±100 cross opposite → ZL cross opposite (full exit). Default exit distribution 50% T1 / 30% T2 / 20% trail mirrors the S2 file.

---

## Key Findings

### 1. Source authority pyramid is shallow and Hebrew-centric

The single most complete documentation of all 9 patterns at the required level of detail is the **Liran/Zohar Leibovich Hebrew Woodies CCI Manual (Nov 2016)**, supplied by the owner. Ken Wood's primary materials — the 8-DVD home study course, the woodiescciclub.com forum archives, James L. O'Connell's *Basic Patterns and Terminology* PDF, and Jim O'Connell's trading-attitude.com PDFs — define the same 8–9 patterns but with looser tolerances. Wood's work is anecdotal chat-room transcripts and DVD narration from 1999–2008, not peer-reviewed. There is **zero Bulkowski-equivalent statistical work for CCI patterns** anywhere in the public literature.

### 2. Direct CCI statistics that exist (all weak)

- Barry D. Moore (liberatedstocktrader.com) ran a 43,297-trade aggregate backtest using TrendSpider software and reported "My 396 years of TrendSpider backtests revealed conclusively that the best setting for the Commodity Channel Index is using CCI-20 on a 1-minute chart, producing a 50% win rate." The backtest is plain CCI-20, not the 9 Woodies-specific patterns.
- A QuantifiedStrategies forex CCI-divergence backtest reported a 65% win rate over 3 years (small sample, daily timeframe, forex not futures).
- Picture Perfect Portfolios reported a CCI+MA confluence strategy at 10% annual return with "higher accuracy" — no N reported, content-site source.
- **None of these test the 9 Woodies-specific patterns.** Treat all as 🔴 anecdotal.

### 3. Bulkowski analogies (chart-pattern, not CCI-pattern)

For the **GHOST** pattern (CCI head-and-shoulders), the closest published analog is Bulkowski's Head-and-Shoulders Top: **19% break-even failure rate, 16% average decline, 68% pullback rate, 51% meeting price target, performance rank 9 out of 36, based on more than 2,800 perfect trades** (thepatternsite.com/hst.html, stats updated 8/26/2020). For **VEGAS** (cup-and-handle on the oscillator with a +200/−200 extreme + cup + handle structure), the closest analog is the Eve & Eve Double Bottom: **12% break-even failure rate, 50% average rise, 65% throwback rate, 65% meeting price target, performance rank 5 out of 39, based on 952 perfect trades** (thepatternsite.com/eedb.html, page updated 8/4/25). **Both analogies are price-chart on daily/weekly stock data, not CCI-line on 5-min futures — application is a documented regime shift.**

### 4. MES 5-min ATR-14 baseline

No first-party publisher (CME, Barchart, NinjaTrader) reports a 5-min ATR-14 for MES specifically. Triangulated from Young Money Investments' cited daily ATR range of 40–65 points for ES during 2024–2025 normal conditions, plus practitioner conventions (TraderFuel 2026, JustinTrading), the defensible derived range is:

- **Normal vol (daily ATR 40–55 pts):** 5-min ATR-14 ≈ **2–4 points = 8–16 ticks**
- **Elevated vol (daily ATR 60+):** 5-min ATR-14 ≈ **5–8 points = 20–32 ticks**
- **Low-vol/chop (daily ATR 20–35):** 5-min ATR-14 ≈ **1.5–2.5 points = 6–10 ticks**

This sets the ATR-cap multipliers on Sheet C §6.1.

### 5. Day-type mapping rationale

Per Jim Dalton's *Mind Over Markets* day-type taxonomy, the seven MEMS26 day types map cleanly onto continuation-vs-reversal logic:

- **TN, TDD**: Strong directional conviction, narrow IB, one-timeframing → CONT patterns thrive (CCI stays >6 bars above ZL with at least one bar past +100, ideally past +200 — exactly Liran's Stage-1 requirement). REV patterns systematically fail because divergences and CCI H&S formations get steamrolled by trend persistence.
- **NV (Variation)**: Most common day in the MEMS26 spec (~70%); matches Dalton's published 41.77% Normal Variation figure. Both CONT and REV work conditionally — CONT only in trend-direction of IB-extension, REV only at the rejected extreme.
- **NeuE (Neutral Extreme), NeuC (Neutral Center), Norm**: Both OTF participants active, balanced; REV patterns excel (fade extremes, range trade); CONT patterns get whipsawed.
- **NT (Non-trend)**: Per Dalton, ~6.81% of days, lacks directional conviction, narrow IB. CCI oscillates around ZL without ever achieving Liran's 6-bar trend lock. **All 9 patterns ❌.**

### 6. The four-state trend handling problem (P-W5)

Liran is explicit: trend doesn't flip in fewer than 6 bars, and a new trend needs at least one bar past ±100 to lock. The YELLOW state ("5th consecutive bar opposite — next bar will flip") is a *warning state*, not a tradeable state. **Researcher's read: YELLOW should block all 9 patterns**, because either (a) the prior trend is dying (CONT patterns invalid by definition — Stage-1 fails), or (b) the new trend isn't locked yet (REV patterns premature, FAMIR by Liran definition can only fire AFTER a Stage-3 ZLR). The A1 gate handling only GRAY is incomplete relative to Spec V1's 4-state design. Wood's transcripts call this state "WSI = Wait, Sit, Inspect."

---

## Details · Sheet A / B / C structured content

> **Note:** The structured per-pattern detail (Sheet A 9 rows), the 9×7 day-type verdict matrix (Sheet B 63 cells), and the Stop/Target/Trend/Caveats/Anti-patterns/P-W structure (Sheet C) are duplicated in machine-readable CSV form at:
>
> - `docs/spec_authority/S4_WOODIES_TABLE_A_Pattern_Setup.csv`
> - `docs/spec_authority/S4_WOODIES_TABLE_B_DayType_Matrix.csv`
> - `docs/spec_authority/S4_WOODIES_TABLE_C_Strategy_Caveats.csv`
> - Source-of-truth xlsx: `docs/spec_authority/S4_WOODIES_PATTERN_TABLES_V1.xlsx`
>
> See D-092 LOCKED (`docs/decisions/D-092_S4_WOODIES_UPDATE.md`) for the per-pattern doctrine summary. This narrative file preserves the prose justification and source citations only — the CSVs/xlsx remain canonical for structured lookup.

---

## Recommendations

**Stage 1 — Build the file now (this week):**
1. Generate `s4_woodies_pattern_tables.xlsx` using the three-sheet specification above. All 9 patterns marked 🔴 NO_STATS in the stats cells with the narrative analogies inline. ✅ DONE 23/5
2. Add the date-stamped header to Sheet A row 1: `MEMS26 V9 — S4 Woodies CCI Pattern Setup · MES 5-min RTH · 9 Patterns · 2026-05-23`. ✅ DONE
3. Cite Liran's Hebrew Manual inline on every pattern row (Author column). ✅ DONE

**Stage 2 — SHADOW data extraction (next 2 weeks):**
4. Run the recommended query per pattern: `SELECT * FROM v9_trades WHERE firing_system=4 AND pattern_name='X'` against MEMS26's local SQLite. Compute hit rate T1, hit rate T2, median MFE, median MAE, E[R], failure mode. Update the 🔴 NO_STATS cells with 🟢 if N≥500.
5. **Threshold for promoting a pattern from 🔴 to 🟢:** N≥500 SHADOW trades AND E[R] > 0 AND hit rate T1 > 40%.
6. **Threshold for dropping a pattern entirely:** N≥500 AND E[R] < 0 AND hit rate T1 < 35%.

**Stage 3 — Address P-W open questions:** ✅ all 10 LOCKED 25/5 — see `docs/handoff/MEGA_PROMPT_PW_DECISIONS_INTAKE.md` §Locked Decisions.

7. Fix P-W3 (ZLR test failures) first — audit test fixtures for Liran's Stage-1 completeness (≥6 bars above ZL + ≥1 bar >+200). · **LOCKED A** (audit-first probe · deferred to Pipeline 2 G0)
8. Extend A1 gate to block YELLOW (P-W5). · **LOCKED A** (block all 9 in YELLOW)
9. Normalize all 9 confidence scores to [0,1] (P-W8). · **LOCKED hybrid** (V1 = R_t1 comparator · normalization deferred to Phase B with SHADOW data)
10. Build YAML threshold loader (P-W9). · **LOCKED E** (Python defaults + optional YAML overlay)

**Stage 4 — Beyond V1:**
11. Re-run SHADOW after each Liran-threshold change to confirm robustness.
12. Decide P-W10 (all-9 keep vs drop) only after SHADOW phase completes per Stage 2 thresholds. · **LOCKED A** (keep all-9 through V1 SHADOW · post-launch decision)

---

## Caveats (10 numbered · same as Sheet C §8)

1. **Ken Wood's original work is largely 1999–2008 chat-room transcripts — not peer-reviewed statistical work.** Wood's DVDs and PDFs (Jim O'Connell's *Basic Patterns and Terminology*) teach but do not measure.
2. **No Bulkowski-equivalent stats exist for CCI patterns.** Statistical backing is weaker than S2. Do not invent stats.
3. **Woodies CCI was developed for forex / stocks daily — application to MES 5-min is a regime shift.** Wood himself uses CCI-20 (not 14) for daily+ timeframes and does not use TCCI on daily charts.
4. **TCCI (CCI-6) is a Woodies addition not in Donald Lambert's original CCI** (Lambert 1980 introduced CCI in *Commodities* magazine, October 1980). TT is Wood-specific.
5. **HFE has no Wood/Rensink documentation as MEMS26 codes it** — it is a MEMS26 internal pattern variant. Statistical backing must come from SHADOW data only.
6. **Sidewinder (SWI) is Wood-specific** — thresholds (>20 / <−20) are from Wood transcripts only, not from any non-Wood source.
7. **The 39 ZLR test failures (Master Index 16/5) are unresolved.** Do not assume ZLR is "working perfectly" without addressing P-W3.
8. **The Hebrew manual by Liran is an INTERPRETATION of Wood's work, not Wood himself.** Where Liran adds Zohar Leibovich's framework (specific entry timing windows, +210 cap on ZLR signal bar, ±50 strengthening rule for TT, "mentally hardest" framing for FAMIR), flag as "Liran/Zohar interpretation, not original Wood doctrine."
9. **Bulkowski analogies for GHOST and VEGAS are price-chart daily — not CCI 5-min futures.** The 12%/19% failure rates and 65%/68% throwback rates apply to stocks, not MES intraday CCI.
10. **Day-type assignments use Dalton's published frequencies (Normal Variation 41.77%, Trend 18.99%, Neutral 30.21%, Non-Trend 6.81%, Normal 2.43%)** which are stock-index data and may not match MES 5-min RTH 2026 distribution precisely.

---

## Cross-references

- D-092 LOCKED: `docs/decisions/D-092_S4_WOODIES_UPDATE.md`
- Sheet A Pattern Setup CSV: `docs/spec_authority/S4_WOODIES_TABLE_A_Pattern_Setup.csv`
- Sheet B Day-Type Matrix CSV: `docs/spec_authority/S4_WOODIES_TABLE_B_DayType_Matrix.csv`
- Sheet C Strategy & Caveats CSV: `docs/spec_authority/S4_WOODIES_TABLE_C_Strategy_Caveats.csv`
- Master xlsx: `docs/spec_authority/S4_WOODIES_PATTERN_TABLES_V1.xlsx`
- P-W locks (10 closed 25/5): `docs/handoff/MEGA_PROMPT_PW_DECISIONS_INTAKE.md` §Locked Decisions
- **DTV1 (1085 LOC · A1-A7 + B1-B14 · STANDALONE architecture)** — referenced by P-W1 lock but **not yet committed to repo** (pending Michael handoff)

---

*End of research deliverable · saved 2026-05-25 IL · informs but does not supersede D-092 LOCKED.*
