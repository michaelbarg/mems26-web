"""PLACE_BRACKET v3 — a real stop (+ optional target) on an EXISTING position.

Michael 2026-07-28: "המערכת כן תוכל לנהל עסקה שאני מבצע ולהוסיף לה סטופ ונקודות
מימוש" — he was right and the 8-day-old claim that ACSIL cannot do this was wrong.

Two prior failures these tests exist to prevent:
  • v2 called sc.SubmitOrder, which has zero public definitions in ACSIL — it
    would not have compiled, and no test would have caught it because no test
    existed. The DLL is source-checked here.
  • v2 validated the order side against the POSITION sign but never against the
    MARKET. A sell stop above the market executes instantly: a forced exit
    wearing the costume of protection.
"""
import json

import pytest

import backend.v9.services.sierra_command as sc_cmd
import backend.v9.services.sierra_position_reconciler as rec


# ── command writer ───────────────────────────────────────────────────────────

@pytest.fixture
def _captured(monkeypatch):
    box = {}
    monkeypatch.setattr(sc_cmd, "_write_command",
                        lambda payload: box.setdefault("p", payload) or {"ok": True})
    return box


def test_long_bracket_payload(_captured):
    sc_cmd.write_place_bracket(qty=6, stop=7416.0, side="LONG", target=7504.0)
    p = _captured["p"]
    assert p["op"] == "PLACE_BRACKET"
    assert p["qty"] == 6 and p["stop"] == 7416.0 and p["target"] == 7504.0
    assert p["side"] == "LONG"


def test_no_account_field_is_ever_sent(_captured):
    """The account is chosen DLL-side from sc.SelectedTradeAccount. Sending one
    from here was the root cause of every r=-1 on 07-27."""
    sc_cmd.write_place_bracket(qty=2, stop=7400.0, side="LONG")
    assert "account" not in _captured["p"]


def test_stop_only_when_no_target(_captured):
    sc_cmd.write_place_bracket(qty=2, stop=7400.0, side="LONG")
    assert "target" not in _captured["p"]


def test_long_rejects_target_below_stop(_captured):
    with pytest.raises(ValueError, match="stop < target"):
        sc_cmd.write_place_bracket(qty=2, stop=7500.0, side="LONG", target=7400.0)


def test_short_rejects_target_above_stop(_captured):
    with pytest.raises(ValueError, match="target < stop"):
        sc_cmd.write_place_bracket(qty=2, stop=7400.0, side="SHORT", target=7500.0)


@pytest.mark.parametrize("kw", [
    {"qty": 0, "stop": 7400.0, "side": "LONG"},
    {"qty": 2, "stop": 0, "side": "LONG"},
    {"qty": 2, "stop": 7400.0, "side": "FLAT"},
    {"qty": 2, "stop": 7400.0, "side": "LONG", "target": -1},
])
def test_bad_input_rejected(kw, _captured):
    with pytest.raises(ValueError):
        sc_cmd.write_place_bracket(**kw)


# ── target derivation ────────────────────────────────────────────────────────

def test_target_off_by_default(monkeypatch):
    monkeypatch.delenv("PLACE_BRACKET_TARGET_R", raising=False)
    assert rec._bracket_target_for({"entry": 7430.0, "stop": 7416.0, "side": "LONG"}) is None


def test_target_at_r_multiple(monkeypatch):
    monkeypatch.setenv("PLACE_BRACKET_TARGET_R", "2")
    t = rec._bracket_target_for({"entry": 7430.0, "stop": 7416.0, "side": "LONG"})
    assert t == 7458.0                      # 14pt risk → 2R above entry


def test_target_short_side_is_below(monkeypatch):
    monkeypatch.setenv("PLACE_BRACKET_TARGET_R", "2")
    t = rec._bracket_target_for({"entry": 7430.0, "stop": 7444.0, "side": "SHORT"})
    assert t == 7402.0


def test_zero_risk_gives_no_target(monkeypatch):
    """entry == stop → no honest target (Rule 1: None, not a made-up price)."""
    monkeypatch.setenv("PLACE_BRACKET_TARGET_R", "2")
    assert rec._bracket_target_for({"entry": 7430.0, "stop": 7430.0, "side": "LONG"}) is None


# ── flag gating + fallback ───────────────────────────────────────────────────

def test_flag_off_means_no_real_bracket(monkeypatch):
    monkeypatch.delenv("PLACE_BRACKET_OP_V1", raising=False)
    assert rec._place_bracket_enabled() is False


def test_flag_on(monkeypatch):
    monkeypatch.setenv("PLACE_BRACKET_OP_V1", "1")
    assert rec._place_bracket_enabled() is True


def test_result_reader_accepts_both_op_names(monkeypatch, tmp_path):
    """The DLL result says PLACE_BRACKET_OK; older builds said PLACE_STOP_OK."""
    import backend.v9.services.sierra_position_reconciler as r2
    p = tmp_path / "trade_result.json"
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(tmp_path))
    p.write_text(json.dumps({"status": "PLACE_BRACKET_OK", "r": 9731}))
    ok, status = r2._read_place_bracket_result(0.0, timeout_s=1.0)
    assert ok and status == "PLACE_BRACKET_OK"


def test_result_reader_reports_refusal(monkeypatch, tmp_path):
    import backend.v9.services.sierra_position_reconciler as r2
    p = tmp_path / "trade_result.json"
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(tmp_path))
    p.write_text(json.dumps({"status": "PLACE_BRACKET_REJECT_WRONG_SIDE", "r": -1}))
    ok, status = r2._read_place_bracket_result(0.0, timeout_s=1.0)
    assert ok is False and "WRONG_SIDE" in status


# ── DLL source contract ──────────────────────────────────────────────────────

_DLL = "sc_study/MES_AI_DataExport_merged.cpp"


def _dll() -> str:
    with open(_DLL, encoding="utf-8") as f:
        return f.read()


def test_dll_does_not_call_the_nonexistent_submitorder():
    """sc.SubmitOrder has ZERO public definitions in ACSIL — v2 called it and
    could never have compiled."""
    assert "sc.SubmitOrder(" not in _dll()


def test_dll_uses_exit_family_with_oco_limit_stop():
    src = _dll()
    assert "SCT_ORDERTYPE_OCO_LIMIT_STOP" in src
    assert "sc.SellExit(o)" in src and "sc.BuyExit(o)" in src


def test_dll_routes_to_selected_trade_account():
    assert "o.TradeAccount  = sc.SelectedTradeAccount" in _dll()


def test_dll_has_the_price_vs_market_gate():
    """The half v2 was missing: stop/target compared against the LIVE price."""
    src = _dll()
    i = src.index("PLACE_BRACKET v3")
    block = src[i:i + 9000]
    assert "last_px" in block
    assert "PLACE_BRACKET_REJECT_WRONG_SIDE" in block
    assert "pb_stop < last_px" in block and "pb_stop > last_px" in block


def test_dll_bracket_is_reduce_only_and_refuses_when_flat():
    src = _dll()
    i = src.index("PLACE_BRACKET v3")
    block = src[i:i + 9000]
    assert "PLACE_BRACKET_NO_POSITION" in block
    assert "clamped_qty" in block


def test_dll_bracket_never_uses_the_broken_exit_op():
    """op=EXIT is the broken partial-exit path (CLAUDE.md). This handler must
    not touch it."""
    src = _dll()
    i = src.index("PLACE_BRACKET v3")
    block = src[i:i + 9000]
    assert '"EXIT"' not in block
