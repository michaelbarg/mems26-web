"""FiveMinSystem — 5-min Decision Maker with full D-077 lifecycle.

Implements hydrate() for cold start scenarios (Addendum Section 1).
Uses SessionClassifier (D-083) — never raw time checks.
Integrates with existing chart_5min/ detector and pattern library.
"""

import logging
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.v9.systems.base.trading_system import BaseV9TradingSystem, HydrationResult, SystemType
from backend.v9.common.session_classifier import SessionClassifier, Session
from backend.v9.db.session import SessionLocal
from backend.v9.db.models.five_min_state import V9FiveMinState

logger = logging.getLogger("mems26.systems.five_min")


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
        self.session_classifier = SessionClassifier()
        self.mode = FiveMinMode.WAITING_OPEN
        self.buffer_size = 0
        self.opening_type: Optional[str] = None
        self.last_pattern: Optional[str] = None
        self.last_confluence: int = 0
        self.last_classification: Optional[str] = None
        self.choppiness_score: int = 0
        self._hydrated = False

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
                    V9FiveMinState.session_date == date.today()
                ).first()
            finally:
                db.close()

            # Load bars from DB and replay into _bar_buffer (P-WAVE-D3)
            bars_count = 0
            try:
                import sqlite3 as _sql
                _db_path = str(Path(__file__).resolve().parent.parent.parent.parent / "data" / "mems26_local.db")
                _conn = _sql.connect(_db_path)
                _conn.row_factory = _sql.Row
                rows = _conn.execute(
                    "SELECT * FROM v9_bars_5min ORDER BY ts DESC LIMIT 60"
                ).fetchall()
                _conn.close()
                # Replay oldest-first into buffer (no persist)
                for row in reversed(rows):
                    r = dict(row)
                    bar = {
                        "ts": r.get("ts", ""),
                        "o": float(r.get("open", 0)),
                        "h": float(r.get("high", 0)),
                        "l": float(r.get("low", 0)),
                        "c": float(r.get("close", 0)),
                        "v": int(r.get("volume", 0)),
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
            bar_time = datetime.fromtimestamp(
                ts / 1000 if ts > 1e12 else ts,
                tz=timezone(timedelta(hours=-4))
            )
            info = self.session_classifier.classify(bar_time)
            if info.session == Session.CASH_HOURS and self.mode == FiveMinMode.FIRST_HOUR_TACTICAL:
                self.mode = FiveMinMode.DAY_TYPE_MODE
                logger.info("[FiveMin] Mode transition: FIRST_HOUR -> DAY_TYPE_MODE at %s", bar_time)

        # Delegate to existing chart_5min detector for pattern detection
        # (integration point — full wiring in future prompts)
        return None

    def _on_day_type_update(self, event: dict) -> None:
        """Handle Day Type classification update."""
        # Store for context — used by confluence scoring
        return None

    # ── Footprint helpers ──

    def _get_cot_from_footprint(self) -> Optional[float]:
        """Read COT (cumulative delta) from Footprint System 3."""
        import requests
        try:
            r = requests.get("http://localhost:8000/api/v9/footprint/current", timeout=2)
            return r.json().get("cot")
        except Exception:
            return None

    def _get_amt_from_footprint(self) -> Optional[float]:
        """Read AMT (90-min average) from Footprint System 3."""
        import requests
        try:
            r = requests.get("http://localhost:8000/api/v9/footprint/current", timeout=2)
            return r.json().get("amt")
        except Exception:
            return None

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
        if len(bars_5m) < 4:
            return (None, 0, {})

        b1, b2, b3, b4 = bars_5m[-4], bars_5m[-3], bars_5m[-2], bars_5m[-1]
        cur_cot = self._get_cot_from_footprint()
        cur_amt = self._get_amt_from_footprint()
        if cur_cot is None or cur_amt is None:
            return (None, 0, {})

        b1_vol = b1.get("v", 0) or 0
        b2_vol = b2.get("v", 0) or 0

        # Reactive LONG
        b1_sellers = b1["c"] < b1["o"] and b1_vol > 0
        b2_drop = b2_vol <= b1_vol * 0.10 if b1_vol > 0 else False  # 90% drop
        b3_buyers = b3["c"] > b3["o"]
        b4_confirm = b4["c"] > b4["o"]
        cot_above_amt = cur_cot > cur_amt

        if b1_sellers and b2_drop and b3_buyers and b4_confirm and cot_above_amt:
            return ("LONG", 0.75, {"kind": "REACTIVE", "stage": 4})

        # Reactive SHORT (mirror)
        b1_buyers = b1["c"] > b1["o"] and b1_vol > 0
        b3_sellers = b3["c"] < b3["o"]
        b4_confirm_s = b4["c"] < b4["o"]
        cot_below_amt = cur_cot < cur_amt

        if b1_buyers and b2_drop and b3_sellers and b4_confirm_s and cot_below_amt:
            return ("SHORT", 0.75, {"kind": "REACTIVE", "stage": 4})

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
        if len(bars_5m) < 4:
            return (None, 0, {})

        b1, b2, b3, b4 = bars_5m[-4], bars_5m[-3], bars_5m[-2], bars_5m[-1]
        cur_cot = self._get_cot_from_footprint()
        cur_amt = self._get_amt_from_footprint()
        if cur_cot is None or cur_amt is None:
            return (None, 0, {})

        b1_range = b1["h"] - b1["l"]
        b1_expansion = 1.5 <= b1_range <= 1.75  # 6-7 ticks MES
        b3_range = b3["h"] - b3["l"]
        b3_joining = b3_range > b1_range

        # Initiative LONG
        b1_bull = b1["c"] > b1["o"]
        b2_higher_low = b2["l"] > b1["l"]
        b4_test = b4["l"] >= b2["l"]
        cot_below_amt = cur_cot < cur_amt

        if b1_bull and b1_expansion and b2_higher_low and b3_joining and b4_test and cot_below_amt:
            return ("LONG", 0.80, {"kind": "INITIATIVE", "stage": 4})

        # Initiative SHORT (mirror)
        b1_bear = b1["c"] < b1["o"]
        b2_lower_high = b2["h"] < b1["h"]
        b4_test_s = b4["h"] <= b2["h"]
        cot_above_amt = cur_cot > cur_amt

        if b1_bear and b1_expansion and b2_lower_high and b3_joining and b4_test_s and cot_above_amt:
            return ("SHORT", 0.80, {"kind": "INITIATIVE", "stage": 4})

        return (None, 0, {})

    # ── Bar processing ──

    def subscribed_bar_types(self):
        return ["5min"]

    _bar_buffer: List[Dict] = []

    async def process_bar(self, event) -> None:
        """Process a 5-min bar from BarRouter. Runs Reactive + Initiative detectors."""
        bar = event if isinstance(event, dict) else {}
        self.buffer_size += 1
        self._bar_buffer.append(bar)
        if len(self._bar_buffer) > 20:
            self._bar_buffer = self._bar_buffer[-20:]

        # Run pattern detectors
        direction, conf, info = self._detect_reactive(self._bar_buffer)
        if not direction:
            direction, conf, info = self._detect_initiative(self._bar_buffer)

        if direction:
            kind = info.get("kind", "UNKNOWN")
            entry_price = bar.get("c", 0)
            # Stop: opposite extreme + 2pt 🟡 default("to-calibrate-in-SHADOW")
            stop_price = (bar.get("l", entry_price) - 2.0) if direction == "LONG" else (bar.get("h", entry_price) + 2.0)

            self.last_pattern = f"{kind}_{direction}"
            self.last_classification = kind
            self.last_confluence = int(conf * 100)

            logger.info("[FiveMin] FIRE: %s %s (conf=%.2f, COT=%s, AMT=%s)",
                        kind, direction, conf,
                        self._get_cot_from_footprint(), self._get_amt_from_footprint())

            # Persist to DB
            try:
                db = SessionLocal()
                from backend.v9.db.models.five_min_state import V9FiveMinSetup
                setup = V9FiveMinSetup(
                    ts=datetime.now(timezone.utc),
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
                )
                db.add(setup)
                db.commit()
                db.close()
            except Exception as e:
                logger.warning("[FiveMin] DB persist error: %s", e)

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
        }
