# cc-macbook — URGENT (live day): stops must sit at the STRUCTURAL EDGE, all patterns

**Michael 2026-07-20, live, losing on mislocated stops. "keep live, fix fast."** Two S2 shorts
failed because the stop was placed INSIDE the structure, not beyond its edge. `git pull` first.
No op=EXIT. Flag-gate the change; unit-test it deterministically (sim not available on the live
trading machine mid-session). cowork verifies. This is Task #7 (+ Task #6 reconciliation in parallel).

## The proof (use as the regression fixture)
Trade #420, S2 REACTIVE_SHORT: entry **7508.75**, stop **7514.0**, exit 7514.25, STOP_HIT in **8 seconds**.
5-min bars around entry (v9_bars_5min_woodies, 2026-07-20):
```
17:00 H=7527.5   17:05 H=7525.0   17:10 H=7517.75   17:15 H=7518.75
17:20 H=7516.25  17:25 H=7521.25  (entry bar)       17:30 H=7523.0
```
Structure edge (swing high) = **7521.25–7527.5**. Stop 7514.0 was **7–13pt INSIDE** the structure —
below the swing high, even below the entry bar's own high (7521.25) → hit instantly.
Root: S2 stop = entry + 1.75×ATR5m floor (5.25pt), an ATR distance — NOT the structural swing high.
`config/stop_anchors.yaml` declares `structural_stop_always_wins: true` but S2's adaptive_stop
does NOT enforce it. (The 8pt floor band-aid was tried + reverted — 8pt is still inside 13pt.)

## The fix (all patterns, not just S2)
1. The protective stop MUST sit **beyond the structural edge**: SHORT → above the swing-high /
   rejected-zone high + **6T** buffer; LONG → below the swing-low − 6T. Never inside the structure.
2. **Structural anchor WINS over the ATR floor when structure is WIDER** than the floor. The ATR
   floor may only *raise* a too-tight structural stop; it must NEVER place the stop inside a wider
   structure. (Today the floor was the binding value and sat inside the structure — wrong.)
3. Identify the correct structural extreme per S2 pattern (REACTIVE support/resistance zone,
   OFA/Flag breakout-bar, Double_BT/HnS structure) and per S4 (ZLR/TT/GB100). Use the same
   swing/zone the pattern is reacting to. Cross-check `stop_resolver.py` (rung ladder + 6T already there)
   vs `five_min/adaptive_stop.py` (the S2 path that misfired) — unify so S2 uses the structural rung.
4. Guard R:R: a correctly-wider structural stop changes R:R — verify it doesn't silently trip
   RR_ENTRY_GATE into blocking everything (the ZLR "T1 below R:R" block Michael saw). Report the
   interaction; don't auto-loosen RR without Michael.

## Deterministic test (no live sim needed)
`tests/v9/regression/test_stop_at_structural_edge.py`: feed the #420 bars above as a REACTIVE_SHORT
at entry 7508.75 → assert the resolved stop is **> 7521.25 + 6T** (above the swing high, beyond
structure), NOT 7514.0. Mirror a LONG case. Flag-OFF byte-identical.

## Order
Build flag-gated (default OFF) + deterministic test → cowork verifies raw output → Michael rules
enable. Task #6 (Sierra fill reconciliation, trade_fills.json empty) runs in parallel — until it
works, validate stops against the bar math (as above), not against the unverified recorded P&L.
