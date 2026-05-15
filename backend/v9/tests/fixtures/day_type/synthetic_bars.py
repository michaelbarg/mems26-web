"""Synthetic bar generators for E2E day type tests.

Generates realistic 5-min bar sequences for specific day type scenarios.
Each scenario produces bars that should classify to a specific day type
when fed through the full state machine pipeline.
"""

from backend.v9.systems.day_type.schemas import BarInput


def _bar(session_min, o, h, l, c, **kwargs):
    """Create a BarInput with sensible defaults."""
    defaults = dict(
        ts=1000000.0 + session_min * 60,
        session_min=session_min,
        open=o, high=h, low=l, close=c,
        volume=500,
    )
    defaults.update(kwargs)
    return BarInput(**defaults)


def generate_trend_normal_od_narrow(base=5250.0):
    """Open Drive + Narrow IB -> Trend_Normal.

    Pattern: strong directional open, narrow IB (< 15pt), extension after IB.
    """
    bars = []
    # A1: Pre-open context (1 bar)
    bars.append(_bar(0, base, base + 5, base - 1, base + 4,
                     pd_high=base + 20, pd_low=base - 20, pd_close=base))
    # A2: Opening — strong drive up (3 bars, 5-min each)
    for i in range(1, 4):
        o = base + i * 4
        bars.append(_bar(i * 5, o, o + 5, o - 0.5, o + 4,
                         pd_high=base + 20, pd_low=base - 20, pd_close=base))
    # A3: IB period (09:30-10:30 = minutes 0-60, narrow range ~12 pts)
    for m in range(20, 65, 5):
        bars.append(_bar(m, base + 10, base + 12, base, base + 10))
    # Post-IB: extension up
    for m in range(65, 120, 5):
        offset = (m - 60) * 0.3
        bars.append(_bar(m, base + 12 + offset, base + 14 + offset,
                         base + 10 + offset, base + 13 + offset, atr=20))
    return bars


def generate_variation_otd_medium(base=5250.0):
    """Open Test Drive + Medium IB -> Variation.

    Pattern: test drive down then reversal, medium IB (15-25pt).
    """
    bars = []
    bars.append(_bar(0, base, base + 2, base - 3, base - 2,
                     pd_high=base + 15, pd_low=base - 15, pd_close=base))
    # Opening: test drive — initial dip then recovery
    for i in range(1, 4):
        o = base - i * 2
        bars.append(_bar(i * 5, o, o + 3, o - 2, o + 2,
                         pd_high=base + 15, pd_low=base - 15, pd_close=base))
    # IB: medium range (~18 pts)
    for m in range(20, 65, 5):
        bars.append(_bar(m, base - 5, base + 8, base - 10, base + 3))
    # Post-IB: rotation
    for m in range(65, 120, 5):
        bars.append(_bar(m, base + 3, base + 10, base - 5, base + 1,
                         atr=20, extensions_up=1, returned_to_range=True))
    return bars


def generate_nontrend_oa_in_narrow(base=5250.0):
    """Open Auction In + Narrow IB -> Nontrend.

    Pattern: quiet open inside prior day, narrow IB, no extension.
    """
    bars = []
    bars.append(_bar(0, base, base + 1, base - 1, base,
                     pd_high=base + 30, pd_low=base - 30, pd_close=base))
    # Opening: rotational
    for i in range(1, 4):
        bars.append(_bar(i * 5, base + i % 2, base + 2, base - 2, base - i % 2,
                         pd_high=base + 30, pd_low=base - 30, pd_close=base))
    # IB: very narrow (~8 pts)
    for m in range(20, 65, 5):
        bars.append(_bar(m, base, base + 4, base - 4, base + 1))
    # Post-IB: compressed, no extension
    for m in range(65, 120, 5):
        bars.append(_bar(m, base + 1, base + 3, base - 3, base, atr=20))
    return bars


def generate_trend_dd_oa_out_narrow(base=5250.0):
    """Open Auction Out + Narrow IB -> Trend_DD.

    Pattern: gap up above prior day, narrow IB, strong extension.
    """
    bars = []
    gap_base = base + 40  # above pd_high
    bars.append(_bar(0, gap_base, gap_base + 3, gap_base - 1, gap_base + 2,
                     pd_high=base + 20, pd_low=base - 20, pd_close=base))
    for i in range(1, 4):
        o = gap_base + i * 2
        bars.append(_bar(i * 5, o, o + 3, o - 1, o + 2,
                         pd_high=base + 20, pd_low=base - 20, pd_close=base))
    # IB: narrow
    for m in range(20, 65, 5):
        bars.append(_bar(m, gap_base + 5, gap_base + 10, gap_base, gap_base + 7))
    # Post-IB: extension
    for m in range(65, 120, 5):
        offset = (m - 60) * 0.4
        bars.append(_bar(m, gap_base + 10 + offset, gap_base + 13 + offset,
                         gap_base + 8 + offset, gap_base + 12 + offset, atr=20))
    return bars


def generate_neutral_extensions(base=5250.0):
    """Both-side extension scenario.

    Pattern: extends above IB then below — should become Neutral via delta rule.
    """
    bars = []
    bars.append(_bar(0, base, base + 2, base - 2, base,
                     pd_high=base + 15, pd_low=base - 15, pd_close=base))
    for i in range(1, 4):
        bars.append(_bar(i * 5, base, base + 3, base - 3, base + 1,
                         pd_high=base + 15, pd_low=base - 15, pd_close=base))
    # IB
    for m in range(20, 65, 5):
        bars.append(_bar(m, base, base + 8, base - 8, base + 2))
    # Post-IB: extension UP then DOWN
    for m in range(65, 90, 5):
        bars.append(_bar(m, base + 8, base + 15, base + 6, base + 12,
                         atr=20, extensions_up=1))
    for m in range(90, 120, 5):
        bars.append(_bar(m, base - 5, base - 2, base - 12, base - 10,
                         atr=20, extensions_up=1, extensions_down=1))
    return bars
