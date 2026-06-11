"""TradingGateway — 3-mode trade routing per 3-Mode Spec V3 section 8.

Modes:
  SHADOW: unlimited parallel trades, always active, record-only
  DEMO:   single slot, one trade at a time, simulated execution
  LIVE:   single slot, one trade at a time, strict risk checks, real orders

Cross-context: at route_setup time, snapshot all 6 systems' state.
"""

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .risk_checks import passes_strict_checks
from .cooldown import CooldownManager, ClusterGuard
from .suffering_side_veto import SufferingSideVeto
from backend.v9.services.sierra_command import command_from_setup
from backend.v9.gateway.session_gate import is_within_firing_window
from backend.v9.services.trade_context import extract_g1_entry_context


def resolve_pattern_id(setup: dict, g1: dict) -> Optional[str]:
    """Resolve pattern_id_at_entry: prefer the firing setup's classification.

    Bug fix (2026-06-12): g1 reads from woodies_system snapshot which reflects
    S4's active pattern. For S2 trades this produced wrong pattern_ids
    (id 43: REACTIVE_LONG recorded as VEGAS). Now: setup.classification first,
    metadata.pattern second, g1 fallback last.
    """
    return (
        setup.get("classification")
        or (setup.get("metadata") or {}).get("pattern")
        or g1.get("pattern_id_at_entry")
    ) or None

logger = logging.getLogger(__name__)

import os as _os
# Use the same DATABASE_URL as db/session.py — no more hardcoded path.
# Tests can override via DATABASE_URL or db_path constructor arg.
_DB_URL = _os.environ.get("DATABASE_URL", "sqlite:///./data/mems26_local.db")
DB_PATH = _DB_URL.replace("sqlite:///", "") if _DB_URL.startswith("sqlite") else "./data/mems26_local.db"


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
        self._trade_manager = None
        # D-094: R:R fire selection (flag OFF = first-wins, flag ON = same-bar buffering)
        import os
        self._rr_selection_enabled = os.environ.get(
            "RR_FIRE_SELECTION", ""
        ).lower() in ("1", "true", "yes")
        self._slot_candidates: List[Dict] = []  # buffered DEMO/LIVE candidates

    def set_system_registry(self, registry: Dict) -> None:
        """Inject system references for cross-context snapshots."""
        self._system_registry = registry

    def set_trade_manager(self, trade_manager) -> None:
        """W11 TradeManager — SHADOW lifecycle + PnL via BarLevelDetector."""
        self._trade_manager = trade_manager

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

        # B-13 D3: session firing gate — NO firing outside 08:30–15:00 CT in ANY mode
        if not is_within_firing_window():
            result["blocked_by"] = "session_gate_closed"
            logger.info("[Gateway] BLOCKED by session gate: outside 08:30–15:00 CT (all modes)")
            return result

        # ζ.A4 + ζ.A5 + ζ.B2 + ζ.F2: pre-trade risk gates (GW-02: no record_attempt before PASS)
        direction = setup.get("direction", "")
        if self.cooldown.is_blocked():
            result["blocked_by"] = "cooldown"
            logger.info("[Gateway] BLOCKED by 2-stop cooldown")
            return result
        if self.ssv.check_veto(direction):
            result["blocked_by"] = "suffering_side_veto"
            logger.info("[Gateway] BLOCKED by SSV D-049: %s is suffering side", direction)
            return result

        # Layer-0 chop fire-veto — DISABLED by default (Michael 2026-06-08).
        # chop_state==SEARCHING must NOT block fires until explicit re-approval.
        # Re-enable ONLY by setting env LAYER0_CHOP_GATE=1 AND with Michael's
        # explicit approval. See CLAUDE.md § "Chop Gates (disabled — approval to
        # re-enable)". When disabled we still compute + log chop_state for
        # observability, but do not block.
        _layer0_chop_enabled = os.getenv("LAYER0_CHOP_GATE", "0").lower() in ("1", "true", "yes")
        if _layer0_chop_enabled:
            chop_state = self._get_chop_state()
            if chop_state == "SEARCHING":
                result["blocked_by"] = "chop_searching"
                logger.info("[Gateway] BLOCKED by Layer 0: chop_state=SEARCHING (high chop)")
                return result
        # FIX 4: skip _get_chop_state entirely when gate disabled (avoids
        # HTTP self-calls that deadlock single-worker uvicorn)

        # D-088: cluster_guard blocks DEMO/LIVE only — SHADOW still records (3-Mode §8)
        cluster_blocked = self.cluster_guard.is_blocked()
        if not cluster_blocked:
            # ζ.A5: count only setups that passed cooldown/SSV/chop (GW-02)
            self.cluster_guard.record_attempt()

        # SHADOW: always log when past hard gates, unlimited slots
        shadow_trade = self._execute_shadow(setup, system_id, cross_context)
        self.shadow_trades.append(shadow_trade)
        if len(self.shadow_trades) > 500:
            self.shadow_trades = self.shadow_trades[-300:]
        result["shadow"] = shadow_trade["trade_id"]

        if cluster_blocked:
            result["blocked_by"] = "cluster_guard"
            logger.info(
                "[Gateway] SHADOW recorded; DEMO/LIVE blocked by cluster guard D-037"
            )
            return result

        # DEMO/LIVE: D-094 R:R selection or first-wins
        if self._rr_selection_enabled:
            # Buffer candidate for bar-close flush (slot NOT filled yet)
            candidate = {
                "setup": setup,
                "system_id": system_id,
                "cross_context": cross_context,
                "result_ref": result,
            }
            if self._is_demo_enabled(system_id) or self._is_live_enabled(system_id):
                if self.demo_slot is None or self.live_slot is None:
                    self._slot_candidates.append(candidate)
                    logger.info(
                        "[Gateway] D-094 buffered: system=%d classification=%s (awaiting bar-close flush)",
                        system_id, setup.get("classification", "?"),
                    )
                else:
                    logger.info("[Gateway] D-094: all slots occupied, skipping system %d", system_id)
        else:
            # Original first-wins logic (flag OFF)
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

    async def on_bar_close(self, event=None) -> None:
        """D-094: Flush buffered candidates at bar close — select winner by R:R.

        Called by BarRouter on new 5min bar (= previous bar closed).
        Only active when RR_FIRE_SELECTION flag is ON.
        """
        if not self._rr_selection_enabled or not self._slot_candidates:
            return

        from backend.v9.gateway.rr_score import compute_rr_score

        candidates = self._slot_candidates
        self._slot_candidates = []

        # Score each candidate
        scored = []
        for c in candidates:
            rr = compute_rr_score(c["setup"])
            confidence = c["setup"].get("confidence", 0.0)
            system_id = c["system_id"]
            scored.append((rr or 0.0, confidence, -system_id, c))

        # Sort: highest R:R → highest confidence → lowest system_id (tie-break)
        scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)

        winner = scored[0][3] if scored else None

        if winner:
            setup = winner["setup"]
            system_id = winner["system_id"]
            cross_context = winner["cross_context"]

            # DEMO slot fill
            if self._is_demo_enabled(system_id) and self.demo_slot is None:
                demo_trade = self._execute_demo(setup, system_id, cross_context)
                self.demo_slot = demo_trade
                logger.info(
                    "[Gateway] D-094 WINNER: system=%d R:R=%.2f classification=%s → DEMO slot filled",
                    system_id, scored[0][0], setup.get("classification", "?"),
                )

            # LIVE slot fill
            if self._is_live_enabled(system_id) and self.live_slot is None:
                if passes_strict_checks(setup, "live", self):
                    live_trade = self._execute_live(setup, system_id, cross_context)
                    self.live_slot = live_trade
                    logger.info(
                        "[Gateway] D-094 WINNER: system=%d R:R=%.2f → LIVE slot filled",
                        system_id, scored[0][0],
                    )

        # Log outranked candidates
        for i, (rr, conf, neg_sys, c) in enumerate(scored[1:], 1):
            logger.info(
                "[Gateway] D-094 OUTRANKED #%d: system=%d R:R=%.2f classification=%s",
                i, c["system_id"], rr, c["setup"].get("classification", "?"),
            )

    def _get_chop_state(self) -> str:
        """ζ.F2: Read Layer 0 chop state for gating (direct compute — no self-HTTP)."""
        try:
            from backend.v9.systems.layer0.chop_score import get_chop_score

            data = get_chop_score()
            state = data.get("state")
            if state:
                return str(state)
            score = data.get("chop_score")
            if score is None:
                return "UNKNOWN"
            from backend.v9.systems.layer0.chop_score import classify_state

            return classify_state(float(score))
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
        """SHADOW: TradeManager row + auto-close on 5min bars (PnL in v9_trades)."""
        if self._trade_manager is not None:
            entry = setup.get("entry_price")
            # G1: extract queryable columns from the SAME cross_context snapshot
            g1 = extract_g1_entry_context(cross_context)
            tm_setup = {
                "firing_system": system_id,
                "direction": setup.get("direction", "LONG"),
                "stop": setup.get("stop", 0.0),
                "t1": setup.get("t1", 0.0),
                "t2": setup.get("t2", 0.0),
                "t3": setup.get("t3", 0.0),
                "entry_price": entry,
                "classification": setup.get("classification", ""),
                "confidence": setup.get("confidence", 0.0),
                "metadata": setup.get("metadata") or {},
                "trigger": (
                    setup.get("classification")
                    or (setup.get("metadata") or {}).get("pattern")
                    or (setup.get("metadata") or {}).get("signal")
                ),
                "cross_context": cross_context,
                # G1 promoted columns
                "day_type_at_entry": g1["day_type_at_entry"],
                "pattern_id_at_entry": resolve_pattern_id(setup, g1),
                "session_at_entry": g1["session_at_entry"],
            }
            trade_id = self._trade_manager.accept_setup(tm_setup, "shadow")
            if entry is not None:
                self._trade_manager.on_fill(trade_id, float(entry))
            try:
                self._trade_manager._db.commit()
            except Exception as commit_err:
                logger.warning("[Gateway] SHADOW trade commit failed: %s", commit_err)
            logger.info(
                "[Gateway] SHADOW trade TM id=%d: %s %s system=%d",
                trade_id, tm_setup["direction"], setup.get("classification", ""), system_id,
            )
            return {
                "trade_id": str(trade_id),
                "mode": "shadow",
                "firing_system": system_id,
                "direction": tm_setup["direction"],
                "state": "FILLED",
                "entry_price": entry,
                "entry_ts": datetime.now(timezone.utc).isoformat(),
            }

        trade = self._build_trade("shadow", setup, system_id, cross_context)
        self._persist_trade(trade)
        logger.info("[Gateway] SHADOW trade (legacy persist): %s system=%d",
                     trade["direction"], system_id)
        return trade

    def _execute_demo(self, setup: dict, system_id: int, cross_context: dict) -> dict:
        """DEMO: persist and write Sierra SIM command file."""
        trade = self._build_trade("demo", setup, system_id, cross_context)
        self._persist_trade(trade)
        command = command_from_setup(
            setup,
            trade_id=trade["trade_id"],
            account="PA-APEX-125218-01",
            mode="demo",
        )
        trade["sierra_command"] = command
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
        # G1: extract queryable columns from the SAME cross_context snapshot
        g1 = extract_g1_entry_context(cross_context)
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
            # G1 promoted columns
            "day_type_at_entry": g1["day_type_at_entry"],
            "pattern_id_at_entry": resolve_pattern_id(setup, g1),
            "session_at_entry": g1["session_at_entry"],
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
        from backend.v9.db.safe_writer import safe_execute
        safe_execute(
            """INSERT INTO v9_trades
            (mode, firing_system, direction, state, entry_ts, entry_price,
             stop, t1, t2, t3, cross_context,
             day_type_at_entry, pattern_id_at_entry, session_at_entry,
             created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                trade["mode"], trade["firing_system"], trade["direction"],
                trade["state"], trade["entry_ts"], trade["entry_price"],
                trade["stop"], trade["t1"], trade["t2"], trade["t3"],
                json.dumps(trade["cross_context"], default=str),
                trade.get("day_type_at_entry"),
                trade.get("pattern_id_at_entry"),
                trade.get("session_at_entry"),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    def _persist_exit(self, trade: dict) -> None:
        from backend.v9.db.safe_writer import safe_execute
        safe_execute(
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
