"""Michael 2026-08-19: "אם אין מספיק מרגין לסחור על 4 לא לשאול לבצע".

If the account cannot carry the ruled 6, trade FOUR — not the max affordable,
not 5 (18.08: a 5-lot was rejected over ~$6 of headroom), and never 3/2/1/0
(the 08-13 "1:1" ruling still forbids silent shrink below the fallback).
Missing/stale account data changes nothing (Rule 1 — no guess).

Anti-tautological: the module is exercised through cap_contracts with a
monkeypatched state reader, covering every branch the ruling defines.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

import backend.v9.services.margin_sizing as ms  # noqa: E402


def _state(avail, qty=0, req=0.0):
    return {"acct_ok": 1, "acct_available_funds": avail,
            "position_qty": qty, "acct_margin_req": req}


def _arm(monkeypatch, state, per_contract="386.20", buf="50"):
    monkeypatch.setenv("MARGIN_AWARE_SIZING_V1", "1")
    monkeypatch.setenv("MES_MARGIN_PER_CONTRACT", per_contract)
    monkeypatch.setenv("MARGIN_BUFFER_USD", buf)
    monkeypatch.setattr(ms, "_read_state", lambda: state)


def test_affordable_6_stays_6(monkeypatch):
    # 6×386.20 = 2,317.20; avail 3,000 − 50 buffer covers it.
    _arm(monkeypatch, _state(3000.0))
    allowed, why = ms.cap_contracts(6)
    assert allowed == 6 and "margin ok" in why


def test_unaffordable_6_falls_to_4_not_5(monkeypatch):
    # avail 1,977 (the live cash balance class): covers 4 (1,544.80) and even
    # 5 numerically minus buffer? 1,927 usable < 5×386.20=1,931 — and even if
    # it did cover 5, the ruling says 4. Assert 4, never 5.
    _arm(monkeypatch, _state(1977.0))
    allowed, why = ms.cap_contracts(6)
    assert allowed == 4 and "MARGIN FALLBACK" in why


def test_even_affordable_5_is_skipped(monkeypatch):
    # avail 2,050 → usable 2,000 covers 5×386.20=1,931 but not 6×=2,317.20.
    # The ruling's fallback is 4 — headroom over max-affordable.
    _arm(monkeypatch, _state(2050.0))
    allowed, _ = ms.cap_contracts(6)
    assert allowed == 4


def test_below_fallback_never_shrinks(monkeypatch):
    # 08-13 "1:1": a requested 4 stays 4 even when unaffordable — the broker
    # adjudicates; we do not invent 3/2/1/0.
    _arm(monkeypatch, _state(250.11))          # the live 08-19 morning number
    for n in (4, 3, 2, 1):
        allowed, why = ms.cap_contracts(n)
        assert allowed == n, f"requested {n} must not shrink, got {allowed}"
        assert "1:1" in why


def test_missing_state_changes_nothing(monkeypatch):
    monkeypatch.setenv("MARGIN_AWARE_SIZING_V1", "1")
    monkeypatch.setattr(ms, "_read_state", lambda: None)
    allowed, why = ms.cap_contracts(6)
    assert allowed == 6 and "no guess" in why


def test_flag_off_is_inert(monkeypatch):
    monkeypatch.setenv("MARGIN_AWARE_SIZING_V1", "0")
    allowed, why = ms.cap_contracts(6)
    assert allowed == 6 and "off" in why


def test_per_contract_takes_conservative_max(monkeypatch):
    # Held-position maintenance (275.33) must not fool the cap below the
    # recorded OPENING requirement (386.20): max() wins.
    _arm(monkeypatch, _state(3000.0, qty=6, req=1651.98))
    per = ms.margin_per_contract(_state(3000.0, qty=6, req=1651.98))
    assert abs(per - 386.20) < 0.01


def test_live_derivation_used_when_no_env(monkeypatch):
    monkeypatch.delenv("MES_MARGIN_PER_CONTRACT", raising=False)
    per = ms.margin_per_contract(_state(3000.0, qty=6, req=1651.98))
    assert abs(per - 1651.98 / 6) < 0.01
