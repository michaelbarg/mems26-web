"""
shadow_trader.py — Shadow Trading Engine for MEMS26

Collects structured trade-like data without sending orders.
Every setup that passes 3-pillars is tracked as a phantom trade.

Two parallel shadows per setup:
  - cb_respected=True  — mirrors real CB/NEWS/MAX_TRADES
  - cb_respected=False — takes every setup for benchmark

Shadow trades include 15 strategic tags for Phase 3 scoring calibration.
"""

import asyncio
import json
import time
import logging
from datetime import datetime, time as dtime
from dataclasses import dataclass, field
from typing import Optional
from zoneinfo import ZoneInfo

from config import (
    STOP_MIN_PT, STOP_MAX_PT, T1_RR, T1_MIN_PT, T2_RR,
    CB_SOFT_LIMIT, CB_HARD_LIMIT, CB_MAX_TRADES, CB_CONSEC_LOSSES,
    EOD_FLATTEN_TIME, KILLZONES, CLOUD_URL, BRIDGE_TOKEN,
    REDIS_URL, REDIS_TOKEN,
)

log = logging.getLogger("shadow")
ET = ZoneInfo("America/New_York")

MAX_SHADOW_TRADES = 50  # Max concurrent shadow trades


@dataclass
class ShadowTrade:
    id: str
    direction: str  # LONG or SHORT
    entry_price: float
    stop: float
    t1: float
    t2: float
    t3: float
    risk_pts: float
    entry_ts: int
    setup_type: str
    level_name: str
    cb_respected: bool
    # 15 strategic tags
    day_type_at_entry: str = ""
    killzone_at_entry: str = ""
    minutes_into_session: int = 0
    cb_state_at_entry: str = ""
    news_state_at_entry: str = ""
    day_pnl_before_entry: float = 0.0
    setup_number_today: int = 0
    rel_vol_at_entry: float = 0.0
    cvd_direction_at_entry: str = ""
    mtf_aligned: bool = False
    vwap_side: str = ""
    sweep_wick_pts: float = 0.0
    fvg_size_pts: float = 0.0
    stacked_dominant_vol: bool = False
    bars_building_before_live: int = 0
    # Tracking state
    mae_pts: float = 0.0
    mfe_pts: float = 0.0
    status: str = "OPEN"
    exit_price: float = 0.0
    exit_ts: int = 0
    pnl_pts: float = 0.0
    pnl_usd: float = 0.0
    close_reason: str = ""
    pillar_detail: str = ""


class ShadowEngine:
    def __init__(self):
        self.active: list[ShadowTrade] = []
        self.closed_today: list[dict] = []
        self.setup_count_today: int = 0
        self._last_date: str = ""
        self._last_eval_ts: float = 0
        self._cooldown_setups: dict[str, float] = {}  # level_name -> last_ts

    def _reset_daily(self):
        today = datetime.now(ET).strftime("%Y-%m-%d")
        if today != self._last_date:
            self._last_date = today
            self.closed_today.clear()
            self.setup_count_today = 0
            self._cooldown_setups.clear()
            log.info(f"[SHADOW] Daily reset for {today}")

    def _get_killzone(self) -> str:
        now = datetime.now(ET)
        et_min = now.hour * 60 + now.minute
        for name, (start_s, end_s) in KILLZONES.items():
            sh, sm = map(int, start_s.split(":"))
            eh, em = map(int, end_s.split(":"))
            if sh * 60 + sm <= et_min < eh * 60 + em:
                return name
        return "OUTSIDE"

    def _get_minutes_into_session(self) -> int:
        """Minutes since session open (17:00 ET previous day or 09:30 ET)."""
        now = datetime.now(ET)
        # Regular session starts 09:30 ET
        session_start = now.replace(hour=9, minute=30, second=0, microsecond=0)
        if now >= session_start:
            return int((now - session_start).total_seconds() / 60)
        return 0

    async def evaluate_setup(self, market_data: dict, candles: list, http_session):
        """Called every tick from bridge main loop. Checks for 3-pillar pass."""
        self._reset_daily()
        now = time.time()

        # Rate limit: evaluate at most every 3 seconds
        if now - self._last_eval_ts < 3.0:
            return
        self._last_eval_ts = now

        if len(self.active) >= MAX_SHADOW_TRADES:
            return

        # Extract market data
        bar = market_data.get("bar", {}) or {}
        price = market_data.get("current_price", 0) or bar.get("c", 0)
        if price <= 0:
            return

        session = market_data.get("session", {}) or {}
        levels = market_data.get("levels", {}) or {}
        profile = market_data.get("profile", {}) or {}
        vwap_data = market_data.get("vwap", {}) or {}
        vol_ctx = market_data.get("volume_context", {}) or {}
        fp = market_data.get("footprint_bools", {}) or {}
        of2 = market_data.get("order_flow", {}) or {}
        cvd = market_data.get("cvd", {}) or {}
        day_info = market_data.get("day", {}) or {}
        mtf = market_data.get("mtf", {}) or {}
        cp = market_data.get("candle_patterns", {}) or {}

        day_type = (day_info.get("type", "") or "").upper()
        is_trend = day_type in ("TREND", "TREND_DAY")
        rel_vol = vol_ctx.get("rel_vol", 1.0) or 1.0

        # Build levels
        all_levels = self._build_levels(levels, session, vwap_data, profile, candles, price)

        # Find setup hits
        sorted_candles = sorted(candles, key=lambda c: c.get("ts", 0), reverse=True)
        live_candle = {
            "ts": 0, "o": bar.get("o", 0), "h": bar.get("h", 0),
            "l": bar.get("l", 0), "c": bar.get("c", price),
            "buy": bar.get("buy", 0), "sell": bar.get("sell", 0),
            "delta": bar.get("delta", 0),
        }
        recent10 = [live_candle] + sorted_candles[:9]
        recent20 = sorted_candles[:20]

        avg_vol20 = 1.0
        if recent20:
            avg_vol20 = sum((c.get("buy", 0) or 0) + (c.get("sell", 0) or 0) for c in recent20) / len(recent20) or 1.0

        long_hit, short_hit = self._find_hits(recent10, all_levels, avg_vol20, price, bar, rel_vol, cp)

        # Evaluate each direction
        for direction, hit in [("LONG", long_hit), ("SHORT", short_hit)]:
            if not hit:
                continue

            # Cooldown: don't re-enter same level within 5 minutes
            cooldown_key = f"{direction}_{hit['levelName']}"
            if cooldown_key in self._cooldown_setups:
                if now - self._cooldown_setups[cooldown_key] < 300:
                    continue

            # Check if already tracking this direction at this level
            already = any(
                s.direction == direction and s.level_name == hit["levelName"] and s.status == "OPEN"
                for s in self.active
            )
            if already:
                continue

            # Calculate entry/stop/targets
            entry_levels = self._calc_levels(direction.lower(), hit, price, market_data)
            if not entry_levels or entry_levels.get("stopTooWide"):
                continue

            # Compute score
            score = self._compute_score(direction, hit, bar, rel_vol, cvd, cp, price)
            if score < 60:
                continue

            # 3-Pillar evaluation
            eval_result = self._evaluate_pillars(
                hit, direction.lower(), market_data, sorted_candles,
                is_trend, vwap_data, fp, of2, price
            )

            if not eval_result["pass"]:
                # Log rejected attempt
                await self._log_attempt(
                    hit, direction, eval_result, market_data, day_type, http_session
                )
                continue

            # 3 pillars passed — create shadow trade(s)
            self._cooldown_setups[cooldown_key] = now
            self.setup_count_today += 1

            # Get CB/News state
            cb_state = await self._get_cb_state(http_session)
            news_state = await self._get_news_state(http_session)

            # Strategic tags
            tags = self._build_tags(
                market_data, day_type, cb_state, news_state,
                hit, rel_vol, cvd, vwap_data, fp, sorted_candles, mtf
            )

            # FVG size
            fvg_size = self._find_fvg_size(sorted_candles[:10], direction.lower())

            # Shadow 1: cb_respected=False (always taken)
            await self._open_shadow(
                direction, hit, entry_levels, eval_result,
                tags, fvg_size, cb_respected=False,
                http_session=http_session
            )

            # Shadow 2: cb_respected=True (check CB/NEWS/MAX)
            cb_allows = self._check_cb_allows(cb_state, news_state)
            kz = self._get_killzone()
            kz_allows = kz != "OUTSIDE"

            if cb_allows and kz_allows:
                await self._open_shadow(
                    direction, hit, entry_levels, eval_result,
                    tags, fvg_size, cb_respected=True,
                    http_session=http_session
                )
            else:
                # Log as rejected attempt with CB reason
                reason = "CB_BLOCKED" if not cb_allows else "OUTSIDE_KILLZONE"
                await self._log_attempt(
                    hit, direction,
                    {"pass": False, "reason": reason, "eval_type": eval_result.get("eval_type", "range")},
                    market_data, day_type, http_session, cb_respected=True
                )

    async def track_price(self, price: float, ts: int):
        """Called every tick to update MAE/MFE and check exits."""
        to_close = []
        for shadow in self.active:
            if shadow.status != "OPEN":
                continue

            is_long = shadow.direction == "LONG"
            pnl = (price - shadow.entry_price) if is_long else (shadow.entry_price - price)

            # Update MAE/MFE
            adverse = -pnl if pnl < 0 else 0
            favorable = pnl if pnl > 0 else 0
            if adverse > shadow.mae_pts:
                shadow.mae_pts = round(adverse, 2)
            if favorable > shadow.mfe_pts:
                shadow.mfe_pts = round(favorable, 2)

            # Check stop
            if is_long and price <= shadow.stop:
                to_close.append((shadow, price, "STOP"))
            elif not is_long and price >= shadow.stop:
                to_close.append((shadow, price, "STOP"))
            # Check T1 (partial — for shadow we close fully at T2 or track to T3)
            elif is_long and price >= shadow.t2:
                to_close.append((shadow, price, "T2"))
            elif not is_long and price <= shadow.t2:
                to_close.append((shadow, price, "T2"))
            elif is_long and price >= shadow.t3 and shadow.t3 > 0:
                to_close.append((shadow, price, "T3"))
            elif not is_long and price <= shadow.t3 and shadow.t3 > 0:
                to_close.append((shadow, price, "T3"))

        for shadow, exit_price, reason in to_close:
            await self._close_shadow(shadow, exit_price, reason, ts)

    async def eod_flatten(self):
        """Close all open shadows at EOD."""
        for shadow in list(self.active):
            if shadow.status == "OPEN":
                await self._close_shadow(shadow, shadow.entry_price, "EOD_FLATTEN", int(time.time()))

    async def close_for_real_trade(self, direction: str, level_name: str):
        """When user clicks EXECUTE on same setup, close matching shadow."""
        for shadow in list(self.active):
            if shadow.status == "OPEN" and shadow.direction == direction and shadow.level_name == level_name:
                await self._close_shadow(shadow, shadow.entry_price, "REAL_TRADE_COLLISION", int(time.time()))

    def get_active_count(self) -> int:
        return sum(1 for s in self.active if s.status == "OPEN")

    # ── Internal: Level Building ──────────────────────────────────────────

    def _build_levels(self, levels, session, vwap, profile, candles, price):
        all_levels = []
        mappings = [
            ("prev_high", "PDH"), ("prev_low", "PDL"),
            ("overnight_high", "ONH"), ("overnight_low", "ONL"),
        ]
        for key, name in mappings:
            v = levels.get(key, 0) or 0
            if v > 0:
                all_levels.append({"price": v, "name": name})

        if session.get("ibh", 0) > 0 and session.get("ib_locked"):
            all_levels.append({"price": session["ibh"], "name": "IBH"})
        if session.get("ibl", 0) > 0 and session.get("ib_locked"):
            all_levels.append({"price": session["ibl"], "name": "IBL"})
        if (vwap.get("value", 0) or 0) > 0:
            all_levels.append({"price": vwap["value"], "name": "VWAP"})
        if (profile.get("poc", 0) or 0) > 0:
            all_levels.append({"price": profile["poc"], "name": "POC"})
        if (profile.get("vah", 0) or 0) > 0:
            all_levels.append({"price": profile["vah"], "name": "VAH"})
        if (profile.get("val", 0) or 0) > 0:
            all_levels.append({"price": profile["val"], "name": "VAL"})
        if (session.get("sh", 0) or 0) > 0:
            all_levels.append({"price": session["sh"], "name": "SH"})
        if (session.get("sl", 0) or 0) > 0:
            all_levels.append({"price": session["sl"], "name": "SL"})

        # Swing levels from 30-candle range
        sorted_c = sorted(candles, key=lambda c: c.get("ts", 0), reverse=True)
        if len(sorted_c) >= 10:
            r30 = sorted_c[:30]
            lows = [c.get("l", 0) or c.get("low", 0) for c in r30 if (c.get("l") or c.get("low", 0)) > 0]
            highs = [c.get("h", 0) or c.get("high", 0) for c in r30 if (c.get("h") or c.get("high", 0)) > 0]
            if lows:
                sw_l = min(lows)
                if not any(abs(l["price"] - sw_l) < 1.5 for l in all_levels):
                    all_levels.append({"price": sw_l, "name": "SwL"})
            if highs:
                sw_h = max(highs)
                if not any(abs(l["price"] - sw_h) < 1.5 for l in all_levels):
                    all_levels.append({"price": sw_h, "name": "SwH"})

        return all_levels

    def _find_hits(self, recent10, all_levels, avg_vol20, price, bar, rel_vol, cp):
        long_hit = None
        short_hit = None

        for ri, rb in enumerate(recent10):
            rb_vol = (rb.get("buy", 0) or 0) + (rb.get("sell", 0) or 0)
            rb_rel_vol = rb_vol / avg_vol20 if avg_vol20 > 0 else 1.0
            rb_delta = rb.get("delta", 0) or ((rb.get("buy", 0) or 0) - (rb.get("sell", 0) or 0))
            lower_wick = min(rb.get("o", 0), rb.get("c", 0)) - rb.get("l", 0)
            upper_wick = rb.get("h", 0) - max(rb.get("o", 0), rb.get("c", 0))
            body = abs(rb.get("c", 0) - rb.get("o", 0))
            total_range = rb.get("h", 0) - rb.get("l", 0)
            next_rb = recent10[ri - 1] if ri > 0 else None

            for lv in all_levels:
                # LONG Sweep
                if not long_hit and rb.get("l", 0) < lv["price"] - 0.5:
                    wick_ratio = lower_wick / total_range if total_range > 0 else 0
                    if wick_ratio >= 0.4:
                        if rb.get("c", 0) > lv["price"]:
                            long_hit = {"level": lv["price"], "levelName": lv["name"], "bar": rb, "relVol": rb_rel_vol, "type": "sweep"}
                        elif next_rb and next_rb.get("c", 0) > lv["price"]:
                            long_hit = {"level": lv["price"], "levelName": lv["name"], "bar": next_rb, "relVol": rb_rel_vol, "type": "sweep"}
                        elif ri > 0 and price > lv["price"]:
                            long_hit = {"level": lv["price"], "levelName": lv["name"], "bar": rb, "relVol": rb_rel_vol, "type": "sweep"}

                # LONG Rejection
                if not long_hit and abs(rb.get("l", 0) - lv["price"]) < 1.0:
                    if rb.get("c", 0) > lv["price"] and rb.get("c", 0) > rb.get("o", 0) and lower_wick > body * 1.5:
                        long_hit = {"level": lv["price"], "levelName": lv["name"], "bar": rb, "relVol": rb_rel_vol, "type": "rejection"}

                # SHORT Sweep
                if not short_hit and rb.get("h", 0) > lv["price"] + 0.5:
                    wick_ratio = upper_wick / total_range if total_range > 0 else 0
                    if wick_ratio >= 0.4:
                        if rb.get("c", 0) < lv["price"]:
                            short_hit = {"level": lv["price"], "levelName": lv["name"], "bar": rb, "relVol": rb_rel_vol, "type": "sweep"}
                        elif next_rb and next_rb.get("c", 0) < lv["price"]:
                            short_hit = {"level": lv["price"], "levelName": lv["name"], "bar": next_rb, "relVol": rb_rel_vol, "type": "sweep"}
                        elif ri > 0 and price < lv["price"]:
                            short_hit = {"level": lv["price"], "levelName": lv["name"], "bar": rb, "relVol": rb_rel_vol, "type": "sweep"}

                # SHORT Rejection
                if not short_hit and abs(rb.get("h", 0) - lv["price"]) < 1.0:
                    if rb.get("c", 0) < lv["price"] and rb.get("c", 0) < rb.get("o", 0) and upper_wick > body * 1.5:
                        short_hit = {"level": lv["price"], "levelName": lv["name"], "bar": rb, "relVol": rb_rel_vol, "type": "rejection"}

            if long_hit and short_hit:
                break

        return long_hit, short_hit

    def _calc_levels(self, direction, hit, price, market_data):
        is_long = direction == "long"
        bar = hit["bar"]
        entry = bar.get("h", 0) + 0.25 if is_long and hit["type"] == "sweep" else \
                bar.get("l", 0) - 0.25 if not is_long and hit["type"] == "sweep" else price
        stop = bar.get("l", 0) - 0.25 if is_long else bar.get("h", 0) + 0.25
        risk = abs(entry - stop)
        if risk < STOP_MIN_PT:
            stop = entry - STOP_MIN_PT if is_long else entry + STOP_MIN_PT
            risk = STOP_MIN_PT
        stop_too_wide = risk > STOP_MAX_PT

        t1 = entry + risk * T1_RR if is_long else entry - risk * T1_RR
        t2 = entry + risk * T2_RR if is_long else entry - risk * T2_RR
        woodi = market_data.get("woodi", {}) or {}
        if is_long:
            t3 = woodi.get("r1", 0) if woodi.get("r1", 0) > entry + risk * 2 else entry + risk * 3
        else:
            t3 = woodi.get("s1", 0) if woodi.get("s1", 0) and woodi.get("s1", 0) < entry - risk * 2 else entry - risk * 3

        return {
            "entry": round(entry, 2), "stop": round(stop, 2),
            "t1": round(t1, 2), "t2": round(t2, 2), "t3": round(t3, 2),
            "riskPts": round(risk * 4) / 4, "stopTooWide": stop_too_wide,
        }

    def _compute_score(self, direction, hit, bar, rel_vol, cvd, cp, price):
        is_long = direction == "LONG"
        checks = []
        checks.append(hit is not None)  # pattern found (critical)
        checks.append(  # price correct side (critical)
            (price > hit["level"]) if is_long else (price < hit["level"])
        )
        delta = bar.get("delta", 0) or 0
        checks.append(delta > 50 if is_long else delta < -50)  # delta (critical)

        critical_pass = sum(checks)
        if critical_pass < 3:
            return int(critical_pass / 3 * 40)

        bonus = 0
        total_bonus = 2
        if hit["relVol"] > 1.1:
            bonus += 1
        if is_long:
            if cp.get("bull_engulf") or cp.get("bar0") in ("HAMMER", "BULL_STRONG"):
                bonus += 1
        else:
            if cp.get("bear_engulf") or cp.get("bar0") in ("SHOOTING_STAR", "BEAR_STRONG"):
                bonus += 1

        return 45 + int((3 + bonus) / (3 + total_bonus) * 55)

    # ── 3-Pillar Evaluation ───────────────────────────────────────────────

    def _evaluate_pillars(self, hit, direction, market_data, candles, is_trend, vwap, fp, of2, price):
        if is_trend:
            return self._eval_trend(hit, direction, market_data, candles, vwap, fp, of2, price)
        return self._eval_range(hit, direction, market_data, candles, fp, of2, price)

    def _eval_range(self, hit, direction, market_data, candles, fp, of2, price):
        is_long = direction == "long"
        macro = ["PDH", "PDL", "ONH", "ONL", "IBH", "IBL", "VWAP", "POC", "VAH", "VAL", "SH", "SL"]

        # P1: ZONE — sweep at macro level
        if hit["type"] != "sweep":
            return {"pass": False, "reason": f"P1: Range requires sweep (not {hit['type']})", "eval_type": "range"}

        bar = hit["bar"]
        if is_long:
            sweep_wick = min(bar.get("o", 0), bar.get("c", 0)) - bar.get("l", 0)
        else:
            sweep_wick = bar.get("h", 0) - max(bar.get("o", 0), bar.get("c", 0))
        if sweep_wick < 1.5:
            return {"pass": False, "reason": f"P1: Sweep wick {sweep_wick:.1f}pt < 1.5pt", "eval_type": "range"}
        if hit["levelName"] not in macro:
            return {"pass": False, "reason": "P1: Middle of Nowhere", "eval_type": "range"}

        # P2: PATTERN — MSS + FVG + RelVol + Stacked
        recent20 = candles[:20]
        has_mss = False
        if is_long:
            swing_highs = [c.get("h", 0) or c.get("high", 0) for c in recent20[2:10]]
            swing_h = max(swing_highs) if swing_highs else 0
            has_mss = price > swing_h > 0
        else:
            swing_lows = [c.get("l", 0) or c.get("low", 0) for c in recent20[2:10]]
            swing_l = min(swing_lows) if swing_lows else 999999
            has_mss = price < swing_l < 999999
        if not has_mss:
            return {"pass": False, "reason": "P2: No MSS", "eval_type": "range"}

        has_fvg = self._check_fvg(candles[:10], is_long)
        if not has_fvg:
            return {"pass": False, "reason": "P2: No FVG", "eval_type": "range"}

        if hit["relVol"] <= 1.2:
            return {"pass": False, "reason": f"P2: RelVol {hit['relVol']:.2f} <= 1.2", "eval_type": "range"}

        stacked = (fp.get("stacked_imbalance_count") or
                   (of2.get("imbalance_bull", 0) or 0) + (of2.get("imbalance_bear", 0) or 0))
        if stacked < 2:
            return {"pass": False, "reason": f"P2: Stacked {stacked} < 2", "eval_type": "range"}

        # P3: FLOW
        absorption = fp.get("absorption_at_fvg") or \
                     (of2.get("absorption_bull") if is_long else of2.get("absorption_bear")) or False
        if not absorption:
            return {"pass": False, "reason": "P3: No absorption at FVG", "eval_type": "range"}

        delta_confirmed = fp.get("delta_confirmed_1m", False)
        if not delta_confirmed:
            return {"pass": False, "reason": "P3: No delta confirm (1m)", "eval_type": "range"}

        return {"pass": True, "reason": "All 3 pillars PASS", "eval_type": "range"}

    def _eval_trend(self, hit, direction, market_data, candles, vwap, fp, of2, price):
        is_long = direction == "long"

        # P1: ZONE — Pullback to VWAP or FVG
        vwap_val = vwap.get("value", 0) or 0
        vwap_dist = abs(price - vwap_val) if vwap_val else 999
        has_pullback = vwap_dist <= 3.0

        if not has_pullback:
            has_pullback = self._check_fvg_pullback(candles[:10], is_long, price)
        if not has_pullback:
            return {"pass": False, "reason": "P1: No pullback to VWAP/FVG", "eval_type": "trend"}

        # P2: PATTERN — MSS + FVG + RelVol
        recent20 = candles[:20]
        has_mss = False
        if is_long:
            swing_highs = [c.get("h", 0) or c.get("high", 0) for c in recent20[2:10]]
            swing_h = max(swing_highs) if swing_highs else 0
            has_mss = price > swing_h > 0
        else:
            swing_lows = [c.get("l", 0) or c.get("low", 0) for c in recent20[2:10]]
            swing_l = min(swing_lows) if swing_lows else 999999
            has_mss = price < swing_l < 999999
        if not has_mss:
            return {"pass": False, "reason": "P2: No continuation MSS", "eval_type": "trend"}

        has_fvg = self._check_fvg(candles[:10], is_long)
        if not has_fvg:
            return {"pass": False, "reason": "P2: No FVG", "eval_type": "trend"}

        if hit["relVol"] <= 1.2:
            return {"pass": False, "reason": f"P2: RelVol {hit['relVol']:.2f} <= 1.2", "eval_type": "trend"}

        # P3: FLOW — declining delta + confirmed
        recent5 = candles[:5]
        if len(recent5) >= 3:
            deltas = [abs(c.get("delta", 0) or 0) for c in recent5]
            if not (deltas[0] < deltas[1] or deltas[1] < deltas[2]):
                return {"pass": False, "reason": "P3: Delta not declining", "eval_type": "trend"}

        delta_confirmed = fp.get("delta_confirmed_1m", False)
        if not delta_confirmed:
            return {"pass": False, "reason": "P3: No delta confirm (1m)", "eval_type": "trend"}

        return {"pass": True, "reason": "All 3 pillars PASS", "eval_type": "trend"}

    def _check_fvg(self, candles, is_long):
        for i in range(len(candles) - 2):
            c1 = candles[i]
            c3 = candles[i + 2]
            if is_long:
                gap = (c1.get("l", 0) or c1.get("low", 0)) - (c3.get("h", 0) or c3.get("high", 0))
                if 0.5 <= gap <= 4.0:
                    return True
            else:
                gap = (c3.get("l", 0) or c3.get("low", 0)) - (c1.get("h", 0) or c1.get("high", 0))
                if 0.5 <= gap <= 4.0:
                    return True
        return False

    def _check_fvg_pullback(self, candles, is_long, price):
        for i in range(len(candles) - 2):
            c1 = candles[i]
            c3 = candles[i + 2]
            if is_long:
                c1_l = c1.get("l", 0) or c1.get("low", 0)
                c3_h = c3.get("h", 0) or c3.get("high", 0)
                gap = c1_l - c3_h
                if gap >= 0.5 and abs(price - (c1_l + c3_h) / 2) <= 2.0:
                    return True
            else:
                c1_h = c1.get("h", 0) or c1.get("high", 0)
                c3_l = c3.get("l", 0) or c3.get("low", 0)
                gap = c3_l - c1_h
                if gap >= 0.5 and abs(price - (c1_h + c3_l) / 2) <= 2.0:
                    return True
        return False

    def _find_fvg_size(self, candles, direction):
        is_long = direction == "long"
        for i in range(len(candles) - 2):
            c1 = candles[i]
            c3 = candles[i + 2]
            if is_long:
                gap = (c1.get("l", 0) or c1.get("low", 0)) - (c3.get("h", 0) or c3.get("high", 0))
                if 0.5 <= gap <= 4.0:
                    return round(gap, 2)
            else:
                gap = (c3.get("l", 0) or c3.get("low", 0)) - (c1.get("h", 0) or c1.get("high", 0))
                if 0.5 <= gap <= 4.0:
                    return round(gap, 2)
        return 0.0

    # ── CB/News checks ────────────────────────────────────────────────────

    async def _get_cb_state(self, http):
        try:
            import aiohttp
            async with http.get(
                f"{CLOUD_URL}/trade/circuit-breaker",
                timeout=aiohttp.ClientTimeout(total=3)
            ) as resp:
                return await resp.json()
        except Exception:
            return {}

    async def _get_news_state(self, http):
        try:
            import aiohttp
            async with http.get(
                f"{REDIS_URL}/get/mems26:news:state",
                headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
                timeout=aiohttp.ClientTimeout(total=3)
            ) as resp:
                result = await resp.json()
                val = result.get("result")
                if val and isinstance(val, str):
                    return json.loads(val)
        except Exception:
            pass
        return {}

    def _check_cb_allows(self, cb_state, news_state):
        if cb_state.get("hard_locked"):
            return False
        if cb_state.get("soft_locked"):
            return False
        if cb_state.get("trade_count", 0) >= CB_MAX_TRADES:
            return False
        ns = news_state.get("state", "") if isinstance(news_state, dict) else ""
        if ns in ("PRE_NEWS_FREEZE", "NEWS_ACTIVE"):
            return False
        return True

    # ── Tags ──────────────────────────────────────────────────────────────

    def _build_tags(self, market_data, day_type, cb_state, news_state, hit, rel_vol, cvd, vwap, fp, candles, mtf):
        kz = self._get_killzone()
        vwap_val = vwap.get("value", 0) or 0
        price = market_data.get("current_price", 0) or market_data.get("bar", {}).get("c", 0)

        # MTF alignment
        mtf_count = 0
        for tf in ["m5", "m15", "m30", "m60"]:
            tf_d = (mtf.get(tf) or {})
            c_val = tf_d.get("c", 0)
            o_val = tf_d.get("o", 0)
            d_val = tf_d.get("delta", 0)
            if c_val > o_val and d_val > 0:
                mtf_count += 1
            elif c_val < o_val and d_val < 0:
                mtf_count += 1

        # Bars building: count how many candles had hits at same level
        bars_building = 0
        for c in candles[:20]:
            c_l = c.get("l", 0) or c.get("low", 0)
            c_h = c.get("h", 0) or c.get("high", 0)
            if abs(c_l - hit["level"]) < 2 or abs(c_h - hit["level"]) < 2:
                bars_building += 1

        return {
            "day_type_at_entry": day_type,
            "killzone_at_entry": kz,
            "minutes_into_session": self._get_minutes_into_session(),
            "cb_state_at_entry": json.dumps({
                "locked": cb_state.get("soft_locked") or cb_state.get("hard_locked"),
                "trades": cb_state.get("trade_count", 0),
                "pnl": cb_state.get("pnl", 0),
            }) if cb_state else "{}",
            "news_state_at_entry": news_state.get("state", "CLEAR") if isinstance(news_state, dict) else "CLEAR",
            "day_pnl_before_entry": cb_state.get("pnl", 0.0) if cb_state else 0.0,
            "setup_number_today": self.setup_count_today,
            "rel_vol_at_entry": round(rel_vol, 2),
            "cvd_direction_at_entry": cvd.get("trend", "NEUTRAL"),
            "mtf_aligned": mtf_count >= 3,
            "vwap_side": "ABOVE" if price > vwap_val else "BELOW" if vwap_val > 0 else "UNKNOWN",
            "stacked_dominant_vol": bool(fp.get("stacked_imbalance_count", 0) or 0 >= 3),
            "bars_building_before_live": bars_building,
        }

    # ── Shadow lifecycle ──────────────────────────────────────────────────

    async def _open_shadow(self, direction, hit, levels, eval_result, tags, fvg_size, cb_respected, http_session):
        shadow_id = f"SH_{int(time.time())}_{direction[0]}{'R' if cb_respected else 'B'}"
        shadow = ShadowTrade(
            id=shadow_id,
            direction=direction,
            entry_price=levels["entry"],
            stop=levels["stop"],
            t1=levels["t1"],
            t2=levels["t2"],
            t3=levels["t3"],
            risk_pts=levels["riskPts"],
            entry_ts=int(time.time()),
            setup_type=hit["type"].upper(),
            level_name=hit["levelName"],
            cb_respected=cb_respected,
            sweep_wick_pts=tags.pop("sweep_wick_pts", 0.0) if "sweep_wick_pts" in tags else 0.0,
            fvg_size_pts=fvg_size,
            pillar_detail=eval_result.get("reason", ""),
            **tags,
        )
        self.active.append(shadow)
        log.info(f"[SHADOW] OPEN {shadow_id} {direction} @ {levels['entry']} "
                 f"stop={levels['stop']} cb_respected={cb_respected} "
                 f"level={hit['levelName']} type={hit['type']}")

        # Persist to backend
        await self._persist_trade(shadow, http_session)

    async def _close_shadow(self, shadow: ShadowTrade, exit_price: float, reason: str, ts: int):
        shadow.status = "CLOSED"
        shadow.exit_price = exit_price
        shadow.exit_ts = ts
        pnl = (exit_price - shadow.entry_price) if shadow.direction == "LONG" else (shadow.entry_price - exit_price)
        shadow.pnl_pts = round(pnl, 2)
        shadow.pnl_usd = round(pnl * 5, 2)  # MES = $5/pt
        shadow.close_reason = reason

        duration = (ts - shadow.entry_ts) / 60 if ts > shadow.entry_ts else 0
        mfe = shadow.mfe_pts
        exit_eff = round(pnl / mfe * 100, 1) if mfe > 0 else 0

        log.info(f"[SHADOW] CLOSE {shadow.id} PnL={pnl:+.2f}pt reason={reason} "
                 f"MAE={shadow.mae_pts:.1f} MFE={shadow.mfe_pts:.1f} dur={duration:.0f}min")

        self.closed_today.append(self._to_dict(shadow))

        # Remove from active
        self.active = [s for s in self.active if s.id != shadow.id]

    async def _persist_trade(self, shadow: ShadowTrade, http_session):
        """Persist shadow trade to backend Postgres."""
        try:
            import aiohttp
            trade_dict = self._to_dict(shadow)
            async with http_session.post(
                f"{CLOUD_URL}/trades/log/shadow",
                json=trade_dict,
                headers={"x-bridge-token": BRIDGE_TOKEN, "content-type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    log.warning(f"[SHADOW] Persist failed: {resp.status} {body[:100]}")
        except Exception as e:
            log.warning(f"[SHADOW] Persist error: {e}")

    async def _log_attempt(self, hit, direction, eval_result, market_data, day_type, http_session, cb_respected=False):
        """Log a rejected setup attempt."""
        try:
            import aiohttp
            attempt = {
                "ts": int(time.time()),
                "direction": direction,
                "setup_type": hit["type"].upper(),
                "level_name": hit["levelName"],
                "level_price": hit["level"],
                "price_at_detect": market_data.get("current_price", 0),
                "rejection_reason": eval_result.get("reason", ""),
                "pillars_detail": eval_result.get("reason", ""),
                "day_type": day_type,
                "killzone": self._get_killzone(),
                "is_shadow": True,
                "cb_respected": cb_respected,
            }
            async with http_session.post(
                f"{CLOUD_URL}/analytics/attempts",
                json=attempt,
                headers={"content-type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=3)
            ) as resp:
                pass
        except Exception as e:
            log.debug(f"[SHADOW] Attempt log failed: {e}")

    def _to_dict(self, shadow: ShadowTrade) -> dict:
        d = {
            "id": shadow.id,
            "direction": shadow.direction,
            "entry_price": shadow.entry_price,
            "exit_price": shadow.exit_price,
            "stop": shadow.stop,
            "t1": shadow.t1,
            "t2": shadow.t2,
            "t3": shadow.t3,
            "risk_pts": shadow.risk_pts,
            "pnl_pts": shadow.pnl_pts,
            "pnl_usd": shadow.pnl_usd,
            "contracts": 1,
            "entry_ts": shadow.entry_ts,
            "exit_ts": shadow.exit_ts,
            "status": shadow.status,
            "close_reason": shadow.close_reason,
            "setup_type": shadow.setup_type,
            "day_type": shadow.day_type_at_entry,
            "killzone": shadow.killzone_at_entry,
            "sweep_wick_pts": shadow.sweep_wick_pts,
            "pillars_passed": 3,
            "pillar_detail": shadow.pillar_detail,
            "mae_pts": shadow.mae_pts,
            "mfe_pts": shadow.mfe_pts,
            "duration_min": round((shadow.exit_ts - shadow.entry_ts) / 60, 1) if shadow.exit_ts else 0,
            "is_shadow": True,
            "cb_respected": shadow.cb_respected,
            "day_type_at_entry": shadow.day_type_at_entry,
            "killzone_at_entry": shadow.killzone_at_entry,
            "minutes_into_session": shadow.minutes_into_session,
            "cb_state_at_entry": shadow.cb_state_at_entry,
            "news_state_at_entry": shadow.news_state_at_entry,
            "day_pnl_before_entry": shadow.day_pnl_before_entry,
            "setup_number_today": shadow.setup_number_today,
            "rel_vol_at_entry": shadow.rel_vol_at_entry,
            "cvd_direction_at_entry": shadow.cvd_direction_at_entry,
            "mtf_aligned": shadow.mtf_aligned,
            "vwap_side": shadow.vwap_side,
            "sweep_wick_pts_tag": shadow.sweep_wick_pts,
            "fvg_size_pts": shadow.fvg_size_pts,
            "stacked_dominant_vol": shadow.stacked_dominant_vol,
            "bars_building_before_live": shadow.bars_building_before_live,
        }
        return d
