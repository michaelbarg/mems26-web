# TREND_STEP Fix Proposal — Why It Broke OOS (2026-08-24)

**Ruling:** Michael 23.08 — "מאשר להעביר לצל ולהציע תיקון לאיך היא הופכת טובה יותר"
**Status:** SHADOW from 2026-08-24 (was LIVE since 2026-08-14)

## Evidence for demotion

| Metric | Value |
|--------|-------|
| IS (07-15..08-12, 21 sessions) | **+$4,354** |
| OOS (08-13..08-22) | **-$2,011** |
| Since ignition (books) | **-$198** |
| Removing from slot (X1) | **+$834** |
| X1 + with-trend rule (X4) | **+$1,332** (OOS +$1,011) |

## Hypotheses — why OOS collapsed

### (a) Thresholds calibrated on July only
The impulse (8-45pt), retracement (20-55%), and pause (1-3 bars) were tuned on
July sessions.  **Proposed fix:** re-express as ATR-relative:
- `IMP_MIN` = `k1 * ATR14` (e.g. 0.5x)
- `IMP_MAX` = `k2 * ATR14` (e.g. 3.0x)
- `RETR_MIN/MAX` stay percentage-based (already relative)
- `PAUSE_MAX` → time-based or ATR-scaled

**Measurement needed:** full IS/OOS replay with ATR-relative params.  Expect
the parametric stability (same win-rate across ATR regimes) to improve.

### (b) `STAIR_OR` condition added 18.08
The staircase-OR (`TREND_STEP_STAIR_OR_V1`) was enabled 18.08 — adds 12
candidates that individually averaged +$29.21 with P(negative)=23%.  The OR
opened coverage but may have degraded signal quality in the OOS window.

**Measurement needed:** replay with STAIR_OR=0 vs =1 on full IS/OOS split
separately. If OOS improves without STAIR_OR, the OR itself is the
overfitting vector.

### (c) Delta-based quality filter (absorption in pause)
Michael's primitive: absorption during the pause = a quality signal.  A step
where the pause shows delta absorption (sellers stepping in during an up-step
pause, or vice versa) is higher confidence.

**Measurement needed:** annotate each step with `pause_delta_absorption` (bool)
from `v9_bars_cumulative_delta`, measure win-rate conditional on it.  If the
filter selects a subset with positive OOS, it becomes a quality gate.

### (d) Retest entry instead of breakout
Current entry: at the close of the bar that breaks the impulse extreme (the
step's high/low).  Alternative: enter on the **retest** of that level — the
bar that dips back into the step and then resumes.

**Measurement needed:** tick-level replay with retest-entry logic.  Expect
better MAE (smaller stops) but fewer fills (some steps never retest).

## Proposed research plan

| Variant | Description | Replay scope |
|---------|-------------|--------------|
| V0 | Baseline (current params, STAIR_OR=1) | Full IS/OOS |
| V1 | ATR-relative thresholds | Full IS/OOS |
| V2 | V1 + STAIR_OR=0 | Full IS/OOS |
| V3 | V1 + delta-absorption quality gate | Full IS/OOS |
| V4 | V1 + retest entry | Full IS/OOS (tick-level) |

Each variant: full replay with IS/OOS split, report NET / win% / max-DD / per-session breakdown.

**Recommendation:** Run V0-V3 first (bar-level, fast).  V4 requires tick replay
infrastructure (slower).  Present the table to Michael with one recommendation.

## Current state

- `TREND_STEP_ENTRY_V1=shadow` in .env
- Detector still runs on every 5-min bar, routes through full gate chain
- F4 struct-exempt preserved in shadow (logs, doesn't take slot)
- STAIR_OR and STRUCT_EXEMPT flags remain =1 (detection logic unchanged)
- RULED_FLAGS.yaml updated: expected="shadow", date="2026-08-23"

*Generated 2026-08-24 by cc-macbook*
