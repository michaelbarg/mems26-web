"""D-WDIAG: Extreme-CCI trend relabel — shared function.

Called by woodies_system.py (production) AND tests (verification).
Single source of truth for the relabel logic.

When S4_EXTREME_TREND_RELABEL=true and |CCI|>=200 with trend GRAY/YELLOW,
relabels studies["trend_state"] to BLUE (CCI>0) or RED (CCI<0).

Mutates the studies dict in place.
"""

from backend.v9.shared.atr import S4_EXTREME_TREND_RELABEL


def apply_extreme_trend_relabel(studies: dict) -> None:
    """D-WDIAG: Relabel GRAY/YELLOW → BLUE/RED on extreme CCI (±200+).

    Mutates studies["trend_state"] in place. No-op when flag OFF or CCI < 200.
    """
    if not S4_EXTREME_TREND_RELABEL:
        return
    trend = studies.get("trend_state")
    if trend not in ("GRAY", "YELLOW", "GREY"):
        return
    cci = studies.get("cci_14") or 0
    if abs(cci) >= 200:
        studies["trend_state"] = "BLUE" if cci > 0 else "RED"
