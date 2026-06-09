"""FiveMinSystem — 5-min Decision Maker with full D-077 lifecycle.

Implements hydrate() for cold start scenarios (Addendum Section 1).
Uses SessionClassifier (D-083) — never raw time checks.
"""

import logging
from datetime import date, datetime, timezone, timedelta

from backend.v9.common.trading_date import et_today
from typing import Any, Dict, List, Optional

from backend.v9.systems.base.trading_system import BaseV9TradingSystem, HydrationResult, SystemType
from backend.v9.common.session_classifier import SessionClassifier, Session
from backend.v9.db.session import SessionLocal
from backend.v9.systems.five_min.setup_emitter import emit_t1_setup
from backend.v9.systems.five_min.cot_amt import read_cumulative_delta, compute_cot, compute_amt
from backend.v9.db.models.bars_5min import V9Bar5Min
from backend.v9.db.models.five_min_state import V9FiveMinState
from backend.v9.systems.five_min.patterns.head_shoulders import detect_inverse_hns, detect_hns_top
from backend.v9.systems.five_min.patterns.double_bt import detect_double_bottom_ee, detect_double_top_aa
from backend.v9.systems.five_min.patterns.flags import detect_bull_flag, detect_bear_flag
from backend.v9.systems.five_min.first_hour_buffer import FirstHourBuffer
from backend.v9.systems.five_min.choppiness import compute_choppiness
from backend.v9.api.v9.tpo_routes import _load_sierra_tpo

logger = logging.getLogger("mems26.systems.five_min")

# Pkg 2bc · OFA configuration (config-driven thresholds per Master Sheet 7)
DROP_THRESHOLD_PCT: float = 0.10               # bar 2 vol ≤ 10% of bar 1 vol (90% drop)
EXPANSION_MIN_PT: float = 1.5                  # Initiative bar 1 range min (points)
EXPANSION_MAX_PT: float = 1.75                 # Initiative bar 1 range max (points)
POC_RETURN_TOLERANCE_PT: float = 0.5           # Initiative bar 2 POC return tolerance
MIN_BARS_REQUIRED: int = 7                     # 4 pattern + 3 lookback (Pkg 2bc)
LOOKBACK_BARS: int = 3                         # bars before bar 1 to check "normal" volume
LOOKBACK_MAX_VOL_RATIO: float = 0.6            # max(lookback_3bars.volume) / bar1.volume < this
BELLY_DOMINANCE_RATIO: float = 1.5             # bar 3 buy/sell ratio threshold for Reactive

# ── S2 ATR-relative thresholds (E2E 2/2 · shadow only) ──
from backend.v9.shared.atr import S2_ATR_RELATIVE  # noqa: E402
from typing import Optional as _Opt  # noqa: E402

# Expansion gate: bar must be notably larger than recent average (Michael 2026-06-08)
_EXPANSION_MIN_K = 1.3   # bar_range ≥ 1.3 × avg_range (30% above average)
_EXPANSION_MAX_K = 2.5   # bar_range ≤ 2.5 × avg_range (cap: not a gap bar)
_EXPANSION_LOOKBACK = 14  # bars to average over

# POC return tolerance — relative to avg bar range
_POC_RETURN_K = 0.2      # tolerance ~0.2 × avg_range

# Fallback when no bars available
_DEFAULT_AVG_RANGE = 3.0  # MES 5-min historical average range (pts)


def get_expansion_range(bars: _Opt[list] = None, lookback: int = _EXPANSION_LOOKBACK):
    """Return (min_pt, max_pt) for Initiative expansion gate.

    Uses average bar range (h-l) of the last `lookback` bars, not ATR.
    A bar must be 1.3× the average (notably larger) but not 2.5× (gap bar).
    Michael 2026-06-08: ratio adapts to average candle size, not fixed ATR×k.
    """
    avg = _DEFAULT_AVG_RANGE
    if bars and len(bars) >= 3:
        window = bars[-lookback:]
        ranges = [b.get("h", b.get("high", 0)) - b.get("l", b.get("low", 0)) for b in window]
        avg = sum(ranges) / len(ranges) if ranges else _DEFAULT_AVG_RANGE
    if avg <= 0:
        avg = _DEFAULT_AVG_RANGE
    return (_EXPANSION_MIN_K * avg, _EXPANSION_MAX_K * avg)


def get_poc_return_tolerance(bars: _Opt[list] = None, lookback: int = _EXPANSION_LOOKBACK) -> float:
    """Return POC return tolerance in points.

    Relative to average bar range (Michael 2026-06-08).
    """
    avg = _DEFAULT_AVG_RANGE
    if bars and len(bars) >= 3:
        window = bars[-lookback:]
        ranges = [b.get("h", b.get("high", 0)) - b.get("l", b.get("low", 0)) for b in window]
        avg = sum(ranges) / len(ranges) if ranges else _DEFAULT_AVG_RANGE
    if avg <= 0:
        avg = _DEFAULT_AVG_RANGE
    return _POC_RETURN_K * avg


def build_s2_gateway_setup(t1_setup, info: dict) -> dict:
    """Build the S2→gateway setup dict from a resolved T1Setup.

    Extracted so the bracket-level mapping (esp. T3) is unit-testable.
    T3 is passed through faithfully: None when the day type has no fixed T3
    (trail/no-T3 per targets_table), a real price for fixed-T3 days
    (Trend_Normal=4R, Trend_DD=4R cap). It must NOT be coerced to 0.0 —
    a 0.0 T3 is treated by active_trade_manager as a phantom (unreachable)
    target on the C3 leg.
    """
    return {
        "firing_system": 2,
        "direction": t1_setup.direction,
        "classification": t1_setup.pattern_name,
        "confidence": t1_setup.confidence / 100.0,
        "entry_price": t1_setup.entry_price,
        "stop": t1_setup.stop_price or 0.0,
        "t1": t1_setup.t1_price or 0.0,
        "t2": t1_setup.t2_price or 0.0,
        "t3": t1_setup.t3_price,  # None when trail/no-T3; real price for TN/TDD
        "metadata": {
            "pattern": t1_setup.pattern_name,
            "sizing": t1_setup.sizing_contracts,
            "variant": info.get("variant"),  # D-RVX: A_VSA/B_RVOL/C_STRICT
            "variants_passed": info.get("variants_passed"),
        },
    }


class FiveMinMode:
    WAITING_OPEN = "WAITING_OPEN"
    FIRST_HOUR_TACTICAL = "FIRST_HOUR_TACTICAL"
    DAY_TYPE_MODE = "DAY_TYPE_MODE"
    OVERNIGHT_MODE = "OVERNIGHT_MODE"
    WEEKEND = "WEEKEND"
    MAINTENANCE = "MAINTENANCE"
    RECOVERING = "RECOVERING"
    LIVE_ONLY = "LIVE_ONLY"


class FiveMinSystem(BaseV9TradingSystem):
    """System 2: 5-min pattern detection + setup package publishing."""

    system_id = 2
    name = "five_min"
    color = "#06b6d4"
    system_type = SystemType.FIRING
    subscribed_channels = [
        "mems26:events:bar.5min",
        "mems26:events:system.day_type.classification",
    ]

    def __init__(self):
        self._gateway = None  # injected post-init via set_gateway() (Prompt 14)
        self._footprint_system = None  # injected post-init via set_footprint_system() (P31-02b)
        self.session_classifier = SessionClassifier()
        self.mode = FiveMinMode.WAITING_OPEN
        self.buffer_size = 0
        self.opening_type: Optional[str] = None
        self.current_day_type: Optional[str] = None  # Stream 2 · D-091.Q1 NeuE/NeuC source
        self._nt_skip_count: int = 0                 # Stream 2 · D-091.Q2 SHADOW counter
        self._nt_skip_last_log_ts: float = 0.0       # Rate-limit anchor for NT skip log
        self.last_pattern: Optional[str] = None
        self.last_confluence: int = 0
        self.last_classification: Optional[str] = None
        self.choppiness_score: int = 0
        self._current_atr_5m: _Opt[float] = None  # D-094: rolling ATR for relative thresholds
        self._fhb = FirstHourBuffer()      # First Hour Buffer — bar-count gate
        self._last_bar_ts_for_count: Optional[str] = None  # dedup: count bars, not pushes
        # A2: per-pattern fire dedup (prevents stateless detectors like Double Top
        # from firing 43x on the same setup). Key = "KIND_DIR", value = bar_count
        # at last fire. Skip same pattern+direction within cooldown bars.
        self._fire_dedup: Dict[str, int] = {}
        _DEDUP_COOLDOWN = {"DOUBLE_TOP_AA": 30, "DOUBLE_BOTTOM_EE": 30,
                           "INVERSE_HNS": 30, "HNS_TOP": 30,
                           "BULL_FLAG": 20, "BEAR_FLAG": 20}
        self._dedup_cooldown = _DEDUP_COOLDOWN
        self._hydrated = False
        self.current_state: Dict[str, Any] = {}

    def set_gateway(self, gateway) -> None:
        """Inject TradingGateway for auto-routing fire signals (Prompt 14)."""
        self._gateway = gateway

    def set_footprint_system(self, footprint_system) -> None:
        """Inject FootprintSystem for in-process cot/amt/belly reads (P31-02b).

        Without injection, the helpers below fall back to HTTP self-calls
        (`requests.get http://localhost:8000/api/v9/footprint/current`) which
        are the documented root cause of the 8s SLOW handler — see
        docs/handoff/P31_TASK_BOARD.md §6.1. With injection, the same data
        is read in-process in <1ms.
        """
        self._footprint_system = footprint_system

    def hydrate(self) -> HydrationResult:
        """D-077 hydration using SessionClassifier (D-083)."""
        try:
            info = self.session_classifier.classify()
            session = info.session

            # Non-trading sessions
            if session == Session.WEEKEND:
                self.mode = FiveMinMode.WEEKEND
                self._hydrated = True
                return HydrationResult(success=True, reached_state=FiveMinMode.WEEKEND,
                                       notes="Weekend, no trading")

            if session == Session.MAINTENANCE:
                self.mode = FiveMinMode.MAINTENANCE
                self._hydrated = True
                return HydrationResult(success=True, reached_state=FiveMinMode.MAINTENANCE,
                                       notes="Daily maintenance window")

            # Stream 2 · hydrate current_day_type from v9_day_type_state (D-091.Q1)
            # Moved BEFORE overnight early-return so current_day_type is populated
            # even during Globex sessions (P31-F).
            # Uses 24h sliding window instead of func.current_date() to avoid
            # UTC vs ET date boundary mismatch (Fix #6 case b, 2026-05-28).
            try:
                from backend.v9.systems.day_type.models import V9DayTypeState
                db = SessionLocal()
                try:
                    _cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
                    _latest_dt = (
                        db.query(V9DayTypeState)
                        .filter(V9DayTypeState.ts >= _cutoff)
                        .order_by(V9DayTypeState.id.desc())
                        .first()
                    )
                    if (_latest_dt is not None
                            and _latest_dt.day_type
                            and _latest_dt.day_type != "UNKNOWN"):
                        self.current_day_type = _latest_dt.day_type
                        logger.info(
                            "[FiveMin] Hydrated current_day_type=%s from v9_day_type_state",
                            self.current_day_type,
                        )
                finally:
                    db.close()
            except Exception as _hydrate_err:
                logger.warning(
                    "[FiveMin] day_type hydrate failed: %s · live updates will populate",
                    _hydrate_err,
                )

            # Globex sessions (overnight, pre-market, after-hours)
            if session in (Session.OVERNIGHT, Session.PRE_MARKET, Session.AFTER_HOURS):
                self.mode = FiveMinMode.OVERNIGHT_MODE
                self._hydrated = True
                return HydrationResult(success=True, reached_state=FiveMinMode.OVERNIGHT_MODE,
                                       notes=f"Globex session: {session.value}")

            # Try to load today's state from DB
            db = SessionLocal()
            try:
                state = db.query(V9FiveMinState).filter(
                    V9FiveMinState.session_date == et_today()
                ).first()
            finally:
                db.close()

            # Load bars from DB and replay into _bar_buffer (P-WAVE-D3)
            bars_count = 0
            try:
                db = SessionLocal()
                try:
                    rows = (
                        db.query(V9Bar5Min)
                        .filter(V9Bar5Min.is_synthetic == 0)
                        .order_by(V9Bar5Min.ts.desc())
                        .limit(60)
                        .all()
                    )
                finally:
                    db.close()
                # Replay oldest-first into buffer (no persist)
                for row in reversed(rows):
                    bar = {
                        "ts": str(row.ts or ""),
                        "o": float(row.open or 0),
                        "h": float(row.high or 0),
                        "l": float(row.low or 0),
                        "c": float(row.close or 0),
                        "v": int(row.volume or 0),
                    }
                    self._bar_buffer.append(bar)
                bars_count = len(rows)
                if len(self._bar_buffer) > 20:
                    self._bar_buffer = self._bar_buffer[-20:]
                logger.info("[FiveMin] Hydrated %d bars from DB, buffer_size=%d",
                            bars_count, len(self._bar_buffer))
            except Exception as e:
                logger.warning("[FiveMin] DB bar replay failed: %s", e)

            # Cash open / First hour
            if session in (Session.CASH_OPEN, Session.FIRST_HOUR):
                self.mode = FiveMinMode.FIRST_HOUR_TACTICAL
                self.buffer_size = bars_count
                if state:
                    self.opening_type = state.opening_type
                    self.choppiness_score = state.choppiness_score or 0
                self._hydrated = True
                return HydrationResult(
                    success=True,
                    reached_state=FiveMinMode.FIRST_HOUR_TACTICAL,
                    bars_replayed=bars_count,
                    notes=f"Mid-first-hour, {bars_count} bars replayed",
                )

            # Scenario C: Post-lock (10:30+ ET)
            self.mode = FiveMinMode.DAY_TYPE_MODE
            # FHB: first hour is over — mark as COMPLETE so inspector shows correct state
            from backend.v9.systems.five_min.first_hour_buffer import BufferState
            self._fhb._bar_count = 13
            self._fhb._state = BufferState.COMPLETE
            if state:
                self.opening_type = state.opening_type
                self.choppiness_score = state.choppiness_score or 0
            self._hydrated = True
            return HydrationResult(
                success=True,
                reached_state=FiveMinMode.DAY_TYPE_MODE,
                bars_replayed=bars_count,
                notes=f"Post-IB lock. Day Type Mode active. {bars_count} bars.",
            )

        except Exception as e:
            logger.warning("[FiveMin] Hydration error: %s", e)
            self.mode = FiveMinMode.LIVE_ONLY
            self._hydrated = True
            return HydrationResult(
                success=False,
                reached_state=FiveMinMode.LIVE_ONLY,
                error=str(e),
            )

    def process(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process incoming events (bar.5min.closed or day_type.classification)."""
        event_type = event.get("event_type", "")

        if "bar.5min" in event_type:
            return self._on_bar_closed(event)
        elif "day_type" in event_type:
            return self._on_day_type_update(event)
        return None

    def _on_bar_closed(self, event: dict) -> Optional[dict]:
        """Process a closed 5-min bar."""
        self.buffer_size += 1

        # Mode transition via SessionClassifier (D-080 + D-083)
        ts = event.get("ts_ms") or event.get("ts")
        if ts and isinstance(ts, (int, float)):
            from zoneinfo import ZoneInfo
            bar_time = datetime.fromtimestamp(
                ts / 1000 if ts > 1e12 else ts,
                tz=ZoneInfo("America/New_York"),
            )
            info = self.session_classifier.classify(bar_time)
            if info.session == Session.CASH_HOURS and self.mode == FiveMinMode.FIRST_HOUR_TACTICAL:
                self.mode = FiveMinMode.DAY_TYPE_MODE
                logger.info("[FiveMin] Mode transition: FIRST_HOUR -> DAY_TYPE_MODE at %s", bar_time)

        # Delegate to existing chart_5min detector for pattern detection
        # (integration point — full wiring in future prompts)
        return None

    def _on_day_type_update(self, event: dict) -> None:
        """Handle Day Type classification update (Stream 2 · D-091)."""
        payload = event.get("payload", {}) if isinstance(event, dict) else {}
        new_dt = payload.get("day_type") or payload.get("classification")
        if new_dt and isinstance(new_dt, str):
            if new_dt != self.current_day_type:
                logger.info(
                    "[FiveMin] current_day_type: %s → %s",
                    self.current_day_type,
                    new_dt,
                )
            self.current_day_type = new_dt
        new_ot = payload.get("opening_type")
        if new_ot and isinstance(new_ot, str):
            self.opening_type = new_ot
        return None

    async def on_day_type_event(self, event) -> None:
        """Async wrapper for bar_router day_type_classification events.

        Memorial Day fix #4A.1 (corrective): BarRouter's `BarEvent` dataclass
        (`backend/v9/services/bar_router.py:19-26`) exposes the inner data on
        `.payload` — NOT `.data`. The prior implementation read `.data`, which
        does not exist on the real `BarEvent`, so the wrapper silently no-op'd
        in production despite passing tests that used a fake `.data` attr.

        `_on_day_type_update` expects `{"payload": {...}}`, so we wrap
        `event.payload` accordingly. Plain dicts are accepted as-is for
        testing convenience.
        """
        if isinstance(event, dict):
            self._on_day_type_update(event)
            return
        if hasattr(event, "payload"):
            self._on_day_type_update({"payload": event.payload})
            return
        logger.warning(
            "[FiveMin] on_day_type_event: unsupported event type %s — ignored",
            type(event).__name__,
        )

    # ── Footprint helpers ──

    def _footprint_state(self) -> Dict[str, Any]:
        """In-process footprint state if injected, else HTTP fallback (P31-02b).

        Production wires this via FiveMinSystem.set_footprint_system at startup.
        Tests inject a mock. The HTTP fallback preserves backward compatibility
        for instances created without the wire-up — slow but functional.
        """
        if self._footprint_system is not None:
            try:
                state = self._footprint_system.get_current()
                return state if isinstance(state, dict) else {}
            except Exception:
                return {}
        # FIX 4: removed HTTP self-call fallback (deadlocked single-worker uvicorn).
        # If footprint_system not injected, return empty (S3 is muted anyway).
        return {}

    def _get_belly_from_footprint(self) -> Optional[bool]:
        """Read belly_ratio_dominant from Footprint System 3.

        True if buyers dominate bottom of recent bar (belly forming).
        Falls back to None (not False) if unavailable — explicit per §6.7.
        """
        val = self._footprint_state().get("belly_ratio_dominant")
        if val is None:
            return None
        return bool(val)

    def _get_belly_ratio_from_footprint(self, direction: str) -> Optional[float]:
        """Pkg 2bc · compute belly dominance ratio for bar 3 from forces_history.

        LONG belly: ratio = ask_vol / bid_vol (buyers dominate).
        SHORT belly: ratio = bid_vol / ask_vol (sellers dominate).

        Returns None if history unavailable — caller SKIPS check (graceful degradation).
        """
        state = self._footprint_state()
        history = state.get("forces_history") or []
        if len(history) < 2:
            return None
        bar3 = history[-2]  # bar 3 (one bar ago · current bar is bar 4)
        ask = bar3.get("ask_vol")
        bid = bar3.get("bid_vol")
        if ask is None or bid is None:
            return None
        if direction == "LONG":
            if bid <= 0:
                return None
            return ask / bid
        else:  # SHORT
            if ask <= 0:
                return None
            return bid / ask

    def _poc_vol_rising(self, bars: List[Dict], n: int = 3) -> bool:
        """Check if POC price level is rising across last N bars.

        Per V3 T1: POC_VOL rising = volume POC moving up across bars.
        Uses TPO POC as proxy (V3 D-046 distinction acknowledged 🟡).
        """
        if len(bars) < n:
            return False
        recent = bars[-n:]
        poc_prices = []
        for b in recent:
            poc = b.get("poc_vol") or b.get("poc")
            if poc is None:
                # Estimate POC as VWAP proxy: weighted midpoint
                poc = (b.get("h", 0) + b.get("l", 0) + b.get("c", 0)) / 3
            poc_prices.append(poc)
        # Rising = each >= previous
        return all(poc_prices[i] >= poc_prices[i - 1] for i in range(1, len(poc_prices)))

    def _poc_vol_falling(self, bars: List[Dict], n: int = 3) -> bool:
        """Check if POC price level is falling across last N bars (SHORT mirror)."""
        if len(bars) < n:
            return False
        recent = bars[-n:]
        poc_prices = []
        for b in recent:
            poc = b.get("poc_vol") or b.get("poc")
            if poc is None:
                poc = (b.get("h", 0) + b.get("l", 0) + b.get("c", 0)) / 3
            poc_prices.append(poc)
        return all(poc_prices[i] <= poc_prices[i - 1] for i in range(1, len(poc_prices)))

    def _cot_amt_from_sierra(self) -> tuple:
        """Read COT and AMT from Sierra cumulative_delta.json (spec-compliant).

        Spec (Constitution V3 §T1): COT = Sierra session CDV (latest cumulative
        value), AMT = 90-min rolling average of CDV points. This is the correct
        source per compliance_manifest.yaml COT_AMT node and cot_amt.py.

        Returns (cot, amt) or (None, None) if the file is unavailable.
        """
        try:
            data = read_cumulative_delta()
            if not data:
                return (None, None)
            pts = data.get("points") or data.get("bars") or []
            if not pts:
                return (None, None)
            return (compute_cot(pts), compute_amt(pts))
        except Exception:
            return (None, None)

    def _get_cot_from_footprint(self) -> Optional[float]:
        """COT — Sierra CDV preferred; footprint in-process as fallback."""
        cot, _ = self._cot_amt_from_sierra()
        if cot is not None:
            return cot
        return self._footprint_state().get("cot")

    def _get_amt_from_footprint(self) -> Optional[float]:
        """AMT — Sierra CDV rolling avg preferred; footprint in-process as fallback."""
        _, amt = self._cot_amt_from_sierra()
        if amt is not None:
            return amt
        return self._footprint_state().get("amt")

    # ── Pattern detectors (Constitution V3 Layer 1 T1) ──

    def _detect_reactive(self, bars_5m: List[Dict]) -> tuple:
        """Reactive 4-bar pattern per Constitution V3.

        LONG (seller weakness):
          Bar 1: sellers dominate (bearish close + high vol)
          Bar 2: 90% volume drop vs Bar 1
          Bar 3: buyer belly (bullish close) + POC_VOL rising
          Bar 4: confirmation (bullish close)
          COT > AMT required.

        SHORT: Mirror of LONG.
        Returns (direction, confidence, info) or (None, 0, {}).
        """
        if len(bars_5m) < MIN_BARS_REQUIRED:
            return (None, 0, {})

        b1, b2, b3, b4 = bars_5m[-4], bars_5m[-3], bars_5m[-2], bars_5m[-1]
        cur_cot = self._get_cot_from_footprint()
        cur_amt = self._get_amt_from_footprint()
        # S2 INDEPENDENT OF S3 (Michael 2026-06-08): COT/AMT (footprint/S3) is
        # NOT required for S2 fires by default. S3 is muted/broken at this stage
        # (S3_MUTE / I-11), so S2 must fire on price-geometry + volume alone.
        # Re-require the order-flow confirmation ONLY via env S2_REQUIRE_COT_AMT=1
        # + Michael approval. See CLAUDE.md §"S2 ⟂ S3 (COT/AMT gate disabled)".
        import os as _os
        _require_cot_amt = _os.environ.get("S2_REQUIRE_COT_AMT", "").lower() in ("1", "true", "yes")
        if _require_cot_amt and (cur_cot is None or cur_amt is None):
            return (None, 0, {})

        b0_vol = bars_5m[-5].get("v", 0) or 0 if len(bars_5m) >= 5 else 0  # D-RVX
        b1_vol = b1.get("v", 0) or 0
        b2_vol = b2.get("v", 0) or 0

        # D-RVX: 3-variant volume gate evaluation
        # Read flag at call-time (not module-level) so plist env changes take effect
        import os as _os
        S2_VSA_VOLUME = _os.environ.get("S2_VSA_VOLUME", "").lower() in ("1", "true", "yes")
        _vol_buf = [b.get("v", 0) or 0 for b in bars_5m[:-3] if (b.get("v", 0) or 0) > 0]
        _rolling_avg = sum(_vol_buf[-20:]) / max(len(_vol_buf[-20:]), 1) if _vol_buf else b1_vol

        # Variant A (VSA): lower than both prior bars + below 0.7× rolling avg
        _vsa_pass = (b2_vol < b1_vol and b2_vol < b0_vol and
                     b2_vol <= 0.7 * _rolling_avg) if b1_vol > 0 else False
        # Variant B (RVOL-TOD): below 0.5× rolling avg (stricter, time-normalized proxy)
        _rvol_pass = (b2_vol <= 0.5 * _rolling_avg) if _rolling_avg > 0 else False
        # Variant C (Strict): VSA + narrow spread (b2 range < 0.7× ATR)
        _b2_range = abs(b2.get("h", 0) - b2.get("l", 0))
        _atr = self._current_atr_5m or 2.0
        _strict_pass = _vsa_pass and (_b2_range < 0.7 * _atr)

        if S2_VSA_VOLUME:
            # D-RVX: variant selector from config/s2_firing.yaml (default A_VSA)
            from backend.v9.config_loader import load_s2_firing as _load_v
            _v = _load_v()
            if   _v == "B_RVOL":        b2_drop = _rvol_pass
            elif _v == "C_STRICT":      b2_drop = _strict_pass
            elif _v == "UNION":         b2_drop = _vsa_pass or _rvol_pass or _strict_pass
            elif _v == "INTERSECTION":  b2_drop = _vsa_pass and _rvol_pass and _strict_pass
            else:                       b2_drop = _vsa_pass  # A_VSA — identical to pre-change
        else:
            b2_drop = b2_vol <= b1_vol * DROP_THRESHOLD_PCT if b1_vol > 0 else False

        # Belly confirmation from Footprint (W3-α gap 1)
        belly = self._get_belly_from_footprint()

        # Reactive LONG
        b1_sellers = b1["c"] < b1["o"] and b1_vol > 0
        b3_buyers = b3["c"] > b3["o"]
        b3_belly = belly is not False  # True or None (unavailable) both pass
        b4_confirm = b4["c"] > b4["o"]
        b4_close_above_b3_high = b4["c"] > b3["h"]  # Entry signal per Master Summary Sheet 2
        cot_above_amt = (not _require_cot_amt) or (cur_cot > cur_amt)
        poc_rising = self._poc_vol_rising(bars_5m[-3:])  # W3-α gap 3

        # Pkg 2bc · lookback: 3 bars before bar 1 must show quiet volume
        lookback = bars_5m[-MIN_BARS_REQUIRED:-(MIN_BARS_REQUIRED - LOOKBACK_BARS)]
        lookback_quiet = (
            all(b.get("v", 0) > 0 for b in lookback) and
            max(b.get("v", 0) for b in lookback) < b1_vol * LOOKBACK_MAX_VOL_RATIO
        )
        # B1: VSA gate already validates volume drop — lookback redundant
        if S2_VSA_VOLUME:
            lookback_quiet = True  # Michael approved 2026-06-02
        # Pkg 2bc · belly dominance ratio (graceful degradation)
        belly_ratio = self._get_belly_ratio_from_footprint("LONG")
        belly_ratio_ok = (belly_ratio is None) or (belly_ratio >= BELLY_DOMINANCE_RATIO)

        # D-RVX: variant tags for A/B/C
        _variants_long = {"A_VSA": _vsa_pass, "B_RVOL": _rvol_pass, "C_STRICT": _strict_pass}

        if (b1_sellers and b2_drop and b3_buyers and b3_belly
                and b4_confirm and b4_close_above_b3_high and cot_above_amt
                and lookback_quiet and belly_ratio_ok):
            _active = [k for k, v in _variants_long.items() if v]
            return ("LONG", 0.80 if poc_rising else 0.75,
                    {"kind": "REACTIVE", "stage": 4, "belly": belly, "poc_rising": poc_rising,
                     "belly_ratio": belly_ratio,
                     "variant": _active[0] if _active else "A_VSA",
                     "variants_passed": _active})

        # Reactive SHORT (mirror)
        b1_buyers = b1["c"] > b1["o"] and b1_vol > 0
        b3_sellers = b3["c"] < b3["o"]
        b4_confirm_s = b4["c"] < b4["o"]
        b4_close_below_b3_low = b4["c"] < b3["l"]  # Entry signal per Master Summary Sheet 2
        cot_below_amt = (not _require_cot_amt) or (cur_cot < cur_amt)
        poc_falling = self._poc_vol_falling(bars_5m[-3:])

        # Pkg 2bc · lookback + belly for SHORT
        belly_ratio_s = self._get_belly_ratio_from_footprint("SHORT")
        belly_ratio_ok_s = (belly_ratio_s is None) or (belly_ratio_s >= BELLY_DOMINANCE_RATIO)

        _variants_short = {"A_VSA": _vsa_pass, "B_RVOL": _rvol_pass, "C_STRICT": _strict_pass}

        if (b1_buyers and b2_drop and b3_sellers and b3_belly
                and b4_confirm_s and b4_close_below_b3_low and cot_below_amt
                and lookback_quiet and belly_ratio_ok_s):
            _active_s = [k for k, v in _variants_short.items() if v]
            return ("SHORT", 0.80 if poc_falling else 0.75,
                    {"kind": "REACTIVE", "stage": 4, "belly": belly, "poc_falling": poc_falling,
                     "belly_ratio": belly_ratio_s,
                     "variant": _active_s[0] if _active_s else "A_VSA",
                     "variants_passed": _active_s})

        return (None, 0, {})

    def _detect_initiative(self, bars_5m: List[Dict]) -> tuple:
        """Initiative 4-bar pattern per Constitution V3.

        LONG:
          Bar 1: initial expansion (6-7 ticks = 1.5-1.75 MES points)
          Bar 2: test (Higher Low / POC return)
          Bar 3: joining (range > Bar 1 range)
          Bar 4: second test = entry
          COT < AMT required.

        SHORT: Mirror of LONG.
        Returns (direction, confidence, info) or (None, 0, {}).
        """
        if len(bars_5m) < MIN_BARS_REQUIRED:
            return (None, 0, {})

        b1, b2, b3, b4 = bars_5m[-4], bars_5m[-3], bars_5m[-2], bars_5m[-1]
        cur_cot = self._get_cot_from_footprint()
        cur_amt = self._get_amt_from_footprint()
        # S2 INDEPENDENT OF S3 (Michael 2026-06-08): COT/AMT (footprint/S3) is
        # NOT required for S2 fires by default. S3 is muted/broken at this stage
        # (S3_MUTE / I-11), so S2 must fire on price-geometry + volume alone.
        # Re-require the order-flow confirmation ONLY via env S2_REQUIRE_COT_AMT=1
        # + Michael approval. See CLAUDE.md §"S2 ⟂ S3 (COT/AMT gate disabled)".
        import os as _os
        _require_cot_amt = _os.environ.get("S2_REQUIRE_COT_AMT", "").lower() in ("1", "true", "yes")
        if _require_cot_amt and (cur_cot is None or cur_amt is None):
            return (None, 0, {})

        b1_vol = b1.get("v", 0) or 0
        b1_range = b1["h"] - b1["l"]
        _exp_min, _exp_max = get_expansion_range(bars_5m)
        b1_expansion = _exp_min <= b1_range <= _exp_max
        b3_range = b3["h"] - b3["l"]
        b3_joining = b3_range > b1_range

        # Initiative LONG
        b1_bull = b1["c"] > b1["o"]
        b2_higher_low = b2["l"] > b1["l"]
        # POC return alt: Bar -2 returns to POC_VOL (within tolerance)
        b2_poc = b2.get("poc_vol") or b2.get("poc")
        _poc_tol = get_poc_return_tolerance(bars_5m)
        b2_poc_return = b2_poc is not None and abs(b2["c"] - b2_poc) <= _poc_tol
        b2_test = b2_higher_low or b2_poc_return
        b4_test = b4["l"] >= b2["l"]
        cot_below_amt = (not _require_cot_amt) or (cur_cot < cur_amt)

        b4_close_above_b1_high = b4["c"] > b1["h"]  # Entry signal per Master Summary Sheet 2

        # Pkg 2bc · lookback (no belly check for Initiative)
        lookback = bars_5m[-MIN_BARS_REQUIRED:-(MIN_BARS_REQUIRED - LOOKBACK_BARS)]
        lookback_quiet = (
            all(b.get("v", 0) > 0 for b in lookback) and
            max(b.get("v", 0) for b in lookback) < b1_vol * LOOKBACK_MAX_VOL_RATIO
        ) if b1_vol > 0 else False
        # B1: VSA gate sufficient — bypass lookback for Initiative too
        from backend.v9.shared.atr import flag as _flag
        if _flag("S2_VSA_VOLUME"):
            lookback_quiet = True  # Michael approved 2026-06-02

        if (b1_bull and b1_expansion and b2_test and b3_joining and b4_test
                and b4_close_above_b1_high and cot_below_amt and lookback_quiet):
            return ("LONG", 0.80, {"kind": "INITIATIVE", "stage": 4,
                                   "b2_alt": "poc_return" if b2_poc_return else "higher_low"})

        # Initiative SHORT (mirror)
        b1_bear = b1["c"] < b1["o"]
        b2_lower_high = b2["h"] < b1["h"]
        b2_poc_return_s = b2_poc is not None and abs(b2["c"] - b2_poc) <= _poc_tol
        b2_test_s = b2_lower_high or b2_poc_return_s
        b4_test_s = b4["h"] <= b2["h"]
        b4_close_below_b1_low = b4["c"] < b1["l"]  # Entry signal per Master Summary Sheet 2
        cot_above_amt = (not _require_cot_amt) or (cur_cot > cur_amt)

        if (b1_bear and b1_expansion and b2_test_s and b3_joining and b4_test_s
                and b4_close_below_b1_low and cot_above_amt and lookback_quiet):
            return ("SHORT", 0.80, {"kind": "INITIATIVE", "stage": 4,
                                    "b2_alt": "poc_return" if b2_poc_return_s else "lower_high"})

        return (None, 0, {})

    # ── Sizing (Cockpit V5 LOCKED — per-system internal only) ──

    def calculate_size(self, pattern_state: dict) -> str:
        """System 2 per-system internal sizing decision.

        Spec: Cockpit V5 LOCKED — NOT composite, S2 inputs ONLY.
        ⛔ NO killzone/day_type/footprint/tpo/woodies/layer_0 inputs.
        ✅ Only: bars_formed, pattern_type, direction, COT, AMT, location_vs_poc_vol.

        Returns: 'full' (3 contracts) | 'half' (2 contracts) | 'reject' (0)
        """
        bars_formed = pattern_state.get("bars_formed", 0)
        if bars_formed < 3:
            return "reject"  # Pattern not mature enough

        cot = pattern_state.get("cot", 0) or 0
        amt = pattern_state.get("amt", 0) or 0
        direction = pattern_state.get("direction")

        # COT/AMT alignment check (direction-dependent)
        if direction == "LONG":
            cot_amt_ok = cot > amt
            cot_amt_strong = amt > 0 and cot > amt * 1.2  # 🟡 1.2x threshold
        elif direction == "SHORT":
            cot_amt_ok = cot < amt
            cot_amt_strong = amt > 0 and cot < amt * 0.8  # 🟡 0.8x threshold
        else:
            return "reject"

        if not cot_amt_ok:
            return "reject"  # No flow support for direction

        location = pattern_state.get("location_vs_poc_vol", "far")  # at / near / far

        # Pristine: 4 bars + strong flow + at POC → full (3 contracts)
        if bars_formed == 4 and cot_amt_strong and location == "at":
            return "full"

        # Solid: 3+ bars + flow ok + near/at POC → half (2 contracts)
        if bars_formed >= 3 and cot_amt_ok and location in ("at", "near"):
            return "half"

        return "reject"

    def _compute_location_vs_poc(self, bar: dict) -> str:
        """Determine bar location relative to POC volume level (S2 internal).

        Uses TPO POC from Sierra export (same source as /api/v9/tpo/current).
        🟡 Thresholds: 'at' ≤ 1.0pt, 'near' ≤ 3.0pt, else 'far'.

        P31-02b: was a synchronous HTTP self-call to /api/v9/tpo/current
        (timeout=2s). Now reads the Sierra tpo.json file directly — same
        source the route uses, but bypasses HTTP roundtrip + JSON serialize
        + FastAPI loop contention. Falls back to HTTP if file load fails.
        """
        try:
            from backend.v9.api.v9.tpo_routes import _load_sierra_tpo
            tpo = _load_sierra_tpo() or {}
            # FIX 4: removed HTTP self-call fallback (deadlocked uvicorn)
            poc = tpo.get("poc")
            if poc is None:
                return "far"
            bar_mid = (bar.get("h", 0) + bar.get("l", 0)) / 2
            dist = abs(bar_mid - poc)
            if dist <= 1.0:   # 🟡 default
                return "at"
            elif dist <= 3.0:  # 🟡 default
                return "near"
            return "far"
        except Exception:
            return "far"

    # ── Bar processing ──

    def subscribed_bar_types(self):
        return ["5min"]

    _bar_buffer: List[Dict] = []

    async def process_bar(self, event) -> None:
        """Process a 5-min bar from BarRouter. Runs Reactive + Initiative detectors.

        Spec (AGENT_S2 §SHOULD_BLOCK): no pattern detection or firing during
        OVERNIGHT_MODE, MAINTENANCE, or WEEKEND — only buffer the bar for
        session context.
        """
        bar = dict(event.payload) if hasattr(event, "payload") else (event if isinstance(event, dict) else {})

        # Live session transition: advance out of OVERNIGHT_MODE when RTH opens.
        # hydrate() sets mode at startup — if backend started pre-RTH this check
        # promotes mode automatically on the first RTH bar without a restart.
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
        elif self.mode == FiveMinMode.FIRST_HOUR_TACTICAL:
            try:
                info = self.session_classifier.classify()
                if info.session == Session.CASH_HOURS:
                    self.mode = FiveMinMode.DAY_TYPE_MODE
                    logger.info("[FiveMin] Mode transition: FIRST_HOUR_TACTICAL → DAY_TYPE_MODE (live bar)")
            except Exception:
                pass

        # B-13 D3: DAY_TYPE→OVERNIGHT transition at 15:00 CT (firing close).
        # Without this, S2 stays armed in DAY_TYPE_MODE through the close and
        # will fire on any bar that passes BarRouter (including stale/corrupt).
        if self.mode in (FiveMinMode.DAY_TYPE_MODE, FiveMinMode.FIRST_HOUR_TACTICAL):
            try:
                from backend.v9.gateway.session_gate import is_after_firing_close
                if is_after_firing_close():
                    logger.info(
                        "[FiveMin] Mode transition %s → OVERNIGHT_MODE (15:00 CT close)",
                        self.mode,
                    )
                    self.mode = FiveMinMode.OVERNIGHT_MODE
            except Exception:
                pass

        # Spec: S2 must not fire outside trading sessions
        if self.mode in (FiveMinMode.OVERNIGHT_MODE, FiveMinMode.MAINTENANCE, FiveMinMode.WEEKEND):
            self.buffer_size += 1
            self._bar_buffer.append(bar)
            if len(self._bar_buffer) > 20:
                self._bar_buffer = self._bar_buffer[-20:]
            return
        bar.setdefault("o", bar.get("open", 0))
        bar.setdefault("h", bar.get("high", 0))
        bar.setdefault("l", bar.get("low", 0))
        bar.setdefault("c", bar.get("close", 0))
        bar.setdefault("vol", bar.get("volume", 0))
        bar.setdefault("v", bar.get("vol", bar.get("volume", 0)))

        # Dedup: bridge pushes same bar ~20x while building. Buffer always
        # updates (latest OHLC), but bar counting + FHB + pattern detection
        # only run on genuinely new bar timestamps.
        _bar_ts = str(bar.get("ts", ""))
        is_new_bar = _bar_ts != self._last_bar_ts_for_count
        if is_new_bar:
            self._last_bar_ts_for_count = _bar_ts
            self.buffer_size += 1
            self._bar_buffer.append(bar)
            if len(self._bar_buffer) > 20:
                self._bar_buffer = self._bar_buffer[-20:]
        elif self._bar_buffer:
            # Same bar — update last buffer entry with latest OHLC
            self._bar_buffer[-1] = bar

        if not is_new_bar:
            return  # duplicate push — skip counting, FHB, pattern detection

        # Update rolling ATR-14 from bar buffer (for relative thresholds)
        from backend.v9.shared.atr import atr_5min as _compute_atr_5m
        self._current_atr_5m = _compute_atr_5m(self._bar_buffer, period=14)

        # First Hour Buffer: advance bar count during first hour
        if self.mode == FiveMinMode.FIRST_HOUR_TACTICAL:
            self._fhb.on_bar()

        # Compute choppiness continuously (all modes, not just FIRST_HOUR)
        # so s2_inspector.choppiness_ok stays fresh in DAY_TYPE_MODE.
        # Uses last 14 bars (rolling window) for stable measurement.
        _chop_bars = self._bar_buffer[-14:] if len(self._bar_buffer) >= 5 else self._bar_buffer
        if _chop_bars:
            self.choppiness_score = int(compute_choppiness(_chop_bars))

        # D-091.Q2 · NT NO_TRADE early-skip (CPU efficiency + emit-layer defense)
        if self.current_day_type == "Nontrend":
            self._nt_skip_count += 1
            import time as _time
            _now = _time.monotonic()
            if _now - self._nt_skip_last_log_ts >= 60.0:  # rate-limit 1/min
                logger.info(
                    "[S2] NT NO_TRADE skip · cumulative=%d · D-091.Q2",
                    self._nt_skip_count,
                )
                self._nt_skip_last_log_ts = _now
            return

        # Run pattern detectors on COMPLETED bars only (Bug #3 fix 2026-06-08).
        # The bridge pushes each bar ~20x while building. Detection runs only on
        # is_new_bar (first push of a new ts), but at that point bars[-1] is the
        # NEW bar with partial OHLC (opening tick). bars[-2..-5] are already
        # complete. Using buffer[:-1] ensures b4 = the last COMPLETED bar, not
        # the partial one. FHB/ATR/choppiness above still use the full buffer.
        #
        # NOT flag-gated (deliberate): detecting on partial OHLC is always wrong
        # — it produces incorrect entry prices, wrong stops, and false pattern
        # matches. There is no valid use case for the old behavior. The trim is
        # the mathematically correct detection window given the bridge push model.
        # Cowork reviewed 2026-06-09.
        _det_buf = self._bar_buffer[:-1] if len(self._bar_buffer) >= 8 else self._bar_buffer
        direction, conf, info = self._detect_reactive(_det_buf)
        if not direction:
            direction, conf, info = self._detect_initiative(_det_buf)

        # Pkg 5a · chart patterns (Stage 3 + day-type gated · D-091 §5+§6)
        if not direction and self.mode == FiveMinMode.DAY_TYPE_MODE:
            if self.current_day_type is None:
                import time as _time_mod
                _now = _time_mod.monotonic()
                if _now - getattr(self, "_dt_none_last_warn_ts", 0.0) >= 60.0:
                    logger.warning(
                        "[FiveMin] current_day_type is None in DAY_TYPE_MODE — "
                        "Pkg 5a/5b/5c chart patterns are silently skipped. "
                        "Check hydrate() or S1 event delivery."
                    )
                    self._dt_none_last_warn_ts = _now
            if self.current_day_type in (
                "Neutral_Extreme", "Neutral_Center", "Normal", "Variation",
            ):
                direction, conf, info = detect_inverse_hns(_det_buf)
                if not direction:
                    direction, conf, info = detect_hns_top(_det_buf)
                # Pkg 5b · Double Bottom + Double Top (after H&S in chain)
                if not direction:
                    direction, conf, info = detect_double_bottom_ee(_det_buf, atr_5m=self._current_atr_5m)
                if not direction:
                    direction, conf, info = detect_double_top_aa(_det_buf, atr_5m=self._current_atr_5m)

        # Pkg 5c · Flag patterns (continuation · Stage 3 + Q5 EXPANDED day-type gate · D-091 §9+§10 + Q5)
        if not direction and self.mode == FiveMinMode.DAY_TYPE_MODE:
            if self.current_day_type in (
                "Trend_Normal", "Trend_DD", "Variation",
                "Neutral_Extreme", "Normal",
            ):
                direction, conf, info = detect_bull_flag(_det_buf)
                if not direction:
                    direction, conf, info = detect_bear_flag(_det_buf)

        # A2: per-pattern fire dedup — stateless detectors (Double Top, H&S, Flag)
        # fire on every bar after breakout. Skip same pattern+direction within cooldown.
        if direction:
            _kind = info.get("kind", "UNKNOWN")
            _dedup_key = f"{_kind}_{direction}"
            _cooldown = self._dedup_cooldown.get(_kind, 0)
            if _cooldown > 0:
                _last = self._fire_dedup.get(_dedup_key)
                if _last is not None and (self.buffer_size - _last) < _cooldown:
                    logger.debug("[FiveMin] dedup: %s skipped (fired %d bars ago, cooldown=%d)",
                                 _dedup_key, self.buffer_size - _last, _cooldown)
                    direction = None

        # First Hour Buffer eligibility gate (Tree V3.3 §Stage B)
        if direction and self.mode == FiveMinMode.FIRST_HOUR_TACTICAL:
            kind_check = info.get("kind", "UNKNOWN")
            fhb_key = f"{kind_check}_{direction}"
            if not self._fhb.is_pattern_eligible(fhb_key):
                logger.info(
                    "[FiveMin] FHB gate: %s blocked (fhb_state=%s bar=%d)",
                    fhb_key, self._fhb.state.value, self._fhb.bar_count,
                )
                direction = None

        if direction:
            kind = info.get("kind", "UNKNOWN")
            # Entry from the COMPLETED bar (last in detection buffer), not the
            # partial new bar. Bug #3 fix: consistent with detection window.
            _completed_bar = _det_buf[-1] if _det_buf else bar
            entry_price = _completed_bar.get("c", bar.get("c", 0))
            # Stop: 3-layer adaptive (D-091 §Adaptive Stop Engine · corrected 2026-05-23)
            from backend.v9.systems.five_min.adaptive_stop import compute_stop, compute_stop_v2 as s2_compute_stop_v2, compute_today_typical
            from backend.v9.shared.atr import flag as _flag
            today_typical = compute_today_typical(self._bar_buffer)  # uses today's bars in buffer
            # Pkg 5a + 5b · chart pattern routing
            if kind in ("INVERSE_HNS", "HNS_TOP"):
                family = "HnS"
                structural_anchor = info["structural_anchor"]
            elif kind in ("DOUBLE_BOTTOM_EE", "DOUBLE_TOP_AA"):
                family = "Double_BT"
                structural_anchor = info["structural_anchor"]
            elif kind in ("BULL_FLAG", "BEAR_FLAG"):
                family = "Flag"
                structural_anchor = info["structural_anchor"]
            else:
                family = "Reactive" if kind == "REACTIVE" else "OFA"
                structural_anchor = (
                    bar.get("l", entry_price) if direction == "LONG"
                    else bar.get("h", entry_price)
                )

            if _flag("STOP_ANCHORS_V2"):
                from backend.v9.config_loader import load_stop_anchors
                from backend.v9.systems.stop_anchors import resolver as SA
                cfg = load_stop_anchors()
                if cfg:
                    # Map S2 family → YAML anchor key
                    _s2_family_key = {
                        "Reactive": "Reactive", "OFA": "OFA_Initiative",
                        "Double_BT": "Double_BT", "HnS": "HnS", "Flag": "Flag",
                    }
                    a = cfg["anchors"][_s2_family_key[family]]
                    # Resolve V2 structural stop per anchor type
                    if a["type"] in ("support_zone", "breakout_bar") and a.get("window"):
                        # Cluster/breakout: window extreme + 3T offset
                        window_bars = self._bar_buffer[-a["window"]:]
                        struct = SA.resolve_anchor_from_window(
                            window_bars, direction, cfg["principles"]["anchor_offset_ticks"])
                    else:
                        # Pattern-provided structural_anchor already bakes in a
                        # 1-tick buffer (flags.py/double_bt.py/head_shoulders.py:
                        # `structure ∓ TICK_SIZE`). Strip it so apply_offset adds
                        # EXACTLY the spec's 3T from the RAW structure — uniform
                        # with the window-anchored patterns (else: 4T not 3T).
                        _tick = SA.MES_TICK
                        raw_structure = (structural_anchor + _tick) if direction == "LONG" \
                            else (structural_anchor - _tick)
                        struct = SA.apply_offset(
                            raw_structure, direction, cfg["principles"]["anchor_offset_ticks"])
                    v2_comp = s2_compute_stop_v2(
                        entry_price=entry_price,
                        direction=direction,
                        structural_stop_price=struct,
                        family=family,
                        today_typical=today_typical,
                    )
                    stop_price = v2_comp.stop_price
                    if v2_comp.cap_exceeded:
                        logger.info("[FiveMin] V2 cap_exceeded: family=%s risk=%dt cap=%dt",
                                    family, v2_comp.risk_ticks, v2_comp.atr_cap_ticks)
                else:
                    # cfg load failed → fallback to legacy
                    stop_comp = compute_stop(
                        entry_price=entry_price, direction=direction,
                        structural_anchor=structural_anchor, family=family,
                        today_typical=today_typical)
                    stop_price = stop_comp.stop_price
            else:
                stop_comp = compute_stop(
                    entry_price=entry_price,
                    direction=direction,
                    structural_anchor=structural_anchor,
                    family=family,
                    today_typical=today_typical,
                )
                stop_price = stop_comp.stop_price
                if stop_comp.reduce_size_signal:
                    logger.info("[FiveMin] adaptive_stop reduce_size: family=%s · A_tighter_than_B", family)
                    # actual size reduction handled in Pkg 3c · for now just log

            # Sizing decision (Cockpit V5 — S2 internal only)
            cot_val = info.get("cot") or self._get_cot_from_footprint() or 0
            amt_val = info.get("amt") or self._get_amt_from_footprint() or 0
            location = self._compute_location_vs_poc(bar)
            v2_sizing_result = None
            if _flag("STOP_ANCHORS_V2"):
                try:
                    from backend.v9.systems.stop_anchors.sizing import compute_v2_sizing
                    cfg = load_stop_anchors()
                    if cfg:
                        _s2_family_key = {
                            "Reactive": "Reactive", "OFA": "OFA_Initiative",
                            "Double_BT": "Double_BT", "HnS": "HnS", "Flag": "Flag",
                        }
                        _auth = None
                        try:
                            from backend.v9.config_loader import load_auth_matrix
                            _auth = load_auth_matrix()
                        except Exception:
                            pass
                        _is_rev = kind in ("INVERSE_HNS", "HNS_TOP", "DOUBLE_BOTTOM_EE", "DOUBLE_TOP_AA")
                        _trend_state = self.current_state.get("trend_state", "GRAY")
                        _day_has_dir = _trend_state in ("BLUE", "RED")
                        _with_trend = (
                            (direction == "LONG" and _trend_state == "BLUE") or
                            (direction == "SHORT" and _trend_state == "RED")
                        ) if _day_has_dir else None
                        v2_sizing_result = compute_v2_sizing(
                            entry_price=entry_price,
                            stop_price=stop_price,
                            direction=direction,
                            pattern_key=_s2_family_key[family],
                            day_type=self.current_day_type or "Normal",
                            confidence_tier="medium",
                            day_has_direction=_day_has_dir,
                            trade_with_trend=_with_trend,
                            value_area_full_traverse=None,
                            cfg=cfg,
                            auth_matrix=_auth,
                            reversal=_is_rev,
                        )
                        if v2_sizing_result is None:
                            logger.info("[FiveMin] V2 sizing: SKIP (auth verdict)")
                            sizing = "reject"
                        else:
                            _c = v2_sizing_result.contracts
                            sizing = "full" if _c >= 3 else ("half" if _c >= 2 else ("reject" if _c == 0 else "half"))
                            logger.info("[FiveMin] V2 sizing: %s contracts=%d mode=%s risk=%.1fpt",
                                        family, _c, v2_sizing_result.mode, v2_sizing_result.risk_points)
                except Exception as e:
                    logger.warning("[FiveMin] V2 sizing failed (%s) — falling back to legacy", e)
                    v2_sizing_result = None

            if v2_sizing_result is None:
                sizing = self.calculate_size({
                    "bars_formed": info.get("stage", 4),
                    "pattern_type": kind.lower(),
                    "direction": direction,
                    "cot": cot_val,
                    "amt": amt_val,
                    "location_vs_poc_vol": location,
                })

            _variant = info.get("variant", "")  # D-RVX
            self.last_pattern = f"{kind}_{direction}"
            self.last_classification = kind
            self.last_confluence = int(conf * 100)

            # ζ.H1: reasoning_notes (AP-SY02)
            reasoning_notes = (f"{kind} {direction} size={sizing}: "
                               f"{info.get('stage',4)}-bar pattern, COT={cot_val:.0f} vs AMT={amt_val:.0f}, "
                               f"location={location}")
            self.current_state["last_reasoning_notes"] = reasoning_notes

            logger.info("[FiveMin] FIRE: %s %s (conf=%.2f, size=%s, COT=%.1f, AMT=%.1f, loc=%s)",
                        kind, direction, conf, sizing, cot_val, amt_val, location)

            # A2: record fire in dedup tracker
            _dedup_key = f"{kind}_{direction}"
            self._fire_dedup[_dedup_key] = self.buffer_size

            # FIX 1+5: provisional day_type for targets + auth when UNKNOWN.
            # Computed ONCE here, used by both targets and emit_t1_setup.
            _emit_day_type = self.current_day_type
            if not _emit_day_type or _emit_day_type in ("UNKNOWN", "None"):
                try:
                    from backend.v9.systems.day_type.decision_matrix import DECISION_MATRIX
                    import importlib
                    _app = importlib.import_module("backend.v9.app").app
                    _dtm = getattr(_app.state, "day_type_machine", None)
                    if _dtm and _dtm.opening and _dtm.ib_class:
                        _key = (_dtm.opening.opening_type, _dtm.ib_class.ib_width)
                        _cell = DECISION_MATRIX.get(_key)
                        if _cell:
                            _prov = _cell.get("top1") if isinstance(_cell, dict) else _cell
                            if _prov and hasattr(_prov, 'value'):
                                _emit_day_type = _prov.value
                                logger.info("[FiveMin] provisional day_type=%s (from %s × %s)",
                                            _emit_day_type, _dtm.opening.opening_type.value,
                                            _dtm.ib_class.ib_width.value)
                except Exception:
                    pass

            # Persist to DB
            try:
                db = SessionLocal()
                from backend.v9.db.models.five_min_setups import V9FiveMinSetup
                _vp = info.get("variants_passed", [])
                # Bug #2 fix: parse ts robustly (bridge sends ISO string, not epoch)
                _raw_ts = _completed_bar.get("ts", bar.get("ts", 0))
                if isinstance(_raw_ts, str):
                    try:
                        _fire_ts = datetime.fromisoformat(_raw_ts)
                    except (ValueError, TypeError):
                        _fire_ts = datetime.now(timezone.utc)
                elif isinstance(_raw_ts, (int, float)):
                    _fire_ts = datetime.fromtimestamp(float(_raw_ts), tz=timezone.utc)
                else:
                    _fire_ts = datetime.now(timezone.utc)
                setup = V9FiveMinSetup(
                    ts=_fire_ts,
                    pattern=f"{kind}_{direction}",
                    direction=direction,
                    entry_price=entry_price,
                    stop_price=stop_price,
                    confidence=conf,
                    pattern_type=f"{kind}_{direction}",
                    setup_kind=kind,
                    bar_stage=info.get("stage", 4),
                    cot_at_fire=self._get_cot_from_footprint(),
                    amt_at_fire=self._get_amt_from_footprint(),
                    variant_tag=info.get("variant", ""),
                    variants_passed=",".join(_vp) if _vp else "",
                )
                db.add(setup)
                db.commit()
                db.close()
            except Exception as e:
                logger.warning("[FiveMin] DB persist error: %s", e)

            # Phase 5.5: Wire to setup_emitter → gateway (SHADOW auto-fire)
            try:
                pattern_name = f"{kind}_{direction}"

                # Pkg 5a + 5b · chart patterns use pattern-measure targets (NOT R-based)
                if kind in ("INVERSE_HNS", "HNS_TOP"):
                    pm = info["pattern_measure"]  # positive (head-to-neckline depth)
                    sign = 1.0 if direction == "LONG" else -1.0
                    t1_price = entry_price + sign * 0.50 * pm
                    t2_price = entry_price + sign * 0.74 * pm
                    t3_price = None  # trail per day type · Pkg 6 enforces
                elif kind == "DOUBLE_BOTTOM_EE":
                    pm = info["pattern_measure"]
                    t1_price = entry_price + 0.50 * pm
                    t2_price = entry_price + 0.66 * pm   # x0.66 haircut (D-091 §T2)
                    t3_price = None  # trail per day type · Pkg 6 enforces
                elif kind == "DOUBLE_TOP_AA":
                    pm = info["pattern_measure"]
                    t1_price = entry_price - 0.50 * pm
                    t2_price = entry_price - 0.74 * pm   # x0.74 haircut (D-091 §T2)
                    t3_price = None
                elif kind in ("BULL_FLAG", "BEAR_FLAG"):
                    # FIX 7B: Flag T1 relative to stop distance (YAML-tunable).
                    # t1_r slides linearly from 0.8 (tight stop ≤15pt) to 0.4 (wide ≥25pt).
                    pole = info["pattern_measure"]
                    sign = 1.0 if direction == "LONG" else -1.0
                    stop_dist = abs(entry_price - stop_price)

                    # Read relative T1 params from YAML (config-tunable)
                    _t1_r = 0.8  # default
                    try:
                        from backend.v9.config_loader import load_stop_anchors
                        _sa = load_stop_anchors()
                        if _sa and "flag_relative_t1" in _sa:
                            _ft = _sa["flag_relative_t1"]
                            _r_max = float(_ft.get("t1_r_max", 0.8))
                            _r_min = float(_ft.get("t1_r_min", 0.4))
                            _d_tight = float(_ft.get("dist_tight_pts", 15))
                            _d_wide = float(_ft.get("dist_wide_pts", 25))
                            if stop_dist <= _d_tight:
                                _t1_r = _r_max
                            elif stop_dist >= _d_wide:
                                _t1_r = _r_min
                            else:
                                _t1_r = _r_max - (stop_dist - _d_tight) / (_d_wide - _d_tight) * (_r_max - _r_min)
                    except Exception:
                        pass

                    t1_price = entry_price + sign * _t1_r * stop_dist
                    t3_price = None

                    full_pole = entry_price + sign * pole

                    _tpo_refs: dict = {}
                    try:
                        _tpo_refs = _load_sierra_tpo() or {}
                    except Exception as _e:
                        logger.warning("[FiveMin] Pkg 5c · Sierra TPO read failed for Flag T2: %s", _e)

                    dt = self.current_day_type
                    trail_active = False
                    if dt in ("Trend_Normal", "Variation"):
                        t2_price = full_pole
                        trail_active = True
                    elif dt == "Trend_DD":
                        cap_4r = entry_price + sign * 4.0 * stop_dist
                        t2_price = min(full_pole, cap_4r) if sign > 0 else max(full_pole, cap_4r)
                    elif dt == "Neutral_Extreme":
                        va_ref = _tpo_refs.get("vah") if direction == "LONG" else _tpo_refs.get("val")
                        if va_ref is None or va_ref <= 0:
                            logger.warning("[FiveMin] Pkg 5c · NeuE T2 fallback · VAH/VAL unavailable · using full_pole")
                            t2_price = full_pole
                        else:
                            t2_price = float(va_ref)
                    elif dt == "Normal":
                        poc_ref = _tpo_refs.get("poc")
                        if poc_ref is None or poc_ref <= 0:
                            logger.warning("[FiveMin] Pkg 5c · Norm T2 fallback · POC unavailable · using full_pole")
                            t2_price = full_pole
                        else:
                            t2_price = float(poc_ref)
                    else:
                        logger.warning("[FiveMin] Pkg 5c · unexpected day_type=%s reached Flag T2 fork", dt)
                        t2_price = full_pole

                    # Side-of-entry guard · Q5 monotonicity enforcement
                    if (direction == "LONG" and t2_price <= entry_price) or \
                       (direction == "SHORT" and t2_price >= entry_price):
                        logger.warning(
                            "[FiveMin] Pkg 5c · T2 ref behind entry (dt=%s · t2=%.2f · entry=%.2f · dir=%s) · "
                            "falling back to full_pole",
                            dt, t2_price, entry_price, direction,
                        )
                        t2_price = full_pole

                    info["trail_active"] = trail_active
                else:
                    # V2: use R-ladder T1 for Reactive/OFA when sizing result available
                    if v2_sizing_result is not None:
                        t1_price = v2_sizing_result.t1_price
                        t1_risk = abs(entry_price - stop_price)
                        t2_price = (entry_price + 2 * t1_risk) if direction == "LONG" else (entry_price - 2 * t1_risk)
                        t3_price = None
                        logger.info("[FiveMin] V2 T1=%.2f (R-ladder) risk=%.1fpt", t1_price, v2_sizing_result.risk_points)
                    else:
                        # Existing OFA path · resolve targets per day_type
                        # Use provisional day_type (_emit_day_type) when available,
                        # so targets come from the table, not generic fallback.
                        from backend.v9.systems.day_type.day_type_targets import compute_targets_for_day_type
                        _targets = compute_targets_for_day_type(
                            day_type=_emit_day_type or self.current_day_type,
                            entry_price=entry_price,
                            stop_price=stop_price,
                            direction=direction,
                        )
                        t1_risk = abs(entry_price - stop_price)
                        if _targets is not None:
                            t1_price = _targets["t1_price"]
                            t2_price = _targets.get("t2_price") or (
                                (entry_price + 2 * t1_risk) if direction == "LONG"
                                else (entry_price - 2 * t1_risk)
                            )
                            t3_price = _targets.get("t3_price")
                        else:
                            t1_price = (entry_price + t1_risk) if direction == "LONG" else (entry_price - t1_risk)
                            t2_price = (entry_price + 2 * t1_risk) if direction == "LONG" else (entry_price - 2 * t1_risk)
                            t3_price = None

                # _emit_day_type already computed above (FIX 1+5)
                # FIX 4: pass TPO data in-memory (not HTTP self-call which
                # deadlocks the single-worker uvicorn → 2s timeout).
                _tpo_for_emit = None
                try:
                    _tpo_for_emit = _load_sierra_tpo()
                except Exception:
                    pass
                t1_setup = emit_t1_setup(
                    pattern_name, direction,
                    entry_price=entry_price, stop_price=stop_price,
                    t1_price=t1_price, t2_price=t2_price,
                    bar_index=self.buffer_size,
                    day_type=_emit_day_type,
                    t3_price=t3_price,
                    current_price=entry_price,
                    tpo_data=_tpo_for_emit,
                )
                if t1_setup and self._gateway:
                    gateway_setup = build_s2_gateway_setup(t1_setup, info)
                    try:
                        self._gateway.route_setup(gateway_setup, 2)
                        logger.info("[FiveMin] Auto-routed: %s %s → gateway SHADOW", pattern_name, direction)
                    except Exception as gw_err:
                        logger.warning("[FiveMin] Gateway route_setup failed: %s", gw_err)
                elif t1_setup:
                    logger.info("[FiveMin] T1Setup emitted but no gateway injected: %s", pattern_name)
            except Exception as emit_err:
                logger.error("[FiveMin] emit_t1_setup failed (non-fatal): %s", emit_err)

    def get_state(self) -> dict:
        """Current system state for API/status."""
        return {
            "running": self._hydrated,
            "hydrated": self._hydrated,
            "mode": self.mode,
            "buffer_size": self.buffer_size,
            "opening_type": self.opening_type,
            "last_pattern": self.last_pattern,
            "last_confluence": self.last_confluence,
            "last_classification": self.last_classification,
            "last_reasoning_notes": self.current_state.get("last_reasoning_notes"),
        }

    def get_current(self) -> dict:
        """Snapshot for cross-context capture at trade fire time (RCA-2)."""
        return self.get_state()
