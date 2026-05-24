"""W11 Trade Manager — trade lifecycle: entry -> bracket -> exit.

NOT a decision maker. Receives setup objects from firing systems,
manages state transitions, emits events. Each firing system makes
its own entry decision independently.

PnL calculation: per-contract (c1/c2/c3 independently), NOT 3x.
MES tick = $1.25 per tick per contract.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from backend.v9.services.market_clock import now_utc as _market_now_utc

from backend.v9.db.models.trades import V9Trade
from backend.v9.services.trade_manager.state_machine import (
    InvalidTransition,
    TradeState,
    TradeStateMachine,
)

# Legacy gateway / cockpit rows use state="OPEN" (not in TradeState enum).
_ACTIVE_TRADE_STATES = frozenset({
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

        firing_system = setup["firing_system"]
        if firing_system not in (1, 2, 4):
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
        quality = {
            "classification": classification,
            "confidence": setup.get("confidence"),
            "metadata": meta,
            "trigger": trigger,
            "blocked_by": setup.get("blocked_by"),
        }

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

        self._emitter.emit("trade_filled", trade_id, {
            "fill_price": fill_price,
            "state": TradeState.FILLED.value,
        })

    def on_target_hit(
        self,
        trade_id: int,
        target: str,
        fill_ts: Optional[datetime] = None,
    ) -> None:
        """Record a target hit (T1, T2, T3). T1 -> PARTIAL, T3 -> CLOSED."""
        if target not in ("T1", "T2", "T3"):
            raise ValueError(f"Invalid target: {target}")

        trade = self._get_trade(trade_id)
        machine = self._get_machine(trade)
        hit_ts = fill_ts or _market_now_utc()  # Prompt 26b: market time

        # Capture cross-system snapshot at target hit (per spec Section 2.2)
        self._append_snapshot(trade, f"{target.lower()}_hit")

        if target == "T1":
            machine.transition(TradeState.PARTIAL)
            trade.state = TradeState.PARTIAL.value
            trade.t1_hit_ts = hit_ts
            self._apply_smart_be_after_t1(trade)
            self._calculate_pnl(trade)
        elif target == "T2":
            trade.t2_hit_ts = hit_ts
            self._calculate_pnl(trade)
        elif target == "T3":
            machine.transition(TradeState.CLOSED)
            trade.state = TradeState.CLOSED.value
            trade.t3_hit_ts = hit_ts
            trade.exit_ts = hit_ts
            trade.exit_reason = "T3_HIT"
            self._calculate_pnl(trade)
            self._set_outcome(trade)
            self._cleanup_machine(trade_id)

        self._db.flush()

        self._emitter.emit(f"target_{target.lower()}_hit", trade_id, {
            "target": target,
            "ts": hit_ts.isoformat(),
            "state": trade.state,
        })

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

    def _apply_smart_be_after_t1(self, trade: V9Trade) -> None:
        """Move stop to BE+1T after T1 hit · D-094 Gap 1 fix.

        OLD behavior: stop = entry (BE) — too tight, no slippage room.
        NEW behavior: stop = entry + 1T (LONG) or entry - 1T (SHORT) per Sheet C.

        Idempotent: if stop is ALREADY at BE+1T or tighter, no-op (Gap 13 'never widen').
        """
        from backend.v9.systems.five_min.constants import MES_TICK_SIZE
        if trade.entry_price is None:
            return
        direction = (trade.direction or "").upper()
        entry = float(trade.entry_price)
        tick = MES_TICK_SIZE

        # Save initial stop before any move
        q = dict(trade.quality) if isinstance(trade.quality, dict) else {}
        if "initial_stop" not in q and trade.stop is not None:
            q["initial_stop"] = float(trade.stop)
            trade.quality = q

        stop_before = float(trade.stop) if trade.stop is not None else None

        if direction == "LONG":
            target_stop = entry + tick
            if trade.stop is not None and float(trade.stop) >= target_stop:
                return  # Already at or tighter than BE+1T
            trade.stop = target_stop
        elif direction == "SHORT":
            target_stop = entry - tick
            if trade.stop is not None and float(trade.stop) <= target_stop:
                return  # Already at or tighter than BE+1T
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
            "reason": "BE+1T after T1 hit",
        }
        ctx = list(trade.cross_context) if isinstance(trade.cross_context, list) else []
        ctx.append(audit_entry)
        trade.cross_context = ctx

        logger.info(
            "[TradeManager] Smart BE+1T after T1: trade %s stop %.2f -> %.2f",
            trade.id, stop_before if stop_before else 0, trade.stop,
        )

    def on_stop_hit(
        self,
        trade_id: int,
        fill_ts: Optional[datetime] = None,
    ) -> None:
        """Close trade on stop hit."""
        trade = self._get_trade(trade_id)
        machine = self._get_machine(trade)

        hit_ts = fill_ts or _market_now_utc()  # Prompt 26b: market time

        # Capture cross-system snapshot at stop hit (per spec Section 2.2)
        self._append_snapshot(trade, "stop_hit")

        machine.transition(TradeState.CLOSED)
        trade.state = TradeState.CLOSED.value
        trade.stop_hit_ts = hit_ts
        trade.exit_ts = hit_ts
        trade.exit_price = trade.stop
        trade.exit_reason = "STOP_HIT"

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

    def close_trade(self, trade_id: int, reason: str) -> None:
        """Manual close — any active state -> CLOSED."""
        trade = self._get_trade(trade_id)
        machine = self._get_machine(trade)

        # Capture cross-system snapshot at close (per spec Section 2.2)
        self._append_snapshot(trade, "close")

        machine.transition(TradeState.CLOSED)
        trade.state = TradeState.CLOSED.value
        trade.exit_ts = _market_now_utc()  # Prompt 26b: market time
        trade.exit_reason = reason

        self._calculate_pnl(trade)
        self._set_outcome(trade)
        self._cleanup_machine(trade_id)
        self._db.flush()

        self._emitter.emit("trade_closed", trade_id, {
            "reason": reason,
            "state": TradeState.CLOSED.value,
            "outcome": trade.outcome,
            "pnl_usd": trade.pnl_usd,
        })

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

    def _calculate_pnl(self, trade: V9Trade) -> None:
        """Calculate PnL per-contract. MES = $5/point.

        Per-contract PnL: each contract (c1, c2, c3) exits at its own
        target level. We sum the individual contract PnLs.

        For stop exits: all contracts exit at stop.
        For target exits: c1@T1, c2@T2, c3@T3 (whatever was hit).
        """
        if trade.entry_price is None:
            return

        direction_mult = 1.0 if trade.direction == "LONG" else -1.0
        t1 = self._valid_target(trade.t1)
        t2 = self._valid_target(trade.t2)
        t3 = self._valid_target(trade.t3)
        stop = self._valid_target(trade.stop)

        # Determine per-contract exit prices based on what was hit
        contract_exits: List[float] = []

        if trade.state == TradeState.PARTIAL.value and not trade.exit_reason:
            total_pnl = 0.0
            hits = 0
            for target, hit_ts in ((t1, trade.t1_hit_ts), (t2, trade.t2_hit_ts)):
                if hit_ts is not None and target is not None:
                    total_pnl += (target - trade.entry_price) * direction_mult * MES_POINT_VALUE
                    hits += 1
            trade.pnl_usd = round(total_pnl, 2)
            risk_stop = self._initial_stop(trade)
            if risk_stop is not None and hits > 0:
                risk_per_contract = abs(trade.entry_price - risk_stop) * MES_POINT_VALUE
                if risk_per_contract > 0:
                    trade.pnl_r = round(total_pnl / (hits * risk_per_contract), 2)
            return

        if trade.exit_reason == "STOP_HIT" and stop is not None:
            contract_exits = [
                t1 if trade.t1_hit_ts and t1 is not None else stop,
                t2 if trade.t2_hit_ts and t2 is not None else stop,
                t3 if trade.t3_hit_ts and t3 is not None else stop,
            ]
        elif trade.exit_reason == "T3_HIT":
            exit_p = self._valid_target(trade.exit_price) or trade.entry_price
            c1 = t1 if trade.t1_hit_ts and t1 is not None else exit_p
            c2 = t2 if trade.t2_hit_ts and t2 is not None else exit_p
            c3 = t3 if (trade.t3_hit_ts and t3 is not None) else exit_p
            contract_exits = [c1, c2, c3]
        else:
            exit_p = trade.exit_price or trade.entry_price
            c1 = t1 if trade.t1_hit_ts and t1 is not None else exit_p
            c2 = t2 if trade.t2_hit_ts and t2 is not None else exit_p
            c3 = exit_p
            contract_exits = [c1, c2, c3]

        total_pnl = 0.0
        for exit_price in contract_exits:
            points = (exit_price - trade.entry_price) * direction_mult
            total_pnl += points * MES_POINT_VALUE

        trade.pnl_usd = round(total_pnl, 2)

        # pnl_r = PnL / (3 contracts × initial risk per contract)
        risk_stop = self._initial_stop(trade)
        if risk_stop is not None and trade.entry_price is not None:
            risk_per_contract = abs(trade.entry_price - risk_stop) * MES_POINT_VALUE
            if risk_per_contract > 0:
                total_risk = 3 * risk_per_contract
                trade.pnl_r = round(total_pnl / total_risk, 2)

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
