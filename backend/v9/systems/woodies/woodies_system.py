"""System 4 — Woodies CCI Decision Maker (30-min bars + 8 patterns).

Subscribes to woodies_30min bars via BarRouter (D-048).
Computes all 11 Woodies studies per bar via cci_calc.compute_all_studies().
Runs 8-pattern engine (ZLR, TLB, TT, GB100, VEGAS, GHOST, FAMIR, HTLB).
Publishes signal events independently.
"""
import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional, Dict

from backend.v9.systems.base.trading_system import BaseV9TradingSystem, HydrationResult, SystemType
from backend.v9.systems.woodies.cci_calc import compute_all_studies
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult
from backend.v9.systems.woodies.pattern_engine import detect_all_patterns, PATTERN_IDS

logger = logging.getLogger(__name__)


class WoodiesSystem(BaseV9TradingSystem):
    system_id = 4
    name = "woodies"
    color = "#f97316"
    system_type = SystemType.FIRING

    def __init__(self, db_path: str = None):
        self.db_path = db_path or "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"
        # Raw OHLCV buffers for study computation
        self._highs: List[float] = []
        self._lows: List[float] = []
        self._closes: List[float] = []
        self._bar_buffer: List[WoodiesBar] = []
        self.max_buffer = 50
        self._active_patterns: List[PatternResult] = []
        self.current_state: Dict = {
            "running": False,
            "hydrated": False,
            "cci_14": None,
            "cci_6_tcci": None,
            "ema_34": None,
            "lsma_value": None,
            "swi_value": None,
            "czi_value": None,
            "trend_state": "GRAY",
            "predictor_next_cci": None,
            "signal": "NEUTRAL",
            "direction": None,
            "strength": 0,
            "buffer_size": 0,
            "active_patterns": [],
            "classification": "NO_SETUP",
        }

    def subscribed_bar_types(self) -> List[str]:
        return ["woodies_30min"]

    def hydrate(self) -> HydrationResult:
        """Load last N bars from v9_bars_30min_woodies for warm start."""
        loaded = 0
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM v9_bars_30min_woodies ORDER BY ts DESC LIMIT ?",
                (self.max_buffer,),
            ).fetchall()
            conn.close()

            # Reverse to oldest-first
            for row in reversed(rows):
                r = dict(row)
                self._highs.append(float(r["high"]))
                self._lows.append(float(r["low"]))
                self._closes.append(float(r["close"]))
                wb = WoodiesBar(
                    ts=0,  # historical, no exact epoch needed
                    open=float(r["open"]),
                    high=float(r["high"]),
                    low=float(r["low"]),
                    close=float(r["close"]),
                    volume=float(r.get("volume", 0)),
                    cci_14=float(r.get("cci_14") or 0),
                    cci_6_tcci=float(r.get("cci_6_tcci") or 0),
                    ema_34=float(r.get("ema_34") or 0),
                    lsma_value=float(r.get("lsma_value") or 0),
                    swi_value=float(r.get("swi_value") or 0),
                    czi_value=float(r.get("czi_value") or 0),
                    trend_state=r.get("trend_state") or "GRAY",
                    predictor_next_cci=float(r.get("predictor_next_cci") or 0),
                )
                self._bar_buffer.append(wb)
                loaded += 1
        except Exception as e:
            logger.warning("[Woodies] Hydration from DB failed (non-fatal): %s", e)

        self.current_state["running"] = True
        self.current_state["hydrated"] = True
        self.current_state["buffer_size"] = len(self._bar_buffer)

        # Recompute current studies from buffer if we have data
        if self._bar_buffer:
            last = self._bar_buffer[-1]
            self.current_state.update({
                "cci_14": last.cci_14,
                "cci_6_tcci": last.cci_6_tcci,
                "trend_state": last.trend_state,
            })

        return HydrationResult(
            success=True,
            reached_state="ACTIVE",
            confidence=1.0,
            notes=f"Woodies CCI ready; hydrated {loaded} bars from DB; subscribed to woodies_30min",
        )

    def process(self, event: Dict) -> Optional[Dict]:
        return None

    async def process_bar(self, event) -> None:
        """Process a 30-min bar: compute studies, detect patterns, persist."""
        try:
            bar = dict(event.payload) if hasattr(event, 'payload') else dict(event)

            h = float(bar.get("high", bar.get("h", 0)))
            l = float(bar.get("low", bar.get("l", 0)))
            c = float(bar.get("close", bar.get("c", 0)))
            o = float(bar.get("open", bar.get("o", 0)))
            v = float(bar.get("volume", bar.get("v", 0)))

            # Append to OHLCV buffers
            self._highs.append(h)
            self._lows.append(l)
            self._closes.append(c)

            # Trim buffers
            if len(self._highs) > self.max_buffer:
                self._highs = self._highs[-self.max_buffer:]
                self._lows = self._lows[-self.max_buffer:]
                self._closes = self._closes[-self.max_buffer:]

            # Compute all 11 studies using full price history
            studies = compute_all_studies(self._highs, self._lows, self._closes)

            # Build WoodiesBar for pattern engine
            bar_ts = bar.get("ts", 0)
            if isinstance(bar_ts, str):
                try:
                    bar_ts = datetime.fromisoformat(bar_ts.replace("Z", "+00:00")).timestamp()
                except Exception:
                    bar_ts = 0

            wb = WoodiesBar(
                ts=float(bar_ts),
                open=o, high=h, low=l, close=c, volume=v,
                **studies,
            )
            self._bar_buffer.append(wb)
            if len(self._bar_buffer) > self.max_buffer:
                self._bar_buffer = self._bar_buffer[-self.max_buffer:]

            # Run 8-pattern engine
            patterns = detect_all_patterns(self._bar_buffer)
            self._active_patterns = patterns

            # Classify overall state
            signal = "NEUTRAL"
            direction = None
            strength = 0
            classification = "NO_SETUP"

            if patterns:
                # Highest-confidence pattern wins
                best = max(patterns, key=lambda p: p.confidence)
                signal = best.pattern_id
                direction = best.direction
                strength = int(best.confidence * 4)
                classification = "STRATEGIC" if best.group == "REVERSAL" else "TACTICAL"

            # Update current state
            self.current_state.update({
                "cci_14": studies["cci_14"],
                "cci_6_tcci": studies["cci_6_tcci"],
                "ema_34": studies["ema_34"],
                "lsma_value": studies["lsma_value"],
                "swi_value": studies["swi_value"],
                "czi_value": studies["czi_value"],
                "trend_state": studies["trend_state"],
                "predictor_next_cci": studies["predictor_next_cci"],
                "signal": signal,
                "direction": direction,
                "strength": strength,
                "buffer_size": len(self._bar_buffer),
                "classification": classification,
                "active_patterns": [
                    {
                        "pattern_id": p.pattern_id,
                        "direction": p.direction,
                        "confidence": round(p.confidence, 3),
                        "group": p.group,
                        "entry_price": p.entry_price,
                        "stop": p.stop,
                        "targets": p.targets,
                    }
                    for p in patterns
                ],
            })

            # Persist patterns to DB (LIVE mode only)
            mode = getattr(event, 'mode', bar.get('mode', 'LIVE'))
            if mode == "LIVE":
                self._persist_bar(bar_ts, o, h, l, c, v, studies)
                for p in patterns:
                    self._persist_pattern(bar_ts, event, studies, p)

        except Exception as e:
            logger.error("[Woodies] process_bar error: %s", e, exc_info=True)

    def _persist_bar(self, ts, o, h, l, c, v, studies):
        """Write enriched bar to v9_bars_30min_woodies."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """INSERT INTO v9_bars_30min_woodies
                (ts, symbol, open, high, low, close, volume,
                 cci_14, cci_6_tcci, lsma_value, swi_value, czi_value,
                 ema_34, trend_state, predictor_next_cci, zlr_detected, zlr_direction)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    datetime.now(timezone.utc).isoformat(), "MES",
                    o, h, l, c, int(v),
                    studies["cci_14"], studies["cci_6_tcci"],
                    studies["lsma_value"], studies["swi_value"], studies["czi_value"],
                    studies["ema_34"], studies["trend_state"], studies["predictor_next_cci"],
                    False, "NONE",
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning("[Woodies] Bar persist failed: %s", e)

    def _persist_pattern(self, bar_ts, event, studies, pattern: PatternResult):
        """Write detected pattern to v9_woodies_signals."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """INSERT INTO v9_woodies_signals
                (ts, bar_id, cci_14, cci_prev, signal_type, direction, strength,
                 reasoning, session, created_at,
                 czi_state, swi_state, persistence_bars,
                 signal_type_core, signal_confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    datetime.now(timezone.utc).isoformat(),
                    None,
                    studies["cci_14"],
                    None,
                    pattern.pattern_id,
                    pattern.direction,
                    int(pattern.confidence * 4),
                    f"{pattern.pattern_id} {pattern.direction} conf={pattern.confidence:.2f} "
                    f"CCI={studies['cci_14']:.1f} trend={studies['trend_state']}",
                    getattr(event, 'session', 'UNKNOWN'),
                    datetime.now(timezone.utc).isoformat(),
                    "CZI" if abs(studies["cci_14"]) < 100 else "TREND_ZONE",
                    "SWI" if abs(studies["cci_14"]) >= 200 else "NORMAL",
                    len(self._bar_buffer),
                    pattern.pattern_id,
                    pattern.confidence,
                ),
            )
            conn.commit()
            conn.close()
            logger.info(
                "[Woodies] Pattern %s %s fired: CCI=%.1f conf=%.2f trend=%s",
                pattern.pattern_id, pattern.direction,
                studies["cci_14"], pattern.confidence, studies["trend_state"],
            )
        except Exception as e:
            logger.warning("[Woodies] Pattern persist failed: %s", e)

    def get_current(self) -> dict:
        return dict(self.current_state)
