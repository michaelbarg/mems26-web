# CC fix — intra-bar IB-break day-type reclassification (Michael 2026-07-06)

Owner: Claude Code (classifier change → build + SHADOW-validate + flag-gate; NOT
mid-live-session). Michael's live-session directive, recorded verbatim:

> "It shouldn't wait for the end of the candle — it's enough that price exited [the
> IB] to reclassify what type of day it is."

## The finding (live 2026-07-06, verified with data)
Day opened OPEN_REJECTION_REVERSE, dipped to 7552.25, reversed and ground UP to
test the IB high (IB 16:30-17:30 = high 7580.75 / low 7552.25). By 17:30 the last
5 bars were a clean uptrend — a Variation/Trend-up character. But `day_type` stayed
**Normal** (the 30-min staged classification), so S2 INITIATIVE_LONG fires kept
getting **Auth Table SKIP** (Normal-day, low tier) — i.e. the system would MISS the
trend-up trades if the day is really extending.

Root: the day-type reclassification is **bar-close gated**. Extension is counted on
bar data (`backend/v9/systems/day_type/detector.py:375` `detect_intraday_behavior`,
`extensions_up`/`extensions_down` = counts above IB high / below IB low), and the
classifier runs on `_day_type_on_bar` (bar events). So an IB breakout mid-bar is not
recognized until that 5-min bar CLOSES — a up-to-5-minute lag on the single most
important intraday day-type signal (range extension out of the IB).

## The fix
Reclassify the **moment price crosses the IB boundary**, intra-bar, independent of
the 5-min bar close:
- Feed the live tick (`live_price.json`, already polled) into an IB-break check:
  `price > ib_high` (up-extension) or `price < ib_low` (down-extension), once the IB
  is locked (60 min).
- On the crossing, trigger the same reclassification path the bar-close uses (recompute
  `extensions_up`/`extensions_down` with the live extreme, re-run `detect_intraday_behavior`
  → Variation/Trend). Do NOT wait for `is_new_bar`.
- Debounce so a one-tick poke that immediately reverts doesn't flip the type (e.g.
  require price to hold beyond IB ± a small buffer for N seconds / a tick count) — but
  the DETECTION fires immediately; the confirmation gate is separate from the lag fix.

## Phase 0 — audit first (paste raw, Rule 2)
Confirm the exact trigger: where `detect_intraday_behavior` is called, how
`extensions_up/down` are populated, and that the only entry is bar-close
(`_day_type_on_bar`). Identify the live-price ingress (the same one `useLivePricePoll` /
live_price.json feeds) to hook the intra-bar check.

## Guardrails
- Flag-gate (default OFF) — this changes when day_type upgrades → changes which fires
  are authorized → trading-risk surface. Michael sign-off before live-ON.
- No synthesis: use the real live price + real IB levels; if IB not yet locked (<60min),
  no extension reclass (staged classification still holds). Honor the staged rules
  (opening@15 / day_type@30 / IB-lock@60) — this fix only removes the bar-close LAG on
  the post-IB extension, it does not change the rules.
- SHADOW-validate: replay a known extension day, prove the reclass fires at the crossing
  tick, not the bar close; anti-tautological + fail-on-old (old code = reclass only on
  bar close).

## Verification to return (Rule 5)
git + pytest (incl. fail-on-old intra-bar test) + a SHADOW replay showing the
reclass timestamp == the crossing tick (< the next bar close) + NOT-DONE section.
