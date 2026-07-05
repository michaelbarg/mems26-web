"""System 6 — active-trade supervisor: diagnosis + auto-correct routing."""
import random

from backend.v9.systems.system6_supervisor import (
    diagnose_trade, scan_active_trade, SupervisorReport,
    CRITICAL, WARN, AUTO, ALERT,
)

ATR = 8.0


def _trade(**kw):
    base = {"direction": "SHORT", "entry_price": 7540.0, "stop": 7548.0,
            "t1": 7532.0, "t2": 7524.0, "t3": None, "contracts": 3}
    base.update(kw)
    return base


def _codes(rep):
    return {i.code for i in rep.issues}


# --- healthy baseline ---
def test_healthy_trade_no_issues():
    rep = diagnose_trade(trade=_trade(), atr=ATR, expected_contracts=3)
    assert rep.healthy and rep.issues == []


# --- naked / wrong-side stop (CRITICAL) ---
def test_naked_stop_critical_with_be_correction():
    rep = diagnose_trade(trade=_trade(stop=None), atr=ATR)
    assert not rep.healthy
    iss = next(i for i in rep.issues if i.code == "naked_stop")
    assert iss.severity == CRITICAL and iss.action == ALERT
    assert iss.correction["op"] == "MODIFY_STOP"


def test_stop_wrong_side_critical():
    # SHORT with stop BELOW entry (wrong side)
    rep = diagnose_trade(trade=_trade(stop=7532.0), atr=ATR)
    assert "stop_wrong_side" in _codes(rep)


# --- BE after T1 (AUTO) ---
def test_stop_not_at_be_after_t1_autocorrects():
    # SHORT, T1 hit, stop still above entry+ (7548 > 7540) → not BE
    rep = diagnose_trade(trade=_trade(stop=7548.0), atr=ATR, t1_hit=True)
    iss = next(i for i in rep.issues if i.code == "stop_not_at_be")
    assert iss.action == AUTO and iss.correction == {"op": "MODIFY_STOP", "price": 7540.0}


def test_be_stop_after_t1_is_healthy():
    rep = diagnose_trade(trade=_trade(stop=7540.0), atr=ATR, t1_hit=True)
    assert "stop_not_at_be" not in _codes(rep)


# --- stop band ---
def test_financed_stop_flagged():
    # risk 1.0pt << floor 4.0 (0.5*8)
    rep = diagnose_trade(trade=_trade(stop=7541.0), atr=ATR)
    assert "stop_too_tight" in _codes(rep)


def test_absurd_wide_stop_flagged():
    rep = diagnose_trade(trade=_trade(stop=7600.0), atr=ATR)
    assert "stop_too_wide" in _codes(rep)


# --- targets wrong side (I-61, AUTO drop) ---
def test_wrong_side_target_dropped():
    # SHORT with t2 ABOVE entry
    rep = diagnose_trade(trade=_trade(t2=7550.0), atr=ATR)
    iss = next(i for i in rep.issues if i.code == "t2_wrong_side")
    assert iss.action == AUTO and iss.correction == {"op": "DROP_TARGET", "target": "t2"}


# --- T1 too close ---
def test_t1_too_close_flagged():
    rep = diagnose_trade(trade=_trade(t1=7539.0), atr=ATR)  # 1pt < floor 4
    assert "t1_too_close" in _codes(rep)


# --- size + EOD + reconcile ---
def test_contract_mismatch_flagged():
    rep = diagnose_trade(trade=_trade(contracts=2), atr=ATR, expected_contracts=3)
    assert "contract_mismatch" in _codes(rep)


def test_eod_open_position_flagged():
    rep = diagnose_trade(trade=_trade(), atr=ATR, now_ct_min=14 * 60 + 30)
    assert "eod_open_position" in _codes(rep)


def test_reconcile_mismatch_is_critical():
    rep = diagnose_trade(trade=_trade(), atr=ATR, reconcile_mismatch=True,
                         reconcile_verdict="MISMATCH_ORPHAN_DB")
    iss = next(i for i in rep.issues if i.code == "reconcile_mismatch")
    assert iss.severity == CRITICAL


# --- scan wrapper: gating + executor routing ---
def test_scan_disabled_returns_none(monkeypatch):
    monkeypatch.delenv("SYSTEM6_SUPERVISOR", raising=False)
    assert scan_active_trade(trade=_trade(), atr=ATR) is None


def test_scan_reports_but_does_not_apply_when_autocorrect_off(monkeypatch):
    monkeypatch.setenv("SYSTEM6_SUPERVISOR", "1")
    monkeypatch.delenv("SYSTEM6_AUTOCORRECT", raising=False)
    applied = []
    rep = scan_active_trade(trade=_trade(stop=7548.0), atr=ATR, t1_hit=True,
                            executor=lambda c: applied.append(c) or True)
    assert rep is not None and not rep.healthy
    assert applied == [], "must NOT apply corrections when SYSTEM6_AUTOCORRECT is off"


def test_scan_applies_auto_when_autocorrect_on(monkeypatch):
    monkeypatch.setenv("SYSTEM6_SUPERVISOR", "1")
    monkeypatch.setenv("SYSTEM6_AUTOCORRECT", "1")
    applied = []
    scan_active_trade(trade=_trade(stop=7548.0), atr=ATR, t1_hit=True,
                      executor=lambda c: applied.append(c) or True)
    assert {"op": "MODIFY_STOP", "price": 7540.0} in applied


def test_scan_never_applies_alert_only_issues(monkeypatch):
    """A naked stop is ALERT (needs human) — auto-correct must not fire it even
    though it carries a suggested correction."""
    monkeypatch.setenv("SYSTEM6_SUPERVISOR", "1")
    monkeypatch.setenv("SYSTEM6_AUTOCORRECT", "1")
    applied = []
    scan_active_trade(trade=_trade(stop=None), atr=ATR,
                      executor=lambda c: applied.append(c) or True)
    assert applied == [], "naked_stop is ALERT-only; must not be auto-applied"


# --- fuzz: an AUTO correction is never emitted for a wrong-side stop (CRITICAL) ---
def test_fuzz_critical_never_auto():
    rnd = random.Random(60)
    for _ in range(2000):
        direction = rnd.choice(["LONG", "SHORT"])
        entry = round(rnd.uniform(7400, 7700), 2)
        stop = round(entry + rnd.uniform(-15, 15), 2)
        t1_hit = rnd.random() < 0.5
        rep = diagnose_trade(trade={"direction": direction, "entry_price": entry,
                                    "stop": stop}, atr=ATR, t1_hit=t1_hit)
        for i in rep.issues:
            # invariant: every CRITICAL issue is ALERT (never silently auto-fixed)
            if i.severity == CRITICAL:
                assert i.action == ALERT
