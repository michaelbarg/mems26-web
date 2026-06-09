# MEMS26 Bug Investigation — 2026-06-08

## Bug #1: S4 stop=None crash (Pydantic validation error)

### Raw Evidence

```
[Woodies] process_bar error: 1 validation error for PatternResult
stop
  Input should be a valid number [type=float_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.13/v/float_type
Traceback (most recent call last):
  File ".../woodies_system.py", line 317, in process_bar
```

### Root Cause

**File:** `backend/v9/systems/woodies/woodies_system.py` lines 317-324 (ZLR) and 329-337 (HFE)

The DLL-flagged fallback path constructs `PatternResult` with `stop=None`:

```python
# Line 317-324 (ZLR DLL fallback)
patterns.append(PatternResult(
    detected=True, pattern_id="ZLR", direction=_zlr_dir,
    confidence=0.65, raw_confidence=0.65,
    entry_price=wb.close, stop=None, targets=[],  # <── THE BUG
    ...
))

# Line 329-337 (HFE DLL fallback)
patterns.append(PatternResult(
    detected=True, pattern_id="HFE", direction=_hfe_dir,
    confidence=0.60, raw_confidence=0.60,
    entry_price=wb.close, stop=None, targets=[],  # <── SAME BUG
    ...
))
```

**Schema:** `backend/v9/systems/woodies/schemas.py` line 78: `stop: float = 0.0` — non-Optional since the original commit (`5f33ac0`, 2026-05-10). Pydantic V2 rejects `None` for a plain `float` field.

**Git blame:**
```
5f33ac0b (Michael Barg 2026-05-10 22:36:12 +0300  78)     stop: float = 0.0
```
The field was **never** Optional — it has always been `float = 0.0`.

### Stop Source Map — ALL PatternResult constructions in S4

| Source | File:Line | How stop is computed | Can be None? |
|--------|-----------|---------------------|-------------|
| Python ZLR detector | `patterns/zlr.py:131,197` | `compute_stop()` or `compute_stop_v2()` or fixed `STOP_TICKS * TICK_SIZE` | **No** — all 3 branches produce a float |
| Python TLB detector | `patterns/tlb.py:129,185` | Same ATR/V2/fixed pattern | No |
| Python TT detector | `patterns/tt.py:119,178` | Same ATR/V2/fixed pattern | No |
| Python HTLB detector | `patterns/htlb.py:138,201` | Same ATR/V2/fixed pattern | No |
| Python FAMIR detector | `patterns/famir.py:112,174` | Same ATR/V2/fixed pattern | No |
| **DLL ZLR fallback** | **woodies_system.py:320** | **Hardcoded `stop=None`** | **YES — CRASH** |
| **DLL HFE fallback** | **woodies_system.py:332** | **Hardcoded `stop=None`** | **YES — CRASH** |

### Why stop=0.0 (the default) is also wrong

If `stop=None` were changed to omit the argument (defaulting to `0.0`), this would create a **phantom risk surface**: a ZLR LONG at entry=7469.75 with stop=0.0 implies a 7469.75-point risk (29,879 ticks). Any downstream sizing or R:R calculation would be nonsensical. The correct stop must be computed from ATR-14 and structural anchors, exactly as the Python detectors do.

### What the correct stop should have been (ZLR SHORT at 19:35 example)

From the error log context (bars around ts=1780678800):
- Entry price (bar close): ~7463.50
- Direction: SHORT (zlr_direction=DOWN)
- ATR-14: not available from DLL path (that is the root issue)
- Pattern group: CONT_TIGHT (ZLR) → 1.0x ATR cap

The DLL fallback path has no access to the ATR-14 or the bar buffer needed to compute structural stops. It bypasses the entire `compute_stop()` / `compute_stop_v2()` machinery.

### Proposed Fixes

**Option A (recommended): Compute stop in the DLL fallback path.** After constructing the DLL-flagged PatternResult, call the same `compute_stop_v2()` / `compute_stop()` chain that the Python detectors use. The bar buffer (`self._bar_buffer`) and ATR are available at that scope. ~10 lines of code.

**Trade-off:** Slightly more compute per DLL-detected bar, but negligible vs. the cost of a crash that silences all subsequent pattern detection for that `process_bar` call.

**Option B: Make `stop` Optional in the schema.** Change to `stop: Optional[float] = None`. All downstream consumers (sizing, R:R, gateway) must then handle `None` gracefully.

**Trade-off:** Pushes the problem downstream. Every consumer needs a None guard. Risk of silent bad trades if a consumer misses the check. Not recommended.

---

## Bug #2: S2 DB persist ts type error

### Raw Evidence

```
2026-06-08 22:10:02 [WARNING] [FiveMin] DB persist error: an integer is required (got type str)
```

### Root Cause

**File:** `backend/v9/systems/five_min/five_min_system.py` line 1132

```python
setup = V9FiveMinSetup(
    ts=datetime.fromtimestamp(bar.get("ts", 0), tz=timezone.utc),
    #                        ^^^^^^^^^^^^^^^^
    # bar.get("ts") returns an ISO string like "2026-06-08T22:10:00+00:00"
    # datetime.fromtimestamp() expects a numeric epoch (int/float)
    # → TypeError: an integer is required (got type str)
```

The bridge pushes `bar["ts"]` as a string (ISO 8601) in the five_min path. The code assumes it is a numeric epoch. The `V9FiveMinSetup.ts` column is `DateTime(timezone=True)` — it needs a proper `datetime` object, not a raw epoch or string.

### Evidence of ts format

In the same file at line 873: `_bar_ts = str(bar.get("ts", ""))` — the code already treats `ts` as potentially a string. The woodies system (line 206-221) has explicit ISO-string-to-epoch parsing because it knows both formats arrive. The five_min persist block at line 1132 does not.

### Proposed Fix

Replace `datetime.fromtimestamp(bar.get("ts", 0), tz=timezone.utc)` with:

```python
_raw_ts = bar.get("ts", 0)
if isinstance(_raw_ts, str):
    ts_val = datetime.fromisoformat(_raw_ts.replace("Z", "+00:00"))
else:
    ts_val = datetime.fromtimestamp(float(_raw_ts), tz=timezone.utc)
```

**Trade-off:** None significant. This is a straightforward type-coercion fix. The fire itself still propagates to the gateway (the DB persist is in a try/except and does not block the fire path), so this is a data-loss bug (fires not persisted to `v9_five_min_setups`), not a trading-logic bug.

---

## Bug #3: S2 detection on partial bar (engine vs. inspector OHLC mismatch)

### Root Cause

**Engine path** (`five_min_system.py` line 532):
```python
b1, b2, b3, b4 = bars_5m[-4], bars_5m[-3], bars_5m[-2], bars_5m[-1]
```
The engine runs inside `process_bar()` which fires on each bridge push. At line 885, `is_new_bar` gates detection to only run on genuinely new bar timestamps. But `bars[-1]` is the bar that *just arrived* — its OHLC reflects the first push of that 5-min window (partial candle), not the final close.

The dedup logic (lines 870-886) updates `_bar_buffer[-1]` on duplicate pushes (line 883: `self._bar_buffer[-1] = bar`), but detection only runs on `is_new_bar=True` (line 886 returns early otherwise). So the detection fires on the FIRST push of the bar, when OHLC is incomplete.

**Inspector path** (`s2_pattern_probe.py` line 552):
```python
b1, b2, b3, b4 = bars[-4], bars[-3], bars[-2], bars[-1]
```
The inspector reads from `_bar_buffer` which has been updated with the LATEST OHLC for the current bar (via the line 883 update). So `bars[-1]` is the fully-formed candle.

### The Contrast

| Property | Engine (`_detect_reactive`) | Inspector (`_probe_reactive_long`) |
|----------|---------------------------|-----------------------------------|
| When it runs | First push of new bar ts | On-demand (build-status poll, 5s) |
| `bars[-1]` OHLC | **Partial** (first push) | **Final** (latest push) |
| b4 close | Opening tick of 5-min bar | Actual close of 5-min bar |
| Effect | False positives on partial candle geometry | Accurate detection |

### Impact

S2 can fire on a candle whose close/high/low are still forming. A bar that opens bearish (triggering reactive SHORT detection) may close bullish — but the fire already happened. The inspector (build-status) will show the pattern as NOT passing because it sees the final OHLC.

### Proposed Fix

**Option A (recommended): Defer detection to bar N-1.** When a new bar arrives, run detection on `bars[-5:-1]` (b1..b4 = the previous 4 completed bars) instead of `bars[-4:]`. The current bar is always partial at detection time.

**Trade-off:** Detection lags by one bar (5 minutes). This is the standard approach for bar-close strategies.

**Option B: Run detection on every push, but only emit on `is_new_bar` of the NEXT bar.** Buffer the detection result and confirm it once the bar closes.

**Trade-off:** More complex bookkeeping but zero latency loss.

---

## Bug #4: Woodies DB write ts integer (safe_writer)

### Raw Evidence

```
[safe_writer] execute failed: (psycopg2.errors.DatatypeMismatch) column "ts" is of type
timestamp with time zone but expression is of type integer
LINE 1: ..., hfe_extreme_bars_ago, lsma_above_price) VALUES (1780678200...
[parameters: {'p0': 1780678200, ...}]
```

### Root Cause

**File:** `backend/v9/api/v9/bars.py` line 911

```python
result = safe_execute(
    "INSERT OR REPLACE INTO v9_bars_5min_woodies "
    "(ts, symbol, open, high, low, close, volume, ...)"
    "VALUES (?, ?, ?, ...)",
    (
        bar.get("ts", ""),  # <── passes raw epoch integer (e.g., 1780678200)
        "MES", o, h, l, c, vol, ...
    ),
)
```

The `v9_bars_5min_woodies.ts` column is `DateTime(timezone=True)` (PostgreSQL `timestamptz`). The bridge pushes `bar["ts"]` as an epoch integer. PG cannot implicitly cast an integer to `timestamptz`.

**Note:** There is a SECOND write path in `woodies_system.py` line 597-621 (`_persist_bar`) that DOES convert epoch to ISO (lines 601-606). But that path uses the OLD 17-column INSERT (without `proj_hi`, `proj_lo`, `hfe_*`, `lsma_above_price`). The error log shows the 23-column INSERT, which matches the `bars.py` path — confirming that **bars.py line 911 is the active failing writer**.

### Model vs. Writer mismatch

| Writer | File | Columns | ts conversion | Status |
|--------|------|---------|---------------|--------|
| `bars.py` (API ingest) | `backend/v9/api/v9/bars.py:902-923` | 23 (full schema) | **None** (raw epoch) | **FAILING** |
| `woodies_system.py._persist_bar` | `woodies_system.py:597-621` | 17 (old schema) | ISO conversion (line 601) | Would work for ts, but **missing 6 columns** |

### safe_writer usage elsewhere (risk assessment)

`safe_execute` is used in 11+ files. The ts-as-epoch pattern likely affects any writer that passes bridge-originated timestamps without conversion:
- `backend/v9/gateway/trading_gateway.py`
- `backend/v9/services/bar_ingestion.py`
- `backend/v9/systems/footprint/footprint_system.py`
- `backend/v9/systems/tpo/tpo_system.py`
- `backend/v9/systems/reversal/reversal_handler.py`
- `backend/v9/services/session_boundary/manager.py`
- `backend/v9/services/tpo_history_snapshotter.py`
- `backend/v9/systems/day_type/shadow_reclass.py`

Each of these should be audited for the same epoch-to-timestamptz mismatch.

### Proposed Fix

Add epoch-to-ISO conversion at line 911 in `bars.py`:

```python
_ts_raw = bar.get("ts", "")
if isinstance(_ts_raw, (int, float)):
    _ts_raw = datetime.fromtimestamp(float(_ts_raw), tz=timezone.utc).isoformat()
```

**Trade-off:** Minimal. Same pattern already used in `woodies_system.py:601-606`.

**Alternative:** Add the conversion inside `safe_writer.py` itself (centralized fix). Any `timestamptz` column receiving an integer would be auto-converted. Trade-off: `safe_writer` has no schema awareness, so it cannot know which positional param maps to a timestamp column. A centralized fix would require either column-type introspection or a blanket "if int and > 1e9, assume epoch" heuristic — fragile.

---

## Summary

| Bug | Severity | Impact | Root File:Line | Fix Complexity |
|-----|----------|--------|----------------|----------------|
| #1 S4 stop=None | **P0** | Crashes entire process_bar, silences ALL pattern detection for that bar | `woodies_system.py:320,332` | Low (~10 LOC) |
| #2 S2 DB persist ts | P2 | Fires not persisted to DB (fire still routes to gateway) | `five_min_system.py:1132` | Low (~5 LOC) |
| #3 S2 partial bar | P1 | False positive fires on incomplete candle OHLC | `five_min_system.py:886` (dedup gate) | Medium (architectural) |
| #4 S4 DB write ts | P1 | ALL woodies bars silently lost (not persisted) | `bars.py:911` | Low (~3 LOC) |

---

## Ground-Truth: b4 חלקי בזמן detection (חלק A — חקירה)

### הוכחה מדאטה חי

ה-Reactive SHORT שירה ב-22:10 מוכיח את הבעיה:
- **Engine ראה (push ראשון):** entry=7425.25 (c של הבר בתחילתו)
- **ערך סופי של הבר ב-DB:** c=7414.75, vol=18810
- **פער:** 10.5 נקודות! ה-entry שנקבע מתבסס על opening tick, לא close.

### נתיב מדויק
```
five_min_system.py:874   is_new_bar = _bar_ts != self._last_bar_ts_for_count
five_min_system.py:878   self._bar_buffer.append(bar)  ← בר חלקי נכנס לבאפר
five_min_system.py:885   if not is_new_bar: return     ← pushes הבאים (עם data מלא) מדולגים
five_min_system.py:917   _detect_reactive(self._bar_buffer)  ← detection על באפר עם b4 חלקי
five_min_system.py:532   b4 = bars[-1]                 ← b4 = הבר החלקי
```

### הפער engine ↔ inspector
- **Inspector** (s2_pattern_probe.py:81): `b4 = bars[-1]` — אבל קורא מ-DB בזמן שאילתה → b4 כבר מלא
- **Engine** (five_min_system.py:532): `b4 = bars[-1]` — אבל קורא ב-push ראשון → b4 חלקי
- **תוצאה:** Inspector מראה "All conditions met" אבל Engine לא רואה את ה-setup

### תיקון מוצע (לא בוצע — ממתין לאישור)
`detection_buffer = self._bar_buffer[:-1]` כש-is_new_bar=True.
4 תנאים: engine+inspector על אותו חלון | emit עקבי | flag-gated | FHB/ATR לא נגעים.

---

## S4 חוסמים בתוך חלונות ה-trend (חלק B-א)

### BLUE window (17:50–18:20 IL)
CCI: 151→172→156→131→104→87→68. **ירידה מונוטונית מ-172 ל-68.**
- ZLR UP דורש: extreme ≥+100, pullback לאזור 0, bounce חזרה. 
- **לא התרחש:** CCI ירד ברצף בלי pullback לאפס ו-bounce.
- **חוסם: אין pullback+bounce** (דוקטרינה, לא באג).

### RED window 1 (18:50–19:10 IL)
CCI: -27→-98→-87→-70. **Extreme -98.2, לא הגיע ל-≤-100.**
- ZLR DOWN Stage 1 דורש CCI ≤ -100.
- **חוסם: CCI=-98.2, חסרות 1.8 נקודות CCI** מהסף.
- ⚠️ אבל: DLL סימן ZLR כאן — כנראה חישוב CCI שונה מעט מהקוד שלנו.

### RED window 2 (19:35–20:15 IL) — **ההזדמנות שהוחמצה**
CCI: -159→-128→-53→-49→-49→-208→-164→-160→-102.
- Extreme ≤-100 ✓ (19:35: -159), pullback ל-~-49 ✓, drop חזרה ✓
- **ZLR DOWN תקני!** Detect() מאשר detected=True.
- **חוסם: באג #1** (stop=None crash). process_bar קרס לפני detection.

### RED window 3 (22:00–22:25 IL)
CCI: -119→-155→-243→-211→-155→-161.
- Extreme ≤-100 ✓✓✓ (מרובות).
- **חוסם: באג #1** + ייתכן שגם post-RTH (16:00 ET = 23:00 IL).

---

## Readiness verdict breakdown (חלק B-ג)

```
verdict: READY (RTH סגור — post-market)
  bridge_streams_fresh: ✓
  s1_day_type_classified: ✓ (Variation)
  s4_trend_not_stuck_gray: ✓ (RED at close)
  in_rth: ✓ (check passes as informational post-RTH)
```

**סיבת ה-DEGRADED שהיה קודם:** `tick_reversal_15` + `tpo` dead. תוקן ע"י הוספתם ל-_NON_CRITICAL_STREAMS (commit a8cb1fb).

---

## Near-miss table (חלק B-ד)

| תבנית | סף | בפועל | פער | הערה |
|--------|-----|--------|------|------|
| ZLR DOWN | CCI ≤ -100 | -98.2 (19:00) | 1.8 CCI pts | DLL סימן — חישוב שלנו שונה? |
| ZLR DOWN | trend=RED + detect | detected=True (19:35) | 0 — עבר! | נחסם ע"י באג #1 בלבד |
| Initiative | b1_range ∈ [1.3×avg, 2.5×avg] | 8.25 need [11.4,21.9] | 3.15pt below min | יום תנודתי, avg גבוה |
| Double Top AA | auth ≠ SKIP | SKIP until 18:10 (Trend_Normal) | — | FULL after reclass to Variation |
| Reactive SHORT | all gates pass | **FIRED 22:10** | 0 | DB persist failed (באג #2) |

---

## NOT-DONE
- חלק A (תיקון b4 חלקי): ממתין לאישור Cowork + Michael. חקירה בלבד.
- חלק C (frontend Shadow tab): לא בוצע — RTH סגור, frontend changes deferred.
- ZLR CCI delta (DLL vs Python): חישוב ה-CCI שלנו מחזיר -98.2, DLL סימן ZLR. ייתכן הבדל ב-seed/period/smoothing. לחקור.
- Near-miss calibration (K values): לא שונה — Michael מאשר.
