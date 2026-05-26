# MEGA PROMPT · Package 3b · Stream 3 · D-094 retrofit + Layer 4 wiring

**Authority chain (read in order, do not paraphrase):**
1. `docs/decisions/D-094_PKG3B_TRAIL_DECISIONS.md` (LOCKED) — §3.B.2 (5 services in scope) · §3.B.3 (wiring order) · §3.C (3-layer model)
2. `docs/handoff/MEGA_PROMPT_PKG3B_STREAM2.md` (predecessor) — TrailEngine class, BarRouter subscription, trade-context locks
3. `backend/v9/services/layer4/*.py` (5 service files · code is authoritative · LAYER 4 SERVICES ARE FORBIDDEN TO MODIFY)
4. `sc_study/v9_woodies_export.h` — Sierra DLL JSON contract for `woodies_5min` stream
5. Constitution V3 PART 5 B11–B17 (Layer 4 don't-give-back rules · NO additions beyond the 5 existing services in this stream)

**Predecessor commit (HEAD):** Stream 3b-2 landed at `23c8456` (TrailEngine class + persistence + concurrency · 29 tests · functional but D-094 gaps documented below).

**Revision v3 (2026-05-24 20:35 IL · Michael directive):** 6 Claude review fixes + 4 D-094 gap retrofits from Cursor G3 on `23c8456` —

Claude fixes (orthogonal to gap fixes):
(1) `close_trade(trade_id, reason)` 2-arg · `bar_ts=` kwargs removed from LOCK 5 + tcci EXIT + pre-flight grep added;
(2) test #46 fixture `"No_Trade"` → `"Nontrend"` (canonical per `targets_table.py:117,128`);
(3) `_update_mfe` uses `dict(trade.quality)` copy (matches 3b-2 `_save_state`);
(4) LOCK 5 cross_context logs ALL WARN rules (escalation gate stays narrow);
(5) pre-flight grep for `detect_from_buffer` return shape before tests #36/#37/#43;
(6) LOCK 1 `swi_tighten` counter-trend pairing reworded (LONG↔red · SHORT↔blue).

D-094 gap retrofits (Michael directive · "תקן הכל במגה פרומפט הרלוונטי"):
(Gap 11) `_append_cross_context` helper added (LOCK 6 · §0.5.A) — audit logging retrofit.
(Gap 2) `last_5_lows: List[float]` + `last_5_highs: List[float]` REPLACE `swing_high/swing_low` in TrailState (LOCK 7 · §0.6) — 5-bar HL/LH window per D-094 §3.B.
(Gap 5) `chandelier_engaged` + `t2_atr_at_engage` + `t2_bar_ts` added to TrailState · NEW `_engage_chandelier` method · ATR frozen at engage (LOCK 8 · §0.7) — D-094 Gap 5.
(Gap 14) `fetch_bars_since` constructor callable + NEW `_reconstruct_state_from_db` method · `_load_state` falls back on corrupt state (LOCK 9 · §0.8) — D-094 Gap 14.

**Phase A flag (REQUIRED in commit message verbatim):**
`Phase A mechanical · DEMO+ parametric calibration deferred to post-SHADOW per D-094 §4`

**Estimated CC time:** ~5-6 hours · ~500 LOC + ~30 tests (was ~2.5h for v2 · doubled due to D-094 retrofit)

---

## §0.5 · CRITICAL · 3b-2 D-094 retrofit (Cursor G3 finding 2026-05-24 20:15 IL · Michael directive 20:35 IL)

**The 3b-2 commit `23c8456` deviates from the mega prompt §2 inline spec.** CC wrote `trail_engine.py` from scratch rather than using the inline reference design. Four D-094 gap violations were identified in Cursor G3 and **MUST be retrofitted as part of Stream 3b-3** (Michael directive):

| Gap | Spec (D-094) | CC actual (`23c8456`) | Retrofit location |
|-----|------|-----------|----------------|
| Gap 2 (HL/LH window) | `last_5_lows: List[float]` 5-bar rolling window · stop=min(last 5) when full | `swing_low: float` all-time extreme · stop=swing_low immediately | LOCK 7 · §0.6 |
| Gap 5 (Frozen ATR) | `t2_atr_at_engage: Optional[float]` immutable · `_engage_chandelier` runs once | `state.atr14` recomputed every bar | LOCK 8 · §0.7 |
| Gap 11 (Audit log) | `_log_audit` / `_append_cross_context` helper writes to `trade.cross_context` | MISSING · TrailEngine writes nothing to cross_context | LOCK 6 · §0.5.A |
| Gap 14 (Restart) | `_reconstruct_state_from_db` queries `v9_bars_5min` since `t2_hit_ts` | Returns empty `TrailState()` silently on corrupt | LOCK 9 · §0.8 |

**3b-2 actual implementation details CC must work with:**
- TrailEngine constructor signature is `(trade_manager, bar_router, yesterday_bars=None, mode=None)`. 3b-3 will EXTEND to `(trade_manager, bar_router, yesterday_bars=None, mode=None, fetch_bars_since=None, woodies_provider=None)`.
- State persistence method is named `_save_state` (NOT `_persist_state`). 3b-3 wiring step 3.d calls `_save_state(trade, state)`.
- TrailState currently has fields: `swing_high`, `swing_low`, `bars_processed`, `last_bar_ts`, `atr14`, `time_stop_fired`, `trail_active`. 3b-3 will REPLACE the first two and ADD three new fields per LOCK 7+8 below.
- `_process_trade` body will be refactored per LOCK 7 (use 5-bar window) and LOCK 8 (frozen ATR via `_engage_chandelier`).

### §0.5.A · LOCK 6 · `_append_cross_context` helper (Gap 11 retrofit)

Add to TrailEngine class as the FIRST new method (insertion point: BEFORE `_apply_layer4`):

```python
import json   # add to module-level imports if not present

def _append_cross_context(self, trade, entry: Dict[str, Any]) -> None:
    """Append an audit entry to trade.cross_context (Gap 11 retrofit).

    Validates JSON-serializability via json.dumps(default=str) BEFORE
    mutation to fail loud-early (NOT at later DB commit). Reassigns
    trade.cross_context to a new list so SQLAlchemy detects the change.
    """
    json.dumps(entry, default=str)  # validate or raise NOW
    ctx = list(trade.cross_context) if isinstance(trade.cross_context, list) else []
    ctx.append(entry)
    trade.cross_context = ctx
```

All 4 cross_context call sites in §2 + §0 LOCK 5 use this helper. Also add 2 retrofit call sites in `_process_trade` (per LOCK 8): one for `chandelier_engaged` event, one for `trail_compute_discarded_sierra_fill` event.

---

## §0.6 · LOCK 7 · 5-bar HL/LH window (Gap 2 retrofit · D-094 §3.B)

**TrailState REPLACEMENT (NOT additive — 3b-2 fields `swing_high` + `swing_low` are REMOVED):**

```python
@dataclass
class TrailState:
    """Per-trade trail state · persisted to trade.quality['trail_state'].

    All fields are JSON-serialisable primitives so to_dict / from_dict
    provide a lossless round-trip.
    """
    # Pkg 3b-3 LOCK 7 · 5-bar window (REPLACES swing_high/swing_low)
    last_5_lows: List[float] = field(default_factory=list)   # LONG HL trail window
    last_5_highs: List[float] = field(default_factory=list)  # SHORT LH trail window

    # Pkg 3b-3 LOCK 8 · chandelier engage state (Gap 5 frozen ATR)
    max_high_since_t2: Optional[float] = None   # LONG chandelier anchor (peak since T2)
    min_low_since_t2: Optional[float] = None    # SHORT chandelier anchor (trough since T2)
    chandelier_engaged: bool = False            # True once _engage_chandelier ran
    t2_bar_ts: Optional[str] = None             # ISO ts of the T2-engage bar
    t2_atr_at_engage: Optional[float] = None    # frozen Wilder ATR-14 at engage (immutable)

    # Surviving 3b-2 fields
    bars_processed: int = 0
    last_bar_ts: Optional[str] = None
    time_stop_fired: bool = False
    trail_active: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TrailState":
        return cls(
            last_5_lows=list(d.get("last_5_lows") or []),
            last_5_highs=list(d.get("last_5_highs") or []),
            max_high_since_t2=d.get("max_high_since_t2"),
            min_low_since_t2=d.get("min_low_since_t2"),
            chandelier_engaged=bool(d.get("chandelier_engaged", False)),
            t2_bar_ts=d.get("t2_bar_ts"),
            t2_atr_at_engage=d.get("t2_atr_at_engage"),
            bars_processed=int(d.get("bars_processed", 0)),
            last_bar_ts=d.get("last_bar_ts"),
            time_stop_fired=bool(d.get("time_stop_fired", False)),
            trail_active=bool(d.get("trail_active", False)),
        )
```

**`_process_trade` HL/LH section REPLACEMENT** (post-T2 gate · between `state.trail_active = True` and the chandelier section):

```python
# Layer 1 (HL/LH 5-bar trail · D-094 Gap 2)
if direction == "LONG":
    window = (state.last_5_lows + [bar_low])[-5:]
    state.last_5_lows = window
    if len(window) >= 5:   # only fire when window is full
        self._move_stop_tighter_only(
            trade, min(window), direction, "hl_lh_trail_5bar", bar_ts,
        )
elif direction == "SHORT":
    window = (state.last_5_highs + [bar_high])[-5:]
    state.last_5_highs = window
    if len(window) >= 5:
        self._move_stop_tighter_only(
            trade, max(window), direction, "hl_lh_trail_5bar", bar_ts,
        )
```

**Reason string changed** from `"hl_lh_swing"` (3b-2) → `"hl_lh_trail_5bar"` (3b-3) to signal the spec-aligned semantics. Cross_context audit entries will reflect the new reason.

---

## §0.7 · LOCK 8 · Frozen ATR at engage (Gap 5 retrofit · D-094 §3.D)

**NEW method `_engage_chandelier`** (insertion point: BEFORE `_compute_chandelier_stop`):

```python
def _engage_chandelier(self, trade, bar: Dict[str, Any], state: TrailState) -> None:
    """First-time engagement at past-T2 bar · freezes Wilder ATR per Gap 5.

    Runs ONCE per trade (gated by state.chandelier_engaged). After engagement,
    state.t2_atr_at_engage is IMMUTABLE for the trade's lifetime.

    LIMITATION (intentional Phase A · NOT a bug):
    If T2 hits early in session (e.g., 10:00 ET · only 0-10 bars exist since
    session open), self._fetch_bars_since may return <14 bars. Wilder ATR-14
    requires >=14 bars and returns None. Therefore state.t2_atr_at_engage
    stays None and chandelier remains DORMANT for this trade's lifetime
    (HL/LH 5-bar trail still operates normally).
    """
    direction = (trade.direction or "").upper()
    state.chandelier_engaged = True
    state.t2_bar_ts = str(bar["ts"])
    if direction == "LONG":
        state.max_high_since_t2 = float(bar["high"])
    elif direction == "SHORT":
        state.min_low_since_t2 = float(bar["low"])

    try:
        if self._fetch_bars_since is not None and trade.t2_hit_ts is not None:
            today_bars = self._fetch_bars_since(trade.id, str(trade.t2_hit_ts))
        else:
            today_bars = list(self._today_bars)  # fall back to in-memory accumulator
        state.t2_atr_at_engage = compute_continuous_atr14(self._yesterday_bars, today_bars)
    except Exception as exc:
        logger.warning(
            "[TrailEngine] ATR freeze failed trade=%s: %r",
            getattr(trade, "id", "?"), exc,
        )
        state.t2_atr_at_engage = None

    self._append_cross_context(trade, {
        "event": "chandelier_engaged",
        "bar_ts": str(bar["ts"]),
        "frozen_atr": state.t2_atr_at_engage,
        "direction": direction,
    })
```

**`_process_trade` chandelier section REPLACEMENT** (post-T2 gate · the existing `atr = compute_continuous_atr14(...)` line goes AWAY · replaced with frozen-ATR engage-once logic):

```python
# Layer 2 (Chandelier · D-094 Gap 5 frozen ATR)
if state.chandelier_engaged or trade.t2_hit_ts is not None:
    if not state.chandelier_engaged:
        self._engage_chandelier(trade, bar, state)
    if state.t2_atr_at_engage is not None:
        # Update peak anchor BEFORE applying chandelier
        if direction == "LONG":
            if state.max_high_since_t2 is None:
                state.max_high_since_t2 = bar_high
            else:
                state.max_high_since_t2 = max(state.max_high_since_t2, bar_high)
        elif direction == "SHORT":
            if state.min_low_since_t2 is None:
                state.min_low_since_t2 = bar_low
            else:
                state.min_low_since_t2 = min(state.min_low_since_t2, bar_low)

        chandelier_stop = self._compute_chandelier_stop_v3(trade, state, direction)
        if chandelier_stop is not None:
            self._move_stop_tighter_only(
                trade, chandelier_stop, direction, "chandelier_atr14_frozen", bar_ts,
            )
```

**NEW `_compute_chandelier_stop_v3` method** (REPLACES the existing `_compute_chandelier_stop` from 3b-2):

```python
def _compute_chandelier_stop_v3(self, trade, state: TrailState, direction: str) -> Optional[float]:
    """Chandelier exit: anchor ± k * frozen_ATR (NOT live ATR · Gap 5)."""
    atr = state.t2_atr_at_engage   # FROZEN since engage · do not recompute
    if atr is None:
        return None
    quality = trade.quality if isinstance(trade.quality, dict) else {}
    pattern_name: Optional[str] = quality.get("pattern_name")
    family = _pattern_to_family(pattern_name) if pattern_name else None
    if family is None:
        return None  # explicit None — NO silent fallback (pre-LIVE protocol)
    multiplier = ATR_MULTIPLIERS.get(family)
    if multiplier is None:
        return None  # explicit None — NO silent fallback

    if direction == "LONG":
        anchor = state.max_high_since_t2
        if anchor is None:
            return None
        return anchor - multiplier * atr
    if direction == "SHORT":
        anchor = state.min_low_since_t2
        if anchor is None:
            return None
        return anchor + multiplier * atr
    return None
```

**Note on Pre-LIVE protocol alignment:** The 3b-2 `_compute_chandelier_stop` had a silent fallback `k = ATR_MULTIPLIERS.get(family, 1.5) if family else 1.5`. The v3 method REMOVES this silent fallback per pre-LIVE protocol §No silent failures. Unknown pattern family → no chandelier · explicit skip.

---

## §0.8 · LOCK 9 · DB reconstruct on restart (Gap 14 retrofit · D-094)

**Constructor signature EXTENSION:**

```python
def __init__(
    self,
    trade_manager,
    bar_router,
    yesterday_bars: Optional[List[Any]] = None,
    mode: Optional[str] = None,
    fetch_bars_since: Optional[Callable[[int, str], List[Any]]] = None,  # NEW
    woodies_provider: Optional[Callable[[], Optional[Dict]]] = None,     # NEW (LOCK 2)
) -> None:
    self._tm = trade_manager
    self._mode = mode
    self._yesterday_bars: List[Any] = list(yesterday_bars or [])
    self._today_bars: List[Any] = []
    self._fetch_bars_since = fetch_bars_since   # NEW
    self._woodies_provider = woodies_provider or (lambda: None)   # NEW
    bar_router.subscribe("5min", self.on_bar_close)
    logger.info("[TrailEngine] subscribed to 5min bars (mode=%s)", mode)
```

**NEW method `_reconstruct_state_from_db`** (insertion point: AFTER `_load_state`):

```python
def _reconstruct_state_from_db(self, trade) -> TrailState:
    """Rebuild TrailState from v9_bars_5min since t2_hit_ts (Gap 14 fallback).

    LIMITATION (intentional Phase A · NOT a bug):
    ATR is NOT recoverable from bars alone (Wilder ATR requires running the
    recursive formula from a known seed · the seed is lost on restart).
    We deliberately keep `state.chandelier_engaged = True` AND
    `state.t2_atr_at_engage = None`. Result:
      - _compute_chandelier_stop_v3 returns None (ATR=None)
      - chandelier remains DORMANT for this trade's lifetime
      - HL/LH 5-bar trail still operates (reconstructed from bars)
      - max_high_since_t2 / min_low_since_t2 ARE recovered from bars

    REJECTED ALTERNATIVE: setting chandelier_engaged=False here so
    _engage_chandelier runs on next bar to acquire fresh ATR. Would WORK
    for ATR but the engage method overwrites max_high_since_t2 with
    current bar high — DISCARDS the recovered peak anchor. That causes
    silent stop-loosening after restart · unacceptable for Phase A.
    DEFERRED to post-SHADOW if dormant chandelier proves material. The
    fix would be to preserve max via `is not None` check (NOT `or` due
    to 0.0 falsy trap) in engage.
    """
    state = TrailState()
    if trade.t2_hit_ts is None or self._fetch_bars_since is None:
        return state
    try:
        bars = self._fetch_bars_since(trade.id, str(trade.t2_hit_ts))
    except Exception:
        return state
    state.t2_bar_ts = str(trade.t2_hit_ts)
    state.chandelier_engaged = True   # accept dormant chandelier per limitation above
    direction = (trade.direction or "").upper()
    highs = [self._bar_attr(b, "high") for b in bars]
    lows = [self._bar_attr(b, "low") for b in bars]
    highs = [h for h in highs if h is not None]
    lows = [l for l in lows if l is not None]
    if direction == "LONG":
        state.max_high_since_t2 = max(highs) if highs else None
        state.last_5_lows = lows[-5:]
    elif direction == "SHORT":
        state.min_low_since_t2 = min(lows) if lows else None
        state.last_5_highs = highs[-5:]
    return state

@staticmethod
def _bar_attr(bar: Any, key: str) -> Optional[float]:
    """Read high/low from either attribute or dict shape."""
    if hasattr(bar, key):
        v = getattr(bar, key)
        return float(v) if v is not None else None
    if isinstance(bar, dict):
        v = bar.get(key, bar.get(key[0]))
        return float(v) if v is not None else None
    return None
```

**`_load_state` REPLACEMENT** (REPLACES the 3b-2 version):

```python
def _load_state(self, trade) -> TrailState:
    """Load TrailState from trade.quality['trail_state']; reconstruct on corrupt."""
    quality = trade.quality if isinstance(trade.quality, dict) else {}
    raw = quality.get("trail_state")
    if raw is None:
        return TrailState()
    try:
        return TrailState.from_dict(raw)
    except Exception as exc:
        self._append_cross_context(trade, {
            "event": "trail_state_load_failed",
            "exc": repr(exc),
        })
        return self._reconstruct_state_from_db(trade)
```

**Production wiring** (in `app.py` or wherever TrailEngine is instantiated · CC do NOT modify the wiring file · just document the expected pattern):

```python
def fetch_bars_since(trade_id: int, since_ts_iso: str) -> List[Dict]:
    """Implementation hint — actual wiring is out of scope for 3b-3."""
    from backend.v9.db.session import SessionLocal
    from backend.v9.db.models.bars_5min import V9Bar5Min
    with SessionLocal() as db:
        rows = db.query(V9Bar5Min).filter(
            V9Bar5Min.ts > datetime.fromisoformat(since_ts_iso.replace("Z","+00:00"))
        ).order_by(V9Bar5Min.ts.asc()).all()
        return [{"high": r.high, "low": r.low, "close": r.close, "ts": r.ts.isoformat()} for r in rows]

trail_engine = TrailEngine(
    trade_manager=tm,
    bar_router=br,
    yesterday_bars=yesterday_bars_loaded,
    mode="shadow",
    fetch_bars_since=fetch_bars_since,
    woodies_provider=woodies_system.get_layer4_context,
)
```

---

---

## §0 · Five Cursor-Michael LOCKS that resolve gap analysis

The audit of the 5 Layer 4 services revealed 6 data-flow gaps between the
service `evaluate()` signatures and what TrailEngine has direct access to.
The locks below are AUTHORITATIVE for Stream 3b-3. They were resolved on
2026-05-24 with Michael's explicit lock.

### LOCK 1 · Sierra is the data source for SWI + CCI history (F2 + F3)

The Sierra DLL `v9_woodies_export.h` already exports per `woodies_5min`
bar (verbatim from the DLL JSON · confirmed lines 437–559):

- `cci_14` (Study ID:4 SG0 · CCI-14 native)
- `cci_6_tcci` (Study ID:10 SG0 · TCCI native)
- `swi_value` (Study ID:6 SG5 · Sidewinder native)
- `trend_state` (Study ID:1 · "RED"/"YELLOW"/"BLUE"/"GRAY")
- A `history[]` array of the last N bars with the same fields each

Therefore:

- **F2 SWI** is sourced verbatim from Sierra. The Layer 4 service
  `swi_tighten.evaluate(trade, swi)` expects `swi = {value, color}`.
  Build it as:

  ```python
  swi = {
      "value": float(last_woodies_bar.swi_value or 0.0),
      "color": (last_woodies_bar.trend_state or "GRAY").lower(),
  }
  ```

  **`swi_tighten` counter-trend directional pairing (per Sierra's
  Sidewinder classification · service handles internally):**
  - LONG trade  ↔ tightens when color == `"red"`  (counter-trend down)
  - SHORT trade ↔ tightens when color == `"blue"` (counter-trend up)
  - Either direction skips when `"yellow"` (neutral) or `"gray"` (no data)

  Sierra's `trend_state` uses uppercase "RED"/"BLUE"/"YELLOW"/"GRAY"
  (lowercased → "red"/"blue"/etc.). The service's `evaluate()` reads
  trade.direction internally and applies the pairing — TrailEngine just
  passes `swi = {value, color}` unmodified. No threshold logic in
  TrailEngine — Sierra's classification is canonical.

- **F3 CCI history** is sourced verbatim from Sierra. The Layer 4 service
  `cci_flat_tighten.evaluate(trade, cci_history)` expects a list of
  floats, most recent last. Build it as:

  ```python
  cci_history = [float(b.cci_14 or 0.0) for b in bar_buffer[-3:]]
  ```

  Service requires `len(history) >= 3` (its `CCI_FLAT_BARS_REQUIRED`).
  If buffer < 3 bars · service returns None · TrailEngine does nothing.

NO new Sierra DLL exports. NO change to `sc_study/`. NO bridge changes.

### LOCK 2 · WoodiesSystem provides a single context method (provider callable pattern)

The `woodies_5min` stream is consumed by `WoodiesSystem` (S4), not by
`BarRouter "5min"` (which TrailEngine subscribes to). Therefore TrailEngine
needs a way to obtain the latest Woodies snapshot at the time it is
processing a "5min" BarRouter event.

**LOCKED — Option A · provider callable** (parallel to `fetch_bars` from
Stream 3b-2):

1. Add ONE method to `backend/v9/systems/woodies/woodies_system.py`:

   ```python
   def get_layer4_context(self) -> Optional[Dict]:
       """Snapshot needed by TrailEngine Layer 4 services (Pkg 3b-3).

       Returns None if buffer empty (TrailEngine then skips Layer 4 entirely).
       Otherwise returns a dict with:
         - swi: {value: float, color: str (lowercased trend_state)}
         - cci_history: list of last 3 cci_14 floats (most recent last)
         - direction_change_event: output of W3-beta
           direction_change_detector.detect_from_buffer (None if no cross)
         - current_bar_ts: float ts of the most recent buffered bar

       All fields are read from self._bar_buffer (WoodiesBar list).
       No computation — pure snapshot.
       """
       if not self._bar_buffer:
           return None
       last = self._bar_buffer[-1]
       cci_hist = [float(b.cci_14 or 0.0) for b in self._bar_buffer[-3:]]
       try:
           dc_event = detect_direction_change(self._bar_buffer)
       except Exception:
           logger.exception("[WoodiesSystem] direction_change detect failed")
           dc_event = None
       return {
           "swi": {
               "value": float(last.swi_value or 0.0),
               "color": (last.trend_state or "GRAY").lower(),
           },
           "cci_history": cci_hist,
           "direction_change_event": dc_event,
           "current_bar_ts": float(last.ts),
       }
   ```

   Note: `detect_direction_change` is the existing
   `from backend.v9.systems.woodies.direction_change_detector import detect_from_buffer as detect_direction_change`
   import that already exists at `woodies_system.py:19`. No new imports
   needed.

2. TrailEngine constructor accepts a new keyword arg `woodies_provider`:

   ```python
   def __init__(
       self,
       trade_manager,
       bar_router,
       fetch_bars,
       fetch_bars_since,
       woodies_provider: Optional[Callable[[], Optional[Dict]]] = None,
   ) -> None:
       ...
       self._woodies_provider = woodies_provider or (lambda: None)
   ```

   Production wiring (in `app.py` or wherever TrailEngine is instantiated):

   ```python
   trail_engine = TrailEngine(
       trade_manager=tm,
       bar_router=br,
       fetch_bars=fetch_bars_impl,
       fetch_bars_since=fetch_bars_since_impl,
       woodies_provider=woodies_system.get_layer4_context,
   )
   ```

3. When `woodies_provider() is None` (buffer empty or system not ready):
   TrailEngine SKIPS the Woodies-specific Layer 4 services (cci_flat,
   tcci_cross, swi) but STILL runs the universal services (mfe_peak,
   day_type_targets_verify). This matches D-094 §3.B.3 ordering — only
   #2/#3 (Woodies-specific S4 trades) gate on the snapshot.

NO Redis. NO new BarRouter topic. NO change to `WoodiesSystem.process_bar`.

### LOCK 3 · Trade-dict adapter (key-name normalization)

The 5 Layer 4 services use INCONSISTENT key naming on the `trade` dict
argument (this is forbidden to modify per §5.B). The dict TrailEngine
passes MUST contain BOTH naming variants to satisfy every service:

| Key in adapted dict | Required by | Source on `V9Trade` |
|---|---|---|
| `entry` | `mfe_peak_tighten` | `trade.entry_price` |
| `stop` | `mfe_peak_tighten` | `trade.stop` |
| `stop_price` | `cci_flat_tighten`, `swi_tighten` | `trade.stop` (same value as `stop`) |
| `t1` | `day_type_targets_verify` (indirect via `get_targets`) | `trade.t1` |
| `t2` | `mfe_peak_tighten`, `day_type_targets_verify` | `trade.t2` |
| `t3` | `day_type_targets_verify` | `trade.t3` |
| `current_price` | `mfe_peak_tighten`, `cci_flat_tighten`, `swi_tighten` | bar payload `close` (NOT on `V9Trade`) |
| `mfe` | `mfe_peak_tighten` | `trade.quality["mfe_high"]` (LONG) OR `trade.quality["mfe_low"]` (SHORT) — see LOCK 4 |
| `direction` | ALL 5 services | `trade.direction` |
| `day_type_at_entry` | `day_type_targets_verify` | `trade.quality["day_type"]` (written by accept_setup post-Stream 3b-2) |
| `time_stop_minutes` | `day_type_targets_verify` | `trade.quality.get("time_stop_minutes")` if previously cached, else None |

**LOCKED · adapter helper on TrailEngine:**

```python
def _adapt_trade_for_layer4(self, trade, bar_close: float) -> Dict:
    """Build the dict shape Layer 4 services expect.

    NEVER mutate the V9Trade object. Always copy out. Callers must NOT
    use this dict for persistence — it is read-only for service eval.
    """
    quality = trade.quality or {}
    direction = trade.direction
    mfe_key = "mfe_high" if direction == "LONG" else "mfe_low"
    return {
        "id": trade.id,
        "direction": direction,
        "entry": float(trade.entry_price),
        "stop": float(trade.stop),
        "stop_price": float(trade.stop),
        "t1": float(trade.t1) if trade.t1 is not None else None,
        "t2": float(trade.t2) if trade.t2 is not None else None,
        "t3": float(trade.t3) if trade.t3 is not None else None,
        "current_price": float(bar_close),
        "mfe": quality.get(mfe_key),
        "day_type_at_entry": quality.get("day_type"),
        "time_stop_minutes": quality.get("time_stop_minutes"),
    }
```

### LOCK 4 · MFE tracking lives in `trade.quality` (the F1 gap)

Sierra does not know about our trades. MFE (maximum favorable excursion)
is a per-trade state variable updated by TrailEngine on every "5min" bar.

**LOCKED — store in `trade.quality` JSON (consistent with `trail_state`
pattern from Stream 3b-2):**

```python
def _update_mfe(self, trade, bar: Dict) -> None:
    """Update per-trade MFE on every bar (Pkg 3b-3 LOCK 4).

    Called from on_bar_close BEFORE Layer 4 evaluation. Mutates a
    DEFENSIVE COPY of trade.quality (NEVER the original ORM-tracked
    dict) — pattern matches Stream 3b-2 `_save_state` to ensure
    SQLAlchemy detects the mutation on reassignment. The existing
    update_stop_with_audit or trail_state persist will then flush.
    """
    # Force dict copy so SQLAlchemy sees a NEW dict on reassign
    # (same pattern as Stream 3b-2 _save_state · NOT a shared mutable ref)
    quality = dict(trade.quality) if isinstance(trade.quality, dict) else {}
    direction = trade.direction
    if direction == "LONG":
        prev = quality.get("mfe_high")
        cur = float(bar["high"])
        if prev is None or cur > prev:
            quality["mfe_high"] = cur
    elif direction == "SHORT":
        prev = quality.get("mfe_low")
        cur = float(bar["low"])
        if prev is None or cur < prev:
            quality["mfe_low"] = cur
    trade.quality = quality
```

Initialization: `accept_setup` already writes `trade.quality["entry_price"]`
(Stream 3b-1) but does NOT write `mfe_high/mfe_low`. The first call to
`_update_mfe` performs the seed (the `None` branch). NO accept_setup change
needed for MFE.

Persistence happens implicitly: every call that ultimately reaches
`tm.update_stop_with_audit` flushes the whole `trade` row (SQLAlchemy
session.commit() on `trade.quality` JSON · same path as `trail_state`).
If no Layer 4 service fires AND no Stream 2 trail logic fires, the MFE
update is held in the SQLAlchemy session and committed on the next event
that triggers a flush. Acceptable for Phase A — restart recovery will
re-derive MFE from the bar history (NOT in scope for this stream — see
§7).

### LOCK 5 · `day_type_targets_verify` escalates WARN → EXIT for no-trade reclassification

D-094 §3.B.3 marks `day_type_targets_verify` as "most dangerous · can
close trades mid-flight". The service ITSELF (forbidden to modify)
returns `action="WARN"` even when the day re-classified to NO_TRADE
(see lines 55–58, 67–76 of `day_type_targets_verify.py`).

**LOCKED — escalation lives in TrailEngine (NOT in the service):**

```python
def _handle_day_type_action(self, trade, action: Dict, bar_ts: str) -> None:
    """D-094 escalation: WARN → CLOSE_ALL when current_day_type is NO_TRADE.

    The Layer 4 service returns WARN for ALL day-type mismatches. We
    escalate ONLY when reclassification is to a no_trade day type. The
    decision uses get_targets() to confirm no_trade (same source the
    service used — single source of truth).
    """
    if action.get("action") != "WARN":
        return

    # Pkg 3b-3 v2 · log ALL WARN rules to cross_context (not only
    # DAY_TYPE_TARGETS_MISMATCH). Escalation gate stays narrow —
    # only DAY_TYPE_TARGETS_MISMATCH + no_trade reclass triggers close_trade.
    rule = action.get("rule", "UNKNOWN_WARN")
    from backend.v9.systems.day_type.targets_table import get_targets
    current_day_type = action.get("current_day_type")
    current_targets = get_targets(current_day_type) if current_day_type else None

    # Default: log WARN to cross_context · no close
    if rule != "DAY_TYPE_TARGETS_MISMATCH" or not current_targets or not current_targets.get("no_trade"):
        self._append_cross_context(trade, {
            "event": "layer4_warn",
            "rule": rule,
            "current_day_type": current_day_type,
            "bar_ts": bar_ts,
            "notes": action.get("reasoning_notes"),
        })
        return

    # Escalation: close the trade
    self._append_cross_context(trade, {
        "event": "layer4_exit",
        "rule": "DAY_TYPE_NO_TRADE_RECLASS",
        "current_day_type": current_day_type,
        "bar_ts": bar_ts,
        "notes": action.get("reasoning_notes"),
    })
    try:
        # close_trade signature is (trade_id, reason) — 2-arg only.
        # bar_ts is already captured in the cross_context entry above.
        self.tm.close_trade(trade.id, "DAY_TYPE_NO_TRADE_RECLASS")
    except Exception:
        logger.exception(
            "[TrailEngine] close_trade failed during day_type escalation trade_id=%s",
            trade.id,
        )
```

**Pre-flight verification (CC must run before implementing LOCK 5):**

```bash
grep -nE '^\s+def close_trade' backend/v9/services/trade_manager/manager.py
```

Expected output: `def close_trade(self, trade_id: int, reason: str) -> None:` (2-arg).
If the signature has changed and accepts kwargs, restore the `bar_ts=bar_ts`
kwarg pattern. If it remains 2-arg, the positional call above is correct.

The service is unchanged. The escalation policy lives where it belongs
(the orchestrator). Tests #45–#46 verify both branches (mismatch-only
WARN vs no_trade-escalation EXIT).

---

## §1 · SCOPE

### WRITE NEW (0 files)

NONE. Stream 3b-3 modifies existing files only.

### MODIFY EXISTING (3 files · D-094 retrofit + Layer 4 wiring)

| Path | Edit | Lines net |
|------|------|-----------|
| `backend/v9/systems/woodies/woodies_system.py` | Add `get_layer4_context` method per LOCK 2 | +30 |
| `backend/v9/services/trail_engine.py` | **REFACTOR + EXTEND** · TrailState dataclass replaces `swing_high/swing_low` with 5-bar window + chandelier fields per LOCK 7/8 · constructor extended with `fetch_bars_since` + `woodies_provider` per LOCK 9/2 · `_process_trade` HL/LH and chandelier sections rewritten per LOCK 7/8 · NEW methods: `_append_cross_context` (LOCK 6) · `_engage_chandelier` (LOCK 8) · `_compute_chandelier_stop_v3` (LOCK 8 · REPLACES 3b-2's `_compute_chandelier_stop`) · `_reconstruct_state_from_db` + `_bar_attr` (LOCK 9) · `_load_state` REPLACED to use reconstruct fallback (LOCK 9) · `_apply_layer4` + `_adapt_trade_for_layer4` + `_update_mfe` + `_handle_day_type_action` + `_apply_tightest_stop` + `_fetch_current_day_type` (Layer 4 wiring) | +~350 / -~30 = net +~320 |
| `tests/v9/services/test_trail_engine.py` | **UPDATE 11 existing tests + APPEND 30 new tests** · existing 3b-2 tests that reference `swing_high/swing_low` must migrate to `last_5_lows/last_5_highs` semantics (see §3.5) · existing chandelier tests that mock live ATR must migrate to frozen-ATR semantics (see §3.5) · 30 new tests cover Gap 2/5/11/14 retrofits + Layer 4 wiring (see §3.6) | net +~600 |

### FORBIDDEN (do NOT touch)

- ❌ `backend/v9/services/layer4/*.py` — **all 5 service files are FROZEN**. No edits to evaluate() signatures, no edits to docstrings, no test-only changes. If a service needs different inputs · TrailEngine adapts in `_adapt_trade_for_layer4` or `_apply_layer4`. NO EXCEPTIONS.
- ❌ `backend/v9/db/models/trades.py` — no schema migration (consistent with Stream 3b-2 LOCK 2)
- ❌ `backend/v9/systems/five_min/adaptive_stop.py` (Pkg 1 untouchable per D-094 §3.D Option 3)
- ❌ `backend/v9/systems/five_min/atr_caps.py`, `constants.py` (Pkg 3b-1 shipped)
- ❌ `backend/v9/systems/day_type/targets_table.py` (Pkg 3a · Pkg 3b-1 do NOT regress)
- ❌ `backend/v9/systems/woodies/direction_change_detector.py` (W3-β · used as-is)
- ❌ `backend/v9/systems/woodies/schemas.py` (`WoodiesBar` schema · used as-is)
- ❌ Any DLL · `sc_study/` · `bridge/` · `frontend/`
- ❌ Any change to BarRouter · EventDispatcher · TradingGateway
- ❌ Stream 3b-2 tests in `test_trail_engine.py` (extend the file · do not modify existing tests)
- ❌ Any test in `tests/v9/api/`, `tests/v9/bridge/`, `tests/v9/gateway/`, `tests/v9/frontend/`

---

## §2 · D-094 §3.B.3 wiring order (exact)

```text
on_bar_close(event):
  1. bar = _normalize_bar(event)
  2. trades = tm.list_trades_past_t1()
  3. for trade in trades (failure-isolated per-trade try/except):
       a. _update_mfe(trade, bar)                       # LOCK 4 · always
       b. Stream 3b-2 trail logic (existing _process_trade body)
       c. _apply_layer4(trade, bar, event.ts)           # NEW (this stream)
       d. _save_state(trade, state)                     # 3b-2 actual method name (NOT _persist_state)
```

`_apply_layer4` runs the 5 services in this exact order (per D-094 §3.B.3
LOCK):

| # | Service | Type | Stops on first match? |
|---|---|---|---|
| 1 | `mfe_peak_tighten` | Universal · all trades | No · continue to 2 |
| 2 | `cci_flat_tighten` | Woodies-only (S4) · skipped if `woodies_ctx is None` | No · continue to 3 |
| 3 | `tcci_cross_exit` | Woodies-only (S4) · skipped if `woodies_ctx is None` | **YES** — if returns EXIT, close trade and RETURN |
| 4 | `swi_tighten` | Universal · runs even if S2 trade · uses Woodies snapshot if available | No · continue to 5 |
| 5 | `day_type_targets_verify` | Universal · queries day_type via callable | **YES** — if escalated to EXIT (LOCK 5), close trade and RETURN |

TIGHTEN_STOP actions accumulate · the TIGHTEST stop wins (per
D-094 Gap 13). Implementation:

```python
def _apply_layer4(self, trade, bar: Dict, bar_ts: str) -> None:
    """Run Layer 4 services in D-094 §3.B.3 order.

    Tightens accumulate (tightest wins · Gap 13). EXIT actions short-circuit.
    Woodies-specific services skip cleanly if woodies_provider returns None.
    """
    from backend.v9.services.layer4 import (
        mfe_peak_tighten,
        cci_flat_tighten,
        tcci_cross_exit,
        swi_tighten,
        day_type_targets_verify,
    )

    adapted = self._adapt_trade_for_layer4(trade, bar["close"])
    woodies_ctx = self._woodies_provider() or {}
    candidate_stops: List[Dict] = []  # collected TIGHTEN actions

    # 1. mfe_peak_tighten (universal)
    try:
        act = mfe_peak_tighten.evaluate(adapted)
        if act:
            candidate_stops.append(act)
    except Exception:
        logger.exception("[TrailEngine] mfe_peak_tighten failed trade_id=%s", trade.id)

    # 2. cci_flat_tighten (S4 only · needs cci_history)
    cci_history = woodies_ctx.get("cci_history") if woodies_ctx else None
    if cci_history and len(cci_history) >= 3:
        try:
            act = cci_flat_tighten.evaluate(adapted, cci_history)
            if act:
                candidate_stops.append(act)
        except Exception:
            logger.exception("[TrailEngine] cci_flat_tighten failed trade_id=%s", trade.id)

    # 3. tcci_cross_exit (S4 only · EXIT short-circuits)
    dc_event = woodies_ctx.get("direction_change_event")
    if dc_event:
        try:
            act = tcci_cross_exit.evaluate(adapted, dc_event)
            if act and act.get("action") == "EXIT":
                self._append_cross_context(trade, {
                    "event": "layer4_exit",
                    "rule": "TCCI_CROSS",
                    "bar_ts": bar_ts,
                    "notes": act.get("reasoning_notes"),
                })
                # close_trade signature is (trade_id, reason) — 2-arg only.
                # bar_ts already captured in cross_context entry above.
                self.tm.close_trade(trade.id, "TCCI_CROSS_AGAINST_TRADE")
                return
        except Exception:
            logger.exception("[TrailEngine] tcci_cross_exit failed trade_id=%s", trade.id)

    # 4. swi_tighten (universal · skip cleanly if no woodies)
    swi = woodies_ctx.get("swi")
    if swi and swi.get("value") is not None:
        try:
            act = swi_tighten.evaluate(adapted, swi)
            if act:
                candidate_stops.append(act)
        except Exception:
            logger.exception("[TrailEngine] swi_tighten failed trade_id=%s", trade.id)

    # Apply TIGHTEST candidate stop (Gap 13 · tightens only)
    if candidate_stops:
        self._apply_tightest_stop(trade, candidate_stops, bar_ts)

    # 5. day_type_targets_verify (universal · LAST per §3.B.3)
    current_day_type = self._fetch_current_day_type()
    if current_day_type:
        try:
            act = day_type_targets_verify.evaluate(adapted, current_day_type)
            if act:
                self._handle_day_type_action(trade, act, bar_ts)
        except Exception:
            logger.exception("[TrailEngine] day_type_targets_verify failed trade_id=%s", trade.id)
```

Helper `_apply_tightest_stop` (Gap 13):

```python
def _apply_tightest_stop(self, trade, candidates: List[Dict], bar_ts: str) -> None:
    """Apply the tightest new_stop from accumulated TIGHTEN actions.

    LONG: highest new_stop wins (closest to entry below price).
    SHORT: lowest new_stop wins (closest to entry above price).

    Defers to update_stop_with_audit for the actual move (which checks
    is_fill_locked + 'tighter-only' invariant per Stream 3b-2).
    """
    if not candidates:
        return
    direction = trade.direction
    if direction == "LONG":
        winner = max(candidates, key=lambda a: a["new_stop"])
    else:
        winner = min(candidates, key=lambda a: a["new_stop"])
    try:
        self.tm.update_stop_with_audit(
            trade_id=trade.id,
            new_stop=float(winner["new_stop"]),
            reason=f"LAYER4_{winner['rule']}",
            bar_ts=bar_ts,
        )
        self._append_cross_context(trade, {
            "event": "layer4_tighten",
            "rule": winner["rule"],
            "new_stop": winner["new_stop"],
            "old_stop": winner.get("old_stop"),
            "bar_ts": bar_ts,
            "notes": winner.get("reasoning_notes"),
        })
    except Exception:
        logger.exception(
            "[TrailEngine] update_stop_with_audit failed trade_id=%s rule=%s",
            trade.id,
            winner.get("rule"),
        )
```

Helper `_fetch_current_day_type`:

```python
def _fetch_current_day_type(self) -> Optional[str]:
    """Query S1 for current day type classification.

    Returns None on any error · day_type_targets_verify gracefully
    no-ops with None.
    """
    try:
        from backend.v9.systems.day_type.day_type_state import get_current_day_type
        return get_current_day_type()
    except Exception:
        logger.debug("[TrailEngine] day_type state unavailable")
        return None
```

**NOTE for CC:** If `backend.v9.systems.day_type.day_type_state` does not
expose `get_current_day_type` · STOP and ask Cursor before guessing. Do
NOT call the HTTP API from the engine.

---

## §3 · 20 golden tests (`tests/v9/services/test_trail_engine.py` · APPEND)

Each test follows the existing 3b-2 fixture pattern (MagicMock TradeManager
+ in-memory BarRouter substitute + `make_bar(ts, h, l, c)` helper). Add a
new fixture `make_woodies_ctx(swi_color, swi_value, cci_history, dc_event)`.

**Pre-flight verification (CC must run BEFORE writing tests #36/#37/#43):**

```bash
grep -nE 'def (detect|detect_from_buffer)' backend/v9/systems/woodies/direction_change_detector.py
grep -nE 'return\s+\{' backend/v9/systems/woodies/direction_change_detector.py
```

Expected `detect()` return shape (verified 2026-05-24):
```python
{
    "type": "DIRECTION_CHANGE",
    "direction": "BULLISH" | "BEARISH",
    "cci_14": float,
    "tcci": float,
    "prev_cci_14": float,
    "prev_tcci": float,
    "reasoning_notes": str,
}
```

`tcci_cross_exit.evaluate()` ONLY reads `.get("type")` + `.get("direction")` +
`.get("reasoning_notes")` — tests #36/#37/#43 can pass minimum-fixture dicts.
But if `detect()` signature has changed (e.g., added required fields), CC
MUST update fixtures to match before writing tests. If the return shape no
longer includes `"direction"` or `"type"` keys · STOP and report.

### Layer 4 Service evaluation correctness (10 tests)

| # | Test name | Setup | Expected |
|---|---|---|---|
| 30 | `test_mfe_peak_tighten_fires_at_80pct_long` | LONG entry=100, t2=110, mfe=108 (80%), stop=98, bar.close=107 | `update_stop_with_audit` called with `new_stop=104.0` (entry+50% of mfe_distance=8 → +4) |
| 31 | `test_mfe_peak_tighten_does_not_loosen` | LONG entry=100, t2=110, mfe=104, stop=103 (already tight) | `update_stop_with_audit` NOT called |
| 32 | `test_mfe_peak_tighten_short_direction` | SHORT entry=100, t2=90, mfe=92 (80%), stop=102 | `update_stop_with_audit` called with `new_stop=96.0` (entry-50% of 8 → -4) |
| 33 | `test_cci_flat_tighten_three_flat_bars` | LONG, cci_history=[50, 53, 48], stop=98, close=100 | TIGHTEN by 20% → `new_stop = 98 + 0.2*(100-98) = 98.4` |
| 34 | `test_cci_flat_tighten_skips_when_not_flat` | LONG, cci_history=[50, 80, 110] | no tighten (range > 10 between consecutive) |
| 35 | `test_cci_flat_tighten_skips_when_no_woodies_ctx` | LONG, woodies_provider returns None | service not even called (verify via MagicMock.assert_not_called or skip-branch coverage) |
| 36 | `test_tcci_cross_exit_long_with_bearish_cross_closes_trade` | LONG trade, dc_event=`{type: DIRECTION_CHANGE, direction: BEARISH}` | `tm.close_trade(reason="TCCI_CROSS_AGAINST_TRADE")` called · `_apply_layer4` returns (no further services run) |
| 37 | `test_tcci_cross_exit_long_with_bullish_cross_noop` | LONG trade, dc_event direction=BULLISH (with-trade) | no close · subsequent services still run |
| 38 | `test_swi_tighten_fires_when_red` | LONG, swi=`{value: -25, color: "red"}`, stop=98, close=100 | TIGHTEN 25% → `new_stop = 98 + 0.25*2 = 98.5` |
| 39 | `test_swi_tighten_skips_when_blue` | LONG, swi=`{value: 30, color: "blue"}` | no tighten |

### Wiring order + Gap 13 (5 tests)

| # | Test name | Setup | Expected |
|---|---|---|---|
| 40 | `test_layer4_runs_services_in_d094_order` | Spy all 5 evaluate fns via MagicMock side_effect=lambda *a,**k: None | call_order recorded == [`mfe_peak`, `cci_flat`, `tcci_cross`, `swi`, `day_type_targets_verify`] |
| 41 | `test_tightest_stop_wins_long` | LONG, mfe_peak suggests new_stop=103, swi suggests new_stop=104 | only one `update_stop_with_audit` call · new_stop=104 (higher = tighter for LONG) |
| 42 | `test_tightest_stop_wins_short` | SHORT, mfe_peak suggests new_stop=97, swi suggests new_stop=96 | new_stop=96 (lower = tighter for SHORT) |
| 43 | `test_tcci_exit_short_circuits_subsequent_services` | LONG, tcci_cross EXIT fires · swi suggests TIGHTEN_STOP | only `close_trade` called · `update_stop_with_audit` NOT called · day_type service NOT called |
| 44 | `test_layer4_skips_woodies_services_when_provider_returns_none` | woodies_provider returns None | only `mfe_peak` and `day_type_targets_verify` evaluated (verify via MagicMock spy) |

### day_type escalation (LOCK 5) + MFE tracking (LOCK 4) (5 tests)

| # | Test name | Setup | Expected |
|---|---|---|---|
| 45 | `test_day_type_warn_only_logs_to_cross_context` | day re-classifies Normal → Trend_DD (both tradable) · service returns WARN | `cross_context` appended event=layer4_warn · NO `close_trade` |
| 46 | `test_day_type_escalates_to_close_when_no_trade` | day re-classifies Normal → `"Nontrend"` (canonical day-type key per `targets_table.py:117,128`) · `get_targets("Nontrend").no_trade == True` | `close_trade(trade_id, "DAY_TYPE_NO_TRADE_RECLASS")` called · cross_context appended |
| 47 | `test_mfe_long_updates_on_higher_bar_high` | LONG, quality.mfe_high=104, bar.high=107 | `quality["mfe_high"] == 107.0` after on_bar_close |
| 48 | `test_mfe_long_does_not_regress_on_lower_high` | LONG, quality.mfe_high=110, bar.high=108 | `quality["mfe_high"] == 110.0` (unchanged) |
| 49 | `test_mfe_short_updates_on_lower_bar_low` | SHORT, quality.mfe_low=92, bar.low=89 | `quality["mfe_low"] == 89.0` after on_bar_close |

All 20 tests use the same `MagicMock(spec=TradeManager)` from Stream 3b-2.
No DB writes in tests. No real Sierra payloads — `make_woodies_ctx` returns
plain dicts.

---

## §3.5 · Existing 3b-2 tests · MIGRATION required (D-094 retrofit consequences)

The 29 tests in `test_trail_engine.py` from commit `23c8456` test CC's
3b-2 actual implementation. The §0.6 + §0.7 + §0.9 refactors break ~15
of them. CC must update these tests as part of Stream 3b-3 work.

**Migration principles:**

1. Any test that references `state.swing_high` or `state.swing_low` directly
   must be migrated to `state.last_5_highs` (SHORT) or `state.last_5_lows`
   (LONG). The stop now equals `min(last_5_lows)` only when `len(last_5_lows) >= 5`.

2. Any test that expects `update_stop_with_audit` to fire on the FIRST
   bar after T2 must seed a `trail_state` with a pre-filled 4-element
   window (so the new bar makes the 5th) OR change the assertion to
   "stop did NOT move (window < 5)".

3. Any test that uses `patch("compute_continuous_atr14")` to inject a
   live ATR per bar must instead set `state.t2_atr_at_engage = X` in the
   seeded `trail_state` (frozen ATR) AND set `state.chandelier_engaged=True`
   to skip the engage step.

4. Any test that expects `state.atr14` field must migrate to checking
   `state.t2_atr_at_engage` (the new field name · frozen semantics).

5. Reason string `"hl_lh_swing"` (3b-2) → `"hl_lh_trail_5bar"` (3b-3 spec).
   Reason string `"chandelier_atr14"` (3b-2) → `"chandelier_atr14_frozen"` (3b-3).

**Per-test migration matrix** (CC: read the existing test · apply the
relevant migration · keep the test name unless §3.6 says otherwise):

| Existing 3b-2 test | Migration action | Expected fix |
|---|---|---|
| `test_long_swing_stop_follows_bar_low` | RENAME → `test_hl_lh_long_5_bar_window_min_fires` · seed `last_5_lows=[5252,5251,5250,5249]`, new bar low=5248 → window=[5251,5250,5249,5248] len<5 · NO move. Seed with 4 entries OR add a 5th in test. | Add full 5-bar seed → fires once window full |
| `test_long_swing_stop_does_not_widen` | RENAME → `test_hl_lh_long_never_widens` · seed full window with min above current stop → no move | Same semantics · cleaner |
| `test_short_swing_stop_follows_bar_high` | RENAME → `test_hl_lh_short_5_bar_window_max_fires` · seed `last_5_highs` with 4 entries · 5th bar fires | Same as LONG-side |
| `test_short_swing_stop_does_not_widen` | RENAME → `test_hl_lh_short_never_widens` | Same |
| `test_swing_stop_skips_before_t2` | KEEP NAME · already valid (t2_hit_ts gate is unchanged) | No change |
| `test_swing_high_accumulated_across_bars` | DELETE this test (accumulating-max semantics removed) · replace with `test_hl_lh_window_slides_drops_oldest` per §3.6 | New behavior covered in §3.6 |
| `test_chandelier_long_uses_swing_high_minus_k_atr` | MIGRATE · seed `t2_atr_at_engage=4.0`, `max_high_since_t2=5265`, `chandelier_engaged=True` · stop computed from frozen ATR (NOT patched live ATR) | Frozen-ATR semantics |
| `test_chandelier_short_uses_swing_low_plus_k_atr` | MIGRATE · symmetric · seed `min_low_since_t2`, `t2_atr_at_engage`, `chandelier_engaged=True` | Same |
| `test_chandelier_uses_initiative_multiplier` | MIGRATE · same as above · seed frozen ATR | Same |
| `test_chandelier_uses_reactive_multiplier` | MIGRATE · same | Same |
| `test_chandelier_no_op_when_atr_none` | MIGRATE · seed `t2_atr_at_engage=None`, `chandelier_engaged=True` · expect NO move | Frozen-ATR=None path |
| `test_chandelier_does_not_widen_stop` | MIGRATE · seed frozen state, expect not-widening | Same |
| `test_time_stop_*` (4 tests) | KEEP · Layer 3 unchanged | No change |
| `test_trail_state_to_dict_round_trip` | UPDATE field list · `last_5_lows`/`last_5_highs`/`max_high_since_t2`/`min_low_since_t2`/`chandelier_engaged`/`t2_bar_ts`/`t2_atr_at_engage` instead of `swing_high/swing_low/atr14` | New TrailState fields |
| `test_state_saved_to_trade_quality` | UPDATE field assertions to new TrailState shape | New shape |
| `test_state_loaded_from_trade_quality` | UPDATE seeded `trail_state` dict to new shape | New shape |
| `test_bars_processed_increments_on_each_bar` | KEEP · `bars_processed` survives | No change |
| `test_trail_active_set_after_t2` | KEEP · `trail_active` survives | No change |
| `test_update_stop_audit_reason_swing` | RENAME → `test_update_stop_audit_reason_hl_lh_trail_5bar` · reason string changed | Reason string |
| `test_update_stop_audit_bar_ts_forwarded` | KEEP · agnostic to internals | No change |
| `test_close_trade_time_stop_reason` | KEEP | No change |
| `test_fill_locked_trade_skipped_entirely` | KEEP | No change |
| `test_fill_lock_checked_inside_move_stop` | KEEP | No change |
| `test_unlocked_trade_processes_normally` | UPDATE seed (now requires `t2_hit_ts` + seeded `last_5_lows` with 4 entries to fire on 5th bar) | New shape |
| `test_on_bar_close_dispatches_to_process_trade` | UPDATE seed for 5-bar window | New shape |
| `test_on_bar_close_no_op_when_t2_not_hit` | KEEP | No change |

**Net:** 6 RENAMES · 9 MIGRATE-SEMANTICS · 1 DELETE · 13 KEEP. Total 29 → 28 (one merged into §3.6).

---

## §3.6 · NEW tests for D-094 retrofits (Gap 2/5/11/14) — 10 additional tests beyond §3 (Layer 4)

These complement §3's 20 Layer-4 tests · they cover the Stream 3b-3 D-094
retrofits added in §0.5-0.8. Total NEW tests in 3b-3: 30 (= 20 Layer-4 + 10 retrofit).

| # | Test name | Setup | Expected |
|---|---|---|---|
| 50 | `test_hl_lh_window_slides_drops_oldest` | LONG · seed `last_5_lows=[5240,5241,5242,5243,5244]` · new bar low=5245 | window becomes `[5241,5242,5243,5244,5245]` · `min=5241` · stop moves to 5241 IF tighter |
| 51 | `test_hl_lh_needs_5_bars_before_firing` | LONG · seed `last_5_lows=[5240,5241,5242]` (3 entries) · new bar low=5243 | window becomes `[5240,5241,5242,5243]` len=4 · `update_stop_with_audit` NOT called |
| 52 | `test_chandelier_engaged_freezes_atr_once` | LONG just hit T2 · `fetch_bars_since` returns 14 dummy bars (high=5250 each, low=5245, close=5247) · call `_engage_chandelier` · then call `_process_trade` with different bar set (would compute different ATR if live) | `state.t2_atr_at_engage` set on first call · UNCHANGED on second call · `compute_continuous_atr14` NOT called from `_process_trade` chandelier path |
| 53 | `test_chandelier_engage_writes_audit` | LONG t2_hit, no prior engage | `_engage_chandelier` runs · `trade.cross_context` has entry `{event: "chandelier_engaged", frozen_atr: ...}` |
| 54 | `test_chandelier_skips_when_pattern_family_unknown` | LONG t2_hit · pattern_name=`"UNKNOWN_PATTERN"` (no family resolution) · seed frozen ATR | `_compute_chandelier_stop_v3` returns None · NO silent fallback to k=1.5 · no chandelier stop move |
| 55 | `test_append_cross_context_validates_json_serializability` | construct trade with cross_context=[] · call `_append_cross_context(trade, {"ts": datetime.now()})` | `trade.cross_context[-1]` has the entry · `json.dumps(trade.cross_context[-1], default=str)` succeeds |
| 56 | `test_append_cross_context_reassigns_list` | trade.cross_context starts as `[{"event": "entry"}]` · call `_append_cross_context` with new entry | reassignment occurs (new list object) · old entry preserved · new entry appended |
| 57 | `test_load_state_corrupt_falls_back_to_db_reconstruct` | `trade.quality = {"trail_state": {"last_5_lows": 12345}}` (non-list triggers list(int) TypeError in from_dict) · `fetch_bars_since` returns 5 fake bars · `trade.t2_hit_ts` set | (a) `cross_context` has `"trail_state_load_failed"` entry · (b) returned state has `chandelier_engaged=True` · (c) `max_high_since_t2` = max(high) of fake bars · NOT None · NOT corrupt |
| 58 | `test_load_state_missing_returns_empty` | `trade.quality = {}` | `_load_state` returns `TrailState()` defaults (all None/empty) · no DB query |
| 59 | `test_reconstruct_state_returns_empty_when_t2_hit_ts_none` | trade.t2_hit_ts=None · call `_reconstruct_state_from_db` | returns empty `TrailState()` · NO query attempt |

**Test scaffolding for retrofits:**

```python
@pytest.fixture
def fetch_bars_since_5bars():
    """Returns 5 fake LONG-friendly bars for reconstruct tests."""
    def _fetch(trade_id, since_ts):
        return [
            {"high": 5260.0, "low": 5252.0, "close": 5258.0, "ts": "2026-05-23T10:00:00Z"},
            {"high": 5262.0, "low": 5253.0, "close": 5260.0, "ts": "2026-05-23T10:05:00Z"},
            {"high": 5265.0, "low": 5254.0, "close": 5263.0, "ts": "2026-05-23T10:10:00Z"},
            {"high": 5263.0, "low": 5255.0, "close": 5260.0, "ts": "2026-05-23T10:15:00Z"},
            {"high": 5266.0, "low": 5256.0, "close": 5264.0, "ts": "2026-05-23T10:20:00Z"},
        ]
    return _fetch


@pytest.fixture
def fetch_bars_since_14bars():
    """Returns 14 dummy LONG bars · sufficient for Wilder ATR-14."""
    def _fetch(trade_id, since_ts):
        return [{"high": 5250.0, "low": 5245.0, "close": 5247.0,
                 "ts": f"2026-05-23T10:{5*i:02d}:00Z"} for i in range(14)]
    return _fetch
```

---

## §4 · WoodiesSystem method · exact insertion

`backend/v9/systems/woodies/woodies_system.py` — append the method to
`class WoodiesSystem` AFTER all existing methods (alphabetical convention
is OK — pick a clear spot · suggestion: near `current_state`/`get_state`
if such accessor exists · otherwise at the end of the class).

```python
def get_layer4_context(self) -> Optional[Dict]:
    """Snapshot for TrailEngine Layer 4 wiring (Pkg 3b-3 LOCK 2).

    Returns None when buffer is empty (Woodies services then skip cleanly
    in TrailEngine._apply_layer4). Otherwise returns:

    {
      "swi": {"value": float, "color": str (lowercased trend_state)},
      "cci_history": [last 3 cci_14 floats · most recent last],
      "direction_change_event": dc_event dict or None,
      "current_bar_ts": float (most recent buffered bar ts),
    }

    All fields are read from self._bar_buffer (no computation here).
    detect_direction_change is the existing W3-β detector already
    imported at module top.
    """
    if not self._bar_buffer:
        return None
    last = self._bar_buffer[-1]
    cci_hist = [float(b.cci_14 or 0.0) for b in self._bar_buffer[-3:]]
    try:
        dc_event = detect_direction_change(self._bar_buffer)
    except Exception:
        logger.exception("[WoodiesSystem] direction_change detect failed")
        dc_event = None
    return {
        "swi": {
            "value": float(last.swi_value or 0.0),
            "color": (last.trend_state or "GRAY").lower(),
        },
        "cci_history": cci_hist,
        "direction_change_event": dc_event,
        "current_bar_ts": float(last.ts),
    }
```

Imports required: ensure `Optional` and `Dict` are in the typing import at
top of the file (they likely already are · verify before adding).

NO change to `process_bar` or `_bar_buffer` lifecycle.

---

## §5 · Self-verification (CC must report at end)

After writing all changes · before commit · CC must verify and include in
the final report:

1. Service files untouched: `git diff backend/v9/services/layer4/ | wc -l` == 0
2. `WoodiesBar` schema untouched: `git diff backend/v9/systems/woodies/schemas.py | wc -l` == 0
3. DLL/bridge untouched: `git diff sc_study/ bridge/ frontend/ | wc -l` == 0
4. 20 new tests in `test_trail_engine.py` pass: `pytest tests/v9/services/test_trail_engine.py -k "test_mfe or test_cci_flat or test_tcci or test_swi or test_layer4 or test_day_type_warn or test_day_type_escalates" -v`
5. Existing 29 Stream 3b-2 tests still pass: `pytest tests/v9/services/test_trail_engine.py -v` (49 total tests · 49 passing)
6. Layer 4 atomic tests untouched (regression sanity): `pytest tests/atomic/test_l4_* -q`
7. Pkg 1 ATR_MULTIPLIERS unchanged smoke (per Stream 3b-1 G3): grep `ATR_MULTIPLIER` in `backend/v9/systems/five_min/adaptive_stop.py` matches exactly the pre-Pkg-3b values
8. Trail engine wiring order: log the actual MagicMock call_order from test #40
9. Commit message includes the Phase A flag verbatim per §0 header

---

## §6 · Commit checklist (DO NOT MERGE if any unchecked)

### Layer 4 wiring (original v1 scope)

- [ ] All 9 LOCKS from §0 implemented as specified · zero drift (LOCK 1-5 Layer 4 · LOCK 6-9 D-094 retrofit)
- [ ] WoodiesSystem.get_layer4_context returns None on empty buffer (LOCK 2)
- [ ] `_apply_layer4` runs services in exact D-094 §3.B.3 order (mfe → cci_flat → tcci_cross → swi → day_type_targets_verify) verified by test #40
- [ ] TIGHTEN actions accumulate · tightest wins per Gap 13 (tests #41–#42)
- [ ] TCCI EXIT short-circuits subsequent services (test #43)
- [ ] day_type_targets_verify escalation to close_trade ONLY when `get_targets(current).no_trade == True` (LOCK 5 · tests #45–#46)
- [ ] MFE tracked in `quality["mfe_high"]` / `quality["mfe_low"]` · tightens-only invariant (LOCK 4 · tests #47–#49)
- [ ] Trade-dict adapter contains BOTH `stop` AND `stop_price` keys (LOCK 3)

### D-094 retrofit (v3 NEW scope · Michael directive)

- [ ] TrailState refactored per LOCK 7 · `last_5_lows` + `last_5_highs` REPLACE `swing_high` + `swing_low` (Gap 2)
- [ ] TrailState additions per LOCK 8 · `max_high_since_t2` + `min_low_since_t2` + `chandelier_engaged` + `t2_bar_ts` + `t2_atr_at_engage` (Gap 5)
- [ ] `_engage_chandelier` method added · runs ONCE per trade · `t2_atr_at_engage` IMMUTABLE after engage (Gap 5)
- [ ] `_compute_chandelier_stop_v3` REPLACES `_compute_chandelier_stop` · uses `state.t2_atr_at_engage` (frozen) NOT `compute_continuous_atr14` (live)
- [ ] Silent fallback `ATR_MULTIPLIERS.get(family, 1.5)` REMOVED · unknown family → return None (pre-LIVE protocol)
- [ ] `_append_cross_context` helper added per LOCK 6 · all audit writes use it (Gap 11)
- [ ] `_reconstruct_state_from_db` method added per LOCK 9 · `_load_state` falls back on corrupt state (Gap 14)
- [ ] Constructor extended with `fetch_bars_since` + `woodies_provider` keyword args (LOCK 2 + LOCK 9)
- [ ] Reason strings updated · `"hl_lh_swing"` → `"hl_lh_trail_5bar"` · `"chandelier_atr14"` → `"chandelier_atr14_frozen"`

### Test migration (per §3.5)

- [ ] 11 existing 3b-2 tests migrated per §3.5 matrix (6 renamed · 9 semantics-migrated · 1 deleted · 13 kept as-is)
- [ ] 10 NEW retrofit tests #50-#59 added per §3.6 (window slide · 5-bar warmup · frozen ATR · audit · DB reconstruct)
- [ ] 20 NEW Layer-4 tests #30-#49 added per §3 (original v1 spec)
- [ ] Total test count: 28 migrated 3b-2 tests + 30 new = 58 tests in `test_trail_engine.py`
- [ ] `pytest tests/v9/services/test_trail_engine.py -q` → all 58 PASS

### Regression guards

- [ ] No edits to ANY file in `backend/v9/services/layer4/`
- [ ] No edits to `V9Trade` model, BarRouter, EventDispatcher, TradingGateway
- [ ] No edits to Pkg 1 (`adaptive_stop.py` · `ATR_MULTIPLIERS` unchanged)
- [ ] No edits to Pkg 3a (`targets_table.py` · `day_type_targets.py`)
- [ ] No new dependencies · no new bar topic · no Redis use
- [ ] All Layer 4 service calls wrapped in try/except (per-service failure isolation)
- [ ] All cross_context appends use `json.dumps(default=str)` validation (Gap 11)
- [ ] `pytest tests/v9/services/test_trade_manager.py -q` → 60 PASS · 2 pre-existing failures unchanged (no new regressions)
- [ ] `pytest tests/v9/systems/ -q` → 682 PASS · 1 skipped (unchanged from post-3c baseline)
- [ ] `pytest backend/v9/tests/ -q` → 531 PASS · 2 skipped (no regressions)
- [ ] Commit message contains the Phase A flag verbatim per §0
- [ ] Self-verification §5 items 1–9 all pass

---

## §7 · Deferred (NOT in this stream)

These are knowingly deferred · do NOT attempt to "while I'm here" them:

- **MFE restart recovery from bar history** — Phase A accepts that an
  in-flight restart loses MFE state until the next live bar updates it.
  Worst case: re-engagement of MFE peak tighten requires a fresh peak.
  Acceptable for SHADOW soak. Pkg 6 will reconstruct from `v9_bars_5min`
  if it becomes a problem.
- **W3-β direction_change_detector wiring beyond Layer 4** — the detector
  is used by us VIA `get_layer4_context`. If S4 needs it elsewhere for
  its own decision tree, that is a separate concern (likely already done
  in `decision_tree.py`).
- **`day_type_targets_verify` calibration** — service uses
  `time_stop_minutes` and `no_trade` from `targets_table.get_targets`.
  If the calibration knobs need to change post-SHADOW · that is a
  D-09x amendment · not a Stream 3b-3 concern.
- **Audit table for Layer 4 events** — all events go to `cross_context`
  on the trade row. A separate `v9_layer4_events` table is NOT in this
  stream.
- **HTTP `/api/v9/day_type/current` fallback** — `_fetch_current_day_type`
  uses the in-process `day_type_state` module only. No HTTP. If that
  module does not exist · STOP and ask Cursor.

---

## §8 · Reference index

- D-094 LOCKED: `docs/decisions/D-094_PKG3B_TRAIL_DECISIONS.md`
- Stream 3b-2 mega-prompt: `docs/handoff/MEGA_PROMPT_PKG3B_STREAM2.md`
- Pkg 3b master handoff: `docs/handoff/DESKTOP_PKG3B_TRAIL_LOGIC_HANDOFF.md`
- Sierra DLL contract: `sc_study/v9_woodies_export.h`
- Layer 4 services (FROZEN): `backend/v9/services/layer4/{mfe_peak_tighten,cci_flat_tighten,tcci_cross_exit,swi_tighten,day_type_targets_verify}.py`
- W3-β detector: `backend/v9/systems/woodies/direction_change_detector.py`
- WoodiesBar schema: `backend/v9/systems/woodies/schemas.py`
- TrailEngine (post-Stream-3b-2): `backend/v9/services/trail_engine.py`
- TradeManager (post-Stream-3b-2): `backend/v9/services/trade_manager/manager.py`

End of MEGA PROMPT · Pkg 3b · Stream 3.
