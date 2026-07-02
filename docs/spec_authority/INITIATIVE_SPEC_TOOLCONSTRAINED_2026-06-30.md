# INITIATIVE Pattern — Tool-Constrained Construction & Management Spec

**Type:** Theory/design synthesis (no system/data access). Pairs with the CC research handoff (`CC_INITIATIVE_RESEARCH_2026-06-30.md`) that will backtest + calibrate on live data.
**Date:** 2026-06-30 · **Prepared for:** Michael (MEMS26 / S2). Produced from `RESEARCH_INITIATIVE_TOOLCONSTRAINED_2026-06-30.md`.
**Hard constraint:** every rule below is expressed using ONLY the §2 tools the system has. Where best practice needs a §3 capability we lack (footprint / stacked imbalances / per-cell absorption), it is re-expressed as a proxy from §2 or dropped — see §B.
**All numbers are PRIORS to calibrate, not measured facts.** Tags: **[C]** = broad practitioner/AMT consensus · **[K]** = calibration-dependent (CC settles on live data).

---

## A · Definition (confirmed against AMT/Dalton)
Initiative = **location + acceptance, not the action.** Aggressive buying *accepted above* established value (prior-day VAH / IB-high / balance-high) that **builds new value upward** is initiative; the identical buy *below* VAL targeting a reversion to POC is responsive/reactive. Initiative is the engine of trend days, conducted by other-time-frame (OTF) participants; per Dalton (*Mind Over Markets*), a **migrating POC** is the signature of directional value discovery. **The crux is acceptance vs rejection:** a breakout is initiative only if price is *accepted* beyond the level (value builds there); a single-print wick that snaps back within 1–2 bars is *rejection* → a failed auction, which is itself a reactive setup the other way (§B5). Because trend days are rare (**~9.5% [C]**), initiative must be gated by a **strict conjunction — require ALL mandatory conditions, not any.**

Two distinct geometries live under "INITIATIVE." Treat them as named variants (and let CC measure them separately — they were mixed in the live sample):
- **IB-1 · Breakout-Acceptance** — price *closes* above the reference and accepts beyond it. Classic initiative.
- **IB-2 · Edge-Retest Continuation** — inside an already-established up-auction (OTF higher-lows, value migrating up), a *shallow pullback to the developing VAH / value edge holds* (higher-low) and resumes. Functionally an entry *with* the initiative; this is the geometry that produced the in-house winner (entry at the value edge with rising CVD).

Everything below is written for **initiative-long**; **initiative-short is the exact mirror** (accept *below* VAL/IB-low, CVD to new session *low* with downside acceleration, value migrating down) — see §F.

---

## B · The tool-constraint translation (§3 we lack → §2 proxy)  *(core of this brief)*
We have **one CVD line** (per-bar delta + running cumulative) + volume + developing value area — **no footprint, no stacked-imbalance (3:1) detection, no per-cell absorption.** The footprint-dependent best-practice signals must be rebuilt from what we have:

| Theory needs (we LACK) | Proxy from §2 (what we BUILD instead) |
|---|---|
| Stacked buy imbalances (≥3 levels, 3:1) on the breakout | **CVD makes a new session high on the trigger bar** **[C]** + **per-bar delta of the trigger bar in the top decile of the session's per-bar delta** **[K]** + **volume ≥ `vol_mult` × recent-N-bar average** **[K]**. (Aggression = strong positive delta carrying price, not cell-by-cell.) |
| Absorption-by-cell (passive limits soak aggression) | **"Effort without result" on the single line:** large \|per-bar delta\| but **price fails to extend** — trigger-bar range ≤ `absorb_range_atr` × ATR **AND/OR** developing VA does **not** expand upward. For initiative this is a **VETO** (big buy delta + no price progress = sellers absorbing = reject). **[K]** |
| "No responsive selling stepping in" | **No bearish CVD divergence at the new highs:** price new high **must** be matched by CVD new high; price new high while CVD makes a *lower* high → divergence → **VETO**. **[C]** |
| Iceberg/defended level read | **Value-building proxy:** developing POC/VAH migrating up to *include* the new prices over ≥ `accept_N` bars (acceptance), vs price passing through quickly (rejection). **[C]** |

Net: aggression and absorption are detectable from the *single CVD line + volume + value-migration* — at coarser resolution than footprint, so we compensate with the **acceptance** requirement (time/value beyond the level), which footprint users sometimes skip. **The acceptance rule is what replaces the lost per-cell precision.**

---

## C · Construction — entry state machine (§2 inputs only)
**STATE 0 — Context (session start).** Load prior-day VAH/VAL/POC, PDH/PDL, overnight H/L. *(Flag: we lean on prior-day VAH and PDH heavily — confirm these are populated.)*

**STATE 1 — IB build (first 60 min).** Record IB high/low/width; capture opening-type (Open-Drive / Open-Test-Drive / Open-Rejection-Reverse / Open-Auction). Day-type classifier running (locks ~60 min after open).

**STATE 2 — Regime gate (A6 · the minimal mandatory set).** Arm initiative-long ONLY if **all** hold:
1. **Day-type ∈ {Trend_Normal, Trend_DD, Variation}** — confidence ≥ `dt_conf` once locked; **pre-lock**, substitute **opening-type ∈ {Open-Drive, Open-Test-Drive} in the up direction** as the regime proxy. **[C]**
2. **LSMA slope up and price above LSMA** (with-trend). **[C]**
3. **Value not migrating down** (developing POC flat-or-up). **[C]**
   → *Confirming (not mandatory):* Woodies CCI with-trend; OTF higher-lows. Keep these as score-boosters, not gates, to avoid over-filtering the rare signal.

**STATE 3 — Reference selection (A2).** Pick the upside line:
- Opened **above** prior value (Open-Drive/Test-Drive out) → reference = **prior-day VAH** (then PDH/ONH as next).
- Opened **inside** value, breakout developing intraday → reference = **IB-high** (or developing VAH if IB already broken and value rebuilt).
- Decision rule **[C]**; exact precedence **[K]**.

**STATE 4 — Trigger (the two variants).**
- **IB-1:** a 5-min bar **closes above** the reference.
- **IB-2:** in an established up-auction, price **pulls back to the developing VAH / value edge** and the pullback bar makes a **higher-low at/above the edge** (no acceptance below it).

**STATE 5 — Acceptance (A1 · the key tunable).**
- **IB-1:** require **`accept_N` consecutive 5-min closes beyond the reference** (prior **2** [K]; trade-off curve: 2 = fast/more signals/more false breaks; ~6 ≈ the 30-min "80% Rule" [C] = slower/cleaner) **AND** developing VA **expands upward** to include ≥ `va_expand_ticks` of new price **[K]** **AND** no snap-back inside within 1–2 bars.
- **IB-2:** require the retest to **hold** — pullback closes back up off the edge, no close accepted below the edge.

**STATE 6 — CVD + LSMA confirmation (A3).** All mandatory:
- CVD **new session high** on the trigger/breakout bar. **[C]**
- **Acceleration:** trigger-bar per-bar delta jump (top-decile of session) **or** CVD slope jump vs the prior `slope_lookback` bars. **[K]**
- **No bearish divergence** (price new high ⇒ CVD new high). **VETO if violated.** **[C]**
- **No absorption** (effort-without-result veto, §B). **[K]**
- **LSMA** slope up, price above. **[C]**
- **Volume** ≥ `vol_mult` × recent-N-bar average. **[K]**

**STATE 7 — Distance & size gate (A5 · anti-chase).**
- **`|entry − broken reference| ≤ max_dist`**, prior = **min(1.0 × IB-width, 1.0 × ATR)** **[K]**. Beyond this, the move is chasing the extreme, not initiating from value → **reject** (this is the lever that would have blocked the in-house ~80-pt-below-value loser; note that loser was a *short* far below VAL — same principle mirrored).
- **IB-width-relative size** (wider IB / higher ATR → fewer/smaller, since stops widen). **[K]**

**STATE 8 — Entry (B1) + dedup.**
- **Conservative (default):** retest-and-hold of the broken level (it should now act as support) — higher win-rate, better fill. **[C]**
- **Aggressive:** acceptance-bar close — earlier, lower win-rate.
- **Single fire per setup** — cooldown `dedup_bars` **[K]** OR until structure changes (new reference / new consolidation). *Dedup is the single biggest P&L lever from the live look — enforce it here, not just downstream.*

**STATE 9 — Management.** → §D.

**STATE 10 — Failed-initiative → reactive flip (B5).** If, after the trigger, price **closes back inside the reference within 1–2 bars** AND **CVD diverges/stalls** (no new high, or lower high) → cancel/stop the initiative; **optionally arm a reactive short toward POC** (hand to the REACTIVE engine, not S2). **[C]**

---

## D · Management — stop / target / trail / exit
### D1 · Stop (B2) — resolving the "tight wins vs give-it-room" tension
**Anchor:** broken-reference − offset, or breakout-bar low, or retest low. **[C on anchor]**
**Why a tight initial stop can outperform on *accepted* breakouts (conceptual resolution):** on a true accepted breakout the broken level flips to support and one-time-framing means price does **not** revisit the entry — so the initial stop's only job is to detect **invalidation** (acceptance was false), which happens **fast and close** (price back inside old value = thesis already dead). A wider stop adds risk **without adding information**: once price is back inside, holding only loses more. Therefore **tight by default**, AND **the runner R comes from the *trail*, not the initial stop** (the in-house +4.89R came from trailing ~11.75 pt off ~2.4 pt risk — the trail captured the edge, not a wide stop).
**When a wider structural stop IS justified:** stop width should scale with the **noise at the level**, not a fixed "room" rule. In high-ATR / wide-IB regimes, normal noise around the broken level is larger, so floor the stop by volatility:
> **`initial_stop_pts = clamp( max( structural_offset, k_atr × ATR ), [stop_min, stop_max] )`**, with `stop_min`/`stop_max` as a hard max-risk cap. Tight in normal vol; ATR-floored so it isn't absurdly tight in high vol. `k_atr`, caps = **[K]**. *(This is the explicit hypothesis for CC: tight-default + ATR-floor, vs the prior "tight wins" measured in a different, all-patterns context.)*

### D2 · Targets (B3) — mapping to the structural-targets engine across 3 contracts
Initiative runs further than reactive → favor IB-multiples with a structural overlay:
| Contract | Target | Prior |
|---|---|---|
| **C1** | First structural level above / **1× IB extension** | de-risk; bank the high-probability leg **[C]** |
| **C2** | **1.5–2× IB** or next reference (POC-above / VA-edge / PDH) | primary structural target **[C]** |
| **C3** | **2–3× IB** / measured move / **naked POC** | runner, trailed **[C]**; exact multiple **[K]** |
Pick IB-multiple vs structural per day-type: **Trend_Normal/DD → lean IB-multiples** (let it run); **Variation → lean structural** (cap nearer the realistic extension). **[C]**

### D3 · Trail / exit (B4)
- **Trail:** structural re-anchor — move the runner stop under **each new consolidation/step after an advance** (preferred, matches the engine), with OTF-higher-low as the step definition. **[C]**
- **Explicit exit-all triggers (any):** close back **inside** the reference / old value · close **below LSMA** · **CVD divergence** at new highs (price HH, CVD LH) · **OTF break** (bar low < prior bar low) on the runner. **[C]**

---

## E · Tunable-parameter table (priors + tags)
| Parameter | Prior | Tag | Note |
|---|---|---|---|
| `accept_N` (closes beyond ref, IB-1) | 2 | **[K]** | 2 = fast; ~6 = 30-min "80% Rule". **The single most important tunable.** |
| `va_expand_ticks` (developing-VA upward expansion) | small, non-zero | **[K]** | Acceptance must build value, not just close beyond |
| require value-building | true | **[C]** | |
| reference precedence (PDVAH / IB-high / dev-VAH) | by opening+day-type | **[C]** logic / **[K]** order | §C STATE 3 |
| `cvd_new_session_high` | true | **[C]** | Mandatory |
| `cvd_accel` (top-decile per-bar delta / slope jump) | top-decile | **[K]** | Aggression proxy (no footprint) |
| `cvd_divergence_veto` | true | **[C]** | Price HH ⇒ CVD HH, else block |
| `absorb_range_atr` (effort-without-result veto) | ~0.5 | **[K]** | Big delta + small range/no-expansion = absorb |
| `lsma_slope_up` & price>LSMA | true | **[C]** | |
| `vol_mult` (breakout vol vs recent avg) | 1.5–2.0× | **[K]** | ORB literature prior |
| `max_dist` (entry vs broken ref) | min(1×IB, 1×ATR) | **[K]** | Anti-chase; **derive from theory, don't fit to extremes** |
| IB-width-relative sizing | on | **[K]** | |
| entry mode | retest-hold (default) / close | **[C]** | |
| `dedup_bars` (single fire) | until structure changes | **[K]** | Biggest live P&L lever |
| stop anchor | broken-ref / breakout-bar low | **[C]** | |
| `k_atr`, `stop_min`/`stop_max` | tight + ATR floor + max-risk cap | **[K]** | §D1 resolution |
| targets C1/C2/C3 | 1× / 1.5–2× / 2–3× IB (+structural) | **[C]** map / **[K]** exact | |
| trail | consolidation re-anchor (OTF step) | **[C]** | |
| `dt_conf` (day-type confidence gate) | TBD | **[K]** | |

---

## F · Worked example (plausible MES, ~7,400 regime — priors, not measured)
**IB-1 Breakout-Acceptance LONG — FIRES.**
- *Context:* Variation day; opening Open-Test-Drive above prior value. Prior VAH **7489.5**, POC **7483**, VAL **7478**, PDH **7492**. IB **7480–7494** → width **14**. LSMA up, price above; value migrating up.
- *Reference:* IB-high **7494** (above prior VAH).
- *Trigger:* 11:05 bar **closes 7497** (> 7494).
- *Acceptance:* 11:10 closes **7500**, 11:15 closes **7502** → 2 closes beyond; developing VAH migrates **7494 → 7499**; no snap-back. ✔
- *CVD/LSMA:* CVD prints a **new session high** on 11:05; trigger-bar per-bar delta ≈ **+3.1k** vs prior bars ≈ +0.8k (top-decile accel); **no bearish divergence**; price extends with the delta (**no absorption**); volume ≈ **1.9×** the prior-10-bar avg; LSMA slope up, price above. ✔
- *Distance gate:* retest entry ~**7495** vs broken **7494** → **~1.5 pt ≤ max_dist (14)**. ✔
- *Entry:* retest-and-hold **7495** (or aggressive 7502 close). Single fire.
- *Stop:* below broken level / breakout-bar low → **7488** (just inside old IB) → risk **7 pt = $35/contract** (×$5).
- *Targets (IB 14 from 7494):* **C1 = 1× = 7508** (+13 / $65) · **C2 = 1.5× = 7515** (+20 / $100) · **C3 = 2–3× = 7522→7536** / PDH-extension / naked POC. Trail C3 under each new consolidation.
- *R:R:* C1 ≈ 13:7 ≈ **1.9:1**; blended scale-out well >3:1 — the asymmetry that justifies trading the rare signal.

**Failure / rejection variant — NO entry.**
- 11:05 **wicks to 7498 but CLOSES back at 7493** (inside IB) on flat/declining CVD: **no new session high**, per-bar delta only **+0.4k**, and price made the high while **CVD made a lower high (divergence)**. → rejection / failed auction → **block initiative.** Per §B5, optionally arm a **reactive short toward POC 7483**.

**Initiative-SHORT (symmetry):** mirror — reference = prior-day VAL / IB-low; trigger = close *below*; acceptance = `accept_N` closes below + developing VA expanding *down*; CVD = **new session low** + downside accel, **no bullish divergence**, **no absorption** (big sell delta but price won't extend = buyers absorbing = veto); stop just *inside* the broken level (above); targets = IB-extensions downward / VAL-below / PDL / naked POC.

---

## G · Open calibration questions for CC (settle on live data)
1. **`accept_N`:** 2 vs 3–6 closes — where does the false-breakout rate stop falling faster than signal count? (The dominant tunable.)
2. **Tight-stop tension:** does the prior "tight wins +11% (n=5188, all-patterns)" hold on the **trend-only + acceptance** sample, measured by **expectancy AND max-adverse-excursion**? Find `k_atr` / caps for the ATR-floor.
3. **Absorption veto marginal lift:** measure it **separately from dedup and from the distance cap** (all three "fix" the same loser class → n=1 can't attribute). Does it kill the failed-breakout class without killing winners?
4. **`max_dist`:** confirm the anti-chase cap (IB-multiple vs ATR) — is there a distance beyond which initiative is −EV?
5. **IB-1 vs IB-2 split:** do **breakout-acceptance** and **edge-retest continuation** have different expectancy? (The in-house winner was IB-2; the engine currently mixes them.) Calibrate geometry per variant.
6. **`cvd_accel` & `va_expand_ticks` thresholds**, `vol_mult`, `dedup_bars`, `dt_conf` — fit each.
7. **Targets per contract & trail step definition:** which consolidation/step captures the most runner R (the +4.89R came from the trail)?
8. **Reference precedence** (PDVAH vs IB-high vs dev-VAH) by opening/day-type — which line gives the cleanest acceptance?

*Keep-regardless (theory, don't fit to noise): the location+acceptance definition, the divergence/absorption vetoes, the distance cap's existence, the strict-conjunction gating. Fit-and-validate (needs ≥N independent setups): the exact geometry combo, all point distances, all thresholds above.*
