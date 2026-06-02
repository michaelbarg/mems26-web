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

from .types import BuildStatusResponse, SystemStatus, RTBSession, Readiness, ReadinessCheck
from . import s2_inspector, woodies_inspector, day_type_inspector, bridge_inspector, footprint_inspector

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
        footprint_system=None,
        db_path: Optional[str] = None,
    ):
        self._five_min_system = five_min_system
        self._woodies_system = woodies_system
        self._footprint_system = footprint_system
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
            systems = ["bridge", "five_min", "footprint", "woodies", "day_type"]

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

        # ── S3 Footprint ────────────────────────────────────────────────────
        if "footprint" in systems:
            try:
                fp_sys = footprint_inspector.inspect(
                    footprint_system=self._footprint_system,
                )
                result_systems.append(fp_sys)
            except Exception as e:
                _rate_limited_warn(
                    "agg_footprint_inspector",
                    f"[BuildStatus/Agg] footprint_inspector.inspect() raised: {e}",
                )
                errors.append(f"footprint_inspector failed: {e}")
                result_systems.append(SystemStatus(
                    id="footprint",
                    name="S3 · Footprint Patterns",
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

        # D-RDY: readiness verdict from PRE_TRADE_PROTOCOL checks
        readiness = _compute_readiness(result_systems, rtb)

        return BuildStatusResponse(
            ts=now_utc.isoformat(),
            build_version="v1",
            session_date=et_today().isoformat(),
            rtb_session=rtb,
            systems=result_systems,
            errors=errors,
            readiness=readiness,
        )


def _compute_readiness(systems: List[SystemStatus], rtb: RTBSession) -> Readiness:
    """D-RDY: derive READY/DEGRADED/BLOCKED from system states.

    Maps PRE_TRADE_PROTOCOL Phase 0-4 checks. Read-only — does NOT gate firing.
    RTH-aware: bridge DEAD outside RTH (09:30-16:00 ET) downgrades to 'info'.
    """
    checks: list = []
    in_rth = rtb.in_session

    # Helper: find system by id
    sys_map = {s.id: s for s in systems}

    # Check 1: bridge streams fresh (block during RTH, info outside)
    bridge = sys_map.get("bridge")
    if bridge:
        all_fresh = all(g.present for g in bridge.global_gates) if bridge.global_gates else False
        dead_gates = [g.key for g in bridge.global_gates if not g.present]
        severity = "block" if in_rth else "info"
        checks.append(ReadinessCheck(
            key="bridge_streams_fresh",
            passed=all_fresh,
            severity=severity,
            detail=f"dead: {','.join(dead_gates)}" if dead_gates else None,
        ))

    # Check 2: S1 day_type classified
    dt = sys_map.get("day_type")
    if dt:
        day_type_val = None
        for inp in dt.live_inputs:
            if inp.field == "day_type":
                day_type_val = inp.value
                break
        for interp in dt.interpretations:
            if interp.key == "day_type" and interp.value:
                day_type_val = interp.value
                break
        classified = day_type_val not in (None, "", "UNKNOWN", "unknown")
        checks.append(ReadinessCheck(
            key="s1_day_type_classified",
            passed=classified,
            severity="degrade",
            detail=f"day_type={day_type_val}",
        ))

    # Check 3: S4 trend not stuck GRAY
    woodies = sys_map.get("woodies")
    if woodies:
        trend_val = None
        for inp in woodies.live_inputs:
            if inp.field == "trend_state":
                trend_val = inp.value
                break
        trend_ok = trend_val in ("BLUE", "RED")
        checks.append(ReadinessCheck(
            key="s4_trend_not_stuck_gray",
            passed=trend_ok,
            severity="degrade",
            detail=f"trend_state={trend_val}",
        ))

    # Check 4: in RTH (info only)
    checks.append(ReadinessCheck(
        key="in_rth",
        passed=in_rth,
        severity="info",
        detail="RTH 09:30-16:00 ET" if in_rth else "outside RTH",
    ))

    # Compute verdict
    has_block_fail = any(not c.passed and c.severity == "block" for c in checks)
    has_degrade_fail = any(not c.passed and c.severity == "degrade" for c in checks)

    if has_block_fail:
        first_blocker = next(c for c in checks if not c.passed and c.severity == "block")
        return Readiness(verdict="BLOCKED", reason=first_blocker.detail or first_blocker.key, checks=checks)
    elif has_degrade_fail:
        first_degrader = next(c for c in checks if not c.passed and c.severity == "degrade")
        return Readiness(verdict="DEGRADED", reason=first_degrader.detail or first_degrader.key, checks=checks)
    else:
        return Readiness(verdict="READY", reason="all checks passed", checks=checks)


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
