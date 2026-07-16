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
    # SHORT with stop BELOW entry/price (wrong side — unprotected)
    rep = diagnose_trade(trade=_trade(stop=7532.0), atr=ATR)
    assert "stop_wrong_side" in _codes(rep)


def test_profit_locked_stop_not_wrong_side():
    """Incident 07-10: LONG entry 7608.5, stop moved to 7611.25 after T1.
    Stop ABOVE entry = profit-locked = DESIRED state, not wrong side.
    Price is at 7614 — stop is below price = correctly protective.
    If reverted → RED because the old code compared stop vs entry,
    flagging stop>entry as wrong_side even when it's profit-locked."""
    trade = {"direction": "LONG", "entry_price": 7608.5, "stop": 7611.25,
             "t1": 7617.5, "contracts": 3}
    rep = diagnose_trade(trade=trade, atr=ATR, t1_hit=True, price=7614.0)
    assert "stop_wrong_side" not in _codes(rep)


def test_wrong_side_stop_above_price():
    """LONG with stop above current price = truly wrong side (unprotected)."""
    trade = {"direction": "LONG", "entry_price": 7600.0, "stop": 7620.0,
             "contracts": 3}
    rep = diagnose_trade(trade=trade, atr=ATR, price=7615.0)
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


# --- N4(a) rescue-tier: counter-signal / stuck / runner-reversal (all ALERT-only) ---
def test_counter_signal_before_t1_flagged():
    rep = diagnose_trade(trade=_trade(), atr=ATR, counter_signal_pre_t1=True, t1_hit=False)
    iss = next(i for i in rep.issues if i.code == "counter_signal_pre_t1")
    assert iss.action == ALERT and iss.correction is None


def test_counter_signal_after_t1_not_flagged():
    """Once T1 is proven, a new opposite signal elsewhere isn't a 'falling trade' tell."""
    rep = diagnose_trade(trade=_trade(stop=7540.0), atr=ATR,
                         counter_signal_pre_t1=True, t1_hit=True)
    assert "counter_signal_pre_t1" not in _codes(rep)


def test_counter_signal_false_default_no_flag():
    rep = diagnose_trade(trade=_trade(), atr=ATR)
    assert "counter_signal_pre_t1" not in _codes(rep)


def test_stuck_trade_flagged_when_no_progress():
    # risk = |7540-7548| = 8pt; progress 1.0pt < 25% of 8pt (2.0pt) -> stuck
    rep = diagnose_trade(trade=_trade(), atr=ATR, bars_since_entry=12, progress_pts=1.0)
    iss = next(i for i in rep.issues if i.code == "stuck_trade")
    assert iss.action == ALERT and iss.severity == WARN


def test_stuck_trade_not_flagged_with_good_progress():
    # progress 5.0pt >= 25% of 8pt risk -> not stuck
    rep = diagnose_trade(trade=_trade(), atr=ATR, bars_since_entry=12, progress_pts=5.0)
    assert "stuck_trade" not in _codes(rep)


def test_stuck_trade_not_flagged_before_threshold_bars():
    rep = diagnose_trade(trade=_trade(), atr=ATR, bars_since_entry=5, progress_pts=0.0)
    assert "stuck_trade" not in _codes(rep)


def test_stuck_trade_silent_without_both_signals():
    """Rule 1: never guess progress — missing bars_since_entry OR progress_pts -> no flag."""
    rep = diagnose_trade(trade=_trade(), atr=ATR, bars_since_entry=20)  # progress_pts missing
    assert "stuck_trade" not in _codes(rep)


def test_stuck_trade_not_flagged_once_t1_hit():
    rep = diagnose_trade(trade=_trade(stop=7540.0), atr=ATR, t1_hit=True,
                         bars_since_entry=50, progress_pts=0.0)
    assert "stuck_trade" not in _codes(rep)


def test_runner_reversal_flagged_after_t1():
    rep = diagnose_trade(trade=_trade(stop=7540.0), atr=ATR, t1_hit=True, runner_reversal=True)
    iss = next(i for i in rep.issues if i.code == "runner_reversal")
    assert iss.action == ALERT and iss.correction is None


def test_runner_reversal_not_flagged_before_t1():
    """Pre-T1 there's no 'runner' yet — the check is post-T1 only."""
    rep = diagnose_trade(trade=_trade(), atr=ATR, t1_hit=False, runner_reversal=True)
    assert "runner_reversal" not in _codes(rep)


def test_n4a_signals_never_auto_applied(monkeypatch):
    """All three N4(a) issues are ALERT — AUTOCORRECT=1 must never execute them."""
    monkeypatch.setenv("SYSTEM6_SUPERVISOR", "1")
    monkeypatch.setenv("SYSTEM6_AUTOCORRECT", "1")
    applied = []
    scan_active_trade(trade=_trade(stop=7540.0), atr=ATR, t1_hit=True,
                      counter_signal_pre_t1=True, runner_reversal=True,
                      bars_since_entry=99, progress_pts=0.0,
                      executor=lambda c: applied.append(c) or True)
    assert applied == [], "N4(a) rescue-tier issues are ALERT-only; must never auto-apply"


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
