# SOT_HEALTH Audit — 04 — day_type API=None
Run: 2026-05-29 13:25 IL · 06:25 ET · market: OFF-HOURS (Globex overnight)
Verdict: CONFIRMED-REAL
SHADOW-blocker?: NO for S4. PARTIAL for S2 (chart patterns blocked, Reactive/Initiative unaffected)

## What was checked
Why `/api/v9/five_min/current.current_day_type = None` despite `v9_day_type_history` having a row for today. Traced the data path from state machine → `v9_day_type_state` → S2 hydrate → API.

## Evidence

### DB v9_day_type_history (last rows)

| date | day_type | status | probability | last_updated_at |
|------|----------|--------|-------------|-----------------|
| 2026-05-29 | UNKNOWN | PENDING | 0.0 | 2026-05-29 06:59:21 |
| 2026-05-28 | Normal | LOCKED_LOW_CONF | 0.68 | 2026-05-28 23:55:04 |
| 2026-05-27 | Trend_Normal | LOCKED_LOW_CONF | 0.38 | 2026-05-27 23:59:43 |

Today's row exists but is `UNKNOWN/PENDING` — the state machine hasn't classified yet (pre-RTH).

### DB v9_day_type_state (source for S2 hydrate)

Today: **122 Normal rows** (from overnight carry-over before restart) + **133 UNKNOWN rows** (after restart at ~05:44 UTC / 01:44 ET).

| id | ts | day_type | event |
|----|-----|----------|-------|
| 39102 | 05:00:03 UTC | Normal | Last carry-over before restart |
| 39103 | 05:44:32 UTC | UNKNOWN | First row after backend restart |
| 39235 | 07:21:29 UTC | UNKNOWN | Latest row |

The backend restarted at ~05:44 UTC (01:44 ET). Fresh state machine starts at stage A1, `day_type=UNKNOWN`. All subsequent overnight bars produce `UNKNOWN` because there's no RTH data to classify.

### API current_day_type (http + json)

```
GET /api/v9/five_min/current
  current_day_type: None
  mode: OVERNIGHT_MODE
  opening_type: None

GET /api/v9/day_type/v9/current
  classified: False
  day_type: 'UNKNOWN'
  session_date: '2026-05-29'
```

### Root in code (file:line · source blob)

S2 hydrate path (`five_min_system.py:129-155`):
1. Queries `v9_day_type_state` with 24h sliding window (`ts >= now - 24h`)
2. Takes `ORDER BY id DESC LIMIT 1` → latest row = `UNKNOWN`
3. Line 143: `if _latest_dt.day_type` — `"UNKNOWN"` is truthy, so it sets `current_day_type = "UNKNOWN"`
4. But wait — the API shows `None`, not `"UNKNOWN"`

This means one of:
- (a) The hydrate ran but `_latest_dt.day_type` was empty/None at that moment (race with first UNKNOWN write)
- (b) S2 is in `OVERNIGHT_MODE` which was set BEFORE the day_type hydrate in the hydrate sequence
- (c) The hydrate succeeded but something later reset it to None

Checking sequence: `hydrate()` at line 94 classifies session first → if overnight, returns early at line 117 **before** the day_type hydrate at line 129. **This is the root cause.**

```python
# five_min_system.py hydrate():
if session in (Session.OVERNIGHT, Session.PRE_MARKET, Session.AFTER_HOURS):
    self.mode = FiveMinMode.OVERNIGHT_MODE
    self._hydrated = True
    return HydrationResult(...)   # ← EARLY RETURN before day_type hydrate!

# ... day_type hydrate at line 129 is NEVER REACHED during overnight
```

### Fix #6 status (commit history + doc)

Fix #6 in commit `99671e4` changed the hydrate query from `func.current_date()` to a 24h sliding window. This fix is **IMPLEMENTED** and correct — but it's moot because the hydrate early-returns during overnight before reaching the day_type query.

The fix addresses case (b) from the prompt (UTC vs ET date boundary mismatch) but does NOT address the early-return during overnight sessions.

## Finding

**`current_day_type = None` is REAL and caused by:**

The `hydrate()` method in `five_min_system.py` returns early for overnight/pre-market sessions (line 114-118) **before** reaching the day_type hydrate block (line 129). So `current_day_type` stays at its `__init__` default of `None`.

This is NOT related to RCA-2 (empty cross_context blobs). It's a simpler ordering bug: the overnight early-return skips the day_type hydrate.

**Impact on firing:**

| System | Blocked? | Why |
|--------|----------|-----|
| S4 (Woodies) | **NO** | S4 does not read `current_day_type` at all in runtime path |
| S2 Reactive/Initiative | **NO** | These only check `current_day_type == "Nontrend"` (line 717). `None != "Nontrend"` → passes |
| S2 Chart patterns (H&S, DblBT) | **YES** | Line 736: `None not in ("Neutral_Extreme", "Normal", ...)` → blocked |
| S2 Flags (Bull/Bear) | **YES** | Line 750: `None not in ("Trend_Normal", "Normal", ...)` → blocked |

During RTH, the `_on_day_type_update` event handler (line 266-272) will set `current_day_type` once the state machine classifies. So **chart patterns and flags are blocked only until the first S1 classification event arrives** (typically 10:30 ET after IB lock). Reactive and Initiative work from 09:30.

## Recommendation (for Cursor/Michael — DO NOT execute)

1. **Not a SHADOW blocker for S4.** S4 fires independently of `current_day_type`.
2. **Partial S2 blocker** — chart patterns blocked until first S1 event. Reactive/Initiative unaffected.
3. **Root fix:** Move the day_type hydrate block (lines 129-155) to BEFORE the overnight early-return, or duplicate it inside the overnight return path. One-line move, not a new mechanism.
4. **sot_health.py** should downgrade this from 🔴 to 🟡 pre-RTH — `current_day_type=None` is expected off-hours with the current code. After RTH + first S1 event, if still None → 🔴.
5. **Fix #6 is implemented but insufficient** — it fixed the UTC/ET boundary issue but the early-return issue is a separate bug in the same function.

## Open questions

1. Should the day_type hydrate run even during overnight? The state machine writes `UNKNOWN` overnight, so S2 would hydrate `current_day_type = "UNKNOWN"` — which is equivalent to `None` for the chart pattern gates (neither passes). The real fix may be: during RTH, if `current_day_type` is still None/UNKNOWN after the first 30 bars, fall back to yesterday's classification.
2. The 122 `Normal` rows followed by 133 `UNKNOWN` rows today suggest the overnight carry-over (before the session_date ET fix) was writing `Normal` from yesterday. After the backend restart, the fresh state machine correctly writes `UNKNOWN`. This confirms the session_date fix is working as intended.
