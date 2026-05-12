"""System 5 — TPO Profile Observer (STANDALONE).

Builds TPO profile from 5-min bars. Publishes POC/VAH/VAL/shape.
Subscribes to 5min via BarRouter.
"""
import logging
import sqlite3
from datetime import datetime, date
from typing import List, Optional, Dict, Any

from backend.v9.systems.base.trading_system import BaseV9TradingSystem, HydrationResult, SystemType
from backend.v9.common.session_classifier import SessionClassifier, Session

logger = logging.getLogger(__name__)

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


class TPOSystem(BaseV9TradingSystem):
    system_id = 5
    name = "tpo"
    color = "#eab308"
    system_type = SystemType.OBSERVING

    def __init__(self, db_path: str = None):
        self.db_path = db_path or "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"
        self.session_clf = SessionClassifier()
        self.bar_buffer: List[Dict] = []
        self.max_buffer = 100
        self.tick_size = 0.25
        # TPO state
        self.profile: Dict[str, List[str]] = {}  # price_key -> [letters]
        self.current_letter_idx = 0
        self.current_session_id: Optional[str] = None
        self.current_session_type: Optional[str] = None
        self.ib_high: Optional[float] = None
        self.ib_low: Optional[float] = None
        self.ib_locked = False
        self._ib_width: Optional[float] = None
        self._ib_class: Optional[str] = None
        self._ib_locked_ts: Optional[str] = None
        self.current_state = {
            "running": False,
            "hydrated": False,
            "session_type": None,
            "poc": None,
            "vah": None,
            "val": None,
            "profile_shape": "NA",
            "opening_type": "NA",
            "ib_high": None,
            "ib_low": None,
            "ib_locked": False,
            "ib_width": None,
            "ib_class": None,
            "ib_locked_ts": None,
            "letter_count": 0,
            "buffer_size": 0,
            "bars_processed_today": 0,
        }

    def subscribed_bar_types(self) -> List[str]:
        return ["5min"]

    def hydrate(self) -> HydrationResult:
        self.current_state["running"] = True
        self.current_state["hydrated"] = True
        # Try to load today's session
        try:
            conn = sqlite3.connect(self.db_path)
            row = conn.execute(
                "SELECT * FROM v9_tpo_sessions WHERE trading_date=? ORDER BY id DESC LIMIT 1",
                (date.today().isoformat(),)
            ).fetchone()
            conn.close()
            if row:
                return HydrationResult(success=True, reached_state="RESUMED",
                                       notes="Loaded existing session from DB")
        except Exception as e:
            logger.warning(f"TPO hydrate DB read failed: {e}")
        return HydrationResult(success=True, reached_state="ACTIVE",
                               notes="TPO observer ready; subscribed via BarRouter")

    def process(self, event: Dict) -> Optional[Dict]:
        return None

    async def process_bar(self, event) -> None:
        try:
            bar = dict(event.payload) if hasattr(event, 'payload') else dict(event)
            self.bar_buffer.append(bar)
            if len(self.bar_buffer) > self.max_buffer:
                self.bar_buffer.pop(0)

            ts_str = getattr(event, 'ts', '') or bar.get('ts', '')
            session = getattr(event, 'session', 'UNKNOWN')

            # Determine session type
            session_type = "CASH" if session in ("CASH_OPEN", "FIRST_HOUR", "CASH_HOURS") else "GLOBEX"
            today = date.today().isoformat()
            session_id = f"{session_type}_{today}"

            # New session?
            if session_id != self.current_session_id:
                self._open_session(session_id, session_type, today, ts_str)

            # IB tracking (P3.2)
            self._update_ib(bar, session)

            # Add bar to profile
            high = bar.get("high", bar.get("h", 0))
            low = bar.get("low", bar.get("l", 0))
            close = bar.get("close", bar.get("c", 0))

            if high > 0 and low > 0:
                letter = LETTERS[min(self.current_letter_idx, len(LETTERS) - 1)]
                price = low
                while price <= high + 0.001:
                    key = f"{round(price / self.tick_size) * self.tick_size:.2f}"
                    if key not in self.profile:
                        self.profile[key] = []
                    if letter not in self.profile[key]:
                        self.profile[key].append(letter)
                    price += self.tick_size

                # Advance letter every 6 bars (30 min / 5 min = 6)
                if len(self.bar_buffer) % 6 == 0:
                    self.current_letter_idx += 1

                # IB tracking (first 12 bars = 60 min)
                if not self.ib_locked:
                    if self.ib_high is None or high > self.ib_high:
                        self.ib_high = high
                    if self.ib_low is None or low < self.ib_low:
                        self.ib_low = low
                    if self.current_state["bars_processed_today"] >= 12:
                        self.ib_locked = True

                # Compute POC / VAH / VAL
                poc, vah, val = self._compute_levels()

                # Shape detection
                shape = self._detect_shape()

                # Update state
                self.current_state.update({
                    "session_type": session_type,
                    "poc": poc,
                    "vah": vah,
                    "val": val,
                    "profile_shape": shape,
                    "ib_high": self.ib_high,
                    "ib_low": self.ib_low,
                    "ib_locked": self.ib_locked,
                    "ib_width": self._ib_width,
                    "ib_class": self._ib_class,
                    "ib_locked_ts": self._ib_locked_ts,
                    "letter_count": self.current_letter_idx + 1,
                    "buffer_size": len(self.bar_buffer),
                    "bars_processed_today": self.current_state["bars_processed_today"] + 1,
                })

                # Persist (LIVE only)
                mode = getattr(event, 'mode', 'LIVE')
                if mode == "LIVE":
                    self._persist_session(session_id, session_type, today, poc, vah, val, shape)
                    self._persist_letter(session_id, ts_str, letter, low, high)

        except Exception as e:
            logger.error(f"TPOSystem.process_bar error: {e}", exc_info=True)

    def _update_ib(self, bar: dict, session: str) -> None:
        """Update IB tracking during 09:30-10:30 ET cash session."""
        from datetime import time as _time
        # Only track IB during cash session
        if session not in ("CASH_OPEN", "FIRST_HOUR"):
            # After first hour, lock if not already locked
            if session == "CASH_HOURS" and self.ib_high is not None and not self.ib_locked:
                self.ib_locked = True
                self._ib_locked_ts = datetime.now(pytz.timezone('America/New_York')).isoformat() if 'pytz' in dir() else datetime.utcnow().isoformat()
                self._ib_width = (self.ib_high - self.ib_low) if self.ib_low else 0
                self._ib_class = self._classify_ib_width(self._ib_width)
                self._persist_ib_to_session()
                logger.info("[TPO] IB LOCKED: H=%.2f L=%.2f W=%.2f class=%s",
                            self.ib_high, self.ib_low, self._ib_width, self._ib_class)
            return

        if self.ib_locked:
            return

        bar_high = float(bar.get("high", bar.get("h", 0)))
        bar_low = float(bar.get("low", bar.get("l", 0)))
        if bar_high <= 0 or bar_low <= 0:
            return

        if self.ib_high is None:
            self.ib_high = bar_high
            self.ib_low = bar_low
        else:
            self.ib_high = max(self.ib_high, bar_high)
            self.ib_low = min(self.ib_low, bar_low)

    @staticmethod
    def _classify_ib_width(width: float) -> str:
        """Mind Over Markets thresholds."""
        if width < 15.0:
            return "NARROW"
        if width <= 25.0:
            return "MEDIUM"
        return "WIDE"

    def _persist_ib_to_session(self):
        """Write IB fields to current session row."""
        if not self.current_session_id:
            return
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """UPDATE v9_tpo_sessions SET ib_high=?, ib_low=?, ib_width=?,
                   ib_class=?, ib_locked=1, ib_locked_ts=? WHERE session_id=?""",
                (self.ib_high, self.ib_low, self._ib_width, self._ib_class,
                 self._ib_locked_ts, self.current_session_id)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"TPO IB persist failed: {e}")

    def _open_session(self, session_id, session_type, today, ts_str):
        self.current_session_id = session_id
        self.current_session_type = session_type
        self.profile = {}
        self.current_letter_idx = 0
        self.ib_high = None
        self.ib_low = None
        self.ib_locked = False
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "INSERT OR IGNORE INTO v9_tpo_sessions (session_id, session_type, trading_date, opened_ts) VALUES (?,?,?,?)",
                (session_id, session_type, today, ts_str)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"TPO open session failed: {e}")

    def _compute_levels(self):
        if not self.profile:
            return None, None, None
        # POC = price with most letters
        sorted_prices = sorted(self.profile.items(), key=lambda x: len(x[1]), reverse=True)
        poc = float(sorted_prices[0][0]) if sorted_prices else None

        # Value Area = 70% of total letters
        total_letters = sum(len(v) for v in self.profile.values())
        target = total_letters * 0.7
        # Start from POC, expand up/down
        prices_sorted = sorted([float(k) for k in self.profile.keys()])
        if not prices_sorted or poc is None:
            return poc, None, None
        poc_idx = min(range(len(prices_sorted)), key=lambda i: abs(prices_sorted[i] - poc))
        accumulated = len(self.profile.get(f"{poc:.2f}", []))
        lo, hi = poc_idx, poc_idx
        while accumulated < target and (lo > 0 or hi < len(prices_sorted) - 1):
            up_count = len(self.profile.get(f"{prices_sorted[min(hi + 1, len(prices_sorted) - 1)]:.2f}", [])) if hi < len(prices_sorted) - 1 else 0
            dn_count = len(self.profile.get(f"{prices_sorted[max(lo - 1, 0)]:.2f}", [])) if lo > 0 else 0
            if up_count >= dn_count and hi < len(prices_sorted) - 1:
                hi += 1
                accumulated += up_count
            elif lo > 0:
                lo -= 1
                accumulated += dn_count
            else:
                break
        vah = prices_sorted[hi] if hi < len(prices_sorted) else None
        val = prices_sorted[lo] if lo >= 0 else None
        return poc, vah, val

    def _detect_shape(self) -> str:
        if not self.profile or self.current_letter_idx < 2:
            return "NA"
        prices = sorted([float(k) for k in self.profile.keys()])
        if len(prices) < 3:
            return "NA"
        total = len(prices)
        poc, _, _ = self._compute_levels()
        if poc is None:
            return "NA"
        poc_pos = (poc - prices[0]) / (prices[-1] - prices[0]) if prices[-1] != prices[0] else 0.5

        if 0.35 <= poc_pos <= 0.65:
            return "D"
        elif poc_pos > 0.65:
            return "b"
        elif poc_pos < 0.35:
            return "P"
        return "neutral"

    def _persist_session(self, session_id, session_type, today, poc, vah, val, shape):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """UPDATE v9_tpo_sessions SET poc_price=?, vah_price=?, val_price=?,
                   profile_shape=?, ib_high=?, ib_low=?, ib_locked=?, letter_count=?
                   WHERE session_id=?""",
                (poc, vah, val, shape, self.ib_high, self.ib_low, int(self.ib_locked),
                 self.current_letter_idx + 1, session_id)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"TPO session persist failed: {e}")

    def _persist_letter(self, session_id, ts, letter, low, high):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "INSERT INTO v9_tpo_journal (session_id, ts, letter, price_low, price_high) VALUES (?,?,?,?,?)",
                (session_id, ts, letter, low, high)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"TPO letter persist failed: {e}")

    def get_current(self) -> dict:
        return dict(self.current_state)
