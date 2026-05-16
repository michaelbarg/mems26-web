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

        # Capture cross-system snapshot at entry (per spec Section 2.4)
        cross_ctx = setup.get("cross_context")
        if self._snapshot is not None:
            snapshot = self._snapshot.capture(
                "entry", firing_system_id=firing_system,
            )
            cross_ctx = [snapshot]

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
        )

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
        elif target == "T2":
            trade.t2_hit_ts = hit_ts
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
        """Return all non-CLOSED trades, optionally filtered by mode."""
        query = self._db.query(V9Trade).filter(
            V9Trade.state != TradeState.CLOSED.value
        )
        if mode is not None:
            query = query.filter(V9Trade.mode == mode)
        return query.all()

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
            # Restore from DB state (e.g., after restart)
            self._machines[trade.id] = TradeStateMachine(
                TradeState(trade.state)
            )
        return self._machines[trade.id]

    def _cleanup_machine(self, trade_id: int) -> None:
        """Remove state machine for closed trade — prevents unbounded growth."""
        self._machines.pop(trade_id, None)

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

        # Determine per-contract exit prices based on what was hit
        contract_exits: List[float] = []

        if trade.exit_reason == "STOP_HIT":
            # All 3 contracts exit at stop
            contract_exits = [trade.stop, trade.stop, trade.stop]
        elif trade.exit_reason == "T3_HIT":
            # c1@T1, c2@T2, c3@T3
            contract_exits = [trade.t1, trade.t2, trade.t3]
        else:
            # Manual close or partial — use whatever exit_price is set
            exit_p = trade.exit_price or trade.entry_price
            # c1 at T1 if hit, else exit_p; c2 at T2 if hit, else exit_p
            c1 = trade.t1 if trade.t1_hit_ts else exit_p
            c2 = trade.t2 if trade.t2_hit_ts else exit_p
            c3 = exit_p
            contract_exits = [c1, c2, c3]

        total_pnl = 0.0
        for exit_price in contract_exits:
            points = (exit_price - trade.entry_price) * direction_mult
            total_pnl += points * MES_POINT_VALUE

        trade.pnl_usd = round(total_pnl, 2)

        # pnl_r = risk-reward ratio (PnL / initial risk per contract)
        if trade.stop is not None and trade.entry_price is not None:
            risk_per_contract = abs(trade.entry_price - trade.stop) * MES_POINT_VALUE
            if risk_per_contract > 0:
                # Total risk = 3 contracts * risk_per_contract
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
