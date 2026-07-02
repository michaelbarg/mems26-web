"""
MEMS26 - Reactive-Long Detector Library
Strategic-Architect spec for Claude Code (CC). v0.1
WHAT THIS IS
  Boolean detectors for the reactive-long pattern and its variations, on 5-min
  bars, for MES. Each detector inspects a short rolling buffer of closed bars and
  returns a Setup (entry / stop / T1-T3) or None. A master scan() routes by the
  day-type regime: reversal family in BALANCE, continuation family in TREND_UP,
  opening family during the opening window.
NON-NEGOTIABLES
  * Compute CVD / per-bar delta / footprint imbalance on ES (the liquid leg) and
    EXECUTE on MES. MES order flow is too thin to threshold directly.
  * Every number in DetectorConfig is a CALIBRATION TARGET, not a constant. Fit on
    >=24h of ES RTH order-flow data (London + NY Open + NY Close) before locking.
    No threshold changes off a single session (MEMS26 data-first rule).
  * A detector firing is necessary, not sufficient: passes_entry_gate() must also
    hold (qualifying VP level nearby, LSMA reclaim, no news, correct regime).
ROBUSTNESS TIERS (automate in this order)
  A  double_bottom_div, one_two_three_low, hidden_div   (clean structure + invalidation)
  B  spring, absorption, pullback_flag                   (strong; threshold-sensitive)
  C  climax, bullish_engulfing, b_shape_flush            (high payoff; loose/rare; refinement)
  D  poor_low_retest, open_test_drive, open_rejection_reverse  (context-dependent)
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence, Tuple
# --------------------------------------------------------------------------- #
# Data structures
# --------------------------------------------------------------------------- #
@dataclass
class Bar:
    t: int        # bar open time, epoch seconds
    o: float
    h: float
    l: float
    c: float
    volume: float  # total bar volume (ES)
    delta: float   # per-bar net delta (ES): ask-initiated minus bid-initiated
    cvd: float     # session cumulative delta at this bar's close (the "buffer")
@dataclass
class Levels:
    dpoc: float    # developing (today) POC
    dvah: float
    dval: float
    ppoc: float    # prior-day POC
    pvah: float
    pval: float
    ib_high: float
    ib_low: float
    vwap: float
    lsma: float        # 5-min LSMA endpoint
    lsma_slope: float  # LSMA[-1] - LSMA[-2], index pts
    pday_high: float = 0.0
    naked_pocs: Sequence[float] = ()
class Regime(Enum):
    BALANCE = "balance"      # fade enabled (reversal family)
    TREND_UP = "trend_up"    # with-trend longs only (continuation family)
    TREND_DOWN = "trend_down"
    UNDECIDED = "undecided"
@dataclass
class Context:
    regime: Regime
    atr5: float                  # ATR(14) of 5-min bars, index pts
    median_vol20: float          # median volume of last 20 bars (ES)
    tick: float = 0.25           # MES tick size, index pts
    point_value: float = 5.0     # $/point MES
    news_blackout: bool = False  # True within +/- window of a release
    opening_window: bool = False
    session_open: float = 0.0
@dataclass
class DetectorConfig:
    # --- shared gate ---
    vp_level_max_ticks: int = 15      # structure low must be within N ticks of a VP level
    require_lsma_reclaim: bool = True
    # --- swing / pivot ---
    pivot_lookback: int = 3           # bars each side for a swing pivot
    equal_low_ticks: int = 6          # |low2-low1| <= this => "equal" low
    # --- volume / absorption ---
    vol_spike_mult: float = 2.0       # key-bar volume >= mult * median_vol20
    climax_vol_mult: float = 3.0      # climax bar volume >= mult * median_vol20
    absorption_range_atr: float = 0.5  # absorption bar range <= this * atr5
    long_wick_frac: float = 0.55      # lower wick >= frac of bar range => tail/pin
    poor_low_wick_frac: float = 0.15  # lower wick <= frac of range => "poor" (no excess)
    # --- imbalance (footprint, computed on ES) ---
    imbalance_ratio: float = 3.0      # diagonal bid/ask >= 3:1
    imbalance_min_abs: float = 50.0   # min absolute contracts (ES)
    stacked_levels: int = 3
    # --- delta flip / reclaim ---
    flip_ratio: float = 0.6           # reclaim_delta >= ratio * |adverse (sell) delta|
    # --- divergence magnitude ---
    div_min_frac: float = 0.20        # CVD low gap >= frac * recent CVD range
    cvd_range_lookback: int = 20
    # --- stops (index pts) ---
    stop_buffer_ticks: int = 2        # beyond the structural extreme
    stop_min_pts: float = 4.0
    stop_max_pts: float = 12.0
    # --- targets ---
    min_rr_overall: float = 1.5       # whole-trade R:R, checked against T3
    buffer_bars: int = 12             # rolling window unit detectors inspect
@dataclass
class Setup:
    name: str
    tier: str               # "A".."D"
    family: str             # "reversal" | "continuation" | "opening"
    side: str               # "long"
    entry: float
    stop: float
    t1: float
    t2: float
    t3: float
    note: str = ""
# --------------------------------------------------------------------------- #
# Primitives
# --------------------------------------------------------------------------- #
def _rng(b: Bar) -> float:
    return max(b.h - b.l, 1e-9)
def _lower_wick(b: Bar) -> float:
    return min(b.o, b.c) - b.l
def _upper_half_close(b: Bar) -> bool:
    return b.c >= (b.l + b.h) / 2.0
def _bull(b: Bar) -> bool:
    return b.c > b.o
def _bear(b: Bar) -> bool:
    return b.c < b.o
def _is_swing_low(bars: Sequence[Bar], i: int, k: int) -> bool:
    if i - k < 0 or i + k >= len(bars):
        return False
    return all(bars[i].l <= bars[j].l for j in range(i - k, i + k + 1) if j != i)
def _is_swing_high(bars: Sequence[Bar], i: int, k: int) -> bool:
    if i - k < 0 or i + k >= len(bars):
        return False
    return all(bars[i].h >= bars[j].h for j in range(i - k, i + k + 1) if j != i)
def _swing_lows(bars: Sequence[Bar], cfg: DetectorConfig) -> List[int]:
    k = cfg.pivot_lookback
    return [i for i in range(len(bars)) if _is_swing_low(bars, i, k)]
def _swing_highs(bars: Sequence[Bar], cfg: DetectorConfig) -> List[int]:
    k = cfg.pivot_lookback
    return [i for i in range(len(bars)) if _is_swing_high(bars, i, k)]
def _recent_cvd_range(bars: Sequence[Bar], n: int) -> float:
    w = bars[-n:] if len(bars) >= n else bars
    cs = [b.cvd for b in w]
    return max(max(cs) - min(cs), 1e-9)
def _support_levels(levels: Levels) -> List[float]:
    base = [levels.dval, levels.pval, levels.ib_low, levels.ppoc, levels.dpoc, levels.vwap]
    base += list(levels.naked_pocs)
    return [x for x in base if x and x > 0]
def _near_support(price: float, levels: Levels, ctx: Context, cfg: DetectorConfig) -> Optional[float]:
    tol = cfg.vp_level_max_ticks * ctx.tick
    cands = [L for L in _support_levels(levels) if abs(price - L) <= tol]
    return min(cands, key=lambda L: abs(price - L)) if cands else None
def _delta_flip_ok(reclaim: Bar, adverse_delta: float, cfg: DetectorConfig) -> bool:
    # reclaim must be net-buying and recover >= flip_ratio of the adverse (sell) delta
    if reclaim.delta <= 0:
        return False
    return reclaim.delta >= cfg.flip_ratio * abs(adverse_delta)
# --------------------------------------------------------------------------- #
# Shared entry gate + stop/target builder
# --------------------------------------------------------------------------- #
def passes_entry_gate(reclaim: Bar, level: float, levels: Levels,
                      ctx: Context, cfg: DetectorConfig) -> bool:
    if ctx.news_blackout:
        return False
    # entry should not be miles from the qualifying level
    if abs(reclaim.c - level) > (cfg.vp_level_max_ticks * 2) * ctx.tick:
        return False
    if cfg.require_lsma_reclaim:
        if not (reclaim.c > levels.lsma and levels.lsma_slope >= 0):
            return False
    return True
def _targets_above(entry: float, levels: Levels, mode: str) -> List[float]:
    if mode == "continuation":
        ext = max(levels.ib_high - levels.ib_low, 0.0)
        cands = [levels.dvah, levels.ib_high, levels.ib_high + ext,
                 levels.ib_high + 2 * ext, levels.pday_high]
    else:  # reversal
        cands = [levels.dpoc, levels.vwap, levels.dvah, levels.ib_high,
                 levels.pvah, levels.pday_high]
    cands += list(levels.naked_pocs)
    return sorted({round(c, 2) for c in cands if c and c > entry})
def _build_long(entry: float, struct_low: float, levels: Levels,
                ctx: Context, cfg: DetectorConfig, mode: str
                ) -> Optional[Tuple[float, float, float, float]]:
    raw_stop = struct_low - cfg.stop_buffer_ticks * ctx.tick
    stop_pts = max(cfg.stop_min_pts, min(cfg.stop_max_pts, entry - raw_stop))
    stop = entry - stop_pts
    tg = _targets_above(entry, levels, mode)
    if not tg:
        return None
    t1 = tg[0]
    t2 = tg[1] if len(tg) > 1 else t1 + stop_pts
    t3 = tg[2] if len(tg) > 2 else t2 + stop_pts
    if (t3 - entry) < cfg.min_rr_overall * stop_pts:
        return None  # whole trade does not clear minimum R:R
    return stop, t1, t2, t3
def _finish(name: str, tier: str, family: str, reclaim: Bar, entry: float,
            stop_ref: float, levels: Levels, ctx: Context, cfg: DetectorConfig,
            mode: str, note: str = "", level_ref: Optional[float] = None) -> Optional[Setup]:
    lr = stop_ref if level_ref is None else level_ref
    level = _near_support(lr, levels, ctx, cfg)
    if level is None:
        return None
    if not passes_entry_gate(reclaim, level, levels, ctx, cfg):
        return None
    built = _build_long(entry, stop_ref, levels, ctx, cfg, mode)
    if built is None:
        return None
    stop, t1, t2, t3 = built
    return Setup(name, tier, family, "long", entry, stop, t1, t2, t3, note)
# --------------------------------------------------------------------------- #
# Reversal family (BALANCE regime)
# --------------------------------------------------------------------------- #
def detect_double_bottom_div(bars: Sequence[Bar], levels: Levels,
                             ctx: Context, cfg: DetectorConfig) -> Optional[Setup]:
    if len(bars) < cfg.pivot_lookback * 2 + 3:
        return None
    sl = _swing_lows(bars, cfg)
    if len(sl) < 2:
        return None
    i1, i2 = sl[-2], sl[-1]
    b1, b2 = bars[i1], bars[i2]
    if not (b2.l <= b1.l + cfg.equal_low_ticks * ctx.tick):       # equal/lower price low
        return None
    rng = _recent_cvd_range(bars, cfg.cvd_range_lookback)
    if not (b2.cvd - b1.cvd >= cfg.div_min_frac * rng):           # higher CVD low (magnitude)
        return None
    reclaim = bars[-1]
    neck = max(b.h for b in bars[i1:i2 + 1])
    if not (_bull(reclaim) and reclaim.c > neck and reclaim.delta > 0):
        return None
    return _finish("double_bottom_div", "A", "reversal", reclaim, reclaim.c,
                   min(b1.l, b2.l), levels, ctx, cfg, "reversal",
                   "price equal/lower low, CVD higher low")
def detect_one_two_three_low(bars: Sequence[Bar], levels: Levels,
                             ctx: Context, cfg: DetectorConfig) -> Optional[Setup]:
    if len(bars) < cfg.pivot_lookback * 2 + 4:
        return None
    lows, highs = _swing_lows(bars, cfg), _swing_highs(bars, cfg)
    if len(lows) < 2 or not highs:
        return None
    p1, p3 = lows[-2], lows[-1]
    mids = [h for h in highs if p1 < h < p3]
    if not mids or not (bars[p3].l > bars[p1].l):                 # need a higher low
        return None
    p2 = max(mids, key=lambda h: bars[h].h)
    reclaim = bars[-1]
    if not (_bull(reclaim) and reclaim.c > bars[p2].h and reclaim.delta > 0):
        return None
    return _finish("one_two_three_low", "A", "reversal", reclaim, reclaim.c,
                   bars[p3].l, levels, ctx, cfg, "reversal",
                   "LL -> HL -> break of swing high",
                   level_ref=min(bars[p1].l, bars[p3].l))
def detect_spring(bars: Sequence[Bar], levels: Levels,
                  ctx: Context, cfg: DetectorConfig) -> Optional[Setup]:
    if len(bars) < 3:
        return None
    reclaim = bars[-1]
    for L in _support_levels(levels):
        for j in (-2, -3):
            if len(bars) < -j:
                continue
            sweep = bars[j]
            pierced = sweep.l < L - ctx.tick and (
                sweep.c <= L or _lower_wick(sweep) >= cfg.long_wick_frac * _rng(sweep))
            if not pierced:
                continue
            if not (_bull(reclaim) and reclaim.c > L and reclaim.delta > 0):
                continue
            if not _delta_flip_ok(reclaim, sweep.delta, cfg):
                continue
            s = _finish("spring", "B", "reversal", reclaim, reclaim.c, sweep.l,
                        levels, ctx, cfg, "reversal",
                        "sweep below level then reclaim, delta flip")
            if s:
                return s
    return None
def detect_absorption(bars: Sequence[Bar], levels: Levels,
                      ctx: Context, cfg: DetectorConfig) -> Optional[Setup]:
    if len(bars) < 3:
        return None
    reclaim = bars[-1]
    for n in (1, 2, 3):
        if len(bars) < n + 1:
            break
        cluster = bars[-(n + 1):-1]
        if not cluster:
            continue
        L = _near_support(min(b.l for b in cluster), levels, ctx, cfg)
        if L is None:
            continue
        absorbed = all(
            b.volume >= cfg.vol_spike_mult * ctx.median_vol20
            and _rng(b) <= cfg.absorption_range_atr * ctx.atr5
            and b.delta < 0
            and _upper_half_close(b)
            and b.c >= L - ctx.tick                 # held the level (no acceptance below)
            for b in cluster)
        if not absorbed:
            continue
        if not (_bull(reclaim) and reclaim.delta > 0 and reclaim.c > cluster[-1].h):
            continue
        s = _finish("absorption", "B", "reversal", reclaim, reclaim.c,
                    min(b.l for b in cluster), levels, ctx, cfg, "reversal",
                    "high-vol small-range sell bars held, then delta flip")
        if s:
            return s
    return None
def detect_climax(bars: Sequence[Bar], levels: Levels,
                  ctx: Context, cfg: DetectorConfig) -> Optional[Setup]:
    if len(bars) < 2:
        return None
    cl = bars[-1]
    if not (cl.volume >= cfg.climax_vol_mult * ctx.median_vol20
            and _lower_wick(cl) >= cfg.long_wick_frac * _rng(cl)
            and cl.delta < 0
            and _upper_half_close(cl)):
        return None
    if _near_support(cl.l, levels, ctx, cfg) is None or ctx.news_blackout:
        return None
    if cfg.require_lsma_reclaim and not (cl.c > levels.lsma and levels.lsma_slope >= 0):
        return None
    entry = cl.h + ctx.tick                          # confirmed: break of climax-bar high
    built = _build_long(entry, cl.l, levels, ctx, cfg, "reversal")
    if built is None:
        return None
    stop, t1, t2, t3 = built
    return Setup("climax", "C", "reversal", "long", entry, stop, t1, t2, t3,
                 "single capitulation bar: huge vol, long lower wick, sell delta")
def detect_bullish_engulfing(bars: Sequence[Bar], levels: Levels,
                             ctx: Context, cfg: DetectorConfig) -> Optional[Setup]:
    if len(bars) < 2:
        return None
    prev, reclaim = bars[-2], bars[-1]
    if not (_bear(prev) and _bull(reclaim)
            and reclaim.o <= prev.c and reclaim.c >= prev.o):
        return None
    if not _delta_flip_ok(reclaim, prev.delta, cfg):
        return None
    return _finish("bullish_engulfing", "C", "reversal", reclaim, reclaim.c,
                   min(prev.l, reclaim.l), levels, ctx, cfg, "reversal",
                   "down bar engulfed by up bar at level, delta flip")
def detect_b_shape_flush(bars: Sequence[Bar], levels: Levels,
                         ctx: Context, cfg: DetectorConfig) -> Optional[Setup]:
    if len(bars) < 4:
        return None
    reclaim = bars[-1]
    flush = bars[-4:-1]
    if not (sum(1 for b in flush if _bear(b)) >= 2 and sum(b.delta for b in flush) < 0):
        return None
    flush_low = min(b.l for b in flush)
    if not (_bull(reclaim) and reclaim.l > flush_low and reclaim.delta > 0):
        return None
    return _finish("b_shape_flush", "C", "reversal", reclaim, reclaim.c, flush_low,
                   levels, ctx, cfg, "reversal",
                   "long-liquidation flush exhausts, base + reclaim")
def detect_poor_low_retest(bars: Sequence[Bar], levels: Levels,
                           ctx: Context, cfg: DetectorConfig) -> Optional[Setup]:
    if len(bars) < cfg.pivot_lookback * 2 + 3:
        return None
    lows = _swing_lows(bars, cfg)
    if len(lows) < 2:
        return None
    poor = bars[lows[-2]]
    if _lower_wick(poor) > cfg.poor_low_wick_frac * _rng(poor):    # poor = no excess tail
        return None
    reclaim = bars[-1]
    if not (abs(reclaim.l - poor.l) <= cfg.equal_low_ticks * ctx.tick
            and _bull(reclaim) and reclaim.delta > 0):
        return None
    return _finish("poor_low_retest", "D", "reversal", reclaim, reclaim.c,
                   min(reclaim.l, poor.l), levels, ctx, cfg, "reversal",
                   "poor low (no excess) revisited and held")
# --------------------------------------------------------------------------- #
# Continuation family (TREND_UP regime) - the inverted reactive long
# --------------------------------------------------------------------------- #
def detect_hidden_div(bars: Sequence[Bar], levels: Levels,
                      ctx: Context, cfg: DetectorConfig) -> Optional[Setup]:
    if ctx.regime != Regime.TREND_UP:
        return None
    if len(bars) < cfg.pivot_lookback * 2 + 3:
        return None
    lows = _swing_lows(bars, cfg)
    if len(lows) < 2:
        return None
    i1, i2 = lows[-2], lows[-1]
    b1, b2 = bars[i1], bars[i2]
    if not (b2.l > b1.l):                                          # higher price low
        return None
    rng = _recent_cvd_range(bars, cfg.cvd_range_lookback)
    if not (b1.cvd - b2.cvd >= cfg.div_min_frac * rng):           # lower CVD low
        return None
    reclaim = bars[-1]
    if not (_bull(reclaim) and reclaim.delta > 0 and reclaim.c > bars[i2].h):
        return None
    if not (reclaim.c > levels.vwap or reclaim.c > levels.lsma):  # above rising value
        return None
    return _finish("hidden_div", "A", "continuation", reclaim, reclaim.c, b2.l,
                   levels, ctx, cfg, "continuation",
                   "price higher low, CVD lower low -> trend resumes")
def detect_pullback_flag(bars: Sequence[Bar], levels: Levels,
                         ctx: Context, cfg: DetectorConfig) -> Optional[Setup]:
    if ctx.regime != Regime.TREND_UP:
        return None
    if len(bars) < 4:
        return None
    reclaim = bars[-1]
    pull = bars[-4:-1]
    pull_low = min(b.l for b in pull)
    tol = cfg.vp_level_max_ticks * ctx.tick
    near_value = any(abs(pull_low - v) <= tol for v in (levels.vwap, levels.dpoc, levels.lsma))
    cvd_supportive = reclaim.cvd >= min(b.cvd for b in pull)
    if not (near_value and cvd_supportive):
        return None
    if not (_bull(reclaim) and reclaim.delta > 0 and reclaim.c > pull[-1].h):
        return None
    return _finish("pullback_flag", "B", "continuation", reclaim, reclaim.c, pull_low,
                   levels, ctx, cfg, "continuation",
                   "shallow pullback to rising value, reclaim")
# --------------------------------------------------------------------------- #
# Opening family (Dalton opening types) - discretionary
# --------------------------------------------------------------------------- #
def detect_open_test_drive(bars: Sequence[Bar], levels: Levels,
                           ctx: Context, cfg: DetectorConfig) -> Optional[Setup]:
    if not ctx.opening_window or len(bars) < 2:
        return None
    ref = None
    for L in (levels.pval, levels.ib_low):
        if L and L > 0:
            ref = L if ref is None else min(ref, L)
    if ref is None:
        return None
    reclaim = bars[-1]
    sess_low = min(b.l for b in bars)
    tested = ref - cfg.vp_level_max_ticks * ctx.tick <= sess_low <= ref + cfg.equal_low_ticks * ctx.tick
    if not (tested and _bull(reclaim) and reclaim.delta > 0 and reclaim.c > ref):
        return None
    return _finish("open_test_drive", "D", "opening", reclaim, reclaim.c, sess_low,
                   levels, ctx, cfg, "reversal",
                   "open, test level below, hold, drive up", level_ref=ref)
def detect_open_rejection_reverse(bars: Sequence[Bar], levels: Levels,
                                  ctx: Context, cfg: DetectorConfig) -> Optional[Setup]:
    if not ctx.opening_window or ctx.session_open <= 0 or len(bars) < 2:
        return None
    reclaim = bars[-1]
    sess_low = min(b.l for b in bars)
    drove_below = sess_low < ctx.session_open - ctx.tick
    reversed_up = reclaim.c > ctx.session_open and _bull(reclaim) and reclaim.delta > 0
    if not (drove_below and reversed_up):
        return None
    return _finish("open_rejection_reverse", "D", "opening", reclaim, reclaim.c, sess_low,
                   levels, ctx, cfg, "reversal",
                   "open, drive down, reject, reverse back through open",
                   level_ref=ctx.session_open)
# --------------------------------------------------------------------------- #
# Dispatcher
# --------------------------------------------------------------------------- #
REVERSAL_DETECTORS = [detect_double_bottom_div, detect_one_two_three_low,
                      detect_spring, detect_absorption, detect_climax,
                      detect_bullish_engulfing, detect_b_shape_flush,
                      detect_poor_low_retest]
CONTINUATION_DETECTORS = [detect_hidden_div, detect_pullback_flag]
OPENING_DETECTORS = [detect_open_test_drive, detect_open_rejection_reverse]
_TIER_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3}
def scan(bars: Sequence[Bar], levels: Levels, ctx: Context,
         cfg: Optional[DetectorConfig] = None) -> List[Setup]:
    """Route by regime and return triggered Setups, best-tier first.
    Call once per closed 5-min bar. `bars` ascending, bars[-1] = last closed bar.
    """
    cfg = cfg or DetectorConfig()
    if len(bars) < 3:
        return []
    w = bars[-cfg.buffer_bars * 3:] if len(bars) > cfg.buffer_bars * 3 else bars
    found: List[Setup] = []
    if ctx.opening_window:
        found += [s for d in OPENING_DETECTORS if (s := d(w, levels, ctx, cfg))]
    if ctx.regime == Regime.BALANCE:
        found += [s for d in REVERSAL_DETECTORS if (s := d(w, levels, ctx, cfg))]
    elif ctx.regime == Regime.TREND_UP:
        found += [s for d in CONTINUATION_DETECTORS if (s := d(w, levels, ctx, cfg))]
    best = {}
    for s in found:
        if s.name not in best or _TIER_ORDER[s.tier] < _TIER_ORDER[best[s.name].tier]:
            best[s.name] = s
    return sorted(best.values(), key=lambda s: _TIER_ORDER[s.tier])
# --------------------------------------------------------------------------- #
# Smoke test (illustrative synthetic data; relaxed cfg for a toy example)
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    def mk(t, o, h, l, c, v, d, cvd):
        return Bar(t, o, h, l, c, v, d, cvd)
    # ES-scaled double-bottom + bullish CVD divergence on a balance day
    seq = [
        mk(0, 5000.0, 5001.0, 4994.0, 4994.5, 800, -300, -300),
        mk(1, 4994.5, 4995.0, 4988.0, 4988.5, 1200, -500, -800),   # low-1 (CVD -800)
        mk(2, 4988.5, 4994.0, 4988.2, 4993.5, 900, 300, -500),
        mk(3, 4993.5, 4994.5, 4993.0, 4994.0, 700, 50, -450),       # neckline ~4994.5
        mk(4, 4994.0, 4994.2, 4988.2, 4989.0, 1100, -200, -650),    # low-2 equal, CVD -650 (higher)
        mk(5, 4989.0, 4997.0, 4988.5, 4996.5, 1500, 600, -50),      # reclaim breaks neckline, +600
    ]
    levels = Levels(dpoc=5000.0, dvah=5006.0, dval=4990.0, ppoc=5002.0, pvah=5008.0,
                    pval=4990.0, ib_high=5006.0, ib_low=4990.0, vwap=4996.5,
                    lsma=4994.0, lsma_slope=0.2, pday_high=5012.0)
    ctx = Context(regime=Regime.BALANCE, atr5=8.0, median_vol20=900.0)
    cfg = DetectorConfig(pivot_lookback=1, min_rr_overall=1.2)  # relaxed for the toy
    print("scan() ->")
    for s in scan(seq, levels, ctx, cfg):
        print(f"  [{s.tier}] {s.name:<20} entry={s.entry}  stop={s.stop}  "
              f"T1={s.t1} T2={s.t2} T3={s.t3}  ({s.note})")
