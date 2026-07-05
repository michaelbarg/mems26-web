# Order-flow exit signals — professional literature review (2026-07-05)

Commissioned by Michael ("לחקור בספרות מקצועית") after our backtest showed the
raw counter-CVD-delta exit was net-negative/noisy. The literature explains WHY,
and prescribes the refinement.

## What the literature says

**1. The pro exit signal is DIVERGENCE, not raw counter-delta.**
Price makes a new favorable extreme but CVD/delta FAILS to confirm (makes a
lower high on a price higher-high, or a higher low on a price lower-low). "Price
is moving, but the underlying participation is not confirming" → exhaustion →
take profit. For our SHORT: price prints a new low but CVD prints a *higher* low
(selling drying up) → exit. This is a RELATIVE measure (price-extreme vs
CVD-extreme) — which is exactly why it filters the noise that sank our raw
2-bar-delta version.

**2. It is quantified for OUR instrument.** Reported backtests on S&P 500
E-mini: persistent CVD divergence preceded ~**65–75%** of major intraday
pullbacks (studies cite ~70% before major ES intraday pullbacks). So divergence
is a real edge on ES specifically — not just crypto folklore.

**3. Absorption = the "at a level" version (Michael's original framing).**
Aggressive volume shows up but price CANNOT make new extremes at a reference
level (high volume + one-sided flow + LOW price impact) → the move is being
absorbed → reversal risk. Absorption is inherently AT A LEVEL.

**4. Exhaustion = fading aggression + stalled price.** "Falling volume,
weakening imbalance, stalled price near the end of a move." This is essentially
our `price_stall` signal (which already backtested +93 pts) plus a volume-fade
confirm.

**5. The universal caveat (every source repeats it):** order-flow divergence is
**CONTEXT, not a standalone trigger**. "Entries still require structure, levels,
or confirmation from price action." "Look for divergence AT a known reference
level, then wait for a reaction (failure to continue + a shift in CVD) before
acting." — i.e. divergence + level + price-reaction, never raw delta alone.

## Why this matches our backtest exactly
Our raw counter-CVD-delta exit: 10 saved but 5 expensive misses → net-negative.
The literature predicts precisely this: raw delta is noisy; the signal only
works as (a) divergence (relative), (b) at a level (absorption), (c) with a
price-reaction/stall confirmation. We were missing all three filters.

## Refined design (to build + re-backtest)
Replace the standalone `counter_flow_wins` trigger with:
- **`cvd_divergence`** — within a window, price makes a new favorable extreme but
  CVD does not (CVD makes the opposite extreme). Normalised, noise-resistant.
- **gate at a level** — only count it when price is at/near an item-22 confluence
  zone (absorption context).
- **confirm with stall** — require `price_stall` (failure to continue) alongside,
  per "wait for the reaction." This also matches our data: stall is the proven
  winner; divergence-at-level becomes its high-quality confirmation.

Net: the exit engine = `price_stall` (exhaustion, proven +93) + `opposite_patterns`
(proven +116) + `cvd_divergence`-at-a-level (absorption, literature ~70% on ES) as
confirmation — not raw counter-delta. Then re-run the backtest to size it.

## Sources
- Bookmap — CVD trading strategy / divergence: https://bookmap.com/blog/how-cumulative-volume-delta-transform-your-trading-strategy
- Bookmap learning center — absorption & exhaustion: https://bookmap.com/learning-center/en/supply-demand-setups/supply-demand-setups/absorption-exhaustion
- CoinGlass — order flow, taker volume & divergence: https://www.coinglass.com/learn/cvd-en
- zitaplus — CVD divergence details & strategies: https://zitaplus.com/blog/analysis/cumulative-volume-delta-divergence-details--strategies/
- Axia Futures — scalping the exhaustion move: https://axiafutures.com/blog/2-ways-to-scalp-the-exhaustion-move/
- GoCharting — delta & cumulative delta divergence strategy: https://gocharting.com/docs/orderflow/delta-and-cumulative-delta-bars
- OrderFlow Labs — footprint / absorption: https://orderflowlabs.com/blogs/theblog/footprint-chart-guide
- Finowings — footprint delta divergence & imbalance: https://www.finowings.com/Trading/order-flow-analysis-footprint-delta
