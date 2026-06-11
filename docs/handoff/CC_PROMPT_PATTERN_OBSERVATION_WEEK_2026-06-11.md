# CC Prompt — Pattern Observation Week: verify ALL patterns actually work (2026-06-11)

**Contract:** `docs/handoff/CC_HANDOFF_CONTRACT.md` — anti-tautological tests, NOT-DONE
section, raw evidence per claim (Rule 5). All new behavior flag-gated default-OFF;
log-only flags may be turned ON in SHADOW without a trading-logic gate.

## Context

Michael: "S2 fired only REACTIVE today. Unclear why no trades in the other patterns.
I want a week of observations, analyzing all patterns at end of each day — and to be
SURE every pattern actually works." Inventory + today's per-pattern evidence:
`docs/reports/S2_PATTERNS_INVENTORY_2026-06-11.md`.

## T0 — FIX the silent patterns (Michael directive 06-11 evening — top priority)

Michael: "אני רוצה שנתקן את התבניות שלא ירו והיו צריכות לירות." Diagnose-first, then fix,
flag-gated. Three concrete candidates, in order:
1. **Pkg 5a day_type gap**: add `Trend_Normal` to the chart-pattern day_type list
   (HnS/Double currently muted exactly in the post-IB hour on trend days). One line +
   regression test. Trading-logic → present diff to Michael, then enable in SHADOW.
2. **INITIATIVE dead chain**: it has NEVER detected (verify with DB count). After the
   expansion gate went relative, trace which of b2_test/b3_joining/b4_test is
   unsatisfiable on real bars (use T3 logging on historical bars via replay, or add the
   log first and replay 06-09..06-11). Propose a corrected/relaxed chain, flag-gated
   `S2_INITIATIVE_V2`, with fixture proving it fires on a real historical setup.
3. **Double Bottom EE oversized anchor**: both detections today rejected on
   risk (73pt) / R:R. The `second_bottom_top` anchor resolves too far — verify resolver,
   propose cap (e.g. structural anchor but risk-capped at 25pt → SIZE-DOWN instead of
   reject). Flag-gated.

## T1 — Explain per-pattern silence (code-level, with evidence)

For each of the 8 S2 patterns (REACTIVE, INITIATIVE, HnS top, Inverse HnS,
Double Bottom EE, Double Top AA, Bull Flag, Bear Flag) and the 9 S4 patterns:
1. Query DB: has this pattern EVER produced a signal/trade? (`v9_trades.pattern_id_at_entry`,
   signals tables, since Pkg 5 deploy). Paste counts.
2. Read the detector; list its AND-chain conditions and any gate (day_type list, mode,
   dedup cooldown, FHB).
3. INITIATIVE specifically: `S2_ATR_RELATIVE=true` made the expansion gate relative
   (1.3–2.5× avg) — yet 0 detections persist. Trace b2_test / b3_joining / b4_test on
   today's 75 RTH bars and report which condition kills every candidate.
4. Confirm or refute: Pkg 5a day_type list excludes Trend_Normal (HnS/Double muted
   17:00–18:00 today). Is that intended per D-091 §5+§6? If unclear — STRATEGIC STOP,
   ask Michael (one-line fix if not intended).

## T2 — Fixture proof that every pattern CAN fire (anti-tautological)

Per detector: a regression test feeding a synthetic bar sequence that MUST produce a
detection, plus a control where one condition is broken and detection MUST be None.
RED-on-revert: breaking the detector breaks the test. A pattern with no passing fixture
= classified BROKEN in the weekly health table.

## T3 — Per-bar detection logging (the observation instrument)

Flags `S2_DETECTION_LOG=1` / `S4_DETECTION_LOG=1` (log-only): one line per new bar per
detector with the condition boolean vector + key values (volumes, ranges, day_type, mode,
dedup state). Rate/size guard: single line per bar, no per-push spam (dedup by bar ts).
These are observability-only → may go ON in SHADOW immediately.

## T4 — CVD (cumulative delta) capture per trade (Michael request)

At fire time and on each trade-management event, snapshot cumulative delta from the
Sierra CVD source (`v9_bars_cumulative_delta` / `read_cumulative_delta()`) into the trade
record (metadata/quality: `cvd_at_entry`, `cvd_at_t1`, `cvd_at_exit`, plus per-bar CVD
series reference for the trade window). Source-of-truth Rule 1: if CVD unavailable →
None, never synthesize. Surface in `/api/v9/trades` so the Trades page and EOD report
can show CVD divergence per trade. Flag-gated `TRADE_CVD_SNAPSHOT=1` (observability).

## T5 — EOD per-pattern report (daily, 5 trading days)

Script `scripts/eod_pattern_report.py` (or fold into #16 `eod_shadow_audit.py` — audit
existing first, do NOT duplicate): per pattern — bars scanned, condition-failure
histogram (which condition killed most candidates), detections, pre_fire rejections
(+reasons), trades + P&L + CVD-at-entry, day_type windows. Output:
`docs/reports/EOD_PATTERNS_<date>.md` + one summary line in STATUS_BOARD.
End of week: pattern-health table — VERIFIED-WORKING / TOO-STRICT (calibration) / BROKEN.

## NOT-DONE / Out of scope

- No detector threshold changes this week (observation first; calibration = Michael gate
  after the data is in).
- Standing Decisions stay OFF. No `sc_study`/bridge changes (§7a).

## Report

`docs/reports/PATTERN_OBSERVATION_SETUP_<date>.md` with raw evidence; update boards.
