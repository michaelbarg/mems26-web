"""System 3 — Footprint + Tick Reversal Engine (STANDALONE observer)."""
import json
import logging
import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any

from backend.v9.systems.base.trading_system import BaseV9TradingSystem, HydrationResult, SystemType
from .detectors import (
    detect_cluster, detect_empty_zones, analyze_context, compute_signals,
)

logger = logging.getLogger(__name__)


class FootprintSystem(BaseV9TradingSystem):
    system_id = 3
    name = "footprint"
    color = "#a855f7"
    system_type = SystemType.OBSERVING

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"
        self.bar_buffer: List[Dict[str, Any]] = []
        self.max_buffer = 30
        self.current_state = {
            "running": False,
            "hydrated": False,
            "last_classification": "NO_SETUP",
            "last_pattern": None,
            "last_confluence": 0,
            "bars_processed_today": 0,
            "buffer_size": 0,
        }

    def subscribed_bar_types(self) -> List[str]:
        return ["tick_reversal_15", "tick_reversal_12"]

    def hydrate(self) -> HydrationResult:
        self.current_state["running"] = True
        self.current_state["hydrated"] = True
        return HydrationResult(
            success=True,
            reached_state="ACTIVE",
            confidence=1.0,
            notes="Footprint observer ready; subscribed via BarRouter",
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
            self.current_state["last_classification"] = classification
            self.current_state["last_pattern"] = pattern
            self.current_state["last_confluence"] = confluence
            self.current_state["bars_processed_today"] += 1
            self.current_state["buffer_size"] = len(self.bar_buffer)
            mode = getattr(event, 'mode', 'LIVE')
            if mode == "LIVE":
                self._write_journal(event, bar, cluster, empty, ctx, pattern, signals, confluence, classification)
                if classification != "NO_SETUP":
                    self._write_setup(event, bar, classification, pattern, confluence)
        except Exception as e:
            logger.error(f"FootprintSystem.process_bar error: {e}", exc_info=True)

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
            conn = sqlite3.connect(self.db_path)
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
            conn.close()
        except Exception as e:
            logger.warning(f"Footprint journal write failed: {e}")

    def _write_setup(self, event, bar, classification, pattern, confluence):
        try:
            conn = sqlite3.connect(self.db_path)
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
            conn.close()
        except Exception as e:
            logger.warning(f"Footprint setup write failed: {e}")

    def get_current(self) -> dict:
        return dict(self.current_state)
