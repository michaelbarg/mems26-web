"""D-WDIAG: Extreme-CCI trend relabel — shared function.

Called by woodies_system.py (production) AND tests (verification).
Single source of truth for the relabel logic.

When S4_EXTREME_TREND_RELABEL=true and |CCI|>=200 with trend GRAY/YELLOW,
relabels studies["trend_state"] to BLUE (CCI>0) or RED (CCI<0).

Mutates the studies dict in place.
"""

from backend.v9.shared.atr import flag


def apply_extreme_trend_relabel(studies: dict) -> None:
    """Relabel GRAY → BLUE/RED when the CCI is clearly extended past the
    Stage-1 ±line, so S4 patterns don't wait ~6 bars for the lagging paint.

    Mutates studies["trend_state"] in place. Always records
    studies["trend_original"] (pre-relabel) for A/B comparison.

    Two layers (both no-op unless their flag is ON):

    • S4_GRAY_RELABEL_V1 (Michael ruling 2026-07-17, HARD EVIDENCE): the DLL
      paint lags the CCI by ~6 bars — on 07-17 the CCI hit +182 during the
      16:45→17:05 rally while paint stayed GRAY until 17:15, by which time the
      +56pt move was over (S4 blind the whole way). Relabel **GRAY only** to
      BLUE/RED when |CCI| >= S4_GRAY_RELABEL_CCI (default 100 = the ±100 line
      GB100/Stage-1 itself trades). YELLOW is NOT touched — that is the trend-
      transition whipsaw guard (P-W5), a different rule; Michael ruled out the
      GRAY, not the YELLOW.

    • S4_EXTREME_TREND_RELABEL (legacy D-WDIAG): GRAY *and* YELLOW at ±200.
      Preserved byte-identical for backward compat.
    """
    import os as _os
    studies["trend_original"] = studies.get("trend_state")
    trend = studies.get("trend_state")
    cci = studies.get("cci_14") or 0

    # ── Layer 1: GRAY de-lag at the Stage-1 line (Michael 2026-07-17) ──
    if flag("S4_GRAY_RELABEL_V1") and trend in ("GRAY", "GREY"):
        try:
            _thr = float(_os.getenv("S4_GRAY_RELABEL_CCI", "100"))
        except (TypeError, ValueError):
            _thr = 100.0
        if abs(cci) >= _thr:
            studies["trend_state"] = "BLUE" if cci > 0 else "RED"
            studies["trend_relabel_src"] = "gray_delag"
            return

    # ── Layer 2: legacy extreme relabel (GRAY+YELLOW at ±200) ──
    if not flag("S4_EXTREME_TREND_RELABEL"):
        return
    if trend not in ("GRAY", "YELLOW", "GREY"):
        return
    if abs(cci) >= 200:
        studies["trend_state"] = "BLUE" if cci > 0 else "RED"
        studies["trend_relabel_src"] = "extreme_200"
