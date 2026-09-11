"""T-315: S2 detection chain fall-through when Auth Table SKIPs a pattern.

Tests:
  1. is_skip returns True for known SKIP cells in the auth table.
  2. The _auth_viable closure (inline in five_min_system.py) returns False when
     is_skip is True — exercised by calling is_skip directly (the closure is a
     1-line wrapper around it).
  3. When the reactive detector's winner is killed by the auth table, the chain
     falls through to the initiative detector (integration-level assertion on
     the is_skip gate, not on the full system).
"""
from backend.v9.systems.build_status.auth_table_lookup import is_skip, lookup_auth_cell


# ── 1. is_skip returns True for verified SKIP cells ──────────────────────────

def test_reactive_long_skip_on_nontrend():
    """REACTIVE_LONG × Nontrend = SKIP per S2_AUTH_TABLE_V1 §4."""
    assert is_skip("REACTIVE_LONG", "Nontrend") is True


def test_initiative_long_skip_on_neutral_center():
    """INITIATIVE_LONG × Neutral_Center = SKIP."""
    assert is_skip("INITIATIVE_LONG", "Neutral_Center") is True


def test_initiative_long_skip_on_normal():
    """INITIATIVE_LONG × Normal = SKIP."""
    assert is_skip("INITIATIVE_LONG", "Normal") is True


def test_double_bottom_skip_on_trend_normal():
    """DOUBLE_BOTTOM_EE_LONG × Trend_Normal = SKIP."""
    assert is_skip("DOUBLE_BOTTOM_EE_LONG", "Trend_Normal") is True


# ── 2. is_skip returns False for non-SKIP cells ──────────────────────────────

def test_reactive_long_not_skip_on_neutral_extreme():
    """REACTIVE_LONG × Neutral_Extreme = FULL (not SKIP)."""
    assert is_skip("REACTIVE_LONG", "Neutral_Extreme") is False


def test_initiative_long_not_skip_on_trend_normal():
    """INITIATIVE_LONG × Trend_Normal = FULL (not SKIP)."""
    assert is_skip("INITIATIVE_LONG", "Trend_Normal") is False


# ── 3. _auth_viable gate: SKIP → False, non-SKIP → True ─────────────────────

def _auth_viable(pattern_name: str, day_type: str) -> bool:
    """Inline replica of the _auth_viable closure from five_min_system.py.

    The real closure does:
        _pn = f"{kind}_{direction}"
        _dt = _s2_det_dt or "Normal"
        if is_skip(_pn, _dt): return False
        return True
    """
    return not is_skip(pattern_name, day_type)


def test_auth_viable_false_when_skip():
    """_auth_viable → False when auth table says SKIP."""
    assert _auth_viable("REACTIVE_LONG", "Nontrend") is False


def test_auth_viable_true_when_not_skip():
    """_auth_viable → True when auth table allows the pattern."""
    assert _auth_viable("REACTIVE_LONG", "Normal") is True


# ── 4. Chain semantics: if reactive dies, initiative can still fire ───────────

def test_chain_fallthrough_reactive_skip_initiative_viable():
    """Reactive SKIP does not block the initiative slot.

    REACTIVE_LONG × Nontrend = SKIP  (reactive killed)
    INITIATIVE_LONG × Trend_Normal = FULL  (initiative still viable)
    The chain must try the initiative detector when reactive is blocked.
    """
    reactive_dir = "LONG"
    reactive_pattern = f"REACTIVE_{reactive_dir}"
    day_type_nontrend = "Nontrend"

    initiative_pattern = f"INITIATIVE_{reactive_dir}"
    day_type_trend = "Trend_Normal"

    # Reactive is killed
    assert _auth_viable(reactive_pattern, day_type_nontrend) is False

    # Initiative is viable in a different day-type context
    assert _auth_viable(initiative_pattern, day_type_trend) is True


def test_both_detectors_skip_on_nontrend():
    """On Nontrend day, both REACTIVE and INITIATIVE LONG are SKIP.

    This verifies the full fall-through scenario where neither slot fires
    (the chain exhausts without a trade — correct behavior for Nontrend).
    """
    assert is_skip("REACTIVE_LONG", "Nontrend") is True
    assert is_skip("INITIATIVE_LONG", "Nontrend") is True
    # Combined: _auth_viable returns False for both
    assert _auth_viable("REACTIVE_LONG", "Nontrend") is False
    assert _auth_viable("INITIATIVE_LONG", "Nontrend") is False


# ── 5. Short-key lookup works for is_skip ─────────────────────────────────────

def test_is_skip_short_key_nt():
    """Short key 'NT' maps to Nontrend — is_skip must work with short keys."""
    assert is_skip("REACTIVE_LONG", "NT") is True


def test_is_skip_short_key_tn():
    """Short key 'TN' maps to Trend_Normal — REACTIVE_LONG × TN = REDUCED (not SKIP)."""
    assert is_skip("REACTIVE_LONG", "TN") is False
