"""Shared fixtures for pattern tests."""

import pytest
from backend.v9.systems.chart_5min.models import Bar


def make_bar(o=100, h=101, c=100.5, l=99.5, vol=100, **kw) -> Bar:
    return Bar(o=o, h=h, l=l, c=c, vol=vol, **kw)


def bullish_bar(base=100, size=1.0, **kw) -> Bar:
    return Bar(o=base, h=base + size * 1.2, l=base - size * 0.3, c=base + size, vol=100, **kw)


def bearish_bar(base=100, size=1.0, **kw) -> Bar:
    return Bar(o=base + size, h=base + size * 1.2, l=base - size * 0.3, c=base, vol=100, **kw)
