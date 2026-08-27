"""FiveMinSystem — 5-min Decision Maker with full D-077 lifecycle.

Implements hydrate() for cold start scenarios (Addendum Section 1).
Uses SessionClassifier (D-083) — never raw time checks.
"""

import logging
import os
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


def _s2_ledger(event_type, *, pattern, direction, signal_bar_ts, **kwargs):
    try:
        from backend.v9.services.candidate_ledger import enabled, record
        if not enabled():
            return None
        return record(
            event_type,
            system_id=2,
            pattern=str(pattern or ""),
            direction=direction,
            signal_bar_ts=signal_bar_ts,
            family="S2",
            **kwargs,
        )
    except Exception:
        return None
from backend.v9.api.v9.tpo_routes import _load_sierra_tpo

logger = logging.getLogger("mems26.systems.five_min")


def _canon_bar_ts(raw) -> str:
    """F2 (2026-08-12): canonical UTC key for the process_bar dedup.

    The old dedup compared the RAW ts string, so the same instant arriving as
    "2026-08-11 16:20:00+00:00" (Sierra path, str(datetime)) and
    "2026-08-11T16:20:00+00:00" (aggregator path, isoformat()) counted as TWO
    new bars — every 5-min bar entered the S2 buffer twice from two different
    price series (SYSTEM2_FULL_AUDIT §7). Normalise datetime / epoch / ISO
    ('T' or ' ', 'Z' or offset, naive → assume UTC) to one aware-UTC ISO
    string; unparseable input falls back to the raw string (never raises).
    """
    if isinstance(raw, datetime):
        dt = raw
    else:
        s = str(raw or "").strip()
        if not s:
            return ""
        try:
            if s.replace(".", "", 1).isdigit():          # epoch seconds
                dt = datetime.fromtimestamp(float(s), tz=timezone.utc)
            else:
                dt = datetime.fromisoformat(s.replace("Z", "+00:00").replace(" ", "T"))
        except (ValueError, OSError, OverflowError):
            return s
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


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

# ── Pkg 5a/5c day-type gates (D-091 §5+§6 / §9+§10+Q5) ──
# Default lists = pre-2026-06-12 behavior exactly. Flag S2_CHART_ALL_DAYTYPES=1
# (Michael approved 2026-06-12, anchor-trial observation day) opens chart patterns
# to ALL day types. Nontrend stays excluded — the NT NO_TRADE early-skip upstream
# (D-091.Q2) returns before detection regardless, and we keep it explicit here.
_PKG5A_DAYTYPES = ("Neutral_Extreme", "Neutral_Center", "Normal", "Variation")
_PKG5C_DAYTYPES = ("Trend_Normal", "Trend_DD", "Variation", "Neutral_Extreme", "Normal")


# ── Volatility-adaptive S2 geometry (Michael 2026-06-12) ──
# On VOLATILE days (avg 14-bar range ≥ S2_VOL_REGIME_PT) the fixed geometry rules
# interact badly with giant bars: (1) REACTIVE's "b4 closes beyond b3's full
# extreme" failed 18/18 bars on 06-12; (2) INITIATIVE's relative expansion floor
# (1.3×avg) inflates to 20-25pt demands. Flag S2_VOL_ADAPTIVE=1 (default OFF)
# relaxes BOTH only while the volatile regime is active; calm days unchanged.
_VOL_REGIME_PT = 8.0          # avg 14-bar range ≥ this ⇒ VOLATILE (env S2_VOL_REGIME_PT)
_VOL_CONFIRM_FRACTION = 0.75  # b4 must close beyond 75% of b3's range (not 100%)
_VOL_EXP_FLOOR_CAP_PT = 8.0   # absolute cap on Initiative expansion floor
_VOL_JOIN_FACTOR = 0.8        # Initiative b3_joining: b3_range > 0.8×b1_range


def vol_adaptive_active(bars) -> bool:
    """True only when flag ON and the live volatility regime is VOLATILE."""
    import os as _os
    if _os.environ.get("S2_VOL_ADAPTIVE", "").lower() not in ("1", "true", "yes"):
        return False
    if not bars or len(bars) < 5:
        return False
    win = bars[-14:]
    avg = sum((b.get("h", 0) - b.get("l", 0)) for b in win) / len(win)
    try:
        thr = float(_os.environ.get("S2_VOL_REGIME_PT", _VOL_REGIME_PT))
    except ValueError:
        thr = _VOL_REGIME_PT
    return avg >= thr


def reactive_confirm_threshold(b3_high: float, b3_low: float, direction: str, adaptive: bool) -> float:
    """Price b4 must close beyond. Non-adaptive: b3's full extreme (original rule)."""
    rng = b3_high - b3_low
    if not adaptive or rng <= 0:
        return b3_high if direction == "LONG" else b3_low
    if direction == "LONG":
        return b3_high - (1.0 - _VOL_CONFIRM_FRACTION) * rng
    return b3_low + (1.0 - _VOL_CONFIRM_FRACTION) * rng


def chart_patterns_allowed(day_type, pkg: str) -> bool:
    """Day-type gate for Pkg 5a (HnS/Double) and 5c (Flags) chart patterns.

    Flag OFF (default): exact pre-existing allow-lists. Flag ON: any known
    day_type except Nontrend. None/UNKNOWN never pass (S1 not ready).
    """
    if not day_type or day_type in ("UNKNOWN", "Nontrend"):
        return False
    import os as _os
    if _os.environ.get("S2_CHART_ALL_DAYTYPES", "").lower() in ("1", "true", "yes"):
        return True
    return day_type in (_PKG5A_DAYTYPES if pkg == "5a" else _PKG5C_DAYTYPES)

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


# ── S2_ADAPTIVE_THRESHOLDS_V1 (Michael 2026-08-19 ~19:15) ──
# "לשלוח סוכן שיבצע התאמה לספים בהתאם לגודל הנר וסוג היום... אני רוצה פיתרון
#  חכם שמותאם לסוג היום ולגודל הנרות — זה יחסי בסוף"
# Audit finding (2026-08-19): INITIATIVE's b1_expansion floor (1.3×avg14)
# demanded ~7.5pt while the day's real closed-bar ranges ran 1.5-4.5pt —
# mathematically unreachable on grind days (open bars inflate the mean).
# REACTIVE's b2 volume gate demanded ≤10% of b1 (a 90% drop — near-impossible).
# Under the flag, both thresholds derive from the bars themselves:
#   expansion: b1 range ≥ max(P80 of last-20 closed-bar ranges, 0.55×ATR14),
#              ×0.85 on Trend*/Variation day types (None/UNKNOWN → ×1.0).
#              P80 is outlier-robust where the mean is not — relative by
#              construction, no fixed points anywhere.
#   b2 drop:   b2_vol < b1_vol AND b2_vol ≤ 0.8×avg20 (the VSA-style relative
#              variant already proven in the S2_VSA_VOLUME path).
# Flag OFF (default, code-level) → byte-identical legacy behavior.
_ADAPTIVE_EXP_LOOKBACK = 20    # closed bars in the P80 window
_ADAPTIVE_EXP_PCTL = 0.80      # percentile of ranges (nearest-rank)
_ADAPTIVE_ATR_K = 0.55         # ATR14 fraction floor
_ADAPTIVE_TREND_MULT = 0.85    # multiplier on trend/variation day types
_ADAPTIVE_B2_AVG_K = 0.8       # b2_vol ≤ this × rolling avg20


def s2_adaptive_thresholds_on() -> bool:
    """Call-time flag read (env changes take effect without reimport)."""
    import os as _os
    return _os.environ.get("S2_ADAPTIVE_THRESHOLDS_V1", "").lower() in ("1", "true", "yes")


def adaptive_daytype_mult(day_type) -> float:
    """×0.85 on directional day types (Trend_* / *Variation*); UNKNOWN/None → 1.0.

    Covers both spellings live in this codebase: "Variation" (PKG5A list) and
    "Normal_Variation" (7-type classifier / TREND_STOP_FLOOR).
    """
    if not day_type or not isinstance(day_type, str):
        return 1.0
    if day_type.startswith("Trend") or "Variation" in day_type:
        return _ADAPTIVE_TREND_MULT
    return 1.0


def adaptive_expansion_floor(bars: _Opt[list], atr14: _Opt[float] = None,
                             day_type: _Opt[str] = None) -> _Opt[float]:
    """S2_ADAPTIVE_THRESHOLDS_V1 expansion floor (points), or None if no bars.

    max(P80 of last-20 closed-bar ranges, 0.55×ATR14) × day-type multiplier.
    ATR None (cold start, <14 bars) → the P80 term alone — no synthetic ATR
    (Rule 1: honest failure > synthetic value).
    """
    if not bars:
        return None
    window = bars[-_ADAPTIVE_EXP_LOOKBACK:]
    ranges = sorted(
        (b.get("h", b.get("high", 0)) or 0) - (b.get("l", b.get("low", 0)) or 0)
        for b in window
    )
    if not ranges:
        return None
    import math as _math
    idx = max(0, min(len(ranges) - 1,
                     _math.ceil(_ADAPTIVE_EXP_PCTL * len(ranges)) - 1))
    p80 = ranges[idx]
    atr_term = _ADAPTIVE_ATR_K * atr14 if atr14 else 0.0
    return max(p80, atr_term) * adaptive_daytype_mult(day_type)


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
            "candidate_id": info.get("candidate_id"),
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
        # 2026-08-19 audit (S2-F3): _bar_buffer was ONLY a class attribute, so
        # every FiveMinSystem() shared one list — /api/v9/status hydrates a
        # scratch instance per poll and appended stale DB bars into the SAME
        # buffer the live instance detects on (unbounded leak + replay-bar
        # injection). Instance-own the buffer.
        self._bar_buffer: List[Dict] = []
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
                           "BULL_FLAG": 20, "BEAR_FLAG": 20,
                           "RE_PULLBACK": 12}
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
                    # ROOT-FIX 2026-08-13 (mac-2 restart → S2 dead all session):
                    # v9_bars_5min is the LEGACY table (superseded by
                    # v9_bars_5min_woodies — see docs/SOURCE_OF_TRUTH.md). On a
                    # clean machine it is empty, so the buffer came up EMPTY
                    # after every restart: no CCI history, no recency → all 14
                    # S2 patterns blocked. Fall back to the canonical live table.
                    if not rows:
                        from backend.v9.db.models.bars_woodies import V9Bar5MinWoodies as _W
                        rows = (
                            db.query(_W)
                            .order_by(_W.ts.desc())
                            .limit(60)
                            .all()
                        )
                        if rows:
                            logger.info(
                                "[FiveMin] legacy v9_bars_5min empty → hydrated %d bars "
                                "from v9_bars_5min_woodies (canonical)", len(rows))
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
                # ROOT-FIX 2026-08-13 (mac-2 lost the whole first hour after a
                # 17:00 IL emergency restart): the replay above fills _bar_buffer
                # but left the FirstHourBuffer at zero — a mid-first-hour boot
                # stayed ACCUMULATING/UNKNOWN → fhb_eligible=False until the
                # 10:30 ET mode flip. Rebuild the FHB from the bars the session
                # has ALREADY printed (same on_bar path, deterministic).
                try:
                    from datetime import datetime as _fhb_dt, time as _fhb_t
                    from zoneinfo import ZoneInfo as _fhb_zi
                    _fhb_et = _fhb_zi("America/New_York")
                    _rth_seen = 0
                    for _b in self._bar_buffer:
                        try:
                            _bts = _b.get("ts") or ""
                            _bdt = _fhb_dt.fromisoformat(str(_bts).replace("Z", "+00:00"))
                            _bet = _bdt.astimezone(_fhb_et)
                            if (_bet.date() == _fhb_dt.now(_fhb_et).date()
                                    and _bet.time() >= _fhb_t(9, 30)):
                                _rth_seen += 1
                        except Exception:
                            continue
                    for _ in range(min(_rth_seen, 13)):
                        self._fhb.on_bar()
                    if _rth_seen:
                        logger.info("[FiveMin] FHB rebuilt from replay: %d RTH bars → state=%s",
                                    _rth_seen, self._fhb.state.value)
                except Exception as _fhb_err:
                    logger.warning("[FiveMin] FHB rebuild failed (non-fatal): %s", _fhb_err)
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

    # ── CVD confirmation for S2 detection (S2_CVD_DETECTION_V1) ──

    def _compute_setup_cvd(self, bars_5m: List[Dict], window: int = 4) -> Optional[Dict]:
        """Compute CVD features over the setup window (last `window` bars).

        Returns dict with:
          net_delta: cvd[last] - cvd[first] (positive = buying, negative = selling)
          perbar_deltas: list of per-bar deltas [d1, d2, ...] (diff of consecutive cumulatives)
          cumulatives: raw cumulative values aligned to the window
        Or None if CVD data is unavailable/stale.
        Fail-safe: any error → None (caller proceeds without CVD).
        Source: v9_bars_cumulative_delta (live CVD stream, NOT v9_bars_5min).
        """
        try:
            from backend.v9.db.read import read_all
            bar_timestamps = [b.get("ts") for b in bars_5m[-window:] if b.get("ts")]
            if len(bar_timestamps) < 2:
                return None
            first_ts, last_ts = bar_timestamps[0], bar_timestamps[-1]
            # Gap #1 fix: str(datetime) uses space separator but the
            # varchar column stores ISO with 'T'.  The lexicographic
            # comparison ' ' < 'T' means ts <= :t1 NEVER matched —
            # the CVD gate was a complete no-op in production (0/76
            # windows on 08-21).  Use .isoformat() to match the stored
            # format.  NOTE: this ENABLES a gate that never ran; the
            # gate itself is fail-open (returns None → caller proceeds).
            def _iso(ts):
                if hasattr(ts, 'isoformat'):
                    return ts.isoformat()
                s = str(ts)
                # str(datetime) uses space; replace with T
                if len(s) > 10 and s[10] == ' ':
                    return s[:10] + 'T' + s[11:]
                return s
            rows = read_all(
                "SELECT cumulative FROM v9_bars_cumulative_delta "
                "WHERE ts >= :t0 AND ts <= :t1 ORDER BY ts ASC",
                {"t0": _iso(first_ts), "t1": _iso(last_ts)},
            )
            cums = [float(r["cumulative"]) for r in rows
                    if r.get("cumulative") is not None]
            if len(cums) < window:
                # A1 (map §S2-6): CVD ran on 2-3 rows 55.4% of the time,
                # producing an artifact worth $585.  Rule 1: honest failure
                # when the window isn't fully covered.
                if cums:
                    logger.warning(
                        "[S2-CVD] insufficient coverage: %d/%d rows — "
                        "returning None (Rule 1)", len(cums), window)
                return None
            perbar = [cums[i] - cums[i - 1] for i in range(1, len(cums))]
            return {
                "net_delta": cums[-1] - cums[0],
                "perbar_deltas": perbar,
                "cumulatives": cums,
            }
        except Exception:
            return None

    @staticmethod
    def _cvd_delta_read(cvd_data: Optional[Dict], direction: str,
                        bars_window: List[Dict]) -> Dict:
        """Michael ruling 23.08: interpretive CVD reading per setup.

        Returns {reading, slope, entry_bar_delta, divergence, numbers}.
        reading ∈ {SUPPORTING, OPPOSING, ABSORPTION, MISSING}.
        """
        if cvd_data is None:
            return {"reading": "MISSING", "reason": "no CVD data in window"}
        pb = cvd_data.get("perbar_deltas", [])
        cums = cvd_data.get("cumulatives", [])
        net = cvd_data.get("net_delta", 0)
        entry_d = pb[-1] if pb else 0
        is_long = direction == "LONG"
        slope_with = (net > 0) if is_long else (net < 0)
        noise_threshold = 50  # delta units
        # Absorption: price makes new extreme but CVD doesn't
        absorption = False
        if len(cums) >= 3 and bars_window:
            prices = [b.get("h", 0) for b in bars_window] if is_long else [b.get("l", 0) for b in bars_window]
            price_new_ext = (bars_window[-1].get("h", 0) >= max(prices[:-1]) if is_long
                            else bars_window[-1].get("l", 0) <= min(prices[:-1]))
            cvd_ext_fn = max if is_long else min
            cvd_new_ext = (cums[-1] >= cvd_ext_fn(cums[:-1]) if is_long
                          else cums[-1] <= cvd_ext_fn(cums[:-1]))
            if price_new_ext and not cvd_new_ext:
                absorption = True
        if absorption:
            reading = "ABSORPTION"
            reason = f"price extreme but CVD diverges (net={net:.0f})"
        elif abs(net) < noise_threshold:
            reading = "SUPPORTING" if slope_with else "MISSING"
            reason = f"net delta {net:.0f} below noise threshold"
        elif slope_with:
            reading = "SUPPORTING"
            reason = f"CVD slope WITH {direction} (net={net:.0f})"
        else:
            reading = "OPPOSING"
            reason = f"CVD slope AGAINST {direction} (net={net:.0f})"
        return {
            "reading": reading,
            "slope_net": round(net, 1),
            "entry_bar_delta": round(entry_d, 1),
            "absorption": absorption,
            "reason": reason,
        }

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
        for _b in (b1, b2, b3, b4):
            _b.setdefault("c", _b.get("close", 0)); _b.setdefault("o", _b.get("open", 0))
            _b.setdefault("h", _b.get("high", 0)); _b.setdefault("l", _b.get("low", 0))
            _b.setdefault("v", _b.get("volume", 0))
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
        elif s2_adaptive_thresholds_on():
            # S2_ADAPTIVE_THRESHOLDS_V1 (Michael 2026-08-19): VSA-style relative drop.
            # S2_REACTIVE_DAYTYPE_V1 (Michael 2026-08-20): per-day-type coefficients
            # from config/s2_reactive_calibration.yaml.
            _b2k = _ADAPTIVE_B2_AVG_K
            _b2_vs_b1_k = 1.0
            if _os.environ.get("S2_REACTIVE_DAYTYPE_V1", "").lower() in ("1", "true", "yes"):
                try:
                    from backend.v9.config_loader import load_s2_reactive_calibration as _lrc
                    from backend.v9.services.trade_context import get_live_day_type as _gldt2
                    _rdt = _gldt2()
                    _rcal = _lrc(_rdt)
                    _vol_cal = _rcal.get("volume", {})
                    _b2k = float(_vol_cal.get("b2_avg_k", _ADAPTIVE_B2_AVG_K))
                    _b2_vs_b1_k = float(_vol_cal.get("b2_vs_b1", 1.0))
                except Exception:
                    pass
            b2_drop = (b2_vol < b1_vol * _b2_vs_b1_k
                       and b2_vol <= _b2k * _rolling_avg) if b1_vol > 0 else False
        else:
            b2_drop = b2_vol <= b1_vol * DROP_THRESHOLD_PCT if b1_vol > 0 else False

        # Belly confirmation from Footprint (W3-α gap 1)
        belly = self._get_belly_from_footprint()

        # Reactive LONG
        b1_sellers = b1["c"] < b1["o"] and b1_vol > 0
        b3_buyers = b3["c"] > b3["o"]
        b3_belly = belly is not False  # True or None (unavailable) both pass
        b4_confirm = b4["c"] > b4["o"]
        # Entry signal per Master Summary Sheet 2; volatile regime relaxes to 75% of b3 range
        _vol_adaptive = vol_adaptive_active(bars_5m)
        _confirm_thr = reactive_confirm_threshold(b3["h"], b3["l"], "LONG", _vol_adaptive)
        b4_close_above_b3_high = b4["c"] > _confirm_thr
        # S2_REACTIVE_DAYTYPE_V1: ATR-relative geometry tolerance per day-type
        if (not b4_close_above_b3_high
                and _os.environ.get("S2_REACTIVE_DAYTYPE_V1", "").lower() in ("1", "true", "yes")):
            try:
                if '_rcal' not in dir():
                    from backend.v9.config_loader import load_s2_reactive_calibration as _lrc
                    from backend.v9.services.trade_context import get_live_day_type as _gldt2
                    _rcal = _lrc(_gldt2())
                _tol = float(_rcal.get("geometry", {}).get("confirm_tol_atr", 0)) * _atr
                b4_close_above_b3_high = b4["c"] >= (_confirm_thr - _tol)
            except Exception:
                pass
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

        # Item-5: b4 volume rising (S2_B4_VOL_V1, default OFF)
        b4_vol = b4.get("v", 0) or 0
        b3_vol = b3.get("v", 0) or 0
        import os as _b4v_os
        _b4_vol_ok = True
        if _b4v_os.environ.get("S2_B4_VOL_V1", "").lower() in ("1", "true", "yes"):
            _b4_vol_ok = b4_vol > b3_vol
            if not _b4_vol_ok:
                logger.info("[S2-B4VOL] REACTIVE LONG rejected: b4_vol=%d <= b3_vol=%d", b4_vol, b3_vol)

        if (b1_sellers and b2_drop and b3_buyers and b3_belly
                and b4_confirm and b4_close_above_b3_high and cot_above_amt
                and lookback_quiet and belly_ratio_ok and _b4_vol_ok):
            # S2_CVD_DETECTION_V1: REACTIVE LONG = fade sellers → CVD must show
            # absorption: perbar_delta(B4) > 0 (buyers at entry bar) OR bullish
            # divergence (price made lower low B1→B3 but CVD made higher low).
            import os as _cvd_os
            _cvd_mode = _cvd_os.environ.get("S2_CVD_DETECTION_V1", "").lower()
            if _cvd_mode in ("1", "true", "yes", "shadow"):
                _cvd = self._compute_setup_cvd(bars_5m, window=4)
                _dr = self._cvd_delta_read(_cvd, "LONG", bars_5m[-4:])
                logger.info("[S2-CVD] REACTIVE LONG delta_read=%s: %s",
                            _dr["reading"], _dr["reason"])
                if _cvd is not None:
                    _pb = _cvd["perbar_deltas"]
                    _entry_bar_buying = _pb[-1] > 0 if _pb else False
                    _cums = _cvd["cumulatives"]
                    _price_ll = b3["l"] < b1["l"] if len(_cums) >= 3 else False
                    _cvd_hl = _cums[-2] > _cums[0] if len(_cums) >= 3 else False
                    _divergence = _price_ll and _cvd_hl
                    if not (_entry_bar_buying or _divergence) and _cvd_mode != "shadow":
                        logger.info("[S2-CVD] REACTIVE LONG rejected: no absorption (entry_delta=%.0f, div=%s)",
                                    _pb[-1] if _pb else 0, _divergence)
                        return (None, 0, {})  # fall through to INITIATIVE
            _active = [k for k, v in _variants_long.items() if v]
            # cc-1: structural anchor = min low of b1..b3 (demand zone floor for LONG)
            _struct_anchor_l = min(b1["l"], b2["l"], b3["l"])
            return ("LONG", 0.80 if poc_rising else 0.75,
                    {"kind": "REACTIVE", "stage": 4, "belly": belly, "poc_rising": poc_rising,
                     "belly_ratio": belly_ratio,
                     "variant": _active[0] if _active else "A_VSA",
                     "variants_passed": _active,
                     "structural_anchor": _struct_anchor_l})

        # Reactive SHORT (mirror)
        b1_buyers = b1["c"] > b1["o"] and b1_vol > 0
        b3_sellers = b3["c"] < b3["o"]
        b4_confirm_s = b4["c"] < b4["o"]
        # Entry signal per Master Summary Sheet 2; volatile regime relaxes to 75% of b3 range
        _confirm_thr_s = reactive_confirm_threshold(b3["h"], b3["l"], "SHORT", _vol_adaptive)
        b4_close_below_b3_low = b4["c"] < _confirm_thr_s
        # S2_REACTIVE_DAYTYPE_V1: ATR-relative geometry tolerance (SHORT mirror)
        if (not b4_close_below_b3_low
                and _os.environ.get("S2_REACTIVE_DAYTYPE_V1", "").lower() in ("1", "true", "yes")):
            try:
                if '_rcal' not in dir():
                    from backend.v9.config_loader import load_s2_reactive_calibration as _lrc
                    from backend.v9.services.trade_context import get_live_day_type as _gldt2
                    _rcal = _lrc(_gldt2())
                _tol = float(_rcal.get("geometry", {}).get("confirm_tol_atr", 0)) * _atr
                b4_close_below_b3_low = b4["c"] <= (_confirm_thr_s + _tol)
            except Exception:
                pass
        cot_below_amt = (not _require_cot_amt) or (cur_cot < cur_amt)
        poc_falling = self._poc_vol_falling(bars_5m[-3:])

        # Pkg 2bc · lookback + belly for SHORT
        belly_ratio_s = self._get_belly_ratio_from_footprint("SHORT")
        belly_ratio_ok_s = (belly_ratio_s is None) or (belly_ratio_s >= BELLY_DOMINANCE_RATIO)

        _variants_short = {"A_VSA": _vsa_pass, "B_RVOL": _rvol_pass, "C_STRICT": _strict_pass}

        # Item-5: b4 volume rising for SHORT (same flag)
        _b4_vol_ok_s = True
        if _b4v_os.environ.get("S2_B4_VOL_V1", "").lower() in ("1", "true", "yes"):
            _b4_vol_ok_s = b4_vol > b3_vol
            if not _b4_vol_ok_s:
                logger.info("[S2-B4VOL] REACTIVE SHORT rejected: b4_vol=%d <= b3_vol=%d", b4_vol, b3_vol)

        if (b1_buyers and b2_drop and b3_sellers and b3_belly
                and b4_confirm_s and b4_close_below_b3_low and cot_below_amt
                and lookback_quiet and belly_ratio_ok_s and _b4_vol_ok_s):
            # S2_CVD_DETECTION_V1: REACTIVE SHORT = fade buyers → CVD must show
            # distribution: perbar_delta(B4) < 0 (selling at entry bar) OR bearish
            # divergence (price HH B1→B3 but CVD LH), and/or net selling slope.
            import os as _cvd_os2
            _cvd_mode2 = _cvd_os2.environ.get("S2_CVD_DETECTION_V1", "").lower()
            if _cvd_mode2 in ("1", "true", "yes", "shadow"):
                _cvd = self._compute_setup_cvd(bars_5m, window=4)
                _dr_s = self._cvd_delta_read(_cvd, "SHORT", bars_5m[-4:])
                logger.info("[S2-CVD] REACTIVE SHORT delta_read=%s: %s",
                            _dr_s["reading"], _dr_s["reason"])
                if _cvd is not None:
                    _pb_s = _cvd["perbar_deltas"]
                    _entry_bar_selling = _pb_s[-1] < 0 if _pb_s else False
                    _net_selling = _cvd["net_delta"] < 0
                    _cums_s = _cvd["cumulatives"]
                    _price_hh = b3["h"] > b1["h"] if len(_cums_s) >= 3 else False
                    _cvd_lh = _cums_s[-2] < _cums_s[0] if len(_cums_s) >= 3 else False
                    _divergence_s = _price_hh and _cvd_lh
                    if not (_entry_bar_selling or _net_selling or _divergence_s) and _cvd_mode2 != "shadow":
                        logger.info("[S2-CVD] REACTIVE SHORT rejected: no distribution (entry_delta=+%.0f, net=+%.0f, div=%s)",
                                    _pb_s[-1] if _pb_s else 0, _cvd["net_delta"], _divergence_s)
                        return (None, 0, {})  # fall through to INITIATIVE
            _active_s = [k for k, v in _variants_short.items() if v]
            # cc-1: structural anchor = max high of b1..b3 (supply zone ceiling for SHORT)
            _struct_anchor_s = max(b1["h"], b2["h"], b3["h"])
            return ("SHORT", 0.80 if poc_falling else 0.75,
                    {"kind": "REACTIVE", "stage": 4, "belly": belly, "poc_falling": poc_falling,
                     "belly_ratio": belly_ratio_s,
                     "variant": _active_s[0] if _active_s else "A_VSA",
                     "variants_passed": _active_s,
                     "structural_anchor": _struct_anchor_s})

        # S2_DETECTION_LOG: per-bar condition vector (observability, flag-gated)
        import os as _dl_os
        if _dl_os.environ.get("S2_DETECTION_LOG", "").lower() in ("1", "true", "yes"):
            _bar_ts = bars_5m[-1].get("ts", "?") if bars_5m else "?"
            logger.info(
                "[S2-DL] REACTIVE ts=%s L:[b1s=%d b2d=%d b3b=%d b4c=%d b4>h=%d] "
                "S:[b1b=%d b3s=%d b4c=%d b4<l=%d] vsa=%d rvol=%d",
                _bar_ts,
                int(b1_sellers), int(b2_drop), int(b3_buyers), int(b4_confirm), int(b4_close_above_b3_high),
                int(b1_buyers), int(b3_sellers), int(b4_confirm_s), int(b4_close_below_b3_low),
                int(_vsa_pass), int(_rvol_pass),
            )

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
        for _b in (b1, b2, b3, b4):
            _b.setdefault("c", _b.get("close", 0)); _b.setdefault("o", _b.get("open", 0))
            _b.setdefault("h", _b.get("high", 0)); _b.setdefault("l", _b.get("low", 0))
            _b.setdefault("v", _b.get("volume", 0))
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
        # Volatile regime (S2_VOL_ADAPTIVE): cap the expansion floor at an absolute
        # value and relax joining — the relative floor inflates on giant-bar days.
        _vol_adaptive_i = vol_adaptive_active(bars_5m)
        if _vol_adaptive_i:
            _exp_min = min(_exp_min, _VOL_EXP_FLOOR_CAP_PT)
        b1_expansion = _exp_min <= b1_range <= _exp_max
        if s2_adaptive_thresholds_on():
            # S2_ADAPTIVE_THRESHOLDS_V1 (Michael 2026-08-19): relative expansion
            # — b1 range ≥ max(P80 of last-20 closed ranges, 0.55×ATR14), ×0.85
            # on Trend/Variation days (live label the system already carries;
            # None/UNKNOWN → ×1.0). Replaces the 1.3×avg14 floor that demanded
            # ~7.5pt on a 1.5-4.5pt day. P80 is outlier-robust; no upper cap —
            # the floor tracks the tape by construction.
            _adaptive_floor = adaptive_expansion_floor(
                bars_5m, atr14=self._current_atr_5m,
                day_type=self.current_day_type)
            if _adaptive_floor is not None:
                b1_expansion = b1_range >= _adaptive_floor
        b3_range = b3["h"] - b3["l"]
        _join_req = b1_range * (_VOL_JOIN_FACTOR if _vol_adaptive_i else 1.0)
        # S2_INITIATIVE_JOIN_ATR_CAP_V1 (Michael 2026-08-20, A2): cap the joining
        # requirement at 0.55×ATR so an explosive b1 (12.60pt) doesn't demand an
        # impossible b3 (10.08pt). 6/7 at two pivot points failed on 7.00 vs 12.60.
        if _os.environ.get("S2_INITIATIVE_JOIN_ATR_CAP_V1", "").lower() in ("1", "true", "yes"):
            # 2026-08-21 P0 HOTFIX: this read `_atr`, a LOCAL of _detect_reactive
            # (:818) — NameError on EVERY bar, which crashed process_bar and took
            # the whole of S2 down with it (19/19 bars today; the chart-pattern
            # detectors at :1755, incl. DOUBLE_BOTTOM, were never reached — a
            # 22.25pt setup missed). Use the instance attribute, like :1068/:1755.
            _atr_i = self._current_atr_5m
            _join_atr_cap = 0.55 * (_atr_i or 5.0)
            if _join_req > _join_atr_cap:
                logger.debug("[S2-JOIN-CAP] b3_join req %.2f capped to %.2f (ATR=%.2f)",
                             _join_req, _join_atr_cap, _atr_i or 0)
                _join_req = _join_atr_cap
        b3_joining = b3_range > _join_req

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
            # S2_CVD_DETECTION_V1: INITIATIVE LONG = with-flow → net buying
            # over the breakout window (cvd[B4] - cvd[B1] > 0).
            import os as _cvd_os3
            _cvd_mode3 = _cvd_os3.environ.get("S2_CVD_DETECTION_V1", "").lower()
            if _cvd_mode3 in ("1", "true", "yes", "shadow"):
                _cvd_i = self._compute_setup_cvd(bars_5m, window=4)
                _dr_il = self._cvd_delta_read(_cvd_i, "LONG", bars_5m[-4:])
                logger.info("[S2-CVD] INITIATIVE LONG delta_read=%s: %s",
                            _dr_il["reading"], _dr_il["reason"])
                if _cvd_i is not None and _cvd_i["net_delta"] < 0 and _cvd_mode3 != "shadow":
                    logger.info("[S2-CVD] INITIATIVE LONG rejected: net_delta=%.0f (selling against breakout)", _cvd_i["net_delta"])
                    return (None, 0, {})
            # cc-1: structural anchor = min low of b1..b3 for LONG
            _ini_anchor_l = min(b1["l"], b2["l"], b3["l"])
            return ("LONG", 0.80, {"kind": "INITIATIVE", "stage": 4,
                                   "b2_alt": "poc_return" if b2_poc_return else "higher_low",
                                   "structural_anchor": _ini_anchor_l})

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
            # S2_CVD_DETECTION_V1: INITIATIVE SHORT = with-flow → net selling
            # over the breakdown window (cvd[B4] - cvd[B1] < 0).
            import os as _cvd_os4
            _cvd_mode4 = _cvd_os4.environ.get("S2_CVD_DETECTION_V1", "").lower()
            if _cvd_mode4 in ("1", "true", "yes", "shadow"):
                _cvd_i = self._compute_setup_cvd(bars_5m, window=4)
                _dr_is = self._cvd_delta_read(_cvd_i, "SHORT", bars_5m[-4:])
                logger.info("[S2-CVD] INITIATIVE SHORT delta_read=%s: %s",
                            _dr_is["reading"], _dr_is["reason"])
                if _cvd_i is not None and _cvd_i["net_delta"] > 0 and _cvd_mode4 != "shadow":
                    logger.info("[S2-CVD] INITIATIVE SHORT rejected: net_delta=+%.0f (buying against breakdown)", _cvd_i["net_delta"])
                    return (None, 0, {})
            # cc-1: structural anchor = max high of b1..b3 for SHORT
            _ini_anchor_s = max(b1["h"], b2["h"], b3["h"])
            return ("SHORT", 0.80, {"kind": "INITIATIVE", "stage": 4,
                                    "b2_alt": "poc_return" if b2_poc_return_s else "lower_high",
                                    "structural_anchor": _ini_anchor_s})

        # S2_DETECTION_LOG: per-bar initiative condition vector
        import os as _dl_os2
        if _dl_os2.environ.get("S2_DETECTION_LOG", "").lower() in ("1", "true", "yes"):
            _bar_ts2 = bars_5m[-1].get("ts", "?") if bars_5m else "?"
            logger.info(
                "[S2-DL] INITIATIVE ts=%s b1_exp=%d b2_test=%d b3_join=%d b4_test=%d "
                "b1_bull=%d b1_bear=%d b1_range=%.1f exp=[%.1f,%.1f]",
                _bar_ts2,
                int(b1_expansion), int(b2_test or b2_test_s), int(b3_joining),
                int(b4_test or b4_test_s),
                int(b1_bull), int(b1_bear), b1_range, _exp_min, _exp_max,
            )

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
        import os as _os

        # ── S2_REACTIVE_EDGE_FIX_V1 (Michael live ruling 2026-07-17 ~20:00) ──
        # Two doctrine bugs this legacy fallback carried, both silently REJECTing
        # a valid edge-fade (never reaching route_setup → invisible in decisions):
        #   1. LOCATION INVERTED: it demanded location=="at"/"near" the POC — but
        #      `location_vs_poc_vol` measures distance FROM the POC, so a REACTIVE
        #      fade at VAH/VAL (the edge, where fades belong) is "far" → rejected.
        #      A responsive fade is CORRECT at the value-area EDGE, not at centre.
        #   2. COT/AMT HARD-REJECT contradicts the S2⟂S3 standing decision
        #      (CLAUDE.md: COT/AMT NOT required; S3 muted). With the CVD export
        #      empty today cot=amt=0 → every reactive auto-rejected.
        # Fix (flag ON by default per ruling): flow is a size booster, not a gate
        # unless S2_REQUIRE_COT_AMT=1; edge location is welcome for a fade.
        _edge_fix = _os.getenv("S2_REACTIVE_EDGE_FIX_V1", "1").lower() in ("1", "true", "yes")
        _require_flow = _os.getenv("S2_REQUIRE_COT_AMT", "0").lower() in ("1", "true", "yes")

        # COT/AMT alignment (direction-dependent) — used for the FULL-size booster
        if direction == "LONG":
            cot_amt_ok = cot > amt
            cot_amt_strong = amt > 0 and cot > amt * 1.2  # 🟡 1.2x threshold
        elif direction == "SHORT":
            cot_amt_ok = cot < amt
            cot_amt_strong = amt > 0 and cot < amt * 0.8  # 🟡 0.8x threshold
        else:
            return "reject"

        if not _edge_fix:
            # legacy path (byte-identical) when the fix flag is off
            if not cot_amt_ok:
                return "reject"
            location = pattern_state.get("location_vs_poc_vol", "far")
            if bars_formed == 4 and cot_amt_strong and location == "at":
                return "full"
            if bars_formed >= 3 and cot_amt_ok and location in ("at", "near"):
                return "half"
            return "reject"

        # ── fixed path ──
        if _require_flow and not cot_amt_ok:
            return "reject"  # only gate on flow when explicitly re-required
        location = pattern_state.get("location_vs_poc_vol", "far")  # at / near / far
        # FULL = a mature fade with confirming flow (location no longer gates —
        # an edge fade ("far") is the textbook responsive entry).
        if bars_formed == 4 and cot_amt_strong:
            return "full"
        # SOLID = 3+ bar reactive; ships at half regardless of POC distance.
        if bars_formed >= 3:
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

        # Live session transition: advance out of OVERNIGHT_MODE / WEEKEND when
        # RTH opens. hydrate() sets mode at startup — if backend started pre-RTH
        # (or on a weekend) this check promotes mode automatically on the first
        # RTH bar without a restart.
        # D1 fix (2026-08-11): WEEKEND label was stuck because there was no
        # transition code for it — bars were buffered silently forever.
        if self.mode in (FiveMinMode.OVERNIGHT_MODE, FiveMinMode.WEEKEND):
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

        # Normalize bar keys BEFORE buffering (avoids KeyError: 'c' when
        # OVERNIGHT bars lack short-form keys and later RTH detection reads them)
        bar.setdefault("o", bar.get("open", 0))
        bar.setdefault("h", bar.get("high", 0))
        bar.setdefault("l", bar.get("low", 0))
        bar.setdefault("c", bar.get("close", 0))
        bar.setdefault("v", bar.get("vol", bar.get("volume", 0)))

        # Spec: S2 must not fire outside trading sessions
        if self.mode in (FiveMinMode.OVERNIGHT_MODE, FiveMinMode.MAINTENANCE, FiveMinMode.WEEKEND):
            self.buffer_size += 1
            self._bar_buffer.append(bar)
            if len(self._bar_buffer) > 20:
                self._bar_buffer = self._bar_buffer[-20:]
            return
        # (bar keys o/h/l/c/v already normalized above)

        # Dedup: bridge pushes same bar ~20x while building. Buffer always
        # updates (latest OHLC), but bar counting + FHB + pattern detection
        # only run on genuinely new bar timestamps.
        # F2 (2026-08-12): compare the CANONICAL UTC instant, not the raw
        # string — "…T16:20:00+00:00" and "…16:20:00+00:00" are the same bar.
        _bar_ts = _canon_bar_ts(bar.get("ts", ""))
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

        # ── Opening-entry triggers (Michael 07-22 "ירי לפי סוג-פתיחה" — REVISED
        # per the 31-session historical validation, SHADOW phase). Evaluates
        # bars 2-6 of the session; emits shadow_only setups (gateway records,
        # never routes live while OPENING_ENTRY_V1=shadow). Honest guards:
        # collection starts ONLY on the true 16:30-IL open bar (restart
        # mid-window → skip the day, no fake OR). Non-fatal on any error.
        if self.mode == FiveMinMode.FIRST_HOUR_TACTICAL:
            _oe_mode = os.getenv("OPENING_ENTRY_V1", "0").lower()
            if _oe_mode in ("shadow", "1", "true"):
                try:
                    from backend.v9.systems.opening_entry import (
                        build_opening_setup, evaluate_opening_entry)
                    # OPEN-FIRE v1 (Michael 07-23 "live" ruling): extend the
                    # window to 60 min and activate PULLBACK-CONT. OFF ⇒ 30-min
                    # window, no pullback → byte-identical to the SHADOW spec.
                    _of_on = os.getenv("OPENING_FIRE_V1", "0").lower() in ("1", "true", "yes")
                    _oe_win = 12 if _of_on else 6
                    # OPENING_DIR_FUSION_V1: volume-confirmed opening-direction GATE over
                    # the opening entries (empirical study 07-24: 73% vs 53%). OFF ⇒ never
                    # computed, never gates → byte-identical.
                    _fusion_on = os.getenv("OPENING_DIR_FUSION_V1", "0").lower() in ("1", "true", "yes")
                    _ts_raw = bar.get("ts")
                    _bar_dt = None
                    # ROOT FIX 2026-07-29 (Michael: the big opening trades were
                    # never signalled). The open-bar anchor below compares
                    # hour:minute — but the ts was parsed into WHICHEVER tz its
                    # format implied: epoch → Israel, ISO-naive → left as-is
                    # (UTC). Mixed formats = mixed anchors: boot-replays fired
                    # phantom OPENING_DRIVEs at 07:38 IL (blocked by
                    # session_gate_closed) while the REAL 16:30 open bar parsed
                    # as 13:30 and was never recognised — the opening engine
                    # waited forever and the day's drive-short + reject-long
                    # were never even signalled. Normalise EVERY format to the
                    # exchange clock via UTC, then convert to IL for the
                    # anchor. (Rule 4: the 16:30-IL anchor itself is a known
                    # DST hazard — ET-anchoring is CC's follow-up; today IL
                    # 16:30 == ET 09:30 so this fix is behaviour-correct now.)
                    try:
                        from zoneinfo import ZoneInfo as _ZI
                        _IL = _ZI("Asia/Jerusalem")
                        # P0 (2026-07-29): OPENING_ANCHOR_ET_V1 — anchor on
                        # 09:30 ET instead of 16:30 IL. IL 16:30 == ET 09:30
                        # only outside DST transitions (5 weeks/year differ).
                        # Flag OFF → legacy IL anchor (byte-identical to cowork's fix).
                        _use_et = os.getenv("OPENING_ANCHOR_ET_V1", "0").lower() in (
                            "1", "true", "yes")
                        _anchor_tz = _ZI("America/New_York") if _use_et else _IL
                        _anchor_hour = 9 if _use_et else 16
                        _anchor_min = 30
                        if isinstance(_ts_raw, (int, float)):
                            _bar_dt_utc = datetime.fromtimestamp(
                                _ts_raw / 1000 if _ts_raw > 1e12 else _ts_raw,
                                tz=timezone.utc)
                        elif _ts_raw:
                            _p = datetime.fromisoformat(str(_ts_raw).replace("Z", "+00:00"))
                            if _p.tzinfo is None:
                                _p = _p.replace(tzinfo=timezone.utc)
                            _bar_dt_utc = _p
                        else:
                            _bar_dt_utc = None
                        _bar_dt = _bar_dt_utc.astimezone(_anchor_tz) if _bar_dt_utc else None
                        # Also keep IL view for the day-key (date boundary)
                        _bar_dt_il = _bar_dt_utc.astimezone(_IL) if _bar_dt_utc else None
                    except Exception:
                        _bar_dt = None
                        _bar_dt_utc = None
                        _bar_dt_il = None
                    _d_key = (_bar_dt_il or _bar_dt).date().isoformat() if (_bar_dt_il or _bar_dt) else str(_ts_raw)[:10]
                    if getattr(self, "_oe_date", None) != _d_key:
                        self._oe_date = _d_key
                        self._oe_bars = []
                        self._oe_fired = set()
                        self._oe_disabled = False
                        self._oe_seed_bias = None
                        self._oe_fusion = None
                        self._oe_fusion_done = False
                    if not getattr(self, "_oe_disabled", False):
                        # P0 anti-phantom (2026-07-29): opening signals only
                        # when the bar is < 10 min old. Replay/hydration bars
                        # are historical and must NOT produce opening signals.
                        _anti_phantom_ok = True
                        if _bar_dt_utc is not None:
                            _bar_age_s = (datetime.now(timezone.utc) - _bar_dt_utc).total_seconds()
                            if _bar_age_s > 600:  # > 10 minutes old
                                _anti_phantom_ok = False
                        if not self._oe_bars:
                            # FIX 16:44 (live): _anti_phantom_ok belonged to
                            # EMISSION, not collection. With it here, a restart
                            # mid-window could never rebuild the opening bars
                            # from hydration (the 16:30 bar is >10min old by
                            # then) → the next live bar found the window empty
                            # → "honest skip today" → opening engine dead for
                            # the day. Collection accepts the true open bar at
                            # any age; the emission guard below still blocks
                            # signals from stale bars.
                            _is_open_bar = bool(
                                _bar_dt
                                and _bar_dt.hour == _anchor_hour
                                and _bar_dt.minute == _anchor_min)
                            if _is_open_bar:
                                self._oe_bars.append(bar)
                            elif _bar_dt and (_bar_dt.hour, _bar_dt.minute) > (_anchor_hour, _anchor_min):
                                if _anti_phantom_ok:
                                    self._oe_disabled = True
                                    logger.info(
                                        "[FiveMin] OPENING_ENTRY: first seen bar %s is past %02d:%02d — honest skip today",
                                        _ts_raw, _anchor_hour, _anchor_min)
                                # else: replay bar past the open → silently skip (not a real miss)
                            # else: pre-open bar → wait for the 16:30 bar
                        elif len(self._oe_bars) < _oe_win:
                            self._oe_bars.append(bar)
                        # Cache the opening-type seed bias (only non-None in the
                        # first 15 min) so PULLBACK-CONT — which fires later in
                        # the 60-min window — can use it as a safety filter.
                        if _of_on:
                            try:
                                from backend.v9.services.trade_context import get_opening_type_seed
                                _seed = get_opening_type_seed()
                                if _seed in ("UP", "DOWN"):
                                    self._oe_seed_bias = "LONG" if _seed == "UP" else "SHORT"
                            except Exception:
                                pass
                        # OPENING_DIR_FUSION_V1: compute the volume-confirmed direction once
                        # the first 30 min are in (bar 6); cache UP/DOWN/None for the gate.
                        if _fusion_on and not getattr(self, "_oe_fusion_done", False) and len(self._oe_bars) >= 6:
                            try:
                                from backend.v9.services.trade_context import get_opening_dir_fusion
                                self._oe_fusion = get_opening_dir_fusion(self._oe_bars)
                                logger.info("[FiveMin] OPENING_DIR_FUSION = %s", self._oe_fusion)
                            except Exception as _fx:
                                self._oe_fusion = None
                                logger.warning("[FiveMin] opening-dir-fusion failed (non-fatal): %s", _fx)
                            # T7b (2026-08-16) — do NOT latch a transient None.
                            # The fusion now reads its volume from the CANONICAL
                            # closed bars, so at the moment the 6th live bar
                            # arrives the 6th row may not be closed in the table
                            # yet, and the honest answer is None = "not ready".
                            # `_oe_fusion_done = True` used to be set BEFORE the
                            # call, so that transient None became the answer for
                            # the whole day and the gate dropped every opening
                            # candidate. Latch only on a definitive UP/DOWN, or
                            # once the window has moved on (8 bars = 40 min, well
                            # past the 30-min measurement) so a genuinely quiet
                            # open still settles to None and stops re-querying.
                            if self._oe_fusion is not None or len(self._oe_bars) >= 8:
                                self._oe_fusion_done = True
                            else:
                                logger.info(
                                    "[FiveMin] OPENING_DIR_FUSION not ready yet "
                                    "(closed bars still catching up) — will retry next bar")
                        if 2 <= len(self._oe_bars) <= _oe_win and _anti_phantom_ok:
                            _trig = evaluate_opening_entry(
                                self._oe_bars, self._oe_fired,
                                window_last_bar=_oe_win, enable_pullback=_of_on,
                                bias=getattr(self, "_oe_seed_bias", None))
                            # direction gate: drop low-conviction (fusion None) or a trigger
                            # that fights the fusion direction. Only once fusion is computed.
                            if _trig and _fusion_on and getattr(self, "_oe_fusion_done", False):
                                _fb = getattr(self, "_oe_fusion", None)
                                if _fb is None or (_trig.get("direction") and _fb != _trig["direction"]):
                                    logger.info("[FiveMin] OPENING_DIR_FUSION gate dropped %s %s (fusion=%s)",
                                                _trig.get("type"), _trig.get("direction"), _fb)
                                    _trig = None
                            # OPENING_FIRST_TRADE_STRICT_V1 (Michael 2026-07-31
                            # 18:20): the first trade fires only with opening-type
                            # CERTAINTY (conf >= 0.7) + a confirmation bar. #575
                            # fired on bar-1's close at conf 0.00 and lost $199.
                            if _trig and os.getenv("OPENING_FIRST_TRADE_STRICT_V1",
                                                   "0").lower() in ("1", "true", "yes"):
                                try:
                                    from backend.v9.systems.opening_entry import (
                                        opening_first_trade_ok as _ft_ok_fn)
                                    _ft_conf = None
                                    try:
                                        from backend.v9.services.market_context import (
                                            get_market_context as _ft_mc)
                                        _mc = _ft_mc()
                                        _ft_conf = getattr(_mc, "opening_conf", None) if _mc else None
                                    except Exception:
                                        _ft_conf = None
                                    _ft_ok, _ft_why = _ft_ok_fn(
                                        self._oe_bars, _trig["direction"], _ft_conf,
                                        trigger_type=_trig.get("type"),
                                        opening_type=getattr(_mc, "opening_type",
                                                             None) if _mc else None)
                                    if not _ft_ok:
                                        logger.warning(
                                            "[FiveMin] OPENING_FIRST_TRADE_STRICT held %s %s — %s",
                                            _trig.get("type"), _trig.get("direction"), _ft_why)
                                        _trig = None
                                except Exception as _ft_err:
                                    # fail-CLOSED: strictness gate broken => no first trade
                                    logger.warning(
                                        "[FiveMin] first-trade-strict errored — holding: %s", _ft_err)
                                    _trig = None
                            if _trig:
                                self._oe_fired.add(_trig["type"])
                                _setup = build_opening_setup(
                                    _trig, self._oe_bars,
                                    shadow_only=(_oe_mode == "shadow"))
                                if _setup and self._gateway:
                                    logger.info(
                                        "[FiveMin] OPENING_ENTRY %s %s entry=%.2f stop=%.2f t1=%.2f (%s)",
                                        _trig["type"], _trig["direction"],
                                        _setup["entry_price"], _setup["stop"], _setup["t1"],
                                        "SHADOW" if _oe_mode == "shadow" else "live-eligible")
                                    self._gateway.route_setup(_setup, 2)
                except Exception as _oe_err:
                    logger.warning("[FiveMin] opening-entry failed (non-fatal): %s", _oe_err)

                # ── EDGE_FADE_V1 (DEV_PLAN 02.08 §P1 — the $1,550 detection gap):
                # responsive edge-fade on balance days. Location+direction here;
                # TIMING stays with awaiting_release (deliberately not exempt) —
                # the 07-27 winner was edge-location + release-timing combined.
                try:
                    if (os.getenv("EDGE_FADE_V1", "0").lower() in ("1", "true", "yes")
                            and self._gateway):
                        from backend.v9.systems.edge_fade import (
                            evaluate_edge_fade, build_edge_fade_setup, FADE_DAY_TYPES)
                        from backend.v9.db.read import read_one as _ef_read1, read_all as _ef_readN
                        _ef_dt_row = _ef_read1(
                            "SELECT day_type, confidence FROM v9_day_type_state "
                            "ORDER BY id DESC LIMIT 1", {})
                        _ef_dt = _ef_dt_row["day_type"] if _ef_dt_row else None
                        try:
                            _ef_conf = float(_ef_dt_row["confidence"]) if _ef_dt_row and \
                                _ef_dt_row["confidence"] is not None else 0.0
                        except (TypeError, ValueError):
                            _ef_conf = 0.0
                        if _ef_dt in FADE_DAY_TYPES and _ef_conf >= 0.4:
                            _ef_rows = _ef_readN(
                                "SELECT extract(epoch from ts) ets, open o, high h, "
                                "low l, close c FROM v9_bars_5min_woodies "
                                "WHERE (ts AT TIME ZONE 'America/New_York')::date = "
                                "(now() AT TIME ZONE 'America/New_York')::date "
                                "AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' "
                                "ORDER BY ts", {})
                            _ef_rows = list(_ef_rows or [])
                            # anti-phantom: newest closed bar must be fresh (<10 min)
                            import time as _ef_time
                            _ef_fresh = bool(_ef_rows) and (
                                _ef_time.time() - float(_ef_rows[-1]["ets"])) < 600
                            if _ef_fresh:
                                # ARM → RELEASE two-stage (see edge_fade.py header)
                                from backend.v9.systems.edge_fade import (
                                    build_release_entry_setup, ARM_WINDOW_BARS)
                                from backend.v9.systems.release_gate import (
                                    Bar as _ef_Bar, check_release as _ef_release)
                                if not hasattr(self, "_ef_fired"):
                                    self._ef_fired = set()
                                if not hasattr(self, "_ef_armed"):
                                    self._ef_armed = {}
                                _ef_n_bars = len(_ef_rows)
                                # stage 1 — arm on an edge rejection
                                _ef_trig = evaluate_edge_fade(
                                    _ef_rows, _ef_dt, self._ef_fired)
                                if _ef_trig and _ef_trig["type"] not in self._ef_armed:
                                    self._ef_armed[_ef_trig["type"]] = (_ef_n_bars, _ef_trig)
                                    logger.info(
                                        "[FiveMin] EDGE_FADE ARMED %s %s (edge %.2f, "
                                        "awaiting release)", _ef_trig["type"],
                                        _ef_trig["direction"], _ef_trig["edge"])
                                # stage 2 — enter on the release confirmation
                                for _ef_side, (_ef_ai, _ef_tg) in list(self._ef_armed.items()):
                                    if _ef_side in self._ef_fired:
                                        continue
                                    if _ef_n_bars - _ef_ai > ARM_WINDOW_BARS:
                                        del self._ef_armed[_ef_side]
                                        continue
                                    _ef_rbars = [
                                        _ef_Bar(float(b["h"]), float(b["l"]),
                                                float(b["c"]), 0.0)
                                        for b in _ef_rows]
                                    # volume needed for the release check — refetch light
                                    try:
                                        _ef_v = _ef_readN(
                                            "SELECT volume FROM v9_bars_5min_woodies "
                                            "WHERE (ts AT TIME ZONE 'America/New_York')::date = "
                                            "(now() AT TIME ZONE 'America/New_York')::date "
                                            "AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' "
                                            "ORDER BY ts", {})
                                        for _bi, _vr in enumerate(_ef_v or []):
                                            if _bi < len(_ef_rbars):
                                                _ef_rbars[_bi].volume = float(_vr["volume"] or 0)
                                    except Exception:
                                        pass
                                    _ef_verdict = _ef_release(_ef_rbars, _ef_tg["direction"])
                                    if not _ef_verdict.released:
                                        continue
                                    self._ef_fired.add(_ef_side)
                                    del self._ef_armed[_ef_side]
                                    # ONE resolver (2026-08-19): was a 3/4/1 ladder
                                    # that shipped 4 while the ruling was 6.
                                    from backend.v9.services.contract_size import ruled_contracts as _rc19
                                    _ef_n = _rc19() or 1
                                    _ef_setup = build_release_entry_setup(
                                        _ef_tg["direction"],
                                        float(_ef_rows[-1]["c"]),
                                        _ef_verdict.structural_stop,
                                        float(_ef_tg["target_mid"]),
                                        float(_ef_tg["stop"]),
                                        contracts=_ef_n)
                                    logger.info(
                                        "[FiveMin] EDGE_FADE RELEASE-ENTRY %s %s "
                                        "entry=%.2f stop=%.2f t1=%.2f t2=%.2f (%s)",
                                        _ef_side, _ef_tg["direction"],
                                        _ef_setup["entry_price"], _ef_setup["stop"],
                                        _ef_setup["t1"], _ef_setup["t2"],
                                        _ef_verdict.reason[:60])
                                    self._gateway.route_setup(_ef_setup, 2)
                except Exception as _ef_err:
                    logger.warning("[FiveMin] edge-fade failed (non-fatal): %s", _ef_err)

                # ── VA_FADE_V1 (Phase 2): value-area rotation generator ──
                # Dalton doctrine: on balance days, buy VAL rejection, sell VAH
                # rejection, target the middle. 25.08 anchor: 4 rotations, zero
                # doctrine-fires. This is the GENERATOR, not a filter.
                try:
                    if (os.getenv("VA_FADE_V1", "0").lower() in ("1", "true", "yes", "shadow")
                            and self._gateway):
                        from backend.v9.systems.va_fade import (
                            detect_va_fade, build_va_fade_setup)
                        # Get VAH/VAL from TPO
                        _vf_vah = _vf_val = None
                        try:
                            _vf_tpo = _load_sierra_tpo() or {}
                            _vf_vah = float(_vf_tpo.get("vah") or 0) or None
                            _vf_val = float(_vf_tpo.get("val") or 0) or None
                        except Exception:
                            pass
                        if _vf_vah and _vf_val:
                            if not hasattr(self, "_vf_fired"):
                                self._vf_fired = set()
                            _vf_trig = detect_va_fade(
                                _det_buf, _s2_det_dt,
                                _vf_vah, _vf_val,
                                already_fired=self._vf_fired)
                            if _vf_trig:
                                self._vf_fired.add(_vf_trig["type"])
                                _vf_setup = build_va_fade_setup(_vf_trig)
                                logger.warning(
                                    "[VA_FADE] %s %s @%.2f (VAH=%.2f VAL=%.2f) → gateway",
                                    _vf_trig["direction"], _vf_trig["type"],
                                    _vf_trig["entry"], _vf_vah, _vf_val)
                                self._gateway.route_setup(_vf_setup, 2)
                except Exception as _vf_err:
                    logger.warning("[VA_FADE] failed (non-fatal): %s", _vf_err)

                # ── FAILED_BREAK_VA_V1: entry after failed attempt to break VA edge ──
                # Michael 26.08: "לזהות מתי המחיר לא מצליח לעבור קיצון ואז חוזר חזרה"
                # §D: +$118/33 sessions, 56% win. Three-step: attempt→failure→return.
                try:
                    if (os.getenv("FAILED_BREAK_VA_V1", "0").lower() in ("1", "true", "yes", "shadow")
                            and self._gateway):
                        from backend.v9.systems.failed_break import (
                            detect_failed_break, build_failed_break_setup)
                        _fb_vah = _fb_val = None
                        try:
                            _fb_tpo = _load_sierra_tpo() or {}
                            _fb_vah = float(_fb_tpo.get("vah") or 0) or None
                            _fb_val = float(_fb_tpo.get("val") or 0) or None
                        except Exception:
                            pass
                        if _fb_vah and _fb_val:
                            if not hasattr(self, "_fb_fired"):
                                self._fb_fired = set()
                            _fb_trig = detect_failed_break(
                                _det_buf, _fb_vah, _fb_val,
                                edge_label="VA", already_fired=self._fb_fired)
                            if _fb_trig:
                                self._fb_fired.add(_fb_trig["type"])
                                _fb_setup = build_failed_break_setup(_fb_trig)
                                logger.warning(
                                    "[FailedBreak] %s %s @%.2f (VAH=%.2f VAL=%.2f extreme=%.2f) → gateway",
                                    _fb_trig["direction"], _fb_trig["type"],
                                    _fb_trig["entry"], _fb_vah, _fb_val,
                                    _fb_trig.get("failed_extreme", 0))
                                self._gateway.route_setup(_fb_setup, 2)
                except Exception as _fb_err:
                    logger.warning("[FailedBreak] failed (non-fatal): %s", _fb_err)

        # Compute choppiness continuously (all modes, not just FIRST_HOUR)
        # so s2_inspector.choppiness_ok stays fresh in DAY_TYPE_MODE.
        # Uses last 14 bars (rolling window) for stable measurement.
        _chop_bars = self._bar_buffer[-14:] if len(self._bar_buffer) >= 5 else self._bar_buffer
        if _chop_bars:
            self.choppiness_score = int(compute_choppiness(_chop_bars))

        # G2/G3 — S2_DETECTION_LIVE_DAYTYPE_V1: resolve day_type from live source
        # when flag ON, instead of the stale hydrated self.current_day_type.
        # Fixes I-44/I-50 split: detection saw stale Normal while live was Trend.
        _s2_det_dt = self.current_day_type
        if os.getenv("S2_DETECTION_LIVE_DAYTYPE_V1", "0").lower() in ("1", "true", "yes"):
            try:
                from backend.v9.services.trade_context import get_live_day_type
                _live = get_live_day_type()
                if _live and _live not in ("UNKNOWN", "None", ""):
                    _s2_det_dt = _live
            except Exception:
                pass  # fail-safe: keep hydrated value

        # D-091.Q2 · NT NO_TRADE early-skip (CPU efficiency + emit-layer defense)
        if _s2_det_dt == "Nontrend":
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

        # A4 (map §S2-5/S2-7): HLST removed from the detection chain.
        # It ran BEFORE DOUBLE_BOTTOM (first-match-wins) and would suppress it.
        # Replay: HLST −$4,574.  The detector module is preserved for future
        # research but no longer competes for the slot.

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
            if chart_patterns_allowed(_s2_det_dt, "5a"):
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
            if chart_patterns_allowed(_s2_det_dt, "5c"):
                direction, conf, info = detect_bull_flag(_det_buf)
                if not direction:
                    direction, conf, info = detect_bear_flag(_det_buf)

        # Pkg 5d · RE_PULLBACK_ENTRY_V1 (C2, default OFF): pullback retest of
        # broken IB edge — the missing Dalton entry. Fires after IB lock when
        # price breaks the IB, extends, pulls back to the edge, and a rejection
        # bar closes WITH the break direction. Needs IB context from Sierra TPO.
        if not direction and os.getenv("RE_PULLBACK_ENTRY_V1", "0").lower() in ("1", "true", "yes"):
            try:
                from backend.v9.systems.five_min.patterns.pullback_retest import detect_pullback_retest
                _pb_tpo = _load_sierra_tpo() or {}
                _pb_ibh = _pb_tpo.get("ib_high")
                _pb_ibl = _pb_tpo.get("ib_low")
                _pb_ib_locked = bool(_pb_tpo.get("ib_locked", False))
                # session_min from the current bar's position
                _pb_session_min = 0
                if _det_buf:
                    _pb_ts = _det_buf[-1].get("ts")
                    if _pb_ts:
                        try:
                            from datetime import datetime as _pb_dt
                            from zoneinfo import ZoneInfo as _pb_ZI
                            _pb_et = _pb_dt.fromtimestamp(float(_pb_ts), _pb_ZI("America/New_York"))
                            _pb_session_min = max(0, (_pb_et.hour - 9) * 60 + _pb_et.minute - 30)
                        except Exception:
                            _pb_session_min = 90  # assume post-IB if time unavailable
                direction, conf, info = detect_pullback_retest(
                    _det_buf,
                    ib_high=float(_pb_ibh) if _pb_ibh else None,
                    ib_low=float(_pb_ibl) if _pb_ibl else None,
                    ib_locked=_pb_ib_locked,
                    session_min=_pb_session_min,
                )
            except Exception as _pb_err:
                logger.warning("[FiveMin] RE_PULLBACK errored (fail-open): %s", _pb_err)

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
                    _s2_ledger(
                        "DETECTED",
                        pattern=f"{_kind}_{direction}",
                        direction=direction,
                        signal_bar_ts=bar.get("ts"),
                        variant_tag=info.get("variant", ""),
                    )
                    _s2_ledger(
                        "EMIT_DECISION",
                        pattern=f"{_kind}_{direction}",
                        direction=direction,
                        signal_bar_ts=bar.get("ts"),
                        variant_tag=info.get("variant", ""),
                        verdict="REJECT",
                        blocked_by="dedup",
                    )
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
                _s2_ledger(
                    "DETECTED",
                    pattern=fhb_key,
                    direction=direction,
                    signal_bar_ts=bar.get("ts"),
                    variant_tag=info.get("variant", ""),
                )
                _s2_ledger(
                    "EMIT_DECISION",
                    pattern=fhb_key,
                    direction=direction,
                    signal_bar_ts=bar.get("ts"),
                    variant_tag=info.get("variant", ""),
                    verdict="REJECT",
                    blocked_by="fhb",
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
            elif kind == "RE_PULLBACK":
                family = "CONT"
                # Stop and targets come from the detection info
                structural_anchor = (
                    info.get("retest_low", entry_price) if direction == "LONG"
                    else info.get("retest_high", entry_price)
                )
            else:
                family = "Reactive" if kind == "REACTIVE" else "OFA"
                # cc-1 (STRUCTURAL_STOP_ORIGIN_V1): use the pattern's structural
                # anchor (swing extreme of b1..b3) instead of the current bar's
                # high/low. #420: entry bar high was 7514, but the structural
                # resistance was 7521-7527 → stop placed inside structure.
                # When flag OFF: byte-identical (current bar extreme).
                if (os.getenv("STRUCTURAL_STOP_ORIGIN_V1", "0").lower() in ("1", "true", "yes")
                        and info.get("structural_anchor") is not None):
                    structural_anchor = info["structural_anchor"]
                else:
                    structural_anchor = (
                        bar.get("l", entry_price) if direction == "LONG"
                        else bar.get("h", entry_price)
                    )

            _s2_cap_pts = None  # group ATR-cap (points) — set when V2 stop runs (SIZE_CAP_CUT_V1)
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
                        # Cluster/breakout: window extreme + 3T offset.
                        # FIX-2 (STOP_WINDOW_COMPLETED_V1, default OFF): the stop
                        # anchor window must read the COMPLETED-bar buffer, not the
                        # live buffer whose last element is the just-opened PARTIAL
                        # bar (range ~= 0). For window:1 families (Flag / OFA_Initiative
                        # / ZLR) the live buffer collapses the structural distance to
                        # ~the 3T offset -> the ATR floor always binds -> too-tight
                        # stops / premature wick-outs. `_det_buf` (defined above as
                        # self._bar_buffer[:-1] when >= 8 bars) already excludes the
                        # partial bar, matching the detection + entry window.
                        # OFF -> byte-identical to today (live buffer).
                        # Ruling D (Michael 07-21 22:22, built 07-22): the stop
                        # anchors behind the STRUCTURE extreme, not a single
                        # bar — window:1 families (ZLR/Flag/OFA) collapse to the
                        # last bar without this. Widen the anchor window to
                        # structure_window_bars (completed bars). OFF → as-is.
                        _w_eff = a["window"]
                        if _flag("STOP_STRUCTURE_EXTREME_V1"):
                            _w_eff = max(_w_eff, int(cfg["principles"].get("structure_window_bars", 12)))
                        if _flag("STOP_WINDOW_COMPLETED_V1"):
                            window_bars = _det_buf[-_w_eff:]
                        else:
                            window_bars = self._bar_buffer[-_w_eff:]
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
                    _s2_cap_pts = v2_comp.atr_cap_ticks * 0.25  # → SIZE_CAP_CUT_V1
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

            # ── TREND_STOP_FLOOR_V1 (2026-08-04): on Trend days (or Variation
            # with a live leg), with-trend trades get a stop floor = max(6,
            # 0.15 × IB_width). The 08-03 case: 4/4 losses were with-trend
            # trades stopped on noise (2.5-4pt stops); all 4 would have reached
            # T1 with the floor. Before T1 only (after T1 → BE). Opening trades
            # exempt (they have their own caps). Flag OFF → byte-identical.
            if _flag("TREND_STOP_FLOOR_V1") and stop_price is not None:
                try:
                    _tsf_day_type = _emit_day_type or self.current_day_type or ""
                    _tsf_is_trend = _tsf_day_type.startswith("Trend") or (
                        _tsf_day_type == "Normal_Variation"
                        and hasattr(self, "_live_leg")
                        and callable(getattr(self, "_live_leg", None))
                    )
                    # Check with-trend: setup direction matches day direction
                    _tsf_with_trend = False
                    if _tsf_is_trend:
                        try:
                            from backend.v9.services.market_context import get_market_context
                            _tsf_mc = get_market_context()
                            _tsf_bias = getattr(_tsf_mc, "day_bias", "NONE") if _tsf_mc else "NONE"
                            _tsf_leg = getattr(_tsf_mc, "leg_dir", None) if _tsf_mc else None
                            _tsf_with_trend = (
                                (direction == "LONG" and (_tsf_bias == "UP" or _tsf_leg == "UP"))
                                or (direction == "SHORT" and (_tsf_bias == "DOWN" or _tsf_leg == "DOWN"))
                            )
                        except Exception:
                            pass
                    # Not opening trade (they have their own caps)
                    _tsf_is_opening = kind in (
                        "OPENING_DRIVE", "OPENING_TEST_DRIVE", "OPENING_ORR",
                        "OPENING_EXTREME_REJECT", "OPENING_PULLBACK_CONT",
                        "EDGE_FADE_LONG", "EDGE_FADE_SHORT",
                    )
                    if _tsf_with_trend and not _tsf_is_opening:
                        # Compute floor: max(6.0, 0.15 × IB_width)
                        _tsf_ib_w = None
                        try:
                            from backend.v9.db.read import read_one as _tsf_rd
                            _tsf_ib = _tsf_rd(
                                "SELECT MAX(high) - MIN(low) as ib_w FROM ("
                                "  SELECT high, low FROM v9_bars_5min_woodies "
                                "  WHERE (ts AT TIME ZONE 'America/New_York')::date = "
                                "  (now() AT TIME ZONE 'America/New_York')::date "
                                "  ORDER BY ts LIMIT 12"
                                ") sub", {})
                            if _tsf_ib and _tsf_ib.get("ib_w"):
                                _tsf_ib_w = float(_tsf_ib["ib_w"])
                        except Exception:
                            pass
                        _tsf_floor = max(6.0, 0.15 * (_tsf_ib_w or 40.0))
                        _tsf_sign = 1.0 if direction == "LONG" else -1.0
                        _tsf_risk = abs(entry_price - stop_price)
                        if _tsf_risk < _tsf_floor:
                            _tsf_new_stop = entry_price - _tsf_sign * _tsf_floor
                            # Clamp to pattern max risk (SIZE_CAP, not expand)
                            _tsf_max = float(os.getenv("TREND_STOP_FLOOR_MAX_PTS", "15"))
                            if abs(entry_price - _tsf_new_stop) <= _tsf_max:
                                logger.info(
                                    "[FiveMin] TREND_STOP_FLOOR: %s %s stop %.2f→%.2f "
                                    "(floor=%.1f, IB=%.1f, was=%.1f)",
                                    kind, direction, stop_price, _tsf_new_stop,
                                    _tsf_floor, _tsf_ib_w or 0, _tsf_risk)
                                stop_price = _tsf_new_stop
                            else:
                                logger.info(
                                    "[FiveMin] TREND_STOP_FLOOR: floor %.1f exceeds max %.1f — not applied",
                                    _tsf_floor, _tsf_max)
                except Exception as _tsf_err:
                    logger.debug("[FiveMin] trend stop floor error (fail-safe): %s", _tsf_err)

            # Sizing decision (Cockpit V5 — S2 internal only)
            cot_val = info.get("cot") or self._get_cot_from_footprint() or 0
            amt_val = info.get("amt") or self._get_amt_from_footprint() or 0
            location = self._compute_location_vs_poc(bar)
            # ── D-0717-A (Michael live finding 2026-07-17 18:06): the auth verdict
            # inside compute_v2_sizing (_auth_cell lookup) resolved pattern × day_type
            # with self.current_day_type — the OLD engine's event/hydration value —
            # while DAY_TYPE_MANUAL_OVERRIDE=2026-07-17:Variation was live, so S2
            # showed "INITIATIVE_LONG × Normal" (SKIP row) instead of "× Variation"
            # (FULL row). Consult the canonical override-aware source FIRST
            # (trade_context.get_live_day_type — the same source the emit path at
            # `_emit_day_type` already uses), falling back to the event value when
            # it returns None. Fail-open: any error → prior behavior; never raises
            # into the fire path.
            _live_day_type = None
            try:
                from backend.v9.services.trade_context import get_live_day_type as _gldt_s2
                _live_day_type = _gldt_s2()
            except Exception:
                _live_day_type = None
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
                        # SIZE_CAP_CUT_V1: pass the group ATR-cap (points) when the
                        # V2 stop computation ran (_s2_cap_pts set alongside v2_comp;
                        # None on the legacy path → no cut, honest missing).
                        _cap_pts = _s2_cap_pts
                        v2_sizing_result = compute_v2_sizing(
                            entry_price=entry_price,
                            stop_price=stop_price,
                            direction=direction,
                            pattern_key=_s2_family_key[family],
                            # D-0717-A: override-aware live day_type first (see above)
                            day_type=_live_day_type or self.current_day_type or "Normal",
                            confidence_tier="medium",
                            day_has_direction=_day_has_dir,
                            trade_with_trend=_with_trend,
                            value_area_full_traverse=None,
                            cfg=cfg,
                            auth_matrix=_auth,
                            reversal=_is_rev,
                            cap_risk_points=_cap_pts,
                        )
                        if v2_sizing_result is None:
                            logger.info("[FiveMin] V2 sizing: SKIP (auth verdict)")
                            sizing = "reject"
                        else:
                            _c = v2_sizing_result.contracts
                            # same enum squeeze as S4 — see woodies_system.
                            # _c == 1 used to ship 2 contracts.
                            sizing = "reject" if _c == 0 else (
                                "full" if _c >= 3 else "half")
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

            # FIX 1+5: day_type for targets + auth. Computed ONCE, used by both
            # targets and emit_t1_setup.
            # DAYTYPE_GATE_LIVE_V1: read the LIVE promoted 7-type first (same source
            # as V2Sizing / position gate). Falls back to self.current_day_type, then
            # the old DECISION_MATRIX provisional. Single helper shared with
            # extract_g1_entry_context (no duplicate logic).
            # D-0717-A: reuse the override-aware value resolved ONCE before sizing
            # (_live_day_type, same get_live_day_type() source) so sizing/auth,
            # targets and emit all see the SAME label within a single fire.
            _emit_day_type = _live_day_type or self.current_day_type
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
            _raw_ts_ledger = _completed_bar.get("ts", bar.get("ts", 0))
            _cid = _s2_ledger(
                "DETECTED",
                pattern=f"{kind}_{direction}",
                direction=direction,
                signal_bar_ts=_raw_ts_ledger,
                variant_tag=info.get("variant", ""),
                prices={"entry": entry_price, "stop": stop_price},
            )
            if _cid:
                info["candidate_id"] = _cid
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
                        _ft_key = "flag_relative_t1_v2" if _flag("T1_LADDER_V2") and _sa and "flag_relative_t1_v2" in _sa else "flag_relative_t1"
                        if _sa and _ft_key in _sa:
                            _ft = _sa[_ft_key]
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

                    dt = _s2_det_dt  # G3: resolved via S2_DETECTION_LIVE_DAYTYPE_V1
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

                # ── Ruling C (Michael 07-21 ~18:15, built 07-22 "תבצע אתה"):
                # T1_STRUCTURE_END_V1 — T1 = the END of the entry structure
                # (profit-side extreme of the completed-bar structure window),
                # REPLACING the R/ladder computation. Applies to Reactive/OFA
                # (chart patterns HNS/Double/Flag keep their pattern-measure —
                # that IS their per-pattern structure). Structure exhausted →
                # keep computed T1 + honest log. OFF → byte-identical.
                if (_flag("T1_STRUCTURE_END_V1")
                        and kind not in ("INVERSE_HNS", "HNS_TOP", "DOUBLE_BOTTOM_EE",
                                         "DOUBLE_TOP_AA", "BULL_FLAG", "BEAR_FLAG")):
                    try:
                        from backend.v9.config_loader import load_stop_anchors as _lsa_c
                        from backend.v9.systems.stop_anchors import resolver as _SA_c
                        _sa_c = _lsa_c() or {}
                        _pr_c = _sa_c.get("principles", {})
                        _w_c = int(_pr_c.get("structure_window_bars", 12))
                        _min_t = int(_pr_c.get("t1_min_ticks", 2))
                        _win_c = _det_buf[-_w_c:] if _det_buf and len(_det_buf) >= 2 else None
                        if _win_c:
                            _t1_struct = _SA_c.structure_end_t1(_win_c, direction)
                            # 07-22 18:55 breakout blind-spot fix (see woodies twin):
                            # structural T1 only when viable (≥ rr_min×risk);
                            # exhausted ahead → T1 = 1R per the targets table.
                            _t1_dist_c = abs(_t1_struct - entry_price)
                            _risk_c = abs(entry_price - stop_price) if stop_price else 0.0
                            _rr_min_s2 = float(os.getenv("RR_MIN_ROTATION", "0.65") or 0.65)
                            if (_SA_c.t1_structure_valid(entry_price, _t1_struct, direction, _min_t)
                                    and _risk_c > 0 and _t1_dist_c >= _rr_min_s2 * _risk_c):
                                logger.info(
                                    "[FiveMin] T1_STRUCTURE_END: %s %s t1 %.2f→%.2f (structure end over %d bars)",
                                    kind, direction, t1_price or 0.0, _t1_struct, len(_win_c))
                                t1_price = _t1_struct
                            elif _risk_c > 0:
                                _sign_c = 1.0 if direction == "LONG" else -1.0
                                _t1r_m = 1.0
                                try:
                                    _t1r_m = float(os.getenv("T1_BANK_R", "1.0") or 1.0)
                                except (TypeError, ValueError):
                                    _t1r_m = 1.0
                                t1_price = entry_price + _sign_c * _t1r_m * _risk_c  # T1_BANK_R x risk
                                info["t1_structure_exhausted"] = True
                                logger.info(
                                    "[FiveMin] T1_STRUCTURE_END: %s %s structure exhausted ahead (end %.2f) — T1=1R %.2f",
                                    kind, direction, _t1_struct, t1_price)
                    except Exception as _c_err:
                        logger.warning("[FiveMin] T1_STRUCTURE_END failed (computed T1 kept): %s", _c_err)

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
                    candidate_id=info.get("candidate_id"),
                    signal_bar_ts=_raw_ts_ledger,
                )
                if t1_setup and self._gateway:
                    # P2 (2026-07-29): global anti-phantom — block signals from
                    # replay/hydration bars. Two conditions:
                    #   1. Bar age < 10 min from real time
                    #   2. |entry − last_close| < 2% (catches garbage prices)
                    # Fail-open: unknown age → allow (live bars don't carry age info).
                    _phantom_block = False
                    try:
                        # Compute bar UTC time if not already available
                        _ap_bar_utc = locals().get("_bar_dt_utc")
                        if _ap_bar_utc is None and _ts_raw:
                            try:
                                if isinstance(_ts_raw, (int, float)):
                                    _ap_bar_utc = datetime.fromtimestamp(
                                        _ts_raw / 1000 if _ts_raw > 1e12 else _ts_raw,
                                        tz=timezone.utc)
                                else:
                                    _p2 = datetime.fromisoformat(
                                        str(_ts_raw).replace("Z", "+00:00"))
                                    if _p2.tzinfo is None:
                                        _p2 = _p2.replace(tzinfo=timezone.utc)
                                    _ap_bar_utc = _p2
                            except Exception:
                                pass
                        if _ap_bar_utc is not None:
                            _age_s = (datetime.now(timezone.utc) - _ap_bar_utc).total_seconds()
                            if _age_s > 600:  # > 10 min old
                                _phantom_block = True
                                logger.debug(
                                    "[FiveMin] ANTI-PHANTOM: blocked %s %s (bar age %.0fs > 600s)",
                                    pattern_name, direction, _age_s)
                        _ap_close = _det_buf[-1].get("c", _det_buf[-1].get("close")) if _det_buf else None
                        if not _phantom_block and entry_price and _ap_close:
                            _price_dev = abs(entry_price - float(_ap_close)) / float(_ap_close)
                            if _price_dev > 0.02:
                                _phantom_block = True
                                logger.warning(
                                    "[FiveMin] ANTI-PHANTOM: blocked %s %s (|entry %.2f − close %.2f| = %.1f%% > 2%%)",
                                    pattern_name, direction, entry_price, float(_ap_close), _price_dev * 100)
                    except Exception:
                        pass  # fail-open
                    if _phantom_block:
                        logger.info("[FiveMin] ANTI-PHANTOM: %s %s suppressed (replay/hydration bar)", pattern_name, direction)
                        _s2_ledger(
                            "EMIT_DECISION",
                            pattern=pattern_name,
                            direction=direction,
                            signal_bar_ts=_raw_ts_ledger,
                            variant_tag=info.get("variant", ""),
                            candidate_id=info.get("candidate_id"),
                            verdict="REJECT",
                            blocked_by="anti_phantom",
                        )
                    else:
                        gateway_setup = build_s2_gateway_setup(t1_setup, info)
                        if info.get("candidate_id"):
                            gateway_setup["candidate_id"] = info["candidate_id"]
                        # C2: absorption context field (P1a) — available to all
                        # detectors for quality assessment.  As ENTRY = −$2,871;
                        # as context-only field = $0 but enables future filters.
                        try:
                            _abs_cvd = self._compute_setup_cvd(_det_buf, window=4)
                            if _abs_cvd is not None:
                                _abs_pb = _abs_cvd.get("perbar_deltas", [])
                                _abs_net = _abs_cvd.get("net_delta", 0)
                                # Absorption = delta opposing the direction
                                # (sellers in an up-move, buyers in a down-move)
                                _is_long = direction == "LONG"
                                gateway_setup.setdefault("metadata", {})["absorption"] = {
                                    "net_delta": round(_abs_net, 1),
                                    "entry_bar_delta": round(_abs_pb[-1], 1) if _abs_pb else None,
                                    "opposing": (_abs_net < 0) if _is_long else (_abs_net > 0),
                                }
                        except Exception:
                            pass  # never block a setup on context
                        try:
                            self._gateway.route_setup(gateway_setup, 2)
                            logger.info("[FiveMin] Auto-routed: %s %s → gateway (SHADOW records; DEMO/LIVE if gates pass)", pattern_name, direction)
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
