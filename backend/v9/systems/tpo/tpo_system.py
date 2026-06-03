"""System 5 — TPO Profile Observer (STANDALONE).

Builds TPO profile from 5-min bars. Publishes POC/VAH/VAL/shape.
Subscribes to 5min via BarRouter.
"""
import logging
from datetime import datetime, date

from backend.v9.common.trading_date import et_today
from typing import List, Optional, Dict, Any

from backend.v9.systems.base.trading_system import BaseV9TradingSystem, HydrationResult, SystemType
from backend.v9.common.session_classifier import SessionClassifier, Session
from backend.v9.services.market_clock import now_utc as _market_now_utc

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
        # POC Migration (P-TPO-A.2)
        self._previous_poc: Optional[float] = None
        self._poc_stuck_since: Optional[datetime] = None
        self._poc_migration: Optional[Dict] = None
        self._previous_direction: Optional[str] = None
        # HVN/LVN (P-TPO-A.3)
        self._hvn_zones: List[Dict] = []
        self._lvn_zones: List[Dict] = []
        self._previous_hvn_count: int = -1
        # Volume Cluster (P-TPO-A.4)
        self._volume_cluster: Optional[Dict] = None
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
            "poc_migration": None,
            "hvn_zones": [],
            "lvn_zones": [],
            "volume_cluster": None,
            "letter_count": 0,
            "buffer_size": 0,
            "bars_processed_today": 0,
        }

    def subscribed_bar_types(self) -> List[str]:
        return ["5min"]

    def hydrate(self) -> HydrationResult:
        self.current_state["running"] = True
        self.current_state["hydrated"] = True
        # Try to load today's session — PA2-D2: restore IB state on restart
        try:
            from backend.v9.db.read import read_one
            row = read_one(
                "SELECT * FROM v9_tpo_sessions WHERE trading_date=:today ORDER BY id DESC LIMIT 1",
                {"today": et_today().isoformat()},
            )
            if row:
                r = dict(row)
                # Restore IB state from DB (PA2-D2: critical for post-restart)
                if r.get("ib_high") is not None and r.get("ib_low") is not None:
                    self.ib_high = float(r["ib_high"])
                    self.ib_low = float(r["ib_low"])
                    if r.get("ib_locked"):
                        self.ib_locked = True
                        self._ib_width = self.ib_high - self.ib_low
                        self._ib_class = self._classify_ib_width(self._ib_width)
                        self._ib_locked_ts = r.get("ib_locked_ts")
                    self.current_state.update({
                        "ib_high": self.ib_high,
                        "ib_low": self.ib_low,
                        "ib_locked": self.ib_locked,
                        "ib_width": self._ib_width,
                        "ib_class": self._ib_class,
                        "ib_locked_ts": self._ib_locked_ts,
                    })
                    logger.info("[TPO] Hydrated IB from DB: H=%.2f L=%.2f locked=%s W=%s",
                                self.ib_high, self.ib_low, self.ib_locked, self._ib_width)
                # Restore POC/VAH/VAL
                if r.get("poc_price") is not None:
                    self.current_state["poc"] = float(r["poc_price"])
                if r.get("vah_price") is not None:
                    self.current_state["vah"] = float(r["vah_price"])
                if r.get("val_price") is not None:
                    self.current_state["val"] = float(r["val_price"])
                return HydrationResult(success=True, reached_state="RESUMED",
                                       notes=f"Loaded session from DB: IB locked={self.ib_locked}")
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
            today = et_today().isoformat()
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

                # IB intentionally NOT tracked here — Sierra Study ID:6 is
                # the source of truth (handled in self._update_ib() called
                # at line 151). Pre-LIVE source-of-truth cleanup
                # (2026-05-28): removed the second bar-based IB accumulator
                # which was overwriting Sierra's locked IB with running
                # session_high/low values (e.g. 7574/7525.5 instead of the
                # real 7543.75/7522.0 IB). See _update_ib() docstring.

                # Compute POC / VAH / VAL
                poc, vah, val = self._compute_levels()

                # Shape detection
                shape = self._detect_shape()

                # POC Migration (P-TPO-A.2)
                if poc is not None:
                    now_dt = _market_now_utc()  # Prompt 26b: replay-safe
                    self._poc_migration = self._update_poc_migration(poc, now_dt)

                # HVN/LVN + Volume Cluster (P-TPO-A.3/A.4) — compute from profile
                self._hvn_zones, self._lvn_zones = self._compute_volume_nodes_from_profile()
                # W4-δ: UFL/UFH detection
                self._ufl_ufh = self._compute_ufl_ufh()
                self._volume_cluster = self._compute_volume_cluster_from_profile()

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
                    "poc_migration": self._poc_migration,
                    "hvn_zones": self._hvn_zones,
                    "lvn_zones": self._lvn_zones,
                    "volume_cluster": self._volume_cluster,
                    "ufl_ufh": getattr(self, '_ufl_ufh', {"ufl": None, "ufh": None}),
                    "otf_clarity": self._compute_otf_clarity(),
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

    def _update_poc_migration(self, current_poc: float, bar_ts: datetime) -> Dict:
        """POC migration tracker per MP_SPEC_V1. (P-TPO-A.2)"""
        STUCK_THRESHOLD = 0.5
        prev_poc = self._previous_poc
        if prev_poc is None:
            self._previous_poc = current_poc
            self._poc_stuck_since = bar_ts
            return {"direction": "STUCK", "magnitude_pts": 0.0, "stuck_minutes": 0, "previous_poc": None}

        delta = current_poc - prev_poc
        mag = abs(delta)
        if mag <= STUCK_THRESHOLD:
            direction = "STUCK"
            stuck_min = int((bar_ts - self._poc_stuck_since).total_seconds() / 60) if self._poc_stuck_since else 0
        elif delta > 0:
            direction = "UP"
            stuck_min = 0
            self._poc_stuck_since = bar_ts
        else:
            direction = "DOWN"
            stuck_min = 0
            self._poc_stuck_since = bar_ts

        self._previous_poc = current_poc
        return {"direction": direction, "magnitude_pts": round(mag, 2), "stuck_minutes": stuck_min, "previous_poc": round(prev_poc, 2)}

    def _compute_volume_nodes_from_profile(self) -> tuple:
        """HVN/LVN from TPO profile letter counts. (P-TPO-A.3)"""
        if not self.profile or len(self.profile) < 5:
            return [], []
        counts = [(float(k), len(v)) for k, v in self.profile.items()]
        vols = sorted([c for _, c in counts])
        n = len(vols)
        p80 = vols[int(0.8 * n)] if n > 5 else vols[-1]
        p60 = vols[int(0.6 * n)] if n > 5 else vols[-1]
        p10 = vols[max(0, int(0.1 * n))]
        p25 = vols[max(0, int(0.25 * n))]

        hvn, lvn = [], []
        for price, count in counts:
            if count >= p80:
                hvn.append({"price": price, "type": "PRIMARY_HVN", "letters": count})
            elif count >= p60:
                hvn.append({"price": price, "type": "SECONDARY_HVN", "letters": count})
            if count <= p10:
                lvn.append({"price": price, "type": "PRIMARY_LVN", "letters": count})
            elif count <= p25:
                lvn.append({"price": price, "type": "SECONDARY_LVN", "letters": count})
        return hvn, lvn

    def _compute_volume_cluster_from_profile(self) -> Optional[Dict]:
        """Top 3 prices by letter count + weighted center. (P-TPO-A.4)"""
        if not self.profile:
            return None
        counts = sorted([(float(k), len(v)) for k, v in self.profile.items()], key=lambda x: x[1], reverse=True)
        top3 = counts[:3]
        if not top3:
            return None
        total = sum(c for _, c in top3)
        center = sum(p * c for p, c in top3) / total if total > 0 else None
        return {"prices": sorted([round(p, 2) for p, _ in top3]), "center": round(center, 2) if center else None}

    def _compute_ufl_ufh(self) -> Dict:
        """Detect Unfair Low/High from TPO letter profile. (W4-δ)"""
        if not self.profile:
            return {"ufl": None, "ufh": None, "reasoning_notes": "No letter data"}
        # profile: price_key (str) → list of letters
        counts = {float(k): len(v) for k, v in self.profile.items() if v}
        prices = sorted(counts.keys())
        if not prices:
            return {"ufl": None, "ufh": None, "reasoning_notes": "Empty profile"}
        session_low = prices[0]
        session_high = prices[-1]
        notes = []
        ufh = session_high if counts.get(session_high, 0) == 1 else None
        ufl = session_low if counts.get(session_low, 0) == 1 else None
        if ufh:
            notes.append(f"UFH at {ufh:.2f} (1 letter at session high)")
        if ufl:
            notes.append(f"UFL at {ufl:.2f} (1 letter at session low)")
        if not notes:
            notes.append("No UFL/UFH (extremes have multiple letters)")
        return {"ufl": ufl, "ufh": ufh, "reasoning_notes": "; ".join(notes)}

    def _compute_otf_clarity(self) -> str:
        """Compute OTF Clarity from TPO profile tails (PROMPT 1 · 1.6a).

        Per tpo/schemas.py OTFClarity enum:
          BOTH_CLEAR:    buying + selling tail → all trades OK
          SELLERS_CLEAR: selling tail only → LONG preferred
          BUYERS_CLEAR:  buying tail only → SHORT preferred
          UNCLEAR:       neither tail → no clear direction

        Tails: consecutive single-letter levels at session extremes.
        Buying tail = at session LOW (buyers rejected lower).
        Selling tail = at session HIGH (sellers rejected higher).
        """
        if not self.profile:
            return "UNCLEAR"
        counts = {float(k): len(v) for k, v in self.profile.items() if v}
        if not counts:
            return "UNCLEAR"
        prices = sorted(counts.keys())

        # Count buying tail (from bottom, consecutive single-letter)
        buying_tail = 0
        for p in prices:
            if counts.get(p, 0) <= 1:
                buying_tail += 1
            else:
                break

        # Count selling tail (from top, consecutive single-letter)
        selling_tail = 0
        for p in reversed(prices):
            if counts.get(p, 0) <= 1:
                selling_tail += 1
            else:
                break

        MIN_TAIL = 2  # minimum letters for a valid tail
        has_buying = buying_tail >= MIN_TAIL
        has_selling = selling_tail >= MIN_TAIL

        if has_buying and has_selling:
            return "BOTH_CLEAR"
        elif has_selling:
            return "SELLERS_CLEAR"
        elif has_buying:
            return "BUYERS_CLEAR"
        return "UNCLEAR"

    def _update_ib(self, bar: dict, session: str) -> None:
        """IB authoritative source: Sierra Study ID:6 via tpo.json.

        Pre-LIVE source-of-truth cleanup (2026-05-28):
        - Removed in-process MAX/MIN computation from incoming 5min bars
          (used to write divergent values to v9_tpo_sessions.ib_*).
        - Removed DB recovery fallback (was perpetuating bad data across
          restarts).
        - IB now comes from `_load_sierra_tpo()['ib_high'|'ib_low'|'ib_width']`
          and is persisted to v9_tpo_sessions whenever Sierra reports a
          locked IB (ib_found=true).

        Side-effects:
        - Sets self.ib_high / self.ib_low / self._ib_width / self._ib_class
        - Sets self.ib_locked when Sierra Study locked (10:30 ET onward)
        - Persists to v9_tpo_sessions row on transition to locked
        """
        try:
            from backend.v9.api.v9.tpo_routes import _load_sierra_tpo
            sierra = _load_sierra_tpo() or {}
        except Exception as e:
            logger.debug("[TPO] Sierra tpo.json load failed for IB update: %s", e)
            return

        if not sierra.get("ib_found"):
            return  # Pre-RTH or Sierra Study not yet emitting → leave NULL

        try:
            ib_high = float(sierra.get("ib_high"))
            ib_low = float(sierra.get("ib_low"))
        except (TypeError, ValueError):
            return
        if ib_high <= 0 or ib_low <= 0 or ib_high < ib_low:
            return

        prev_high, prev_low = self.ib_high, self.ib_low
        self.ib_high = ib_high
        self.ib_low = ib_low
        self._ib_width = ib_high - ib_low
        self._ib_class = self._classify_ib_width(self._ib_width)

        # Sierra's `ib_locked` is True once the Study finishes the 09:30-10:30
        # window. We mirror that flag so downstream consumers (A4, A2) see
        # the same lock state Sierra shows on chart.
        was_locked = self.ib_locked
        self.ib_locked = bool(sierra.get("ib_locked"))
        if self.ib_locked and not self._ib_locked_ts:
            self._ib_locked_ts = _market_now_utc().isoformat()
        # Persist on lock transition OR whenever Sierra reports new values
        # (covers Michael's "1:1 tracking" requirement — if Sierra changes IB
        # mid-session because the study was re-configured, DB follows).
        if self.ib_locked != was_locked or prev_high != ib_high or prev_low != ib_low:
            self._persist_ib_to_session()
        if self.ib_locked and not was_locked:
            logger.info("[TPO] IB LOCKED (from Sierra): H=%.2f L=%.2f W=%.2f class=%s",
                        self.ib_high, self.ib_low, self._ib_width, self._ib_class)
        elif prev_high != ib_high or prev_low != ib_low:
            logger.info("[TPO] IB updated from Sierra: H=%.2f L=%.2f W=%.2f class=%s",
                        self.ib_high, self.ib_low, self._ib_width, self._ib_class)

    @staticmethod
    def _classify_ib_width(width: float) -> str:
        """Mind Over Markets thresholds."""
        if width < 15.0:
            return "NARROW"
        if width <= 25.0:
            return "MEDIUM"
        return "WIDE"

    def _persist_ib_to_session(self):
        """Write Sierra-sourced IB fields to current session row.

        Mirrors Sierra 1:1 (pre-LIVE "doesn't lock the way it locked"
        requirement 2026-05-28). Always called from `_update_ib()` after
        Sierra emits a real IB (`ib_found=true`), so we never write NULL/0
        here — Sierra-silent path is handled by the COALESCE-guarded
        `_persist_session()`.
        """
        if not self.current_session_id:
            return
        from backend.v9.db.safe_writer import safe_execute
        safe_execute(
            """UPDATE v9_tpo_sessions SET ib_high=?, ib_low=?, ib_width=?,
               ib_class=?, ib_locked=?, ib_locked_ts=COALESCE(?, ib_locked_ts)
               WHERE session_id=?""",
            (self.ib_high, self.ib_low, self._ib_width, self._ib_class,
             int(self.ib_locked), self._ib_locked_ts, self.current_session_id),
        )

    def _open_session(self, session_id, session_type, today, ts_str):
        # Pre-LIVE "doesn't lock the way it locked" (2026-05-28):
        # Only reset IB state when the trading_date changes. Switching session
        # type within the same trading_date (e.g. GLOBEX→CASH at 09:30 ET, or
        # a re-open due to bridge resubscribe) must NOT wipe a Sierra-emitted
        # locked IB. Sierra is the source of truth; in-memory cache mirrors it.
        prev_session_id = self.current_session_id
        prev_trading_date = (
            prev_session_id.split("_", 1)[1]
            if prev_session_id and "_" in prev_session_id
            else None
        )
        self.current_session_id = session_id
        self.current_session_type = session_type
        self.profile = {}
        self.current_letter_idx = 0
        if prev_trading_date != today:
            self.ib_high = None
            self.ib_low = None
            self.ib_locked = False
            self._ib_width = None
            self._ib_class = None
            self._ib_locked_ts = None
        from backend.v9.db.safe_writer import safe_execute
        safe_execute(
            "INSERT OR IGNORE INTO v9_tpo_sessions (session_id, session_type, trading_date, opened_ts) VALUES (?,?,?,?)",
            (session_id, session_type, today, ts_str),
        )

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
        # Pre-LIVE "doesn't lock the way it locked" (2026-05-28):
        # Use COALESCE on IB columns so a transient `self.ib_*=None` (e.g.
        # Sierra Study cleared subgraphs post-lock) does NOT wipe a previously
        # captured Sierra-emitted locked IB. _update_ib() always overwrites
        # the row when Sierra emits a real IB, so 1:1 tracking is preserved;
        # this only prevents data loss when Sierra goes silent.
        from backend.v9.db.safe_writer import safe_execute
        safe_execute(
            """UPDATE v9_tpo_sessions SET
                   poc_price=?, vah_price=?, val_price=?, profile_shape=?,
                   ib_high=COALESCE(?, ib_high),
                   ib_low=COALESCE(?, ib_low),
                   ib_locked=CASE WHEN ? IS NULL THEN ib_locked ELSE ? END,
                   letter_count=?
               WHERE session_id=?""",
            (
                poc, vah, val, shape,
                self.ib_high, self.ib_low,
                self.ib_high, int(self.ib_locked),
                self.current_letter_idx + 1, session_id,
            ),
        )

    def _persist_letter(self, session_id, ts, letter, low, high):
        from backend.v9.db.safe_writer import safe_execute
        safe_execute(
            "INSERT INTO v9_tpo_journal (session_id, ts, letter, price_low, price_high) VALUES (?,?,?,?,?)",
            (session_id, ts, letter, low, high),
        )

    def get_current(self) -> dict:
        return dict(self.current_state)
