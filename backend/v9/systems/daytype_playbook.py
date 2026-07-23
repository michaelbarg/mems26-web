"""Day-type playbook decision engine (flag-gated, default OFF).

Reads ``config/daytype_playbook.yaml`` and decides FULL / REDUCED / SKIP for a
pattern given the current day-type, plus direction discipline (with-trend only on
trend days). One editable config drives it — change a pattern's block to change
only that pattern.

GATE: env ``DAYTYPE_PLAYBOOK`` in {1,true,yes}. When unset/off, ``decide()``
returns a PASS verdict (FULL, full size) for everything → ZERO change to firing.
FAIL-OPEN: any config gap / unknown pattern / unknown day-type also returns FULL —
this engine can only *narrow* trading when explicitly enabled and matched; it never
blocks on uncertainty.

NOT wired into the fire path yet (Michael gate). Inert until a caller consults it
AND the flag is on. Stop/target numbers live in stop_anchors.yaml / targets.yaml —
not duplicated here.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Optional

from backend.v9.config_loader import _load_yaml  # reuse loader + config dir

_VALID_DT = {
    "Trend_Normal", "Trend_DD", "Normal", "Variation",
    "Neutral_Center", "Neutral_Extreme", "Nontrend",
}
_TREND_DAYS = {"Trend_Normal", "Trend_DD"}
# D-1: Variation is a directional day — require_with_trend applies there too
_DIRECTIONAL_DAYS = {"Trend_Normal", "Trend_DD", "Variation"}

_cache: Optional[dict] = None
_loaded = False


@dataclass
class Decision:
    verdict: str        # FULL | REDUCED | SKIP
    contracts: int      # resolved contract count (0 on SKIP)
    reason: str

    @property
    def allow(self) -> bool:
        return self.verdict != "SKIP"


def _enabled() -> bool:
    return os.environ.get("DAYTYPE_PLAYBOOK", "").lower() in ("1", "true", "yes")


def _nonconviction_active() -> bool:
    """P1-8 (env NONCONVICTION_ACTIVE_V1, default OFF). When ON, 'Nonconviction'
    becomes a VALID day-type here so config/daytype_playbook.yaml's ``Nonconviction:
    SKIP`` cells actually gate a no-conviction day (stand aside / NO_TRADE). When OFF,
    'Nonconviction' stays out of the valid set -> decide() fails open to FULL,
    byte-identical to today. Paired with main.py's NO_TRADE-sentinel promotion."""
    return os.environ.get("NONCONVICTION_ACTIVE_V1", "0").lower() in ("1", "true", "yes")


def _day_direction_v1() -> bool:
    """REQUIRE_WITH_TREND_DAY_DIRECTION_V1 (default OFF). When ON, require_with_trend
    compares against day-direction / expansion — not momentary trend_state.
    Responsive REV (REACTIVE/HNS) are location-gated (SHORT@VAH / LONG@VAL).
    OFF → legacy trend_state path, byte-identical."""
    return os.environ.get("REQUIRE_WITH_TREND_DAY_DIRECTION_V1", "0").lower() in (
        "1", "true", "yes",
    )


# Responsive fade patterns: exempt from trend_state / day-dir color; location owns them.
_RESPONSIVE_REV = frozenset({"REACTIVE", "HNS"})


def _normalize_location(location: Optional[str]) -> Optional[str]:
    if not location:
        return None
    loc = str(location).strip().lower().replace("-", "_")
    aliases = {
        "at_vah": "near_vah", "vah": "near_vah", "ceiling": "near_vah",
        "at_val": "near_val", "val": "near_val", "floor": "near_val",
        "above": "above_value", "below": "below_value", "mid": "mid_value",
    }
    return aliases.get(loc, loc)


def _resolve_location(
    location: Optional[str],
    entry_price: Optional[float],
    levels: Optional[dict],
) -> Optional[str]:
    """Prefer explicit location; else derive from entry vs VAH/VAL (location_gate.zone_of)."""
    loc = _normalize_location(location)
    if loc is not None:
        return loc
    if entry_price is None or not isinstance(levels, dict):
        return None
    try:
        from backend.v9.systems.location_gate import zone_of
        vah = float(levels["vah"])
        val = float(levels["val"])
        return zone_of(float(entry_price), vah, val, levels.get("ib_width"))
    except (KeyError, TypeError, ValueError):
        return None


def _cfg() -> Optional[dict]:
    global _cache, _loaded
    if not _loaded:
        _loaded = True
        _cache = _load_yaml("daytype_playbook.yaml")
    return _cache


def reset_cache() -> None:
    """Testing only — clears the cached config."""
    global _cache, _loaded
    _cache = None
    _loaded = False


def _norm(pattern: str) -> str:
    """Normalize a fired pattern id to a playbook key (strip _LONG/_SHORT, alias)."""
    p = (pattern or "").upper().strip()
    for suf in ("_LONG", "_SHORT"):
        if p.endswith(suf):
            p = p[: -len(suf)]
    aliases = {
        "INVERSE_HNS": "HNS", "HNS_TOP": "HNS", "IHNS": "HNS",
        "DOUBLE_BOTTOM": "DBDT", "DOUBLE_TOP": "DBDT", "DB_EE": "DBDT", "DT_AA": "DBDT",
        "DOUBLE_BOTTOM_EE": "DBDT", "DOUBLE_TOP_AA": "DBDT",  # item-9: real pattern IDs
        "BULL_FLAG": "FLAGS", "BEAR_FLAG": "FLAGS", "FLAG": "FLAGS",
    }
    return aliases.get(p, p)


def decide(
    pattern: str,
    day_type: Optional[str],
    direction: Optional[str],
    trend_state: Optional[str] = None,
    max_contracts: Optional[int] = None,
    *,
    day_direction: Optional[str] = None,
    location: Optional[str] = None,
    entry_price: Optional[float] = None,
    levels: Optional[dict] = None,
) -> Decision:
    """Return a Decision for (pattern, day_type, direction, live trend_state).

    OFF or any unmatched input → FULL (fail-open, never blocks).

    #68: When DAYTYPE_POSITION_GATE is ON, the position gate is the
    direction control — the playbook returns FULL for everything (all
    patterns fire; direction filtering happens in the position gate).
    The playbook's SKIP/REDUCED verdicts only apply when the position
    gate is OFF (legacy mode).

    REQUIRE_WITH_TREND_DAY_DIRECTION_V1 (default OFF): when ON, require_with_trend
    uses ``day_direction`` (UP/DOWN from get_live_expansion / dir_bias) instead of
    momentary ``trend_state``. Responsive REV (REACTIVE/HNS) skip the color check
    and are gated by location (SHORT near VAH / LONG near VAL). Extra kwargs are
    ignored when the flag is OFF → byte-identical legacy path.
    """
    cfg = _cfg()
    cap = max_contracts or (cfg or {}).get("max_contracts", 3)

    if not _enabled():
        return Decision("FULL", cap, "playbook-off")

    # #68: position gate supersedes pattern suppression
    if os.environ.get("DAYTYPE_POSITION_GATE", "0").lower() in ("1", "true", "yes"):
        return Decision("FULL", cap, f"position-gate-active (all-patterns-fire)")

    if not cfg:
        return Decision("FULL", cap, "no-config")

    pkey = _norm(pattern)
    pat = (cfg.get("patterns") or {}).get(pkey)
    # P1-8: 'Nonconviction' is a VALID day-type only when NONCONVICTION_ACTIVE_V1 is ON
    # (else it stays unmapped -> fail-open FULL, byte-identical to today).
    _valid_dt = (_VALID_DT | {"Nonconviction"}) if _nonconviction_active() else _VALID_DT
    if not pat or day_type not in _valid_dt:
        return Decision("FULL", cap, f"unmapped({pkey}/{day_type})")

    # Direction discipline: with-trend only on directional days (D-1: incl. Variation).
    if pat.get("require_with_trend") and day_type in _DIRECTIONAL_DAYS:
        d = (direction or "").upper()
        if _day_direction_v1():
            if pkey in _RESPONSIVE_REV:
                # RESPONSIVE_WITH_DAY_TREND_V1 (Michael ruling 2026-07-23 "לבנות +
                # לאמת-סים + להדליק חי"): on a directional day the responsive family
                # must obey the DAY TREND, not just value-location. The 07-23 live
                # miss — a RED (down) session, price pulled back UP to mid-value —
                # exposed both halves of the location-only bug: the with-trend SHORT
                # was BLOCKED ("not at VAH", mid_value) while a counter-trend LONG at
                # VAL would have been ALLOWED (buy-the-dip into a downtrend). Doctrine
                # (Dalton): on a trend day you SELL the rally and NEVER fade the
                # trend. When a day_direction is known (accepted-break expansion, or
                # the held-LSMA dir_bias fallback):
                #   • counter-trend (LONG on DOWN / SHORT on UP) → SKIP (never fade)
                #   • with-trend  (SHORT on DOWN / LONG on UP) → ALLOW as continuation,
                #     off the value-edge — a pullback-high short is the "מנקודה גבוהה"
                #     entry Michael wanted, NOT a value-edge fade — EXCEPT when it is
                #     chasing the far extreme (SHORT at below_value / LONG at
                #     above_value) → SKIP ("enter from a pullback, not the low").
                # Flag OFF or day_direction unknown → location-only (byte-identical).
                _dd = (day_direction or "").upper()
                _wt_on = os.environ.get(
                    "RESPONSIVE_WITH_DAY_TREND_V1", "0"
                ).lower() in ("1", "true", "yes")
                _with_trend_allow = False
                if _wt_on and _dd in ("UP", "DOWN"):
                    if (d == "LONG" and _dd == "DOWN") or (d == "SHORT" and _dd == "UP"):
                        return Decision(
                            "SKIP", 0,
                            f"{pkey} counter-trend responsive on {day_type} "
                            f"(day_dir={_dd}) — never fade the trend",
                        )
                    _loc_wt = _resolve_location(location, entry_price, levels)
                    _chase = (d == "SHORT" and _loc_wt == "below_value") or (
                        d == "LONG" and _loc_wt == "above_value")
                    if _chase:
                        return Decision(
                            "SKIP", 0,
                            f"{pkey} with-trend {d} chasing extreme ({_loc_wt}) on "
                            f"{day_type} — enter from a pullback, not the {'low' if d == 'SHORT' else 'high'}",
                        )
                    _with_trend_allow = True  # continuation: bypass the value-edge check
                if not _with_trend_allow:
                    # Responsive fade: location owns allow/deny — ignore trend_state.
                    loc = _resolve_location(location, entry_price, levels)
                    if loc is not None:
                        short_ok = loc in ("near_vah", "above_value")
                        long_ok = loc in ("near_val", "below_value")
                        if d == "SHORT" and not short_ok:
                            return Decision(
                                "SKIP", 0,
                                f"{pkey} responsive SHORT not at VAH ({loc}) on {day_type}",
                            )
                        if d == "LONG" and not long_ok:
                            return Decision(
                                "SKIP", 0,
                                f"{pkey} responsive LONG not at VAL ({loc}) on {day_type}",
                            )
                    # missing location → fail-open (do not fall back to trend_state)
            else:
                # Non-responsive (e.g. CONFLUENCE): compare vs day expansion direction.
                dd = (day_direction or "").upper()
                if dd in ("UP", "DOWN"):
                    counter = (d == "LONG" and dd == "DOWN") or (d == "SHORT" and dd == "UP")
                    if counter:
                        return Decision(
                            "SKIP", 0,
                            f"{pkey} counter-day-direction on {day_type} (day_dir={dd})",
                        )
                # missing day_direction → fail-open (honest; no trend_state fallback)
        elif trend_state:
            # Legacy path (flag OFF): momentary CCI / trend_state — byte-identical.
            ts = trend_state.upper()
            counter = (d == "LONG" and ts == "RED") or (d == "SHORT" and ts == "BLUE")
            if counter:
                return Decision("SKIP", 0, f"{pkey} counter-trend on {day_type} (trend={ts})")

    verdict = (pat.get("cells") or {}).get(day_type, "FULL")
    if verdict == "SKIP":
        return Decision("SKIP", 0, f"{pkey} SKIP on {day_type}")
    if verdict == "REDUCED":
        return Decision("REDUCED", max(1, math.ceil(cap / 2)), f"{pkey} REDUCED on {day_type}")
    return Decision("FULL", cap, f"{pkey} FULL on {day_type}")
