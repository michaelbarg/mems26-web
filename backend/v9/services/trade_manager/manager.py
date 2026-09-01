"""W11 Trade Manager — trade lifecycle: entry -> bracket -> exit.

NOT a decision maker. Receives setup objects from firing systems,
manages state transitions, emits events. Each firing system makes
its own entry decision independently.

PnL calculation: per-contract (c1/c2/c3 independently), NOT 3x.
MES tick = $1.25 per tick per contract.

Pipeline 5 Phase 2: in DEMO mode, manager actions emit Sierra commands
(MODIFY_STOP, MODIFY_TARGET, EXIT) so the SAME dynamic strategy drives
the real Sierra position.
"""

import logging
import os
import time as _time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from backend.v9.services.market_clock import now_utc as _market_now_utc

from backend.v9.db.models.trades import V9Trade
from backend.v9.db.models.trade_log import V9TradeManagementLog
from backend.v9.services.trade_manager.state_machine import (
    InvalidTransition,
    TradeState,
    TradeStateMachine,
)

# Legacy gateway / cockpit rows use state="OPEN" (not in TradeState enum).
_ACTIVE_TRADE_STATES = frozenset({
    TradeState.PENDING.value,
    TradeState.FILLED.value,
    TradeState.PARTIAL.value,
    "OPEN",
})


def _coerce_trade_state(raw: Optional[str]) -> TradeState:
    """Map DB state strings to TradeStateMachine values."""
    if not raw:
        return TradeState.PENDING
    if raw == "OPEN":
        return TradeState.FILLED
    try:
        return TradeState(raw)
    except ValueError:
        logger.warning(
            "[TradeManager] unknown trade.state=%r — treating as FILLED for transitions",
            raw,
        )
        return TradeState.FILLED
from backend.v9.services.trade_manager.events import TradeEventEmitter
from backend.v9.services.snapshot_service.snapshot import CrossSystemSnapshotService

logger = logging.getLogger(__name__)

# MES futures: $1.25 per tick (0.25 point = 1 tick)
MES_TICK_VALUE = 1.25
MES_TICK_SIZE = 0.25
MES_POINT_VALUE = MES_TICK_VALUE / MES_TICK_SIZE  # $5 per point


def trade_contract_count(trade) -> int:
    """L7 (2026-07-08): the contract count for a trade — quality["contracts"]
    (persisted at accept from effective_contracts), else the FIXED_CONTRACTS_2/_3
    env (covers trades created before the count was persisted), else legacy 3.
    Shared by manager PnL/close logic and the /trades API display."""
    q = trade.quality if isinstance(getattr(trade, "quality", None), dict) else {}
    try:
        n = int(q.get("contracts") or 0)
    except (TypeError, ValueError):
        n = 0
    # T3/T8 (2026-08-15): the whitelist stopped at 4, so a 6-contract trade
    # (Michael's 15.08 ruling) fell through to the env branches and booked 4 or
    # 3 legs — the same class of silent under-count that hid 25% of every
    # 4-contract P&L. Any positive persisted count is the truth.
    if n >= 1:
        return n
    # One resolver (2026-08-17) — this ladder was missing FIXED_CONTRACTS_5
    # entirely, so a 5-contract trade with no persisted count would have booked
    # 3 legs. Same class as the [:3] truncation, one level up.
    from backend.v9.services.contract_size import ruled_contracts as _ruled
    return _ruled() or 3


def _zlr_mgmt_enabled() -> bool:
    """ZLR_MGMT_V1 (Michael 2026-07-14) — default OFF, code default (no env var
    needed). When unset every ZLR management path is byte-identical to today."""
    return os.environ.get("ZLR_MGMT_V1", "0").strip().lower() in ("1", "true", "yes")


def _position_ref_price_enabled() -> bool:
    """T-155 killswitch (cowork 30.08): default ON (preserves T-43 behavior).
    Set POSITION_REF_PRICE_V1=0 to revert to per-trade entry_price."""
    return os.environ.get("POSITION_REF_PRICE_V1", "1").lower() not in ("0", "false", "no", "off")


def _position_reference_price(trade, db_session) -> float:
    """T-43 (Michael 28.08 19:30): when Sierra manages a net position with an
    averaged entry, the reference price for stop management must be the broker's
    avg_price — NOT the individual trade.entry_price.

    Sierra averages automatically when >1 trade is open on the same side.
    The TM tracks separate trades (parent + SCALE_IN child), each with its own
    entry_price. Stops computed from the individual entry sit at the wrong level
    relative to the real averaged position.

    Logic:
      1. Count same-direction live trades in TM.
      2. If only one → trade.entry_price is the correct reference (no averaging).
      3. If >1 → read sierra_state.json avg_price (the broker's truth).
      4. If avg_price unavailable (stale/weekend) → weighted average of TM entries
         as a local approximation (honest fallback, not synthetic truth).
    """
    entry = float(trade.entry_price)
    # T-155: killswitch — OFF reverts to per-trade entry_price
    if not _position_ref_price_enabled():
        return entry
    direction = (getattr(trade, "direction", "") or "").upper()
    if direction not in ("LONG", "SHORT"):
        return entry

    # Count same-direction live trades
    try:
        same_dir_trades = db_session.query(V9Trade).filter(
            V9Trade.state.in_(_ACTIVE_TRADE_STATES),
            V9Trade.direction == direction,
            V9Trade.mode.in_(("live", "demo")),
        ).all()
    except Exception:
        return entry  # fail-safe: single-trade behavior

    if len(same_dir_trades) <= 1:
        return entry  # single trade — no averaging

    # Multiple same-direction trades: Sierra is averaging. Use broker's avg.
    from backend.v9.services.sierra_position_reconciler import _sierra_state_avg_price
    sierra_avg = _sierra_state_avg_price()
    if sierra_avg is not None:
        logger.info(
            "[TradeManager] T-43 position ref: %d same-dir %s trades → "
            "sierra.avg_price=%.2f (trade.entry=%.2f)",
            len(same_dir_trades), direction, sierra_avg, entry)
        return sierra_avg

    # Fallback: weighted average of TM entries (Rule 1 — honest approximation)
    total_contracts = 0
    weighted_sum = 0.0
    for t in same_dir_trades:
        ep = getattr(t, "entry_price", None)
        if ep is None:
            continue
        nc = trade_contract_count(t)
        weighted_sum += float(ep) * nc
        total_contracts += nc
    if total_contracts > 0:
        approx_avg = weighted_sum / total_contracts
        logger.warning(
            "[TradeManager] T-43 position ref: sierra.avg stale — using "
            "TM weighted avg=%.2f (%d contracts, %d trades)",
            approx_avg, total_contracts, len(same_dir_trades))
        return approx_avg

    return entry  # absolute fallback


def is_zlr_trade(trade) -> bool:
    """True for a System-4 (woodies) ZLR trade.

    accept_setup persists the fire's pattern id into quality.pattern_name /
    trigger / classification == "ZLR" (woodies_system stamps classification =
    metadata.pattern = pattern_id = "ZLR"). No other system uses the "ZLR" id, so
    a case-insensitive string match is unambiguous and keeps the change ZLR-scoped.
    """
    q = trade.quality if isinstance(getattr(trade, "quality", None), dict) else {}
    for _v in (q.get("pattern_name"), q.get("trigger"), q.get("classification")):
        if isinstance(_v, str) and _v.strip().upper() == "ZLR":
            return True
    meta = q.get("metadata") if isinstance(q.get("metadata"), dict) else {}
    _mp = meta.get("pattern")
    return isinstance(_mp, str) and _mp.strip().upper() == "ZLR"


class TradeManager:
    """Manages the full lifecycle of V9 trades.

    Responsibilities:
    - Accept setups from firing systems (no filtering)
    - Track state transitions via TradeStateMachine
    - Record target hits and stop hits
    - Calculate PnL per-contract
    - Emit events on every state change
    - Persist all changes to DB
    """

    def __init__(
        self,
        db: Session,
        event_emitter: Optional[TradeEventEmitter] = None,
        snapshot_service: Optional[CrossSystemSnapshotService] = None,
    ):
        self._db = db
        self._emitter = event_emitter or TradeEventEmitter()
        self._snapshot = snapshot_service
        # Active state machines keyed by trade_id — bounded by active trades
        self._machines: Dict[int, TradeStateMachine] = {}
        self._fill_locks: set = set()  # Pkg 3b-2 · Sierra fill lock (LOCK 3)
        # L2-residual (2026-07-08): rate-limit state for skipped-emit warnings
        self._emit_skip_warned: Dict[tuple, float] = {}

    def _log_management(self, trade_id: int, action: str, value: Optional[Dict] = None) -> None:
        """Write to V9TradeManagementLog — observability for trades page timeline."""
        try:
            self._db.add(V9TradeManagementLog(
                trade_id=trade_id,
                ts=datetime.now(timezone.utc),
                action=action,
                value=value,
            ))
        except Exception as e:
            logger.debug("[TradeManager] management_log write failed: %s", e)

    def _is_demo_mode(self, trade) -> bool:
        """Check if a trade should emit Sierra commands (DEMO or LIVE, not SHADOW)."""
        trade_mode = getattr(trade, "mode", "shadow")
        if trade_mode == "live":
            return os.environ.get(
                "LIVE_EXECUTION_V1", "0").lower() in ("1", "true", "yes")
        if trade_mode == "demo":
            return os.environ.get(
                "DEMO_EXECUTION_ENABLED", "0").lower() in ("1", "true", "yes")
        return False

    def _get_sierra_order_id(self, trade) -> Optional[int]:
        """Get the Sierra order ID stored on the trade (from PLACE ACK)."""
        q = trade.quality if isinstance(trade.quality, dict) else {}
        oid = q.get("sierra_order_id")
        return int(oid) if oid is not None else None

    _EMIT_SKIP_WARN_SECS = 60.0

    def _warn_emit_skipped(self, trade, op: str, reason: str) -> None:
        """No-silent-failures (L2-residual, 2026-07-08): a skipped Sierra emit used
        to `return` silently → the DB recorded stop-moves Sierra never saw
        (records ≠ reality, live trade 299). Warn, rate-limited per
        trade+op+reason. Shadow trades never reach here — skipping them is
        by-design, not a failure."""
        import time as _time
        key = (getattr(trade, "id", None), op, reason)
        now = _time.monotonic()
        cache = getattr(self, "_emit_skip_warned", None)
        if cache is None:  # instances built without full __init__ (tests, pickling)
            cache = self._emit_skip_warned = {}
        if now - cache.get(key, -1e9) >= self._EMIT_SKIP_WARN_SECS:
            cache[key] = now
            logger.warning(
                "[TradeManager] %s SKIPPED for trade %s (mode=%s): %s — Sierra will "
                "NOT see this change",
                op, getattr(trade, "id", "?"), getattr(trade, "mode", "?"), reason)

    def _emit_drop_target(self, trade, target_field: str) -> bool:
        """N4 (2026-07-17, System6 rescue tier): apply a DROP_TARGET correction.

        System6's diagnose_trade already emits this AUTO correction for a
        wrong-side t1/t2/t3 (I-61) and SYSTEM6_AUTOCORRECT=protective already
        covers it doctrinally (CLAUDE.md: "protective... emits only MODIFY_STOP
        + advisory DROP_TARGET (not wired)") — bar_level_detector.py's `_exec`
        just had no case for it, so it silently fell through to the generic
        "needs manual handling" warning and nothing happened. This is a
        backend-only DB correction (null the bad target field) — no new
        Sierra op is invented; T1/T2/T3 hit-detection and the UI read this
        field directly, so nulling it here is enough to stop the system
        treating a wrong-side level as live. Never touches Sierra.
        """
        if target_field not in ("t1", "t2", "t3"):
            logger.warning("[TradeManager] DROP_TARGET ignored: unknown field %r", target_field)
            return False
        try:
            setattr(trade, target_field, None)
            self._db.commit()
            logger.warning("[TradeManager] DROP_TARGET applied: trade %s %s -> None",
                            getattr(trade, "id", "?"), target_field)
            return True
        except Exception as e:
            logger.warning("[TradeManager] DROP_TARGET failed for trade %s %s: %s",
                            getattr(trade, "id", "?"), target_field, e)
            try:
                self._db.rollback()
            except Exception:
                pass
            return False

    def _emit_modify_stop(self, trade, new_stop: float) -> None:
        """Emit a MODIFY_STOP command to Sierra (DEMO + LIVE)."""
        if not self._is_demo_mode(trade):
            if getattr(trade, "mode", "shadow") in ("demo", "live"):
                self._warn_emit_skipped(trade, "MODIFY_STOP",
                                        "execution flag OFF for this mode")
            return
        oid = self._get_sierra_order_id(trade)
        if oid is None:
            self._warn_emit_skipped(trade, "MODIFY_STOP",
                                    "no sierra_order_id on trade (order-id map missing)")
            return
        # Collect per-contract stop IDs from quality JSON so the DLL doesn't
        # depend on persistent slots (Pipeline 5 may clear them).
        q = trade.quality if isinstance(trade.quality, dict) else {}
        stop_ids = []
        for key in ("c1_stop_id", "c2_stop_id", "c3_stop_id", "c4_stop_id"):
            sid = q.get(key)
            if sid is not None:
                stop_ids.append(int(sid))
        # T2 IDEMPOTENCY (2026-08-15). This emitter sent the command but never
        # wrote the new stop back to the trade, so System 6's `stop_not_at_be`
        # invariant kept seeing the OLD stop and re-fired on every bar:
        # 393 identical MODIFY_STOP commands for trade 657 in one session, and
        # 110 command files expired in the queue without ever being sent — a
        # clogged wire that can swallow the FLATTEN queued behind it.
        # Two guards: an in-memory recent-emit window (survives a DB failure)
        # and the DB write-back (survives a restart).
        _dedup_key = (int(trade.id), round(float(new_stop), 2))
        _now = _time.time()
        _recent = getattr(self, "_recent_stop_emits", None)
        if _recent is None:
            _recent = self._recent_stop_emits = {}
        for _k, _ts in list(_recent.items()):
            if _now - _ts > 300.0:
                _recent.pop(_k, None)
        if _now - _recent.get(_dedup_key, 0.0) < 60.0:
            logger.debug("[TradeManager] MODIFY_STOP suppressed (identical within 60s): "
                         "trade %s stop %.2f", trade.id, new_stop)
            return
        try:
            from backend.v9.services.sierra_command import write_modify_stop
            write_modify_stop(
                trade_id=str(trade.id), order_id=oid, new_stop=new_stop,
                stop_ids=stop_ids or None,
            )
            _recent[_dedup_key] = _now
        except Exception as e:
            logger.warning("[TradeManager] Sierra MODIFY_STOP failed: %s", e)
            return
        # Write-back: the books must reflect the stop we just asked for, or the
        # invariant re-fires forever. A DB failure here is rolled back so the
        # shared session is not left ABORTED (that poisoning is what silently
        # killed every later write on mac-2).
        try:
            trade.stop = float(new_stop)
            self._db.commit()
        except Exception as _wb_err:
            try:
                self._db.rollback()
            except Exception:
                pass
            logger.warning("[TradeManager] MODIFY_STOP write-back failed (rolled back): %s",
                           _wb_err)

    def _emit_modify_target(self, trade, new_target: float, target_order_id: Optional[int] = None) -> None:
        """Emit a MODIFY_TARGET command to Sierra (DEMO + LIVE).
        If target_order_id is given, modifies that specific target (per-runner).
        Otherwise uses the trade's sierra_order_id (legacy/fallback).
        """
        if not self._is_demo_mode(trade):
            if getattr(trade, "mode", "shadow") in ("demo", "live"):
                self._warn_emit_skipped(trade, "MODIFY_TARGET",
                                        "execution flag OFF for this mode")
            return
        oid = target_order_id or self._get_sierra_order_id(trade)
        if oid is None:
            self._warn_emit_skipped(trade, "MODIFY_TARGET",
                                    "no sierra_order_id on trade (order-id map missing)")
            return
        try:
            from backend.v9.services.sierra_command import write_modify_target
            write_modify_target(trade_id=str(trade.id), order_id=oid, new_target=new_target)
        except Exception as e:
            logger.warning("[TradeManager] Sierra MODIFY_TARGET failed: %s", e)

    def set_sierra_order_ids(self, trade_id: int, ids: dict) -> None:
        """Store Sierra order IDs on the trade (from ENTRY fill).

        Keys: sierra_order_id, c1_target_id, c1_stop_id,
              c2_target_id, c2_stop_id, c3_target_id, c3_stop_id.
        """
        trade = self._get_trade(trade_id)
        if trade is None:
            return
        q = dict(trade.quality) if isinstance(trade.quality, dict) else {}
        for k, v in ids.items():
            if v is not None and v != 0:
                q[k] = v
        trade.quality = q
        self._db.flush()
        logger.info("[TradeManager] Sierra IDs stored on trade %d: %s",
                     trade_id, {k: v for k, v in ids.items() if v})

    def _emit_exit(self, trade, contracts: int) -> None:
        """Emit an EXIT command to Sierra (DEMO mode only)."""
        if not self._is_demo_mode(trade):
            if getattr(trade, "mode", "shadow") in ("demo", "live"):
                self._warn_emit_skipped(trade, "EXIT",
                                        "execution flag OFF for this mode")
            return
        oid = self._get_sierra_order_id(trade)
        if oid is None:
            self._warn_emit_skipped(trade, "EXIT",
                                    "no sierra_order_id on trade (order-id map missing)")
            return
        try:
            from backend.v9.services.sierra_command import write_exit
            write_exit(trade_id=str(trade.id), order_id=oid, contracts=contracts)
        except Exception as e:
            logger.warning("[TradeManager] Sierra EXIT failed: %s", e)

    def accept_setup(
        self,
        setup: Dict[str, Any],
        mode: str,
    ) -> int:
        """Create a V9Trade row from a setup object. Returns trade_id.

        Setup must contain: firing_system, direction, stop, t1, t2, t3.
        Optional: entry_price, entry_ts, cross_context.
        """
        if mode not in ("shadow", "demo", "live"):
            raise ValueError(f"Invalid mode: {mode}")

        # ROOT-FIX 2026-08-15 (mac-2 wrote ZERO trades for 28 days): this
        # session is shared with BarLevelDetector + FillPoller (main.py:1076).
        # Once any of them aborted the transaction without rolling back, every
        # later statement raised InFailedSqlTransaction — the fire passed all
        # gates, then died here, swallowed upstream. A trade write must never
        # inherit someone else's poisoned transaction.
        try:
            from backend.v9.db.session_guard import ensure_clean
            ensure_clean(self._db, where="accept_setup")
        except Exception:
            pass

        firing_system = setup["firing_system"]
        if firing_system not in (1, 2, 3, 4):
            raise ValueError(f"Invalid firing_system: {firing_system}")

        direction = setup["direction"]
        if direction not in ("LONG", "SHORT"):
            raise ValueError(f"Invalid direction: {direction}")

        meta = dict(setup.get("metadata")) if isinstance(setup.get("metadata"), dict) else {}
        if setup.get("stop") is not None:
            meta["stop_initial"] = float(setup["stop"])
        classification = setup.get("classification") or meta.get("pattern") or meta.get("signal")
        trigger = (
            setup.get("trigger")
            or classification
            or meta.get("pattern")
            or meta.get("signal")
            or f"system_{firing_system}"
        )
        # L7 (2026-07-08): persist the LIVE contract count on the trade — the same
        # number command_from_setup sends to Sierra. Without this the DB row had
        # no count at all → PnL/close/display all assumed 3 contracts.
        from backend.v9.services.sierra_command import effective_contracts
        _n_contracts = effective_contracts(setup)
        quality = {
            "classification": classification,
            "confidence": setup.get("confidence"),
            "metadata": meta,
            "trigger": trigger,
            "blocked_by": setup.get("blocked_by"),
            "contracts": _n_contracts,
        }
        # T-200a: entry_stop — the stop AT ENTRY, written once, never updated.
        # v9_trades.stop is overwritten 8 times by BE/trail/structure — it is
        # the FINAL stop, not the entry stop. quality.initial_stop is biased
        # (present on 55/117 live, correlated with wins). This field is the
        # immutable truth for risk measurement.
        _entry_stop = setup.get("stop")
        if _entry_stop is not None:
            try:
                quality["entry_stop"] = round(float(_entry_stop), 2)
            except (TypeError, ValueError):
                pass
        # T17 (BE_AFTER_REAL_T1_V1): persist T0 info so on_target_hit can remap
        # DLL T1→T0 (the scalp) and not fire BE prematurely. Same condition as
        # sierra_command.py:351 — 4+ contracts with T0_TARGET_PTS set.
        import os as _t0_os
        _t0p = float(_t0_os.getenv("T0_TARGET_PTS", "0") or 0)
        if _n_contracts >= 4 and _t0p > 0:
            quality["t0_target_pts"] = _t0p
            quality["has_t0"] = True
        # TARGET_MIN_SPACING_V1 (Michael 2026-08-21): the would-be ladder the
        # spacing rule computed for this fire, lifted to a top-level quality key
        # so a replay can read it without digging through metadata. SHADOW mode
        # writes it on every fire — including "no violation", which is evidence
        # too (COWORK_DAILY_READ §3.6).
        _ts_shadow = setup.get("target_spacing_shadow") or meta.get("target_spacing_shadow")
        if _ts_shadow:
            quality["target_spacing_shadow"] = _ts_shadow

        registry_ctx = setup.get("cross_context")
        systems_at_entry = registry_ctx if isinstance(registry_ctx, dict) else {}
        cross_ctx: list = [
            {
                "trigger": trigger,
                "classification": classification,
                "confidence": setup.get("confidence"),
                "metadata": meta,
                "systems": systems_at_entry,
            }
        ]
        if self._snapshot is not None:
            snapshot = self._snapshot.capture(
                "entry", firing_system_id=firing_system,
            )
            cross_ctx.append(snapshot)

        trade = V9Trade(
            mode=mode,
            firing_system=firing_system,
            direction=direction,
            state=TradeState.PENDING.value,
            entry_ts=setup.get("entry_ts"),
            entry_price=setup.get("entry_price"),
            stop=setup["stop"],
            t1=setup["t1"],
            t2=setup["t2"],
            t3=setup["t3"],
            cross_context=cross_ctx,
            quality=quality,
            # G1 promoted columns (from gateway's extract_g1_entry_context)
            day_type_at_entry=setup.get("day_type_at_entry"),
            pattern_id_at_entry=setup.get("pattern_id_at_entry"),
            session_at_entry=setup.get("session_at_entry"),
        )

        # D-094 §3.A · capture resolved trail config (overrides + base)
        _day_type = meta.get("day_type")
        _pattern = meta.get("pattern") or classification
        # Pkg 3b Stream 2 · always write keys (may be None for legacy trades)
        quality["day_type"] = _day_type
        quality["pattern_name"] = _pattern
        if _day_type and _pattern:
            try:
                from backend.v9.systems.day_type.targets_table import resolve_trail_config
                cfg = resolve_trail_config(_day_type, _pattern)
                quality["trail_after_t2"] = cfg.get("trail_after_t2", False)
                quality["t3_label"] = cfg.get("t3")
            except Exception:
                pass  # trail config resolution is advisory — do not block trade creation

        self._db.add(trade)
        self._db.flush()  # get the id

        self._machines[trade.id] = TradeStateMachine(TradeState.PENDING)

        self._emitter.emit("trade_created", trade.id, {
            "mode": mode,
            "firing_system": firing_system,
            "direction": direction,
            "state": TradeState.PENDING.value,
        })

        logger.info(
            "Trade %d created: mode=%s sys=%d dir=%s",
            trade.id, mode, firing_system, direction,
        )
        return trade.id

    def on_fill(self, trade_id: int, fill_price: float) -> None:
        """PENDING -> FILLED on entry fill."""
        trade = self._get_trade(trade_id)
        machine = self._get_machine(trade)

        machine.transition(TradeState.FILLED)
        trade.state = TradeState.FILLED.value
        trade.entry_price = fill_price
        trade.entry_ts = _market_now_utc()  # Prompt 26b: market time

        self._db.flush()

        # IDEA-2 (Michael 07-13): a REAL trade opening (not shadow) → phone push.
        try:
            if str(getattr(trade, "mode", "")) in ("live", "demo"):
                from backend.v9.services.phone_alert import push as _phone_push
                _phone_push(f"trade_open_{trade_id}", "📈 MEMS26: עסקה נפתחה",
                            f"#{trade_id} {getattr(trade, 'direction', '?')} @{fill_price} "
                            f"(mode={trade.mode}, stop={getattr(trade, 'stop', '?')})", priority=0)
        except Exception:
            pass

        self._emitter.emit("trade_filled", trade_id, {
            "fill_price": fill_price,
            "state": TradeState.FILLED.value,
        })

        # N12: one line per lifecycle event to the central OPS_LOG (never raises)
        try:
            from scripts.ops_log import log_event as _ops
            _ops("trade_manager", "INFO",
                 f"ENTRY-FILL #{trade_id} {getattr(trade, 'direction', '?')} "
                 f"@{fill_price} mode={getattr(trade, 'mode', '?')} "
                 f"stop={getattr(trade, 'stop', '?')}")
        except Exception:
            pass

    def on_target_hit(
        self,
        trade_id: int,
        target: str,
        fill_ts: Optional[datetime] = None,
        fill_price: Optional[float] = None,
        fill_qty: Optional[int] = None,
        order_id: Optional[int] = None,
    ) -> None:
        """Record a target hit (T1, T2, T3).

        Per-contract model (Pipeline 5 Phase 2-E):
          T1 = C1 scale-out (1 contract) → PARTIAL + stop→BE
          T2 = C2 scale-out (1 contract) → stay PARTIAL, keep trailing
          T3 = C3 scale-out (last contract) → CLOSED only if all 3 filled

        fill_price: the ACTUAL Sierra fill price from trade_fills.json.
        When provided, updates the target level to the real fill so PnL
        reflects actual execution, not the intended target level.
        fill_qty / order_id: T-62 — the contracts this leg took out and the
        Sierra order that filled it, so the leg is booked at its OWN price.
        """
        if target not in ("T1", "T2", "T3", "T4"):
            raise ValueError(f"Invalid target: {target}")

        trade = self._get_trade(trade_id)
        machine = self._get_machine(trade)
        hit_ts = fill_ts or _market_now_utc()
        n_contracts = trade_contract_count(trade)

        # T17 (Michael ruling 2026-07-20): 4-contract T0 remap.
        # The DLL always reports fills as T1/T2/T3/T4 (slot order). With
        # FIXED_CONTRACTS_4 + T0_TARGET_PTS, C1 is the T0 scalp — DLL calls
        # it "T1" but it's NOT the real T1. Remap: T1→T0, T2→T1, T3→T2, T4→T3.
        # Gate: flag BE_AFTER_REAL_T1_V1 + trade has 4 contracts + quality has t0.
        import os as _t17_os
        _be_t1_fix = _t17_os.getenv("BE_AFTER_REAL_T1_V1", "0").lower() in ("1", "true", "yes")
        _q = trade.quality if isinstance(getattr(trade, "quality", None), dict) else {}
        _has_t0 = bool(_q.get("t0_target_pts") or _q.get("has_t0"))
        if _be_t1_fix and n_contracts >= 4 and _has_t0:
            _remap = {"T1": "T0", "T2": "T1", "T3": "T2", "T4": "T3"}
            _orig = target
            target = _remap.get(target, target)
            if _orig != target:
                logger.info("[TM] T0-remap: DLL %s → logical %s (4c + T0)", _orig, target)

        # Overwrite target level with actual Sierra fill price when available.
        # This ensures _calculate_pnl uses the real execution price.
        if fill_price is not None:
            if target == "T1":
                trade.t1 = fill_price
            elif target == "T2":
                trade.t2 = fill_price
            elif target == "T3":
                trade.t3 = fill_price
            elif target == "T4":
                trade.t4 = fill_price
            # T-62 (2026-08-20): T0 has no t*/t*_hit_ts column of its own, so
            # before the fill ledger the T0 scale-out was INVISIBLE to
            # _calculate_pnl and its contract was booked at the trade's exit
            # fill instead. On #749 that alone cost $41.25 (a +3.25pt scalp
            # booked as a -5.00pt stop). Every leg — T0 included — is now
            # recorded with its own price.
            self._record_exit_fill(trade, target, fill_price, qty=fill_qty,
                                   order_id=order_id, ts=hit_ts)

        self._append_snapshot(trade, f"{target.lower()}_hit")

        # T0 scale-out (4-contract T0 ladder): PARTIAL, no BE
        if target == "T0":
            # P5.3 (2026-07-30): idempotent — a duplicate/late fill report when
            # already PARTIAL raised InvalidTransition PARTIAL→PARTIAL (spammed
            # bar_level_detector.on_bar all night 07-29 and would break booking
            # the NEXT target on a live trade). Same guard the T1 branch has.
            if machine.state != TradeState.PARTIAL:
                machine.transition(TradeState.PARTIAL)
            trade.state = TradeState.PARTIAL.value
            self._log_management(trade_id, "T0_HIT", {"ts": hit_ts.isoformat()})
            self._calculate_pnl(trade)
            # T-211 ROOT-FIX (2026-09-01): this branch `return`s BEFORE the
            # `self._db.flush()` that every other target branch falls through
            # to. `_record_exit_fill` above mutates `trade.quality` in the
            # identity map only; without a flush the T0 leg never reaches the
            # DB, and the NEXT fill (minutes later, after the session has been
            # refreshed) re-reads `quality` WITHOUT it and appends onto the
            # stale list — the leg is not "not recorded", it is OVERWRITTEN.
            # `_log_management` writes its own row, which is why `T0_HIT`
            # survives in v9_trade_management_log while the fill does not:
            # that asymmetry is the fingerprint of this bug.
            #   #942 2026-09-01: Sierra order 10845 T0 1c @7663.25 (entry
            #     7660.25) = +3.00pt. Lost -> booked at the stop (+0.25pt).
            #     Error $13.75.
            #   #948 2026-09-01: Sierra order 10857 T0 1c @7671.75 (entry
            #     7668.75) = +3.00pt. Lost -> booked at the stop (-7.50pt).
            #     Error $52.50, on a trade booked -$187.50 that was -$135.00.
            self._db.flush()
            # T0 is NEVER the last target — always at least T1/T2/T3 after
            return

        # L7 (2026-07-08): the LAST contract's target closes the trade — for a
        # 2-contract trade that is T2 (there IS no T3 order), for 1 contract T1.
        # Before this, only T3 closed → a 2c trade stayed PARTIAL forever after
        # its runner target filled (stuck slot + wrong open-trade accounting).

        if target == "T1":
            # C1 scale-out: FILLED → PARTIAL + stop→BE
            # After T0 remap (4-contract trades), state is already PARTIAL from
            # the T0 scale-out.  Skip the transition to avoid InvalidTransition.
            if machine.state != TradeState.PARTIAL:
                machine.transition(TradeState.PARTIAL)
            trade.state = TradeState.PARTIAL.value
            trade.t1_hit_ts = hit_ts
            self._log_management(trade_id, "T1_HIT", {"ts": hit_ts.isoformat()})
            self._apply_smart_be_after_t1(trade)
            self._calculate_pnl(trade)
            if n_contracts == 1:
                self._close_on_final_target(trade, machine, "T1_HIT", hit_ts)

        elif target == "T2":
            # C2 scale-out: for 3 contracts stay PARTIAL (T3 runner still on);
            # for 2 contracts T2 IS the last contract → close.
            trade.t2_hit_ts = hit_ts
            self._log_management(trade_id, "T2_HIT", {"ts": hit_ts.isoformat()})
            self._calculate_pnl(trade)
            if n_contracts <= 2 and trade.t1_hit_ts is not None:
                self._close_on_final_target(trade, machine, "T2_HIT", hit_ts)
            # else: T2 before T1 (unusual) → stay PARTIAL until T1 fills

        elif target == "T3":
            trade.t3_hit_ts = hit_ts
            self._log_management(trade_id, "T3_HIT", {"ts": hit_ts.isoformat()})
            self._calculate_pnl(trade)
            # Close ONLY if all contracts are out (T1+T2 already filled)
            # For 4-contract trades, T3 is not the last — T4 is.
            all_out = (trade.t1_hit_ts is not None and trade.t2_hit_ts is not None)
            if all_out and n_contracts <= 3:
                self._close_on_final_target(trade, machine, "T3_HIT", hit_ts)
            # else: T3 filled before T2 (unusual) or 4-contract trade → stay PARTIAL

        elif target == "T4":
            # C4 scale-out (Michael 07-15, 4 contracts): last runner.
            trade.t4_hit_ts = hit_ts
            self._log_management(trade_id, "T4_HIT", {"ts": hit_ts.isoformat()})
            self._calculate_pnl(trade)
            all_out = (trade.t1_hit_ts is not None and trade.t2_hit_ts is not None
                       and trade.t3_hit_ts is not None)
            if all_out:
                self._close_on_final_target(trade, machine, "T4_HIT", hit_ts)

        self._db.flush()

        self._emitter.emit(f"target_{target.lower()}_hit", trade_id, {
            "target": target,
            "ts": hit_ts.isoformat(),
            "state": trade.state,
        })

        # N12: central OPS_LOG line per target fill (never raises)
        try:
            from scripts.ops_log import log_event as _ops
            _ops("trade_manager", "INFO",
                 f"{target}-FILL #{trade_id} @{fill_price if fill_price is not None else 'target'} "
                 f"state={trade.state} pnl={getattr(trade, 'pnl', None)}")
        except Exception:
            pass

    def _close_on_final_target(self, trade, machine, exit_reason: str, hit_ts) -> None:
        """L7 (2026-07-08): close the trade when its LAST contract's target fills.
        Extracted from the T3 close block; now also reached by T2 (2 contracts)
        and T1 (1 contract)."""
        machine.transition(TradeState.CLOSED)
        trade.state = TradeState.CLOSED.value
        trade.exit_ts = hit_ts
        trade.exit_reason = exit_reason
        self._calculate_pnl(trade)
        self._set_outcome(trade)
        self._cleanup_machine(trade.id)

    def _initial_stop(self, trade: V9Trade) -> Optional[float]:
        """Risk denominator uses pre–smart-BE stop when stop was moved to entry."""
        q = trade.quality if isinstance(trade.quality, dict) else {}
        raw = q.get("initial_stop")
        if raw is not None:
            try:
                return float(raw)
            except (TypeError, ValueError):
                pass
        return self._valid_target(trade.stop)

    def _zlr_stop_locked(self, trade) -> bool:
        """ZLR_MGMT_V1 (Michael 2026-07-14, ZLR / System-4 ONLY): the ZLR stop is
        FIXED — it holds at the initial structural (5-min candle) stop until T1,
        then makes ONE move to entry (BE) at T1 (in _apply_smart_be_after_t1).
        Every OTHER per-bar stop-move — structure / dynamic / runner trail, the
        post-T2 lock, and the external trail-engine — is a no-op for a ZLR trade,
        so nothing trails the stop off structure before T1 (Michael: "אפס תזוזה
        לפני T1") or off BE after T1 (Michael: "אחרי T1→BE"). Non-ZLR trades and
        flag-OFF return False → byte-identical to today."""
        return _zlr_mgmt_enabled() and is_zlr_trade(trade)

    def _apply_smart_be_after_t1(self, trade: V9Trade) -> None:
        """Move stop to BE+1T after T1 hit · D-094 Gap 1 fix.

        OLD behavior: stop = entry (BE) — too tight, no slippage room.
        NEW behavior: stop = entry + 1T (LONG) or entry - 1T (SHORT) per Sheet C.

        T-43 (Michael 28.08 19:30): when >1 same-direction trade is open,
        the reference price is sierra.avg_price (the broker's net average),
        not the individual trade.entry_price. The broker manages one position;
        a BE stop must sit at the averaged entry, not a phantom per-trade entry
        that doesn't exist in the broker's books.

        Idempotent: if stop is ALREADY at BE+1T or tighter, no-op (Gap 13 'never widen').
        """
        from backend.v9.systems.five_min.constants import MES_TICK_SIZE
        if trade.entry_price is None:
            return
        direction = (trade.direction or "").upper()
        # T-43: use position reference price (avg when multiple trades)
        try:
            entry = _position_reference_price(trade, self._db)
        except Exception:
            entry = float(trade.entry_price)
        tick = MES_TICK_SIZE

        # Save initial stop before any move
        q = dict(trade.quality) if isinstance(trade.quality, dict) else {}
        if "initial_stop" not in q and trade.stop is not None:
            q["initial_stop"] = float(trade.stop)
            trade.quality = q

        stop_before = float(trade.stop) if trade.stop is not None else None

        # ZLR_MGMT_V1 (Michael 2026-07-14 — ZLR / System-4 ONLY): the lone T2-bound
        # runner's stop goes to PLAIN entry (BE) at T1 — never BE±1T and never the
        # STOP_STRUCTURE_TRAIL_V1 structure anchor. This overrides the structure-
        # trail for ZLR alone; idempotent (never widen). Flag-OFF / non-ZLR fall
        # through to the unchanged BE+1T / structure logic below.
        if _zlr_mgmt_enabled() and is_zlr_trade(trade):
            _cur = float(trade.stop) if trade.stop is not None else None
            if direction == "LONG":
                if _cur is not None and _cur >= entry:
                    logger.info("[TradeManager] ZLR BE skip (never widen): trade %s stop=%.2f already >= entry=%.2f",
                                getattr(trade, "id", "?"), _cur, entry)
                    return
            elif direction == "SHORT":
                if _cur is not None and _cur <= entry:
                    logger.info("[TradeManager] ZLR BE skip (never widen): trade %s stop=%.2f already <= entry=%.2f",
                                getattr(trade, "id", "?"), _cur, entry)
                    return
            else:
                logger.warning(
                    "[TradeManager] ZLR BE unknown direction=%s · trade_id=%s",
                    direction, getattr(trade, "id", "?"))
                return
            trade.stop = entry
            audit_entry = {
                "event": "stop_move",
                "from": stop_before,
                "to": float(trade.stop),
                "reason": "ZLR BE (entry) after T1",
            }
            ctx = list(trade.cross_context) if isinstance(trade.cross_context, list) else []
            ctx.append(audit_entry)
            trade.cross_context = ctx
            self._log_management(trade.id, "SMART_BE",
                                 {"from": stop_before, "to": float(trade.stop), "zlr": True})
            self._emit_modify_stop(trade, float(trade.stop))
            logger.info("[TradeManager] ZLR BE after T1: trade %s stop %s -> %.2f",
                        trade.id, stop_before, trade.stop)
            return

        # E2 (S6_TREND_BE_DELAY_V1, default OFF): on Trend days, skip the
        # immediate BE move after T1 — let the trailing stop handle it instead.
        # Measured cost: −$72.50 from trades where BE clipped a trend runner.
        # When ON and day_type is Trend_*: return without moving the stop.
        # The structural trail (STOP_PERBAR_STRUCT_V1) or the bar-level trail
        # will manage the stop on subsequent bars.
        if os.environ.get("S6_TREND_BE_DELAY_V1", "0").lower() in ("1", "true", "yes"):
            try:
                _dt_at_entry = (dict(trade.quality) if isinstance(trade.quality, dict) else {}).get(
                    "day_type_at_entry") or ""
                if not _dt_at_entry:
                    # Try from cross_context
                    _cc = trade.cross_context
                    if isinstance(_cc, dict):
                        _dt_at_entry = _cc.get("day_type_at_entry", "")
                if str(_dt_at_entry).startswith("Trend"):
                    logger.info(
                        "[TradeManager] E2 S6_TREND_BE_DELAY: skipping BE move on %s "
                        "(Trend day — trailing stop will manage) trade=%s",
                        _dt_at_entry, getattr(trade, "id", "?"))
                    return
            except Exception:
                pass  # fail-open: proceed with normal BE

        # STOP_STRUCTURE_TRAIL_V1 (Michael ruling 2026-07-08, flag-OFF): after T1
        # the stop goes to the nearest STRUCTURE, not mechanically to BE — "לקרב
        # לכניסה אבל לשים באזור המבנה כדי לא לפספס הרחבה". BE+1T gets wicked by
        # noise; a structural anchor gives the runner room for the expansion.
        # Never widens (Gap 13); falls back to BE+1T when structure unavailable.
        _struct_stop = None
        if os.environ.get("STOP_STRUCTURE_TRAIL_V1", "0").lower() in ("1", "true", "yes"):
            _struct_stop = self._structure_stop_after_t1(direction)

        # FIX-12 (Cowork, 2026-07-10, ראיית עסקת-סים 340): when the STRUCTURE stop is
        # WIDER than the current stop (e.g. SHORT: swing-high 7605 vs stop 7603.75),
        # the old code used it as target_stop and the never-widen guard returned
        # SILENTLY — the stop never tightened at all. Per Michael's intent ("לקרב
        # לכניסה... באזור המבנה"): use structure only when it TIGHTENS vs the current
        # stop; otherwise fall back to BE±1T. Silent no-op is forbidden (SYS-2).
        if direction == "LONG":
            _be = entry + tick
            _cur = float(trade.stop) if trade.stop is not None else None
            if _struct_stop is not None and (_cur is None or _struct_stop > _cur):
                target_stop = _struct_stop          # structure that tightens
            else:
                target_stop = _be                   # BE+1T fallback
            if _cur is not None and _cur >= target_stop:
                logger.info(
                    "[TradeManager] SMART_BE no-op trade=%s: current stop %.2f already ≥ target %.2f "
                    "(struct=%s) — never widen", trade.id, _cur, target_stop, _struct_stop)
                return
            trade.stop = target_stop
        elif direction == "SHORT":
            _be = entry - tick
            _cur = float(trade.stop) if trade.stop is not None else None
            if _struct_stop is not None and (_cur is None or _struct_stop < _cur):
                target_stop = _struct_stop          # structure that tightens
            else:
                target_stop = _be                   # BE-1T fallback
            if _cur is not None and _cur <= target_stop:
                logger.info(
                    "[TradeManager] SMART_BE no-op trade=%s: current stop %.2f already ≤ target %.2f "
                    "(struct=%s) — never widen", trade.id, _cur, target_stop, _struct_stop)
                return
            trade.stop = target_stop
        else:
            logger.warning(
                "[TradeManager] _apply_smart_be_after_t1 unknown direction=%s · trade_id=%s",
                direction, getattr(trade, "id", "?"),
            )
            return

        # cross_context audit per Gap 11 (reassign list to trigger SQLAlchemy dirty tracking)
        audit_entry = {
            "event": "stop_move",
            "from": stop_before,
            "to": float(trade.stop),
            "reason": ("structure-trail after T1" if _struct_stop is not None
                       else "BE+1T after T1 hit"),
        }
        ctx = list(trade.cross_context) if isinstance(trade.cross_context, list) else []
        ctx.append(audit_entry)
        trade.cross_context = ctx
        self._log_management(trade.id, "SMART_BE", {"from": stop_before, "to": float(trade.stop)})
        self._emit_modify_stop(trade, float(trade.stop))

        logger.info(
            "[TradeManager] Smart BE+1T after T1: trade %s stop %.2f -> %.2f",
            trade.id, stop_before if stop_before else 0, trade.stop,
        )

    def _structure_stop_after_t1(self, direction: str) -> Optional[float]:
        """STOP_STRUCTURE_TRAIL_V1: the nearest structural anchor from the last
        bars (cluster low−offset for LONG / cluster high+offset for SHORT).
        Reads the canonical woodies bars; honest None on any gap (caller falls
        back to BE+1T). Pure read — no synthesis (Rule 1)."""
        try:
            from backend.v9.config_loader import load_stop_anchors
            from backend.v9.db.read import read_all
            from backend.v9.systems.stop_anchors import resolver as SA
            cfg = load_stop_anchors()
            _off = int((cfg or {}).get("principles", {}).get("anchor_offset_ticks", 3))
            _win = int(os.environ.get("STOP_STRUCT_WINDOW_BARS", "8"))
            rows = read_all(
                "SELECT high, low FROM v9_bars_5min_woodies ORDER BY ts DESC LIMIT :n",
                {"n": _win})
            if not rows or len(rows) < 3:
                # No-silent-failure (CLAUDE.md): this None is exactly what collapsed
                # #366's runner to BE (structure unavailable → BE±1T fallback). Surface
                # it so tomorrow we can see WHEN/WHY (usually a woodies-bar feed gap —
                # e.g. the +1h TZ issue fixed in 64d9411). WARNING, not silent.
                logger.warning(
                    "[TradeManager] structure-trail: only %d woodies bars (need >=3) "
                    "-> BE fallback (runner loses structural room; check feed/V9_CHART_TZ)",
                    len(rows) if rows else 0)
                return None
            # resolver's window_extreme reads the zlr-buffer keys "h"/"l"
            # (drill 07-09: {"high","low"} keys → KeyError 'l' → BE fallback)
            bars = [{"h": float(r["high"]), "l": float(r["low"])}
                    for r in reversed(rows)
                    if r.get("high") is not None and r.get("low") is not None]
            if len(bars) < 3:
                return None
            anchor = SA.resolve_anchor_from_window(bars, direction, _off)
            logger.info("[TradeManager] structure-trail anchor (%s, win=%d): %.2f",
                        direction, _win, anchor)
            return float(anchor)
        except Exception as e:
            logger.warning("[TradeManager] structure-trail unavailable (%s) — BE+1T fallback", e)
            return None

    def _apply_window_anchor_trail(self, trade) -> bool:
        """FIX-15 (Michael ruling 2026-07-10: "לבדוק על כל נר את הסטופ ולראות אם
        אפשר לשפר במבנה חדש"): per-bar structural stop improvement BETWEEN
        consolidations, under STOP_PERBAR_STRUCT_V1 (default OFF).

        The dynamic struct-trail moves the stop only when a consolidation zone
        is detected — sparse. This re-checks the rolling window anchor
        (_structure_stop_after_t1) on EVERY post-T1 bar and takes it when it
        TIGHTENS vs the current stop (FIX-12 principle). Never widens; no-op
        is logged loudly (SYS-2: no silent skips in the money path).
        Returns True when the stop moved.
        """
        if self._zlr_stop_locked(trade):
            return False  # ZLR_MGMT_V1: stop is fixed — no per-bar window-anchor trail
        if os.environ.get("STOP_PERBAR_STRUCT_V1", "0").lower() not in ("1", "true", "yes"):
            return False
        if trade.entry_price is None or trade.stop is None:
            return False
        direction = (trade.direction or "").upper()
        if direction not in ("LONG", "SHORT"):
            return False
        anchor = self._structure_stop_after_t1(direction)
        cur = float(trade.stop)
        if anchor is None:
            logger.info("[TradeManager] FIX15 no-op trade=%s: no window anchor (stop stays %.2f)",
                        trade.id, cur)
            return False
        tightens = anchor > cur if direction == "LONG" else anchor < cur
        if not tightens:
            logger.info("[TradeManager] FIX15 no-op trade=%s: anchor %.2f does not tighten "
                        "stop %.2f (%s) — never widen", trade.id, anchor, cur, direction)
            return False
        new_stop = round(float(anchor), 2)
        stop_before = cur
        trade.stop = new_stop
        audit_entry = {
            "event": "stop_move",
            "from": stop_before,
            "to": new_stop,
            "reason": "FIX15 per-bar window-anchor structure",
        }
        ctx = list(trade.cross_context) if isinstance(trade.cross_context, list) else []
        ctx.append(audit_entry)
        trade.cross_context = ctx
        self._log_management(trade.id, "STRUCT_TRAIL", {
            "from": stop_before, "to": new_stop, "source": "window_anchor_fix15",
        })
        self._emit_modify_stop(trade, new_stop)
        logger.info("[TradeManager] FIX15 window-anchor: trade %s stop %.2f -> %.2f (%s)",
                    trade.id, stop_before, new_stop, direction)
        return True

    def apply_target_realism_perbar(self, trade) -> bool:
        """FIX-16 per-bar leg (TARGET_REALISM_V1, default OFF): re-check on every
        bar that the pending first-fill target is still REALISTIC — inside the
        session extreme + today's average breakout step. A target that drifted
        beyond the ceiling is tightened toward it (tighten-only, never farther,
        never across entry) with a MODIFY to the target order + full audit.

        Trade 350 evidence (2026-07-10): T1 7617.5 vs day-high 7614 — missed
        by 2 ticks while price traded at the extreme for an hour.
        Returns True when a target moved.
        """
        if os.environ.get("TARGET_REALISM_V1", "0").lower() not in ("1", "true", "yes"):
            return False
        if trade.entry_price is None:
            return False
        direction = (trade.direction or "").upper()
        if direction not in ("LONG", "SHORT"):
            return False

        # Front pending target: t1 before T1-hit, else t2, else t3 (runner)
        q = dict(trade.quality) if isinstance(trade.quality, dict) else {}
        if getattr(trade, "t1_hit_ts", None) is None and trade.t1 is not None:
            tgt_field, tgt_val, order_id = "t1", float(trade.t1), q.get("c1_target_id")
        elif getattr(trade, "t2_hit_ts", None) is None and trade.t2 is not None:
            tgt_field, tgt_val, order_id = "t2", float(trade.t2), q.get("c2_target_id")
        elif getattr(trade, "t3_hit_ts", None) is None and trade.t3 is not None:
            tgt_field, tgt_val, order_id = "t3", float(trade.t3), q.get("c3_target_id")
        else:
            return False

        from backend.v9.systems.structural_targets import realism_ceiling
        entry = float(trade.entry_price)
        ceiling = realism_ceiling(direction, entry)
        if ceiling is None:
            return False  # honest skip (Rule 1) — no bars, no invented level

        too_far = tgt_val > ceiling if direction == "LONG" else tgt_val < ceiling
        if not too_far:
            return False  # target already realistic — silent OK (every bar)

        floor2t = entry + 0.5 if direction == "LONG" else entry - 0.5
        new_tgt = max(ceiling, floor2t) if direction == "LONG" else min(ceiling, floor2t)
        if abs(new_tgt - tgt_val) < 0.25:
            return False
        setattr(trade, tgt_field, new_tgt)
        audit_entry = {
            "event": "target_move",
            "target": tgt_field,
            "from": tgt_val,
            "to": new_tgt,
            "reason": "FIX16 realism ceiling (session extreme + avg breakout step)",
        }
        ctx = list(trade.cross_context) if isinstance(trade.cross_context, list) else []
        ctx.append(audit_entry)
        trade.cross_context = ctx
        self._log_management(trade.id, "TARGET_REALISM", {
            "target": tgt_field, "from": tgt_val, "to": new_tgt, "ceiling": ceiling,
        })
        if order_id:
            self._emit_modify_target(trade, new_tgt, target_order_id=int(order_id))
        logger.warning(
            "[TradeManager] FIX16 realism: trade %s %s %.2f -> %.2f (ceiling %.2f, %s)",
            trade.id, tgt_field, tgt_val, new_tgt, ceiling, direction)
        return True

    # ---------------------------------------------------------------- F5
    def _swing_bars_today(self):
        """Today's CLOSED RTH 5-min woodies bars + the previous session's.

        Returns (today_bars, prev_bars) or (None, None) on any gap — honest
        failure (Rule 1); the caller falls back to the existing trail rather
        than trailing off an invented level. Cached per bar-timestamp so a
        session with two open trades costs one read, not two (the backend is
        single-worker uvicorn — polling floors exist for this reason).
        """
        from backend.v9.db.read import read_all
        rows = read_all(
            "SELECT (ts AT TIME ZONE 'America/New_York') AS et, high, low, close "
            "FROM v9_bars_5min_woodies "
            "WHERE (ts AT TIME ZONE 'America/New_York')::date >= "
            "      ((now() AT TIME ZONE 'America/New_York')::date - 7) "
            "  AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' "
            "  AND (ts AT TIME ZONE 'America/New_York')::time <  '16:00' "
            "ORDER BY ts ASC", {})
        if not rows:
            return None, None
        by_day = {}
        for r in rows:
            if r.get("high") is None or r.get("low") is None or r.get("close") is None:
                continue
            by_day.setdefault(r["et"].date(), []).append(
                {"h": float(r["high"]), "l": float(r["low"]), "c": float(r["close"])})
        if not by_day:
            return None, None
        days = sorted(by_day)
        today = by_day[days[-1]]
        prev = by_day[days[-2]] if len(days) >= 2 else None
        return today, prev

    def apply_structural_swing_trail(self, trade: V9Trade) -> Optional[bool]:
        """F5 · RUNNER_TRAIL_V2 (Michael 2026-08-20, ORACLE_STUDY §5 R-A).

        "Let the swing run": once the ladder has banked, the remaining runner's
        stop trails behind the LAST CONFIRMED SWING low (LONG) / high (SHORT) on
        CLOSED 5-min bars — never widening, floored at BE+1T. The runner leg is
        placed WITHOUT a fixed target (sierra_command.command_from_setup), so the
        trail is what finally takes it out; that pairing is the whole fix. A stop
        trail alone can never hold a position past a resting limit order, which is
        exactly why RUNNER_TRAIL_V1 could not have earned the $2,315 even if it
        had been wired (it is not — see bar_level_detector).

        Exit levers used: MODIFY_STOP only. op=EXIT stays untouched (CLAUDE.md).

        Returns
            True  — stop moved.
            False — evaluated, structure does not tighten: HOLD. (Deliberate: not
                    falling through to the dynamic trail is the point of F5.)
            None  — could not evaluate (no bars / no ATR / no confirmed swing yet).
                    Caller falls back to the previous trail so a runner is never
                    left un-trailed by a data gap.
        """
        if os.environ.get("RUNNER_TRAIL_V2", "0").lower() not in ("1", "true", "yes"):
            return None
        if self._zlr_stop_locked(trade):
            return False  # ZLR_MGMT_V1: stop is fixed (structural -> BE at T1)
        if trade.entry_price is None or getattr(trade, "t1_hit_ts", None) is None:
            return None  # runner-only: before T1 the banked legs still own the stop
        direction = (trade.direction or "").upper()
        if direction not in ("LONG", "SHORT"):
            return None

        from backend.v9.services.trade_manager.swing_trail import (
            swing_rev_threshold, swing_trail_stop,
        )
        from backend.v9.systems.five_min.constants import MES_TICK_SIZE

        cfg = {}
        try:
            from backend.v9.config_loader import load_stop_anchors
            cfg = ((load_stop_anchors() or {}).get("runner_trail_v2") or {})
        except Exception:
            cfg = {}
        offset_ticks = int(cfg.get("offset_ticks", 1))

        try:
            today, prev = self._swing_bars_today()
        except Exception as e:
            logger.warning("[TradeManager] F5 swing-trail: bar read failed (%s) "
                           "— falling back to the existing trail", e)
            return None
        if not today or len(today) < 3:
            logger.warning("[TradeManager] F5 swing-trail: only %d closed bars today "
                           "(need >=3) — fallback (check the woodies feed)",
                           len(today or []))
            return None

        rev = swing_rev_threshold(prev)
        if rev is None:
            _fb = cfg.get("rev_fallback_pts")
            if _fb is None:
                logger.warning("[TradeManager] F5 swing-trail: no prior-session ATR "
                               "— fallback (Rule 1: no invented threshold)")
                return None
            rev = float(_fb)

        anchor = swing_trail_stop(today, direction, rev=rev, offset_ticks=offset_ticks)
        if anchor is None:
            logger.info("[TradeManager] F5 swing-trail trade=%s: no confirmed swing yet "
                        "(rev=%.2f) — HOLD, stop unchanged", trade.id, rev)
            return None

        # T-43a fix #2 (cowork 29.08): the 28.08 incident was SWING_TRAIL writing
        # 7745.50 from trade.entry_price=7750, not SMART_BE. Use position
        # reference price (sierra.avg_price when multiple same-dir trades).
        try:
            entry = _position_reference_price(trade, self._db)
        except Exception:
            entry = float(trade.entry_price)
        tick = MES_TICK_SIZE
        be_floor = entry + tick if direction == "LONG" else entry - tick
        new_stop = max(anchor, be_floor) if direction == "LONG" else min(anchor, be_floor)
        new_stop = round(new_stop, 2)

        cur = float(trade.stop) if trade.stop is not None else None
        if cur is not None:
            tightens = new_stop > cur if direction == "LONG" else new_stop < cur
            if not tightens:
                logger.info(
                    "[TradeManager] F5 swing-trail trade=%s: swing %.2f (rev=%.2f) does "
                    "not tighten stop %.2f (%s) — HOLD (never widen)",
                    trade.id, anchor, rev, cur, direction)
                return False

        trade.stop = new_stop
        audit_entry = {
            "event": "stop_move",
            "from": cur,
            "to": new_stop,
            "reason": f"F5 swing trail (last confirmed swing {anchor:.2f}, rev={rev:.2f})",
        }
        ctx = list(trade.cross_context) if isinstance(trade.cross_context, list) else []
        ctx.append(audit_entry)
        trade.cross_context = ctx
        self._log_management(trade.id, "SWING_TRAIL", {
            "from": cur, "to": new_stop, "swing": anchor, "rev": rev,
            "be_floor": round(be_floor, 2), "source": "runner_trail_v2",
        })
        self._emit_modify_stop(trade, new_stop)
        logger.warning(
            "[TradeManager] F5 SWING_TRAIL: trade %s stop %s -> %.2f "
            "(swing=%.2f rev=%.2f floor=%.2f %s)",
            trade.id, cur, new_stop, anchor, rev, be_floor, direction)
        return True

    def apply_trail_after_t1(self, trade: V9Trade, bar_high: float, bar_low: float) -> None:
        """Trailing stop after T1 hit (RUNNER_TRAIL_V1).

        Trail = hwm − k×initial_risk (LONG) or hwm + k×risk (SHORT).
        Floor = BE+1T (never below the current smart-BE level).
        Never widens the stop. hwm persisted in quality["trail_hwm"].
        """
        if self._zlr_stop_locked(trade):
            return  # ZLR_MGMT_V1: stop is fixed (structural → BE at T1) — no runner trail
        if trade.entry_price is None:
            return
        initial = self._initial_stop(trade)
        if initial is None:
            return
        entry = float(trade.entry_price)
        risk = abs(entry - initial)
        if risk <= 0:
            return

        from backend.v9.systems.five_min.constants import MES_TICK_SIZE
        tick = MES_TICK_SIZE

        # k_risk from config (tunable). RUNNER_TRAIL_V1 refinement (2026-06-22): momentum-aware
        # widening — once the runner is a STRONG leg (favorable ≥ widen_at_R × risk), give it room
        # (k_wide) instead of cutting on the first pullback. Today's 195/196 were trailed out at the
        # bounce while the trend leg ran on (195 took +1.14R vs +2.44R MFE). Config keys
        # runner_trail.widen_at_R + .k_wide; ABSENT → k_eff == k (exactly current behavior, no change).
        k = 1.0
        widen_at_R = None
        k_wide = None
        try:
            from backend.v9.config_loader import load_stop_anchors
            _sa = load_stop_anchors()
            _rt = (_sa or {}).get("runner_trail") if _sa else None
            if _rt:
                k = float(_rt.get("k_risk", 1.0))
                if "widen_at_R" in _rt and "k_wide" in _rt:
                    widen_at_R = float(_rt["widen_at_R"])
                    k_wide = float(_rt["k_wide"])
        except Exception:
            pass

        direction = (trade.direction or "").upper()

        def _k_eff(hwm_val: float) -> float:
            # widen the trail only after the runner has proven a strong leg (default: no widening)
            if widen_at_R is None or k_wide is None or risk <= 0:
                return k
            fav = (hwm_val - entry) if direction == "LONG" else (entry - hwm_val)
            return max(k, k_wide) if (fav / risk) >= widen_at_R else k

        q = dict(trade.quality) if isinstance(trade.quality, dict) else {}

        if direction == "LONG":
            hwm = max(float(q.get("trail_hwm", entry)), bar_high)
            q["trail_hwm"] = hwm
            trail = hwm - _k_eff(hwm) * risk
            floor = entry + tick  # never below BE+1T
            new_stop = round(max(trail, floor), 2)
            if trade.stop is not None and new_stop <= float(trade.stop):
                trade.quality = q
                return  # never widen
        elif direction == "SHORT":
            hwm = min(float(q.get("trail_hwm", entry)), bar_low)
            q["trail_hwm"] = hwm
            trail = hwm + _k_eff(hwm) * risk
            floor = entry - tick
            new_stop = round(min(trail, floor), 2)
            if trade.stop is not None and new_stop >= float(trade.stop):
                trade.quality = q
                return  # never widen
        else:
            return

        stop_before = float(trade.stop) if trade.stop is not None else None
        trade.stop = new_stop
        trade.quality = q

        # Audit trail (same pattern as _apply_smart_be_after_t1)
        audit_entry = {
            "event": "stop_move",
            "from": stop_before,
            "to": new_stop,
            "reason": f"TRAIL hwm={hwm:.2f} k={k} risk={risk:.2f}",
        }
        ctx = list(trade.cross_context) if isinstance(trade.cross_context, list) else []
        ctx.append(audit_entry)
        trade.cross_context = ctx
        self._log_management(trade.id, "TRAIL", {
            "from": stop_before, "to": new_stop, "hwm": hwm, "k": k, "risk": round(risk, 2),
        })
        self._emit_modify_stop(trade, new_stop)

        logger.info(
            "[TradeManager] TRAIL: trade %s stop %.2f -> %.2f (hwm=%.2f k=%.1f risk=%.1f)",
            trade.id, stop_before or 0, new_stop, hwm, k, risk,
        )

    def apply_dynamic_struct_trail(self, trade, bar_high: float, bar_low: float,
                                    bar_close: float) -> None:
        """Dynamic structure-trailing after T1 (DYNAMIC_STRUCT_TRAIL flag).

        On each bar past T1: detect a new consolidation → move stop just beyond
        the zone (never widen) + advance the next target to the nearer of
        {zone projection, next key level}. Repeats through T3+.

        Michael's rule: runners re-anchor on each NEW CONSOLIDATION after advance.
        """
        if self._zlr_stop_locked(trade):
            return  # ZLR_MGMT_V1: stop is fixed (structural → BE at T1) — no dynamic trail
        if trade.entry_price is None:
            return
        initial = self._initial_stop(trade)
        if initial is None:
            return
        entry = float(trade.entry_price)
        risk = abs(entry - initial)
        if risk <= 0:
            return

        direction = (trade.direction or "").upper()
        from backend.v9.systems.five_min.constants import MES_TICK_SIZE
        tick = MES_TICK_SIZE

        # Load consolidation params from config
        consol_cfg = {"min_bars": 3, "max_range_atr_frac": 0.5,
                      "min_advance_risk_mult": 1.0, "range_floor_pts": 2.0}
        try:
            from backend.v9.config_loader import load_stop_anchors
            _sa = load_stop_anchors()
            _cp = ((_sa or {}).get("dynamic_struct_trail") or {})
            for k_cfg in consol_cfg:
                if k_cfg in _cp:
                    consol_cfg[k_cfg] = float(_cp[k_cfg])
        except Exception:
            pass

        # Build bars-since-entry from the trade's bar history in quality
        q = dict(trade.quality) if isinstance(trade.quality, dict) else {}
        trail_bars = q.get("struct_trail_bars", [])
        trail_bars.append({"high": bar_high, "low": bar_low, "close": bar_close})
        # Keep at most 60 bars (5h of 5-min bars)
        if len(trail_bars) > 60:
            trail_bars = trail_bars[-60:]
        q["struct_trail_bars"] = trail_bars

        # Last anchor = current stop (the reference for "advance beyond")
        last_anchor = float(trade.stop) if trade.stop is not None else entry

        # ATR-14 approximation from recent bars
        atr_14 = None
        if len(trail_bars) >= 14:
            trs = []
            for i, b in enumerate(trail_bars):
                br = b["high"] - b["low"]
                if i > 0:
                    prev_c = trail_bars[i - 1]["close"]
                    br = max(br, abs(b["high"] - prev_c), abs(b["low"] - prev_c))
                trs.append(br)
            atr_14 = sum(trs[-14:]) / 14

        from backend.v9.services.trade_manager.consolidation import (
            detect_consolidation, next_target_from_levels,
        )

        zone = detect_consolidation(
            bars=trail_bars,
            direction=direction,
            last_anchor_price=last_anchor,
            entry_price=entry,
            initial_risk=risk,
            min_bars=int(consol_cfg["min_bars"]),
            max_range_atr_frac=consol_cfg["max_range_atr_frac"],
            min_advance_risk_mult=consol_cfg["min_advance_risk_mult"],
            atr_14=atr_14,
            range_floor_pts=consol_cfg["range_floor_pts"],
        )

        if zone is None:
            trade.quality = q
            # FIX-15: no consolidation this bar — still re-check the rolling
            # window anchor so the stop improves on every new structure.
            self._apply_window_anchor_trail(trade)
            return  # no consolidation → no zone move

        # Move stop just beyond the zone (never widen)
        if direction == "LONG":
            new_stop = round(zone["anchor_extreme"] - 3 * tick, 2)  # 3T below zone low
            floor = entry + tick  # never below BE+1T
            new_stop = max(new_stop, floor)
            if trade.stop is not None and new_stop <= float(trade.stop):
                trade.quality = q
                self._apply_window_anchor_trail(trade)  # FIX-15: zone wider — try window anchor
                return  # never widen
        elif direction == "SHORT":
            new_stop = round(zone["anchor_extreme"] + 3 * tick, 2)  # 3T above zone high
            floor = entry - tick
            new_stop = min(new_stop, floor)
            if trade.stop is not None and new_stop >= float(trade.stop):
                trade.quality = q
                self._apply_window_anchor_trail(trade)  # FIX-15: zone wider — try window anchor
                return  # never widen
        else:
            trade.quality = q
            return

        # Fetch key levels for next target
        key_levels = []
        try:
            import importlib
            _app = importlib.import_module("backend.v9.app").app
            _tpo = getattr(_app.state, "tpo_system", None)
            if _tpo and hasattr(_tpo, "current_state"):
                _cs = _tpo.current_state
                for lvl_key in ("ib_high", "ib_low", "poc", "vah", "val"):
                    v = _cs.get(lvl_key)
                    if v is not None:
                        key_levels.append(float(v))
            # PDH/PDL from key_levels endpoint cache
            from backend.v9.api.v9.key_levels_routes import _load_sierra_tpo
            _sierra = _load_sierra_tpo() or {}
            _pd = _sierra.get("prior_day") or {}
            for k_pd in ("high", "low"):
                v = _pd.get(k_pd)
                if v is not None:
                    key_levels.append(float(v))
        except Exception:
            pass  # fail-safe: no levels → zone projection only

        # Zone projection: the zone range projected from the breakout edge
        zone_proj = None
        if direction == "LONG":
            zone_proj = zone["zone_high"] + zone["zone_range"]
        else:
            zone_proj = zone["zone_low"] - zone["zone_range"]

        next_tgt = next_target_from_levels(
            direction=direction,
            current_price=bar_close,
            zone_projection=zone_proj,
            key_levels=key_levels,
        )

        stop_before = float(trade.stop) if trade.stop is not None else None
        trade.stop = new_stop

        # Advance the FRONT runner's target (C1 target is FIXED — never re-anchor).
        # C2 is the front runner while it's unfilled; once C2 fills, C3 becomes front.
        runner_target_id = None
        if next_tgt is not None:
            if trade.t2 is not None and trade.t2_hit_ts is None:
                trade.t2 = next_tgt
                runner_target_id = q.get("c2_target_id")
            elif trade.t3 is not None and trade.t3_hit_ts is None:
                trade.t3 = next_tgt
                runner_target_id = q.get("c3_target_id")

        trade.quality = q

        # Audit
        audit_entry = {
            "event": "stop_move",
            "from": stop_before,
            "to": new_stop,
            "reason": "STRUCT_TRAIL zone=[%.2f,%.2f] adv=%.1f next_tgt=%s runner_id=%s" % (
                zone["zone_low"], zone["zone_high"], zone["advance"],
                ("%.2f" % next_tgt) if next_tgt else "none",
                runner_target_id or "none"),
        }
        ctx = list(trade.cross_context) if isinstance(trade.cross_context, list) else []
        ctx.append(audit_entry)
        trade.cross_context = ctx
        self._log_management(trade.id, "STRUCT_TRAIL", {
            "from": stop_before, "to": new_stop,
            "zone_high": zone["zone_high"], "zone_low": zone["zone_low"],
            "advance": zone["advance"], "next_target": next_tgt,
            "runner_target_id": runner_target_id,
        })
        self._emit_modify_stop(trade, new_stop)
        if next_tgt is not None and runner_target_id:
            # Route to the FRONT runner's own Sierra target order (NOT C1)
            self._emit_modify_target(trade, next_tgt, target_order_id=int(runner_target_id))

        logger.info(
            "[TradeManager] STRUCT_TRAIL: trade %s stop %.2f -> %.2f "
            "(zone [%.2f,%.2f] adv=%.1f next=%s)",
            trade.id, stop_before or 0, new_stop,
            zone["zone_low"], zone["zone_high"], zone["advance"],
            ("%.2f" % next_tgt) if next_tgt else "none",
        )

    def _apply_stop_after_t2(self, trade: V9Trade) -> None:
        """Move stop to BE + 0.5R after T2 hit (RUNNER_TARGETS_V1).

        Only applies when RUNNER_TARGETS_V1 flag is ON. After T2 hit, lock in
        partial profit by moving the stop to entry + 0.5R (half the initial risk
        in profit direction). Never widens the stop.
        """
        import os as _os
        if self._zlr_stop_locked(trade):
            return  # ZLR_MGMT_V1: stop is fixed at BE after T1 — no post-T2 BE+0.5R lock
        if not _os.environ.get("RUNNER_TARGETS_V1", "").lower() in ("1", "true", "yes"):
            return
        if trade.entry_price is None:
            return

        initial = self._initial_stop(trade)
        if initial is None:
            return

        entry = float(trade.entry_price)
        risk = abs(entry - initial)
        if risk <= 0:
            return

        direction = (trade.direction or "").upper()
        half_r = 0.5 * risk
        if direction == "LONG":
            target_stop = entry + half_r
        elif direction == "SHORT":
            target_stop = entry - half_r
        else:
            return

        stop_before = float(trade.stop) if trade.stop is not None else None
        # Never widen: only move if new stop is tighter (more favorable)
        if direction == "LONG" and stop_before is not None and stop_before >= target_stop:
            return
        if direction == "SHORT" and stop_before is not None and stop_before <= target_stop:
            return

        trade.stop = target_stop
        self._log_management(trade.id, "STOP_AFTER_T2", {
            "from": stop_before, "to": target_stop, "half_r": round(half_r, 2),
        })
        logger.info(
            "[TradeManager] Stop after T2: trade %s stop %.2f -> %.2f (BE+0.5R)",
            trade.id, stop_before or 0, target_stop,
        )

    def on_stop_hit(
        self,
        trade_id: int,
        fill_ts: Optional[datetime] = None,
        fill_price: Optional[float] = None,
        fill_qty: Optional[int] = None,
        order_id: Optional[int] = None,
    ) -> None:
        """Close trade on stop hit.

        fill_price: the ACTUAL Sierra fill price from trade_fills.json.
        When provided, exit_price = the real fill (may differ from trade.stop
        due to slippage). When None (legacy/BarLevelDetector), falls back to
        trade.stop. P&L must reflect the real fill, not the intended level.
        fill_qty / order_id: T-62 — a LADDER stops out in pieces, at different
        prices (#749: 1@7734.75 then 1@7732.50). Only a per-leg quantity keeps
        the second fill from re-pricing the first.
        """
        trade = self._get_trade(trade_id)
        machine = self._get_machine(trade)

        hit_ts = fill_ts or _market_now_utc()  # Prompt 26b: market time

        # T-62: record this stop leg at its own price BEFORE the close, but only
        # when Sierra told us how many contracts it took (`fill_qty`). Without a
        # quantity the honest reading is still "everything left goes at this
        # fill", which is exactly the fallback _calculate_pnl already applies —
        # inventing a per-leg quantity here would be a Rule-1 synthesis.
        if fill_price is not None and fill_qty:
            self._record_exit_fill(trade, "STOP", fill_price, qty=fill_qty,
                                   order_id=order_id, ts=hit_ts)

        # Capture cross-system snapshot at stop hit (per spec Section 2.2)
        self._append_snapshot(trade, "stop_hit")

        machine.transition(TradeState.CLOSED)
        trade.state = TradeState.CLOSED.value
        trade.stop_hit_ts = hit_ts
        trade.exit_ts = hit_ts
        # P&L from Sierra fill: use actual fill price when available
        trade.exit_price = fill_price if fill_price is not None else trade.stop
        trade.exit_reason = "STOP_HIT"
        self._log_management(trade_id, "STOP_HIT", {
            "ts": hit_ts.isoformat(),
            "stop": float(trade.stop) if trade.stop else None,
            "fill_price": fill_price,
        })

        self._calculate_pnl(trade)
        self._set_outcome(trade)
        self._cleanup_machine(trade_id)
        self._db.flush()

        self._emitter.emit("stop_hit", trade_id, {
            "ts": hit_ts.isoformat(),
            "state": TradeState.CLOSED.value,
            "outcome": trade.outcome,
            "pnl_usd": trade.pnl_usd,
        })

        # POST_MORTEM_V1: auto-diagnose losses (observability only, never raises)
        if trade.outcome == "LOSS":
            try:
                from backend.v9.services.postmortem.analyzer import on_trade_closed
                on_trade_closed(trade_id, self._db)
            except Exception:
                pass

        # N12: central OPS_LOG line (never raises)
        try:
            from scripts.ops_log import log_event as _ops
            _ops("trade_manager", "WARN",
                 f"STOP-HIT #{trade_id} @{trade.exit_price} outcome={trade.outcome} "
                 f"pnl_usd={trade.pnl_usd}")
        except Exception:
            pass

    def close_trade(self, trade_id: int, reason: str, exit_price: Optional[float] = None,
                    outcome_override: Optional[str] = None) -> None:
        """Manual close — any active state -> CLOSED.

        exit_price: when provided (e.g. from Sierra fill or OPPOSITE_2X), sets
        the actual exit price for P&L. When None, _calculate_pnl falls back to
        target-based calculation.
        outcome_override: when provided (e.g. "CANCELLED" for ORDER_FAILED),
        replaces the PnL-based outcome. P8 fix (2026-07-22): prevents _set_outcome
        from writing "BE" on a trade that was never actually executed.

        T-160 PNL_REQUIRES_EXIT_PRICE_V1 (cowork 30.08): a close WITHOUT
        exit_price on a demo/live trade sets pnl_usd=NULL and marks
        pnl_status='UNPRICED'. Rule 1: honest failure > synthetic value.
        The phantom_reconcile path was crediting target-price P&L on trades
        that Sierra said "flat" — 11 phantom wins totaling $406.25.
        """
        trade = self._get_trade(trade_id)
        machine = self._get_machine(trade)

        # Capture cross-system snapshot at close (per spec Section 2.2)
        self._append_snapshot(trade, "close")

        machine.transition(TradeState.CLOSED)
        trade.state = TradeState.CLOSED.value
        trade.exit_ts = _market_now_utc()  # Prompt 26b: market time
        trade.exit_reason = reason
        if exit_price is not None:
            trade.exit_price = exit_price

        # T-160: a close without exit_price on demo/live = UNPRICED
        _t160_on = os.environ.get(
            "PNL_REQUIRES_EXIT_PRICE_V1", "0").lower() in ("1", "true", "yes")
        _is_live_demo = getattr(trade, "mode", "shadow") in ("live", "demo")
        if _t160_on and _is_live_demo and exit_price is None:
            trade.pnl_usd = None
            q = dict(trade.quality) if isinstance(trade.quality, dict) else {}
            q["pnl_status"] = "UNPRICED"
            q["pnl_unpriced_reason"] = reason
            trade.quality = q
            if outcome_override:
                trade.outcome = outcome_override
            else:
                trade.outcome = "UNPRICED"
            logger.warning(
                "[TradeManager] T-160: close_trade #%d reason=%s WITHOUT "
                "exit_price — pnl=NULL, status=UNPRICED (Rule 1)",
                trade_id, reason)
            self._cleanup_machine(trade_id)
            # T-177 (2026-09-01): this `return` used to jump over the
            # `self._db.flush()` below, so the close lived only on the
            # in-memory ORM object. `get_active_trades()` calls expire_all()
            # and re-queries, read the row back as PARTIAL, and the phantom
            # heal fired again — 6 times in a row on 2026-08-31, blocking
            # entries via T-43 for ~30 minutes each cycle.
            # It was NON-DETERMINISTIC, which is why it looked fixed: any
            # later query in the same session triggers SQLAlchemy autoflush,
            # so the close sometimes persisted by accident (trade #939 at
            # 22:10 did). Same code, two outcomes. Never rely on autoflush.
            self._db.flush()
            self._emitter.emit("trade_closed", trade_id, {
                "reason": reason,
                "state": TradeState.CLOSED.value,
                "pnl_usd": None,
                "pnl_status": "UNPRICED",
            })
            return

        self._calculate_pnl(trade)
        if outcome_override:
            trade.outcome = outcome_override
            trade.pnl_usd = 0.0
        else:
            self._set_outcome(trade)
        self._cleanup_machine(trade_id)
        self._db.flush()

        self._emitter.emit("trade_closed", trade_id, {
            "reason": reason,
            "state": TradeState.CLOSED.value,
            "outcome": trade.outcome,
            "pnl_usd": trade.pnl_usd,
        })

        # POST_MORTEM_V1: auto-diagnose losses (observability only, never raises)
        if trade.outcome == "LOSS":
            try:
                from backend.v9.services.postmortem.analyzer import on_trade_closed
                on_trade_closed(trade_id, self._db)
            except Exception:
                pass

        # N12: central OPS_LOG line (never raises)
        try:
            from scripts.ops_log import log_event as _ops
            _ops("trade_manager", "INFO",
                 f"CLOSED #{trade_id} reason={reason} @{trade.exit_price} "
                 f"outcome={trade.outcome} pnl_usd={trade.pnl_usd}")
        except Exception:
            pass

    def get_active_trades(self, mode: Optional[str] = None) -> List[V9Trade]:
        """Return all non-CLOSED trades, optionally filtered by mode.

        P30 2026-05-20: the session reaches a "committed" state after any
        write inside the same TradeManager, and a subsequent
        `query.all()` raises `InvalidRequestError: This session is in
        'committed' state; no further SQL can be emitted within this
        transaction.` Call `expire_all()` to reset the session into a
        usable state before issuing a fresh query.
        """
        try:
            self._db.expire_all()
        except Exception:
            # Best-effort — even if expire fails, fall through to query.
            pass
        query = self._db.query(V9Trade).filter(
            V9Trade.state.in_(_ACTIVE_TRADE_STATES)
        )
        if mode is not None:
            query = query.filter(V9Trade.mode == mode)
        return query.all()

    # ── trail-engine API (D-094 Gap 9 · Pkg 3b Stream 2) ───────────

    def list_trades_past_t1(self, mode: Optional[str] = None) -> List[V9Trade]:
        """All non-CLOSED trades that have hit T1 (state == PARTIAL)."""
        try:
            self._db.expire_all()
        except Exception:
            pass
        query = self._db.query(V9Trade).filter(
            V9Trade.state == TradeState.PARTIAL.value,
            V9Trade.t1_hit_ts.isnot(None),
        )
        if mode is not None:
            query = query.filter(V9Trade.mode == mode)
        return query.all()

    def update_stop_with_audit(
        self,
        trade_id: int,
        new_stop: float,
        reason: str,
        bar_ts: str,
    ) -> None:
        """Move stop with cross_context audit append (D-094 Gap 11)."""
        trade = self._get_trade(trade_id)
        if trade is None:
            logger.warning("[TradeManager] update_stop_with_audit trade %s not found", trade_id)
            return
        if self._zlr_stop_locked(trade):
            logger.info(
                "[TradeManager] ZLR_MGMT_V1 stop-lock: trail stop-move skipped on trade %s (%s)",
                trade_id, reason)
            return
        stop_before = float(trade.stop) if trade.stop is not None else None
        entry = {
            "event": "stop_move",
            "from": stop_before,
            "to": float(new_stop),
            "reason": reason,
            "bar_ts": bar_ts,
        }
        ctx = list(trade.cross_context) if isinstance(trade.cross_context, list) else []
        ctx.append(entry)
        trade.cross_context = ctx
        trade.stop = float(new_stop)
        self._log_management(trade_id, "STOP_MOVE", {"from": stop_before, "to": float(new_stop), "reason": reason})
        self._db.flush()
        logger.info(
            "[TradeManager] trail stop move: trade %s %.2f -> %.2f (%s)",
            trade_id, stop_before if stop_before else 0.0, new_stop, reason,
        )

    def acquire_fill_lock(self, trade_id: int) -> None:
        """Mark trade as receiving a Sierra fill — TrailEngine will skip."""
        self._fill_locks.add(trade_id)

    def release_fill_lock(self, trade_id: int) -> None:
        """Release lock after Sierra fill processed."""
        self._fill_locks.discard(trade_id)

    def is_fill_locked(self, trade_id: int) -> bool:
        """Query lock state (TrailEngine concurrency guard)."""
        return trade_id in self._fill_locks

    # ── internal helpers ──────────────────────────────────────────

    def _append_snapshot(self, trade: V9Trade, trigger: str) -> None:
        """Append a cross-system snapshot to trade.cross_context.

        Per spec V1.1 Section 2.2: cross_context is an ARRAY of snapshots,
        one per trade event (entry, t1_hit, t2_hit, t3_hit, stop_hit, close).
        """
        if self._snapshot is None:
            return
        snapshot = self._snapshot.capture(
            trigger, firing_system_id=trade.firing_system,
        )
        if trade.cross_context is None:
            trade.cross_context = []
        # SQLAlchemy JSON mutation: must reassign to flag dirty
        ctx = list(trade.cross_context)
        ctx.append(snapshot)
        trade.cross_context = ctx

    def _get_trade(self, trade_id: int) -> V9Trade:
        trade = self._db.query(V9Trade).filter(V9Trade.id == trade_id).first()
        if trade is None:
            raise ValueError(f"Trade {trade_id} not found")
        return trade

    def _get_machine(self, trade: V9Trade) -> TradeStateMachine:
        """Get or restore the state machine for a trade."""
        if trade.id not in self._machines:
            # Restore from DB state (e.g., after restart or legacy OPEN rows)
            self._machines[trade.id] = TradeStateMachine(
                _coerce_trade_state(trade.state)
            )
        return self._machines[trade.id]

    def _cleanup_machine(self, trade_id: int) -> None:
        """Remove state machine for closed trade — prevents unbounded growth."""
        self._machines.pop(trade_id, None)

    @staticmethod
    def _valid_target(price: Optional[float]) -> Optional[float]:
        """Sierra setups often send 0 for unused T2/T3 — must not enter PnL math."""
        if price is None:
            return None
        try:
            p = float(price)
        except (TypeError, ValueError):
            return None
        return p if p > 0 else None

    #: T-62: which `t1..t4` COLUMN a logical target label persists into. T0 has
    #: no column of its own — that hole is half of #749's error.
    _TARGET_COLUMN = {"T1": 0, "T2": 1, "T3": 2, "T4": 3}

    @staticmethod
    def _ladder_group_for(trade, kind: str) -> Optional[int]:
        """Which LADDER group (0-based, `contract_size.LADDER`) a leg belongs to.

        The DB has t1..t4 columns, but the ruled ladder can open with a T0
        scalp — and then every logical label sits one group further along than
        its column: T0 owns group 0 and no column, logical T1 lives in `t1` but
        is ladder group 1. Conflating the two indexes double-books a leg.
        None = not a target group at all (STOP / FLATTEN).
        """
        k = str(kind).upper()
        if k == "T0":
            return 0
        col = TradeManager._TARGET_COLUMN.get(k)
        if col is None:
            return None
        q = trade.quality if isinstance(getattr(trade, "quality", None), dict) else {}
        has_t0 = bool(q.get("t0_target_pts") or q.get("has_t0"))
        return min(col + 1, 3) if has_t0 else col

    @staticmethod
    def _exit_fill_ledger(trade) -> List[dict]:
        """T-62: the per-leg exit fills Sierra actually reported for this trade.

        Empty for every trade managed WITHOUT Sierra fill prices (shadow twins,
        the bar-level detector, and all history) — and when it is empty the P&L
        math below is byte-identical to the pre-T-62 code.
        """
        q = trade.quality if isinstance(getattr(trade, "quality", None), dict) else {}
        fills = q.get("exit_fills")
        if not isinstance(fills, list):
            return []
        return [f for f in fills if isinstance(f, dict)]

    def _record_exit_fill(self, trade, kind: str, price: Optional[float],
                          qty: Optional[int] = None,
                          order_id: Optional[int] = None,
                          column: Optional[int] = None,
                          ts: Optional[datetime] = None) -> None:
        """T-62 ROOT-FIX (2026-08-20): remember EVERY exit fill with its OWN
        price and quantity. A scalar `exit_price` cannot describe a ladder.

        #749 — the first live TREND_STEP ladder (LONG 4 @ 7737.5) — was booked
        `pnl_usd = -51.25` while its four Sierra fills sum to **+$1.25**:
        T1 1@7740.75 · T3 1@7742.25 · STOP 1@7734.75 · STOP 1@7732.50.
        A $52.50 error on ONE trade, from two independent holes:

          * **-$41.25 — the T0 scale-out had nowhere to live.** With
            BE_AFTER_REAL_T1_V1 + 4 contracts + a T0 target the DLL's "T1" is
            remapped to "T0"; `on_target_hit` stores a fill price only for
            T1..T4 and the T0 branch sets no `*_hit_ts`. So the contract that
            really banked +3.25 pt was invisible and got booked at the stop.
            Proof in `v9_trade_management_log`: `T0_HIT {"ts": ...}` — no price.
          * **-$11.25 — two stop fills, one `exit_price` column.** The ladder
            stopped out in two pieces at two prices; the first (7734.75) closed
            the trade, the second (7732.50) arrived on an already-CLOSED trade
            and re-booked EVERY leg through `update_closed_trade_pnl`. Proof:
            `PNL_CORRECTION {"old_pnl": -17.5, "new_pnl": -51.25}`.

        Dedup key is (kind, order_id, price, ts): the fills file is re-read on
        every mtime bump, and double-counting a leg is the mirror-image lie.
        """
        if price is None:
            return
        try:
            px = float(price)
        except (TypeError, ValueError):
            return
        try:
            n = int(qty) if qty is not None else None
        except (TypeError, ValueError):
            n = None
        if n is None or n <= 0:
            # No quantity from Sierra → use the ladder weight of this leg's
            # group (the same table the DLL brackets with), never a blind 1:
            # at six the T1 and T2 groups hold TWO contracts each.
            from backend.v9.services.contract_size import ladder_for
            g = self._ladder_group_for(trade, kind)
            w = ladder_for(trade_contract_count(trade))
            n = (w[g] if g is not None and g < len(w) else 0) or 1
        if column is None:
            # The COLUMN this leg's target persists into — that is what
            # _calculate_pnl must skip so a fill is not booked twice (once from
            # the ledger, once from its `*_hit_ts`). A stop owns no column.
            column = self._TARGET_COLUMN.get(str(kind).upper())
        # T-211 (2026-09-01): NORMALIZE the dedup timestamp to UTC before it
        # becomes a key. Two call sites feed this with differently-zoned
        # datetimes for the SAME instant: on_target_hit/on_stop_hit pass
        # `fill_ts or _market_now_utc()` (UTC, "+00:00") while
        # update_closed_trade_pnl passes `trade.exit_ts` read back through the
        # ORM as timestamptz in the session zone ("+03:00"). Observed raw in
        # v9_trades.quality.exit_fills on #948 today:
        #     "ts": "2026-09-01T16:15:15+00:00"   (on_stop_hit)
        #     "ts": "2026-09-01T19:15:15+03:00"   (update_closed_trade_pnl)
        # — the same second, two spellings. Those two rows were genuinely
        # different Sierra orders, so nothing was double-booked TODAY; but the
        # fills file is re-read on every mtime bump, and a leg that arrives
        # once through each path differs on the ts component alone, so the
        # dedup silently fails and the leg is booked twice. Normalizing makes
        # the key describe the instant, not the rendering. order_id stays in
        # the key, so two distinct orders remain two distinct legs.
        if hasattr(ts, "isoformat"):
            _t = ts
            try:
                if getattr(_t, "tzinfo", None) is not None:
                    _t = _t.astimezone(timezone.utc)
            except Exception:
                pass
            ts_key = _t.isoformat()
        else:
            ts_key = str(ts) if ts is not None else None

        q = dict(trade.quality) if isinstance(getattr(trade, "quality", None), dict) else {}
        fills = [f for f in (q.get("exit_fills") or []) if isinstance(f, dict)]
        def _norm_ts(v):
            """T-211: compare instants, not spellings — legacy rows already in
            the DB carry the '+03:00' rendering of the same second."""
            if not isinstance(v, str):
                return v
            try:
                d = datetime.fromisoformat(v)
            except Exception:
                return v
            return (d.astimezone(timezone.utc).isoformat()
                    if d.tzinfo is not None else v)

        key = (str(kind).upper(), order_id, round(px, 4), _norm_ts(ts_key))
        for f in fills:
            if (str(f.get("kind", "")).upper(), f.get("order_id"),
                    round(float(f.get("price") or 0), 4),
                    _norm_ts(f.get("ts"))) == key:
                return  # same fill re-read — never book a leg twice
        fills.append({"kind": str(kind).upper(), "price": px, "qty": n,
                      "order_id": order_id, "column": column, "ts": ts_key})
        q["exit_fills"] = fills
        trade.quality = q
        logger.info(
            "[TradeManager] T-62 exit-fill #%s %s %dc @ %.2f (order=%s col=%s) "
            "— ledger now %d leg(s)", getattr(trade, "id", "?"), kind, n, px,
            order_id, column, len(fills))

    def _calculate_pnl(self, trade: V9Trade) -> None:
        """Calculate PnL per-contract. MES = $5/point.

        Every contract belongs to one LADDER GROUP (`contract_size.LADDER`), and
        a group leaves the market exactly once — at its own Sierra fill when we
        have one (T-62), else at its target when that target was hit, else at
        the trade's exit fill.

        T-62 (2026-08-20): the fill ledger is consulted FIRST. When it is empty
        — every shadow trade, every bar-level-detector exit, all history — this
        function is byte-identical to the pre-T-62 code, which is why the whole
        P&L suite stays green.
        """
        if trade.entry_price is None:
            return

        direction_mult = 1.0 if trade.direction == "LONG" else -1.0
        t1 = self._valid_target(trade.t1)
        t2 = self._valid_target(trade.t2)
        t3 = self._valid_target(trade.t3)
        t4 = self._valid_target(getattr(trade, "t4", None))
        stop = self._valid_target(trade.stop)

        # L7 (2026-07-08): the trade's REAL contract count — a 2-contract trade
        # has 2 P&L legs, not 3 (a 2c stop-out was counted 3× = 150% of the
        # real loss; R used a 3-contract denominator).
        n_contracts = trade_contract_count(trade)

        # T-06 (2026-08-19, Michael's 6-contract ladder 1/2/2/1): a banked level
        # exits LADDER-qty contracts, not one. At n<=4 every weight is 1, so the
        # pre-T-06 behavior is preserved exactly. Any size above the protected
        # ladder spills onto the last group — the same place
        # `target_index_for_contract` sends it.
        from backend.v9.services.contract_size import ladder_for
        weights = list(ladder_for(n_contracts))
        _spill = n_contracts - sum(weights)
        if _spill > 0:
            weights[-1] += _spill

        _targets = [t1, t2, t3, t4]
        _hits = [trade.t1_hit_ts, trade.t2_hit_ts, trade.t3_hit_ts,
                 getattr(trade, "t4_hit_ts", None)]

        # Realized-only while the trade is still working: a PARTIAL books what
        # is banked and nothing else (unchanged semantics).
        realized_only = (trade.state == TradeState.PARTIAL.value
                         and not trade.exit_reason)

        # ---- build the legs: (price, qty) -----------------------------------
        legs: List[tuple] = []
        consumed_columns = set()
        for f in self._exit_fill_ledger(trade):
            px = self._valid_target(f.get("price"))
            if px is None:
                continue
            try:
                q_i = int(f.get("qty") or 0)
            except (TypeError, ValueError):
                q_i = 0
            if q_i <= 0:
                continue
            legs.append((px, q_i))
            col = f.get("column")
            if isinstance(col, int):
                # This leg's target already contributed its price; the
                # *_hit_ts loop below must not book the same contracts again.
                consumed_columns.add(col)

        # T3 ROOT-FIX (2026-08-15): build exactly n_contracts legs. The old code
        # always built THREE and then `[:n_contracts]` truncated, so a
        # 4-contract trade lost 25% of its P&L (102 closed trades affected;
        # #682's real loss was $83.75, booked $75.00) and RISK_HALT tripped late.
        for g_idx in range(len(weights)):
            if g_idx in consumed_columns:
                continue  # this level already left the market at a real fill
            tgt = _targets[g_idx] if g_idx < len(_targets) else None
            hit = _hits[g_idx] if g_idx < len(_hits) else None
            if hit is not None and tgt is not None and weights[g_idx] > 0:
                legs.append((tgt, weights[g_idx]))

        covered = sum(q for _, q in legs)
        if covered > n_contracts:
            # Never silent (CLAUDE.md): Sierra filled more contracts than the
            # books think the trade had. Book the truth, scream about the drift.
            logger.warning(
                "[TradeManager] T-62 #%s: exit legs cover %dc but the trade is "
                "booked as %dc — contract-count drift, P&L follows the FILLS",
                getattr(trade, "id", "?"), covered, n_contracts)

        if not realized_only and covered < n_contracts:
            # Whatever is still unaccounted for left at the trade's exit fill.
            if trade.exit_reason == "STOP_HIT" and stop is not None:
                # Actual Sierra fill, not the intended stop level (slippage).
                fallback = self._valid_target(trade.exit_price) or stop
            elif trade.exit_reason == "T3_HIT":
                fallback = self._valid_target(trade.exit_price) or trade.entry_price
            else:
                fallback = trade.exit_price or trade.entry_price
            legs.append((fallback, n_contracts - covered))
            covered = n_contracts

        total_pnl = 0.0
        for exit_price, qty in legs:
            points = (exit_price - trade.entry_price) * direction_mult
            total_pnl += points * MES_POINT_VALUE * qty

        trade.pnl_usd = round(total_pnl, 2)

        # pnl_r = PnL / (contracts at risk × initial risk per contract). A still
        # working trade divides by what has actually left (unchanged).
        risk_stop = self._initial_stop(trade)
        denom_units = covered if realized_only else n_contracts
        if risk_stop is not None and denom_units > 0:
            risk_per_contract = abs(trade.entry_price - risk_stop) * MES_POINT_VALUE
            if risk_per_contract > 0:
                trade.pnl_r = round(total_pnl / (denom_units * risk_per_contract), 2)

    def update_closed_trade_pnl(self, trade_id: int, exit_price: float,
                                exit_reason: Optional[str] = None,
                                fill_qty: Optional[int] = None,
                                order_id: Optional[int] = None,
                                kind: str = "STOP") -> bool:
        """P0-2 (#640): accept a fill on an already-CLOSED trade.

        Only updates P&L and outcome — no state transition. This handles
        the case where the FillPoller receives a Sierra fill event after
        the bar-level detector already closed the trade (CLOSED→CLOSED
        would raise InvalidTransition).

        T-62 (2026-08-20): a LADDER's later legs arrive here too, and this was
        the second half of #749's $52.50 error. Overwriting `exit_price` re-priced
        EVERY leg that had no target of its own — the management log recorded
        `PNL_CORRECTION {"old_pnl": -17.5, "new_pnl": -51.25}` when the fourth
        contract's stop (7732.50) retroactively re-booked the second contract's
        stop (7734.75). With `fill_qty` the late fill is now added as its OWN
        leg and `exit_price` only ever prices contracts nothing else claimed.

        Returns True if the update changed P&L.
        """
        try:
            trade = self._get_trade(trade_id)
            if trade.state != "CLOSED":
                return False  # not our case — use normal close path

            old_pnl = trade.pnl_usd
            if fill_qty:
                self._record_exit_fill(trade, kind, exit_price, qty=fill_qty,
                                       order_id=order_id,
                                       ts=getattr(trade, "exit_ts", None))
            trade.exit_price = exit_price
            if exit_reason:
                trade.exit_reason = exit_reason

            self._calculate_pnl(trade)
            self._set_outcome(trade)
            self._db.flush()

            logger.warning(
                "[TradeManager] P0-2 CLOSED trade #%d P&L update: $%.2f → $%.2f "
                "(exit_price=%.2f, outcome=%s)",
                trade_id, old_pnl or 0, trade.pnl_usd or 0,
                exit_price, trade.outcome,
            )
            self._log_management(trade_id, "PNL_CORRECTION", {
                "old_pnl": old_pnl, "new_pnl": trade.pnl_usd,
                "exit_price": exit_price, "reason": "fill_on_closed",
            })
            return True
        except Exception as e:
            logger.warning("[TradeManager] update_closed_trade_pnl failed: %s", e)
            return False

    def _set_outcome(self, trade: V9Trade) -> None:
        """Set outcome based on PnL: WIN / LOSS / BE."""
        if trade.pnl_usd is None:
            return
        if trade.pnl_usd > 0:
            trade.outcome = "WIN"
        elif trade.pnl_usd < 0:
            trade.outcome = "LOSS"
        else:
            trade.outcome = "BE"
