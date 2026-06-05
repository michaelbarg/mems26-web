"""Woodies CCI inspector — produces 9 pattern status objects.

Source: BUILD_STATUS_ENDPOINT_DESIGN.md §4.2
Pattern list: D-092_S4_WOODIES_UPDATE.md §2 (🔒 LOCKED)
Decision tree stages: MEMS26_WOODIES_DECISION_TREE_V1.md A1..A7, B1..B14
"""

import logging
from datetime import date, datetime, time as _time, timezone
from typing import Optional

from backend.v9.common.trading_date import et_today
from backend.v9.db.read import read_scalar
from .types import PatternStatus, Component, SystemStatus, DataFreshness
from .auth_table_lookup import WOODIES_PATTERN_IDS
from .row_helpers import (
    fires_today,
    freshness_now,
    latest_valid_db_ts,
    make_freshness,
)

# firing_system enum value for Woodies CCI (S4), per
# `backend/v9/services/trade_manager/manager.py` write path.
_FIRING_SYSTEM_WOODIES = 4

logger = logging.getLogger(__name__)

DB_PATH = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"

# Human-readable names per D-092 §2
_PATTERN_NAMES = {
    "ZLR": "Zero Line Reject",
    "TLB": "Trend Line Break",
    "TT": "Tony Trade / Turbo Touch",
    "GB100": "Ghost Bar at ±100",
    "Vegas": "Vegas Divergence / Cup-and-Handle",
    "Ghost": "CCI Head-and-Shoulders",
    "FaMir": "Failed ZLR at ±200",
    "HTLB": "Horizontal Trend Line Break",
    "HFE": "Hook From Extreme",
}

# Map spec IDs (per D-092 §2) → actual engine pattern_ids (PatternResult.pattern_id)
# PatternResult uses ALL_CAPS; spec uses mixed-case for VEGAS/GHOST/FAMIR
_SPEC_ID_TO_ENGINE = {
    "ZLR": "ZLR",
    "TLB": "TLB",
    "TT": "TT",
    "GB100": "GB100",
    "Vegas": "VEGAS",
    "Ghost": "GHOST",
    "FaMir": "FAMIR",
    "HTLB": "HTLB",
    "HFE": "HFE",
}

# Trend states that allow trading (from MEMS26_WOODIES_DECISION_TREE_V1.md §4 A1)
_TRADING_TREND_STATES = {"BLUE", "RED"}


def inspect(woodies_system=None) -> SystemStatus:
    """Build the Woodies CCI system status with 9 patterns.

    Reads WoodiesSystem.get_current() state — no self-HTTP calls.
    Per BUILD_STATUS_ENDPOINT_DESIGN.md §5.4: all inspectors run in-process.

    Args:
        woodies_system: WoodiesSystem instance from app.state (may be None)
    """
    system = SystemStatus(
        id="woodies",
        name="S4 · Woodies CCI Patterns",
    )

    if woodies_system is None:
        # BUILD_STATUS_ENDPOINT_DESIGN.md §5.5:
        # "If app.state.woodies_system is None → running=false, hydrated=false"
        system.running = False
        system.hydrated = False
        for pid in WOODIES_PATTERN_IDS:
            system.patterns.append(PatternStatus(
                id=pid,
                name=_PATTERN_NAMES.get(pid, pid),
                status="unknown",
                label="❓ Unknown",
                reason="WoodiesSystem not initialized",
            ))
        return system

    # Read state via get_current() — returns dict(self.current_state)
    state = woodies_system.get_current()
    system.running = state.get("running", False)
    system.hydrated = state.get("hydrated", False)
    system.mode = None  # Woodies has no mode field per woodies_system.py

    # Data freshness: latest non-future Woodies bar.
    #
    # ROOT CAUSE OF THE -2,291,025,250s (~-72y) LAG BUG:
    #   `v9_bars_5min_woodies` has sentinel rows with ts="2099-01-02 04:00:00"
    #   (placeholder writes from a stalled bridge stream). The old query
    #   `SELECT MAX(ts) FROM v9_bars_5min_woodies` lex-sorts text, so those
    #   sentinel "2099-..." strings beat every real ISO ts → bar_dt is a
    #   datetime in 2099 → (now - bar_dt) ≈ -72 years.
    # FIX (inspector only — no underlying table mutation):
    #   `latest_valid_db_ts` scans the latest 50 rows ordered DESC and
    #   picks the first one whose ts parses to a non-future moment.
    last_bar_ts = None
    lag_seconds = None
    fires_dict: dict = {}
    try:
        last_bar_ts, _, lag_seconds = latest_valid_db_ts(
            "v9_bars_5min_woodies"
        )
        # Authoritative "fired today" surface — read v9_trades, NOT the
        # momentary in-memory active_patterns. See module-level note on
        # the frozen-tail bug: 1s after a fire active_patterns=[] and the
        # old inspector reverted the row to status="armed".
        fires_dict = fires_today(_FIRING_SYSTEM_WOODIES)
    except Exception as e:
        logger.warning("[BuildStatus/Woodies] DB read for freshness failed: %s", e)

    # Fresh if DB bar is recent OR the in-memory system is running with live CCI
    fresh = lag_seconds is not None and lag_seconds < 660
    if not fresh and woodies_system is not None:
        try:
            _live_state = woodies_system.current_state if hasattr(woodies_system, 'current_state') else {}
            if isinstance(_live_state, dict) and _live_state.get("cci_14") is not None:
                fresh = True  # System is processing bars in-memory even if DB write lags
        except Exception:
            pass
    system.data_freshness = DataFreshness(
        last_bar_ts=last_bar_ts,
        lag_seconds=round(lag_seconds, 1) if lag_seconds is not None else None,
        fresh=fresh,
        threshold_seconds=660,
    )

    # Extract key state fields from WoodiesSystem.current_state
    # Fields per woodies_system.py lines 54-75 (verified against source)
    cci_14 = state.get("cci_14")
    tcci = state.get("cci_6_tcci")
    trend_state = state.get("trend_state", "GRAY")

    # I-15 fix: if in-memory state is still at default GRAY (no bars processed),
    # fall back to the latest DB row's trend_state so the board doesn't show a
    # stale GRAY that contradicts /woodies/current (which updates after DB replay).
    if trend_state == "GRAY" and not state.get("bar_count"):
        try:
            _db_row = read_one(
                "SELECT trend_state FROM v9_bars_5min_woodies ORDER BY ts DESC LIMIT 1"
            )
            if _db_row and _db_row.get("trend_state"):
                _db_ts = str(_db_row["trend_state"]).upper()
                if _db_ts in ("BLUE", "RED", "YELLOW", "GRAY"):
                    trend_state = _db_ts
                    logger.info("[BuildStatus/Woodies] I-15: fell back to DB trend_state=%s (in-memory not yet populated)", trend_state)
        except Exception:
            pass  # DB fallback is best-effort
    active_patterns_raw = state.get("active_patterns", [])
    ready_to_route = state.get("ready_to_route", False)
    decision_tree = state.get("decision_tree", {})

    # D-OBS: Populate live inputs from WoodiesSystem state
    from .types import LiveInput, Interpretation
    def _fmt(v, fmt=".2f"):
        return f"{v:{fmt}}" if v is not None else "—"
    system.live_inputs = [
        LiveInput(field="cci_14", value=_fmt(cci_14), source="chart12/study4"),
        LiveInput(field="cci_6_tcci", value=_fmt(tcci), source="chart12/study10"),
        LiveInput(field="trend_state", value=str(trend_state), source="chart12/woodies"),
        LiveInput(field="swi_value", value=_fmt(state.get('swi_value'), ".1f"), source="chart12/study6"),
        LiveInput(field="czi_value", value=_fmt(state.get('czi_value'), ".1f"), source="chart12/study7"),
        LiveInput(field="ema_34", value=_fmt(state.get('ema_34')), source="chart12/study3"),
        LiveInput(field="lsma_value", value=_fmt(state.get('lsma_value')), source="chart12/study2"),
        LiveInput(field="predictor_next_cci", value=_fmt(state.get('predictor_next_cci'), ".1f"), source="chart12/study11"),
    ]
    # D-OBS: Interpretations
    _trend_meaning = {"BLUE": "uptrend (continuation LONG)", "RED": "downtrend (continuation SHORT)",
                      "GRAY": "no trend (WSI: wait)", "YELLOW": "transition (WSI: wait)"}
    _cci_zone = "extreme" if abs(cci_14 or 0) > 100 else "near_ZL" if abs(cci_14 or 0) < 30 else "trending"
    system.interpretations = [
        Interpretation(key="trend_direction", value=_trend_meaning.get(trend_state, "unknown"), from_input="trend_state"),
        Interpretation(key="cci_zone", value=f"{_cci_zone} (CCI={cci_14:.0f})" if cci_14 is not None else "—", from_input="cci_14"),
        Interpretation(key="active_patterns", value=f"{len(active_patterns_raw)} detected" if active_patterns_raw else "none", from_input="pattern_engine"),
        Interpretation(key="ready_to_route", value=str(ready_to_route), from_input="decision_tree"),
    ]

    # RTH gate: is the system configured for RTH-only AND are we currently in RTH?
    _rth_only = getattr(woodies_system, "_rth_only", True)
    try:
        from zoneinfo import ZoneInfo
        _et_now = datetime.now(ZoneInfo("America/New_York"))
        _in_rth = _time(9, 30) <= _et_now.time() < _time(16, 0)
    except Exception:
        _in_rth = False
    rth_gate_ok = (not _rth_only) or _in_rth  # passes if RTH-only is disabled OR we're in RTH

    # Day type context: read today's day_type from DB for Woodies matrix display
    _woodies_day_type = None
    try:
        _wrow = read_scalar(
            "SELECT day_type FROM v9_day_type_history WHERE date = :date LIMIT 1",
            {"date": et_today().isoformat()},
        )
        _woodies_day_type = _wrow
    except Exception:
        pass
    _dt_known = _woodies_day_type not in (None, "UNKNOWN")

    cci_present = cci_14 is not None
    tcci_present = tcci is not None

    # Build set of active engine pattern_ids for fast lookup
    active_engine_ids = set()
    for ap in active_patterns_raw:
        if isinstance(ap, dict):
            pid = ap.get("pattern_id")
        else:
            pid = getattr(ap, "pattern_id", None)
        if pid:
            active_engine_ids.add(str(pid).upper())

    # Stage A1: strategic gate — BLUE/RED required for any trade
    # Source: MEMS26_WOODIES_DECISION_TREE_V1.md §4 Stage A1
    # "IF cci_14 > 0 for 6+ consecutive bars → color = BLUE → LONG allowed"
    # "IF cci_14 < 0 for 6+ consecutive bars → color = RED → SHORT allowed"
    # "GREY/YELLOW → stand aside"
    trend_ok = trend_state in _TRADING_TREND_STATES

    # Pre-compute per-row freshness anchors.
    # `bar_fresh`   — DB-derived recency.
    # `state_fresh` — in-memory WoodiesSystem state (drives CCI / patterns);
    #                 anchored at the same bar ts.
    # `eval_fresh`  — inspector wall-clock for rows synthesized here
    #                 (rth_gate, day_type_gate from a separate DB row).
    bar_fresh = (
        make_freshness(last_bar_ts, "db") if last_bar_ts else freshness_now("db")
    )
    state_fresh = (
        make_freshness(last_bar_ts, "in_memory") if last_bar_ts else freshness_now("in_memory")
    )
    eval_fresh = freshness_now("inspector_eval")

    for pid in WOODIES_PATTERN_IDS:
        engine_id = _SPEC_ID_TO_ENGINE.get(pid, pid.upper())
        components = []

        # Stage: data — cci_14_present
        # Source: BUILD_STATUS_ENDPOINT_DESIGN.md §4.2 "state.cci_14 is not None"
        components.append(Component(
            stage="data",
            key="cci_14_present",
            spec="state.cci_14 is not None",
            present=cci_present,
            value=f"CCI14={cci_14:.2f}" if cci_14 is not None else "None",
            live=f"{cci_14:.2f}" if cci_14 is not None else "null",
            required="!= null",
            freshness=state_fresh,
        ))

        # Stage: data — tcci_present
        # Source: BUILD_STATUS_ENDPOINT_DESIGN.md §4.2 "state.get('tcci_value')"
        components.append(Component(
            stage="data",
            key="tcci_present",
            spec="state.cci_6_tcci is not None",
            present=tcci_present,
            value=f"TCCI={tcci:.2f}" if tcci is not None else "None",
            live=f"{tcci:.2f}" if tcci is not None else "null",
            required="!= null",
            freshness=state_fresh,
        ))

        # Stage: data — 5min bar recency
        components.append(Component(
            stage="data",
            key="5min_bar_recency",
            spec="max(ts) from v9_bars_5min_woodies within last 6 min",
            present=fresh,
            value=f"lag={round(lag_seconds, 0)}s" if lag_seconds is not None else "unknown",
            live=f"{round(lag_seconds, 1)}s" if lag_seconds is not None else "unknown",
            required="<= 360s",
            freshness=bar_fresh,
        ))

        # Stage: stage_a1 — strategic gate
        # Source: MEMS26_WOODIES_DECISION_TREE_V1.md §4 A1_strategic_gate
        components.append(Component(
            stage="stage_a1",
            key="strategic_gate",
            spec="trend_state in {BLUE, RED} (color veto from A1)",
            present=trend_ok,
            value=f"trend_state={trend_state}",
            live=str(trend_state),
            required="in {BLUE, RED}",
            freshness=state_fresh,
        ))

        # Stage: stage_a1 — RTH gate (F-17: bars only processed in RTH)
        _rth_live = (
            "in_rth" if _in_rth
            else ("pre_post_rth" if _rth_only else "rth_only=OFF")
        )
        components.append(Component(
            stage="stage_a1",
            key="rth_gate",
            spec="RTH filter active — 09:30–16:00 ET only",
            present=rth_gate_ok,
            value=(
                "in RTH" if _in_rth
                else ("pre/post RTH" if _rth_only else "rth_only=OFF")
            ),
            live=_rth_live,
            required="in_rth OR rth_only=OFF",
            freshness=eval_fresh,
        ))

        # Stage: stage_a1 — day_type_gate (Woodies matrix authorization)
        components.append(Component(
            stage="stage_a1",
            key="day_type_gate",
            spec="day_type classified (not UNKNOWN) for Woodies matrix",
            present=_dt_known,
            value=str(_woodies_day_type) if _woodies_day_type else "UNKNOWN",
            live=str(_woodies_day_type) if _woodies_day_type is not None else "null",
            required="not in {None, UNKNOWN}",
            freshness=freshness_now("db"),
        ))

        # Stage: detection — pattern_specific
        # Source: BUILD_STATUS_ENDPOINT_DESIGN.md §4.2 "check pattern.id in state.active_patterns"
        pattern_detected = engine_id in active_engine_ids
        components.append(Component(
            stage="detection",
            key="pattern_specific",
            spec=f"pattern_id={pid} in state.active_patterns",
            present=pattern_detected,
            value=f"active={pattern_detected} · engine_id={engine_id}",
            live=str(pattern_detected),
            required="== True",
            freshness=state_fresh,
        ))

        # Stage: targets_stop — r_t1, stop, targets from live PatternResult
        # Replaces the old confidence >= 0.5 proxy with the actual R:R gate.
        # Source: pattern detectors compute stop/r_t1/targets at detection time.
        best_conf = None
        _ap_stop = None
        _ap_r_t1 = None
        _ap_targets = None
        _ap_entry = None
        _ap_direction = None
        for ap in active_patterns_raw:
            if isinstance(ap, dict):
                apid = ap.get("pattern_id", "")
            else:
                apid = getattr(ap, "pattern_id", "")
            if str(apid).upper() == engine_id:
                if isinstance(ap, dict):
                    best_conf = ap.get("confidence")
                    _ap_stop = ap.get("stop")
                    _ap_r_t1 = ap.get("r_t1")
                    _ap_targets = ap.get("targets")
                    _ap_entry = ap.get("entry_price")
                    _ap_direction = ap.get("direction")
                else:
                    best_conf = getattr(ap, "confidence", None)
                    _ap_stop = getattr(ap, "stop", None)
                    _ap_r_t1 = getattr(ap, "r_t1", None)
                    _ap_targets = getattr(ap, "targets", None)
                    _ap_entry = getattr(ap, "entry_price", None)
                    _ap_direction = getattr(ap, "direction", None)
                break

        # R:R gate (replaces confidence >= 0.5 proxy)
        # pre_fire_validator enforces R:R >= 1.0; r_t1 from pattern detector
        _min_r_t1 = 1.0  # pre_fire_validator threshold
        _r_t1_ok = _ap_r_t1 is not None and float(_ap_r_t1) >= _min_r_t1
        if pattern_detected and _ap_r_t1 is None:
            _rr_value = "awaiting backend"
            _rr_live = "null"
        elif _ap_r_t1 is not None:
            _rr_value = f"r_t1={float(_ap_r_t1):.2f} {'≥' if _r_t1_ok else '<'} {_min_r_t1}"
            _rr_live = f"{float(_ap_r_t1):.4f}"
        else:
            _rr_value = "not active"
            _rr_live = "null"
        components.append(Component(
            stage="targets_stop",
            key="r_t1_gate",
            spec=f"r_t1 >= {_min_r_t1} (pre_fire R:R gate)",
            present=_r_t1_ok,
            value=_rr_value,
            live=_rr_live,
            required=f">= {_min_r_t1}",
            freshness=state_fresh,
        ))

        # Stop price
        _stop_val = f"{float(_ap_stop):.2f}" if _ap_stop is not None else "—"
        components.append(Component(
            stage="targets_stop",
            key="stop_price",
            spec="pattern.stop (ATR-based per family)",
            present=_ap_stop is not None,
            value=f"stop={_stop_val}" + (f" · entry={float(_ap_entry):.2f}" if _ap_entry else ""),
            live=_stop_val,
            required="!= null",
            freshness=state_fresh,
        ))

        # Targets (t1/t2 from pattern, fixed ticks per pattern type)
        _tgt_str = "—"
        if _ap_targets and isinstance(_ap_targets, (list, tuple)) and len(_ap_targets) >= 1:
            _tgt_str = " / ".join(f"{float(t):.2f}" for t in _ap_targets if t is not None)
        components.append(Component(
            stage="targets_stop",
            key="targets",
            spec="pattern.targets (t1/t2 per pattern tick table)",
            present=_ap_targets is not None and len(_ap_targets or []) >= 1,
            value=f"targets=[{_tgt_str}]",
            live=_tgt_str,
            required=">= 1 target",
            freshness=state_fresh,
        ))

        # Day-Type Matrix verdict for S4 (✅/⚠️/❌)
        _dt_verdict = "—"
        _dt_verdict_ok = False
        if _woodies_day_type and _woodies_day_type != "UNKNOWN" and pattern_detected:
            try:
                from backend.v9.systems.build_status.auth_table_lookup import lookup_auth_cell, is_skip
                _cell = lookup_auth_cell(pid, _woodies_day_type)
                _dt_verdict = _cell[0]  # verdict string (GO/SKIP/etc.)
                _dt_verdict_ok = not is_skip(pid, _woodies_day_type)
            except (ValueError, Exception):
                _dt_verdict = "lookup error"
        elif not _dt_known:
            _dt_verdict = "day_type unknown"
        components.append(Component(
            stage="targets_stop",
            key="day_type_matrix",
            spec=f"auth_table[{pid}×{_woodies_day_type or '?'}] verdict",
            present=_dt_verdict_ok or _dt_verdict == "—",
            value=f"{_dt_verdict} ({_woodies_day_type})" if _woodies_day_type else _dt_verdict,
            live=_dt_verdict,
            required="allowed",
            freshness=eval_fresh,
        ))

        # Stage: exit_rules — ready_to_route
        # Source: BUILD_STATUS_ENDPOINT_DESIGN.md §4.2 "state.ready_to_route"
        route_present = ready_to_route and pattern_detected
        components.append(Component(
            stage="exit_rules",
            key="ready_to_route",
            spec="state.ready_to_route == True and pattern active",
            present=route_present,
            value="✅" if route_present else "not ready",
            live=f"ready_to_route={ready_to_route}, active={pattern_detected}",
            required="ready_to_route == True AND active == True",
            freshness=state_fresh,
        ))

        # History wins over momentary state: a fire from v9_trades earlier
        # today is the authoritative "fired today" signal even if
        # active_patterns has since cleared (the frozen-tail bug repro).
        fire_entry = fires_dict.get(engine_id)
        fired_today = fire_entry is not None
        last_fire_str = fire_entry["last_ts"] if fire_entry else None
        currently_firing = pattern_detected and route_present

        # Determine status
        blockers = [f"{c.stage}.{c.key}" for c in components if not c.present]

        if not cci_present:
            status = "unknown"
            label = "❓ Unknown"
            reason = "CCI-14 not computed — insufficient bar history"
        elif fired_today and currently_firing:
            status = "fired"
            label = "🟢 Firing now"
            reason = (
                f"{pid} firing now · fired_today=True · "
                f"last_fire_ts={last_fire_str}"
            )
        elif fired_today:
            status = "fired"
            label = "✅ Fired today"
            reason = (
                f"{pid} fired earlier today at {last_fire_str} "
                f"(v9_trades, firing_system=4) · count={fire_entry['count']}"
            )
        elif not trend_ok:
            # MEMS26_WOODIES_DECISION_TREE_V1.md §4 A1: GREY/YELLOW = stand aside
            status = "blocked"
            label = "❌ Blocked"
            reason = (
                f"Stage A1 veto: trend_state={trend_state} "
                "(GREY/YELLOW/INDETERMINATE — Woodies WSI rule)"
            )
        elif currently_firing:
            # Race window: pattern emitting now but v9_trades insert not yet
            # visible to this RO connection. Surface as firing immediately.
            status = "fired"
            label = "🟢 Firing now"
            reason = (
                f"{pid} detected · ready_to_route=True · "
                f"conf={best_conf:.3f}" if best_conf is not None else f"{pid} ready"
            )
        elif pattern_detected:
            status = "armed"
            label = "🟡 Armed"
            reason = f"{pid} pattern detected · awaiting decision tree approval"
        elif fresh and trend_ok and cci_present:
            status = "armed"
            label = "🟡 Armed"
            reason = f"Data ready, trend {trend_state} · {pid} not yet detected"
        else:
            status = "blocked"
            label = "❌ Blocked"
            reason = f"Missing: {', '.join(blockers)}" if blockers else "Insufficient data"

        system.patterns.append(PatternStatus(
            id=pid,
            name=_PATTERN_NAMES.get(pid, pid),
            status=status,
            label=label,
            reason=reason,
            fired_today=fired_today,
            last_fire_ts=last_fire_str,
            components=components,
            blockers=blockers,
        ))

    # System-level aggregation: sum per-pattern counts, max per-pattern ts.
    # Driven by the SAME fires_dict so the system header can never disagree
    # with the per-pattern roll-up.
    system.fired_today_count = sum(v["count"] for v in fires_dict.values())
    last_ts_candidates = [v["last_ts"] for v in fires_dict.values() if v.get("last_ts")]
    system.last_fire_ts = max(last_ts_candidates) if last_ts_candidates else None

    return system
