"""Woodies Terminal State Emitter (PROMPT 4 · 4.1).

Emits all 18 terminal states to DB + Redis + Slack.
Per Decision Tree V1 § Section 6.

Entry Phase (5):
  SKIP_COLOR_VETO, SKIP_NO_PATTERN, SKIP_UNIVERSAL, BUY, SELL

Active Phase (13):
  STOP_LOSS, EOD_FORCE, STRATEGIC_EXIT, SUFFERING_EXIT, CLARITY_EXIT,
  NEWS_EXIT, TIME_STOP, TIGHTEN, PARTIAL, SUCCESS_REACTIVE,
  SUCCESS_INITIATIVE, SUCCESS_TRAIL, HOLD
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class TerminalState(str, Enum):
    """All 18 terminal states per Decision Tree V1 § Section 6."""
    # Entry phase (5)
    SKIP_COLOR_VETO = "SKIP_COLOR_VETO"
    SKIP_NO_PATTERN = "SKIP_NO_PATTERN"
    SKIP_UNIVERSAL = "SKIP_UNIVERSAL"
    BUY = "BUY"
    SELL = "SELL"
    # Active phase (13)
    STOP_LOSS = "STOP_LOSS"
    EOD_FORCE = "EOD_FORCE"
    STRATEGIC_EXIT = "STRATEGIC_EXIT"
    SUFFERING_EXIT = "SUFFERING_EXIT"
    CLARITY_EXIT = "CLARITY_EXIT"
    NEWS_EXIT = "NEWS_EXIT"
    TIME_STOP = "TIME_STOP"
    TIGHTEN = "TIGHTEN"
    PARTIAL = "PARTIAL"
    SUCCESS_REACTIVE = "SUCCESS_REACTIVE"
    SUCCESS_INITIATIVE = "SUCCESS_INITIATIVE"
    SUCCESS_TRAIL = "SUCCESS_TRAIL"
    HOLD = "HOLD"


ENTRY_TERMINALS = {
    TerminalState.SKIP_COLOR_VETO,
    TerminalState.SKIP_NO_PATTERN,
    TerminalState.SKIP_UNIVERSAL,
    TerminalState.BUY,
    TerminalState.SELL,
}

ACTIVE_TERMINALS = {
    TerminalState.STOP_LOSS,
    TerminalState.EOD_FORCE,
    TerminalState.STRATEGIC_EXIT,
    TerminalState.SUFFERING_EXIT,
    TerminalState.CLARITY_EXIT,
    TerminalState.NEWS_EXIT,
    TerminalState.TIME_STOP,
    TerminalState.TIGHTEN,
    TerminalState.PARTIAL,
    TerminalState.SUCCESS_REACTIVE,
    TerminalState.SUCCESS_INITIATIVE,
    TerminalState.SUCCESS_TRAIL,
    TerminalState.HOLD,
}


@dataclass
class TradeContext:
    """Context passed with terminal state emission."""
    trade_id: str = ""
    stage_id: str = ""
    direction: Optional[str] = None
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    pnl_points: Optional[float] = None
    classification: Optional[str] = None
    bar_context: dict = field(default_factory=dict)
    notes: str = ""
    priority_class: Optional[str] = None


class TerminalStateEmitter:
    """Emits terminal states to DB + Redis + Slack.

    Steps per emit:
    1. Write to DB (woodies_trade_terminals)
    2. Update Redis live state (key: woodies:state:<trade_id>)
    3. Post Slack alert
    4. Log to journal
    """

    def __init__(self, db_session=None, redis_client=None, slack_webhook=None):
        self._db = db_session
        self._redis = redis_client
        self._slack_webhook = slack_webhook
        self._emission_log = []  # in-memory log for testing

    def emit(self, state: TerminalState, context: TradeContext) -> dict:
        """Emit a terminal state through all channels.

        Returns dict with emission results for verification.
        """
        phase = "entry" if state in ENTRY_TERMINALS else "active"
        now = datetime.now(timezone.utc)

        record = {
            "trade_id": context.trade_id,
            "terminal_state": state.value,
            "phase": phase,
            "priority_class": context.priority_class,
            "triggered_at": now.isoformat(),
            "bar_context": context.bar_context,
            "stage_id": context.stage_id,
            "direction": context.direction,
            "entry_price": context.entry_price,
            "exit_price": context.exit_price,
            "pnl_points": context.pnl_points,
            "classification": context.classification,
            "notes": context.notes,
        }

        # 1. DB write
        db_ok = self._write_db(record)

        # 2. Redis live state
        redis_ok = self._update_redis(state, context)

        # 3. Slack alert
        slack_ok = self._post_slack(state, context, phase)

        # 4. Journal log
        self._emission_log.append(record)
        logger.info(
            "[Woodies Terminal] %s · %s · trade=%s · stage=%s",
            state.value, phase, context.trade_id, context.stage_id,
        )

        return {
            "state": state.value,
            "phase": phase,
            "db": db_ok,
            "redis": redis_ok,
            "slack": slack_ok,
            "record": record,
        }

    def get_emission_log(self):
        """Return in-memory emission log (for testing)."""
        return list(self._emission_log)

    def _write_db(self, record: dict) -> bool:
        """Write terminal record to DB."""
        if self._db is None:
            return False
        try:
            from backend.v9.db.models.woodies_trade_terminals import WoodiesTradeTerminal
            row = WoodiesTradeTerminal(
                trade_id=record["trade_id"],
                terminal_state=record["terminal_state"],
                phase=record["phase"],
                priority_class=record["priority_class"],
                bar_context=record["bar_context"],
                stage_id=record["stage_id"],
                direction=record["direction"],
                entry_price=record["entry_price"],
                exit_price=record["exit_price"],
                pnl_points=record["pnl_points"],
                classification=record["classification"],
                notes=record["notes"],
            )
            self._db.add(row)
            self._db.flush()
            return True
        except Exception as e:
            logger.error("[Woodies Terminal] DB write failed: %s", e)
            return False

    def _update_redis(self, state: TerminalState, context: TradeContext) -> bool:
        """Update Redis live state key."""
        if self._redis is None:
            return False
        try:
            key = f"woodies:state:{context.trade_id}"
            self._redis.set(key, state.value, ex=86400)  # 24h TTL
            return True
        except Exception as e:
            logger.error("[Woodies Terminal] Redis update failed: %s", e)
            return False

    def _post_slack(self, state: TerminalState, context: TradeContext, phase: str) -> bool:
        """Post Slack alert."""
        if self._slack_webhook is None:
            logger.debug("[Woodies Terminal] Slack webhook not configured (skip)")
            return False
        try:
            import httpx
            msg = f"[Woodies {phase}] {state.value} · {context.direction or ''} · stage={context.stage_id}"
            if context.pnl_points is not None:
                msg += f" · PnL={context.pnl_points:.1f}pts"
            httpx.post(self._slack_webhook, json={"text": msg}, timeout=5)
            return True
        except Exception as e:
            logger.error("[Woodies Terminal] Slack post failed: %s", e)
            return False
