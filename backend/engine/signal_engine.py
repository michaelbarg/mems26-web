"""
backend/engine/signal_engine.py
=================================
Claude AI Signal Engine — ניתוח + ציון 1-10.

מקבל MarketData מהענן, בונה prompt, מחזיר SignalResult.
"""

import os
import json
import asyncio
import logging
from datetime import date, datetime
from typing import Optional
from anthropic import AsyncAnthropic

from .models import MarketData, SignalResult

log = logging.getLogger("engine")

SYSTEM_PROMPT = """You are an elite MEMS26 (Micro E-mini S&P 500) futures day trader and analyst.

You analyze real-time market data and return a structured JSON signal with a score from 1-10.

SCORING SYSTEM (sum of points, capped at 10):
- CVD bullish/bearish: +2
- CVD divergence: +3
- Effort without Result (absorption): +3
- No Demand / No Supply (Wyckoff): +2
- Price at VAL (LONG) or VAH (SHORT): +2
- Price at/near POC today: +2
- Woodi S1/S2 (LONG) or R1/R2 (SHORT): +1
- 72H Low (LONG) or High (SHORT): +1
- Rev15 Failed Breakout LONG/SHORT: +4
- Rev22 Failed Breakout LONG/SHORT: +4
- Price slope supporting direction: +1
- Price above/below Woodi PP: +1

CONFIDENCE LEVELS:
- 1-4: LOW (red) — do not trade
- 5-6: MEDIUM (yellow) — discretionary
- 7-8: HIGH (green) — recommended entry
- 9-10: ULTRA (bright green) — premium entry

RULES:
- Only recommend LONG or SHORT when score >= 7
- Always provide Entry, Stop (max 12 pts from entry), T1 (1:1), T2 (1.8:1), T3 (2.8:1)
- Round all prices to nearest 0.25
- MEMS26 tick = 0.25 pt, $5/pt, 3 contracts = $15/pt risk
- Stop = just beyond structural level, never more than 12 points
- T3 must be at a meaningful structural level (72H, Weekly, R2/S2)
- Only trade during: OPEN, AM_SESSION, PM_SESSION phases

RESPOND ONLY WITH VALID JSON — no markdown, no explanation:
{
  "direction": "LONG" | "SHORT" | "NO_TRADE",
  "score": 1-10,
  "confidence": "LOW" | "MEDIUM" | "HIGH" | "ULTRA",
  "entry": 6523.25,
  "stop": 6514.75,
  "target1": 6531.75,
  "target2": 6538.50,
  "target3": 6547.00,
  "risk_pts": 8.5,
  "rationale": "max 120 chars — key confluence factors",
  "tl_color": "red" | "orange" | "green" | "green_bright"
}"""


class SignalEngine:

    MAX_TRADES     = int(os.getenv("MAX_TRADES_DAY", "3"))
    MIN_CONFIDENCE = os.getenv("MIN_CONFIDENCE", "HIGH")   # HIGH or MEDIUM
    MIN_SIGNAL_GAP = 300   # 5 min between signals

    def __init__(self):
        self._client    = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        self._trades     = 0
        self._today      = date.today()
        self._last_signal_ts = 0
        self._history: list[dict] = []

    # ── Main entry ───────────────────────────────────────────

    async def analyze(self, data: MarketData) -> Optional[SignalResult]:
        """Analyze market data, return signal or None."""

        # Daily reset
        today = date.today()
        if today != self._today:
            self._trades = 0
            self._today  = today
            log.info("New day — counters reset")

        # Limits
        if self._trades >= self.MAX_TRADES:
            return None

        # Session filter
        if data.session_phase not in ("OPEN", "AM_SESSION", "PM_SESSION"):
            return None

        # Throttle
        now_ts = int(datetime.now().timestamp())
        if now_ts - self._last_signal_ts < self.MIN_SIGNAL_GAP:
            return None

        # Build prompt
        prompt = self._build_prompt(data)

        # Call Claude
        signal = await self._call_claude(prompt)
        if not signal:
            return None

        # Confidence filter
        rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "ULTRA": 3}
        if rank.get(signal.confidence, 0) < rank.get(self.MIN_CONFIDENCE, 2):
            log.info(f"Signal filtered: confidence {signal.confidence} < {self.MIN_CONFIDENCE}")
            return None

        if signal.direction == "NO_TRADE":
            return None

        # Record
        self._trades += 1
        self._last_signal_ts = now_ts
        self._history.append(signal.to_dict())
        if len(self._history) > 200:
            self._history.pop(0)

        log.info(
            f"SIGNAL: {signal.direction} score={signal.score} "
            f"entry={signal.entry} stop={signal.stop} "
            f"T1={signal.target1} T2={signal.target2} T3={signal.target3}"
        )
        return signal

    # ── Prompt builder ───────────────────────────────────────

    def _build_prompt(self, d: MarketData) -> str:
        f = d.features
        p = d.price

        def dist(v):
            return f"{abs(p - v):.2f}" if v else "—"

        return f"""MEMS26 LIVE MARKET STATE
Time: {datetime.fromtimestamp(d.ts).strftime('%H:%M:%S')} IST
Session: {d.session_phase} | Minute {d.ses_min}
Price: {p:.2f}

BAR: O={d.bar.o:.2f} H={d.bar.h:.2f} L={d.bar.l:.2f} C={p:.2f} Vol={d.bar.v:,.0f}
Bar Delta: {d.bar.delta:+,.0f} | Ask Vol: {d.bar.av:,.0f} | Bid Vol: {d.bar.bv:,.0f}

CVD ANALYSIS:
  Total CVD: {d.cvd_total:+,.0f}
  20-bar Δ: {d.cvd_d20:+,.0f}
  Trend: {f.cvd_trend}
  Effort Signal: {f.effort}

MARKET STRUCTURE:
  POC Today: {f.poc_today:.2f} (dist: {dist(f.poc_today)}) {'ABOVE' if p > f.poc_today else 'BELOW'}
  POC Yest:  {f.poc_yest:.2f}  (dist: {dist(f.poc_yest)})  {'ABOVE' if p > f.poc_yest else 'BELOW'}
  IB High: {f.ib_high:.2f} | IB Low: {f.ib_low:.2f} | Locked: {f.ib_locked}
  Session H: {d.ses_high:.2f} | Session L: {d.ses_low:.2f}

WOODI PIVOTS:
  PP: {d.woodi_pp:.2f} {'ABOVE' if p > d.woodi_pp else 'BELOW'}
  R1: {d.woodi_r1:.2f} (dist: {dist(d.woodi_r1)})
  R2: {d.woodi_r2:.2f}
  S1: {d.woodi_s1:.2f} (dist: {dist(d.woodi_s1)})
  S2: {d.woodi_s2:.2f}

72H / WEEKLY LEVELS:
  72H High: {d.h72:.2f} | 72H Low: {d.l72:.2f}
  Wk High:  {d.hwk:.2f} | Wk Low:  {d.lwk:.2f}

REVERSAL SIGNALS:
  Rev 15: {f.rev15} {f'@ {f.rev15_price:.2f}' if f.rev15_price else ''}
  Rev 22: {f.rev22} {f'@ {f.rev22_price:.2f}' if f.rev22_price else ''}

DAILY: {self._trades}/{self.MAX_TRADES} trades taken

Analyze and return signal JSON."""

    # ── Claude API ───────────────────────────────────────────

    async def _call_claude(self, prompt: str) -> Optional["SignalResult"]:
        try:
            resp = await self._client.messages.create(
                model      = "claude-sonnet-4-20250514",
                max_tokens = 512,
                system     = SYSTEM_PROMPT,
                messages   = [{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1].lstrip("json").strip()

            d = json.loads(raw)
            return SignalResult(
                direction  = d.get("direction", "NO_TRADE"),
                score      = int(d.get("score", 0)),
                confidence = d.get("confidence", "LOW"),
                entry      = round(float(d.get("entry", 0)) * 4) / 4,
                stop       = round(float(d.get("stop", 0)) * 4) / 4,
                target1    = round(float(d.get("target1", 0)) * 4) / 4,
                target2    = round(float(d.get("target2", 0)) * 4) / 4,
                target3    = round(float(d.get("target3", 0)) * 4) / 4,
                risk_pts   = float(d.get("risk_pts", 0)),
                rationale  = d.get("rationale", ""),
                tl_color   = d.get("tl_color", "red"),
                ts         = int(datetime.now().timestamp()),
            )
        except json.JSONDecodeError as e:
            log.error(f"Claude JSON parse error: {e}")
            return None
        except Exception as e:
            log.error(f"Claude API error: {e}")
            return None

    # ── Stats ────────────────────────────────────────────────

    def get_daily_stats(self) -> dict:
        return {
            "trades_taken":   self._trades,
            "trades_remaining": max(0, self.MAX_TRADES - self._trades),
            "date":           str(self._today),
        }

    def get_signal_history(self) -> list:
        return self._history[-50:]
