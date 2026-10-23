"""T-640 F1 (23.10) · an entry that moves INTO yesterday's value after a rejected gap is not "beyond value".

23.10: open 7661 below yesterday's range (low 7677, value 7685.5–7714, POC 7698.25); the gap was rejected —
closes back above 7677 from 17:40. 18:05 TREND_STEP LONG @7686 was blocked by ELQ beyond_value (today's value).
"""
from backend.v9.systems.prior_value_target import toward_prior_value as T

PREV = dict(prev_vah=7714.0, prev_val=7685.5, prev_poc=7698.25, prev_high=7742.5, prev_low=7677.0)


def test_2310_1805_long_toward_yesterdays_value_is_admitted():
    ok, why = T("LONG", 7686.0, 7661.0, 7686.25, **PREV)
    assert ok and "toward value" in why


def test_the_counter_move_short_is_not_admitted():
    ok, why = T("SHORT", 7686.0, 7661.0, 7686.25, **PREV)
    assert not ok and "only a LONG" in why


def test_gap_not_rejected_yet_is_not_admitted():
    # 17:20: close 7654 still below yesterday's low 7677 — the gap is not rejected
    ok, why = T("LONG", 7656.0, 7661.0, 7654.0, **PREV)
    assert not ok and "not rejected" in why


def test_no_chasing_past_yesterdays_poc():
    ok, why = T("LONG", 7702.0, 7661.0, 7701.0, **PREV)
    assert not ok and "past yesterday's POC" in why


def test_open_inside_value_is_not_this_rule():
    ok, why = T("LONG", 7700.0, 7695.0, 7699.0, **PREV)
    assert not ok and "inside yesterday's value" in why


def test_gap_up_mirror_and_missing_high_low_fall_back_to_value_edges():
    p = dict(prev_vah=7714.0, prev_val=7685.5, prev_poc=7698.25)
    ok, _ = T("SHORT", 7710.0, 7730.0, 7712.0, **p)          # open above VAH, close back under VAH, short toward value
    assert ok
    ok2, why2 = T("SHORT", 7710.0, 7730.0, 7716.0, **p)      # close still above VAH ⇒ not rejected
    assert not ok2 and "not rejected" in why2


def test_bad_input_is_not_admitted():
    assert T("LONG", None, 7661.0, 7686.0, **PREV)[0] is False
    assert T("LONG", 7686.0, 7661.0, 7686.0, prev_vah=7685.5, prev_val=7714.0, prev_poc=7698.25)[0] is False
