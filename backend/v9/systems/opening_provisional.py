"""T-426 — provisional opening type for a CONFIRMED opening drive while the
T-314 label still lags (Michael 20.09 09:40: "תתקן את הענף … שוב קנית מאוחר מדי").

The T-314 detector (opening_detector_v2) calls OPEN_DRIVE only once the open
sits within 20% of the SESSION range from the extreme. Early in a drive the
range is small, so the first bar's counter-spike (4.5 pts on 18.09) exceeds
that tolerance and the label stays OPEN_AUCTION_IN until the range has grown
~5× — at 17:00 on 18.09, after 25 of the drive's 26 points. Meanwhile the
opening engine had a structurally confirmed drive at 16:45 (close beyond the
opening range, 3 closed bars, confirming closed bar), and the phase-B
playbook row for AUCTION_IN allows EDGE_FADE only ⇒ `dalton_intent:kind`.

Measured (scripts/open_drive_branch_study.py, 56 clean sessions, closed bars,
fixed evaluation model, 1 contract to T1=1.5R):
  DRIVE candidates the tree admits today   N=7   43% win  Σ$ −12
  DRIVE candidates the label lag BLOCKS    N=14  64% win  Σ$ +519  (2c ladder +1,270)
The blocked half is the better half. Rule lives in the gateway (doctrine:
rules in gateway/tree, not detectors); the detector is untouched.

Pure function — no I/O, unit-tested in tests/v9/regression/test_opening_provisional.py.
"""
from __future__ import annotations

from typing import Optional, Tuple

_LAGGING_LABELS = frozenset({"OPEN_AUCTION_IN", "OPEN_AUCTION_OUT", "UNKNOWN", "NA", "None", ""})
_PROVISIONAL = {
    "OPENING_DRIVE": "OPEN_DRIVE",
    "OPENING_TEST_DRIVE": "OPEN_TEST_DRIVE",
}


def provisional_opening_type(dp_ot: Optional[str], *, locked: bool, classification: Optional[str],
                             direction: Optional[str]) -> Tuple[str, Optional[str], bool]:
    """Return (opening_type, direction_hint, applied).

    applied=True only when ALL hold:
      • the setup is the opening engine's own drive entry (OPENING_DRIVE /
        OPENING_TEST_DRIVE — a close beyond the opening range on a narrow OR,
        3 closed bars and a confirming closed bar, structural risk ≤ 25 pt);
      • the T-314 label is a lagging one (AUCTION_IN/OUT or unknown) and NOT
        locked (a locked label is a ruling of the day-type machine and stays);
      • the setup carries a LONG/SHORT direction (it becomes the drive direction).
    Otherwise the inputs are returned unchanged (applied=False).
    """
    ot = str(dp_ot or "")
    cls = str(classification or "").upper()
    d = str(direction or "").upper()
    if locked or cls not in _PROVISIONAL or ot not in _LAGGING_LABELS or d not in ("LONG", "SHORT"):
        return ot, None, False
    return _PROVISIONAL[cls], d, True
