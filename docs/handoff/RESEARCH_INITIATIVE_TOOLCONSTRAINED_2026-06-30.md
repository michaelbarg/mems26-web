# Research Brief — INITIATIVE pattern: tool-constrained construction & management

**For:** a research Claude with **NO access to our trading system, code, or data** (a pure literature/design synthesis — like the AMT/Dalton brief we already have).
**Date:** 2026-06-30 · **Prepared by:** Cowork (for Michael).
**Relationship to the other handoff:** this is the *theory/design* half. A separate agent **with** system access (CC) will backtest + calibrate on our live data. Your job is to produce the **buildable design**, expressed **only in terms of the tools we actually have** (below), plus the parameter priors and open questions CC will then calibrate.

---

## 0 · Your task
Research and design **how to best CONSTRUCT (detect/enter) and MANAGE (stop/target/trail/exit)** the **Initiative** trade pattern (Auction Market Theory — initiative = aggressive trade *accepted beyond value*, building new value, the engine of trend days; the location-based opposite of responsive/reactive). 

**Hard constraint:** every recommendation must be expressible using **ONLY the tools listed in §2.** Where best-practice needs a capability in §3 (which we do NOT have), say so explicitly and propose the **closest proxy** built from §2. You cannot backtest (no data) — deliver a design + parameter priors + a worked example, not measured results.

Cover **both** initiative-long and (by symmetry) initiative-short.

---

## 1 · What we already believe (start here; confirm/refute/refine with sources)
- Initiative = **location + acceptance**, not the action: aggressive buying **accepted above** value (prior-day VAH / IB-high / balance-high) that **builds new value up**; reactive = fading **below** value back to POC. Same order — location defines it.
- **Acceptance vs rejection is the crux.** Acceptance ≈ multiple consecutive closes beyond the level + value building there; rejection = single-print wick that snaps back within 1–2 bars (failed auction → reactive setup the other way).
- Trend days are **rare (~9.5%)** → initiative signals must be filtered by a **strict conjunction** (require ALL conditions, not any).
- From our own (separate) live-data look: **duplicate/clustered fires** destroyed past P&L; entries **far below value** (chasing) lost; a winner entered **at the value edge** with **rising CVD** and trailed a large runner; a prior in-house measurement found a **tight** initial stop outperformed a wide one (counter to the "give it room" consensus) — a tension to resolve conceptually.

## 2 · The tools we currently have — DESIGN ONLY WITH THESE
Per 5-min RTH bar / session, the system can read:
1. **5-min OHLC + volume** (RTH).
2. **Market-Profile value area:** POC, **VAH, VAL** — both *developing* (intrabar) and session; **value migration** over time.
3. **One Cumulative Delta (CVD) line** — live per-bar net delta + running cumulative. *(A single delta series — see §3.)*
4. **LSMA** (least-squares MA, ~fast) + **Woodies CCI** — trend slope/direction.
5. **7-type day-type classifier:** Trend_Normal, Trend_DD, Variation, Normal, Neutral_Center, Neutral_Extreme, Nontrend (with confidence + lock state, locking ~60 min after open).
6. **Opening-type:** Open-Drive, Open-Test-Drive, Open-Rejection-Reverse, Open-Auction (in/out).
7. **Initial Balance (IB)** high / low / width (first hour).
8. **Prior-day VAH/VAL/POC, prior-day high/low, overnight high/low** *(assume available from session profiles; flag any you lean on heavily so we can confirm).*
9. **Structural-targets engine** — can project targets to real levels (IB extensions, POC, VA edges) and/or R-multiples per day-type.
10. **Per-pattern stop anchors** — e.g. breakout-bar low, support/consolidation extreme — each with a fixed tick offset and a max-risk cap.
11. **Structural trailing** — "re-anchor the runner on each new consolidation after an advance" — plus a simple high-water trail.
12. **3-contract scale-out** (independent target/stop per contract).
Execution: MES, RTH, single position at a time, demo/sim.

## 3 · Tools we DO NOT have — do NOT design around these
- **No footprint / per-price-level bid×ask matrix** → **no stacked-imbalance (3:1) detection, no per-cell volume filter.**
- **No COT/AMT / order-flow-by-cell** (the footprint subsystem is disabled).
- CVD is **one cumulative line**, not a delta-per-level grid.
➡️ Any best-practice that relies on stacked imbalances / absorption-by-cell **must be re-expressed** using the single CVD line + volume + value-building, **or dropped**. Making that translation well is a core part of this brief.

---

## 4 · Research questions

### A — Construction (detect + enter)
- **A1 Acceptance (the key tunable).** Using only **bar closes + developing-VA expansion**, what is the best acceptance rule beyond a reference? Compare **N consecutive 5-min closes** (2 = fast vs ~6 = the 30-min "80% rule") and how to combine "closes beyond" with "developing value expanding to include the new prices." Give a recommended default + the trade-off curve.
- **A2 Which reference is the line?** prior-day VAH vs IB-high vs current-session developing VAH — decision logic as a function of opening-type and day-type.
- **A3 CVD from a single line (no footprint).** Best confirmation: **new-session-high**, **acceleration** (delta/slope jump on the breakout bar), and a **divergence/absorption proxy** (price new high while CVD makes a lower high). Define each as a tunable threshold expressible from one CVD series + volume.
- **A4 Geometry from OHLC only.** Impulse → shallow test (higher-low / POC-return / **VAH-retest**) → continuation/breakout. Parameterize impulse size (relative to ATR/IB), test depth, and breakout confirmation.
- **A5 Distance & size filters.** A **max-distance-from-value** cap (anti-chase) and **IB-width-relative** sizing — built from VA/IB/ATR.
- **A6 Context conjunction.** Of {day-type ∈ trend/Variation (+confidence), opening-type drive, LSMA up-and-held, value migrating up, OTF higher-lows}, which should be **REQUIRED** vs **confirming**, given the strict-conjunction need? Propose the **minimal mandatory set**.

### B — Management (stop / target / trail / exit)
- **B1 Entry timing.** Acceptance-bar close (aggressive) vs **retest-and-hold** of the broken level (conservative) — trade-offs, both buildable from our bars/levels.
- **B2 Stop.** Options within our anchors: broken-level, breakout-bar low, retest low, below-test-low. **Resolve the tension:** consensus says "give initiative room," but our in-house measure found **tight wins** — explain *why a tight stop can outperform on accepted breakouts*, and specify *when* a wider structural stop is justified (regime/volatility).
- **B3 Targets.** IB-multiples (1× / 1.5× / 2× / 3×) vs structural (POC / VA-edge / prior-day high / naked POC) — which mapping best fits our structural-targets engine, and how to assign across **3 contracts**.
- **B4 Trail / exit.** OTF higher-lows vs LSMA-cross vs **consolidation re-anchor** (we have a structural trail) — the rule that keeps the most runner while exiting on real structure breaks. Specify explicit exit triggers: close back inside value, close below LSMA, CVD divergence, OTF break (bar low < prior low).
- **B5 Failed-initiative → reactive flip.** Detect a failed breakout (close back inside within 1–2 bars + CVD divergence/stall) and optionally flip to a **reactive short toward POC** — designed with our tools.

---

## 5 · Deliverable
A **tool-constrained construction + management spec**:
1. Entry state-logic (a small state machine) using **only §2 inputs**.
2. A **tunable-parameter table** — acceptance N, CVD thresholds, distance cap, size filters, stop, targets, trail — each tagged **consensus** vs **calibration-dependent**, with a recommended prior value.
3. A **"theory needs X (which we lack) → use proxy Y"** mapping (esp. for the missing footprint/imbalance signals).
4. A **worked numeric example** (plausible MES values at the current index regime) showing the rule firing — and one **failure/rejection** variant.
5. **Open calibration questions** to hand to the system-access agent (CC) to settle on live data.

## 6 · Rigor
Cite Auction Market Theory (Dalton, *Mind Over Markets*), Market-Profile practitioner sources, and order-flow/CVD educators. Distinguish **broad consensus** from **calibration-dependent**. Do not invent numbers as measured facts — they are priors to be calibrated. Keep every recommendation expressible with §2; never rely on §3.
