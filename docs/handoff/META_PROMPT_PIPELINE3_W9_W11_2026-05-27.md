# META-PROMPT · Pipeline 3 · W-9 + W-11 · S4 Woodies CCI

**From:** Cursor (G3 reviewer)
**To:** Claude Desktop → Claude Code
**Date:** 2026-05-27 IL
**Branch:** `stabilize/mems26-local-truth-2026-05-16`
**Authority:** Pipeline 2 Cursor Final Report §13 · D-092 · INTAKE v2

---

## CONTEXT FOR CLAUDE DESKTOP

Pipeline 2 closed 9/10 packages. Two packages were legitimately deferred to Pipeline 3:

- **W-9 · LiranExitLadderRule** — blocked on missing prerequisites (S2 Pkg 6 `RiskRule` class + Liran 8-rung doctrine file). Before executing, CC must verify these now exist.
- **W-11 · Partial Exit at T1** — Registry #10. Currently all 3 contracts exit together. Spec requires partial exit (1/3 or 1/2 at T1, remainder trails). DEMO blocker.

Your job: write **two separate CC mega-prompts** (one per package), each following the §5 Memorial Day lessons and pre-LIVE protocol. Then produce the **Michael checklist** and **Cursor G3 review criteria**.

---

## SPEC AUTHORITY (read before writing prompts)

1. `docs/MEMS26_WOODIES_DECISION_TREE_V1.md` — DTV1 · Liran exit ladder §B13 + §B10/11 trail column
2. `docs/decisions/D-092_S4_WOODIES_UPDATE.md` — Sheet A trail column row-by-row
3. `docs/handoff/MEGA_PROMPT_PW_DECISIONS_INTAKE.md` — P-W7 lock (6 touch-points: A2/A4/A5/B4/B5/B9)
4. `MEMS26_SYSTEMS_DECISIONS_REGISTRY_2026-05-23.md` — §7.3 rows #9 (trailing) + #10 (partial exit)
5. `backend/v9/systems/woodies/woodies_system.py` — current trade emit path (lines 257–395)
6. `backend/v9/systems/woodies/stages/b13_trail_check.py` — current EMA-169 trail (production default)
7. `backend/v9/systems/woodies/schemas.py` — PatternResult + trade schemas
8. `backend/v9/systems/woodies/atr_stop.py` — StopResult (used by W-9 ladder)
9. `backend/v9/systems/woodies/time_stop.py` — W-10 enforcer (already wired · W-9 must not conflict)

---

## PACKAGE W-9 · LiranExitLadderRule

### Pre-execution gates (CC must STOP if any fail)

```
Step 0a: rg "class RiskRule" backend/v9/systems/ --type py
         → must return ≥1 match (S2 Pkg 6 prerequisite)

Step 0b: ls docs/spec_authority/ | grep -i liran
         → must find LIRAN_EXIT_LADDER_DOCTRINE.md or equivalent

Step 0c: Read b13_trail_check.py fully
         → understand current EMA-169 production trail before touching it
```

**If Step 0a or 0b fails → CC must STOP and report "prerequisites still missing."
Do NOT implement a stub or workaround. This package cannot proceed without the real prereqs.**

### What W-9 must implement (if gates pass)

Per DTV1 §B13 + Sheet A trail column:

```
8-rung exit ladder:
  Rung 1: entry → initial stop (atr_stop from W-1)
  Rung 2: price moves 0.5R → trail to entry (BE)
  Rung 3: price moves 1.0R → trail to +0.5R
  Rung 4: REV patterns → BE on rung 4 (price 1.5R+)
  Rung 5: CONT patterns → BE on rung 5 (price 2.0R+)
  Rungs 6-8: continue trailing per rung table in doctrine

Key rules:
- EMA-169 trail (b13_trail_check.py) is the fallback when no rung matches
- Ladder is OPT-IN per trade (flag in fire_setup dict)
- Must NOT remove EMA-169 trail — ladder is an enhancement, not a replacement
- RiskRule class must be subclassed or used, not reimplemented
```

### Deliverables

```
backend/v9/systems/woodies/liran_exit_ladder.py      (~200 LOC · LiranExitLadderRule class)
backend/v9/systems/woodies/config/exit_ladder_config.yaml
tests/v9/systems/test_liran_exit_ladder.py            (≥20 tests)
docs/notes/LIRAN_EXIT_LADDER_INTEGRATION.md
```

### §5 Memorial Day self-report requirements

CC must include in self-report:
```
§0 Pre-checks — paste rg output for Step 0a/0b verbatim
§1 Read b13_trail_check.py — quote the evaluate() signature with line numbers
§2 Read RiskRule class — quote class definition + abstract methods
§3 Implementation — full diff summary
§4 Live Python repro — use REAL LiranExitLadderRule class (not Fake)
   Sub-cases: (a) rung 2 triggers BE · (b) rung 5 fires on ZLR CONT · (c) ladder disabled → EMA-169 unchanged
§5 Tests — pytest output verbatim
§6 Forbidden surface — confirm b13_trail_check.py EMA-169 logic UNCHANGED (rg output)
```

---

## PACKAGE W-11 · Partial Exit at T1

### What W-11 must implement

Per Registry #10 + DTV1 §B10:

```
Current behavior: all contracts (C1+C2+C3) remain open after T1 hit
Required behavior: exit 1/3 of position at T1, trail remainder

Sizing matrix (from calculate_size() in woodies_system.py):
  full  = 3 contracts → exit 1 at T1, trail 2
  half  = 2 contracts → exit 1 at T1, trail 1
  single (if ever) = 1 contract → no partial, exit at T1 or T2

Partial exit trigger:
  - On T1 hit: close 1 contract, move stop to BE on remaining
  - T2: close next contract, move stop to T1 on remaining
  - T3 / time_stop / trail: close final contract
```

### Pre-checks (CC must STOP if any fail)

```
Step 0: rg "t1_hit_ts|t1_hit|T1.*hit" backend/v9/services/ backend/v9/systems/woodies/ --type py
        → identify WHERE t1-hit is currently detected and recorded

Step 1: rg "close_trade\|partial.*exit\|exit.*partial" backend/v9/services/ --type py
        → find if TradeManager already has partial close capability

Step 2: Read woodies_system.py lines 257-395 (trade emit + routing)
        → understand full fire_setup dict before touching it
```

### Deliverables

```
backend/v9/systems/woodies/partial_exit.py           (~150 LOC · PartialExitManager class)
backend/v9/systems/woodies/woodies_system.py          (wired: on_t1_hit callback)
tests/v9/systems/test_partial_exit.py                 (≥15 tests)
```

### §5 Memorial Day self-report requirements

```
§0 Pre-checks — paste output of Steps 0/1/2 verbatim
§1 TradeManager partial close — quote existing capability or "not present · implementing"
§2 Implementation — full diff summary
§3 Live Python repro:
   (a) full sizing: T1 hit → 1 contract closed, 2 remain with BE stop
   (b) half sizing: T1 hit → 1 contract closed, 1 remains with BE stop
   (c) T2 hit → next contract closed, stop moves to T1
§4 Tests — pytest verbatim
§5 Forbidden surface — confirm atr_stop.py, pattern_dispatcher.py, time_stop.py UNCHANGED
```

---

## FORBIDDEN SURFACE (both packages)

```
DO NOT touch:
  backend/v9/systems/woodies/pattern_dispatcher.py
  backend/v9/systems/woodies/atr_stop.py
  backend/v9/systems/woodies/time_stop.py
  backend/v9/systems/woodies/anti_patterns.py
  backend/v9/systems/woodies/patterns/*.py  (raw_confidence formulas)
  Any S2 (five_min) code
  MEMS26_CONSTITUTION_V3_FINAL.txt
```

---

## STOP SIGNALS (both packages)

CC must STOP and report if:

1. W-9: Step 0a/0b pre-checks fail (prerequisites missing)
2. W-9: Modifying b13_trail_check.py EMA-169 logic would be required
3. W-11: TradeManager doesn't support partial close and a full rewrite would be needed
4. Either package: regression drops below 947 passing tests
5. Either package: forbidden surface files show diff

---

## CURSOR G3 REVIEW CRITERIA

### W-9
- [ ] Step 0a/0b pre-checks shown verbatim (or legitimate STOP if missing)
- [ ] b13_trail_check.py EMA-169 unchanged (rg confirms)
- [ ] Live repro: 3 sub-cases (rung-2 BE · rung-5 CONT · ladder-off EMA unchanged)
- [ ] ≥20 tests · all pass
- [ ] 947+ regression (0 new failures)
- [ ] RiskRule subclass used correctly

### W-11
- [ ] T1 hit → exactly 1 contract closed (not 2, not 0)
- [ ] BE stop set on remaining contracts after T1
- [ ] Full/half sizing handles correctly (3→close 1, 2→close 1)
- [ ] Live repro: 3 sub-cases
- [ ] ≥15 tests · all pass
- [ ] 947+ regression (0 new failures)
- [ ] time_stop.py wiring untouched

---

## MICHAEL CHECKLIST (after CC delivers)

```
[ ] Forward CC self-report to Cursor for G3 review
[ ] Confirm W-9 ladder fires on live bar (if prerequisites available)
[ ] Confirm partial exit shows correct contract count in UI
[ ] Run: python3 -m pytest tests/v9/systems/ --ignore=tests/v9/systems/test_woodies_dedup.py -q
[ ] Confirm 947+ pass
```

---

## SEQUENCING NOTE

**W-11 CAN start immediately** — no external prerequisites.
**W-9 MUST run Step 0 first** — if prerequisites still missing, W-9 is BLOCKED and W-11 proceeds alone.

Both packages are independent — CC can run W-11 first while waiting on W-9 prerequisites.

---

*Cursor sign-off: Pipeline 2 complete (W-1..W-8 + W-10 · G3 PASS 27/5) · Pipeline 3 open.*
