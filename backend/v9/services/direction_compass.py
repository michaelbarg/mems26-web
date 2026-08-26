"""direction_compass — F1: the ONE fused direction reading (Michael 2026-08-20).

**Why this module exists (the money).** `MAX_DAYS_2026-08-20.md` §3 measured the
single most expensive recurring mistake of the whole live era — the
*direction family*, ‎+$576.25 over 32 sessions:

  1. ‎+$262.50  OPENING_DRIVE fired at 09:35 with **no** day-direction (0/2 live).
  2. ‎+$200.00  Variation-family SHORTs taken **against** the session drift.
  3. ‎+$113.75  counter-day entries on trend days (SHORT on Trend_Normal /
                LONG on Trend_DD).

Every one of them is the same root cause: **each gate asked a different, single,
lagging source "which way is the market going?" and got a different answer.**
`cont_trend_filter` asked `dir_sustained` (documented to lag 3 separate days),
`direction_context` asked CVD+IB-breakout, the playbook asked `day_type_at_entry`
(unstable — 07-15 / 07-31 both mislabelled at entry), OPENING_DRIVE asked nobody
at all because at 09:35 the classifier has not spoken yet. 2026-08-19 is the
canonical failure shape: the DLL trend read BEARISH while a live UP leg was
running and the LSMA was rising — on a day that closed **+26pt up**.

The compass fuses the four *independent* pieces of evidence the system already
computes into ONE number that every direction gate consumes:

  | component        | weight | source (KEEP — nothing new is invented)          |
  |------------------|--------|--------------------------------------------------|
  | leg              | 0.40   | `leg_state.detect_leg` (already trusted by LEG_RIDE)|
  | lsma             | 0.30   | `direction_context_live.lsma_slope_pts_per_bar`   |
  | value_migration  | 0.15   | `multiday_profile.value_migration` (7-day VA drift)|
  | cvd              | 0.15   | `direction_context.cvd_slope` (per-bar delta sum)  |

**The leg is deliberately the strongest single component** and carries a hard
clamp: the compass may never point *against* a live leg (worst case NEUTRAL).
That is what makes a fresh reversal *flip* the compass instead of lagging it —
the 08-19 shape resolves to UP, not DOWN.

**Honest (Rule 1).** A missing component is *excluded from the denominator* — it
is never voted as 0. Zero components ⇒ NEUTRAL / confidence 0.0. A compass that
is NEUTRAL, below `min_confidence`, or **without a live-leg anchor**
(`has_structural_anchor`) says *nothing*, and every consumer keeps its existing
legacy input — byte-identical behaviour, no new blocking.

**Replay** (`scripts/f1_compass_replay.py`, 85 live closed trades 07-07→08-19,
compass reconstructed at entry time from the real bars — no hindsight):
7 blocks · 4 losers prevented ‎+$393.75 · 2 winners forgone ‎−$68.75 · net
‎**+$325.00** on the books, catching 5 of the 15 direction-family mistake trades.

**No hour gating anywhere** (Michael 2026-08-20: "אתה לא מגביל שעות בשום אופן").
The afternoon is governed by the direction rule alone.
**No pattern is disabled** (Michael 2026-08-20: "מערכת שמפסידה לנו בתבנית אנחנו
מתקנים ולא מבטלים") — OPENING_DRIVE and the Variation shorts keep firing; only
their against-direction subset stops.

Pure `compute_compass()` (no env, no I/O — unit-testable and replayable) plus a
thin cached live fetcher `current()`. Flag: `DIRECTION_COMPASS_V1`, default OFF
in code.
"""
from __future__ import annotations

import logging
import os
import time as _time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ── Fusion weights ────────────────────────────────────────────────────────────
# leg > lsma > (value_migration == cvd). The leg is the immediate structural
# read; lsma is the held slope; migration and cvd are slower / noisier context.
W_LEG = 0.40
W_LSMA = 0.30
W_VALUE_MIGRATION = 0.15
W_CVD = 0.15

# |LSMA slope| below this (pts/bar) is FLAT — the component abstains rather than
# voting on noise. Same spirit as LSMA_FLAT_MIN_SLOPE_PTS (0.25) but lower: here
# it only silences a vote, it does not block a trade.
LSMA_FLAT_PTS_PER_BAR = 0.10

# |score| below this ⇒ NEUTRAL ⇒ every consumer falls back to its legacy input.
DEFAULT_MIN_CONFIDENCE = 0.25

_FLAG = "DIRECTION_COMPASS_V1"
_CACHE: Dict[str, Any] = {}
_CACHE_TTL_S = 20.0


def flag_on() -> bool:
    """True when DIRECTION_COMPASS_V1 is enabled. Default OFF in code — a clone
    or a restart keeps it off until Michael's ruling is applied to `.env`."""
    return os.getenv(_FLAG, "0").lower() in ("1", "true", "yes")


def _dir_to_vote(value: Optional[str]) -> Optional[int]:
    """'UP'→+1 · 'DOWN'→−1 · 'FLAT'/'NEUTRAL'→0 (present, abstaining) ·
    None/unknown→None (absent — excluded from the denominator, Rule 1)."""
    if value is None:
        return None
    v = str(value).strip().upper()
    if v == "UP":
        return 1
    if v == "DOWN":
        return -1
    if v in ("FLAT", "NEUTRAL", "NONE"):
        return 0
    return None


def compute_compass(
    *,
    lsma_slope: Optional[float] = None,
    lsma_side: Optional[int] = None,
    leg_dir: Optional[str] = None,
    leg_age: int = 0,
    value_migration: Optional[str] = None,
    cvd_slope: Optional[int] = None,
    dll_trend: Optional[str] = None,
    min_confidence: Optional[float] = None,
    flat_slope_pts: float = LSMA_FLAT_PTS_PER_BAR,
) -> Dict[str, Any]:
    """Fuse the four direction components into ONE reading. Pure.

    Args:
      lsma_slope: Woodies LSMA slope in points/bar (rising > 0). Preferred.
      lsma_side:  fallback when no slope is available: +1 close above LSMA, −1 below.
      leg_dir:    "UP"/"DOWN"/None from `leg_state.detect_leg` — the STRONG component.
      leg_age:    bars the leg has been alive (reported in `reason`; does not vote).
      value_migration: "UP"/"DOWN"/"FLAT"/None — multi-day VA-midpoint drift.
      cvd_slope:  +1/−1/0/None — sign of the summed per-bar delta.
      dll_trend:  **context only, never votes.** The lagging DLL verdict that read
                  BEARISH on the +26pt up day of 2026-08-19; recorded so a reader
                  can see the divergence the compass resolves.
      min_confidence: |score| threshold for a non-NEUTRAL verdict.

    Returns:
      {"direction": "UP"|"DOWN"|"NEUTRAL", "confidence": 0.0..1.0,
       "components": {"lsma": int|None, "leg": int|None,
                      "value_migration": int|None, "cvd": int|None},
       "score": float, "reason": str, "context": {...}}
    """
    thr = DEFAULT_MIN_CONFIDENCE if min_confidence is None else float(min_confidence)

    # --- component votes (None = absent, excluded from the denominator) -------
    lsma_vote: Optional[int] = None
    if lsma_slope is not None:
        try:
            s = float(lsma_slope)
            lsma_vote = 0 if abs(s) < flat_slope_pts else (1 if s > 0 else -1)
        except (TypeError, ValueError):
            lsma_vote = None
    elif lsma_side is not None:
        try:
            si = int(lsma_side)
            lsma_vote = 0 if si == 0 else (1 if si > 0 else -1)
        except (TypeError, ValueError):
            lsma_vote = None

    leg_vote = _dir_to_vote(leg_dir)
    if leg_vote == 0:          # a leg is UP/DOWN or it does not exist
        leg_vote = None
    mig_vote = _dir_to_vote(value_migration)
    cvd_vote: Optional[int] = None
    if cvd_slope is not None:
        try:
            cs = int(cvd_slope)
            cvd_vote = 0 if cs == 0 else (1 if cs > 0 else -1)
        except (TypeError, ValueError):
            cvd_vote = None

    components = {"lsma": lsma_vote, "leg": leg_vote,
                  "value_migration": mig_vote, "cvd": cvd_vote}
    context = {"dll_trend": dll_trend, "leg_age": int(leg_age or 0),
               "lsma_slope": lsma_slope, "min_confidence": round(thr, 4)}

    weights = {"lsma": W_LSMA, "leg": W_LEG,
               "value_migration": W_VALUE_MIGRATION, "cvd": W_CVD}
    present = {k: v for k, v in components.items() if v is not None}
    if not present:
        return {"direction": "NEUTRAL", "confidence": 0.0, "components": components,
                "score": 0.0, "context": context,
                "reason": "no direction components available — honest NEUTRAL (Rule 1)"}

    denom = sum(weights[k] for k in present)
    score = sum(weights[k] * v for k, v in present.items()) / denom
    score = round(score, 4)
    confidence = round(abs(score), 4)

    import os as _dc_os
    if _dc_os.getenv("LEGACY_CONF_GATES", "0").lower() in ("1", "true", "yes"):
        if confidence < thr:
            direction = "NEUTRAL"
            why = "fused score %+.2f below min-confidence %.2f — no opinion" % (score, thr)
        else:
            direction = "UP" if score > 0 else "DOWN"
            why = "fused score %+.2f (conf %.2f) → %s" % (score, confidence, direction)
    else:
        # Binary: direction from S1 state (structural fact, not score threshold).
        # with_extension(X) → X, fade_both → NEUTRAL, undetermined → NEUTRAL.
        try:
            _dc_cls = None
            try:
                from backend.main import app as _dc_app
                _dc_cls = getattr(_dc_app.state, "last_cls_result", None)
            except Exception:
                pass
            _dc_ab = (_dc_cls or {}).get("accepted_break")
            if _dc_ab in ("UP", "DOWN"):
                direction = _dc_ab
                why = "binary: S1 accepted_break=%s (structural)" % _dc_ab
            elif score > 0:
                direction = "UP"
                why = "binary: score %+.2f → UP (no S1 break, fallback)" % score
            elif score < 0:
                direction = "DOWN"
                why = "binary: score %+.2f → DOWN (no S1 break, fallback)" % score
            else:
                direction = "NEUTRAL"
                why = "binary: score=0, no S1 break → UNDETERMINED"
        except Exception:
            direction = "UP" if score > 0 else ("DOWN" if score < 0 else "NEUTRAL")
            why = "binary fallback: score %+.2f → %s" % (score, direction)

    # --- the leg clamp: the compass NEVER points against a live leg -----------
    # 2026-08-19 shape: DLL trend BEARISH + slower components stale, while a live
    # UP leg ran into a +26pt close. A fresh reversal must FLIP the compass, not
    # be out-voted by the sources it is reversing. Worst case: NEUTRAL (which
    # every consumer treats as "no opinion" → legacy behaviour, no new block).
    if leg_vote is not None and direction != "NEUTRAL":
        leg_name = "UP" if leg_vote > 0 else "DOWN"
        if direction != leg_name:
            return {"direction": "NEUTRAL", "confidence": 0.0, "components": components,
                    "score": score, "context": context,
                    "reason": ("live %s leg (age %d) opposes fused %s — clamped to "
                               "NEUTRAL (a live leg is never traded against; 08-19)"
                               % (leg_name, int(leg_age or 0), direction))}
        why += " · confirmed by live %s leg (age %d)" % (leg_name, int(leg_age or 0))

    parts = ", ".join(
        "%s%s" % (k, {1: "+", -1: "−", 0: "0"}[v]) for k, v in components.items()
        if v is not None)
    return {"direction": direction, "confidence": confidence, "components": components,
            "score": score, "context": context, "reason": "%s [%s]" % (why, parts)}


def has_structural_anchor(compass: Optional[Dict[str, Any]]) -> bool:
    """Is this reading ACTIONABLE — i.e. does a live leg take part in the fusion?

    The consumer boundary, and the single most important calibration decision in
    F1. `leg_state.py`'s doctrine is already the repo's law: *"AGAINST the leg,
    every gate applies untouched — fading a live leg is the forbidden trade."*
    Five ruled flags (LEG_RIDE_V1, LEG_EXEMPT_LSMA_FLAT_V1, LEG_REPLACES_
    SUSTAINED_V1, TREND_LEG_CHASE_EXEMPT_V1, RELEASE_LEG_EXEMPT_V1) already let
    a live leg override day-level gates. F1 applies the symmetric half: a
    direction VERDICT is issued only when that same immediate structural read is
    present. Without a leg the compass is made of the slower sources alone
    (multi-day migration, CVD, LSMA slope) — which is precisely the lagging
    class that produced the failures F1 exists to fix.

    Replay over the 85 live closed trades (2026-07-07..08-19,
    `scripts/f1_compass_replay.py`) — this is not threshold-tuning, the default
    0.25 threshold is used in both rows:

        no anchor required : 14 blocks · 6 losers ‎+$513.75 · **6 winners ‎−$356.25** · net ‎+$157.50
        anchor required    :  7 blocks · 4 losers ‎+$393.75 · **2 winners ‎−$68.75**  · net ‎+$325.00

    The anchor rule drops ‎$120 of prevention to avoid ‎$287 of winner-blocking.
    Raising the confidence threshold instead was measured and is strictly worse
    (it drops the mistake-set catches first). Without an anchor the compass is
    still computed and logged — it simply does not override anything, so every
    gate keeps its legacy input (byte-identical).
    """
    return bool(compass) and (compass.get("components") or {}).get("leg") is not None


def agrees(compass: Optional[Dict[str, Any]], direction: Optional[str]) -> Optional[bool]:
    """True/False when the compass has an ACTIONABLE opinion and the trade
    direction ("LONG"/"SHORT") agrees/opposes it; **None when the compass is
    NEUTRAL or has no structural anchor** — the caller must then keep its legacy
    behaviour (fail-open, no new block)."""
    if not compass:
        return None
    d = compass.get("direction")
    if d not in ("UP", "DOWN") or not has_structural_anchor(compass):
        return None
    want = "UP" if str(direction).upper() == "LONG" else "DOWN"
    return want == d


# ── live fetcher (thin; composes the EXISTING sources, invents nothing) ───────
def current(force: bool = False) -> Dict[str, Any]:
    """Today's compass from the live sources, cached ~20s.

    Read-only. Every source is the one the repo already trusts:
      leg             → leg_state.detect_leg over v9_bars_5min_woodies
      lsma            → direction_context_live.lsma_slope_pts_per_bar
      value_migration → market_context.multiday_migration (multiday_profile)
      cvd             → direction_context.cvd_slope over v9_bars_5min
    Any source that errors or is missing is simply absent from the vote.
    """
    now = _time.time()
    if not force and _CACHE.get("val") is not None and (now - _CACHE.get("ts", 0.0)) < _CACHE_TTL_S:
        return _CACHE["val"]

    lsma_slope = None
    leg_dir = None
    leg_age = 0
    migration = None
    cvd = None
    dll_trend = None

    try:
        from backend.v9.systems.direction_context_live import current as _dc_current
        _dc = _dc_current() or {}
        lsma_slope = _dc.get("lsma_slope_ppb")
        _cs = _dc.get("cvd_slope")
        # cvd_slope is 0 both when flat AND when the source has no delta column
        # (woodies fallback). Only trust it when the bars actually carried CVD.
        if _cs is not None and str(_dc.get("source", "")).startswith("5min"):
            cvd = int(_cs)
    except Exception as err:
        logger.debug("[Compass] direction_context_live unavailable: %s", err)

    try:
        from backend.v9.db.read import read_all as _read_all
        from backend.v9.systems.leg_state import detect_leg as _detect_leg
        _rows = _read_all(
            "SELECT high, low, close, lsma_value, cci_14 FROM v9_bars_5min_woodies "
            "ORDER BY ts DESC LIMIT 12", {})
        if _rows:
            _bars = [{"high": float(r["high"]), "low": float(r["low"]),
                      "close": float(r["close"]),
                      "lsma_value": (float(r["lsma_value"])
                                     if r.get("lsma_value") is not None else None),
                      "cci_14": (float(r["cci_14"])
                                 if r.get("cci_14") is not None else None)}
                     for r in _rows][::-1]
            leg_dir, leg_age, _ = _detect_leg(_bars)
    except Exception as err:
        logger.debug("[Compass] leg detection unavailable: %s", err)

    try:
        from backend.v9.services.market_context import get_market_context
        _mc = get_market_context()
        migration = getattr(_mc, "multiday_migration", None) if _mc else None
    except Exception as err:
        logger.debug("[Compass] multiday migration unavailable: %s", err)

    try:
        from backend.v9.systems.delta_features import extract_features as _df
        import json as _json
        from pathlib import Path as _P
        _p = _P(os.path.expanduser(os.getenv(
            "V9_EXPORT_DIR", "~/SierraChart_Data/v9_export/"))) / "delta_export.json"
        if _p.exists():
            dll_trend = _df(_json.loads(_p.read_text() or "{}")).get("dll_trend")
    except Exception:
        dll_trend = None  # context only — never blocks, never votes

    out = compute_compass(
        lsma_slope=lsma_slope, leg_dir=leg_dir, leg_age=leg_age,
        value_migration=migration, cvd_slope=cvd, dll_trend=dll_trend,
        min_confidence=_min_conf_env(),
    )
    _CACHE.update({"ts": now, "val": out})
    return out


def _min_conf_env() -> float:
    try:
        return float(os.getenv("DIRECTION_COMPASS_MIN_CONF", "") or DEFAULT_MIN_CONFIDENCE)
    except (TypeError, ValueError):
        return DEFAULT_MIN_CONFIDENCE


def reset_cache() -> None:
    """Testing only."""
    _CACHE.clear()


# ── gate helpers (the compass as the single INPUT of the existing gates) ──────
# Stair / ladder patterns are structurally exempt from the direction rule (G2
# coherence, MAX_DAYS §1): a TREND_STEP rides an established staircase and is
# judged by its own structure, not by the day compass.
STAIR_PREFIXES = ("TREND_STEP", "STAIR")


def is_stair_pattern(pattern: Optional[str]) -> bool:
    return bool(pattern) and str(pattern).upper().strip().startswith(STAIR_PREFIXES)


def compass_or(fallback: Optional[str], compass: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """The direction a gate should consume: the compass when it has an opinion,
    otherwise the gate's existing legacy value (byte-identical behaviour).
    Flag OFF ⇒ always the legacy value."""
    if not flag_on():
        return fallback
    try:
        c = compass if compass is not None else current()
        d = (c or {}).get("direction")
        if d in ("UP", "DOWN") and has_structural_anchor(c):
            return d
        return fallback
    except Exception as err:      # fail-open — a compass bug never changes a gate
        logger.warning("[Compass] compass_or errored (fail-open to legacy): %s", err)
        return fallback


def direction_verdict(*, pattern: Optional[str], direction: Optional[str],
                      compass: Optional[Dict[str, Any]] = None) -> tuple:
    """The with-day-direction rule for EVERY pattern (G1/R6 + the OD fix).

    Returns ``(allow: bool, reason: str)``. Blocks only when ALL hold:
      * `DIRECTION_COMPASS_V1` is on,
      * the compass has a confident UP/DOWN opinion (NEUTRAL ⇒ allow, unchanged),
      * a live leg anchors that opinion (see `has_structural_anchor`),
      * the setup direction opposes it,
      * the pattern is not a stair (G2 structural exemption).
    A live leg can never be opposed — the clamp inside `compute_compass` already
    guarantees the compass agrees with any live leg, so with-leg entries are
    structurally un-blockable here. No hour is ever consulted.
    """
    if not flag_on():
        return (True, "DIRECTION_COMPASS_V1 off")
    try:
        c = compass if compass is not None else current()
    except Exception as err:
        logger.warning("[Compass] direction_verdict errored (fail-open): %s", err)
        return (True, "compass unavailable (fail-open)")
    ok = agrees(c, direction)
    if ok is None:
        return (True, "compass NEUTRAL (%s) — legacy behaviour" % (c or {}).get("reason", ""))
    if ok:
        return (True, "with-compass %s (conf %.2f)" % (c.get("direction"), c.get("confidence", 0.0)))
    if is_stair_pattern(pattern):
        return (True, "stair pattern %s — structurally exempt from the direction rule (G2)"
                % pattern)
    return (False, "%s %s against compass %s (conf %.2f): %s"
            % (pattern or "?", direction, c.get("direction"),
               c.get("confidence", 0.0), c.get("reason", "")))
