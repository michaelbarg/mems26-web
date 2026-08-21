"""S6 MAE Scratch — adverse-excursion-based early exit (DEV_PLAN 02.08 §P3.1).

Sweeney (1996): the winning trades move favorably quickly; the losers dwell
deep in red. Our data (112 trades): winners median MAE 3.2pt, losers 11.2pt.
When a trade hits the per-pattern MAE threshold before T1, scratch it (FLATTEN).
After T1 → BE already protects; this only fires pre-T1.

Flag: S6_MAE_SCRATCH_V1 (default OFF). When OFF, should_scratch() returns
(False, "") and zero behavior changes. When ON, the bar_level_detector calls
it each bar on open demo/live trades and issues FLATTEN on True.

The thresholds come from config/mae_scratch.yaml (calibrated from actual trades).
Responsive patterns get threshold × 1.5 per Kaminski&Lo (early exit hurts
mean-reversion).

NEVER calls op=EXIT (forbidden). Uses FLATTEN only (the allowed mechanism).

Flag 2: S6_MAE_SCRATCH_ATR_V1 (default OFF, Michael 2026-08-21) — makes the
threshold ATR-relative: max(k x ATR14, floor), k per-pattern in the same yaml,
normalised on the live-era median ATR14 (6.0pt) so a median-ATR day reproduces
the fixed points exactly. It also turns the P2-9 scratch<->stop clamp into a
skip. Evidence: #756 (20.08) scratched at 1.8pt MAE on an 8.07pt-ATR bar and
then ran 27.5pt our way. When this flag is OFF, nothing here changes.
"""
from __future__ import annotations

import logging
import os
from typing import Optional, Tuple

from backend.v9.config_loader import _load_yaml

logger = logging.getLogger(__name__)

_cache = None
_loaded = False


def _flag_on() -> bool:
    return os.getenv("S6_MAE_SCRATCH_V1", "0").lower() in ("1", "true", "yes")


def _atr_flag_on() -> bool:
    """S6_MAE_SCRATCH_ATR_V1 — ATR-relative thresholds (Michael 2026-08-21).

    Default OFF in code. When OFF every code path below is bypassed and
    should_scratch() behaves byte-identically to the pre-2026-08-21 version.
    """
    return os.getenv("S6_MAE_SCRATCH_ATR_V1", "0").lower() in ("1", "true", "yes")


def _cfg():
    global _cache, _loaded
    if not _loaded:
        _loaded = True
        _cache = _load_yaml("mae_scratch.yaml")
    return _cache or {}


def reset_cache():
    global _cache, _loaded
    _cache = None
    _loaded = False


def _normalize_pattern(pattern_name: str) -> str:
    """Normalize pattern name for lookup (strip _LONG/_SHORT suffix)."""
    p = (pattern_name or "").upper().strip()
    for suf in ("_LONG", "_SHORT"):
        if p.endswith(suf):
            p = p[:-len(suf)]
    return p


def get_threshold(pattern_name: str) -> float:
    """Get the MAE scratch threshold for a pattern.

    Uses per-pattern override from config if available, else default.
    Responsive patterns get threshold × multiplier.
    """
    cfg = _cfg()
    default = float(cfg.get("default_threshold_pts", 8.0))
    multiplier = float(cfg.get("responsive_multiplier", 1.5))
    responsive = set(cfg.get("responsive_patterns", []))
    overrides = cfg.get("pattern_thresholds", {})

    norm = _normalize_pattern(pattern_name)

    # Check per-pattern override first
    threshold = overrides.get(norm) or overrides.get(pattern_name)
    if threshold is not None:
        return float(threshold)

    # Check if responsive → apply multiplier
    if norm in responsive or pattern_name in responsive:
        return default * multiplier

    return default


def get_threshold_atr(pattern_name: str, atr: float) -> float:
    """ATR-relative MAE threshold: max(k x ATR14, floor).

    k is per-pattern in the SAME yaml (`atr_relative.pattern_k`), normalised on
    the live-era median ATR14 of 6.0pt so that on a median-ATR day this returns
    the historic fixed points (ZLR 6 / GB100 10 / default 8 ...) to <0.01pt.
    Responsive patterns get the same x1.5 they get on the fixed path.

    `floor` (4.0pt = 1.25 x the winners' median MAE of 3.2pt) is what stops a
    dead-ATR day from producing an absurdly tight threshold.
    """
    cfg = _cfg()
    rel = cfg.get("atr_relative", {}) or {}
    floor = float(rel.get("floor_pts", 4.0))
    default_k = float(rel.get("default_k", 1.3333))
    multiplier = float(cfg.get("responsive_multiplier", 1.5))
    responsive = set(cfg.get("responsive_patterns", []))
    ks = rel.get("pattern_k", {}) or {}

    norm = _normalize_pattern(pattern_name)

    k = ks.get(norm)
    if k is None:
        k = ks.get(pattern_name)
    if k is None:
        k = default_k
        if norm in responsive or pattern_name in responsive:
            k = default_k * multiplier

    return max(float(k) * float(atr), floor)


_ATR_TTL_SEC = 30.0
_atr_cache: Tuple[float, float] = (0.0, 0.0)   # (value, monotonic_ts)


def current_atr14() -> float:
    """14-bar TR average from the canonical bar table — the SAME computation
    bar_level_detector already runs for System 6 (`v9_bars_5min_woodies`).

    Returns 0.0 (the documented honest-zero fallback, Rule 1) when the table is
    unreachable or short; callers treat 0.0 as "no ATR" and fall back to the
    fixed thresholds. Short TTL cache so the per-bar x per-trade loop does not
    hammer the DB. Returns 0.0 immediately when the ATR flag is OFF (no DB read
    at all on the OFF path).
    """
    if not _atr_flag_on():
        return 0.0
    global _atr_cache
    import time as _time
    now = _time.monotonic()
    val, ts = _atr_cache
    if ts and (now - ts) < _ATR_TTL_SEC:
        return val
    atr = 0.0
    try:
        from backend.v9.db.read import read_all as _read
        n = int((_cfg().get("atr_relative", {}) or {}).get("atr_bars", 14))
        rows = _read(
            "SELECT high, low, close FROM v9_bars_5min_woodies "
            f"WHERE symbol='MES' ORDER BY ts DESC LIMIT {n}", {}) or []
        rows = list(reversed(rows))
        trs, prev = [], None
        for b in rows:
            h, l, c = float(b["high"]), float(b["low"]), float(b["close"])
            trs.append(h - l if prev is None
                       else max(h - l, abs(h - prev), abs(l - prev)))
            prev = c
        atr = (sum(trs) / len(trs)) if trs else 0.0
    except Exception as err:      # honest zero, never break trade management
        logger.debug("[MAE_SCRATCH] ATR read failed (fixed-threshold fallback): %s", err)
        atr = 0.0
    _atr_cache = (atr, now)
    return atr


def reset_atr_cache():
    global _atr_cache
    _atr_cache = (0.0, 0.0)


def compute_mae(
    entry_price: float,
    direction: str,
    bar_low: float,
    bar_high: float,
) -> float:
    """Compute the Maximum Adverse Excursion from a single bar's extremes.

    MAE = how far price went AGAINST the trade on this bar.
    LONG: MAE = entry - bar_low (positive when price dipped below entry)
    SHORT: MAE = bar_high - entry (positive when price spiked above entry)
    """
    d = direction.upper()
    if d == "LONG":
        return max(0.0, entry_price - bar_low)
    elif d == "SHORT":
        return max(0.0, bar_high - entry_price)
    return 0.0


SCRATCH_STOP_GAP_PTS = float(os.environ.get("S6_SCRATCH_STOP_GAP_PTS", "2.0") or 2.0)


def should_scratch(
    *,
    pattern_name: str,
    entry_price: float,
    direction: str,
    bar_low: float,
    bar_high: float,
    t1_hit: bool = False,
    stop_price: Optional[float] = None,
    atr: Optional[float] = None,
) -> Tuple[bool, str]:
    """Determine if a trade should be scratched based on MAE.

    Returns (True, reason) if MAE >= threshold and pre-T1.
    Returns (False, "") otherwise or when flag is OFF.

    NEVER returns True after T1 (BE already covers post-T1).

    P2-9 (08-07): scratch↔stop gap enforcement. The scratch threshold
    must be at least SCRATCH_STOP_GAP_PTS (default 2pt) BELOW the stop.
    Without this, scratch=8pt + stop=8.5pt → 0.5pt window → no time to
    react. The gap ensures the scratch fires early enough for FLATTEN to
    execute before the stop is hit.
    """
    if not _flag_on():
        return (False, "")

    if t1_hit:
        return (False, "")  # post-T1 → BE handles it

    mae = compute_mae(entry_price, direction, bar_low, bar_high)

    # ── S6_MAE_SCRATCH_ATR_V1 (Michael 2026-08-21) — ATR-relative yardstick ──
    # Live evidence #756 (20.08): a 1.8pt adverse excursion scratched a
    # TREND_STEP that then ran 27.5pt our way, on a bar whose ATR14 was 8.07pt.
    # The 1.5pt threshold came from the P2-9 clamp (stop 3.5 - gap 2.0), not
    # from the YAML — so under this flag the clamp becomes a SKIP: when the
    # structural threshold cannot fit under the stop with the required gap, the
    # stop is already the protection and we do not scratch.
    # Flag OFF (default) → not one line below runs; behaviour is byte-identical.
    atr_path = False
    if _atr_flag_on():
        _atr = atr if atr is not None else current_atr14()
        try:
            _atr = float(_atr)
        except (TypeError, ValueError):
            _atr = 0.0
        if _atr > 0:
            atr_path = True
            threshold = get_threshold_atr(pattern_name, _atr)
            if stop_price is not None:
                stop_distance = abs(entry_price - stop_price)
                room = stop_distance - SCRATCH_STOP_GAP_PTS
                mode = str(((_cfg().get("atr_relative", {}) or {})
                            .get("stop_gap_mode", "skip"))).lower()
                if threshold > room:
                    if mode == "skip":
                        logger.debug(
                            "[MAE_SCRATCH] no scratch for %s — ATR threshold %.2f "
                            "does not fit under a %.2fpt stop (gap %.1f); the stop "
                            "is the protection", pattern_name, threshold,
                            stop_distance, SCRATCH_STOP_GAP_PTS)
                        return (False, "")
                    if room > 0:
                        threshold = room
        else:
            # honest zero (Rule 1): no ATR → fall back to the fixed thresholds
            logger.debug("[MAE_SCRATCH] ATR unavailable — fixed-threshold fallback")

    if not atr_path:
        threshold = get_threshold(pattern_name)

        # P2-9: enforce minimum gap between scratch and stop
        if stop_price is not None:
            stop_distance = abs(entry_price - stop_price)
            max_scratch = stop_distance - SCRATCH_STOP_GAP_PTS
            if max_scratch > 0 and threshold > max_scratch:
                threshold = max_scratch
                logger.debug("[MAE_SCRATCH] gap-enforced threshold: %.1f (stop=%.1f, gap=%.1f)",
                             threshold, stop_distance, SCRATCH_STOP_GAP_PTS)

    if mae >= threshold:
        reason = (f"MAE scratch: {mae:.1f}pt >= {threshold:.1f}pt threshold "
                  f"for {pattern_name} (pre-T1)")
        if atr_path:
            reason += f" [ATR-relative, ATR14={_atr:.2f}]"
        return (True, reason)

    return (False, "")
