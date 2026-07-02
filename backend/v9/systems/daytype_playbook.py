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
        "BULL_FLAG": "FLAGS", "BEAR_FLAG": "FLAGS", "FLAG": "FLAGS",
    }
    return aliases.get(p, p)


def decide(
    pattern: str,
    day_type: Optional[str],
    direction: Optional[str],
    trend_state: Optional[str] = None,
    max_contracts: Optional[int] = None,
) -> Decision:
    """Return a Decision for (pattern, day_type, direction, live trend_state).

    OFF or any unmatched input → FULL (fail-open, never blocks).

    #68: When DAYTYPE_POSITION_GATE is ON, the position gate is the
    direction control — the playbook returns FULL for everything (all
    patterns fire; direction filtering happens in the position gate).
    The playbook's SKIP/REDUCED verdicts only apply when the position
    gate is OFF (legacy mode).
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
    if not pat or day_type not in _VALID_DT:
        return Decision("FULL", cap, f"unmapped({pkey}/{day_type})")

    # Direction discipline: with-trend only on directional days (D-1: incl. Variation).
    if pat.get("require_with_trend") and day_type in _DIRECTIONAL_DAYS and trend_state:
        d = (direction or "").upper()
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
