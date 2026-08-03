# System-7 External Research — Growing a Small Futures Account Safely (2026-08-03)

**Purpose.** Evidence review to inform System-7: a confluence-scoring judgment layer (0–100 from
day-type / leg / location / delta / opening-confidence) that sizes 1–3 MES contracts, blocks weak
setups, and adds size to strong ones. Account ≈ $900–1,200; MES = $5/pt, $1.25/tick; day-trade
margin ≈ $40–50/contract; current stack: fixed 2–3 contracts, per-contract OCO brackets (T1/T2),
MAE-scratch ON, risk halt at −$800/day.

**Method + honesty rule.** Every claim carries a source link. Evidence is graded:
**[A]** peer-reviewed journal · **[B]** working paper / SSRN / practitioner backtest with data ·
**[C]** practitioner lore / vendor content (directional only, do not parameterize from it).
Where the honest answer is "the literature is thin," it says so. Numbers computed by us are
labeled **[our simulation]** with the method stated (Monte Carlo, 20,000 paths × 250 trades,
NumPy, seed 7, run 2026-08-03).

---

## 1. Position sizing for small accounts

### What the evidence says

- **Fixed-fractional risk (risk a fixed % of equity per trade)** is the standard survival
  framework; risk-of-ruin analysis for futures traders was popularized by Balsara's *Money
  Management Strategies for Futures Traders* (1992), whose tables map win rate × payoff × %risk
  to ruin probability ([EarnForex guide to Balsara/RoR](https://www.earnforex.com/guides/risk-of-ruin-in-trading/),
  [CrossTrade RoR overview](https://crosstrade.io/learn/risk-management/risk-of-ruin)) **[B]**.
  Practitioner consensus target: per-trade risk ≤ 1% keeps RoR well under 1% for any positive-expectancy
  system ([BacktestBase RoR](https://www.backtestbase.com/education/risk-of-ruin-calculator-trading)) **[C]**.
- **Kelly:** full-Kelly maximizes log growth but is intolerant of parameter estimation error; Thorp
  himself used **half-Kelly**, and the MacLean–Thorp–Ziemba literature recommends ¼–½ Kelly in
  practice — half-Kelly keeps ~75% of growth at ~half the variance
  ([Thorp/Kelly overview](https://www.quantblueprint.com/glossary/kelly-criterion),
  [fractional-Kelly dangers](https://medium.com/@tmapendembe_28659/the-dangers-of-full-kelly-criterion-why-most-traders-should-use-fractional-kelly-criterion-instead-0338e3bcc705)) **[B]**.
  For plausible MEMS26 edges (p≈0.45–0.55, payoff 1.0–1.5), full Kelly = 8–10% of equity per trade;
  **quarter-Kelly ≈ 2.0–2.5%** — which independently reproduces the 1–2% industry rule **[our computation]**.
- **Volatility-adjusted sizing** has the strongest academic support of the three: Moreira & Muir,
  *Volatility-Managed Portfolios*, **Journal of Finance 2017** — scaling exposure down when recent
  volatility is high raised Sharpe ratios and alphas across the market and major factors, because
  volatility spikes are not compensated by proportionally higher expected returns
  ([paper](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12513),
  [published PDF](https://amoreira2.github.io/alan-moreira.github.io/VolPortfolios_published.pdf),
  [NBER version](https://www.nber.org/papers/w22208)) **[A]**. (Caveat: performance of
  vol-managed portfolios is weaker after costs/out-of-sample in some follow-ups —
  [Cederburg et al., JFE 2020](https://www.sciencedirect.com/science/article/abs/pii/S0304405X2030132X) **[A]** —
  but the *risk-reduction* half of the result is robust: sizing down in high vol reliably cuts drawdowns.)

### Risk-of-ruin at our exact scale [our simulation]

$1,000 start, 250 trades, fixed-dollar risk per trade (= our fixed-contracts mode). "DD50" = hit
−50% drawdown at any point; "dead" = equity ≤ $100 (cannot post margin).

| Risk/trade | = MES config (3-pt stop) | p=0.45, b=1.5 (+0.125R edge) | p=0.40, b=1.5 (zero edge) |
|---|---|---|---|
| $15 (1.5%) | 1 contract | DD50 0.2% · dead 0.0% | DD50 8% · dead 0.2% |
| $30 (3.0%) | 2 contracts | DD50 5.1% · dead 0.5% | DD50 37% · dead 12% |
| $45 (4.5%) | 3 contracts | DD50 13.2% · dead 2.9% | DD50 55% · dead 30% |
| $75 (7.5%) | 3 contracts, 5-pt stop | DD50 29.7% · dead 12.6% | DD50 71% · dead 53% |

Key readings:

1. **The zero-edge column is the honest planning case.** We do not yet have statistical proof of
   live edge (week-1 live ≈ −$183). At 3 contracts × wide stop, a no-edge system has a coin-flip
   chance of losing half the account in ~3 months and a 1-in-3 chance of dying outright. At 1
   contract it survives long enough to collect the data that proves or disproves the edge.
2. **Losing streaks are normal, not anomalies:** at 45% win rate, P(≥8 consecutive losses within
   250 trades) = **61%**; P(≥10) = **24%** [our simulation]. Any throttle/score logic must treat an
   8-loss streak as expected behavior, not evidence of breakage.
3. **Fixed contracts on a shrinking account = rising fractional risk.** True fixed-fractional
   (risk shrinks with equity) had materially lower death rates at the same nominal risk in our
   runs. With contract granularity of $15/step this argues for a **step-down rule**: drop max
   contracts as equity drops (see §6).
4. **Margin ≠ risk.** $40–50 day margin makes 3 MES *possible* on $1k
   ([AMP/typical MES day margins](https://www.quantvps.com/blog/amp-margin-requirements-explained-initial-vs-maintenance),
   [MES specs](https://www.quantvps.com/blog/mes-tick-value)) — that is a broker credit decision,
   not a sizing sanction. Undercapitalization relative to position size is repeatedly named the
   first killer of small futures accounts
   ([NinjaTrader minimum-capital guide](https://ninjatrader.com/futures/blogs/minimum-capital-required-for-futures-trading/),
   [Ironbeam](https://www.ironbeam.com/how-much-money-to-start-trading-futures/)) **[C]**.

### Defensible fraction for us

- Base risk **1.0–1.5% ($10–15 ≈ 1 MES with a 2–3 pt stop)**; peak risk on the very best setups
  **≤ 4.5% ($45 = 3 MES × 3-pt stop)** — and peak only while the honest estimate of edge is positive
  and current. This is quarter-Kelly-of-a-modest-edge territory, consistent with Thorp/MTZ **[B]**
  and with the simulation above.
- **Pitfall specific to us:** a 5-pt structural stop × 3 contracts silently doubles risk to 7.5%.
  System-7 must size off **dollar risk (stop distance × contracts)**, never off contract count alone.

---

## 2. Confluence / score-based sizing — does it work?

### The direct published analog: meta-labeling

System-7 as specified (primary systems fire; a secondary layer scores the context and sizes/blocks)
is exactly **meta-labeling** (López de Prado, *Advances in Financial Machine Learning*, 2018, and
the Journal of Financial Data Science series):

- **Theory & framework:** a secondary layer on top of a base strategy "to help size positions,
  filter out false-positive signals, and improve metrics such as the Sharpe ratio and maximum
  drawdown" — with a controlled experiment decomposing where the gains come from
  ([Joubert, JFDS Summer 2022](https://jfds.pm-research.com/content/early/2022/06/23/jfds.2022.1.098)) **[A-]**
  (peer-reviewed practitioner journal).
- **Does it add efficacy?** Singh & Joubert test it explicitly
  ([PDF](https://hudsonthames.org/wp-content/uploads/2022/04/Does-Meta-Labeling-Add-to-Signal-Efficacy.pdf)) **[B]**.
- **Sizing from the score:** Meyer, Barziy & Joubert compare six sizing algorithms driven by the
  secondary model's probability; **calibrating the probability materially improves fixed sizing
  methods** ([JFDS Spring 2023](https://jfds.pm-research.com/content/early/2023/03/08/jfds.2023.1.119),
  [code + papers index](https://github.com/hudson-and-thames/meta-labeling)) **[A-]**.
- **It is not a silver bullet:** community replications find gains depend on the secondary model
  seeing information the primary doesn't, and vanish when it's fed noise
  ([QuantConnect discussion](https://www.quantconnect.com/forum/discussion/14706/why-meta-labeling-is-not-a-silver-bullet/)) **[C]**.

### Continuous-signal scaling (Carver)

Rob Carver's futures framework (*Systematic Trading*) scales positions by forecast strength and
reports that (i) larger forecasts are historically more profitable than near-zero forecasts and
(ii) continuous scaling trades cheaper and smoother than binary on/off
([framework summary](https://the7circles.uk/systematic-trading-3-frameworks-and-forecasts/),
[position-sizing chapter summary](https://the7circles.uk/systematic-trading-4-volatility-targeting-and-position-sizing/),
[Carver on risk level](https://qoppac.blogspot.com/2020/03/how-much-risk-should-we-take.html)) **[B]**.
Discretionary-manager analytics vendors claim conviction-linked sizing skill exists but is rare
([Novus](https://www.novus.com/blog/alpha-lives-measuring-conviction-hedge-funds),
[Alpha Theory](https://www.alphatheory.com/blog/what-is-position-sizing)) **[C — vendor data, do not parameterize from]**.

**Bottom line:** there IS published support that a well-built score layer improves Sharpe/drawdown
— it is one of the few "judgment layer" ideas with real evidence. The gains are modest and
conditional on the score containing *independent information* and being *calibrated*.

### Scoring-design pitfalls (all with strong evidence)

1. **Backtest overfitting / selection bias.** Trying many score weightings and keeping the best
   in-sample produces inflated, unrepeatable results — Bailey & López de Prado's Deflated Sharpe
   Ratio and Probability of Backtest Overfitting exist precisely for this
   ([DSR, SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551),
   [Pseudo-Mathematics and Financial Charlatanism, Notices of the AMS 2014](https://sdm.lbl.gov/oapapers/ssrn-id2507040-bailey.pdf),
   [DSR overview](https://en.wikipedia.org/wiki/Deflated_Sharpe_ratio)) **[A]**.
   *For us:* score weights must NOT be tuned on our tiny live sample (~tens of trades); tune on
   sim/replay across regimes, freeze, then validate live-forward.
2. **Correlated factors double-count.** Day-type, leg-direction and location are not independent
   signals; summing correlated inputs overweights one underlying fact — "three uncorrelated tools
   that agree tell you more than ten correlated tools that agree"
   ([indicator-combination framework](https://excavo.com/blog/how-to-combine-trading-indicators),
   [GT-Score overfitting paper](https://www.mdpi.com/1911-8074/19/1/60)) **[B]**.
   *For us:* cap the combined weight of the correlated trio (day-type+leg+location), or gate on it
   once and let delta/opening-confidence carry the incremental score.
3. **Uncalibrated scores mislead sizing.** The JFDS sizing paper's clearest result: calibrate the
   probability before mapping to size ([Meyer et al. 2023](https://jfds.pm-research.com/content/early/2023/03/08/jfds.2023.1.119)) **[A-]**.
   *For us:* start with 3 coarse buckets (block / 1 / 2–3 contracts), verify bucket hit-rates
   monotone on replay before trusting finer gradations.
4. **Monotonicity check.** If score 80+ setups don't outperform score 50–79 setups on replay, the
   score is decoration, not information (Carver's forecast-vs-return check applied to us) **[B]**.

---

## 3. Equity-curve throttles (size-down after losses / stop-day rules)

- **Equity-curve trading (switching the system off/on by its own equity curve): evidence is mixed
  and mostly negative on profit.** Kevin Davey's published tests: "always on" beat equity-curve
  filters on profit for most strategies tested, but **drawdowns do shrink** with the filter — a
  cost/benefit, not a free lunch; filters lag and add an optimization surface
  ([Davey, Equity Curve Trading Myths Analyzed](https://kjtradingsystems.com/equity-curve-trading.html),
  [Davey on risk protection](https://kjtradingsystems.medium.com/algorithmic-trading-tip-building-risk-protection-into-your-trading-92089145b5c0)) **[B]**.
- **Daily loss halts have a real behavioral foundation.** Coval & Shumway (Journal of Finance 2005),
  CBOT proprietary traders: traders with morning losses were **~16% more likely to take
  above-average afternoon risk**, and their loss-driven afternoon trades were systematically bad
  (prices reverted against them)
  ([paper](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2005.00723.x),
  [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=269113)) **[A]**. The same
  loss-chasing/house-money pattern shows up in Taiwan futures traders
  ([Pacific-Basin Finance Journal](https://www.sciencedirect.com/science/article/abs/pii/S0927538X13000759)) **[A]**.
  An automated system does not "tilt," but a daily halt still (a) truncates the fat left tail of
  regime-mismatch days, and (b) removes the temptation for *the human operator* to intervene
  mid-drawdown — both failure modes we have logged (07-15, 07-20, 07-23).
- **Industry norm for the halt size:** futures prop firms set the daily loss limit at roughly
  **2–4.5% of nominal account** ($1,000 on $50k, $2,000/$50k Express, etc.)
  ([Topstep daily loss limit](https://help.topstep.com/en/articles/8284207-what-is-the-daily-loss-limit-and-what-happens-if-i-exceed-it),
  [Topstep rules overview](https://propjournal.net/prop-firms/topstep/rules)) **[B]**. These are
  survival parameters chosen by firms whose business depends on trader longevity.
- **Size-down-after-losses (anti-martingale):** no strong academic study either way; practitioner
  material consistently favors reducing after losses over increasing
  ([FXOpen overview](https://fxopen.com/blog/en/martingale-and-anti-martingale-strategies-in-trading/)) **[C]**.
  The math is not controversial: cutting size in drawdown mechanically lowers ruin probability at
  the cost of slower recovery (§1 simulation, fixed-fractional vs fixed-dollar rows).

**Against our current setup:** a **−$800/day halt on a ~$1k account is 70–80% of equity — it is a
catastrophe brake, not a risk control.** Scaled to the prop-firm norm (2–4.5%) it would be $20–45,
which is smaller than one full-size losing trade — unusably tight. The defensible middle for our
scale: **daily halt = 2–3 full-risk losers ($60–100, i.e. 6–10%)**, plus keeping the $800 line only
as a final catastrophic flatten. Evidence basis: prop-norm direction **[B]** + Coval-Shumway
rationale **[A]** + our streak math (an 8-loss streak must survive *across* days, never inside one).

---

## 4. Intraday judgment layers: time-of-day, day-type, pyramiding

### Time-of-day effects in index products (strong evidence)

- **U-shaped volume/volatility** — high at the open, dead at lunch, high at the close — documented
  since Wood, McInish & Ord (1985) and Harris (1986), with the Admati-Pfleiderer (1988) model
  explaining why ([survey/replication](https://www.researchgate.net/publication/46511595_Are_Intraday_Volume_and_Volatility_U-Shaped_After_Accounting_for_Public_Information),
  [Andersen & Bollerslev 1997 on intraday periodicity](https://finance.martinsewell.com/stylized-facts/volatility/AndersenBollerslev1997b.pdf)) **[A]**.
  SPY minute data: volume bottoms ≈ **12:56 PM ET**; the ~11:30–13:30 ET window has compressed
  ranges and is where most intraday strategies underperform
  ([TOS Indicators lunch-hour study](https://tosindicators.com/research/should-you-trade-during-the-lunch-time-hour),
  [Quantified Strategies lunch effect](https://www.quantifiedstrategies.com/lunch-effect-stock-market/)) **[B]**.
- **Market intraday momentum:** the first half-hour return (from prior close) predicts the last
  half-hour return in SPY, R² ≈ 1.6%, stronger on volatile/high-volume days — Gao, Han, Li & Zhou,
  **Journal of Financial Economics 2018**
  ([paper](https://www.sciencedirect.com/science/article/abs/pii/S0304405X18301351),
  [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2440866)) **[A]**. Practical read:
  late-day entries aligned with the opening direction have a documented tailwind; late-day
  counter-open fades fight it.
- **Opening-range breakout:** Zarattini & Aziz and Zarattini, Barbon & Aziz report large,
  cost-inclusive profits for 5-minute ORB (QQQ leveraged; and "Stocks in Play" universe, net
  +1,600%, Sharpe 2.81, alpha 36%/yr 2016–2023)
  ([Can Day Trading Really Be Profitable?, SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4416622),
  [A Profitable Day Trading Strategy…, SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4729284),
  [independent replication](https://www.quantconnect.com/research/18444/opening-range-breakout-for-stocks-in-play/)) —
  **[B: SSRN, author-affiliated with a trading education firm; treat direction (open has exploitable
  directional information) as supported, treat magnitudes as promotional-grade].**
- **Net for the score:** giving time-of-day a real weight is evidence-backed: full size available in
  the opening 90 minutes and the last hour *with* trend alignment; midday (≈18:30–20:30 IL / 11:30–13:30 ET)
  should cap size at 1 contract or block marginal scores outright.

### Trend-day vs balance-day filters (Dalton)

- Frequency: practitioner TPO censuses put **true trend days at ~5–16% of sessions** (varies by
  definition and year; "normal" days ~2%, normal-variation ~40%+)
  ([ToS Indicators trend-day study: ~35–40/yr ≈ 15%](https://tosindicators.com/research/recognize-trend-days-thinkorswim-indicators),
  [Marketcalls TPO day-type stats](https://www.marketcalls.in/market-profile/market-profile-different-types-of-profile-days.html),
  [eminimind Market Profile guide](https://eminimind.com/the-ultimate-guide-to-market-profile/)) —
  **[C: no peer-reviewed census of Dalton day-types exists; frequencies are practitioner counts].**
  Honest statement: the Dalton framework itself is untested academically; what IS tested is the
  underlying regime fact — volatility/trendiness clusters and conditioning on it helps
  (Moreira-Muir **[A]**, §1).
- Implication we can defend: **a day-type-aware size multiplier is a volatility/regime filter in
  Dalton clothing** — supported in direction; the specific day-type boundaries must be validated on
  our own replay data (which the 7-type classifier work has started).

### Pyramiding (adding contracts to a working position)

- The canonical rule set is the Turtles': add ½N increments up to 4 units, trail all stops up with
  each add — mechanically defined, trend-following context
  ([original Turtle rules PDF](https://oxfordstrat.com/coasdfASD32/uploads/2016/01/turtle-rules.pdf)) **[B/C — famous, but 1980s trend context]**.
- There is **no solid academic evidence that intraday pyramiding beats sizing correctly at entry.**
  Carver's framework reaches larger size on stronger signals *at position level*, not by
  path-dependent adds **[B]**. Adding raises average entry price and concentrates risk at the point
  where trend days are oldest; on a $1k account a 3-contract add-on structure concentrates 4.5%+
  risk exactly when the stop is furthest from structure.
- Defensible version for us, if ever: **add only after the existing position's stop is at
  breakeven or better (risk-neutral add), only on trend-day classification, only to the score's
  max-size ceiling.** Until System-7's entry-scoring is validated, the evidence-consistent choice is
  **score-sized entries, no mid-trade adds** — it captures the same "more size on the best days"
  goal without path-dependence.

---

## 5. What kills small accounts fastest — and the guard for each

The day-trading outcome literature is unusually consistent:

- **Most day traders lose; persistence of skill is rare.** Taiwan complete-market data 1992–2006:
  in a typical six-month window >80% of day traders lose money; ~1% (top ~500 of hundreds of
  thousands) earn reliable net profits; aggregate day-trader performance negative in 14 of 15 years
  (Barber, Lee, Liu, Odean — [Do Individual Day Traders Make Money?](https://faculty.haas.berkeley.edu/odean/papers/Day%20Traders/Day%20Trade%20040330.pdf),
  [Do Day Traders Rationally Learn About Their Ability?](https://faculty.haas.berkeley.edu/odean/papers/Day%20Traders/Day%20Trading%20and%20Learning%20110217.pdf),
  [Just How Much Do Individual Investors Lose by Trading?](https://faculty.haas.berkeley.edu/odean/papers%20current%20versions/justhowmuchdoindividualinvestorslose_rfs_2009.pdf)) **[A]**.
  Regulated-broker CFD disclosures echo it: **74–89% of retail leveraged accounts lose**
  ([ESMA product-intervention decision](https://www.esma.europa.eu/press-news/esma-news/esma-agrees-prohibit-binary-options-and-restrict-cfds-protect-retail-investors)) **[A/B]**.

Ranked killers, each mapped to an automated guard:

| # | Killer | Evidence | Automated guard (ours ✅ / gap ❌) |
|---|---|---|---|
| 1 | **Oversizing / leverage** | Capping retail forex leverage at 50:1 improved high-leverage traders' returns by **18 pp/month**, cutting losses ~40% — Heimer & Simsek, JFE 2019 ([NBER w24176](https://www.nber.org/system/files/working_papers/w24176/revisions/w24176.rev0.pdf), [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2150980)) **[A]**; our §1 zero-edge table | ✅ FIXED_CONTRACTS cap + SIZE_CAP_CUT; ❌ cap is in contracts, not $-risk (stop-width blind) — System-7 should enforce a **$-risk ceiling/trade** |
| 2 | **Overtrading + cost drag** | High-turnover investors underperform by ~6–7 pp/yr (Barber & Odean, JF 2000 — [paper](https://faculty.haas.berkeley.edu/odean/papers%20current%20versions/individual_investor_performance_final.pdf)) **[A]**; our math: 4–8 trades/day × 2 MES at $1.24–2.50 RT = **$200–840/month = 20–84%/yr of a $1k account** [our computation] | ✅ opening caps + first-trade-strict; ❌ no global trades/day cap — System-7 score-block IS the guard; add hard cap (≈4–6 entries/day) |
| 3 | **Revenge risk after losses** | +16% above-average afternoon risk after morning losses, and those trades lose (Coval & Shumway, JF 2005 — [paper](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2005.00723.x)) **[A]**; house-money in Taiwan futures ([PBFJ](https://www.sciencedirect.com/science/article/abs/pii/S0927538X13000759)) **[A]** | ❌ current halt (−$800) too far to matter; add **daily soft-halt at 2–3 full losers** + post-2-loss cooldown (no size-3 after 2 consecutive losses) |
| 4 | **Holding/growing losers (disposition)** | All futures floor traders hold losers longer than winners; the least successful hold them longest; most successful cut fastest (Locke & Mann, JFE 2005 — [paper](https://www.sciencedirect.com/science/article/abs/pii/S0304405X0400203X)) **[A]** | ✅ hard bracket stops + MAE-scratch (Sweeney-calibrated) already encode "cut fast"; keep stops non-negotiable in System-7 (score may never widen a stop) |
| 5 | **Undercapitalization** | §1 simulation: at 4.5–7.5% risk/trade a no-edge system dies 30–53% of the time in 250 trades [our simulation]; broker guidance **[C]** ([NinjaTrader](https://ninjatrader.com/futures/blogs/minimum-capital-required-for-futures-trading/)) | ✅ micro contracts; ❌ 3-contract default on $1k violates the math — 3 must be the *rare, high-score exception*, 1 the default |
| 6 | **Overconfidence in a short live sample** | Only top-decile past performers persist; the rest keep trading on noise ([Barber et al. learning paper](https://faculty.haas.berkeley.edu/odean/papers/Day%20Traders/Day%20Trading%20and%20Learning%20110217.pdf)) **[A]**; DSR/overfitting **[A]** (§2) | ❌ institutional guard = written rule: no size/risk increase until N≥100 live trades with positive expectancy net of costs |

---

## 6. Recommended System-7 parameter table

Concrete, source-backed starting values for MES / ~$1k. All are **proposals for Michael's ruling**
— none are self-enabling; trading-risk flags follow the standing RULED_FLAGS process.

| # | Rule | Rationale (source-backed) | Concrete value (MES, ~$1k) |
|---|---|---|---|
| 1 | **Per-trade $-risk ceiling** (stop-distance × contracts, not contract count) | ¼-Kelly of plausible edge ≈ 2–2.5% ([Thorp/MTZ fractional Kelly](https://www.quantblueprint.com/glossary/kelly-criterion)) **[B]**; RoR sim §1 [ours]; leverage-cap benefit ([Heimer-Simsek](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2150980)) **[A]** | Default **$15–20 (≈1.5–2%)**; absolute max **$45 (4.5%)** only at score ≥ 85; reject any entry whose stop×size > $45 regardless of score |
| 2 | **Score → size map (monotone, coarse)** | Meta-labeling sizing: probability-ranked buckets, calibrated, beat fixed size ([Meyer et al. JFDS 2023](https://jfds.pm-research.com/content/early/2023/03/08/jfds.2023.1.119)) **[A-]**; Carver forecast scaling **[B]** | Score <40: **block** · 40–64: **1 contract** · 65–84: **2** · ≥85: **3** (3 stays disabled until bucket monotonicity is shown on replay ≥100 signals/bucket) |
| 3 | **Correlated-factor cap in the score** | Correlated inputs double-count ([GT-Score](https://www.mdpi.com/1911-8074/19/1/60), [indicator-correlation](https://excavo.com/blog/how-to-combine-trading-indicators)) **[B]** | Day-type+leg+location combined ≤ 50 of 100 points; delta + opening-confidence (independent info) carry the rest; no single factor > 30 |
| 4 | **Score validation gate before enabling** | DSR / backtest-overfitting ([Bailey & López de Prado](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551)) **[A]** | Weights frozen from sim/replay only (never live-tuned); acceptance: bucket win-rates monotone + expectancy(≥85) > expectancy(65–84) > expectancy(40–64) on out-of-sample replay days |
| 5 | **Daily soft-halt (new entries)** | Prop-firm norm 2–4.5%/day ([Topstep](https://help.topstep.com/en/articles/8284207-what-is-the-daily-loss-limit-and-what-happens-if-i-exceed-it)) **[B]** scaled to functional minimum = 2–3 full losers; loss-chasing evidence ([Coval-Shumway](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2005.00723.x)) **[A]** | **−$75/day: no new entries** (≈2.5 full losers ≈ 7.5%); existing brackets manage to completion; keep −$800 RISK_HALT as final catastrophic flatten |
| 6 | **Post-loss size throttle (not shutdown)** | Davey: equity-filters cut DD at profit cost ([Equity Curve Trading Myths](https://kjtradingsystems.com/equity-curve-trading.html)) **[B]**; anti-martingale math §1 [ours] | After 2 consecutive losing trades: max size = 1 contract until next winner; never increase size to "recover" (martingale ban, permanent) |
| 7 | **Equity step-down of the size ceiling** | Fixed contracts on shrinking equity = rising %risk (§1 sim) [ours] | Equity < $800: max 2 contracts · < $600: max 1 · < $400: sim-only until refunded |
| 8 | **Time-of-day multiplier** | U-shape vol ([Andersen-Bollerslev](https://finance.martinsewell.com/stylized-facts/volatility/AndersenBollerslev1997b.pdf)) **[A]**; lunch dead-zone ([TOS study](https://tosindicators.com/research/should-you-trade-during-the-lunch-time-hour)) **[B]**; intraday momentum ([Gao et al. JFE 2018](https://www.sciencedirect.com/science/article/abs/pii/S0304405X18301351)) **[A]** | Full score-size in first 90 min + last hour; **11:30–13:30 ET: score −15 and max 1 contract**; last-hour entries against the opening direction: score −10 |
| 9 | **Day-type multiplier** | Regime/vol conditioning works ([Moreira-Muir](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12513)) **[A]**; Dalton day-type frequencies practitioner-only **[C]** — validate on own replay | Trend-day (7-type classifier, with-trend): eligible for 3 · balance/normal-variation: max 2 · non-trend/narrow-IB day: max 1, counter-trend blocked (extends RESPONSIVE_WITH_DAY_TREND_V1) |
| 10 | **Pyramiding** | No academic support intraday; Turtle adds are trend-context with trailed stops ([Turtle rules](https://oxfordstrat.com/coasdfASD32/uploads/2016/01/turtle-rules.pdf)) **[C]** | **OFF.** Size at entry by score only. Future exception (separate ruling): one add, trend-day only, only after original position stop ≥ BE, total ≤ score ceiling |
| 11 | **Trades/day cap** | Turnover kills after costs ([Barber-Odean 2000](https://faculty.haas.berkeley.edu/odean/papers%20current%20versions/individual_investor_performance_final.pdf)) **[A]**; commission drag = 20–84%/yr at our size [ours] | Max **5 score-approved entries/day**; commissions logged as first-class P&L line in the daily report |
| 12 | **Stop integrity** | Best futures traders cut losers fastest ([Locke-Mann](https://www.sciencedirect.com/science/article/abs/pii/S0304405X0400203X)) **[A]** | Score may reduce size or block — it may **never widen a stop or delay an exit**; MAE-scratch stays independent of System-7 |
| 13 | **Edge-proof gate for size growth** | Skill persistence is rare and only visible after large N ([Barber et al.](https://faculty.haas.berkeley.edu/odean/papers/Day%20Traders/Day%20Trading%20and%20Learning%20110217.pdf)) **[A]** | Re-examine caps only at **N≥100 live trades**: if net expectancy >0 after costs, may raise default to 2; if ≤0 at N=100, drop to 1 contract / revert to sim — pre-committed, in writing |

### Honesty summary (what this table stands on)

- **Solid [A]:** vol/regime sizing helps · leverage caps help retail P&L · loss-chasing after
  intraday losses is real and costly · U-shape + lunch dead-zone + first→last half-hour momentum ·
  overtrading/cost drag · disposition effect in futures traders · overfitting dangers.
- **Moderate [B]:** meta-labeling/score-sized positions improve Sharpe/DD (peer-reviewed
  practitioner journal + replications) · fractional-Kelly practice · prop-firm daily-loss norms ·
  equity-curve throttles cut DD at profit cost · ORB direction-of-effect.
- **Thin/lore [C — flagged, not load-bearing]:** Dalton day-type frequencies · pyramiding rules ·
  anti-martingale superiority · vendor conviction analytics · broker minimum-capital guidance.
- The specific cut-points (40/65/85, −$75, 5 trades) are **our translation to scale**, not
  literature constants — they inherit their defensibility from the sim math and the graded sources
  above, and must pass replay acceptance (row 4) before any flag is enabled.

*Simulation code for §1/§5 numbers: inline NumPy Monte Carlo (20k paths × 250 trades, seed 7),
run locally 2026-08-03; re-run command preserved in the git history of this file's commit message
context. No repo code or DB was touched.*
