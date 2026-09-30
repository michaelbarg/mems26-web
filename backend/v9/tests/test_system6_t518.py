"""T-518 (30.09): System 6 alert de-dup + structural-stop exemption (flag OFF by default)."""
import backend.v9.systems.system6_supervisor as s6


def test_structural_exempt_off_keeps_band_alert(monkeypatch):
    monkeypatch.delenv("SYSTEM6_STRUCTURAL_STOP_EXEMPT_V1", raising=False)
    rep = s6.diagnose_trade(trade={"direction": "LONG", "entry_price": 7727.0, "stop": 7714.25, "t1": 7746.12,
                                   "contracts": 1, "stop_is_structural": True}, atr=7.48)
    assert any(i.code == "stop_too_wide" for i in rep.issues)


def test_structural_exempt_on_skips_band_but_keeps_hard_cap(monkeypatch):
    monkeypatch.setenv("SYSTEM6_STRUCTURAL_STOP_EXEMPT_V1", "1")
    rep = s6.diagnose_trade(trade={"direction": "LONG", "entry_price": 7727.0, "stop": 7714.25, "t1": 7746.12,
                                   "contracts": 1, "stop_is_structural": True}, atr=7.48)
    assert not any(i.code == "stop_too_wide" for i in rep.issues)
    rep2 = s6.diagnose_trade(trade={"direction": "LONG", "entry_price": 7727.0, "stop": 7700.0, "t1": 7746.12,
                                    "contracts": 1, "stop_is_structural": True}, atr=7.48)
    assert any(i.code == "stop_too_wide" and "hard cap" in i.detail for i in rep2.issues)
    # a non-structural stop is judged exactly as before
    rep3 = s6.diagnose_trade(trade={"direction": "LONG", "entry_price": 7727.0, "stop": 7714.25, "t1": 7746.12,
                                    "contracts": 1}, atr=7.48)
    assert any(i.code == "stop_too_wide" for i in rep3.issues)


def test_alert_dedup_window(monkeypatch):
    monkeypatch.setenv("SYSTEM6_ALERT_REPEAT_S", "300")
    s6._ALERT_LAST.clear()
    assert s6._alert_should_log(2594, "stop_too_wide", "risk 12.75pt > cap 11.22pt") is True
    assert s6._alert_should_log(2594, "stop_too_wide", "risk 12.75pt > cap 11.22pt") is False
    assert s6._alert_should_log(2623, "stop_too_wide", "risk 12.75pt > cap 11.22pt") is True   # other trade
    assert s6._alert_should_log(2594, "naked_stop", "x") is True                                # other code
    monkeypatch.setenv("SYSTEM6_ALERT_REPEAT_S", "0")
    assert s6._alert_should_log(2594, "stop_too_wide", "risk 12.75pt > cap 11.22pt") is True   # window 0 = every time
