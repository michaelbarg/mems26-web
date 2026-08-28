"""DALTON_EDGE_V1 — responsive reversal at Dalton termination points (T-118).

Michael's ruling (phone id a65f13aa, 2026-08-28 13:34 IL, chart IMG_3305):
"שנייצר תבנית כזאת שתתחיל לסחור היום לונג ושורט בנקודות סיום של דלתון...
תשים לב לקווים המקווקווים שבניתי עם הווליום... עם סטופ מתאים אפשר להתחיל
במימושים קרובים".

The specimen (2026-08-28 09:00 IL, globex, verified in v9_bars_5min_woodies):
session low 7731.00 touched at the end of a down-move, rejection close 7734.00
(close_pos 0.86), volume 885 vs preceding-SMA20 382.45 (×2.31 — crossed
Michael's dashed volume line). A V-reversal at a Dalton termination point:
excess at a local extreme on an above-average volume spike.

Anatomy (evaluated on the LAST closed bar, oldest→newest input):
  LONG:  the bar's low is the lowest low of the last N bars (N default 12 —
         "termination"; equal-low retest counts, double-bottom excess is
         textbook Dalton too) · rejection close in the top 40% of the bar
         (close >= low + 0.6×range, range >= 2.0 pts sanity) · volume
         confirmation: bar volume >= VOL_MULT × SMA20 of the PRECEDING 20
         bars (excluding the candidate — the spike must clear the average
         it did not inflate).
  SHORT: exact mirror at the highest high.
  Stop:  structural — beyond the extreme ∓ stop_buffer_pts (default 2.0);
         emitted as setup["stop"], which the trade manager copies into
         metadata.stop_initial (manager.py accept_setup) — the same channel
         ZLR's structural stop rides, so StopResolver/ladder machinery
         treats it natively.
  T1:    1R bank ("מימושים קרובים" — near take-profit; same t1_bank_r
         mechanism as edge_fade.build_edge_fade_setup) · T2 = 2R (the family
         degrade norm; the emit-path 3R clamp still applies downstream) ·
         T3 none.

Pure logic — no env, no I/O (edge_fade.py doctrine). The five_min_system
wiring gates on DALTON_EDGE_V1 (unset/"0" = OFF byte-identical · "shadow" =
metadata.shadow_only=True, gateway records-not-routes · "1"/"live" = live
path) and reads the tunables from env: DALTON_EDGE_LOOKBACK_N ·
DALTON_EDGE_VOL_MULT · DALTON_EDGE_STOP_BUFFER_PTS ·
DALTON_EDGE_SKIP_OPEN_BARS (opening-bars guard: skip candidates in the
first K RTH slots after the 9:30-ET open, default 3, 0=off — the 28.08
replay put every RTH loser on those volume-contaminated open bars).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

DEFAULT_LOOKBACK_N = 12       # "termination": extreme of the last ~hour
DEFAULT_VOL_MULT = 2.0        # bar volume >= 2× SMA20 (the dashed line)
DEFAULT_STOP_BUFFER_PTS = 2.0  # structural stop beyond the extreme
VOL_SMA_WINDOW = 20           # SMA window (preceding bars, candidate excluded)
MIN_BAR_RANGE_PTS = 2.0       # rejection needs a real bar, not a 2-tick coil
REJECT_CLOSE_FRAC = 0.6       # close in the far 40% of the bar's range


def _f(bar: Dict[str, Any], *keys: str) -> Optional[float]:
    # family convention (copied, not imported — failed_break.py precedent)
    for k in keys:
        v = bar.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def detect_dalton_edge(bars: List[Dict[str, Any]],
                       cfg: Optional[Dict[str, Any]] = None,
                       already_fired: Optional[Set[str]] = None,
                       ) -> Optional[Dict[str, Any]]:
    """Evaluate the LAST closed bar for a Dalton-termination reversal.

    `bars` = closed 5-min bars oldest→newest (continuous feed — the volume
    SMA deliberately crosses session boundaries, matching Michael's chart).
    `cfg` keys (all optional): lookback_n, vol_mult, stop_buffer_pts.
    Returns a trigger dict {type, direction, entry, stop, extreme, volume,
    vol_sma20, vol_ratio, lookback_n} or None. Honest failure: any missing
    OHLCV in the evaluation window → None (Rule 1 — no synthesis).
    """
    cfg = cfg or {}
    try:
        lookback_n = int(cfg.get("lookback_n") or DEFAULT_LOOKBACK_N)
        vol_mult = float(cfg.get("vol_mult") or DEFAULT_VOL_MULT)
        stop_buffer = float(cfg.get("stop_buffer_pts") or DEFAULT_STOP_BUFFER_PTS)
    except (TypeError, ValueError):
        return None
    if lookback_n < 2 or vol_mult <= 0:
        return None
    fired = already_fired or set()

    n = len(bars)
    if n < max(lookback_n, VOL_SMA_WINDOW + 1):
        return None

    cur = bars[-1]
    ch, cl = _f(cur, "h", "high"), _f(cur, "l", "low")
    cc, cv = _f(cur, "c", "close"), _f(cur, "v", "vol", "volume")
    if None in (ch, cl, cc, cv):
        return None
    bar_rng = ch - cl
    if bar_rng < MIN_BAR_RANGE_PTS:
        return None

    # volume confirmation: SMA20 of the PRECEDING 20 bars (candidate excluded)
    prev_vols = [_f(b, "v", "vol", "volume") for b in bars[-(VOL_SMA_WINDOW + 1):-1]]
    if any(v is None for v in prev_vols):
        return None
    vol_sma = sum(prev_vols) / float(VOL_SMA_WINDOW)
    if vol_sma <= 0 or cv < vol_mult * vol_sma:
        return None

    # termination window: the last N bars including the candidate
    window = bars[-lookback_n:-1]
    prev_highs = [_f(b, "h", "high") for b in window]
    prev_lows = [_f(b, "l", "low") for b in window]
    if any(v is None for v in prev_highs) or any(v is None for v in prev_lows):
        return None

    # ── LONG: lowest low of the last N bars + rejection close up ──
    if ("DALTON_EDGE_LONG" not in fired
            and cl <= min(prev_lows)
            and cc >= cl + REJECT_CLOSE_FRAC * bar_rng):
        return {
            "type": "DALTON_EDGE_LONG", "direction": "LONG",
            "entry": round(cc, 2), "stop": round(cl - stop_buffer, 2),
            "extreme": round(cl, 2), "volume": cv,
            "vol_sma20": round(vol_sma, 2),
            "vol_ratio": round(cv / vol_sma, 2), "lookback_n": lookback_n,
        }

    # ── SHORT: highest high of the last N bars + rejection close down ──
    if ("DALTON_EDGE_SHORT" not in fired
            and ch >= max(prev_highs)
            and cc <= ch - REJECT_CLOSE_FRAC * bar_rng):
        return {
            "type": "DALTON_EDGE_SHORT", "direction": "SHORT",
            "entry": round(cc, 2), "stop": round(ch + stop_buffer, 2),
            "extreme": round(ch, 2), "volume": cv,
            "vol_sma20": round(vol_sma, 2),
            "vol_ratio": round(cv / vol_sma, 2), "lookback_n": lookback_n,
        }
    return None


def build_dalton_edge_setup(trigger: Dict[str, Any],
                            contracts: int = 3,
                            shadow_only: bool = False,
                            t1_bank_r: float = 1.0) -> Dict[str, Any]:
    """Gateway-routable setup from a trigger. T1 = 1R bank ("מימושים
    קרובים"), T2 = 2R, T3 none — the edge_fade target mechanism, no parallel
    path. setup["stop"] carries the structural stop (→ metadata.stop_initial
    via the trade manager, the ZLR channel). shadow_only=True marks the
    setup for the gateway's record-not-route path (FAILED_BREAK precedent);
    parameterized like build_opening_setup so "1"/"live" stays live-capable.
    """
    entry = float(trigger["entry"])
    stop = float(trigger["stop"])
    direction = trigger["direction"]
    risk = abs(entry - stop)
    sign = 1.0 if direction == "LONG" else -1.0
    t1 = entry + sign * t1_bank_r * risk
    t2 = entry + sign * 2.0 * risk
    pat = trigger["type"]
    meta: Dict[str, Any] = {
        "pattern_id": pat,
        "pattern": pat,
        "source": "dalton_edge_v1",
        "extreme": trigger.get("extreme"),
        "volume": trigger.get("volume"),
        "vol_sma20": trigger.get("vol_sma20"),
        "vol_ratio": trigger.get("vol_ratio"),
        "lookback_n": trigger.get("lookback_n"),
    }
    if shadow_only:
        meta["shadow_only"] = True
    return {
        "firing_system": 2,
        "pattern": pat,
        "classification": pat,
        "direction": direction,
        "entry_price": round(entry, 2),
        "stop": round(stop, 2),
        "t1": round(t1, 2),
        "t2": round(t2, 2),
        "t3": None,
        "contracts": contracts,
        "confidence": 65,
        "metadata": meta,
    }
