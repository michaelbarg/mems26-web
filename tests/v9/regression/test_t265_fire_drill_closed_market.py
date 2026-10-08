# -*- coding: utf-8 -*-
"""T-265 / T-532 regression, drill side (BRIEF §3.3, fix-agent night 08→09.10): `fire_drill` must not
declare "feed ישן" on a closed market.

Stage D had two feed lines with two different ideas of "the market": the newest-DB-bar line (T-430,
20.09) was informational on a closed market, but the price-export line (`feed טרי (<30s)`) was a hard
check at any hour — so a Saturday restart window (Sierra off, Globex closed) went NO-GO on a line that
could not pass. Both lines now share one pure predicate, `cme_globex_open`, pinned here edge by edge;
`feed_price_line` is pinned behaviourally through FAILS, the drill's own verdict list.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from scripts import fire_drill as fd

_ET = ZoneInfo("America/New_York")


def _et(y, m, d, hh, mm):
    return datetime(y, m, d, hh, mm, tzinfo=_ET)


# 2026-10-02 Fri · 03 Sat · 04 Sun · 05 Mon · 08 Thu
@pytest.mark.parametrize("when, expected", [
    (_et(2026, 10, 3, 10, 0), False),     # Saturday — the restart window
    (_et(2026, 10, 3, 3, 0), False),      # Saturday 03:00 IL-morning equivalent
    (_et(2026, 10, 4, 17, 59), False),    # Sunday before the 18:00 open
    (_et(2026, 10, 4, 18, 0), True),      # Sunday 18:00 — Globex opens
    (_et(2026, 10, 2, 16, 59), True),     # Friday 16:59 — still open
    (_et(2026, 10, 2, 17, 0), False),     # Friday 17:00 — weekly close
    (_et(2026, 10, 2, 23, 0), False),     # Friday night
    (_et(2026, 10, 8, 16, 59), True),     # Thursday before the daily break
    (_et(2026, 10, 8, 17, 0), False),     # daily break 17:00–18:00 ET
    (_et(2026, 10, 8, 17, 59), False),
    (_et(2026, 10, 8, 18, 0), True),      # reopens 18:00 ET
    (_et(2026, 10, 5, 2, 30), True),      # Monday 02:30 ET (09:30 IL) — Globex open overnight
    (_et(2026, 10, 5, 9, 35), True),      # RTH
])
def test_cme_globex_open_edges(when, expected):
    assert fd.cme_globex_open(when) is expected


class TestFeedPriceLine:
    @pytest.fixture(autouse=True)
    def _clean_fails(self):
        fd.FAILS.clear()
        yield
        fd.FAILS.clear()

    def test_stale_feed_on_closed_market_is_information_not_a_fail(self, capsys):
        assert fd.feed_price_line({"age_ms": 4_000_000}, market_open=False) is False
        assert fd.FAILS == []                                   # ← the fix: no "feed ישן" NO-GO
        assert "השוק סגור" in capsys.readouterr().out

    def test_no_price_on_closed_market_is_information_not_a_fail(self):
        assert fd.feed_price_line(None, market_open=False) is False
        assert fd.FAILS == []

    def test_stale_feed_on_open_market_still_fails(self):
        assert fd.feed_price_line({"age_ms": 4_000_000}, market_open=True) is False
        assert len(fd.FAILS) == 1 and fd.FAILS[0].startswith("feed טרי")

    def test_fresh_feed_on_open_market_passes(self):
        assert fd.feed_price_line({"age_ms": 1200}, market_open=True) is True
        assert fd.FAILS == []
