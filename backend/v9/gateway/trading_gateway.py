"""TradingGateway — 3-mode trade routing per 3-Mode Spec V3 section 8.

Modes:
  SHADOW: unlimited parallel trades, always active, record-only
  DEMO:   single slot, one trade at a time, simulated execution
  LIVE:   single slot, one trade at a time, strict risk checks, real orders

Cross-context: at route_setup time, snapshot all 6 systems' state.
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .risk_checks import passes_strict_checks
from .cooldown import CooldownManager, ClusterGuard
from .suffering_side_veto import SufferingSideVeto

logger = logging.getLogger(__name__)

DB_PATH = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"


class TradingGateway:
    """Central trade routing: SHADOW (unlimited) / DEMO (1 slot) / LIVE (1 slot + risk)."""

    def __init__(self, db_path: str = None, system_registry: Dict = None):
        self.db_path = db_path or DB_PATH
        self._system_registry = system_registry or {}
        self.shadow_trades: List[Dict] = []
        self.demo_slot: Optional[Dict] = None
        self.live_slot: Optional[Dict] = None
        self._demo_enabled_systems: set = set()
        self._live_enabled_systems: set = set()
        self._daily_trades: int = 0
        self._daily_pnl: float = 0.0
        self._consecutive_losses: int = 0
        # ζ.A4 + ζ.A5 + ζ.B2: risk filters
        self.cooldown = CooldownManager()
        self.cluster_guard = ClusterGuard()
        self.ssv = SufferingSideVeto()

    def set_system_registry(self, registry: Dict) -> None:
        """Inject system references for cross-context snapshots."""
        self._system_registry = registry

    def enable_demo(self, system_id: int) -> None:
        self._demo_enabled_systems.add(system_id)

    def disable_demo(self, system_id: int) -> None:
        self._demo_enabled_systems.discard(system_id)

    def enable_live(self, system_id: int) -> None:
        self._live_enabled_systems.add(system_id)

    def disable_live(self, system_id: int) -> None:
        self._live_enabled_systems.discard(system_id)

    def route_setup(self, setup: dict, system_id: int) -> Dict:
        """Route a trade setup through all 3 modes per spec section 8.

        Args:
            setup: Dict with firing_system, direction, classification,
                   confidence, stop, t1, t2, t3, entry_price, metadata.
            system_id: The firing system ID (1, 2, or 4).

        Returns:
            Dict summarizing what happened in each mode.
        """
        cross_context = self._capture_cross_context()
        result = {"shadow": None, "demo": None, "live": None, "blocked_by": None}

        # ζ.A5: Cluster guard — record attempt
        self.cluster_guard.record_attempt()

        # ζ.A4 + ζ.A5 + ζ.B2: pre-trade risk gates
        direction = setup.get("direction", "")
        if self.cooldown.is_blocked():
            result["blocked_by"] = "cooldown"
            logger.info("[Gateway] BLOCKED by 2-stop cooldown")
            return result
        if self.cluster_guard.is_blocked():
            result["blocked_by"] = "cluster_guard"
            logger.info("[Gateway] BLOCKED by cluster guard D-037")
            return result
        if self.ssv.check_veto(direction):
            result["blocked_by"] = "suffering_side_veto"
            logger.info("[Gateway] BLOCKED by SSV D-049: %s is suffering side", direction)
            return result

        # ζ.F2: Layer 0 chop gating
        chop_state = self._get_chop_state()
        if chop_state == "SEARCHING":
            result["blocked_by"] = "chop_searching"
            logger.info("[Gateway] BLOCKED by Layer 0: chop_state=SEARCHING (high chop)")
            return result

        # SHADOW: always log, unlimited slots
        shadow_trade = self._execute_shadow(setup, system_id, cross_context)
        self.shadow_trades.append(shadow_trade)
        if len(self.shadow_trades) > 500:
            self.shadow_trades = self.shadow_trades[-300:]
        result["shadow"] = shadow_trade["trade_id"]

        # DEMO: single slot
        if self._is_demo_enabled(system_id):
            if self.demo_slot is None:
                demo_trade = self._execute_demo(setup, system_id, cross_context)
                self.demo_slot = demo_trade
                result["demo"] = demo_trade["trade_id"]
            else:
                logger.info("[Gateway] DEMO slot occupied, skipping system %d setup", system_id)

        # LIVE: single slot + strict risk checks
        if self._is_live_enabled(system_id):
            if self.live_slot is None and passes_strict_checks(setup, "live", self):
                live_trade = self._execute_live(setup, system_id, cross_context)
                self.live_slot = live_trade
                result["live"] = live_trade["trade_id"]
            elif self.live_slot is not None:
                logger.info("[Gateway] LIVE slot occupied, skipping system %d setup", system_id)

        return result

    def _get_chop_state(self) -> str:
        """ζ.F2: Read Layer 0 chop state for gating."""
        try:
            import requests
            resp = requests.get("http://localhost:8000/api/v9/chop_score/current", timeout=2).json()
            score = resp.get("chop_score") or resp.get("composite_score")
            if score is None:
                return "UNKNOWN"
            if score >= 75:
                return "SEARCHING"
            elif score >= 50:
                return "RESPECTING"
            elif score >= 25:
                return "EXPANDING"
            else:
                return "FOUND"
        except Exception:
            return "UNKNOWN"

    def on_trade_close(self, trade: dict) -> None:
        """Handle trade closure — free slots, update daily stats, update risk filters."""
        trade_id = trade.get("trade_id")
        mode = trade.get("mode")
        pnl = trade.get("pnl_usd", 0.0)
        outcome = trade.get("outcome", "WIN" if pnl >= 0 else "STOP")
        direction = trade.get("direction", "")

        # ζ.A4: cooldown tracking
        self.cooldown.on_trade_close(outcome)
        # ζ.B2: SSV tracking
        self.ssv.record_outcome(direction, outcome)

        if self.demo_slot and self.demo_slot.get("trade_id") == trade_id:
            self.demo_slot = None
            logger.info("[Gateway] DEMO slot freed: %s", trade_id)

        if self.live_slot and self.live_slot.get("trade_id") == trade_id:
            self.live_slot = None
            self._daily_trades += 1
            self._daily_pnl += pnl
            if pnl < 0:
                self._consecutive_losses += 1
            else:
                self._consecutive_losses = 0
            logger.info("[Gateway] LIVE slot freed: %s pnl=%.2f", trade_id, pnl)

        # Persist exit
        self._persist_exit(trade)

    def reset_daily(self) -> None:
        """Reset daily counters (called at session start)."""
        self._daily_trades = 0
        self._daily_pnl = 0.0
        self._consecutive_losses = 0

    def get_status(self) -> dict:
        """Return gateway status for API."""
        return {
            "shadow_active_count": len(self.shadow_trades),
            "demo_slot": self.demo_slot.get("trade_id") if self.demo_slot else None,
            "demo_slot_system": self.demo_slot.get("firing_system") if self.demo_slot else None,
            "live_slot": self.live_slot.get("trade_id") if self.live_slot else None,
            "live_slot_system": self.live_slot.get("firing_system") if self.live_slot else None,
            "daily_pnl": round(self._daily_pnl, 2),
            "trades_today": self._daily_trades,
            "consecutive_losses": self._consecutive_losses,
            "demo_enabled_systems": sorted(self._demo_enabled_systems),
            "live_enabled_systems": sorted(self._live_enabled_systems),
            "cooldown": self.cooldown.get_state(),
            "cluster_guard": self.cluster_guard.get_state(),
            "ssv": self.ssv.get_state(),
            "chop_state": self._get_chop_state(),
        }

    # ── Internal ──

    def _is_demo_enabled(self, system_id: int) -> bool:
        return system_id in self._demo_enabled_systems

    def _is_live_enabled(self, system_id: int) -> bool:
        return system_id in self._live_enabled_systems

    def _execute_shadow(self, setup: dict, system_id: int, cross_context: dict) -> dict:
        """SHADOW: persist trade record only, no Sierra order."""
        trade = self._build_trade("shadow", setup, system_id, cross_context)
        self._persist_trade(trade)
        logger.info("[Gateway] SHADOW trade: %s %s system=%d",
                     trade["direction"], trade.get("classification", ""), system_id)
        return trade

    def _execute_demo(self, setup: dict, system_id: int, cross_context: dict) -> dict:
        """DEMO: log intent, persist — no Sierra connection yet."""
        trade = self._build_trade("demo", setup, system_id, cross_context)
        self._persist_trade(trade)
        logger.info("[Gateway] DEMO trade: %s %s system=%d",
                     trade["direction"], trade.get("classification", ""), system_id)
        return trade

    def _execute_live(self, setup: dict, system_id: int, cross_context: dict) -> dict:
        """LIVE: log intent, persist — no Sierra connection yet."""
        trade = self._build_trade("live", setup, system_id, cross_context)
        self._persist_trade(trade)
        logger.warning("[Gateway] LIVE trade (stub): %s %s system=%d — NOT sent to Sierra",
                        trade["direction"], trade.get("classification", ""), system_id)
        return trade

    def _build_trade(self, mode: str, setup: dict, system_id: int, cross_context: dict) -> dict:
        return {
            "trade_id": str(uuid.uuid4())[:12],
            "mode": mode,
            "firing_system": system_id,
            "direction": setup.get("direction", "LONG"),
            "classification": setup.get("classification", ""),
            "state": "OPEN",
            "entry_ts": datetime.now(timezone.utc).isoformat(),
            "entry_price": setup.get("entry_price"),
            "stop": setup.get("stop", 0.0),
            "t1": setup.get("t1", 0.0),
            "t2": setup.get("t2", 0.0),
            "t3": setup.get("t3", 0.0),
            "confidence": setup.get("confidence", 0.0),
            "cross_context": cross_context,
            "metadata": setup.get("metadata", {}),
        }

    def _capture_cross_context(self) -> dict:
        """Snapshot all 6 systems' current state."""
        ctx = {}
        for name, sys_ref in self._system_registry.items():
            try:
                if hasattr(sys_ref, "get_current"):
                    ctx[name] = sys_ref.get_current()
                elif hasattr(sys_ref, "current_state"):
                    ctx[name] = dict(sys_ref.current_state) if isinstance(sys_ref.current_state, dict) else {}
            except Exception:
                ctx[name] = {"error": "snapshot failed"}
        return ctx

    def _persist_trade(self, trade: dict) -> None:
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """INSERT INTO v9_trades
                (mode, firing_system, direction, state, entry_ts, entry_price,
                 stop, t1, t2, t3, cross_context, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    trade["mode"], trade["firing_system"], trade["direction"],
                    trade["state"], trade["entry_ts"], trade["entry_price"],
                    trade["stop"], trade["t1"], trade["t2"], trade["t3"],
                    json.dumps(trade["cross_context"]),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning("[Gateway] trade persist failed: %s", e)

    def _persist_exit(self, trade: dict) -> None:
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """UPDATE v9_trades SET state='CLOSED', exit_ts=?, exit_price=?,
                   exit_reason=?, pnl_usd=?, pnl_r=?, outcome=?, updated_at=?
                   WHERE mode=? AND entry_ts=? AND state='OPEN'""",
                (
                    trade.get("exit_ts"), trade.get("exit_price"),
                    trade.get("exit_reason"), trade.get("pnl_usd"),
                    trade.get("pnl_r"), trade.get("outcome"),
                    datetime.now(timezone.utc).isoformat(),
                    trade.get("mode"), trade.get("entry_ts"),
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning("[Gateway] exit persist failed: %s", e)
