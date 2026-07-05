"""System 6 exit-signal engine — stall / opposite-patterns / failed-volume."""
import random

from backend.v9.systems.system6_exit_signals import (
    price_stall, opposite_patterns, failed_reaction_volume,
    evaluate_exit, ExitSignal,
)


def _bar(h, l):
    return {"h": h, "l": l}


# --- price_stall ---
def test_stall_fires_when_no_new_low_for_short():
    # SHORT: best low at bar 0, then 3 bars going nowhere (higher lows)
    bars = [_bar(7540, 7530), _bar(7539, 7533), _bar(7540, 7534), _bar(7541, 7535)]
    s = price_stall(direction="SHORT", bars=bars, lookback=6, stall_bars=3)
    assert s.fired and s.score > 0


def test_stall_quiet_when_making_new_lows():
    bars = [_bar(7540, 7535), _bar(7538, 7532), _bar(7536, 7529), _bar(7534, 7527)]
    s = price_stall(direction="SHORT", bars=bars, lookback=6, stall_bars=3)
    assert not s.fired  # last bar is the new low → progressing


def test_stall_long_side():
    bars = [_bar(7550, 7540), _bar(7549, 7541), _bar(7548, 7542), _bar(7549, 7543)]
    s = price_stall(direction="LONG", bars=bars, lookback=6, stall_bars=3)
    assert s.fired  # best high at bar 0, no new high since


# --- opposite_patterns ---
def test_opposite_fires_on_two_counter():
    s = opposite_patterns(trade_direction="SHORT",
                          recent_fire_directions=["LONG", "LONG", "SHORT"], min_count=2)
    assert s.fired and s.score == 1.0


def test_opposite_quiet_on_one_counter():
    s = opposite_patterns(trade_direction="SHORT",
                          recent_fire_directions=["LONG", "SHORT"], min_count=2)
    assert not s.fired


# --- failed_reaction_volume ---
def test_failed_volume_fires_near_level_with_weak_flow():
    s = failed_reaction_volume(direction="SHORT", price=7530.5, level=7530.0,
                               level_tol=2.0, flow_aligned=0.1, weak_below=0.4)
    assert s.fired and s.score > 0


def test_failed_volume_quiet_when_flow_confirms():
    s = failed_reaction_volume(direction="SHORT", price=7530.5, level=7530.0,
                               level_tol=2.0, flow_aligned=0.8, weak_below=0.4)
    assert not s.fired


def test_failed_volume_quiet_when_far_from_level():
    s = failed_reaction_volume(direction="SHORT", price=7545.0, level=7530.0,
                               level_tol=2.0, flow_aligned=0.1, weak_below=0.4)
    assert not s.fired


def test_failed_volume_fails_safe_without_data():
    assert failed_reaction_volume(direction="SHORT", price=7530, level=None,
                                  level_tol=2.0, flow_aligned=None).fired is False


# --- aggregate keeps per-signal detail + recommends ---
def test_evaluate_keeps_each_signal_separate():
    sigs = [
        price_stall(direction="SHORT",
                    bars=[_bar(7540, 7530), _bar(7539, 7533), _bar(7540, 7534), _bar(7541, 7535)],
                    stall_bars=3),
        opposite_patterns(trade_direction="SHORT",
                          recent_fire_directions=["LONG", "LONG"], min_count=2),
    ]
    ev = evaluate_exit(sigs)
    assert len(ev.signals) == 2
    assert len(ev.fired) == 2
    assert ev.recommend_exit
    assert ev.top_reason  # a concrete reason surfaced


def test_evaluate_no_exit_when_all_quiet():
    sigs = [opposite_patterns(trade_direction="SHORT",
                              recent_fire_directions=["SHORT"], min_count=2)]
    ev = evaluate_exit(sigs)
    assert not ev.recommend_exit


# --- fuzz: score always in [0,1], fired implies score>0 ---
def test_fuzz_score_bounds():
    rnd = random.Random(70)
    for _ in range(2000):
        bars = [_bar(round(rnd.uniform(7530, 7560), 2), round(rnd.uniform(7520, 7550), 2))
                for _ in range(rnd.randint(0, 8))]
        s = price_stall(direction=rnd.choice(["LONG", "SHORT"]), bars=bars,
                        lookback=6, stall_bars=rnd.randint(2, 4))
        assert 0.0 <= s.score <= 1.0
        if s.fired:
            assert s.score > 0


# --- counter_flow_wins (Michael's confirmed volume semantic) ---
from backend.v9.systems.system6_exit_signals import counter_flow_wins


def test_counter_flow_fires_when_buyers_win_on_short():
    # SHORT: CVD rising = buyers winning
    s = counter_flow_wins(direction="SHORT", cvd_series=[-11000, -9500, -8700],
                          window=2, threshold=1500)
    assert s.fired and s.score > 0


def test_counter_flow_quiet_when_our_side_leads_short():
    s = counter_flow_wins(direction="SHORT", cvd_series=[-8000, -9000, -10500],
                          window=2, threshold=1500)
    assert not s.fired  # CVD falling = sellers still winning


def test_counter_flow_long_side():
    s = counter_flow_wins(direction="LONG", cvd_series=[9000, 7500, 6800],
                          window=2, threshold=1500)
    assert s.fired  # CVD falling against a long = sellers winning


def test_counter_flow_fails_safe():
    assert counter_flow_wins(direction="SHORT", cvd_series=[1.0],
                             window=3, threshold=1500).fired is False
