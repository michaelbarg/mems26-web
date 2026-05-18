"""System 3 — Footprint + Tick Reversal Engine (FIRING per Constitution V3 T3)."""
import json
import logging
import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any

from backend.v9.systems.base.trading_system import BaseV9TradingSystem, HydrationResult, SystemType
from backend.v9.shared.pre_fire_validator import FireRequest, validate_fire
from .detectors import (
    detect_cluster, detect_empty_zones, analyze_context, compute_signals,
)
from .signals import detect_absorption, detect_stacked_imbalance, detect_sweep_return, detect_exhaustion

logger = logging.getLogger(__name__)


class FootprintSystem(BaseV9TradingSystem):
    system_id = 3
    name = "footprint"
    color = "#a855f7"
    system_type = SystemType.FIRING

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"
        self._conn: Optional[sqlite3.Connection] = None
        self._gateway = None  # injected post-init via set_gateway() (Prompt 22-alt)
        self.bar_buffer: List[Dict[str, Any]] = []
        self.max_buffer = 30
        # Aggressive flow tracking (P-FP-1 v3)
        self._last_forces: Optional[Dict] = None
        self._last_forces_source: Optional[str] = None
        self._last_delta: Optional[float] = None
        self._last_dominance: Optional[str] = None
        self._cumulative_delta: float = 0
        self._last_amt: Optional[float] = None
        self._total_vol: float = 0
        self._total_trades: int = 0
        # Initiative/Reactive (P-FP-2)
        self._recent_bars: List[Dict] = []
        self._last_initiative_type: Optional[str] = None
        self._last_reactive: Optional[bool] = None
        self._last_combined_class: Optional[str] = None
        self.current_state = {
            "running": False,
            "hydrated": False,
            "last_classification": "NO_SETUP",
            "last_pattern": None,
            "last_confluence": 0,
            "bars_processed_today": 0,
            "buffer_size": 0,
            "aggressive_flow": None,
            "forces_source": None,
            "delta": None,
            "cumulative_delta": 0,
            "dominance": None,
            "cot": 0,
            "amt": None,
            "initiative_type": None,
            "reactive_flag": None,
            "combined_class": None,
        }

    def _get_conn(self) -> sqlite3.Connection:
        """Reuse a single WAL-mode connection to avoid per-bar open/close overhead."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, timeout=5)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=3000")
        return self._conn

    def set_gateway(self, gateway) -> None:
        """Inject TradingGateway for validated T3 fire routing."""
        self._gateway = gateway

    def subscribed_bar_types(self) -> List[str]:
        return ["tick_reversal_15", "tick_reversal_12"]

    def hydrate(self) -> HydrationResult:
        self.current_state["running"] = True
        self.current_state["hydrated"] = True

        # P-WAVE-D3: Restore cumulative_delta from last journal entry
        # W1.1: use self.db_path (absolute) instead of __file__ relative traversal
        restored_delta = 0.0
        try:
            import sqlite3 as _sql
            conn = _sql.connect(self.db_path)
            row = conn.execute(
                "SELECT cumulative_delta FROM v9_footprint_journal ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row and row[0]:
                restored_delta = float(row[0])
                self._cumulative_delta = restored_delta
                self.current_state["cumulative_delta"] = restored_delta
                self.current_state["cot"] = restored_delta
            # Also count today's bars for context
            count = conn.execute(
                "SELECT COUNT(*) FROM v9_footprint_journal WHERE date(created_at) = date('now')"
            ).fetchone()[0]
            conn.close()
            logger.info("[Footprint] Hydrated: cumulative_delta=%.1f, today_bars=%d",
                        restored_delta, count)
        except Exception as e:
            logger.warning("[Footprint] Hydration restore failed: %s", e)

        return HydrationResult(
            success=True,
            reached_state="ACTIVE",
            confidence=1.0,
            notes=f"Footprint ready; cumulative_delta restored to {restored_delta:.1f}",
        )

    def process(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return None

    async def process_bar(self, event) -> None:
        try:
            bar = dict(event.payload) if hasattr(event, 'payload') else dict(event)
            self.bar_buffer.append(bar)
            if len(self.bar_buffer) > self.max_buffer:
                self.bar_buffer.pop(0)
            footprint = bar.get("footprint", {})
            cluster = detect_cluster(footprint)
            empty = detect_empty_zones(footprint)
            ctx = analyze_context(self.bar_buffer)
            signals = compute_signals(bar, self.bar_buffer)
            pattern = self._detect_pattern(ctx)
            confluence = sum([
                int(cluster.has_cluster),
                int(empty.has_empty),
                int(ctx.accumulation),
                int(ctx.jumps_count >= 3),
                int(ctx.otf_state in (2, 3)),
            ]) + sum(int(v) for v in signals.values())
            classification = self._classify(confluence, pattern)

            # Aggressive flow (P-FP-1 v3)
            self._update_flow(bar)

            self.current_state["last_classification"] = classification
            self.current_state["last_pattern"] = pattern
            self.current_state["last_confluence"] = confluence
            self.current_state["bars_processed_today"] += 1
            self.current_state["buffer_size"] = len(self.bar_buffer)
            self.current_state["aggressive_flow"] = self._last_forces
            self.current_state["forces_source"] = self._last_forces_source
            self.current_state["delta"] = self._last_delta
            self.current_state["cumulative_delta"] = self._cumulative_delta
            self.current_state["dominance"] = self._last_dominance
            self.current_state["cot"] = self._cumulative_delta
            self.current_state["amt"] = self._last_amt

            # Initiative/Reactive (P-FP-2.2)
            init_type, reactive, combined = self._classify_initiative_reactive(bar)
            self._last_initiative_type = init_type
            self._last_reactive = reactive
            self._last_combined_class = combined
            self._recent_bars.append(bar)
            if len(self._recent_bars) > 20:
                self._recent_bars = self._recent_bars[-20:]
            self.current_state["initiative_type"] = init_type
            self.current_state["reactive_flag"] = reactive
            self.current_state["combined_class"] = combined
            # T3 Firing: check absorption + stacked imbalance signals
            t3_signal = self._check_firing_signals(bar)
            if t3_signal:
                self.current_state["last_signal"] = t3_signal

            mode = getattr(event, 'mode', 'LIVE')
            if mode == "LIVE":
                self._write_journal(event, bar, cluster, empty, ctx, pattern, signals, confluence, classification)
                if classification != "NO_SETUP":
                    self._write_setup(event, bar, classification, pattern, confluence)
                # T3: Fire if signal detected and size != reject
                if t3_signal:
                    self._fire(t3_signal, bar, event)
        except Exception as e:
            logger.error(f"FootprintSystem.process_bar error: {e}", exc_info=True)

    def _classify_initiative_reactive(self, bar: dict) -> tuple:
        """Initiative vs Reactive per MP_SPEC_V1. (P-FP-2.2)"""
        lookback = self._recent_bars[-10:] if len(self._recent_bars) >= 10 else self._recent_bars
        if not lookback or len(lookback) < 5:
            return ("NEUTRAL", True, "BALANCED")
        prev_max_high = max(b.get("high", b.get("h", 0)) for b in lookback)
        prev_min_low = min(b.get("low", b.get("l", float('inf'))) for b in lookback)
        cur_high = bar.get("high", bar.get("h", 0))
        cur_low = bar.get("low", bar.get("l", 0))
        if cur_high > prev_max_high:
            init_type, reactive = "INITIATIVE_UP", False
        elif cur_low < prev_min_low:
            init_type, reactive = "INITIATIVE_DOWN", False
        else:
            init_type, reactive = "NEUTRAL", True
        dom = self._last_dominance
        if init_type == "INITIATIVE_UP" and dom == "BUYER_DOMINATE":
            combined = "BUYER_INITIATIVE"
        elif init_type == "INITIATIVE_DOWN" and dom == "SELLER_DOMINATE":
            combined = "SELLER_INITIATIVE"
        elif reactive and dom == "BUYER_DOMINATE":
            combined = "BUYER_REACTIVE"
        elif reactive and dom == "SELLER_DOMINATE":
            combined = "SELLER_REACTIVE"
        else:
            combined = "BALANCED"
        return (init_type, reactive, combined)

    def _classify_forces_in_bar(self, bar: dict) -> Optional[Dict]:
        """Map Sierra ask_vol/bid_vol to aggressive flow. Passive = NULL (no L2)."""
        ask_vol = bar.get("ask_vol")
        bid_vol = bar.get("bid_vol")
        if ask_vol is None or bid_vol is None:
            return None
        return {
            "agg_buy_vol": float(ask_vol or 0),
            "agg_sell_vol": float(bid_vol or 0),
            "pas_buy_vol": None,
            "pas_sell_vol": None,
            "source": "SIERRA_AGG_ONLY",
        }

    def _update_flow(self, bar: dict) -> None:
        """Compute dominance + delta + COT + AMT from aggressive flow."""
        forces = self._classify_forces_in_bar(bar)
        if forces is None:
            self._last_forces = None
            self._last_delta = None
            self._last_dominance = None
            return
        self._last_forces = forces
        self._last_forces_source = forces["source"]

        agg_buy = forces["agg_buy_vol"]
        agg_sell = forces["agg_sell_vol"]
        delta = agg_buy - agg_sell
        self._cumulative_delta += delta
        self._last_delta = delta

        if agg_buy > 1.5 * agg_sell and agg_buy > 0:
            self._last_dominance = "BUYER_DOMINATE"
        elif agg_sell > 1.5 * agg_buy and agg_sell > 0:
            self._last_dominance = "SELLER_DOMINATE"
        else:
            self._last_dominance = "BALANCED"

        trade_count = int(bar.get("trade_count") or bar.get("ticks_count") or bar.get("n") or 1)
        total_vol = float(bar.get("v") or bar.get("volume") or 0)
        self._last_amt = total_vol / max(trade_count, 1)
        self._total_vol += total_vol
        self._total_trades += trade_count

    def _detect_pattern(self, ctx) -> Optional[str]:
        if ctx.accumulation and ctx.jumps_count >= 3:
            return "ACCUMULATION_BREAKOUT"
        return None

    def _classify(self, confluence: int, pattern: Optional[str]) -> str:
        if confluence >= 6 and pattern:
            return "STRATEGIC"
        if confluence >= 4 and pattern:
            return "TACTICAL"
        return "NO_SETUP"

    def _write_journal(self, event, bar, cluster, empty, ctx, pattern, signals, confluence, classification):
        try:
            conn = self._get_conn()
            conn.execute(
                "INSERT OR IGNORE INTO v9_footprint_journal (ts, bar_id, cluster_data, empty_zone_data, accumulation, jumps_count, jumps_direction, otf_state, pattern_detected, zohar_signals, industry_signals, confluence_total, classification, session, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    getattr(event, 'ts', ''), getattr(event, 'bar_id', ''),
                    json.dumps({"poc": cluster.yellow_poc_price, "pct": cluster.yellow_poc_pct}),
                    json.dumps(empty.zones),
                    int(ctx.accumulation), ctx.jumps_count, ctx.jumps_direction,
                    ctx.otf_state, pattern,
                    json.dumps({k: v for k, v in signals.items() if k in ["belly_ratio_dominant", "vol_drop_90pct", "cot_vs_amt_clear", "tick_breach", "poc_migration"]}),
                    json.dumps({k: v for k, v in signals.items() if k in ["imbalance_250", "stacked_imbalance_3plus", "cumulative_delta_aligned", "exhaustion_zone", "liquidity_sweep"]}),
                    confluence, classification,
                    getattr(event, 'session', 'UNKNOWN'),
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
        except Exception as e:
            logger.warning(f"Footprint journal write failed: {e}")
            self._conn = None

    def _write_setup(self, event, bar, classification, pattern, confluence):
        try:
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO v9_footprint_setups (ts, classification, pattern_type, direction, confluence, entry_price, stop_price, session, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    getattr(event, 'ts', ''), classification, pattern,
                    "LONG" if bar.get("close", 0) > bar.get("open", 0) else "SHORT",
                    confluence, bar.get("close"), bar.get("low"),
                    getattr(event, 'session', 'UNKNOWN'),
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
        except Exception as e:
            logger.warning(f"Footprint setup write failed: {e}")
            self._conn = None

    # ── T3 Firing: Absorption + Stacked Imbalance (Wave S3-T3) ──

    def _check_firing_signals(self, bar: dict) -> Optional[Dict]:
        """Run T3 signal detectors. Returns strongest signal or None."""
        footprint_levels = bar.get("footprint", {}).get("levels", [])

        candidates = []

        # Absorption: uses bar buffer (last N bars)
        absorption = detect_absorption(self.bar_buffer, bar)
        if absorption:
            candidates.append(absorption)

        # Stacked Imbalance: uses footprint cell levels from current bar
        stacked = detect_stacked_imbalance(footprint_levels, bar)
        if stacked:
            candidates.append(stacked)

        # Sweep-Return: liquidity sweep through extreme + return inside range
        sweep = detect_sweep_return(self.bar_buffer, bar)
        if sweep:
            candidates.append(sweep)

        # Exhaustion: directional bar with diminishing volume
        exhaustion = detect_exhaustion(self.bar_buffer, bar)
        if exhaustion:
            candidates.append(exhaustion)

        if not candidates:
            return None

        # Return strongest signal by strength
        return max(candidates, key=lambda s: s["strength"])

    def calculate_size(self, signal: dict) -> str:
        """System 3 per-system internal sizing — Footprint inputs ONLY.

        NO composite cross-system formula (CORR-23 enforced).
        Uses ONLY: signal strength, delta alignment, dominance, initiative type.

        Returns: 'full' (3 contracts) | 'half' (2) | 'reject' (0)
        """
        strength = signal.get("strength", 0)
        direction = signal.get("direction")
        if not direction or strength <= 0:
            return "reject"

        # Delta alignment: cumulative delta supports direction
        delta = self._cumulative_delta or 0
        delta_aligned = (delta > 0 and direction == "LONG") or (delta < 0 and direction == "SHORT")

        # Dominance alignment
        dom = self._last_dominance or "BALANCED"
        dom_aligned = (dom == "BUYER_DOMINATE" and direction == "LONG") or \
                      (dom == "SELLER_DOMINATE" and direction == "SHORT")

        # Initiative alignment
        init = self._last_initiative_type or "NEUTRAL"
        init_aligned = (init == "INITIATIVE_UP" and direction == "LONG") or \
                       (init == "INITIATIVE_DOWN" and direction == "SHORT")

        aux_count = sum([delta_aligned, dom_aligned, init_aligned])

        # Decision tree (per-system, like S2/S4 Wave H pattern)
        if strength >= 0.6 and aux_count >= 3:
            return "full"    # 3 contracts — pristine
        elif strength >= 0.4 and aux_count >= 2:
            return "half"    # 2 contracts — solid
        elif strength >= 0.3 and aux_count >= 1:
            return "half"    # 2 contracts — acceptable
        else:
            return "reject"

    def _fire(self, signal: dict, bar: dict, event) -> None:
        """Fire a trade decision from Footprint signal + size."""
        size = self.calculate_size(signal)
        if size == "reject":
            return

        # ζ.H1: reasoning_notes (AP-SY02)
        reasoning_notes = (f"{signal['signal']} {signal['direction']} size={size}: "
                           f"strength={signal.get('strength', 0):.2f}, "
                           f"delta_aligned={'Y' if (self._cumulative_delta or 0) > 0 and signal['direction'] == 'LONG' or (self._cumulative_delta or 0) < 0 and signal['direction'] == 'SHORT' else 'N'}, "
                           f"dom={self._last_dominance}, init={self._last_initiative_type}")

        self._last_fire = {
            "signal": signal["signal"],
            "direction": signal["direction"],
            "size": size,
            "qty": 3 if size == "full" else 2,
            "level": signal.get("level"),
            "strength": signal.get("strength"),
            "evidence": signal.get("evidence"),
            "reasoning_notes": reasoning_notes,
            "ts": datetime.utcnow().isoformat(),
        }
        pre_fire_req = self._build_pre_fire_request(signal, bar)
        pre_fire = validate_fire(pre_fire_req)
        self._last_fire["pre_fire"] = self._serialize_pre_fire(pre_fire)
        if not pre_fire.valid:
            self._last_fire["routed"] = False
            self._last_fire["blocked_by"] = "pre_fire_validator"
            self._last_fire["route_reason"] = pre_fire.fail_reason
            self.current_state["last_fire"] = self._last_fire
            self.current_state["last_reasoning_notes"] = reasoning_notes
            logger.info("[Footprint] FIRE blocked by pre_fire_validator: %s", pre_fire.fail_reason)
            return

        gateway_payload = self._build_gateway_payload(signal, bar, size, pre_fire_req)
        self._last_fire["gateway_setup"] = gateway_payload
        if self._gateway is None:
            self._last_fire["routed"] = False
            self._last_fire["blocked_by"] = "trading_gateway"
            self._last_fire["route_reason"] = "TradingGateway not injected"
            self.current_state["last_fire"] = self._last_fire
            self.current_state["last_reasoning_notes"] = reasoning_notes
            logger.info("[Footprint] FIRE validated but no gateway injected: %s", signal["signal"])
            return

        try:
            gateway_result = self._gateway.route_setup(gateway_payload, 3)
            self._last_fire["routed"] = True
            self._last_fire["blocked_by"] = gateway_result.get("blocked_by") if isinstance(gateway_result, dict) else None
            self._last_fire["route_reason"] = (
                self._last_fire["blocked_by"] or "routed_to_trading_gateway"
            )
            self._last_fire["gateway"] = gateway_result
            logger.info("[Footprint] FIRE routed to gateway: %s %s size=%s",
                        signal["signal"], signal["direction"], size)
        except Exception as gw_err:
            self._last_fire["routed"] = False
            self._last_fire["blocked_by"] = "trading_gateway"
            self._last_fire["route_reason"] = str(gw_err)
            logger.warning("[Footprint] Gateway route_setup failed: %s", gw_err)

        self.current_state["last_fire"] = self._last_fire
        self.current_state["last_reasoning_notes"] = reasoning_notes

        # Persist to DB
        try:
            conn = self._get_conn()
            conn.execute(
                """INSERT INTO v9_footprint_setups
                (ts, bar_id, classification, pattern, confluence, entry_price, stop_price, session, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    datetime.utcnow().isoformat(),
                    getattr(event, 'bar_id', None),
                    f"FIRE_{signal['signal'].upper()}",
                    signal["signal"],
                    int(signal["strength"] * 10),
                    signal.get("level"),
                    None,
                    getattr(event, 'session', 'UNKNOWN'),
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
            logger.info("[Footprint] FIRE: %s %s size=%s strength=%.2f",
                        signal["signal"], signal["direction"], size, signal["strength"])
        except Exception as e:
            logger.warning("[Footprint] Fire persist failed: %s", e)
            self._conn = None

    def _build_pre_fire_request(self, signal: dict, bar: dict) -> FireRequest:
        direction = signal["direction"]
        entry = float(signal.get("level") or bar.get("close", bar.get("c", 0)) or 0)
        high = float(bar.get("high", bar.get("h", entry)) or entry)
        low = float(bar.get("low", bar.get("l", entry)) or entry)
        tick = float(bar.get("tick_size", 0.25) or 0.25)

        if direction == "LONG":
            stop = min(low, entry - tick)
            risk = max(entry - stop, tick)
            t1 = entry + risk
            t2 = entry + (2 * risk)
        else:
            stop = max(high, entry + tick)
            risk = max(stop - entry, tick)
            t1 = entry - risk
            t2 = entry - (2 * risk)

        confidence = max(0, min(100, int(round(float(signal.get("strength", 0)) * 100))))
        return FireRequest(
            system_id="T3_FOOTPRINT",
            direction=direction,
            entry_price=entry,
            stop_price=stop,
            t1_price=t1,
            t2_price=t2,
            time_stop_minutes=15,
            confidence=confidence,
        )

    def _build_gateway_payload(self, signal: dict, bar: dict, size: str, pre_fire_req: FireRequest) -> dict:
        return {
            "firing_system": 3,
            "direction": signal["direction"],
            "classification": f"FIRE_{signal['signal'].upper()}",
            "confidence": pre_fire_req.confidence / 100.0,
            "entry_price": pre_fire_req.entry_price,
            "stop": pre_fire_req.stop_price,
            "t1": pre_fire_req.t1_price,
            "t2": pre_fire_req.t2_price,
            "t3": 0.0,
            "metadata": {
                "source": "footprint_auto_fire",
                "signal": signal["signal"],
                "size": size,
                "qty": 3 if size == "full" else 2,
                "level": signal.get("level"),
                "evidence": signal.get("evidence"),
                "bar_id": bar.get("bar_id"),
            },
        }

    def _serialize_pre_fire(self, pre_fire) -> dict:
        if hasattr(pre_fire, "model_dump"):
            return pre_fire.model_dump()
        return pre_fire.dict()

    def get_current(self) -> dict:
        state = dict(self.current_state)
        state["last_fire"] = getattr(self, '_last_fire', None)
        return state
