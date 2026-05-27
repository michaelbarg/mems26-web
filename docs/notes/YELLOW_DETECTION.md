# YELLOW Detection — Two Algorithms

## Algorithm 1: cci_calc.py — Simple Zero-Crossing

`calc_trend_state()` detects YELLOW when CCI-14 crosses zero:
```
if (cci14 > 0 and cci14_prev < 0) or (cci14 < 0 and cci14_prev > 0):
    return "YELLOW"
```
Single-bar zero-crossing check. Used by DLL parity and study computation.

## Algorithm 2: a1_strategic_gate.py — 5th-Bar Persistence

`A1StrategicGate.evaluate()` detects YELLOW when a sustained trend
(6+ bars on one side) is followed by a sustained opposite run (6+ bars).
This is the "transition" YELLOW — confirms trend change, not transient chop.

YELLOW here triggers `SKIP -- color veto (YELLOW per P-W5)`.

## Defense-in-Depth Rationale

Both algorithms coexist intentionally:
- **cci_calc YELLOW** catches instantaneous zero crosses (fast, DLL-parity).
- **a1_strategic_gate YELLOW** catches sustained trend transitions (slow, strategic).
- The strategic gate is the authoritative entry filter. The cci_calc version
  is for study output and display.

## Phase B Reconciliation Plan

- Keep both algorithms during SHADOW phase.
- Log any disagreement (cci_calc says YELLOW but A1 says GRAY, or vice versa).
- After 30+ session days of data, reconcile into a single YELLOW definition
  if drift is below 5%. Otherwise, formalize the two-tier model in the spec.
