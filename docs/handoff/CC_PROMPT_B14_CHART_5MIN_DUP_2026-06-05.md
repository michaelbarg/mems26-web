# CC Prompt — B-14: 5-min chart shows a DUPLICATE/offset price-candle cloud

**Reported by Michael (live, Max zoom).** A second candle "cloud" appears ~60–70
pts BELOW the real price series, with a broken right-axis. **CVD pane is intended
and stays** — this is NOT the CVD; it's a duplicate of the 5-min PRICE candles.
Diagnose-first, paste raw evidence (Rule 5). Frontend-only; do NOT touch backend
bar data — it's already verified clean.

## Verified from Cowork side (do not redo, build on it)
- `/api/v9/chart/bars5min?limit=600` is CLEAN: 428 bars, **0 duplicate
  timestamps**, price range 7541.75–7632.75, no garbage values. The duplication
  is NOT in the endpoint data.
- The chart (`ChartV5b.tsx`) defines exactly **one** price candle series
  (`candleRef`, `addSeries(CandlestickSeries, …, 0)`) + one CVD series
  (`cvdSeriesRef`, paneIndex 1). So a second cloud is the SAME series being fed
  bars at offset values — not a second series.
- The second cloud appears at **Max zoom / after panning left into history**,
  which is exactly the trigger for the history-backfill handler.

## Suspect (localized) — history-backfill render path
`ChartV5b.tsx` `onRangeChange` (≈L753–793): on pan-to-left it fetches
`/api/v9/chart/{ep}?limit=240&before={earliestTs}`, dedups by `b.ts` (string Set,
L770–771), merges, then **rebuilds OHLC for the WHOLE merged list via the
stateful `rawBarToOhlc(b, prevHistRaw)` → `sanitizeOhlc(…, prevRaw)`** (L776–784)
and `candleRef.setData(histData)` (L786). Two plausible mechanisms — confirm WHICH:
1. **ts-format dedup miss:** the `before=` response `ts` string differs in format/
   TZ from the initially-loaded bars (e.g. `+03:00` vs `Z` vs epoch), so the
   `Set(allBarsRef.ts)` dedup (L770) fails → the same instant appears twice at
   adjacent x-slots.
2. **Stateful re-sanitize offset:** `sanitizeOhlc(bar, prevRaw)` (the sticky-H/L /
   span guard — see warns L171/L185) yields DIFFERENT OHLC when re-seeded from
   `prevHistRaw=null` over the merged list vs the original initial-load seeding →
   the backfilled segment renders vertically offset (the ~65pt-lower cloud).

## Diagnose (paste raw)
1. Reproduce: load chart, pan left to trigger backfill (or set Max). Confirm the
   second cloud appears.
2. Log in `onRangeChange`: the first 3 `older` bars' raw `ts` strings vs 3
   `allBarsRef.current` `ts` strings → are the formats identical? (tests #1)
3. Log, for ~5 timestamps present in BOTH the initial load and the backfill, the
   `sanitizeOhlc` output in each path → do the OHLC values match? (tests #2)
4. Report which mechanism (or both) is real, with the raw logged values.

## Fix (smallest correct change, after mechanism confirmed)
- If #1: dedup on a **normalized key** (epoch via `tsToUnix(b.ts)`), not the raw
  ts string — mirror the same normalization used on initial load.
- If #2: don't re-derive already-rendered bars — either seed the sanitizer
  consistently (carry the live `prevRaw` chain) or `setData` once on a single
  canonical OHLC list built the same way in both paths.
- Add a regression: build initial 60 bars + a `before=` chunk that overlaps,
  assert the rendered series has unique epochs AND identical OHLC for shared
  timestamps across both load paths. Prove RED on current code.

## Verify (Rule 5) + NOT-DONE
Paste: the diagnostic logs, the regression RED→GREEN, and a screenshot after fix
at Max zoom showing a single price cloud (CVD pane still present below). NOT-DONE:
state whether other timeframes (3m/15m/30m/1h, which share `onRangeChange`) were
checked for the same bug.

## Board
After GO: STATUS_BOARD (root+fix+evidence, dated) + ROADMAP refresh. Note this
corrects the earlier "B-9 duplicates fixed" claim — B-9 was a backend bars-merge
dedup; B-14 is a frontend history-backfill render bug, a DIFFERENT root.
