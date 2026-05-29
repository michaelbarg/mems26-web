"""BuildStatusAggregator — joins S2, Woodies, and Day Type system states.

Source: BUILD_STATUS_ENDPOINT_DESIGN.md §5.1–5.5
Read-only: no DB writes. Uses sqlite3 URI mode=ro.
No self-HTTP calls: per §5.4 "do NOT have the endpoint curl /api/v9/woodies/current"
"""

import logging
import sqlite3
import time
from datetime import date, datetime, timezone

from backend.v9.common.trading_date import et_today
from typing import Optional, List

from .types import BuildStatusResponse, SystemStatus, RTBSession
from . import s2_inspector, woodies_inspector, day_type_inspector, bridge_inspector

logger = logging.getLogger(__name__)

DB_PATH = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"

_WARN_RATE_ANCHOR: dict = {}  # {key: last_warn_ts} for rate-limiting


def _rate_limited_warn(key: str, msg: str, interval_s: float = 60.0) -> None:
    """Log warning at most once per interval_s for a given key.

    Constraint (c): every try/except must log logger.warning().
    Rate-limited to avoid log flooding on hot path.

    Default anchor is float('-inf') so the first call ALWAYS fires regardless
    of process uptime (avoids the 0.0 trap where time.monotonic() < 60s on startup).
    """
    now = time.monotonic()
    if now - _WARN_RATE_ANCHOR.get(key, float("-inf")) >= interval_s:
        _WARN_RATE_ANCHOR[key] = now
        logger.warning(msg)


class BuildStatusAggregator:
    """Aggregates build status from all three live systems.

    Usage:
        agg = BuildStatusAggregator(five_min_system, woodies_system, day_type_machine)
        response = agg.get_status()

    All system args may be None — returns running=false, hydrated=false gracefully.
    Per BUILD_STATUS_ENDPOINT_DESIGN.md §5.5: never raise 500.
    """

    def __init__(
        self,
        five_min_system=None,
        woodies_system=None,
        day_type_machine=None,
        db_path: Optional[str] = None,
    ):
        self._five_min_system = five_min_system
        self._woodies_system = woodies_system
        self._day_type_machine = day_type_machine
        self._db_path = db_path or DB_PATH

    def _get_current_day_type(self) -> Optional[str]:
        """Read today's day_type from v9_day_type_history (same SQL as day_type_v9_routes.py).

        Returns day_type string (e.g. "Neutral_Center") or None if not yet classified.
        Read-only sqlite3 URI per constraint (g).
        """
        today = et_today().isoformat()
        try:
            conn = sqlite3.connect(
                f"file:{self._db_path}?mode=ro&immutable=1", uri=True
            )
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT day_type, ib_width_class FROM v9_day_type_history WHERE date = ? LIMIT 1",
                (today,),
            ).fetchone()
            conn.close()
            if row is None:
                return None
            ib_width_class = row["ib_width_class"]
            is_developing = ib_width_class == "DEVELOPING"
            day_type = row["day_type"]
            if is_developing or day_type in (None, "UNKNOWN"):
                return None
            return day_type
        except Exception as e:
            _rate_limited_warn(
                "agg_day_type_read",
                f"[BuildStatus/Agg] day_type DB read failed: {e}",
            )
            return None

    def get_status(self, systems: Optional[List[str]] = None) -> BuildStatusResponse:
        """Aggregate all system statuses into a BuildStatusResponse.

        Args:
            systems: Optional list of system IDs to include.
                     Defaults to ["five_min", "woodies", "day_type"].

        Returns:
            BuildStatusResponse (never raises — failures are captured in errors[]).

        Per BUILD_STATUS_ENDPOINT_DESIGN.md §5.5:
        "If any inspector raises → wrap in try/except, log logger.warning (rate-limited),
        and emit a partial result with that system marked status: 'unknown' and errors: [...]"
        """
        if systems is None:
            systems = ["bridge", "five_min", "woodies", "day_type"]

        now_utc = datetime.now(timezone.utc)
        errors: List[str] = []

        # Resolve current day type once (used by S2 inspector)
        day_type_str = self._get_current_day_type()

        result_systems: List[SystemStatus] = []

        # ── Bridge Live Feed ────────────────────────────────────────────────
        if "bridge" in systems:
            try:
                br_sys = bridge_inspector.inspect(db_path=self._db_path)
                result_systems.append(br_sys)
            except Exception as e:
                _rate_limited_warn(
                    "agg_bridge_inspector",
                    f"[BuildStatus/Agg] bridge_inspector.inspect() raised: {e}",
                )
                errors.append(f"bridge_inspector failed: {e}")
                result_systems.append(SystemStatus(
                    id="bridge",
                    name="Bridge · Live Data Feed",
                    running=False,
                    hydrated=False,
                ))

        # ── S2 Five-Minute ──────────────────────────────────────────────────
        if "five_min" in systems:
            try:
                s2_sys = s2_inspector.inspect(
                    five_min_system=self._five_min_system,
                    day_type_str=day_type_str,
                )
                result_systems.append(s2_sys)
            except Exception as e:
                _rate_limited_warn(
                    "agg_s2_inspector",
                    f"[BuildStatus/Agg] s2_inspector.inspect() raised: {e}",
                )
                errors.append(f"s2_inspector failed: {e}")
                result_systems.append(SystemStatus(
                    id="five_min",
                    name="S2 · Five-Minute Patterns",
                    running=False,
                    hydrated=False,
                ))

        # ── Woodies ─────────────────────────────────────────────────────────
        if "woodies" in systems:
            try:
                w_sys = woodies_inspector.inspect(
                    woodies_system=self._woodies_system,
                )
                result_systems.append(w_sys)
            except Exception as e:
                _rate_limited_warn(
                    "agg_woodies_inspector",
                    f"[BuildStatus/Agg] woodies_inspector.inspect() raised: {e}",
                )
                errors.append(f"woodies_inspector failed: {e}")
                result_systems.append(SystemStatus(
                    id="woodies",
                    name="S4 · Woodies CCI Patterns",
                    running=False,
                    hydrated=False,
                ))

        # ── Day Type ────────────────────────────────────────────────────────
        if "day_type" in systems:
            try:
                dt_sys = day_type_inspector.inspect(
                    day_type_machine=self._day_type_machine,
                )
                result_systems.append(dt_sys)
            except Exception as e:
                _rate_limited_warn(
                    "agg_day_type_inspector",
                    f"[BuildStatus/Agg] day_type_inspector.inspect() raised: {e}",
                )
                errors.append(f"day_type_inspector failed: {e}")
                result_systems.append(SystemStatus(
                    id="day_type",
                    name="S1 · Day Type Classification",
                    running=False,
                    hydrated=False,
                ))

        # RTB session (simple clock check — no market calendar integration)
        rtb = _compute_rtb_session(now_utc)

        return BuildStatusResponse(
            ts=now_utc.isoformat(),
            build_version="v1",
            session_date=et_today().isoformat(),
            rtb_session=rtb,
            systems=result_systems,
            errors=errors,
        )


def _compute_rtb_session(now_utc: datetime) -> RTBSession:
    """Approximate RTH session window (09:30–16:00 ET).

    Naive UTC offset used: ET = UTC-4 (summer) / UTC-5 (winter).
    Precise DST is not critical for this debug surface.
    """
    try:
        from zoneinfo import ZoneInfo
        et = ZoneInfo("America/New_York")
        now_et = now_utc.astimezone(et)
        market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
        now_min_of_day = now_et.hour * 60 + now_et.minute
        open_min = 9 * 60 + 30
        close_min = 16 * 60
        in_session = open_min <= now_min_of_day < close_min
        minutes_to_open = max(0, open_min - now_min_of_day) if not in_session else 0
        minutes_to_close = max(0, close_min - now_min_of_day) if in_session else None
        return RTBSession(
            in_session=in_session,
            minutes_to_open=minutes_to_open if not in_session else None,
            minutes_to_close=minutes_to_close,
        )
    except Exception as e:
        logger.warning("[BuildStatus/Agg] RTB session compute failed: %s", e)
        return RTBSession()
