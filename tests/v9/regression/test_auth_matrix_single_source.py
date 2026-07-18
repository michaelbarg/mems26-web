"""Ruling 2026-07-19 (A5): daytype_playbook is the SINGLE pattern×day-type authority.

S2_AUTH_MATRIX_SINGLE_SOURCE_V1 retires the auth_matrix gate inside
compute_v2_sizing. This must be ZERO-behaviour-change:

  * For the 4 families that MISSED the matrix on a key mismatch
    (Initiative/Flag/HnS/Double_BT) — flag OFF and ON give the SAME sizing
    output, because the matrix never resolved for them (they "used max" either
    way). This is the core proof: retiring a gate that never fired is a no-op.

  * REACTIVE is the one family the matrix DID resolve. On Nontrend the matrix
    said SKIP → OFF returns None. With the flag ON the sizing no longer returns
    None — but the daytype_playbook independently marks REACTIVE×Nontrend=SKIP,
    so the SYSTEM still blocks it. We pin that playbook cell so the safety net
    is proven to exist.
"""
import pytest

from backend.v9.config_loader import load_stop_anchors, load_auth_matrix


def _size(pattern_key, direction, day_type, retire, monkeypatch):
    if retire:
        monkeypatch.setenv("S2_AUTH_MATRIX_SINGLE_SOURCE_V1", "1")
    else:
        monkeypatch.delenv("S2_AUTH_MATRIX_SINGLE_SOURCE_V1", raising=False)
    monkeypatch.delenv("FIXED_CONTRACTS_4", raising=False)  # isolate the auth effect
    monkeypatch.delenv("FIXED_CONTRACTS_2", raising=False)
    monkeypatch.delenv("FIXED_CONTRACTS_3", raising=False)
    from backend.v9.systems.stop_anchors.sizing import compute_v2_sizing
    cfg = load_stop_anchors()
    auth = load_auth_matrix()
    entry = 7500.0
    stop = 7495.0 if direction == "LONG" else 7505.0
    return compute_v2_sizing(
        entry_price=entry, stop_price=stop, direction=direction,
        pattern_key=pattern_key, day_type=day_type, confidence_tier="medium",
        day_has_direction=False, trade_with_trend=None,
        value_area_full_traverse=None, cfg=cfg, auth_matrix=auth,
        reversal=False, cap_risk_points=None,
    )


@pytest.mark.parametrize("pk", ["OFA_Initiative", "Flag", "HnS", "Double_BT"])
@pytest.mark.parametrize("day", ["Normal", "Neutral_Center", "Trend_DD"])
def test_mismatched_families_retire_is_noop(pk, day, monkeypatch):
    """The 4 key-mismatched families: OFF and ON give the SAME result → retiring
    the never-resolving gate changes nothing for them."""
    off = _size(pk, "LONG", day, retire=False, monkeypatch=monkeypatch)
    on = _size(pk, "LONG", day, retire=True, monkeypatch=monkeypatch)
    # both None or both not-None, and same contract count when not-None
    assert (off is None) == (on is None), f"{pk}×{day}: retire changed fire/no-fire"
    if off is not None and on is not None:
        assert off.contracts == on.contracts, f"{pk}×{day}: retire changed size"


def test_reactive_nontrend_relies_on_playbook_after_retire(monkeypatch):
    """REACTIVE is the family the matrix DID resolve. On Nontrend, OFF → SKIP
    (None); ON → not-None. The system safety net is the playbook — pin that it
    marks REACTIVE×Nontrend=SKIP so the fire is still blocked at the gateway."""
    off = _size("Reactive", "LONG", "Nontrend", retire=False, monkeypatch=monkeypatch)
    on = _size("Reactive", "LONG", "Nontrend", retire=True, monkeypatch=monkeypatch)
    assert off is None, "sanity: OFF must SKIP Reactive×Nontrend via auth"
    assert on is not None, "ON retires auth → sizing no longer SKIPs here"
    # the safety net that makes this system-level zero-change:
    import yaml
    pb = yaml.safe_load(open("config/daytype_playbook.yaml"))["patterns"]
    assert pb["REACTIVE"]["cells"]["Nontrend"] == "SKIP", \
        "playbook must still block REACTIVE×Nontrend (the retire's safety net)"


def test_flag_default_off_preserves_old_behaviour():
    import inspect
    import backend.v9.systems.stop_anchors.sizing as s
    src = inspect.getsource(s)
    assert 'S2_AUTH_MATRIX_SINGLE_SOURCE_V1", "0"' in src, "flag must default OFF"
