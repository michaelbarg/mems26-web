"""DAYTYPE_HONEST_PRELOCK_V1 — a pre-IB-lock day_type is PROVISIONAL, not final.

N1c (2026-07-17): before the IB locks (~60min/12 bars) `day_type_machine.day_type`
can still hold the OLD base engine's own low-confidence read (e.g. "Trend_Normal"
0.35, seen live on both 2026-07-15 and 2026-07-16 around 10:00 ET) —
get_live_day_type()'s exclusion list didn't catch this string, so it passed
through looking like a canonical verdict.

T-47 / F6 (Michael ruling 2026-08-19, re-confirmed 2026-08-20) REPLACES the
original remedy.  The first implementation returned None pre-lock, and that was
measured wrong TWICE on one live day:

  * 2026-07-20 10:10 ET — Michael turned `S4_HONEST_DAYTYPE_FALLBACK_V1` OFF:
    a null label pre-lock made S4 skip a classified down-day ("אזור-מת בשעה
    הראשונה");
  * 2026-07-20 10:58 ET — Michael turned `S2_DETECTION_LIVE_DAYTYPE_V1` OFF:
    `five_min_system` treats None as never-passes, so S2 skipped every setup
    ("פספוס-עסקאות").

Both notes are recorded in `config/RULED_FLAGS.yaml`.  Suppressing the label
costs trades.  The ruled remedy: keep publishing the label, MARK it provisional,
and let the gates that VETO on day type degrade that veto to advisory — through
the SAME `conf < DAYTYPE_PLAYBOOK_MIN_CONF (0.4)` path that already exists, not a
second invented notion of "untrustworthy label".

Default OFF -> byte-identical.
"""
import ast
import os
from unittest.mock import patch, MagicMock

from backend.v9.services.trade_context import daytype_is_provisional, get_live_day_type


def _mock_app_state(day_type_value, ib_locked):
    dtm = MagicMock()
    dtm.day_type = day_type_value
    dtm.ib_locked = ib_locked
    app = MagicMock()
    app.state.day_type_machine = dtm
    return app


def _env(**extra):
    base = {"DAYTYPE_GATE_LIVE_V1": "1"}
    base.update(extra)
    return base


# ==========================================================================
# 1. flag OFF -> byte-identical
# ==========================================================================
def test_flag_off_preserves_prelock_passthrough_byte_identical():
    """Default (flag unset) keeps today's behaviour — proves this is opt-in."""
    mock_app = _mock_app_state("Trend_Normal", ib_locked=False)
    with patch.dict(os.environ, _env()):
        with patch("importlib.import_module", return_value=MagicMock(app=mock_app)):
            assert get_live_day_type() == "Trend_Normal"
            assert daytype_is_provisional() is False


def test_flag_off_postlock_unchanged():
    mock_app = _mock_app_state("Variation", ib_locked=True)
    with patch.dict(os.environ, _env()):
        with patch("importlib.import_module", return_value=MagicMock(app=mock_app)):
            assert get_live_day_type() == "Variation"
            assert daytype_is_provisional() is False


# ==========================================================================
# 2. flag ON -> the label STILL FLOWS, and is marked provisional
# ==========================================================================
def test_flag_on_prelock_keeps_publishing_the_label():
    """The ruled change: pre-lock no longer returns None.

    This is the anti-regression guard for the 2026-07-20 incidents — a null label
    pre-lock is what created the first-hour dead zone for S2 and S4.
    """
    mock_app = _mock_app_state("Trend_Normal", ib_locked=False)
    with patch.dict(os.environ, _env(DAYTYPE_HONEST_PRELOCK_V1="1")):
        with patch("importlib.import_module", return_value=MagicMock(app=mock_app)):
            assert get_live_day_type() == "Trend_Normal"      # NOT None
            assert daytype_is_provisional() is True           # but flagged


def test_flag_on_postlock_is_not_provisional():
    """Post-lock the Market Profile foundation is formed — the label is settled."""
    mock_app = _mock_app_state("Trend_Normal", ib_locked=True)
    with patch.dict(os.environ, _env(DAYTYPE_HONEST_PRELOCK_V1="1")):
        with patch("importlib.import_module", return_value=MagicMock(app=mock_app)):
            assert get_live_day_type() == "Trend_Normal"
            assert daytype_is_provisional() is False


def test_flag_on_already_excluded_value_stays_none():
    """No new leak: an already-excluded raw value is still None."""
    mock_app = _mock_app_state("UNKNOWN", ib_locked=False)
    with patch.dict(os.environ, _env(DAYTYPE_HONEST_PRELOCK_V1="1")):
        with patch("importlib.import_module", return_value=MagicMock(app=mock_app)):
            assert get_live_day_type() is None


def test_manual_override_still_wins(monkeypatch):
    """DAY_TYPE_MANUAL_OVERRIDE (Michael IS the S1 authority) takes precedence —
    checked before the machine is read, must not be shadowed."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    monkeypatch.setenv("DAY_TYPE_MANUAL_OVERRIDE", f"{today}:Neutral_Center")
    monkeypatch.setenv("DAYTYPE_HONEST_PRELOCK_V1", "1")
    monkeypatch.setenv("DAYTYPE_GATE_LIVE_V1", "1")
    mock_app = _mock_app_state("Trend_Normal", ib_locked=False)
    with patch("importlib.import_module", return_value=MagicMock(app=mock_app)):
        assert get_live_day_type() == "Neutral_Center"


# ==========================================================================
# 3. fail-safe: a bug must never degrade a gate
# ==========================================================================
def test_provisional_is_false_when_no_machine():
    app = MagicMock()
    app.state.day_type_machine = None
    with patch.dict(os.environ, _env(DAYTYPE_HONEST_PRELOCK_V1="1")):
        with patch("importlib.import_module", return_value=MagicMock(app=app)):
            assert daytype_is_provisional() is False


def test_provisional_is_false_on_error():
    with patch.dict(os.environ, _env(DAYTYPE_HONEST_PRELOCK_V1="1")):
        with patch("backend.v9.services.trade_context._live_day_type_machine",
                   side_effect=RuntimeError("boom")):
            assert daytype_is_provisional() is False


def test_gateway_helper_mirrors_and_failsafes():
    from backend.v9.gateway.trading_gateway import _daytype_provisional
    with patch("backend.v9.services.trade_context.daytype_is_provisional",
               return_value=True):
        assert _daytype_provisional() is True
    with patch("backend.v9.services.trade_context.daytype_is_provisional",
               side_effect=RuntimeError("boom")):
        assert _daytype_provisional() is False


# ==========================================================================
# 4. the degrade REUSES the conf<0.4 path (the ruling said reuse, not invent)
# ==========================================================================
def _src(*parts):
    return open(os.path.join(os.path.dirname(__file__), "..", "..", "..", *parts)).read()


def test_gateway_provisional_degrades_through_the_same_variable():
    """`_daytype_provisional()` must set the SAME `_pb_conf_ok` flag the conf<0.4
    branch sets, and the block must stay guarded by `if not _ow_ok and _pb_conf_ok`.
    If a future edit gives provisional its own separate block, this fails."""
    src = _src("backend", "v9", "gateway", "trading_gateway.py")
    tree = ast.parse(src)

    def assigns_pb_conf_ok_false(node):
        for n in ast.walk(node):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name) and t.id == "_pb_conf_ok":
                        if isinstance(n.value, ast.Constant) and n.value.value is False:
                            return True
        return False

    found = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        call_names = {n.func.id for n in ast.walk(node.test)
                      if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        if "_daytype_provisional" in call_names and assigns_pb_conf_ok_false(node):
            found = True
    assert found, "provisional must degrade via _pb_conf_ok = False (the conf<0.4 path)"
    assert "if not _ow_ok and _pb_conf_ok:" in src, "the single veto guard must survive"


def test_s2_setup_emitter_provisional_uses_the_same_reduced_branch():
    """S2's AUTH_LOWCONF_REDUCED SKIP->REDUCED-2 degrade must be the same branch
    for conf<0.4 and for provisional — one notion of 'untrustworthy label'."""
    src = _src("backend", "v9", "systems", "five_min", "setup_emitter.py")
    assert "daytype_is_provisional as _lc_prov_fn" in src
    assert "or _lc_prov)" in src
    # still gated by AUTH_LOWCONF_REDUCED_V1, still lands on REDUCED-2
    assert "if _lc_on and ((_lc_conf is not None and _lc_conf < _lc_min) or _lc_prov):" in src
    assert "verdict, sizing = 'REDUCED', 2" in src
