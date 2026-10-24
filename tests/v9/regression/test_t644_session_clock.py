# -*- coding: utf-8 -*-
"""T-644 (24.10.2026) — the session clock (ET+7h) for the DST-mismatch weeks.

Israel leaves DST on 25.10.2026, the US on 01.11.2026: on 26–30.10 the cash session 09:30–16:00 ET is 15:30–22:00 IL.
The gateway's phase (dalton_playbook._resolve_phase), the tree's `hour`/`structure` features and the opening-range
guards compare the Israel clock with constants written for a 7-hour offset (16:30 / 16:45 / 17:30 / 21:00 / 22:00).
SESSION_CLOCK_V1=1 feeds them ET+7h instead. These tests pin:
  1. the session clock reads 16:30 at the open / 17:30 at the end of the IB / 21:00 / 22:00 on normal days AND in the
     mismatch weeks (autumn 2026, spring 2027);
  2. it equals the Israel wall clock on every normal-offset day (=> byte-identical behaviour on the recorded sessions);
  3. with the flag unset the old Israel clock is used (built OFF);
  4. the phases and the tree's 22:00 time cutoff fall where they always did, relative to the market.
"""
import datetime as dt
from zoneinfo import ZoneInfo

import pytest

from backend.v9.services import market_clock as mc
from backend.v9.services.dalton_playbook import _resolve_phase

ET = ZoneInfo("America/New_York")
IL = ZoneInfo("Asia/Jerusalem")


def _et(d, hh, mm):
    return dt.datetime.combine(dt.date.fromisoformat(d), dt.time(hh, mm), ET)


NORMAL = ["2026-10-23", "2026-11-02", "2026-09-21"]          # IL−ET = 7h
MISMATCH = ["2026-10-26", "2026-10-30", "2027-03-15", "2027-03-25"]   # IL−ET = 6h


@pytest.mark.parametrize("d", NORMAL + MISMATCH)
@pytest.mark.parametrize("hm,expect", [((9, 30), "16:30"), ((9, 45), "16:45"), ((10, 30), "17:30"),
                                       ((14, 0), "21:00"), ((15, 0), "22:00"), ((15, 59), "22:59")])
def test_session_clock_reads_the_constants_every_week(d, hm, expect):
    assert mc.session_hhmm(_et(d, *hm)) == expect


@pytest.mark.parametrize("d", NORMAL)
def test_session_clock_equals_il_clock_at_the_normal_offset(d):
    for h in range(9, 16):
        for m in (0, 30):
            t = _et(d, h, m)
            il = t.astimezone(IL)
            assert mc.session_clock(t) == il.replace(tzinfo=None)


@pytest.mark.parametrize("d", MISMATCH)
def test_il_clock_is_an_hour_early_in_the_mismatch_week(d):
    t = _et(d, 9, 30)
    assert t.astimezone(IL).strftime("%H:%M") == "15:30"     # the bug T-644 fixes
    assert mc.session_hhmm(t) == "16:30"


def test_flag_off_keeps_the_israel_clock(monkeypatch):
    monkeypatch.delenv("SESSION_CLOCK_V1", raising=False)
    t = _et("2026-10-26", 9, 30)
    c = mc.session_or_il_clock(t)
    assert c.tzinfo is not None and c.strftime("%H:%M") == "15:30"
    monkeypatch.setenv("SESSION_CLOCK_V1", "0")
    assert mc.session_or_il_clock(t).strftime("%H:%M") == "15:30"


def test_flag_on_uses_the_session_clock(monkeypatch):
    monkeypatch.setenv("SESSION_CLOCK_V1", "1")
    t = _et("2026-10-26", 9, 30)
    c = mc.session_or_il_clock(t)
    assert c.tzinfo is None and c.strftime("%H:%M") == "16:30"
    assert c.date() == dt.date(2026, 10, 26)                 # the session date, as the IL date was


def test_naive_input_is_read_as_utc():
    naive_utc = dt.datetime(2026, 10, 26, 13, 30)             # 13:30 UTC = 09:30 EDT
    assert mc.session_hhmm(naive_utc) == "16:30"


@pytest.mark.parametrize("d", NORMAL + MISMATCH)
@pytest.mark.parametrize("hm,phase", [((9, 30), "A"), ((9, 50), "B"), ((10, 30), "C"), ((13, 59), "C"),
                                      ((14, 0), "D"), ((15, 30), "D")])
def test_phases_relative_to_the_market(d, hm, phase):
    assert _resolve_phase(mc.session_hhmm(_et(d, *hm))) == phase


@pytest.mark.parametrize("d", MISMATCH)
def test_old_clock_misplaces_the_phases_in_the_mismatch_week(d):
    # documents the failure mode: on the Israel clock 10:30 ET (end of the IB) is still phase A
    assert _resolve_phase(_et(d, 10, 30).astimezone(IL).strftime("%H:%M")) == "A"


def test_tree_time_cutoff_fires_at_15_et_on_the_session_clock():
    from backend.v9.services import decision_tree as dt3
    tree = dt3.load_tree()
    for d in NORMAL + MISMATCH:
        hour = mc.session_clock(_et(d, 15, 0)).hour
        leaf, _path = dt3.walk(tree, {"hour": hour})
        assert leaf.get("leaf") == "SKIP" and leaf.get("id") == "time_cutoff", (d, hour, leaf)
        hour_before = mc.session_clock(_et(d, 14, 55)).hour
        leaf2, _ = dt3.walk(tree, {"hour": hour_before})
        assert leaf2.get("id") != "time_cutoff", (d, hour_before)


def test_gap_backfill_guard_reads_the_exchange_clock():
    import importlib.util, os
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    spec = importlib.util.spec_from_file_location("gap_backfill_t644", os.path.join(root, "scripts", "gap_backfill.py"))
    gb = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(gb)
    except SystemExit:
        pytest.skip("gap_backfill runs on import in this environment")
    assert gb.in_rth_il(_et("2026-10-26", 9, 35).astimezone(IL)) is True      # 15:35 IL in the mismatch week
    assert gb.in_rth_il(_et("2026-10-23", 9, 35).astimezone(IL)) is True      # 16:35 IL normally
    assert gb.in_rth_il(_et("2026-10-26", 8, 30).astimezone(IL)) is False
    assert gb.in_rth_il(_et("2026-10-26", 16, 15).astimezone(IL)) is False
