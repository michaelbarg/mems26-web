"""Rule 1 guard — the daily-test header must not print a books sum under a broker label.

Incident (2026-10-06, cowork-dev night queue): the chart had moved to the Sim1 account, so
all four live-flagged trades (#3123/#3130/#3136/#3140) were routed to simulation and
`broker_truth.py` returned ZERO broker rows for the day — yet
`docs/reports/DAY_REVIEW_2026-10-06.md` opened with "לייב 4 עסקאות -6.25$ (ברוקר)".
Two separate lies in one label: the number came from `pnl_usd` (the books) via a silent
fallback, and `#3140` (SIERRA_FLAT, no exit price, no P&L) was counted as 0 instead of
being named as unpriced.

`day_review.py` executes its report at import time, so this is a source-level guard rather
than a unit test of the function: it asserts the header label is derived (`live_src`) and
that the literal broker label is no longer hard-coded into the header line. The label text
itself is verified by running the script (Rule 5):
    2026-10-06 -> "(ספרים · אין רישום-ברוקר ל-4 · ללא תמחור #3140)"
    2026-10-05 -> "(ברוקר)"   # pnl_sierra present on that day's live row
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SRC = os.path.join(ROOT, "scripts", "day_review.py")


def _src():
    with open(SRC, encoding="utf-8") as f:
        return f.read()


def test_header_label_is_derived_not_hardcoded():
    src = _src()
    header = [ln for ln in src.splitlines() if "מהלכים ששווה לתפוס" in ln]
    assert header, "the daily-test header line vanished from day_review.py"
    for ln in header:
        assert "(ברוקר)" not in ln, (
            "the header hard-codes a broker label; it must read the source from live_src "
            "(a books sum under a broker label is the 06.10 Rule 1 incident)"
        )
        assert "live_src" in ln, "the header must print R['live_src']"


def test_live_src_distinguishes_broker_books_and_unpriced():
    src = _src()
    # the three states the label has to be able to say
    assert re.search(r'live_src\s*=\s*"ברוקר"', src), "no broker-only label branch"
    assert "אין רישום-ברוקר" in src, "no 'zero broker rows' label branch"
    assert "ללא תמחור" in src, "unpriced rows are not named in the label"
    # and the sum itself must never fall back from pnl_sierra to pnl_usd silently
    assert "float(t[\"pnl_usd\"] or 0)" not in src, (
        "silent books fallback is back: a row with neither value would count as 0"
    )


def test_review_payload_carries_the_source_fields():
    src = _src()
    assert "live_src=live_src" in src, "live_src is not returned in the review dict"
    assert "live_broker_n=" in src, "live_broker_n is not returned (n/N is a required field)"
    assert "live_unpriced=" in src, "live_unpriced is not returned"
