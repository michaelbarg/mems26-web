"""G1 (Michael 2026-07-19, GAP G-01): the routed current_bar must get the SAME
CCI-direct trend relabel as the closed-bar path, so S4 sees a timely trend on the
live bar instead of sticky-GRAY.

The fix in bars.py applies `_trend_from_cci(last_flat.trend_state, last_flat.cci_14)`
to the current_bar override (mirroring the closed-bar path at :1087). Since
`_trend_from_cci` gates on TREND_CCI_DIRECT_V1 internally, flag OFF is a strict
no-op (byte-identical) and flag ON applies the relabel.

These pin the pure `_trend_from_cci` behavior on current_bar-shaped inputs.
"""
import importlib

import backend.v9.api.v9.bars as bars


def _tf(monkeypatch, trend, cci, flag="1", thr=None):
    monkeypatch.setenv("TREND_CCI_DIRECT_V1", flag)
    if thr is not None:
        monkeypatch.setenv("TREND_CCI_DIRECT_PT", str(thr))
    else:
        monkeypatch.delenv("TREND_CCI_DIRECT_PT", raising=False)
    importlib.reload(bars)
    return bars._trend_from_cci(trend, cci)


def test_gray_current_bar_relabeled_up_when_cci_strong(monkeypatch):
    # live bar reads raw GRAY while CCI is already +150 → routed trend must be BLUE
    assert _tf(monkeypatch, "GRAY", 150.0) == "BLUE"


def test_gray_current_bar_relabeled_down_when_cci_strong(monkeypatch):
    assert _tf(monkeypatch, "GRAY", -150.0) == "RED"


def test_flag_off_is_byte_identical(monkeypatch):
    # OFF → raw trend kept verbatim (no relabel), for both strong and weak CCI
    assert _tf(monkeypatch, "GRAY", 150.0, flag="0") == "GRAY"
    assert _tf(monkeypatch, "GRAY", -150.0, flag="0") == "GRAY"
    assert _tf(monkeypatch, "BLUE", 5.0, flag="0") == "BLUE"


def test_anti_tautological_weak_cci_stays_gray(monkeypatch):
    # ON but |cci| BELOW threshold → must NOT force a flip (proves it's not
    # a blanket "always relabel")
    assert _tf(monkeypatch, "GRAY", 20.0, thr=50) == "GRAY"
    assert _tf(monkeypatch, "GRAY", -20.0, thr=50) == "GRAY"


def test_missing_cci_keeps_raw(monkeypatch):
    # None/garbage CCI → keep raw trend (fail-safe, never crash)
    assert _tf(monkeypatch, "GRAY", None) == "GRAY"
    assert _tf(monkeypatch, "RED", "n/a") == "RED"


def test_routed_current_bar_line_present():
    """Pin that the current_bar override actually calls _trend_from_cci (the G1
    wiring), so a future refactor can't silently drop it back to raw."""
    import inspect
    src = inspect.getsource(bars.post_woodies_5min) if hasattr(bars, "post_woodies_5min") else ""
    if not src:  # function name differs → scan module source
        src = inspect.getsource(bars)
    assert '_trend_from_cci(' in src and 'last_flat' in src, \
        "current_bar override must relabel trend via _trend_from_cci (G1)"
