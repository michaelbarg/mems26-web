"""STOP_TABLE_V1 regression — per-pattern × day_type stop cap table.

Michael's gap (audit): TARGETS are per-pattern×day_type (targets.yaml
pattern_t1_points, e.g. REACTIVE_SHORT/Variation = 9.0pt), but STOPS were a
generic CONT/REV ATR-band resolver (STOP_RESOLVER_V1) with NO day_type input.
STOP_TABLE_V1 lets STOP_RESOLVER_V1 consult config/stop_anchors.yaml
`pattern_stop` so the ATR band cap becomes pattern+day_type aware.

Proves the four required properties of the flag:
  (a) flag OFF  → resolver behavior unchanged (byte-identical decision).
  (b) flag ON   → a pattern+day_type present in the table uses its specific
                  cap/anchor.
  (c) flag ON   → a pattern+day_type NOT in the table falls back to today's
                  generic resolver (no crash, no widening).
  (d) tighten-or-equal only → the table can NEVER widen risk beyond the global
                  ATR cap.

The gateway's stop-table decision lives in small pure module-level helpers so
it is unit-testable without the DB / a full TradingGateway instance:
  _load_pattern_stop_table / _stop_table_lookup / _stop_table_effective_cap /
  _stop_table_decide_cap / _stop_table_should_apply.
"""

import pytest

from backend.v9.gateway.trading_gateway import (
    _load_pattern_stop_table,
    _reset_pattern_stop_cache,
    _stop_table_lookup,
    _stop_table_effective_cap,
    _stop_table_decide_cap,
    _stop_table_should_apply,
)


@pytest.fixture(autouse=True)
def _fresh_cache():
    """Read the pattern_stop table fresh from config/stop_anchors.yaml."""
    _reset_pattern_stop_cache()
    yield
    _reset_pattern_stop_cache()


# ── The real YAML table loads (config wiring) ────────────────────────────────

def test_pattern_stop_table_loads_from_yaml():
    """config/stop_anchors.yaml `pattern_stop` block loads with the expected
    shape (mirrors targets.yaml pattern_t1_points: PATTERN → day_type → spec)."""
    tbl = _load_pattern_stop_table()
    assert isinstance(tbl, dict) and tbl, "pattern_stop must load and be non-empty"
    # A known placeholder entry exists and carries the documented keys.
    entry = _stop_table_lookup(tbl, "REACTIVE_SHORT", "Variation")
    assert entry is not None, "REACTIVE_SHORT/Variation must be present"
    assert entry.get("max_risk_pts") == 15
    assert "band_cap_atr" in entry
    assert entry.get("anchor_type") == "support_zone"


def test_placeholder_caps_mirror_anchor_caps_conservative():
    """Placeholders are conservative: max_risk_pts never exceeds the 25pt global
    cap and mirror the per-pattern anchor caps (not invented aggressive values)."""
    tbl = _load_pattern_stop_table()
    for pattern, dt_map in tbl.items():
        for dt, spec in dt_map.items():
            mr = spec.get("max_risk_pts")
            assert mr is None or (0 < mr <= 25), (
                f"{pattern}/{dt} max_risk_pts={mr} must be within the 25pt global cap"
            )


# ── (a) flag OFF → resolver behavior unchanged ───────────────────────────────

def test_a_flag_off_effective_cap_is_generic_even_when_present():
    """Disabled → decide returns (generic_cap, None) even for a pattern that IS
    in the table. The table has zero effect when the flag is OFF."""
    tbl = _load_pattern_stop_table()
    cap, entry = _stop_table_decide_cap(
        enabled=False, table=tbl,
        classification="REACTIVE_SHORT", day_type="Variation",
        generic_cap_pts=25.0, atr_5m=20.0,
    )
    assert cap == 25.0
    assert entry is None


def test_a_flag_off_apply_decision_is_byte_identical():
    """With the effective cap == the generic cap (flag OFF / no entry), the
    apply decision is the ORIGINAL condition `in_band and not rejected` —
    independent of risk_points. This holds even when tick-grid snapping in
    resolve_stop pushes the post-snap risk a fraction ABOVE the cap, which the
    pre-STOP_TABLE code always applied. That case must still apply."""
    # in-band + snapped risk slightly over the cap → today's code applied it.
    assert _stop_table_should_apply(
        in_band=True, rejected=False,
        risk_points=8.475, effective_cap_pts=8.4, generic_cap_pts=8.4,
    ) is True
    # not in-band / rejected → today's code did nothing.
    assert _stop_table_should_apply(
        in_band=False, rejected=False,
        risk_points=5.0, effective_cap_pts=8.4, generic_cap_pts=8.4,
    ) is False
    assert _stop_table_should_apply(
        in_band=True, rejected=True,
        risk_points=5.0, effective_cap_pts=8.4, generic_cap_pts=8.4,
    ) is False


# ── (b) flag ON + present → uses its specific cap / anchor ────────────────────

def test_b_flag_on_present_uses_specific_cap_and_anchor():
    """Enabled + pattern×day_type present → the table's max_risk_pts tightens the
    generic cap and the entry (with its anchor_type) is returned."""
    tbl = _load_pattern_stop_table()
    cap, entry = _stop_table_decide_cap(
        enabled=True, table=tbl,
        classification="REACTIVE_SHORT", day_type="Variation",
        generic_cap_pts=25.0, atr_5m=20.0,   # generic REV cap 25 (1.5*20 hits 25 hard-cap)
    )
    assert entry is not None
    assert entry["anchor_type"] == "support_zone"
    assert cap == 15.0, "REACTIVE_SHORT/Variation max_risk_pts=15 must tighten 25→15"


def test_b_flag_on_present_declines_rung_over_pattern_cap():
    """A resolver rung whose risk exceeds the tightened pattern cap is DECLINED
    (keep original); a rung within the cap is APPLIED."""
    tbl = _load_pattern_stop_table()
    cap, _ = _stop_table_decide_cap(
        enabled=True, table=tbl,
        classification="INITIATIVE_LONG", day_type="Variation",
        generic_cap_pts=25.0, atr_5m=20.0,
    )
    assert cap == 12.0, "INITIATIVE_LONG/Variation max_risk_pts=12 tightens 25→12"
    # rung risk 10pt ≤ 12pt → apply
    assert _stop_table_should_apply(
        in_band=True, rejected=False,
        risk_points=10.0, effective_cap_pts=cap, generic_cap_pts=25.0,
    ) is True
    # rung risk 18pt > 12pt (would pass generic 25 but not pattern 12) → decline
    assert _stop_table_should_apply(
        in_band=True, rejected=False,
        risk_points=18.0, effective_cap_pts=cap, generic_cap_pts=25.0,
    ) is False


def test_b_band_cap_atr_can_tighten_below_max_risk_pts():
    """band_cap_atr tightens as a multiple of ATR — the tighter of it vs the
    generic band and vs max_risk_pts wins."""
    # Synthetic entry: band_cap_atr 1.0 × ATR 10 = 10pt, tighter than both
    # the generic cap (12) and max_risk_pts (15).
    cap = _stop_table_effective_cap(
        generic_cap_pts=12.0, atr_5m=10.0,
        entry={"max_risk_pts": 15, "band_cap_atr": 1.0},
    )
    assert cap == 10.0


# ── (c) flag ON + absent → generic fallback, no crash, no widening ───────────

def test_c_flag_on_absent_falls_back_to_generic():
    """Enabled but pattern×day_type NOT in the table → generic cap, no entry,
    no crash, no widening."""
    tbl = _load_pattern_stop_table()
    cap, entry = _stop_table_decide_cap(
        enabled=True, table=tbl,
        classification="VEGAS", day_type="Trend_Normal",   # not in the table
        generic_cap_pts=25.0, atr_5m=20.0,
    )
    assert cap == 25.0
    assert entry is None


@pytest.mark.parametrize("classification,day_type", [
    ("REACTIVE_SHORT", "Trend_Normal"),   # pattern present, day_type absent
    ("GHOST", "Variation"),               # pattern absent
    ("", "Variation"),                    # empty classification
    ("REACTIVE_SHORT", None),             # missing day_type
    (None, None),                         # both missing
])
def test_c_missing_entries_never_crash_and_stay_generic(classification, day_type):
    """Any absent / partial key → generic cap, entry None, no exception."""
    tbl = _load_pattern_stop_table()
    cap, entry = _stop_table_decide_cap(
        enabled=True, table=tbl,
        classification=classification, day_type=day_type,
        generic_cap_pts=25.0, atr_5m=20.0,
    )
    assert cap == 25.0
    assert entry is None


# ── (d) tighten-or-equal only — NEVER widen beyond the global cap ─────────────

@pytest.mark.parametrize("entry", [
    None,
    {},
    {"max_risk_pts": 999},                       # absurd wide → clamped to generic
    {"band_cap_atr": 99},                        # absurd wide → clamped to generic
    {"max_risk_pts": 999, "band_cap_atr": 99},   # both absurd → clamped
    {"max_risk_pts": 0},                         # invalid (ignored)
    {"max_risk_pts": -5},                        # invalid (ignored)
    {"band_cap_atr": 0},                         # invalid (ignored)
    {"anchor_type": "support_zone"},             # advisory only, no cap effect
    {"max_risk_pts": 15, "band_cap_atr": 1.5},   # a real (tightening) entry
])
@pytest.mark.parametrize("generic_cap,atr", [(25.0, 20.0), (8.4, 7.0), (12.0, 10.0)])
def test_d_effective_cap_never_exceeds_generic(entry, generic_cap, atr):
    """The effective cap is min(generic, max_risk_pts, band_cap_atr×atr) — it can
    only tighten or equal the generic cap, NEVER widen beyond it (or the global
    ATR cap the generic cap already respects)."""
    cap = _stop_table_effective_cap(generic_cap, atr, entry)
    assert cap <= generic_cap + 1e-9, (
        f"effective cap {cap} must never exceed generic cap {generic_cap} (entry={entry})"
    )


def test_d_decide_cap_never_widens_for_any_real_table_entry():
    """Across every entry actually present in the YAML table, the ON effective
    cap is ≤ the generic cap it was given (never widened)."""
    tbl = _load_pattern_stop_table()
    generic = 25.0
    for pattern, dt_map in tbl.items():
        for dt in dt_map:
            cap, entry = _stop_table_decide_cap(
                enabled=True, table=tbl,
                classification=pattern, day_type=dt,
                generic_cap_pts=generic, atr_5m=20.0,
            )
            assert entry is not None
            assert cap <= generic + 1e-9, f"{pattern}/{dt} widened {generic}→{cap}"


def test_d_apply_is_monotone_tighten_only():
    """A tighter effective cap can only turn an APPLY into a KEEP-ORIGINAL —
    never the reverse. So enabling the table can never apply a stop the generic
    resolver would have declined."""
    # Generic accepts a 10pt rung (10 ≤ 25).
    generic_applies = _stop_table_should_apply(
        in_band=True, rejected=False,
        risk_points=10.0, effective_cap_pts=25.0, generic_cap_pts=25.0,
    )
    # Tightened to 8pt: the SAME 10pt rung is now declined.
    tightened_declines = _stop_table_should_apply(
        in_band=True, rejected=False,
        risk_points=10.0, effective_cap_pts=8.0, generic_cap_pts=25.0,
    )
    assert generic_applies is True
    assert tightened_declines is False
    # There is no (in_band, risk) pair where tightening turns a decline into an
    # apply: for risk within a tighter cap it is also within the wider one.
    for risk in (1.0, 5.0, 8.0, 12.0, 25.0):
        wide = _stop_table_should_apply(
            in_band=True, rejected=False,
            risk_points=risk, effective_cap_pts=25.0, generic_cap_pts=25.0)
        tight = _stop_table_should_apply(
            in_band=True, rejected=False,
            risk_points=risk, effective_cap_pts=8.0, generic_cap_pts=25.0)
        assert not (tight and not wide), f"tighten created an apply at risk={risk}"


# ── flag env divergence (mirrors the gateway's `os.getenv` gate) ─────────────

def test_env_flag_gates_on_off_divergence(monkeypatch):
    """OFF vs ON must diverge for a present pattern, and be identical (generic)
    for an absent one — matching how the gateway reads STOP_TABLE_V1."""
    import os as _os
    tbl = _load_pattern_stop_table()

    def decide(present: bool):
        enabled = _os.getenv("STOP_TABLE_V1", "0").lower() in ("1", "true", "yes")
        cls = "REACTIVE_SHORT" if present else "VEGAS"
        dt = "Variation" if present else "Trend_Normal"
        return _stop_table_decide_cap(
            enabled=enabled, table=tbl if enabled else {},
            classification=cls, day_type=dt,
            generic_cap_pts=25.0, atr_5m=20.0,
        )

    monkeypatch.setenv("STOP_TABLE_V1", "0")
    assert decide(present=True) == (25.0, None)      # OFF → generic

    monkeypatch.setenv("STOP_TABLE_V1", "1")
    cap_on, entry_on = decide(present=True)
    assert cap_on == 15.0 and entry_on is not None   # ON present → tightened
    assert decide(present=False) == (25.0, None)     # ON absent → generic
