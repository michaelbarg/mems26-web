"""T-610 · LADDER_221_V1 — five contracts as 2/2/1 (T1/T2/T3, no T0). Michael 19.10.2026.

    "נעבוד עם 5 חוזים לפי 2 2 1 כאילו זה 3 חוזים רק שבמימוש נתייחס בשלב הזה ככה"

Until this change five contracts ALWAYS executed as LADDER[5]: T0×1 · T1×2 ·
T2×1 · T3×1 — what Michael asked for and what the broker held differed. The
pieces pinned here:

  1. flag OFF — and flag ON whenever the loaded DLL cannot honour per-group
     quantities (heartbeat missing / stale / unreadable / pre-T-610 build), or
     the size is not five — the PLACE payload is BYTE-IDENTICAL to the
     pre-T-610 writer (loaded from git at BASELINE) and the trade row too;
  2. flag ON + DLL cap_lq=1 + five — the PLACE carries lq1..lq4 = 2/2/1/0,
     target_price=T1 · t2=T2 · t3=T3, no t4, no T0; the row records
     ladder_groups=[2,2,1,0] / has_t0=False, decided ONCE in accept_setup;
  3. every consumer follows the TRADE's recorded ladder (books, panel, phone,
     reconciler, System 6) — rows without one compute exactly as before;
  4. the DLL source parses lq1..lq4 with the sum==contracts validation and the
     table fallback, advertises cap_lq, echoes the shape it used, and the
     regeneration guard protects it (nobody can compile before the Remote
     Build, so the C++ is checked statically, including printf arity).
"""
import copy
import functools
import json
import os
import re
import subprocess
import sys
import time
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from backend.v9.services import contract_size as cs          # noqa: E402
from backend.v9.services import sierra_command as sc         # noqa: E402

#: the commit right before T-610 — the "today" every byte-identity test compares to
BASELINE = "7114cecb4"
CPP = REPO / "sc_study" / "MES_AI_DataExport_merged.cpp"

SETUP_LONG = {"direction": "LONG", "entry_price": 7600.0, "stop": 7590.0,
              "t1": 7605.0, "t2": 7612.0, "t3": 7620.0,
              "classification": "REACTIVE_LONG", "firing_system": 2,
              "metadata": {"pattern": "REACTIVE_LONG", "sizing_contracts": 5}}
SETUP_SHORT = {"direction": "SHORT", "entry_price": 7600.0, "stop": 7610.0,
               "t1": 7595.0, "t2": 7588.0, "t3": 7580.0,
               "classification": "REACTIVE_SHORT", "firing_system": 2,
               "metadata": {"pattern": "REACTIVE_SHORT", "sizing_contracts": 5}}
SETUP_ZLR = {"direction": "LONG", "entry_price": 7600.0, "stop": 7592.0,
             "t1": 7604.0, "t2": 7609.0, "t3": 7616.0,
             "classification": "ZLR", "firing_system": 4,
             "metadata": {"pattern": "ZLR", "sizing_contracts": 5}}
SETUPS = [SETUP_LONG, SETUP_SHORT, SETUP_ZLR]
SETUP_IDS = ["long", "short", "zlr"]

_PINNED_OFF = ("FIXED_CONTRACTS_1", "FIXED_CONTRACTS_2", "FIXED_CONTRACTS_3",
               "FIXED_CONTRACTS_4", "FIXED_CONTRACTS_6", "SIZE_CAP_OVER_FIXED_V1",
               "RISK_BUDGET_SIZING_V1", "MARGIN_AWARE_SIZING_V1",
               "RUNNER_BY_DAYTYPE_V1", "LADDER_221_V1")


# ── fixtures / helpers ────────────────────────────────────────────────────────

@pytest.fixture
def env(monkeypatch, tmp_path):
    """Today's live flag set (20.10), pinned — never the ambient .env."""
    for f in _PINNED_OFF:
        monkeypatch.setenv(f, "0")
    monkeypatch.setenv("FIXED_CONTRACTS_5", "1")
    monkeypatch.setenv("T0_TARGET_PTS", "3.0")
    monkeypatch.setenv("BE_AFTER_REAL_T1_V1", "1")
    monkeypatch.setenv("RUNNER_TRAIL_V2", "1")
    monkeypatch.setenv("C4_RULING6_V1", "1")
    monkeypatch.setenv("ZLR_MGMT_V1", "1")
    monkeypatch.setenv("T3_REQUIRED_V1", "1")
    monkeypatch.setenv("LADDER_SANITIZE_V1", "1")
    exp = tmp_path / "export"
    exp.mkdir()
    monkeypatch.setenv("V9_EXPORT_DIR", str(exp))
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(tmp_path / "signals"))
    cs._PLANS.clear()
    cs._CAP_CACHE.clear()
    yield types.SimpleNamespace(export=exp, tmp=tmp_path, mp=monkeypatch)
    cs._PLANS.clear()
    cs._CAP_CACHE.clear()


def _write_state(d, cap=1, age=0.0, raw=None):
    """A sierra_state.json heartbeat as the DLL writes it (cap=None = pre-T-610 DLL)."""
    p = Path(d) / "sierra_state.json"
    if raw is None:
        body = {"ts": int(time.time() - age), "is_sim": 1, "order_placement_armed": 1}
        if cap is not None:
            body["cap_lq"] = cap
        body.update({"position_qty": 0, "working_orders": 0, "orders": []})
        raw = json.dumps(body)
    p.write_text(raw)
    t = time.time() - age
    os.utime(p, (t, t))
    cs._CAP_CACHE.clear()
    return p


@functools.lru_cache(maxsize=1)
def _baseline_module():
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO), "show",
             BASELINE + ":backend/v9/services/sierra_command.py"],
            capture_output=True, timeout=30)
    except Exception:
        return None
    if out.returncode != 0 or not out.stdout:
        return None
    mod = types.ModuleType("_sierra_command_pre_t610")
    mod.__file__ = str(REPO / "backend" / "v9" / "services" / "sierra_command.py")
    exec(compile(out.stdout.decode("utf-8"), "sierra_command@" + BASELINE, "exec"),
         mod.__dict__)
    return mod


def _baseline():
    m = _baseline_module()
    if m is None:
        pytest.skip("pre-T-610 baseline %s not available (no git history here)" % BASELINE)
    return m


def _clean(p):
    """Drop what is volatile by construction (queue stamps, wall-clock)."""
    return {k: v for k, v in p.items() if not k.startswith("_") and k != "ts_submitted"}


def _dumps(p):
    return json.dumps(p, ensure_ascii=False)


def _both(env, setup, trade_id="9001"):
    """(new payload, pre-T-610 payload) for the SAME setup, each in its own wire dir."""
    base = _baseline()
    env.mp.setenv("MEMS26_SIGNALS_DIR", str(env.tmp / "sig_new"))
    new = sc.command_from_setup(copy.deepcopy(setup), trade_id=trade_id,
                                account="Sim1", mode="demo")
    env.mp.setenv("MEMS26_SIGNALS_DIR", str(env.tmp / "sig_old"))
    old = base.command_from_setup(copy.deepcopy(setup), trade_id=trade_id,
                                  account="Sim1", mode="demo")
    return _clean(new), _clean(old)


def _dll_parse_lq(text, contracts):
    """Python mirror of the T-610 C++ block — the per-group quantities the DLL
    uses, or None when it keeps its own table. Proves the WIRE format (json
    indent=2: a space after every colon) is what the C++ expects."""
    if contracts <= 0:
        contracts = 3
    if contracts > 6:
        contracts = 6
    cq = []
    for k in ('"lq1"', '"lq2"', '"lq3"', '"lq4"'):
        qp = text.find(k)
        if qp < 0:
            return None
        qp = text.find(":", qp)
        if qp < 0:
            return None
        qp += 1
        while qp < len(text) and text[qp] in " \t\r\n":
            qp += 1
        if qp >= len(text) or not ("0" <= text[qp] <= "9"):
            return None
        v = int(re.match(r"\d+", text[qp:]).group())
        if v < 0 or v > 6:
            return None
        if cq and v > 0 and cq[-1] == 0:
            return None
        cq.append(v)
    if cq[0] >= 1 and sum(cq) == contracts:
        return tuple(cq)
    return None


# ── 1. the decision ───────────────────────────────────────────────────────────

class TestTheDecision:
    def test_flag_off_is_todays_plan_even_with_a_capable_dll(self, env):
        p = cs.ladder_plan(5, dll_caps={"cap_lq": 1})
        assert p["groups"] == (1, 2, 1, 1) and p["has_t0"] is True
        assert p["lq_cmd"] is False and "off" in p["reason"]

    def test_flag_on_capable_dll_five_is_221(self, env):
        env.mp.setenv("LADDER_221_V1", "1")
        p = cs.ladder_plan(5, dll_caps={"cap_lq": 1})
        assert p["groups"] == (2, 2, 1, 0)
        assert p["has_t0"] is False and p["lq_cmd"] is True
        assert "cap_lq=1" in p["reason"]

    @pytest.mark.parametrize("n", [1, 2, 3, 4, 6])
    def test_flag_on_other_sizes_keep_todays_plan(self, env, n):
        env.mp.setenv("LADDER_221_V1", "1")
        p = cs.ladder_plan(n, dll_caps={"cap_lq": 1})
        assert p["groups"] == cs.LADDER[n] and p["lq_cmd"] is False
        assert p["has_t0"] is (n >= 4)
        assert "ruled for 5 only" in p["reason"]

    @pytest.mark.parametrize("caps", [{}, {"cap_lq": 0}, {"cap_lq": "x"}, None])
    def test_flag_on_without_the_capability_is_todays_plan(self, env, caps):
        env.mp.setenv("LADDER_221_V1", "1")
        if caps is None:      # read from the (absent) heartbeat file
            p = cs.ladder_plan(5)
        else:
            p = cs.ladder_plan(5, dll_caps=caps)
        assert p["groups"] == (1, 2, 1, 1) and p["lq_cmd"] is False
        assert "cap_lq missing" in p["reason"]

    def test_t0_follows_t0_target_pts_exactly_as_accept_setup_did(self, env):
        env.mp.setenv("T0_TARGET_PTS", "0")
        assert cs.ladder_plan(5)["has_t0"] is False

    def test_plan_fits_mirrors_the_dll_validation(self, env):
        assert cs.plan_fits({"groups": (2, 2, 1, 0)}, 5)
        assert not cs.plan_fits({"groups": (2, 2, 1, 0)}, 4)      # sum != contracts
        assert not cs.plan_fits({"groups": (0, 2, 2, 1)}, 5)      # lq1 < 1
        assert not cs.plan_fits({"groups": (2, 0, 2, 1)}, 5)      # group after an empty one
        assert not cs.plan_fits({"groups": (2, 2, 1)}, 5)
        assert not cs.plan_fits({"groups": None}, 5)
        assert cs.format_plan(cs.ladder_plan(5)) == "1/2/1/1+T0"
        assert cs.format_plan({"groups": (2, 2, 1, 0), "lq_cmd": True}) == "2/2/1"


class TestTheHeartbeat:
    def test_missing_stale_unreadable_or_old_dll_is_no_capability(self, env):
        assert cs.dll_capabilities()["cap_lq"] == 0                    # missing
        _write_state(env.export, cap=1)
        c = cs.dll_capabilities()
        assert c["cap_lq"] == 1 and c["ok"] is True
        _write_state(env.export, cap=1, age=cs.DLL_CAP_MAX_AGE_S + 5)  # stale
        assert cs.dll_capabilities()["cap_lq"] == 0
        assert "stale" in cs.dll_capabilities()["why"]
        _write_state(env.export, raw="{not json")                       # unreadable
        assert cs.dll_capabilities()["cap_lq"] == 0
        _write_state(env.export, cap=None)                              # pre-T-610 DLL
        c = cs.dll_capabilities()
        assert c["cap_lq"] == 0 and "Remote Build" in c["why"]
        _write_state(env.export, cap=0)
        assert cs.dll_capabilities()["cap_lq"] == 0

    def test_sierras_bare_inf_does_not_hide_the_capability(self, env):
        # 07-27: the DLL printed "inf" for high/low_during_pos when flat
        _write_state(env.export, raw='{"ts": 1, "high_during_pos": inf, '
                                     '"low_during_pos": -inf, "cap_lq": 1}')
        assert cs.dll_capabilities()["cap_lq"] == 1

    def test_the_path_follows_v9_export_dir(self, env):
        assert cs.sierra_state_path() == env.export / "sierra_state.json"
        env.mp.setenv("V9_EXPORT_DIR", str(env.export / "woodies_5min.json"))
        assert cs.sierra_state_path() == env.export / "sierra_state.json"


# ── 2. byte-identity with the pre-T-610 writer ────────────────────────────────

class TestByteIdenticalWhenNot221:
    @pytest.mark.parametrize("runner_trail", ["0", "1"])
    @pytest.mark.parametrize("setup", SETUPS, ids=SETUP_IDS)
    def test_flag_off(self, env, setup, runner_trail):
        env.mp.setenv("RUNNER_TRAIL_V2", runner_trail)
        _write_state(env.export, cap=1)   # even a capable DLL changes nothing while OFF
        new, old = _both(env, setup)
        assert _dumps(new) == _dumps(old)
        assert new["contracts"] == 5 and "lq1" not in new

    @pytest.mark.parametrize("day", ["Trend_Normal", "Normal", None])
    def test_flag_off_with_runner_by_daytype(self, env, day):
        import backend.v9.services.trade_context as tc
        env.mp.setenv("RUNNER_BY_DAYTYPE_V1", "1")
        env.mp.setattr(tc, "get_live_day_type", lambda: day)
        new, old = _both(env, SETUP_LONG)
        assert _dumps(new) == _dumps(old)

    @pytest.mark.parametrize("state", ["missing", "stale", "unreadable", "cap0", "old_dll"])
    @pytest.mark.parametrize("setup", SETUPS, ids=SETUP_IDS)
    def test_flag_on_without_capability(self, env, setup, state, caplog):
        env.mp.setenv("LADDER_221_V1", "1")
        if state == "stale":
            _write_state(env.export, cap=1, age=600)
        elif state == "unreadable":
            _write_state(env.export, raw="{\"cap_lq\": 1, broken")
        elif state == "cap0":
            _write_state(env.export, cap=0)
        elif state == "old_dll":
            _write_state(env.export, cap=None)
        with caplog.at_level("WARNING", logger="sierra_command"):
            new, old = _both(env, setup)
        assert _dumps(new) == _dumps(old)
        assert "lq1" not in new
        assert "[SierraCmd] LADDER 5c fallback 1/2/1/1+T0 (DLL cap_lq missing" in caplog.text

    @pytest.mark.parametrize("n", [3, 4, 6])
    def test_flag_on_other_sizes(self, env, n):
        env.mp.setenv("LADDER_221_V1", "1")
        env.mp.setenv("FIXED_CONTRACTS_5", "0")
        env.mp.setenv("FIXED_CONTRACTS_%d" % n, "1")
        _write_state(env.export, cap=1)
        new, old = _both(env, SETUP_LONG)
        assert _dumps(new) == _dumps(old)
        assert new["contracts"] == n and "lq1" not in new

    def test_todays_five_is_t0_t1x2_t2_and_a_stop_only_runner(self, env):
        """The exact shape Michael objected to, pinned without git: T0 at
        entry+3 (1c), T1 (2c), T2 (1c), T3 leg stop-only (RUNNER_TRAIL_V2)."""
        s = copy.deepcopy(SETUP_LONG)
        p = sc.command_from_setup(s, trade_id="T610-TODAY", account="Sim1", mode="demo")
        assert p["contracts"] == 5 and "lq1" not in p
        assert p["target_price"] == 7603.0
        assert (p["context"]["t2"], p["context"]["t3"], p["context"]["t4"]) == (
            7605.0, 7612.0, None)
        assert s["t0"] == 7603.0 and s["runner_stop_only"] == "c4"
        assert list(_clean(p)) == ["op", "action", "trade_id", "direction", "price",
                                   "contracts", "stop_price", "target_price",
                                   "account", "mode", "context"]


# ── 3. the 2/2/1 PLACE ────────────────────────────────────────────────────────

class TestThe221Place:
    @pytest.mark.parametrize("setup", SETUPS, ids=SETUP_IDS)
    def test_lq_221_t1_t2_t3_no_t0_no_t4(self, env, setup, caplog):
        env.mp.setenv("LADDER_221_V1", "1")
        _write_state(env.export, cap=1)
        s = copy.deepcopy(setup)
        with caplog.at_level("WARNING", logger="sierra_command"):
            p = sc.command_from_setup(s, trade_id="T610A", account="Sim1", mode="demo")
        assert p["contracts"] == 5
        assert (p["lq1"], p["lq2"], p["lq3"], p["lq4"]) == (2, 2, 1, 0)
        assert p["target_price"] == setup["t1"]          # group 1: 2c @ T1
        assert p["context"]["t2"] == setup["t2"]         # group 2: 2c @ T2
        assert p["context"]["t3"] == setup["t3"]         # group 3: 1c @ T3
        assert p["context"]["t4"] is None                # no 4th group at all
        assert "t0" not in s, "no T0 scalp on the 2/2/1 plan"
        assert "runner_stop_only" not in s and "runner_by_daytype" not in s
        assert ("[SierraCmd] LADDER_221 5c → 2/2/1 T1/T2/T3 (no T0) — DLL cap_lq=1"
                in caplog.text)
        keys = list(p)
        i = keys.index("contracts")
        assert keys[i + 1:i + 5] == ["lq1", "lq2", "lq3", "lq4"]

    def test_the_wire_file_parses_as_221_in_the_dll(self, env):
        env.mp.setenv("LADDER_221_V1", "1")
        _write_state(env.export, cap=1)
        sc.command_from_setup(copy.deepcopy(SETUP_LONG), trade_id="T610W",
                              account="Sim1", mode="demo")
        raw = (env.tmp / "signals" / "trade_command.json").read_text()
        wire = json.loads(raw)
        assert _dll_parse_lq(raw, wire["contracts"]) == (2, 2, 1, 0)
        # every other old-style command: the DLL keeps its table
        env.mp.setenv("LADDER_221_V1", "0")
        env.mp.setenv("MEMS26_SIGNALS_DIR", str(env.tmp / "signals2"))
        sc.command_from_setup(copy.deepcopy(SETUP_LONG), trade_id="T610W2",
                              account="Sim1", mode="demo")
        raw2 = (env.tmp / "signals2" / "trade_command.json").read_text()
        assert _dll_parse_lq(raw2, 5) is None

    @pytest.mark.parametrize("extra,expect", [
        ({"lq1": 2, "lq2": 2, "lq3": 1, "lq4": 0}, (2, 2, 1, 0)),
        ({"lq1": 2, "lq2": 2, "lq3": 1}, None),                 # lq4 missing
        ({"lq1": 2, "lq2": 2, "lq3": 1, "lq4": None}, None),    # null
        ({"lq1": 2, "lq2": 2, "lq3": 2, "lq4": 0}, None),       # sums to 6, contracts 5
        ({"lq1": 0, "lq2": 2, "lq3": 2, "lq4": 1}, None),       # lq1 < 1
        ({"lq1": 2, "lq2": 0, "lq3": 2, "lq4": 1}, None),       # a gap
        ({"lq1": -1, "lq2": 3, "lq3": 2, "lq4": 1}, None),      # negative
        ({"lq1": "2", "lq2": 2, "lq3": 1, "lq4": 0}, None),     # a string
    ])
    def test_the_dll_validation_rules(self, extra, expect):
        payload = {"op": "PLACE", "action": "BUY", "contracts": 5}
        payload.update(extra)
        assert _dll_parse_lq(json.dumps(payload, indent=2), 5) == expect


# ── 4. decided ONCE, recorded on the row ──────────────────────────────────────

@pytest.fixture
def tm(env):
    """A real TradeManager on in-memory SQLite (same pattern as test_trade_manager)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.v9.db.session import Base
    from backend.v9.services.trade_manager.manager import TradeManager
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    db = sessionmaker(bind=eng)()
    m = TradeManager(db, event_emitter=MagicMock())
    yield m
    db.rollback()
    db.close()


class TestRecordedOnce:
    def test_flag_off_row_is_exactly_todays(self, env, tm):
        _write_state(env.export, cap=1)
        tid = tm.accept_setup(copy.deepcopy(SETUP_LONG), "demo")
        q = tm._get_trade(tid).quality
        assert q["contracts"] == 5
        assert q["has_t0"] is True and q["t0_target_pts"] == 3.0
        assert "ladder_groups" not in q and "ladder_reason" not in q
        assert cs.recorded_plan(tid) is None

    def test_221_is_recorded_and_the_place_follows_the_record(self, env, tm):
        env.mp.setenv("LADDER_221_V1", "1")
        _write_state(env.export, cap=1)
        s = copy.deepcopy(SETUP_LONG)
        tid = tm.accept_setup(s, "demo")
        q = tm._get_trade(tid).quality
        assert q["ladder_groups"] == [2, 2, 1, 0]
        assert q["has_t0"] is False and "t0_target_pts" not in q
        assert "cap_lq=1" in q["ladder_reason"]
        assert s["ladder_plan"]["groups"] == (2, 2, 1, 0)
        assert cs.recorded_plan(tid)["groups"] == (2, 2, 1, 0)
        # the heartbeat vanishes between accept and PLACE: the PLACE must NOT
        # re-decide — it carries the trade's recorded plan (the gateway passes
        # a COPY of the setup, so the plan travels by trade id)
        (env.export / "sierra_state.json").unlink()
        cs._CAP_CACHE.clear()
        p = sc.command_from_setup(copy.deepcopy(SETUP_LONG), trade_id=str(tid),
                                  account="Sim1", mode="demo")
        assert (p["lq1"], p["lq2"], p["lq3"], p["lq4"]) == (2, 2, 1, 0)
        assert p["target_price"] == 7605.0

    def test_a_legacy_record_is_never_upgraded_at_place_time(self, env, tm):
        env.mp.setenv("LADDER_221_V1", "1")          # on, but the DLL is not capable yet
        tid = tm.accept_setup(copy.deepcopy(SETUP_LONG), "demo")
        q = tm._get_trade(tid).quality
        assert q["ladder_groups"] == [1, 2, 1, 1]
        assert q["has_t0"] is True and q["t0_target_pts"] == 3.0
        assert "cap_lq missing" in q["ladder_reason"]
        _write_state(env.export, cap=1)              # capability appears before the PLACE
        p = sc.command_from_setup(copy.deepcopy(SETUP_LONG), trade_id=str(tid),
                                  account="Sim1", mode="demo")
        assert "lq1" not in p and p["target_price"] == 7603.0   # today's T0 shape

    def test_a_record_that_no_longer_fits_the_size_is_not_sent(self, env, caplog):
        env.mp.setenv("LADDER_221_V1", "1")
        cs.remember_plan("T610M", {"groups": (2, 2, 1, 0), "has_t0": False,
                                   "lq_cmd": True, "reason": "x"})
        env.mp.setenv("FIXED_CONTRACTS_5", "0")
        env.mp.setenv("FIXED_CONTRACTS_4", "1")      # the size moved 5 → 4
        _write_state(env.export, cap=1)
        p = sc.command_from_setup(copy.deepcopy(SETUP_LONG), trade_id="T610M",
                                  account="Sim1", mode="demo")
        assert p["contracts"] == 4 and "lq1" not in p


# ── 5. every consumer follows the TRADE's ladder ──────────────────────────────

Q221 = {"contracts": 5, "ladder_groups": [2, 2, 1, 0], "has_t0": False,
        "ladder_reason": "LADDER_221_V1 · DLL cap_lq=1"}
Q_TODAY5 = {"contracts": 5, "has_t0": True, "t0_target_pts": 3.0}


class TestLegModel:
    def test_contracts_map_to_t1_t1_t2_t2_t3(self):
        groups, off = cs.contract_ladder_of(Q221, 5)
        assert groups == (2, 2, 1, 0) and off == 1
        assert [cs.target_index_for_contract(i, 5, groups=groups) for i in range(5)] == [
            0, 0, 1, 1, 2]                    # OCO group: C1,C2→g0 · C3,C4→g1 · C5→g2
        assert [min(cs.target_index_for_contract(i, 5, groups=groups) + off, 3)
                for i in range(5)] == [1, 1, 2, 2, 3]   # leg: T1 T1 T2 T2 T3
        assert cs.ladder_for_trade(Q221, 5) == (2, 2, 1, 0)
        assert cs.ladder_leg_count(Q221, 5) == 3      # "כאילו זה 3 חוזים"
        assert cs.leg_quantities(Q221, 5) == [0, 2, 2, 1]

    def test_rows_without_a_record_map_exactly_as_before(self):
        assert cs.contract_ladder_of(Q_TODAY5, 5) == (None, 0)
        assert cs.ladder_for_trade(Q_TODAY5, 5) == cs.LADDER[5] == (1, 2, 1, 1)
        assert [cs.target_index_for_contract(i, 5) for i in range(5)] == [0, 1, 1, 2, 3]
        assert cs.ladder_leg_count(Q_TODAY5, 5) == 5
        assert cs.leg_quantities(Q_TODAY5, 5) is None
        assert cs.ladder_for_trade(types.SimpleNamespace(quality=MagicMock()), 5) == (1, 2, 1, 1)

    @pytest.mark.parametrize("bad", [[2, 2, 1], [2, 2, 2, 0], [0, 2, 2, 1],
                                     [2, 2, -1, 2], "x", None, 7])
    def test_a_damaged_record_falls_back_to_today(self, bad):
        q = {"ladder_groups": bad, "has_t0": False}
        assert cs.ladder_for_trade(q, 5) == cs.LADDER[5]
        assert cs.contract_ladder_of(q, 5) == (None, 0)

    def test_sql_text_values_from_the_phone_query(self):
        # mobile_monitor selects has_t0 / t0_target_pts with ->> (text)
        assert cs.contract_ladder_of({"ladder_groups": [2, 2, 1, 0], "has_t0": "false",
                                      "t0_target_pts": None}, 5) == ((2, 2, 1, 0), 1)
        assert cs.contract_ladder_of({"ladder_groups": [1, 2, 1, 1], "has_t0": "true",
                                      "t0_target_pts": "3.0"}, 5) == ((1, 2, 1, 1), 0)
        assert cs.contract_ladder_of({"ladder_groups": "[2, 2, 1, 0]"}, 5) == ((2, 2, 1, 0), 1)

    def test_open_contracts(self):
        fills = [{"kind": "T1", "qty": 2, "price": 7605.0},
                 {"kind": "T2", "qty": 2, "price": 7612.0}]
        assert cs.open_contracts(5, fills, [True, True, False], quality=Q221) == (1, "exit_fills")
        assert cs.open_contracts(5, None, [True, True, False], quality=Q221) == (1, "ladder_hits")
        assert cs.open_contracts(5, None, [True, False, False], quality=Q221) == (3, "ladder_hits")
        assert cs.open_contracts(5, None, [True, True, True], quality=Q221) == (0, "ladder_hits")
        # no record: today's 1/2/1/1 estimate, unchanged (T1 2c + T2 1c)
        assert cs.open_contracts(5, None, [True, True, False]) == (2, "ladder_hits")
        assert cs.open_contracts(5, None, [True, True, False], quality=Q_TODAY5) == (
            2, "ladder_hits")


def _trade221(**over):
    t = types.SimpleNamespace(
        id=6100, direction="LONG", mode="demo", entry_price=7600.0, stop=7590.0,
        t1=7605.0, t2=7612.0, t3=7620.0, t4=None,
        t1_hit_ts=None, t2_hit_ts=None, t3_hit_ts=None, t4_hit_ts=None,
        stop_hit_ts=None, exit_ts=None, exit_price=None, exit_reason=None,
        state="FILLED", pnl_usd=None, pnl_r=None, outcome=None, cross_context=[],
        quality=dict(Q221, initial_stop=7590.0, sierra_order_id=20001,
                     c1_target_id=20002, c1_stop_id=20003, c2_target_id=20004,
                     c2_stop_id=20005, c3_target_id=20006, c3_stop_id=20007),
    )
    for k, v in over.items():
        setattr(t, k, v)
    return t


def _mgr(trade, state=None):
    """Real state machine + real P&L math; DB/emitter/IO stubbed (as in #749's test)."""
    from backend.v9.services.trade_manager.manager import TradeManager
    from backend.v9.services.trade_manager.state_machine import (
        TradeState, TradeStateMachine)
    m = TradeManager.__new__(TradeManager)
    machine = TradeStateMachine(state or TradeState.FILLED)
    m._machines = {trade.id: machine}
    m._db = MagicMock()
    m._emitter = MagicMock()
    m._log_management = MagicMock()
    m._append_snapshot = MagicMock()
    m._apply_smart_be_after_t1 = MagicMock()
    m._get_trade = lambda tid: trade
    m._get_machine = lambda t: machine
    return m


def _ts(sec):
    return datetime(2026, 10, 20, 17, 30, sec, tzinfo=timezone.utc)


class TestTheBooks:
    @pytest.mark.parametrize("with_qty", [True, False], ids=["sierra_qty", "ladder_weight"])
    def test_t1x2_t2x2_t3x1_and_t3_closes_the_trade(self, env, with_qty):
        """BE_AFTER_REAL_T1_V1=1 + T0_TARGET_PTS=3 are ON (today's .env) — a
        2/2/1 trade has no T0, so the DLL's T1 is NOT remapped to T0."""
        t = _trade221()
        m = _mgr(t)
        q = (lambda n: n) if with_qty else (lambda n: None)
        m.on_target_hit(t.id, "T1", fill_ts=_ts(1), fill_price=7605.0,
                        fill_qty=q(2), order_id=20002)
        assert t.state == "PARTIAL" and t.t1_hit_ts is not None
        assert t.pnl_usd == 2 * 5.0 * 5                       # 2c × 5pt
        m.on_target_hit(t.id, "T2", fill_ts=_ts(2), fill_price=7612.0,
                        fill_qty=q(2), order_id=20004)
        assert t.state == "PARTIAL"
        assert t.pnl_usd == 50.0 + 2 * 12.0 * 5               # + 2c × 12pt
        m.on_target_hit(t.id, "T3", fill_ts=_ts(3), fill_price=7620.0,
                        fill_qty=q(1), order_id=20006)
        assert t.state == "CLOSED" and t.exit_reason == "T3_HIT", (
            "the 2/2/1 trade's T3 is its LAST leg — it must close like a 3-lot")
        assert t.pnl_usd == 50.0 + 120.0 + 1 * 20.0 * 5       # 270
        assert [(f["kind"], f["qty"]) for f in t.quality["exit_fills"]] == [
            ("T1", 2), ("T2", 2), ("T3", 1)]

    def test_without_a_record_a_five_lot_t3_still_waits_as_before(self, env):
        """Pin of today's behavior for every historical 5-lot row."""
        t = _trade221(quality={"contracts": 5, "initial_stop": 7590.0})
        m = _mgr(t)
        for k, px, sec in (("T1", 7605.0, 1), ("T2", 7612.0, 2), ("T3", 7620.0, 3)):
            m.on_target_hit(t.id, k, fill_ts=_ts(sec), fill_price=px, fill_qty=1)
        assert t.state == "PARTIAL"

    def test_pnl_weights_from_the_hit_columns(self, env):
        from backend.v9.services.trade_manager.state_machine import TradeState
        now = datetime(2026, 10, 20, 18, 0, tzinfo=timezone.utc)
        t = _trade221(state="CLOSED", exit_reason="T3_HIT", exit_price=7620.0,
                      t1_hit_ts=now, t2_hit_ts=now, t3_hit_ts=now)
        m = _mgr(t, TradeState.CLOSED)
        m._calculate_pnl(t)
        assert t.pnl_usd == 2 * 5 * 5 + 2 * 12 * 5 + 1 * 20 * 5      # 270
        # the same row WITHOUT the record is booked exactly as today (1/2/1/1
        # weights, the fifth contract at the T3 exit fill) — not silently 2/2/1
        t2 = _trade221(state="CLOSED", exit_reason="T3_HIT", exit_price=7620.0,
                       t1_hit_ts=now, t2_hit_ts=now, t3_hit_ts=now,
                       quality={"contracts": 5, "initial_stop": 7590.0})
        _mgr(t2, TradeState.CLOSED)._calculate_pnl(t2)
        assert t2.pnl_usd == 1 * 5 * 5 + 2 * 12 * 5 + 1 * 20 * 5 + 1 * 20 * 5   # 345

    def test_the_order_keys_are_the_no_t0_ones(self):
        from backend.v9.services.trade_manager.manager import TradeManager
        t = _trade221()
        assert TradeManager._target_order_key(t, "t1") == "c1_target_id"
        assert TradeManager._target_order_key(t, "t3") == "c3_target_id"
        assert [TradeManager._ladder_group_for(t, k) for k in ("T1", "T2", "T3")] == [0, 1, 2]


class TestPanelReconcilerSystem6:
    @pytest.fixture
    def db(self, env):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from backend.v9.db.session import Base
        eng = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(eng)
        s = sessionmaker(bind=eng)()
        yield s
        s.rollback()
        s.close()

    def _row(self, db, quality):
        from backend.v9.db.models.trades import V9Trade
        now = datetime.now(timezone.utc)
        r = V9Trade(mode="demo", firing_system=2, direction="LONG", state="PARTIAL",
                    entry_ts=now - timedelta(minutes=5), entry_price=7600.0,
                    stop=7600.0, t1=7605.0, t2=7612.0, t3=7620.0, t1_hit_ts=now,
                    cross_context=[], quality=quality)
        db.add(r)
        db.flush()
        return r

    def test_the_active_card_rows_follow_the_221_record(self, db):
        from backend.v9.api.v9.trades import get_active_trade
        self._row(db, dict(Q221))
        out = get_active_trade(db=db)
        rows = out["contracts"]
        assert [r["id"] for r in rows] == ["C1", "C2", "C3", "C4", "C5"]
        assert [r["target_price"] for r in rows] == [7605.0, 7605.0, 7612.0, 7612.0, 7620.0]
        assert [r["status"] for r in rows] == ["HIT_TARGET", "HIT_TARGET", "OPEN", "OPEN", "OPEN"]
        assert out["summary"] == "2/5 hit"

    def test_the_active_card_without_a_record_is_unchanged(self, db):
        from backend.v9.api.v9.trades import get_active_trade
        self._row(db, dict(Q_TODAY5))
        rows = get_active_trade(db=db)["contracts"]
        # today's map: C1 on T0 (no level stored), C2-C3 on T1, C4 on T2, C5 on T3
        assert [r["target_price"] for r in rows] == [None, 7605.0, 7605.0, 7612.0, 7620.0]

    def test_the_phone_builds_its_rows_the_same_way(self):
        src = (REPO / "backend" / "v9" / "api" / "v9" / "mobile_monitor.py").read_text(
            encoding="utf-8")
        assert "quality->'ladder_groups' AS ladder_groups" in src
        assert "quality->>'has_t0' AS has_t0" in src
        assert "quality->>'t0_target_pts' AS t0_target_pts" in src
        assert "_lad_groups, _lad_off = contract_ladder_of(r, _n)" in src
        assert "target_index_for_contract(_i, _n, groups=_lad_groups)" in src
        assert "quality=r)" in src


    def _reconcile(self, monkeypatch, quality, sierra_qty):
        import backend.v9.services.sierra_position_reconciler as rec
        import backend.v9.services.phone_alert as pa
        monkeypatch.setattr(rec, "_sierra_state_qty", lambda: sierra_qty)
        monkeypatch.setattr(rec, "_sierra_state_working", lambda: 2)
        monkeypatch.setattr(rec, "_unprotected_contracts", lambda q: None)
        monkeypatch.setattr(rec, "_position_mismatch_block", False)
        monkeypatch.setattr(pa, "push", lambda *a, **k: None)
        now = datetime.now(timezone.utc)
        t = types.SimpleNamespace(id=6101, mode="demo", state="PARTIAL", direction="LONG",
                                  t1_hit_ts=now, t2_hit_ts=now, t3_hit_ts=None,
                                  quality=dict(quality))
        fake_tm = types.SimpleNamespace(get_active_trades=lambda *a, **k: [t])
        return rec.reconcile_position(fake_tm)

    def test_the_reconciler_counts_the_221_legs(self, monkeypatch):
        # T1 (2c) + T2 (2c) banked, no T-62 ledger: ONE contract is left
        ok, msg = self._reconcile(monkeypatch, Q221, 1)
        assert ok and msg.startswith("MATCH: TM=1 Sierra=1"), msg

    def test_the_reconciler_without_a_record_counts_as_before(self, monkeypatch):
        # today's 1/2/1/1 estimate for the same flags: T1 2c + T2 1c → 2 left
        ok, msg = self._reconcile(monkeypatch, {"contracts": 5}, 2)
        assert ok and msg.startswith("MATCH: TM=2 Sierra=2"), msg

    def test_system6_sees_no_size_or_target_mismatch(self, env):
        from backend.v9.systems.system6_supervisor import diagnose_trade
        env.mp.setenv("LADDER_221_V1", "1")
        _write_state(env.export, cap=1)
        p = sc.command_from_setup(copy.deepcopy(SETUP_LONG), trade_id="T610S6",
                                  account="Sim1", mode="demo")
        placed = {"t1": p["target_price"], "t2": p["context"]["t2"],
                  "t3": p["context"]["t3"]}           # what bar_level_detector inv-13 reads
        rep = diagnose_trade(
            trade={"direction": "LONG", "entry_price": 7600.0, "stop": 7590.0,
                   "t1": 7605.0, "t2": 7612.0, "t3": 7620.0, "contracts": 5,
                   "sierra_targets": placed},
            atr=8.0, expected_contracts=cs.ruled_contracts())
        codes = [i.code for i in rep.issues]
        assert "contract_mismatch" not in codes
        assert not [c for c in codes if c.startswith("target_divergence")], codes


# ── 6. the fill path: ENTRY echo + ENTRY_FILL (T-436d ships in the same build) ──

class _TM:
    def __init__(self, *trades):
        self.trades = list(trades)
        self.calls = []
        self._db = MagicMock()

    def _get_trade(self, tid):
        return next((t for t in self.trades if t.id == tid), None)

    def get_active_trades(self, *a, **k):
        return list(self.trades)

    def set_entry_fill_price(self, trade_id, price):
        self.calls.append(("set_entry_fill_price", trade_id, price))
        self._get_trade(trade_id).entry_price = price
        return 0.25

    def on_fill(self, trade_id, price):
        self.calls.append(("on_fill", trade_id, price))

    def set_sierra_order_ids(self, trade_id, ids):
        self.calls.append(("set_sierra_order_ids", trade_id))


def _demo_trade(tid, parent, quality=None):
    q = {"sierra_order_id": parent, "contracts": 5}
    q.update(quality or {})
    return types.SimpleNamespace(id=tid, mode="demo", state="PENDING", direction="LONG",
                                 entry_price=7600.0, quality=q)


class TestTheFillPath:
    def test_unmapped_entry_fill_finds_its_own_trade_not_the_latest(self, env):
        from backend.v9.services.fill_poller import FillPoller
        mine, latest = _demo_trade(7001, 31001), _demo_trade(7002, 31002)
        tm = _TM(mine, latest)
        p = FillPoller(trade_manager=tm)                  # fresh map: a restart
        p._process_fill({"kind": "ENTRY_FILL", "order_id": 31001, "price": 7600.75,
                         "contracts": 5, "ts": 1792500000})
        assert tm.calls == [("set_entry_fill_price", 7001, 7600.75)]
        assert latest.entry_price == 7600.0, "the I-58 guess would have rewritten #7002"
        assert p._orphan_count == 0

    def test_unmapped_entry_fill_with_no_owner_is_dropped_not_an_orphan(self, env, caplog):
        from backend.v9.services.fill_poller import FillPoller
        other = _demo_trade(7003, 31003)
        tm = _TM(other)
        p = FillPoller(trade_manager=tm)
        with caplog.at_level("WARNING", logger="fill_poller"):
            p._process_fill({"kind": "ENTRY_FILL", "order_id": 99999, "price": 7601.0,
                             "contracts": 5, "ts": 1792500000})
        assert tm.calls == [] and other.entry_price == 7600.0
        assert p._orphan_count == 0 and p.get_orphan_fills() == []
        assert "ORPHAN" not in caplog.text and "ENTRY_FILL for parent order 99999" in caplog.text

    def _entry(self, lq, lq_cmd=1):
        return {"kind": "ENTRY", "ts": 1792500000, "order_id": 32001,
                "c1_target_id": 32002, "c1_stop_id": 32003, "c2_target_id": 32004,
                "c2_stop_id": 32005, "c3_target_id": 32006, "c3_stop_id": 32007,
                "c4_target_id": 0, "c4_stop_id": 0, "price": 7600.0, "contracts": 5,
                "direction": "LONG", "lq": lq, "lq_cmd": lq_cmd}

    def test_entry_echo_that_matches_the_record_is_quiet(self, env, monkeypatch, caplog):
        from backend.v9.services.fill_poller import FillPoller
        import backend.v9.services.phone_alert as pa
        pushes = []
        monkeypatch.setattr(pa, "push", lambda *a, **k: pushes.append(a))
        t = _demo_trade(7010, 32001, Q221)
        p = FillPoller(trade_manager=_TM(t))
        p.register_order(32001, 7010)
        with caplog.at_level("INFO", logger="fill_poller"):
            p._process_fill(self._entry("2/2/1/0"))
        assert "LADDER SHAPE MISMATCH" not in caplog.text and pushes == []
        assert "ladder confirmed by the broker" in caplog.text

    def test_entry_echo_that_disagrees_is_critical_and_pushed(self, env, monkeypatch, caplog):
        from backend.v9.services.fill_poller import FillPoller
        import backend.v9.services.phone_alert as pa
        pushes = []
        monkeypatch.setattr(pa, "push", lambda *a, **k: pushes.append(a))
        t = _demo_trade(7011, 32001, Q221)
        p = FillPoller(trade_manager=_TM(t))
        p.register_order(32001, 7011)
        with caplog.at_level("WARNING", logger="fill_poller"):
            p._process_fill(self._entry("1/2/1/1", lq_cmd=0))   # the DLL kept its table
        assert "LADDER SHAPE MISMATCH trade 7011: books 2/2/1/0 vs broker 1/2/1/1" in caplog.text
        assert pushes and pushes[0][0] == "ladder_mismatch_7011"

    def test_no_echo_or_no_record_is_a_no_op(self, env, monkeypatch, caplog):
        from backend.v9.services.fill_poller import FillPoller
        import backend.v9.services.phone_alert as pa
        pushes = []
        monkeypatch.setattr(pa, "push", lambda *a, **k: pushes.append(a))
        t = _demo_trade(7012, 32001)                         # flag-off row: no record
        p = FillPoller(trade_manager=_TM(t))
        p.register_order(32001, 7012)
        p._process_fill(self._entry("1/2/1/1", lq_cmd=0))
        e = self._entry("x")
        e.pop("lq")
        p._process_fill(e)                                   # pre-T-610 DLL: no echo
        assert pushes == []


# ── 7. the DLL source (nobody can compile it before the Remote Build) ─────────

def _cpp():
    return CPP.read_text(encoding="utf-8", errors="ignore")


def _strip_cpp(src):
    """Remove comments, string and char literals — what is left is code shape."""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif c in "\"'":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            out.append(c + c)
            i = j + 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _snprintf_call(src, marker):
    """(format string, n_args_after_format) of the snprintf call containing `marker`."""
    m = src.index(marker)
    start = src.rindex("snprintf(", 0, m) + len("snprintf(")
    args, depth, cur, i = [], 0, [], start
    while True:
        c = src[i]
        if src.startswith("//", i):
            i = src.index("\n", i)
            continue
        if c in "\"'":
            j = i + 1
            while src[j] != c:
                j += 2 if src[j] == "\\" else 1
            cur.append(src[i:j + 1])
            i = j + 1
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            if depth == 0:
                args.append("".join(cur).strip())
                break
            depth -= 1
        elif c == "," and depth == 0:
            args.append("".join(cur).strip())
            cur = []
            i += 1
            continue
        cur.append(c)
        i += 1
    fmt = "".join(re.findall(r'"((?:[^"\\]|\\.)*)"', args[2]))
    return fmt, len(args) - 3


_SPEC = re.compile(r"%(?!%)[-+ #0]*\d*(?:\.\d+)?(?:ll|l|hh|h|z)?[diouxXfFeEgGsc]")


class TestTheDllSource:
    def test_lq_is_parsed_validated_and_falls_back_to_the_table(self):
        src = _cpp()
        a = src.index("int lq[4] = {0, 0, 0, 0};")
        blk = src[a:src.index("s_SCNewOrder o;", a)]
        # the table is still there, first, unchanged
        assert "else if (contracts == 5) { lq[0]=1; lq[1]=2; lq[2]=1; lq[3]=1; }" in blk
        for k in ("lq1", "lq2", "lq3", "lq4"):
            assert '"\\"%s\\""' % k in blk, k
        for rule in ("cq_sum == contracts", "cq[0] >= 1", "cq[qi] < 0 || cq[qi] > 6",
                     "cq[qi - 1] == 0", "cmd_content[qp] < '0' || cmd_content[qp] > '9'"):
            assert rule in blk, rule
        assert (blk.index("if (contracts > 6) contracts = 6;")
                < blk.index("cq_sum == contracts") < blk.index("int lq_sum")), (
            "the override must sit after the clamp and before the order is sized")
        assert "lq[0] = cq[0]; lq[1] = cq[1]; lq[2] = cq[2]; lq[3] = cq[3];" in blk
        assert "lq_cmd = 1;" in blk
        assert "o.OrderQuantity = lq_sum;" in src

    def test_sierra_state_advertises_cap_lq(self):
        src = _cpp()
        i = src.index('"sierra_state.json"')
        blk = src[src.rindex("char sbuf[3072];", 0, i):i]
        assert '\\"cap_lq\\":1,' in blk
        fmt, n_args = _snprintf_call(src, '\\"cap_lq\\":1,')
        assert len(_SPEC.findall(fmt)) == n_args, "sierra_state.json printf arity"

    def test_the_entry_line_echoes_the_shape_with_matching_printf_arity(self):
        src = _cpp()
        assert '\\"lq\\":\\"%d/%d/%d/%d\\",\\"lq_cmd\\":%d}' in src
        fmt, n_args = _snprintf_call(src, '\\"kind\\":\\"ENTRY\\",\\"ts\\"')
        assert fmt.count("%lld") == 10
        assert len(_SPEC.findall(fmt)) == n_args == 18
        echo = json.loads('{"kind":"ENTRY","lq":"2/2/1/0","lq_cmd":1}')   # the line shape
        assert echo["lq"] == "2/2/1/0"

    def test_braces_and_parens_balance(self):
        code = _strip_cpp(_cpp())
        assert code.count("{") == code.count("}")
        assert code.count("(") == code.count(")")
        t610 = code[code.index("int lq_cmd = 0;"):code.index("int lq_sum")]
        assert t610.count("{") == t610.count("}") and t610.count("(") == t610.count(")")

    def test_regeneration_can_never_delete_it(self):
        sh = (REPO / "scripts" / "build_monolithic_cpp.sh").read_text(encoding="utf-8")
        line = [l for l in sh.splitlines() if l.startswith("MONOLITH_ONLY_MARKERS=")][0]
        assert '"cap_lq"' in line
        for f in ("v9_types.h", "v9_exports.h", "v9_woodies_export.h", "MES_AI_DataExport.cpp"):
            assert "cap_lq" not in (REPO / "sc_study" / f).read_text(errors="ignore"), (
                "the marker must exist ONLY in the monolith or the guard cannot fire")
        assert "cap_lq" in _cpp()


_HARNESS = r'''
#include <string>
#include <cstdio>
#include <cstdlib>
#include <ctime>
#include <fstream>
#include <iterator>
struct StubOrder {
    long long InternalOrderID, Target1InternalOrderID, Stop1InternalOrderID,
              Target2InternalOrderID, Stop2InternalOrderID, Target3InternalOrderID,
              Stop3InternalOrderID, Target4InternalOrderID, Stop4InternalOrderID;
};
int main(int, char** argv) {
    std::ifstream cmd_file(argv[1]);
    std::string cmd_content((std::istreambuf_iterator<char>(cmd_file)),
                             std::istreambuf_iterator<char>());
    @@PARSE_INT@@
    double entry_price = 7600.0;
    int    contracts   = parse_int("\"contracts\"");
    if (contracts <= 0) contracts = 3;
    bool is_buy = true;
    @@PLACE@@
    StubOrder o = {1, 2, 3, 4, 5, 6, 7, 0, 0};
    @@ENTRY@@
    printf("LQ %d %d %d %d SUM %d CMD %d\n", lq[0], lq[1], lq[2], lq[3], lq_sum, lq_cmd);
    fwrite(fb, 1, (size_t)fl, stdout);
    return 0;
}
'''


def test_the_t610_block_compiles_and_runs_natively(env, tmp_path):
    """The PLACE code, extracted VERBATIM from the monolith, compiled with
    -Wall -Wformat=2 (printf types vs the new lq args) and executed on the
    real wire file command_from_setup writes. Skips without a C++ compiler."""
    import shutil
    cxx = shutil.which("clang++") or shutil.which("c++") or shutil.which("g++")
    if cxx is None:
        pytest.skip("no C++ compiler on this machine")
    src = _cpp()

    def cut(start, end, s=0, incl=False):
        a = src.index(start, s)
        b = src.index(end, a)
        return src[a:b + (len(end) if incl else 0)], b

    parse_int, _ = cut("auto parse_int = [&](const char* key) -> int {", "};", incl=True)
    place, p_end = cut("int lq[4] = {0, 0, 0, 0};", "s_SCNewOrder o;")
    entry, _ = cut("char fb[2048];", "lq[0], lq[1], lq[2], lq[3], lq_cmd);", p_end, incl=True)
    cpp = tmp_path / "t610.cpp"
    cpp.write_text(_HARNESS.replace("@@PARSE_INT@@", parse_int)
                   .replace("@@PLACE@@", place).replace("@@ENTRY@@", entry),
                   encoding="utf-8")
    exe = tmp_path / "t610"
    r = subprocess.run([cxx, "-std=c++11", "-Wall", "-Wextra", "-Wformat=2",
                        "-Werror=format", "-o", str(exe), str(cpp)],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-2000:]
    assert "warning" not in r.stderr, r.stderr[-2000:]

    env.mp.setenv("LADDER_221_V1", "1")
    _write_state(env.export, cap=1)
    sc.command_from_setup(copy.deepcopy(SETUP_LONG), trade_id="T610CXX",
                          account="Sim1", mode="demo")
    wire = env.tmp / "signals" / "trade_command.json"
    out = subprocess.run([str(exe), str(wire)], capture_output=True, text=True).stdout
    head, _, line = out.partition("\n")
    assert head == "LQ 2 2 1 0 SUM 5 CMD 1"
    e = json.loads(line)
    assert (e["kind"], e["contracts"], e["lq"], e["lq_cmd"]) == ("ENTRY", 5, "2/2/1/0", 1)

    old = tmp_path / "old.json"           # an old-style 5-lot command: the table
    old.write_text(json.dumps({"op": "PLACE", "action": "BUY", "contracts": 5}, indent=2))
    out = subprocess.run([str(exe), str(old)], capture_output=True, text=True).stdout
    assert out.splitlines()[0] == "LQ 1 2 1 1 SUM 5 CMD 0"
    bad = tmp_path / "bad.json"           # inconsistent lq*: the table, never a naked lot
    bad.write_text(json.dumps({"op": "PLACE", "action": "BUY", "contracts": 5,
                               "lq1": 2, "lq2": 2, "lq3": 2, "lq4": 0}, indent=2))
    out = subprocess.run([str(exe), str(bad)], capture_output=True, text=True).stdout
    assert out.splitlines()[0] == "LQ 1 2 1 1 SUM 5 CMD 0"
