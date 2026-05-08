"""
MEMS26 Decision Gates Package.

Per D-046, decision gates are independent veto checks.
Each gate returns PASS or BLOCK with structured reason.
ANY gate fail = NO TRADE.

Gates implemented in this package:
- suffering_side: Veto trades against day POC (D-049, D-065)

Future gates (Sprint 4):
- otf_clarity: Block when OTF buyers/sellers unclear (D-050)
- vegas_strategic: Don't fight strong trend (D-052)
- day_type_risk: Block on Nontrend days (D-052)
- killzone: Block outside main hours (D-052)
"""

from .suffering_side import check_suffering_side, GateResult

__all__ = ["check_suffering_side", "GateResult"]
