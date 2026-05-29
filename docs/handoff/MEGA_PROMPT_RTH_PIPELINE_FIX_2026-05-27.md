# MEGA PROMPT — RTH Pipeline Fix + Pattern Review
**Date:** 2026-05-27  
**For:** Claude Desktop (implementation) + Claude Code (verification)  
**Cursor reviews at end**

---

## CONTEXT — READ FIRST

Today (2026-05-27) the system was active all RTH but fired zero shadow/demo trades.
Root-cause forensic is in: `docs/reports/SHADOW_LIVE_BRINGUP_2026-05-27.md`

Two structural bugs blocked the entire signal chain:
1. **S2 (FiveMin)**: `process_bar()` missing FIRST_HOUR_TACTICAL → DAY_TYPE_MODE transition
2. **S4 (Woodies)**: Gateway `demo_enabled_systems=[]` — no demo trades, shadow not persisted

This prompt is THREE separate passes. Do them in order.

---

## PASS 1 — CODE FIXES (Claude Desktop + Claude Code)

### Fix F1 — S2 Mode Transition

**File:** `backend/v9/systems/five_min/five_min_system.py`  
**Function:** `process_bar()` (around line 663)

**Read first:** Lines 648–710 of the file.

**Current code** has this block:
```python
if self.mode == FiveMinMode.OVERNIGHT_MODE:
    try:
        info = self.session_classifier.classify()
        if info.session in (Session.CASH_OPEN, Session.FIRST_HOUR):
            self.mode = FiveMinMode.FIRST_HOUR_TACTICAL
            self._fhb.reset()
            logger.info("[FiveMin] Mode transition OVERNIGHT → FIRST_HOUR_TACTICAL (live bar)")
        elif info.session == Session.CASH_HOURS:
            self.mode = FiveMinMode.DAY_TYPE_MODE
            logger.info("[FiveMin] Mode transition OVERNIGHT → DAY_TYPE_MODE (live bar)")
    except Exception:
        pass
```

**Add AFTER this block** (not inside it — at the same indentation level):
```python
elif self.mode == FiveMinMode.FIRST_HOUR_TACTICAL:
    try:
        info = self.session_classifier.classify()
        if info.session == Session.CASH_HOURS:
            self.mode = FiveMinMode.DAY_TYPE_MODE
            self._fhb.lock()
            logger.info("[FiveMin] Mode transition: FIRST_HOUR_TACTICAL → DAY_TYPE_MODE (live bar)")
    except Exception:
        pass
```

**Verify:** `_fhb.lock()` must exist on the FirstHourBuffer object. If it doesn't exist, use `pass` after the mode assignment (do NOT add a method that doesn't exist — ask Cursor to verify).

**Regression test:** `tests/v9/systems/test_five_min_mode_transitions.py` — add test:
- Backend starts pre-RTH → hydrates to FIRST_HOUR_TACTICAL
- First bar with session=CASH_HOURS → mode transitions to DAY_TYPE_MODE
- Chart pattern detectors run in DAY_TYPE_MODE

---

### Fix F2 — Enable Demo Mode for Woodies

**File:** `backend/main.py`  
**Section:** Around line 391 where `trading_gateway.set_trade_manager()` is called.

**Read first:** Lines 380–410.

**Find** the gateway setup block that looks like:
```python
if hasattr(app.state, 'five_min_system') and app.state.five_min_system:
    app.state.five_min_system.set_gateway(trading_gateway)
```

**Add after** the gateway injection block:
```python
# Enable DEMO mode for S2 (FiveMin=2) and S4 (Woodies=4)
# Shadow → Demo → Live progression per architecture
trading_gateway.enable_demo(4)   # S4 Woodies CCI
trading_gateway.enable_demo(2)   # S2 FiveMin patterns
logger.info("[Main] Demo mode enabled: systems [2, 4]")
```

**Do NOT** enable live mode. Demo only.

---

### Fix F3 — Persist Shadow Trades to v9_trades

**File:** `backend/v9/gateway/trading_gateway.py`  
**Function:** `_execute_shadow()`

**Read first:** The full `_execute_shadow()` function.

**Goal:** At end of `_execute_shadow()`, before returning the shadow dict, write a row to `v9_trades` with:
```
mode = 'SHADOW'
firing_system = setup.get('firing_system', 0)
direction = setup.get('direction')
state = 'OPEN'
entry_ts = datetime.now(UTC).isoformat()
entry_price = setup.get('entry_price', 0)
stop = setup.get('stop', 0)
t1 = setup.get('t1', 0)
t2 = setup.get('t2', 0)
```

**First read** the `v9_trades` table schema:
```sql
PRAGMA table_info(v9_trades);
```

Match every column in the insert. Do NOT add columns that don't exist.

**Add a `try/except` around the DB write** — shadow trade persistence must never crash the gateway.

---

### Fix F4 — Footprint Gateway System ID (secondary)

**File:** `backend/v9/systems/footprint/footprint_system.py`

**Error:** `[Footprint] Gateway route_setup failed: Invalid firing_system: 3`

**Find** where `route_setup` is called. Check what `firing_system` value is passed.  
The `FireRequest` in `pre_fire_validator.py` accepts only: `T1_NUMBER_BAR`, `T2_WOODIES`, `T3_FOOTPRINT`.

**Fix:** Pass `firing_system=3` (integer) in the setup dict — the validator checks `system_id: int`, not `firing_system`. The error might be in the gateway's internal validation, not `FireRequest`. Trace the exact error before changing.

---

## PASS 2 — PATTERN REVIEW (Claude Code)

Run this after Pass 1 fixes are applied.

### S4 Woodies — Pattern Engine Audit

**File:** `backend/v9/systems/woodies/pattern_engine.py` and `patterns/` directory

For each of the 9 patterns (ZLR, TLB, TT, GB100, VEGAS, GHOST, FAMIR, HTLB, HFE):

1. **Read the detect() function**
2. **Verify entry_price, stop, targets are always set** when `detected=True`
3. **Check compute_stop() call** — does it ever return None stop_price?
4. **Check targets list** — does it always have ≥ 2 elements?
5. **Log any pattern where entry/stop/targets could be None** → that pattern will fail A7

If any pattern can return `PatternResult(detected=True, entry_price=None, ...)`, **fix it** to return `detected=False` with a reject_reason, OR ensure compute_stop always returns a valid price.

### S2 FiveMin — Pattern Audit

**File:** `backend/v9/systems/five_min/` — all detector files

For each detector:
- `detect_reactive()` — what patterns does it look for?
- `detect_initiative()` — same
- `detect_inverse_hns()`, `detect_hns_top()` — read min_bars requirements
- `detect_double_bottom_ee()`, `detect_double_top_aa()` — same
- `detect_bull_flag()`, `detect_bear_flag()` — same

Report: For each detector, what market conditions are needed? Are they reachable on a Trend_Normal day?

---

## PASS 3 — LIVE DATA REVIEW (Claude Code)

Run this during market hours on next trading day (after fixes deployed).

### At RTH Open (09:30 ET):

```bash
# 1. Check S2 mode
curl http://localhost:8000/api/v9/five_min/current | python3 -c "import json,sys; d=json.load(sys.stdin); print('mode:', d.get('mode'))"

# 2. Check build status
curl http://localhost:8000/api/v9/build/pattern-status | python3 -c "import json,sys; d=json.load(sys.stdin); [print(s['id'], s['running']) for s in d['systems']]"

# 3. Check gateway demo status
curl http://localhost:8000/api/v9/gateway/status | python3 -c "import json,sys; d=json.load(sys.stdin); print('demo_systems:', d.get('demo_enabled_systems'))"

# 4. Check bridge freshness
curl http://localhost:8000/api/v9/build/pattern-status | python3 -c "
import json,sys; d=json.load(sys.stdin)
bridge = next((s for s in d['systems'] if s['id']=='bridge'), {})
for g in bridge.get('global_gates', []): print(g['key'], g['present'], g.get('value',''))
"
```

### At 10:30 ET (after FHB lock):

```bash
# Verify mode transitioned to DAY_TYPE_MODE
curl http://localhost:8000/api/v9/five_min/current | python3 -c "import json,sys; d=json.load(sys.stdin); print('mode:', d.get('mode'), '— should be DAY_TYPE_MODE')"
```

### At 11:00+ ET:

```bash
# Check for any setups
python3 -c "
import sqlite3
conn = sqlite3.connect('/Users/michael/Downloads/mems26_web_git/data/mems26_local.db')
rows = conn.execute(\"SELECT ts, pattern, direction FROM v9_five_min_setups WHERE date(ts)=date('now') ORDER BY ts\").fetchall()
print('S2 setups today:', len(rows))
for r in rows: print(' ', r)

rows2 = conn.execute(\"SELECT ts, mode, direction, state FROM v9_trades WHERE date(entry_ts)=date('now') ORDER BY id\").fetchall()
print('Trades today:', len(rows2))
for r in rows2: print(' ', r)
conn.close()
"
```

---

## HANDOFF NOTES

- Do NOT change `_RTH_ONLY` or any trading logic gating
- Do NOT enable LIVE mode — only DEMO
- Do NOT change any spec/decision tree stages
- If `_fhb.lock()` doesn't exist, skip it — don't add dead methods
- Run `pytest tests/v9/ -q` after each fix pass — must stay green
- Report results back to Cursor agent for UAT verification

**Cursor verification checklist (after CC completes):**
- [ ] `v9_five_min_setups` has rows on next trading day
- [ ] Mode transitions correctly at 10:30 ET
- [ ] `demo_enabled_systems: [2, 4]` in gateway status
- [ ] Shadow trades appear in `v9_trades` with `mode='SHADOW'`
- [ ] Build Status shows bridge FRESH indicators
- [ ] All tests pass
