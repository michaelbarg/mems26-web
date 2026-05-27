# META-PROMPT · W-10 · Time Stop Enforcement · S4 Woodies CCI

**From:** Cursor (G3 reviewer)
**To:** Claude Desktop → Claude Code
**Date:** 2026-05-27 IL
**Authority:** Registry #11 (MEMS26_SYSTEMS_DECISIONS_REGISTRY_2026-05-23.md §7.3 row 11) · "חובה לפני LIVE"
**Branch:** `stabilize/mems26-local-truth-2026-05-16`

---

## CONTEXT FOR CLAUDE DESKTOP

Pipeline 2 delivered 9 Woodies patterns with full R_t1 dispatch and ATR-capped stops.
One gap was identified post-delivery as a **LIVE blocker**:

`time_stop_minutes` field exists in the Woodies trade schema and is set to `90` in
`woodies_system.py:267`, but **no code actually enforces it**. A trade opened by the
Woodies system can stay open indefinitely. This is explicitly flagged in
`MEMS26_SYSTEMS_DECISIONS_REGISTRY_2026-05-23.md` §7.3 row 11 as "חובה לפני LIVE."

**Your job:** Write a Claude Code mega-prompt that implements W-10 Time Stop enforcement
for the Woodies system. The prompt must follow the §5 Memorial Day lessons and the
pre-LIVE protocol exactly.

---

## SPEC AUTHORITY (read these before writing the prompt)

1. `MEMS26_SYSTEMS_DECISIONS_REGISTRY_2026-05-23.md` §7.3 row 11 — canonical requirement
2. `backend/v9/systems/woodies/woodies_system.py` — entry point, lines 230–280 (trade emit path)
3. `backend/v9/systems/woodies/schemas.py` — PatternResult / trade schemas; locate `time_stop_minutes`
4. `backend/v9/systems/woodies/stages/` — B-stage lifecycle (b3_color_flip · b13_trail_check · others)
5. `MEMS26_CONSTITUTION_V3_FINAL.txt` — §Time Stop section (read-only · do NOT modify)
6. `docs/decisions/D-092_S4_WOODIES_UPDATE.md` — D-092 trail column + exit discipline

---

## WHAT THE W-10 PROMPT MUST INSTRUCT CC TO DO

### Step 0 · Mandatory pre-checks (CC must STOP if any fail)

```
a. rg "time_stop_minutes" backend/v9/systems/woodies/ --type py
   → must show the field exists in schema + woodies_system.py
   → must show 0 enforcement call sites (confirm the gap is real)

b. rg "class TradeLifecycleManager\|class TradeManager\|_open_trade\|_close_trade" backend/v9/systems/woodies/ --type py
   → identify how trades are opened and the normal exit path

c. Read woodies_system.py lines 230–300 (trade emit + lifecycle)
   → identify the exact hook point for time-based exit
```

### Step 1 · Design decision CC must document in self-report

The time stop must be checked on EVERY bar tick for open Woodies trades.
CC must decide and document which hook fires per-bar:

- Option A: add check inside `WoodiesSystem.on_bar()` after pattern detection
- Option B: add a dedicated `_check_time_stop()` method called from `on_bar()`
- Option C: wire into existing B-stage pipeline as a new stage `b_time_stop.py`

**CC must read existing B-stage files before choosing.** Option C is preferred
if a B-stage `on_bar()` hook already exists. Option B is safe fallback.

### Step 2 · Implementation requirements

```
a. TimeStopResult dataclass:
   - fired: bool
   - bars_open: int
   - limit_bars: int  (= time_stop_minutes // 5  for 5-min bars)
   - reason: str

b. Enforcement logic:
   - Convert time_stop_minutes → bar count (÷5 for 5-min bars · configurable tick_minutes param)
   - Track bars_since_entry per open trade (use existing open_trade state or add field)
   - When bars_open >= limit_bars → emit exit signal with reason="TIME_STOP"
   - Log at WARNING level (NOT debug): f"[woodies] TIME_STOP fired · bars_open={bars_open} · limit={limit_bars} · pattern={pattern_id}"
   - Do NOT raise exception · emit exit and continue

c. Scope:
   - Applies to ALL 9 patterns (ZLR · TLB · TT · GB100 · VEGAS · GHOST · FAMIR · HTLB · HFE)
   - time_stop_minutes default = 90 (= 18 bars on 5-min)
   - Must be overridable per PatternDispatcher config (add optional `time_stop_minutes` key to dispatcher_config.yaml)

d. Forbidden surface:
   - Do NOT touch raw_confidence formulas in any pattern file
   - Do NOT touch PatternDispatcher.select_winner()
   - Do NOT touch atr_stop.py
   - Do NOT touch any S2 (five_min) code
   - Do NOT modify MEMS26_CONSTITUTION_V3_FINAL.txt
```

### Step 3 · Tests required (minimum)

```
tests/v9/systems/test_time_stop.py  (create new · ≥15 tests)

Required test cases:
1. trade open for 17 bars → NOT fired (< 18 bar limit for 90min default)
2. trade open for 18 bars → FIRED · reason="TIME_STOP"
3. trade open for 19 bars → FIRED (idempotent · already-exited trade)
4. time_stop_minutes=45 → limit=9 bars · fires at bar 9
5. time_stop_minutes=None or 0 → no enforcement (disabled path)
6. All 9 patterns fire time stop independently
7. time_stop does NOT fire when trade already closed by trailing stop
8. WARNING log emitted on fire (capture via caplog)
9. TimeStopResult dataclass fields correct
10. YAML config override for time_stop_minutes works
```

### Step 4 · Self-report requirements (§5 Memorial Day lessons)

CC self-report MUST include:

```
§1 Pre-check output — paste rg results from Step 0
§2 Design decision — which option chosen · why · quoted read of hook point with line numbers
§3 Implementation — diff summary per file · no elision
§4 Live Python repro — must use REAL WoodiesSystem class (not Fake)
   Repro must show:
   (a) trade open 18 bars → TimeStopResult.fired = True
   (b) trade open 17 bars → TimeStopResult.fired = False
   (c) WARNING log captured
§5 Test results — pytest output pasted verbatim
§6 Forbidden surface — paste rg output confirming no touch to raw_confidence / select_winner / atr_stop / S2 code
```

---

## CURSOR G3 REVIEW CRITERIA

When CC delivers W-10, Cursor will verify:

- [ ] Pre-checks in §0 show gap is real (0 enforcement sites before fix)
- [ ] WARNING log (not debug) on time stop fire
- [ ] limit_bars = time_stop_minutes ÷ 5 (correct formula)
- [ ] All 9 patterns covered (no pattern-specific exclusion)
- [ ] YAML override path works
- [ ] Forbidden surface untouched (raw_confidence · select_winner · atr_stop)
- [ ] ≥15 tests · all pass
- [ ] Live repro with real WoodiesSystem class present
- [ ] 912+ regression passing (no new failures)

---

## STOP SIGNALS FOR CC

CC must STOP and report back to Michael/Cursor if:

1. Step 0 pre-checks show `time_stop_minutes` is ALREADY enforced somewhere — do not duplicate
2. The hook point identified in Step 1 would require modifying PatternDispatcher or atr_stop
3. Any test reveals time stop fires on a trade that is NOT open (false positive path)
4. Regression suite drops below 912 passing

---

## DELIVERABLES CHECKLIST

```
[ ] backend/v9/systems/woodies/time_stop.py  (or b_time_stop.py if Option C)
[ ] backend/v9/systems/woodies/woodies_system.py  (wired)
[ ] backend/v9/systems/woodies/config/dispatcher_config.yaml  (time_stop_minutes key added)
[ ] tests/v9/systems/test_time_stop.py  (≥15 tests)
[ ] CC_W10_SELF_REPORT.md  (§1-§6 complete)
```

---

## TIMING

Estimated: ~1.5 CC days.
Priority: **HIGH** — LIVE gate. SHADOW can proceed without W-10 (paper trading only).
Do NOT block SHADOW startup on W-10. W-10 must be complete before any real-money LIVE enablement.

---

*Cursor sign-off: G3 W-1..W-8 PASS 27/5 09:00 IL · W-10 is the only remaining LIVE blocker in Pipeline 2.*
