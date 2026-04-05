"""
json_bridge.py — v5
- שומר נתוני זמן אמת ב-Redis (mems26:latest)
- צובר היסטוריית נרות 3m ב-Redis (mems26:candles) עד 960 נרות (48h)
- מעביר ישירות שדות חדשים מ-Study v5: woodies_cci, day_context, candle_patterns, volume_context
"""
import json, asyncio, aiohttp, os, logging, time
from datetime import datetime
from dataclasses import dataclass
from dotenv import load_dotenv
from pattern_scanner import scan_patterns

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("bridge")

SC_JSON_PATH    = os.getenv("SC_JSON_PATH", "/Users/michael/SierraChart2/Data/mes_ai_data.json")
SC_HISTORY_PATH = os.getenv("SC_HISTORY_PATH", "/Users/michael/SierraChart2/Data/mes_ai_history.json")
REDIS_URL       = os.getenv("UPSTASH_REDIS_REST_URL")
REDIS_TOKEN     = os.getenv("UPSTASH_REDIS_REST_TOKEN")
REDIS_KEY       = "mems26:latest"
REDIS_CANDLES   = "mems26:candles"
REDIS_PATTERNS  = "mems26:patterns"
MAX_CANDLES     = 960
POST_INTERVAL   = 1.0
CANDLE_INTERVAL = 180

@dataclass
class SessionState:
    date: str = ""
    daily_open: float = 0.0
    daily_open_set: bool = False
    overnight_high: float = 0.0
    overnight_low: float = 999999.0
    overnight_done: bool = False
    rev15_type: str = "NONE"
    rev22_type: str = "NONE"
    rev15_price: float = 0.0
    rev22_price: float = 0.0

@dataclass
class CandleBuilder:
    start_ts: int = 0
    o: float = 0.0
    h: float = 0.0
    l: float = 999999.0
    c: float = 0.0
    buy: float = 0.0
    sell: float = 0.0
    vol: float = 0.0
    cci14: float = 0.0
    cci6: float = 0.0
    vwap: float = 0.0
    phase: str = ""
    above_vwap: bool = False
    liq_sweep_long: bool = False
    liq_sweep_short: bool = False

    def update(self, price, buy, sell, vol):
        if self.o == 0: self.o = price
        if price > self.h: self.h = price
        if price < self.l: self.l = price
        self.c    = price
        self.buy  = buy   # SET — Sierra כבר מצבר עבורנו
        self.sell = sell
        self.vol  = vol

    def to_dict(self):
        return {
            "ts": self.start_ts,
            "o": self.o, "h": self.h, "l": self.l, "c": self.c,
            "buy": self.buy, "sell": self.sell,
            "vol": self.vol,
            "delta": self.buy - self.sell,
            "cci14": round(self.cci14, 2),
            "cci6": round(self.cci6, 2),
            "vwap": round(self.vwap, 2),
            "phase": self.phase,
            "above_vwap": self.above_vwap,
            "liq_sweep_long": self.liq_sweep_long,
            "liq_sweep_short": self.liq_sweep_short,
        }

state  = SessionState()
candle = CandleBuilder()

# ── Trade Tracker — זיהוי עסקאות אוטומטי מ-Sierra ─────────────────────────
class TradeTracker:
    def __init__(self):
        self.seen_fill_ts: set = set()
        self.open_trade: dict = None
        self.position: float = 0.0
        self.last_stop: float = 0.0    # סטופ אחרון מDOM
        self.t1_hit: bool = False       # האם T1 כבר נלחץ

    def check_exit_levels(self, price: float) -> list:
        """בודק כל tick אם המחיר הגיע לסטופ או לטארגט — מחזיר אירועי אזהרה"""
        if not self.open_trade: return []
        events = []
        side  = self.open_trade.get("side", "")
        stop  = self.open_trade.get("stop", 0)
        t1    = self.open_trade.get("t1", 0)
        t2    = self.open_trade.get("t2", 0)
        entry = self.open_trade.get("entry_price", 0)

        if not entry: return []

        pnl_pts = (price - entry) if side == "LONG" else (entry - price)
        risk    = abs(entry - stop) if stop else 0

        # התראת סטופ קרוב (75% מהדרך לסטופ)
        if stop and risk > 0:
            dist_to_stop = abs(price - stop)
            if dist_to_stop < risk * 0.25:
                events.append({"type": "STOP_NEAR", "price": price, "stop": stop,
                                "dist": round(dist_to_stop, 2)})

        # T1 נלחץ
        if t1 and not self.t1_hit:
            if (side == "LONG" and price >= t1) or (side == "SHORT" and price <= t1):
                self.t1_hit = True
                events.append({"type": "T1_HIT", "price": price, "t1": t1,
                                "pnl_pts": round(pnl_pts, 2),
                                "pnl_usd": round(pnl_pts * 5 * self.open_trade.get("qty",1), 2)})

        # T2 נלחץ
        if t2:
            if (side == "LONG" and price >= t2) or (side == "SHORT" and price <= t2):
                events.append({"type": "T2_HIT", "price": price, "t2": t2,
                                "pnl_pts": round(pnl_pts, 2),
                                "pnl_usd": round(pnl_pts * 5 * self.open_trade.get("qty",1), 2)})

        return events

    def process_fills(self, fills: list, price: float, market_ctx: dict, stop_price: float = 0.0) -> list:
        """
        מקבל רשימת fills מSierra, מחזיר אירועים:
        OPEN | ADD | PARTIAL_EXIT | CLOSE | STOP_NEAR | T1_HIT | T2_HIT
        """
        events = []
        for f in fills:
            ts  = f.get("ts", 0)
            qty = f.get("qty", 0)
            fp  = f.get("price", 0)
            sid = f.get("side", "")
            pos = f.get("pos", 0)

            if ts in self.seen_fill_ts or ts == 0 or fp == 0:
                continue
            self.seen_fill_ts.add(ts)

            direction = 1 if sid == "BUY" else -1
            prev_pos  = self.position
            self.position = pos if pos != 0 else self.position + direction * abs(qty)

            # פתיחת עסקה חדשה
            if prev_pos == 0 and self.position != 0:
                side = "LONG" if self.position > 0 else "SHORT"
                # חשב T1/T2 אוטומטי לפי סטופ (R:R 1:1 ו-1:2)
                risk = abs(fp - stop_price) if stop_price else 0
                t1_auto = (fp + risk) if side == "LONG" else (fp - risk) if risk else 0
                t2_auto = (fp + risk*2) if side == "LONG" else (fp - risk*2) if risk else 0
                self.t1_hit = False
                self.open_trade = {
                    "id":          str(ts),
                    "ts_open":     ts,
                    "side":        side,
                    "entry_price": fp,
                    "qty":         abs(qty),
                    "stop":        stop_price,
                    "t1":          round(t1_auto, 2),
                    "t2":          round(t2_auto, 2),
                    "setup":       "Sierra Auto",
                    "status":      "OPEN",
                    "fills":       [f],
                    "exit_price":  None,
                    "pnl_pts":     None,
                    "pnl_usd":     None,
                    "rr_planned":  1.0 if risk else 0,
                    "ctx":         market_ctx,
                }
                events.append({"type": "OPEN", "trade": dict(self.open_trade)})
                log.info(f"Trade OPEN: {side} {abs(qty)} @ {fp} stop={stop_price} T1={t1_auto:.2f} T2={t2_auto:.2f}")

            # הגדלת פוזיציה
            elif prev_pos != 0 and abs(self.position) > abs(prev_pos) and (
                (self.position > 0 and direction > 0) or
                (self.position < 0 and direction < 0)
            ):
                if self.open_trade:
                    prev_qty = self.open_trade.get("qty", 0)
                    prev_ep  = self.open_trade.get("entry_price", fp)
                    new_qty  = prev_qty + abs(qty)
                    avg_ep   = (prev_ep * prev_qty + fp * abs(qty)) / new_qty
                    self.open_trade["entry_price"] = round(avg_ep, 4)
                    self.open_trade["qty"]         = new_qty
                    self.open_trade["fills"].append(f)
                    events.append({"type": "ADD", "trade": dict(self.open_trade)})
                    log.info(f"Trade ADD: +{abs(qty)} @ {fp} avg={avg_ep:.2f}")

            # יציאה חלקית
            elif prev_pos != 0 and self.position != 0 and abs(self.position) < abs(prev_pos):
                if self.open_trade:
                    partial_pnl = ((fp - self.open_trade["entry_price"]) if self.open_trade["side"] == "LONG"
                                   else (self.open_trade["entry_price"] - fp))
                    self.open_trade["fills"].append(f)
                    self.open_trade["partial_exit_price"] = fp
                    self.open_trade["partial_pnl_pts"] = round(partial_pnl, 2)
                    events.append({"type": "PARTIAL_EXIT", "trade": dict(self.open_trade),
                                   "partial_price": fp, "partial_qty": abs(qty),
                                   "partial_pnl_pts": round(partial_pnl, 2),
                                   "partial_pnl_usd": round(partial_pnl * 5, 2)})
                    log.info(f"Trade PARTIAL: {abs(qty)} @ {fp} pnl={partial_pnl:+.2f}pt")

            # סגירה מלאה
            elif prev_pos != 0 and self.position == 0:
                if self.open_trade:
                    side    = self.open_trade["side"]
                    entry   = self.open_trade["entry_price"]
                    stop    = self.open_trade.get("stop", 0)
                    pnl_pts = round((fp - entry) if side == "LONG" else (entry - fp), 4)
                    pnl_usd = round(pnl_pts * 5 * self.open_trade["qty"], 2)
                    # זיהוי מדויק של סוג יציאה
                    if stop and abs(fp - stop) < 0.5:
                        exit_type = "STOP"
                    elif pnl_pts > 0:
                        exit_type = "TARGET" if self.t1_hit else "MANUAL_WIN"
                    else:
                        exit_type = "MANUAL_LOSS"
                    closed = {
                        **self.open_trade,
                        "status":      "CLOSED",
                        "exit_price":  fp,
                        "ts_close":    ts,
                        "pnl_pts":     pnl_pts,
                        "pnl_usd":     pnl_usd,
                        "exit_type":   exit_type,
                        "fills":       self.open_trade["fills"] + [f],
                    }
                    events.append({"type": "CLOSE", "trade": closed})
                    log.info(f"Trade CLOSE: {side} {pnl_pts:+.2f}pt ${pnl_usd:+.2f} [{exit_type}]")
                    self.open_trade = None
                    self.t1_hit = False

        return events

trade_tracker = TradeTracker()


def enrich(raw):
    global state

    today   = datetime.fromtimestamp(raw["timestamp"]).strftime("%Y-%m-%d")
    ses     = raw.get("session_phase", "OVERNIGHT")
    price   = raw.get("current_price", 0)
    ses_min = raw.get("session_min", -1)

    # ── Session state ─────────────────────────────────────────
    if today != state.date:
        log.info(f"New session: {today}")
        state = SessionState(date=today)

    if ses == "OVERNIGHT" and not state.overnight_done:
        if price > state.overnight_high: state.overnight_high = price
        if price < state.overnight_low:  state.overnight_low  = price

    if ses == "OPEN" and not state.daily_open_set:
        state.daily_open = price
        state.daily_open_set = True
        state.overnight_done = True
        log.info(f"Daily open: {price:.2f}")

    # ── Reversal detection (15m / 22m) ───────────────────────
    dc_study = raw.get("day_context", {})
    ibh = dc_study.get("ib_high", 0)
    ibl = dc_study.get("ib_low", 0)
    for mark, at, ap in [(15,"rev15_type","rev15_price"),(22,"rev22_type","rev22_price")]:
        if ses_min >= mark and getattr(state,at) == "NONE" and ibh and ibl:
            if price > ibh + 0.25:
                setattr(state,at,"FAILED_BREAK_SHORT"); setattr(state,ap,price)
                log.info(f"Rev{mark}: FAILED_BREAK_SHORT @ {price:.2f}")
            elif price < ibl - 0.25:
                setattr(state,at,"FAILED_BREAK_LONG"); setattr(state,ap,price)
                log.info(f"Rev{mark}: FAILED_BREAK_LONG @ {price:.2f}")

    # ── Pull directly from Study ──────────────────────────────
    mtf     = raw.get("mtf", {})
    m3      = mtf.get("m3", {})
    m15     = mtf.get("m15", {})
    m30     = mtf.get("m30", {})
    m60     = mtf.get("m60", {})
    cvd     = raw.get("cvd", {})
    vwap_d  = raw.get("vwap", {})
    mp      = raw.get("market_profile", {})
    wp      = raw.get("woodi_pivots", {})
    tl      = raw.get("time_levels", {})
    of_data = raw.get("order_flow", {})
    cci     = raw.get("woodies_cci", {})       # ← חדש
    vol_ctx = raw.get("volume_context", {})    # ← חדש
    candle_p= raw.get("candle_patterns", {})  # ← חדש

    # Day context — מה-Study ישירות
    day_type    = dc_study.get("day_type", "DEVELOPING")
    ib_locked   = dc_study.get("ib_locked", False)
    ib_range    = dc_study.get("ib_range", 0)
    gap_type    = dc_study.get("gap_type", "FLAT")
    gap         = dc_study.get("gap", 0)
    total_ext   = dc_study.get("total_ext", 0)
    or_high     = dc_study.get("or_high", 0)
    or_low      = dc_study.get("or_low", 0)
    returned    = dc_study.get("returned_after_break", False)

    d20 = cvd.get("change_20bar", 0)
    cvd_trend = "BULLISH" if d20 > 100 else "BEARISH" if d20 < -100 else "NEUTRAL"

    ovl = state.overnight_low if state.overnight_low < 999999 else 0
    above_open = (price > state.daily_open) if state.daily_open_set else None

    return {
        "ts":    raw["timestamp"],
        "sym":   "MEMS26",
        "price": price,

        # נר 3m נוכחי
        "bar": {
            "o": m3.get("o", price), "h": m3.get("h", price),
            "l": m3.get("l", price), "c": price,
            "vol": m3.get("vol", 0), "buy": m3.get("buy", 0),
            "sell": m3.get("sell", 0), "delta": m3.get("delta", 0),
        },

        # MTF
        "mtf": {"m3": m3, "m15": m15, "m30": m30, "m60": m60},

        # CVD
        "cvd": {
            "total":    cvd.get("current", 0),
            "d20":      d20,
            "d5":       cvd.get("change_5bar", 0),
            "bull":     cvd.get("trend", "") == "BULLISH",
            "trend":    cvd_trend,
            "buy_vol":  cvd.get("buy_vol", 0),
            "sell_vol": cvd.get("sell_vol", 0),
            "delta":    cvd.get("delta", 0),
            "m15_delta":m15.get("delta", 0),
            "m60_delta":m60.get("delta", 0),
        },

        # VWAP
        "vwap": vwap_d,

        # Woodies CCI — ישירות מה-Study ← חדש
        "woodies_cci": cci,

        # Session
        "session": {
            "phase":     ses,
            "min":       ses_min,
            "sh":        mp.get("session_high", price),
            "sl":        mp.get("session_low", price),
            "ibh":       ibh,
            "ibl":       ibl,
            "ib_locked": ib_locked,
        },

        # Market Profile + Prev Day POC ← חדש
        "profile": {
            "poc":          mp.get("poc", 0),
            "vah":          mp.get("vah", 0),
            "val":          mp.get("val", 0),
            "tpo_poc":      mp.get("tpo_poc", 0),
            "prev_day_poc": mp.get("prev_day_poc", 0),  # ← חדש
            "in_va":        mp.get("in_value_area", False),
            "above_poc":    mp.get("above_poc", False),
        },

        # Woodi Pivots
        "woodi": {
            "pp": wp.get("pp", 0), "r1": wp.get("r1", 0), "r2": wp.get("r2", 0),
            "s1": wp.get("s1", 0), "s2": wp.get("s2", 0),
            "above_pp": wp.get("above_pp", False),
        },

        # Levels
        "levels": {
            "h72": tl.get("h72_high", 0),       "l72": tl.get("h72_low", 0),
            "hwk": tl.get("weekly_high", 0),    "lwk": tl.get("weekly_low", 0),
            "prev_high":  tl.get("prev_high", 0),
            "prev_low":   tl.get("prev_low", 0),
            "prev_close": tl.get("prev_close", 0),
            "daily_open": tl.get("daily_open", state.daily_open),
            "overnight_high": tl.get("overnight_high", state.overnight_high),
            "overnight_low":  tl.get("overnight_low", ovl),
            "above_open": above_open,
        },

        # Order Flow
        "order_flow": {
            "absorption_bull":  of_data.get("absorption_bull", False),
            "liq_sweep":        of_data.get("liq_sweep_long", False),   # backward compat
            "liq_sweep_long":   of_data.get("liq_sweep_long", False),
            "liq_sweep_short":  of_data.get("liq_sweep_short", False),  # ← חדש
            "imbalance_bull":   sum(1 for i in of_data.get("imbalances",[]) if i.get("ratio",0)>0),
            "imbalance_bear":   sum(1 for i in of_data.get("imbalances",[]) if i.get("ratio",0)<0),
            "imbalances":       of_data.get("imbalances", []),
        },

        # Day Context — מה-Study ← מורחב
        "day": {
            "type":           day_type,
            "ib_range":       ib_range,
            "ib_locked":      ib_locked,
            "gap":            gap,
            "gap_type":       gap_type,
            "total_ext":      total_ext,
            "returned":       returned,
            "or_high":        or_high,
            "or_low":         or_low,
            "range":          round(mp.get("session_high", 0) - mp.get("session_low", 0), 2),
        },

        # Volume Context ← חדש
        "volume_context": vol_ctx,

        # Candle Patterns ← חדש
        "candle_patterns": candle_p,

        # Order Fills — פקודות שבוצעו
        "order_fills": raw.get("order_fills", []),

        # Open Orders — סטופים ו-orders ממתינים
        "open_orders": raw.get("open_orders", []),

        # Footprint — 10 נרות אחרונים
        "footprint": raw.get("footprint", []),

        # Reversal
        "reversal": {
            "ib_high":    ibh,
            "ib_low":     ibl,
            "locked":     ib_locked,
            "rev15_type": state.rev15_type,
            "rev15_price":state.rev15_price,
            "rev22_type": state.rev22_type,
            "rev22_price":state.rev22_price,
        },
    }


async def redis_post(http, path, data):
    """Send data as JSON body (aiohttp serializes dict/list/str → JSON)."""
    try:
        async with http.post(
            f"{REDIS_URL}/{path}",
            headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
            json=data,
            timeout=aiohttp.ClientTimeout(total=4.0)
        ) as resp:
            if resp.status != 200:
                log.warning(f"Redis {path} {resp.status}")
    except Exception as e:
        log.warning(f"Redis failed ({path}): {e}")


async def redis_post_raw(http, path, raw_json_str: str):
    """Send a pre-serialized JSON string as body — avoids double-encoding."""
    try:
        async with http.post(
            f"{REDIS_URL}/{path}",
            headers={"Authorization": f"Bearer {REDIS_TOKEN}",
                     "Content-Type": "application/json"},
            data=raw_json_str,
            timeout=aiohttp.ClientTimeout(total=4.0)
        ) as resp:
            if resp.status != 200:
                log.warning(f"Redis raw {path} {resp.status}")
    except Exception as e:
        log.warning(f"Redis raw failed ({path}): {e}")


async def save_candle(http, c: CandleBuilder, raw: dict = None):
    # העשר נר עם נתוני indicators לפני שמירה
    if raw:
        cci  = raw.get("woodies_cci", {})
        vwap = raw.get("vwap", {})
        of2  = raw.get("order_flow", {})
        sess = raw.get("session", {})
        c.cci14           = float(cci.get("cci14", 0) or 0)
        c.cci6            = float(cci.get("cci6", 0) or 0)
        c.vwap            = float(vwap.get("value", 0) or 0)
        c.phase           = str(sess.get("phase", ""))
        c.above_vwap      = bool(vwap.get("above", False))
        c.liq_sweep_long  = bool(of2.get("liq_sweep_long", False))
        c.liq_sweep_short = bool(of2.get("liq_sweep_short", False))
    candle_dict = c.to_dict()
    candle_json = json.dumps(candle_dict)
    # Use data= (not json=) to avoid double-encoding the already-serialized string
    await redis_post_raw(http, f"lpush/{REDIS_CANDLES}", candle_json)
    await redis_post(http, f"ltrim/{REDIS_CANDLES}/0/{MAX_CANDLES-1}", "")
    log.info(f"Candle saved: {c.c:.2f} Δ={c.buy-c.sell:.0f} CCI14={c.cci14:.1f} VWAP={c.vwap:.2f}")


async def main():
    if not REDIS_URL or not REDIS_TOKEN:
        log.error("Missing UPSTASH credentials"); return

    log.info("="*50)
    log.info("  MEMS26 Bridge v6 — Full Data + History 960")
    log.info(f"  SC JSON    : {SC_JSON_PATH}")
    log.info(f"  SC HISTORY : {SC_HISTORY_PATH}")
    log.info(f"  Redis      : {REDIS_URL}")
    log.info("="*50)

    # ── טעינת היסטוריה ─────────────────────────────────────────
    # אסטרטגיה:
    # 1. אם קובץ Sierra טרי — טען ממנו (מחליף את Redis)
    # 2. אם לא — השאר את מה שכבר ב-Redis (נרות מצטברים)
    # 3. נרות חדשים תמיד מתווספים ב-lpush (חדש בהתחלה)
    async with aiohttp.ClientSession() as http:
        try:
            loaded_from_file = False
            if os.path.exists(SC_HISTORY_PATH):
                age_h = time.time() - os.path.getmtime(SC_HISTORY_PATH)
                if age_h < 604800:  # קובץ עד שעתיים
                    with open(SC_HISTORY_PATH) as hf:
                        hist = json.load(hf)
                    candles_list = hist.get("candles", [])
                    if candles_list:
                        log.info(f"Loading {len(candles_list)} historical candles → Redis...")
                        await redis_post(http, f"del/{REDIS_CANDLES}", "")
                        loaded = 0
                        for c in candles_list[:MAX_CANDLES]:
                            cj = json.dumps(c) if isinstance(c, dict) else str(c)
                            await redis_post_raw(http, f"rpush/{REDIS_CANDLES}", cj)
                            loaded += 1
                        await redis_post(http, f"ltrim/{REDIS_CANDLES}/0/{MAX_CANDLES-1}", "")
                        log.info(f"History loaded: {loaded} candles from file → Redis OK")
                        loaded_from_file = True
                else:
                    log.info(f"History file too old ({age_h/3600:.1f}h), keeping existing Redis candles")

            if not loaded_from_file:
                # בדוק כמה נרות כבר ב-Redis
                try:
                    async with http.get(
                        f"{REDIS_URL}/llen/{REDIS_CANDLES}",
                        headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
                        timeout=aiohttp.ClientTimeout(total=3.0)
                    ) as resp:
                        result = await resp.json()
                        existing = result.get("result", 0)
                        log.info(f"Redis has {existing} existing candles — will append new ones")
                except Exception:
                    log.info("Could not check Redis candle count — will append new ones")

        except Exception as e:
            log.warning(f"History load failed: {e}")

    last_send = 0.0
    last_pattern_scan = 0.0
    PATTERN_SCAN_INTERVAL = 60  # seconds
    candle = CandleBuilder()  # local candle for this session
    footprint_seeded = False   # האם כבר טענו footprint מ-Sierra

    async with aiohttp.ClientSession() as http:
        while True:
            try:
                with open(SC_JSON_PATH) as f:
                    raw = json.load(f)

                age = time.time() - os.path.getmtime(SC_JSON_PATH)
                if age > 30:
                    log.warning(f"Stale ({age:.0f}s)")
                    wall_ts   = int(time.time())
                    candle_ts = (wall_ts // CANDLE_INTERVAL) * CANDLE_INTERVAL
                    if candle.start_ts != 0 and candle_ts > candle.start_ts:
                        candle = CandleBuilder()
                        candle.start_ts = candle_ts
                    await asyncio.sleep(1); continue

                price = raw.get("current_price", 0)
                m3    = raw.get("mtf", {}).get("m3", {})
                buy   = m3.get("buy", 0)
                sell  = m3.get("sell", 0)
                vol   = m3.get("vol", 0)
                ts    = raw.get("timestamp", 0)

                # ── Seed from Sierra footprint (once) ────────
                # footprint = 10 recent 3m candles from Sierra Chart
                # Push any that are newer than what's already in Redis
                if not footprint_seeded:
                    footprint_seeded = True
                    fp_bars = raw.get("footprint", [])
                    if fp_bars:
                        # Get newest candle ts from Redis
                        newest_redis_ts = 0
                        try:
                            async with http.get(
                                f"{REDIS_URL}/lrange/{REDIS_CANDLES}/0/0",
                                headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
                                timeout=aiohttp.ClientTimeout(total=3.0)
                            ) as resp:
                                result = await resp.json()
                                items = result.get("result", [])
                                if items:
                                    c = items[0]
                                    while isinstance(c, str):
                                        c = json.loads(c)
                                    newest_redis_ts = c.get("ts", 0) if isinstance(c, dict) else 0
                        except Exception:
                            pass

                        # Push footprint candles that are newer than Redis
                        fp_sorted = sorted(fp_bars, key=lambda x: x.get("ts", 0))
                        seeded = 0
                        for bar in fp_sorted:
                            bar_ts = bar.get("ts", 0)
                            if bar_ts > newest_redis_ts:
                                cj = json.dumps(bar)
                                await redis_post_raw(http, f"lpush/{REDIS_CANDLES}", cj)
                                seeded += 1
                        if seeded:
                            await redis_post(http, f"ltrim/{REDIS_CANDLES}/0/{MAX_CANDLES-1}", "")
                            log.info(f"Seeded {seeded} candles from Sierra footprint")
                        else:
                            log.info(f"Footprint: {len(fp_bars)} bars, all already in Redis")

                # ── Candle Building — לפי זמן מחשב אמיתי ────
                wall_ts   = int(time.time())
                candle_ts = (wall_ts // CANDLE_INTERVAL) * CANDLE_INTERVAL

                if candle.start_ts == 0:
                    candle.start_ts = candle_ts
                    candle.update(price, buy, sell, vol)
                elif candle_ts > candle.start_ts:
                    await save_candle(http, candle, raw)
                    candle = CandleBuilder()
                    candle.start_ts = candle_ts
                    candle.update(price, buy, sell, vol)
                else:
                    candle.update(price, buy, sell, vol)

                # ── Send to Redis ─────────────────────────────
                now = time.time()
                if now - last_send >= POST_INTERVAL:
                    payload = enrich(raw)
                    payload["current_candle"] = candle.to_dict()
                    payload["wall_ts"] = int(time.time())
                    await redis_post(http, f"set/{REDIS_KEY}", payload)
                    last_send = now
                    day_type = payload["day"]["type"]
                    log.info(f"-> {raw.get('session_phase','?')} | {price:.2f} | {day_type} | buy={buy:.0f} sell={sell:.0f}")

                # ── Trade Detection ───────────────────────────
                fills = raw.get("order_fills", [])
                open_orders = raw.get("open_orders", [])

                # זיהוי סטופ מה-open orders
                stop_price = 0.0
                for o in open_orders:
                    if o.get("type") in ("STOP", "STOP_LIMIT"):
                        stop_price = o.get("price1", 0)
                        break

                if fills:
                    ctx = {
                        "day_type":    raw.get("day_context", {}).get("day_type", ""),
                        "phase":       raw.get("session_phase", ""),
                        "session_min": raw.get("session_min", -1),
                        "vwap_above":  raw.get("vwap", {}).get("above", False),
                        "cci14":       raw.get("woodies_cci", {}).get("cci14", 0),
                        "cvd_trend":   raw.get("cvd", {}).get("trend", ""),
                    }
                    events = trade_tracker.process_fills(fills, price, ctx, stop_price)
                    for ev in events:
                        trade = ev["trade"]
                        API_URL_LOCAL = os.getenv("API_URL", "http://localhost:8000")
                        BRIDGE_TOKEN_LOCAL = os.getenv("BRIDGE_TOKEN", "michael-mems26-2026")
                        try:
                            if ev["type"] == "CLOSE":
                                async with http.delete(
                                    f"{API_URL_LOCAL}/trades/{trade['id']}",
                                    headers={"x-bridge-token": BRIDGE_TOKEN_LOCAL},
                                    timeout=aiohttp.ClientTimeout(total=5.0)
                                ) as _: pass
                            async with http.post(
                                f"{API_URL_LOCAL}/trades",
                                json=trade,
                                headers={"x-bridge-token": BRIDGE_TOKEN_LOCAL, "content-type": "application/json"},
                                timeout=aiohttp.ClientTimeout(total=5.0)
                            ) as resp:
                                if resp.status == 200:
                                    log.info(f"Trade {ev['type']} → API OK")
                        except Exception as e:
                            log.warning(f"Trade API failed: {e}")

                # עדכון סטופ בעסקה פתוחה בזמן אמת
                elif stop_price > 0 and trade_tracker.open_trade:
                    if trade_tracker.open_trade.get("stop") != stop_price:
                        trade_tracker.open_trade["stop"] = stop_price
                        log.info(f"Stop updated: {stop_price}")

                # ── Pattern scan כל 60 שניות ────────────────
                if now - last_pattern_scan > PATTERN_SCAN_INTERVAL:
                    try:
                        async with http.get(
                            f"{REDIS_URL}/lrange/{REDIS_CANDLES}/0/{MAX_CANDLES-1}",
                            headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
                            timeout=aiohttp.ClientTimeout(total=5.0)
                        ) as resp:
                            result = await resp.json()
                            items = result.get("result", [])
                            all_candles = []
                            for item in items:
                                c = item
                                while isinstance(c, str):
                                    c = json.loads(c)
                                if isinstance(c, dict):
                                    all_candles.append(c)
                            if all_candles:
                                patterns = scan_patterns(all_candles)
                                await redis_post(http, f"set/{REDIS_PATTERNS}", json.dumps(patterns))
                                if patterns:
                                    log.info(f"[Pattern] {len(patterns)} detected: {[p['pattern'] for p in patterns]}")
                        last_pattern_scan = now
                    except Exception as e:
                        log.warning(f"[Pattern Error] {e}")

                # ── מעקב מחיר לסטופ/טארגט ───────────────────
                level_events = trade_tracker.check_exit_levels(price)
                for ev in level_events:
                    if ev["type"] == "STOP_NEAR":
                        log.warning(f"⚠ STOP NEAR! price={price} stop={ev['stop']} dist={ev['dist']}")
                    elif ev["type"] == "T1_HIT":
                        log.info(f"✅ T1 HIT @ {ev['price']} pnl={ev['pnl_pts']:+.2f}pt ${ev['pnl_usd']:+.2f}")
                    elif ev["type"] == "T2_HIT":
                        log.info(f"🎯 T2 HIT @ {ev['price']} pnl={ev['pnl_pts']:+.2f}pt ${ev['pnl_usd']:+.2f}")

            except FileNotFoundError:
                log.warning("JSON not found")
            except json.JSONDecodeError:
                pass
            except Exception as e:
                log.error(f"Error: {e}")
            await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(main())
