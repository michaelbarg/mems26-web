"""Delta/CVD features (DEV_PLAN 02.08 §P2 phase-1)."""
from backend.v9.systems.delta_features import (
    cvd_directionality, delta_confirms_extension,
    delta_divergence_at_extreme, extract_features)


def _p(t, d, cum, p):
    return {"t": t, "d": d, "cum": cum, "p": p}


def _oneway():
    return [_p(i, 100, 100 * (i + 1), 7400 + i) for i in range(20)]


def _churn():
    return [_p(i, 100 if i % 2 == 0 else -100, (100 if i % 2 == 0 else 0), 7400)
            for i in range(20)]


def test_directionality_oneway_high():
    assert cvd_directionality(_oneway()) >= 0.95


def test_directionality_churn_low():
    assert cvd_directionality(_churn()) <= 0.1


def test_extension_confirmed_when_cvd_at_extreme():
    assert delta_confirms_extension(_oneway(), "UP") is True


def test_extension_denied_when_cvd_faded():
    pts = _oneway()
    # price keeps rising but cum collapses back to mid-range
    for i in range(15, 20):
        pts[i]["cum"] = 900 - (i - 15) * 150
    assert delta_confirms_extension(pts, "UP") is False


def test_divergence_bearish_price_high_without_cum_high():
    pts = _oneway()
    for i in range(15, 20):                 # price new highs, cum stalls low
        pts[i]["p"] = 7430 + i
        pts[i]["cum"] = 500
    assert delta_divergence_at_extreme(pts) == "BEARISH"


def test_insufficient_data_honest_none():
    assert cvd_directionality([]) is None
    assert delta_confirms_extension([], "UP") is None
    assert delta_divergence_at_extreme([_p(1, 1, 1, 1)]) is None


def test_extract_features_passthrough():
    f = extract_features({"points": _oneway(), "divergence": "NONE",
                          "trend": "UP", "session_delta": 2000})
    assert f["dll_trend"] == "UP" and f["cvd_directionality"] is not None
