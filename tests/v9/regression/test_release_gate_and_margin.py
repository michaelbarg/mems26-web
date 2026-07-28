"""Two live gates that can only reduce risk (Michael 2026-07-28).

He asked for the LIVE system to maximise location and entry today.

RELEASE_ENTRY_GATE_V1 — direction is right roughly three times in four, but the
entry is too early, so the stop sits inside the noise and the trade is gone
before the move it predicted arrives. The gate holds a signal until price leaves
the zone. Modelled on 07-27, a session whose bar timestamps are verified clean.

MARGIN_AWARE_SIZING_V1 — the Account Monitor showed the system asking for four
contracts ($1,104.84) against $97.68 available. Sierra's log that morning holds
six "Insufficient Account Value (NLV) for margin" rejections.
"""
import json

import pytest

from backend.v9.systems.release_gate import Bar, bars_from_rows, check_release
import backend.v9.services.margin_sizing as ms


@pytest.fixture(autouse=True)
def _defaults(monkeypatch):
    monkeypatch.setenv("RELEASE_MIN_HIGHER_LOWS", "2")
    monkeypatch.setenv("RELEASE_VOL_WINDOW", "3")
    monkeypatch.setenv("RELEASE_VOL_RATIO", "0.75")
    monkeypatch.setenv("RELEASE_ZONE_POINTS", "8")


# ── the real 07-27 session ───────────────────────────────────────────────────
# 19:15 low 7416.25 (vol 8235) → rotation on drying volume → 19:50 release.
_0727 = [
    Bar(7425.50, 7416.25, 7420.25, 8235),   # 19:15  the extreme
    Bar(7425.50, 7418.75, 7421.75, 6439),   # 19:20  higher low
    Bar(7424.50, 7419.50, 7420.00, 4552),   # 19:25  higher low, volume drying
    Bar(7430.00, 7419.50, 7429.50, 7148),   # 19:30
    Bar(7430.75, 7423.25, 7424.75, 4666),   # 19:35  higher low
    Bar(7426.75, 7422.50, 7426.00, 4666),   # 19:40
    Bar(7429.25, 7423.50, 7425.25, 4489),   # 19:45  driest
    Bar(7433.50, 7424.50, 7433.00, 6239),   # 19:50  THE RELEASE
]


def test_the_real_0727_release_is_detected():
    v = check_release(_0727, "LONG")
    assert v.released, v.reason
    assert v.structural_stop == 7415.25          # below the 7416.25 extreme
    assert v.higher_lows >= 2


def test_entering_inside_the_zone_is_held():
    """19:24 — where the system actually entered. Nothing has released yet."""
    v = check_release(_0727[:3], "LONG")
    assert not v.released


def test_release_stop_is_wider_than_the_pattern_stop():
    """The point of waiting: the structural stop clears the real extreme.
    ZLR risked 9pt and died; GB100 risked 17.5pt on the same move and made
    +22.75. Entering on the release produces the survivable stop by itself."""
    v = check_release(_0727, "LONG")
    entry = _0727[-1].close
    assert entry - v.structural_stop > 15


def test_no_release_without_volume_confirmation():
    bars = list(_0727[:-1]) + [Bar(7433.50, 7424.50, 7433.00, 900)]
    v = check_release(bars, "LONG")
    assert not v.released and "without volume" in v.reason


def test_no_release_while_still_active_in_the_zone():
    """Volume never contracts → the market is still trading the level."""
    bars = [Bar(b.high, b.low, b.close, 9000) for b in _0727]
    v = check_release(bars, "LONG")
    assert not v.released and "still active" in v.reason


def test_no_release_without_a_structural_turn():
    """Lower lows all the way — a falling knife must never pass."""
    bars = [Bar(7430 - i, 7420 - i, 7425 - i, 5000 - i * 100) for i in range(8)]
    v = check_release(bars, "LONG")
    assert not v.released


def test_short_side_is_mirrored():
    """The 07-27 shape reflected: a HIGH extreme, then lower highs on drying
    volume, then a close BELOW the zone on returning volume."""
    short = [
        Bar(7516.25, 7507.00, 7512.00, 8235),   # the extreme high
        Bar(7513.50, 7506.00, 7510.50, 6439),   # lower high
        Bar(7512.50, 7505.00, 7511.00, 4552),   # lower high, drying
        Bar(7512.00, 7502.00, 7503.00, 7148),
        Bar(7508.75, 7501.00, 7507.00, 4666),   # lower high
        Bar(7508.00, 7503.00, 7505.00, 4666),
        Bar(7507.50, 7502.00, 7506.00, 4489),   # driest
        Bar(7506.00, 7498.00, 7499.00, 6239),   # closes below 7516.25-8 = 7508.25
    ]
    v = check_release(short, "SHORT")
    assert v.released, v.reason
    assert v.structural_stop == 7517.25          # above the 7516.25 extreme


def test_insufficient_data_holds_rather_than_passes():
    """Rule 1: unknown is not permission. Failing open would recreate the early
    entry this gate exists to prevent."""
    assert not check_release([], "LONG").released
    assert not check_release(_0727[:2], "LONG").released


def test_bars_from_rows_skips_unusable():
    rows = [{"high": 1, "low": 0.5, "close": 0.8, "volume": 10},
            {"high": None, "low": 1, "close": 1, "volume": 1},
            {"nope": 1}]
    assert len(bars_from_rows(rows)) == 1


# ── margin-aware sizing ──────────────────────────────────────────────────────

def _state(tmp_path, monkeypatch, **kw):
    d = {"acct_ok": 1, "position_qty": 6, "acct_margin_req": 1657.26,
         "acct_available_funds": 97.68}
    d.update(kw)
    p = tmp_path / "sierra_state.json"
    p.write_text(json.dumps(d))
    monkeypatch.setattr(ms, "STATE", p)
    monkeypatch.setenv("MARGIN_AWARE_SIZING_V1", "1")
    monkeypatch.setenv("MARGIN_BUFFER_USD", "50")
    return p


def test_the_real_situation_blocks_the_four_contract_fire(tmp_path, monkeypatch):
    """$97.68 available, $276.21 per contract → 0. Today's actual numbers."""
    _state(tmp_path, monkeypatch)
    allowed, why = ms.cap_contracts(4)
    assert allowed == 0 and "no margin" in why


def test_reduces_rather_than_refusing_when_partially_covered(tmp_path, monkeypatch):
    """A smaller real trade beats a guaranteed rejection."""
    _state(tmp_path, monkeypatch, acct_available_funds=700.0)
    allowed, why = ms.cap_contracts(4)
    assert allowed == 2 and "reduced 4→2" in why


def test_never_increases_the_request(tmp_path, monkeypatch):
    _state(tmp_path, monkeypatch, acct_available_funds=50000.0)
    assert ms.cap_contracts(1)[0] == 1


def test_margin_per_contract_from_the_live_position(tmp_path, monkeypatch):
    _state(tmp_path, monkeypatch)
    st = json.loads((tmp_path / "sierra_state.json").read_text())
    assert round(ms.margin_per_contract(st), 2) == 276.21


def test_flat_account_falls_back_to_the_configured_margin(tmp_path, monkeypatch):
    _state(tmp_path, monkeypatch, position_qty=0, acct_margin_req=0)
    monkeypatch.setenv("MES_MARGIN_PER_CONTRACT", "276.21")
    st = json.loads((tmp_path / "sierra_state.json").read_text())
    assert ms.margin_per_contract(st) == 276.21


def test_missing_account_data_changes_nothing(tmp_path, monkeypatch):
    """acct_ok=0 → no guess, size untouched (Rule 1)."""
    _state(tmp_path, monkeypatch, acct_ok=0)
    allowed, why = ms.cap_contracts(4)
    assert allowed == 4 and "no guess" in why


def test_flag_off_is_inert(tmp_path, monkeypatch):
    _state(tmp_path, monkeypatch)
    monkeypatch.delenv("MARGIN_AWARE_SIZING_V1", raising=False)
    assert ms.cap_contracts(4)[0] == 4


def test_effective_contracts_applies_the_cap_on_every_path(tmp_path, monkeypatch):
    """The wrapper exists so no sizing branch can bypass the account limit."""
    import backend.v9.services.sierra_command as sc
    _state(tmp_path, monkeypatch)
    monkeypatch.setenv("FIXED_CONTRACTS_4", "1")
    assert sc._effective_contracts_raw({"contracts": 4}) == 4     # sizing says 4
    assert sc.effective_contracts({"contracts": 4}) == 0          # account says no


# ── never send a contract the DLL cannot bracket ─────────────────────────────

def test_bracket_slot_cap():
    """Michael 07-28: 'העסקה היא על 6 חוזים והסטופ והמימוש על חוזה 1'. The DLL
    attaches one bracket per contract and has four slots; a fifth contract would
    ride naked inside a position that looks protected."""
    assert ms.cap_to_bracketable(4)[0] == 4
    assert ms.cap_to_bracketable(7)[0] == 4
    assert "naked" in ms.cap_to_bracketable(7)[1]


def test_bracket_cap_is_unconditional(monkeypatch, tmp_path):
    """It must apply even with margin sizing OFF — an unprotected contract is a
    safety defect, not a sizing policy."""
    import backend.v9.services.sierra_command as sc
    monkeypatch.delenv("MARGIN_AWARE_SIZING_V1", raising=False)
    monkeypatch.setenv("FIXED_CONTRACTS_4", "0")
    assert sc.effective_contracts({"contracts": 7}) == 4
