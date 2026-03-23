"""
bridge/zmq_bridge.py
=====================
הגשר המקומי — רץ על המחשב שמריץ Sierra Chart.

זרימה:
  Sierra Chart (ZMQ PUSH :5555)
      ↓ recv
  Feature Engineering (CVD, Reversals, Effort)
      ↓
  POST/WebSocket → Cloud FastAPI (Render)
      ↓
  Claude AI → Dashboard (Vercel)

הרצה:
  pip install pyzmq websockets aiohttp python-dotenv
  python zmq_bridge.py
"""

import zmq
import json
import asyncio
import aiohttp
import os
import logging
import time
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("bridge")

# ─────────────────────────────────────────────
#  Config
# ─────────────────────────────────────────────
ZMQ_PORT     = int(os.getenv("ZMQ_PORT", "5555"))
CLOUD_URL    = os.getenv("CLOUD_URL", "https://mems26-api.onrender.com")
BRIDGE_TOKEN = os.getenv("BRIDGE_TOKEN", "change-me-secret")
POST_INTERVAL = 1.0   # שניות בין שליחות לענן

# ─────────────────────────────────────────────
#  Feature State
# ─────────────────────────────────────────────
@dataclass
class SessionState:
    """מצב הסשן הנוכחי — מצטבר לאורך הסשן"""
    date:          str  = ""
    ib_high:       float = 0.0
    ib_low:        float = 0.0
    ib_locked:     bool  = False
    rev15_type:    str  = "NONE"
    rev22_type:    str  = "NONE"
    rev15_price:   float = 0.0
    rev22_price:   float = 0.0
    bars:          list  = field(default_factory=list)   # last 30 bars

    poc_today:     float = 0.0
    poc_yest:      float = 0.0
    vah:           float = 0.0
    val:           float = 0.0

state = SessionState()

# ─────────────────────────────────────────────
#  Feature Engineering
# ─────────────────────────────────────────────

def update_session(raw: dict) -> dict:
    """
    קבל נר גולמי מ-ZMQ, החזר enriched payload עם:
    - IB high/low
    - Reversal 15/22 status
    - Effort vs Result
    - Wyckoff No Demand/No Supply
    - POC approximation
    """
    global state

    bar    = raw.get("bar", {})
    ses    = raw.get("session", {})
    cvd    = raw.get("cvd", {})
    woodi  = raw.get("woodi", {})
    levels = raw.get("levels", {})

    today  = datetime.fromtimestamp(raw["ts"]).strftime("%Y-%m-%d")
    sesMin = ses.get("min", -1)
    price  = bar.get("c", 0)
    vol    = bar.get("v", 0)
    hi     = bar.get("h", 0)
    lo     = bar.get("l", 0)

    # Reset on new day
    if today != state.date:
        log.info(f"New session: {today}")
        state = SessionState(date=today)

    # Keep last 30 bars
    state.bars.append(bar)
    if len(state.bars) > 30:
        state.bars.pop(0)

    # ── IB calculation (first 60 minutes) ──────────────
    if 0 <= sesMin <= 60:
        if hi > state.ib_high: state.ib_high = hi
        if lo > 0 and (state.ib_low == 0 or lo < state.ib_low): state.ib_low = lo
    elif sesMin > 60 and not state.ib_locked:
        state.ib_locked = True
        log.info(f"IB locked: H={state.ib_high:.2f} L={state.ib_low:.2f}")

    # ── Reversal 15/22 detection ───────────────────────
    def detect_reversal(mark_min: int, attr_type: str, attr_price: str):
        if sesMin < mark_min or getattr(state, attr_type) != "NONE":
            return
        if not state.ib_high or not state.ib_low:
            return

        recent = state.bars[-3:] if len(state.bars) >= 3 else state.bars
        went_above = any(b.get("h", 0) > state.ib_high + 0.25 for b in recent)
        went_below = any(b.get("l", 9999) < state.ib_low - 0.25 for b in recent)
        back_inside = state.ib_low <= price <= state.ib_high

        if went_above and back_inside:
            setattr(state, attr_type, "FAILED_BREAK_SHORT")
            setattr(state, attr_price, price)
            log.info(f"Rev {mark_min}: FAILED_BREAK_SHORT @ {price:.2f}")
        elif went_below and back_inside:
            setattr(state, attr_type, "FAILED_BREAK_LONG")
            setattr(state, attr_price, price)
            log.info(f"Rev {mark_min}: FAILED_BREAK_LONG @ {price:.2f}")
        elif not went_above and not went_below:
            if abs(price - state.ib_high) < (state.ib_high - state.ib_low) * 0.15:
                setattr(state, attr_type, "REJECTION_SHORT")
                setattr(state, attr_price, price)
            elif abs(price - state.ib_low) < (state.ib_high - state.ib_low) * 0.15:
                setattr(state, attr_type, "REJECTION_LONG")
                setattr(state, attr_price, price)

    detect_reversal(15, "rev15_type", "rev15_price")
    detect_reversal(22, "rev22_type", "rev22_price")

    # ── Effort vs Result (Wyckoff) ─────────────────────
    effort_signal = "NORMAL"
    if len(state.bars) >= 5:
        recent5 = state.bars[-5:]
        avg_vol  = sum(b.get("v", 0) for b in recent5[:-1]) / max(len(recent5) - 1, 1)
        avg_rng  = sum(abs(b.get("h", 0) - b.get("l", 0)) for b in recent5[:-1]) / max(len(recent5) - 1, 1)
        cur_vol  = bar.get("v", 0)
        cur_rng  = abs(hi - lo)

        if cur_vol > avg_vol * 1.6 and cur_rng < avg_rng * 0.5:
            effort_signal = "EFFORT_WITHOUT_RESULT"  # absorption
        elif cur_vol < avg_vol * 0.5 and cur_rng < avg_rng * 0.5:
            ses_high = ses.get("sh", 0)
            ses_low  = ses.get("sl", 0)
            mid      = (ses_high + ses_low) / 2 if ses_high and ses_low else price
            if price > mid:
                effort_signal = "NO_DEMAND"
            else:
                effort_signal = "NO_SUPPLY"
        elif cur_vol > avg_vol * 1.6 and cur_rng > avg_rng * 1.5:
            effort_signal = "EFFORT_WITH_RESULT"

    # ── CVD slope ──────────────────────────────────────
    cvd_trend = "NEUTRAL"
    d20 = cvd.get("d20", 0)
    if   d20 >  500: cvd_trend = "STRONGLY_BULLISH"
    elif d20 >  100: cvd_trend = "BULLISH"
    elif d20 < -500: cvd_trend = "STRONGLY_BEARISH"
    elif d20 < -100: cvd_trend = "BEARISH"

    # ── Approximate POC (session mode price) ──────────
    if len(state.bars) >= 10:
        price_vol: dict[int, float] = {}
        for b in state.bars:
            bh, bl, bv = b.get("h", 0), b.get("l", 0), b.get("v", 0)
            brange = bh - bl
            if brange > 0:
                steps = max(1, int(brange / 0.25))
                per_step = bv / steps
                p = bl
                while p <= bh + 0.001:
                    key = round(p * 4)
                    price_vol[key] = price_vol.get(key, 0) + per_step
                    p += 0.25
        if price_vol:
            state.poc_today = max(price_vol, key=price_vol.get) / 4.0

    # ── Build enriched payload ─────────────────────────
    enriched = {
        **raw,
        "features": {
            "cvd_trend":     cvd_trend,
            "effort":        effort_signal,
            "rev15":         state.rev15_type,
            "rev22":         state.rev22_type,
            "rev15_price":   state.rev15_price,
            "rev22_price":   state.rev22_price,
            "ib_high":       state.ib_high,
            "ib_low":        state.ib_low,
            "ib_locked":     state.ib_locked,
            "poc_today":     round(state.poc_today, 2),
            "poc_yest":      round(state.poc_yest,  2),
        }
    }
    return enriched


# ─────────────────────────────────────────────
#  Cloud Sender
# ─────────────────────────────────────────────
class CloudSender:
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=20)

    async def start(self):
        self._session = aiohttp.ClientSession(
            headers={"X-Bridge-Token": BRIDGE_TOKEN}
        )
        asyncio.create_task(self._send_loop())
        log.info(f"Cloud sender started → {CLOUD_URL}")

    async def push(self, payload: dict):
        try:
            self._queue.put_nowait(payload)
        except asyncio.QueueFull:
            pass  # drop oldest if queue full

    async def _send_loop(self):
        while True:
            try:
                payload = await asyncio.wait_for(self._queue.get(), timeout=5.0)
                await self._post(payload)
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                log.error(f"Send loop error: {e}")
            await asyncio.sleep(POST_INTERVAL)

    async def _post(self, payload: dict):
        try:
            async with self._session.post(
                f"{CLOUD_URL}/ingest",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=4.0)
            ) as resp:
                if resp.status not in (200, 201):
                    log.warning(f"Cloud returned {resp.status}")
        except Exception as e:
            log.debug(f"Post failed: {e}")

    async def close(self):
        if self._session:
            await self._session.close()


# ─────────────────────────────────────────────
#  Main Bridge Loop
# ─────────────────────────────────────────────
async def zmq_loop(sender: CloudSender):
    """
    ZeroMQ PULL — מקבל נתונים מ-Sierra Chart.
    Non-blocking ב-asyncio.
    """
    context = zmq.Context()
    socket  = context.socket(zmq.PULL)
    socket.connect(f"tcp://localhost:{ZMQ_PORT}")
    socket.setsockopt(zmq.RCVTIMEO, 100)  # 100ms timeout

    log.info(f"ZMQ PULL connected to localhost:{ZMQ_PORT}")

    last_send = 0.0

    while True:
        try:
            raw_bytes = socket.recv()
            raw = json.loads(raw_bytes)
            enriched = update_session(raw)

            now = time.time()
            if now - last_send >= POST_INTERVAL:
                await sender.push(enriched)
                last_send = now

                price = raw.get("bar", {}).get("c", 0)
                phase = raw.get("session", {}).get("phase", "?")
                log.info(f"→ Cloud | {phase} | {price:.2f} | "
                         f"CVD:{enriched['features']['cvd_trend']} | "
                         f"Effort:{enriched['features']['effort']} | "
                         f"Rev15:{enriched['features']['rev15']} | "
                         f"Rev22:{enriched['features']['rev22']}")

        except zmq.Again:
            await asyncio.sleep(0.05)
        except json.JSONDecodeError as e:
            log.error(f"JSON decode error: {e}")
        except Exception as e:
            log.error(f"ZMQ loop error: {e}")
            await asyncio.sleep(1.0)


async def main():
    log.info("=" * 50)
    log.info("  MEMS26 ZMQ Bridge — Starting")
    log.info(f"  ZMQ port    : {ZMQ_PORT}")
    log.info(f"  Cloud URL   : {CLOUD_URL}")
    log.info("=" * 50)

    sender = CloudSender()
    await sender.start()

    try:
        await zmq_loop(sender)
    finally:
        await sender.close()


if __name__ == "__main__":
    asyncio.run(main())
