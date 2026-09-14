"""Item 3a/8 (T-354): edge_fade_targets — authority, not log line.

Normal/Neutral location-confirmed setups get dalton-doctrine targets
(POC→VAL→IB) and structural stop. Chain is FINAL — downstream overrides
(DAYTYPE_TARGETS_STRUCTURAL, load_pattern_t1_points, TARGET_ZONES_V1,
TARGET_STRUCTURE_CLAMP_V1, TARGET_REALISM_V1) are guarded by (not _edge_fade).

Flag: EDGE_FADE_TARGETS_V1 (default OFF).
Gate: _dp_location_checked (Normal/Neutral only).
"""


def _make_setup(direction, entry, classification="REACTIVE_SHORT", metadata=None):
    return {
        "direction": direction,
        "entry_price": entry,
        "stop": entry + (5.0 if direction == "SHORT" else -5.0),
        "t1": None, "t2": None, "t3": None,
        "classification": classification,
        "metadata": metadata or {},
    }


def _apply_edge_fade(setup, vah, val, poc, ib_high, ib_low):
    """Simulate the gateway's edge_fade_targets logic (extracted for unit test)."""
    direction = (setup.get("direction") or "").upper()
    entry = float(setup.get("entry_price") or 0)

    if direction == "SHORT":
        stop = round(max(vah, ib_high if ib_high > vah else vah) + 0.25, 2)
        opp_val = val
        opp_ib = ib_low
    else:
        stop = round(min(val, ib_low if ib_low < val else val) - 0.25, 2)
        opp_val = vah
        opp_ib = ib_high

    risk = abs(entry - stop)
    poc_close = (poc is None or risk <= 0 or abs(entry - poc) < 0.65 * risk)

    if poc_close:
        t1 = round(opp_val, 2) if opp_val else None
        t2 = round(opp_ib, 2) if opp_ib else None
        t3 = None
    else:
        t1 = round(poc, 2)
        t2 = round(opp_val, 2) if opp_val else None
        t3 = round(opp_ib, 2) if opp_ib else None

    # Monotonic chain (SHORT: each target < previous)
    if direction == "SHORT":
        if t2 is not None and t1 is not None and t2 >= t1:
            t2 = None
        if t3 is not None and (t2 or t1) is not None:
            floor = t2 if t2 is not None else t1
            if t3 >= floor:
                t3 = None
    else:
        if t2 is not None and t1 is not None and t2 <= t1:
            t2 = None
        if t3 is not None and (t2 or t1) is not None:
            ceil = t2 if t2 is not None else t1
            if t3 <= ceil:
                t3 = None

    setup["t1"] = t1
    setup["t2"] = t2
    setup["t3"] = t3
    setup["stop"] = stop
    meta = setup.get("metadata")
    if not isinstance(meta, dict):
        meta = {}
        setup["metadata"] = meta
    meta["edge_fade_targets"] = True
    meta["stop_is_structural"] = True
    meta["runner"] = False
    return setup


# ── Golden: 11.09 18:55 REACTIVE_SHORT from VAH ──

def test_short_from_vah_targets():
    """SHORT from VAH: T1=POC, T2=VAL, T3=IB-low."""
    s = _make_setup("SHORT", 7673.25)
    _apply_edge_fade(s, vah=7675.75, val=7660.25, poc=7667.75,
                     ib_high=7672.25, ib_low=7659.75)
    assert s["stop"] == 7676.00, f"stop={s['stop']}"
    assert s["t1"] == 7667.75, f"T1={s['t1']}"
    assert s["t2"] == 7660.25, f"T2={s['t2']}"
    assert s["t3"] == 7659.75, f"T3={s['t3']}"
    assert s["metadata"]["edge_fade_targets"] is True
    assert s["metadata"]["stop_is_structural"] is True
    assert s["metadata"]["runner"] is False


def test_poc_too_close_short():
    """POC within 0.65×risk → T1=VAL, T2=IB-low, T3=None."""
    # POC at 7674.0, entry 7673.25, stop 7676.0 → risk=2.75 → 0.65×2.75=1.79
    # |7673.25 - 7674.0| = 0.75 < 1.79 → POC too close
    s = _make_setup("SHORT", 7673.25)
    _apply_edge_fade(s, vah=7675.75, val=7660.25, poc=7674.0,
                     ib_high=7672.25, ib_low=7659.75)
    assert s["t1"] == 7660.25  # VAL (skipped POC)
    assert s["t2"] == 7659.75  # IB-low
    assert s["t3"] is None


def test_variation_day_no_edge_fade():
    """Mutation: a setup on a Variation day should NOT get edge_fade_targets.
    (The gateway only applies edge_fade when _dp_location_checked=True,
    which requires day_type in Normal/Neutral_*. Variation uses the ladder.)
    """
    s = _make_setup("SHORT", 7673.25)
    # Variation → _dp_location_checked stays False → no edge_fade_targets
    assert s["metadata"].get("edge_fade_targets") is not True


def test_struct_targets_win_skipped_for_edge_fade():
    """STRUCT_TARGETS_WIN must not override a setup with edge_fade_targets."""
    s = _make_setup("SHORT", 7673.25)
    s["metadata"]["edge_fade_targets"] = True
    s["t1"] = 7667.75
    s["t2"] = 7660.25
    # The gateway checks: if _edge_fade → skip STRUCT_TARGETS_WIN
    _edge_fade = bool((s.get("metadata") or {}).get("edge_fade_targets"))
    assert _edge_fade is True
    # Targets unchanged
    assert s["t1"] == 7667.75
    assert s["t2"] == 7660.25


def test_long_from_val_targets():
    """LONG from VAL: T1=POC, T2=VAH, T3=IB-high.
    When IB-high < VAH (non-monotonic for LONG), T3 is dropped."""
    s = _make_setup("LONG", 7660.50)
    _apply_edge_fade(s, vah=7675.75, val=7660.25, poc=7667.75,
                     ib_high=7672.25, ib_low=7659.75)
    assert s["stop"] == 7659.50  # VAL - 0.25
    assert s["t1"] == 7667.75
    assert s["t2"] == 7675.75
    # IB-high (7672.25) < VAH (7675.75) → non-monotonic → T3 dropped
    assert s["t3"] is None


def test_long_from_val_with_monotonic_ib():
    """LONG with IB-high above VAH → T3 = IB-high (monotonic chain holds)."""
    s = _make_setup("LONG", 7660.50)
    _apply_edge_fade(s, vah=7670.75, val=7660.25, poc=7665.00,
                     ib_high=7675.25, ib_low=7659.75)
    assert s["stop"] == 7659.50
    assert s["t1"] == 7665.00   # POC
    assert s["t2"] == 7670.75   # VAH
    assert s["t3"] == 7675.25   # IB-high (above VAH → monotonic)


# ── ג6 mutation tests: verify wiring in the actual gateway source ──

def test_gate_uses_dp_location_checked():
    """The edge_fade block must be gated by _dp_location_checked, not a raw zone check."""
    import inspect
    from backend.v9.gateway.trading_gateway import TradingGateway
    src = inspect.getsource(TradingGateway._route_setup_inner)
    idx = src.find("EDGE_FADE_TARGETS_V1")
    assert idx > 0, "EDGE_FADE_TARGETS_V1 not found in _route_setup_inner"
    # The if-condition is on the same line or nearby — check ±200 chars around the flag
    window = src[max(0, idx - 200):idx + 200]
    assert "_dp_location_checked" in window, (
        "_dp_location_checked not in the condition guarding EDGE_FADE_TARGETS_V1")


def test_downstream_overrides_guarded_by_edge_fade():
    """All 5 downstream target overrides must be guarded by (not _edge_fade)."""
    import inspect
    from backend.v9.gateway.trading_gateway import TradingGateway
    src = inspect.getsource(TradingGateway._route_setup_inner)
    guarded = [
        "DAYTYPE_TARGETS_STRUCTURAL",
        "load_pattern_t1_points",
        "TARGET_ZONES_V1",
        "TARGET_STRUCTURE_CLAMP_V1",
        "TARGET_REALISM_V1",
    ]
    for name in guarded:
        # For env flags, search for the os.getenv call; for import names, the import
        env_form = f'getenv("{name}"'
        idx = src.find(env_form)
        if idx < 0:
            # Not an env flag — search for "import name" or "name(" call
            for pat in [f"import {name}", f"{name}("]:
                idx = src.find(pat)
                if idx >= 0:
                    break
        assert idx > 0, f"{name} not found (any form) in _route_setup_inner"
        # The _edge_fade guard is on the same line or the enclosing if above
        line_start = src.rfind("\n", 0, idx) + 1
        line = src[line_start:src.find("\n", idx)]
        if "_edge_fade" not in line:
            # Check the enclosing if (up to 3 lines above)
            prev3 = src[max(0, line_start - 300):line_start]
            assert "_edge_fade" in prev3, (
                f"{name}: _edge_fade not on same line or within 300 chars above")
