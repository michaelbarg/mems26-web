"""EDGE_FADE_V1 — responsive edge-fade (DEV_PLAN 02.08 §P1)."""
from backend.v9.systems.edge_fade import evaluate_edge_fade, build_edge_fade_setup


def _b(o, h, l, c):
    return {"o": o, "h": h, "l": l, "c": c}


def _range_day():
    # 30pt range 7400-7430 established, then bars for probes
    return [_b(7415, 7430, 7412, 7418), _b(7418, 7422, 7405, 7408),
            _b(7408, 7414, 7400, 7412), _b(7412, 7420, 7410, 7417),
            _b(7417, 7424, 7414, 7420), _b(7420, 7426, 7417, 7421)]


def test_upper_edge_rejection_fires_short():
    bars = _range_day() + [_b(7421, 7429.5, 7418, 7419.5)]  # probe 7429.5 (zone), close low half + below zone
    t = evaluate_edge_fade(bars, "Normal")
    assert t is not None and t["direction"] == "SHORT" and t["type"] == "FADE_HIGH"
    s = build_edge_fade_setup(t)
    assert s["stop"] > s["entry_price"] > s["t1"] > s["t2"] or s["t2"] < s["t1"]  # short ladder


def test_lower_edge_rejection_fires_long():
    bars = _range_day() + [_b(7412, 7414, 7400.5, 7411)]   # probe 7400.5, close upper half + above zone
    t = evaluate_edge_fade(bars, "Neutral_Center")
    assert t is not None and t["direction"] == "LONG" and t["type"] == "FADE_LOW"


def test_no_fire_on_variation_day():
    bars = _range_day() + [_b(7421, 7429.5, 7418, 7419.5)]
    assert evaluate_edge_fade(bars, "Variation") is None
    assert evaluate_edge_fade(bars, None) is None


def test_no_fire_in_tight_coil():
    bars = [_b(7410, 7414, 7406, 7411)] * 7                # 8pt range < 20 min
    assert evaluate_edge_fade(bars, "Normal") is None


def test_no_fire_mid_range():
    bars = _range_day() + [_b(7415, 7418, 7411, 7413)]     # nowhere near an edge
    assert evaluate_edge_fade(bars, "Normal") is None


def test_one_per_side():
    bars = _range_day() + [_b(7421, 7429.5, 7418, 7419.5)]
    assert evaluate_edge_fade(bars, "Normal", {"FADE_HIGH"}) is None


def test_probe_that_closes_strong_does_not_fade():
    # bar reaches the high zone but CLOSES at its top = acceptance, not rejection
    bars = _range_day() + [_b(7421, 7429.5, 7420, 7429)]
    assert evaluate_edge_fade(bars, "Normal") is None


def test_stop_capped():
    # huge probe bar → stop capped at 15pt from entry
    bars = _range_day() + [_b(7421, 7429.5, 7402, 7404)]
    t = evaluate_edge_fade(bars, "Normal")
    if t:
        assert abs(t["stop"] - t["entry"]) <= 15.0 + 1e-6


def test_release_entry_setup_uses_structural_stop_capped():
    from backend.v9.systems.edge_fade import build_release_entry_setup
    s = build_release_entry_setup("LONG", 7433.0, 7415.25, 7465.0, 7410.0)
    assert s["stop"] == 7418.0  # 7415.25 is 17.75pt away -> capped at 15
    assert s["t1"] == 7448.0    # 1R of capped risk
    assert s["t2"] == 7465.0    # day mid beyond t1 kept


def test_release_entry_setup_mid_inside_t1_degrades_to_2r():
    from backend.v9.systems.edge_fade import build_release_entry_setup
    s = build_release_entry_setup("SHORT", 7500.0, 7508.0, 7498.0, 7510.0)
    # mid 7498 is inside T1 (7492) -> degrade to 2R = 7484
    assert s["t2"] == 7484.0
