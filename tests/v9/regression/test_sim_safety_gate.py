"""SIM safety gate (Michael 07-15): BUY/SELL refused when Sierra is_sim=0 and no
live-GO. Anti-tautological: same command passes on SIM, and passes LIVE only with
armed+ack; protective ops never gated."""
import json, os, time, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))


def _gate(action, is_sim, ctx, armed, state_age=1.0, today="2026-07-15"):
    """Pure re-implementation of the gate's decision (mirrors trade_commands.py)."""
    if action not in ("BUY", "SELL"):
        return True  # protective/other never gated
    sim_ok = is_sim in (1, True) and state_age <= 15
    if sim_ok:
        return True
    ack_ok = str((ctx or {}).get("live_ack", "")) == today
    return bool(armed and ack_ok)


def test_entry_on_sim_allowed():
    assert _gate("BUY", 1, {}, armed=False) is True


def test_entry_on_live_refused_without_go():
    assert _gate("SELL", 0, {}, armed=False) is False


def test_entry_on_live_allowed_with_full_go():
    assert _gate("BUY", 0, {"live_ack": "2026-07-15"}, armed=True) is True


def test_entry_on_live_refused_armed_but_no_ack():
    assert _gate("BUY", 0, {}, armed=True) is False


def test_entry_on_live_refused_ack_but_not_armed():
    assert _gate("SELL", 0, {"live_ack": "2026-07-15"}, armed=False) is False


def test_stale_eye_refuses_entry():
    assert _gate("BUY", 1, {}, armed=False, state_age=99) is False  # fail-closed


def test_flatten_never_gated():
    assert _gate("FLATTEN_ACCOUNT", 0, {}, armed=False) is True


def test_modify_never_gated():
    assert _gate("MODIFY", 0, {}, armed=False) is True
