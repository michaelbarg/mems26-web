"""Property-based / fuzz invariants for the modules built 2026-07-03.

A different angle from the example-based tests: generate thousands of RANDOM
inputs (stdlib random, no hypothesis dependency) and assert the invariants that
must hold for EVERY input. This catches edge cases hand-picked examples miss —
it already surfaced the resolve_stop wrong-side-rung gap (now guarded).

Each test runs N_ITER cases with a fixed seed (reproducible). On failure the
offending case is printed.
"""
import random

from backend.v9.systems.stop_anchors.stop_resolver import resolve_stop
from backend.v9.systems.target_zones import cluster_levels, select_target_zones
from backend.v9.systems.day_direction import halt_proof_met
from backend.v9.services.reconcile import (
    reconcile_positions, AGREED_FLAT, IN_POSITION_OK, NAKED_STOP_SUSPECT,
    MISMATCH_ORPHAN_DB, MISMATCH_ORPHAN_TM, MISMATCH_PHANTOM_SLOT,
)

N_ITER = 3000
TICK = 0.25


def _on_grid(px):
    return abs((px / TICK) - round(px / TICK)) < 1e-6


# ---------------------------------------------------------------- stop_resolver
def test_stop_resolver_invariants_fuzz():
    rnd = random.Random(41)
    for _ in range(N_ITER):
        direction = rnd.choice(["LONG", "SHORT"])
        entry = round(rnd.uniform(7000, 8000) / TICK) * TICK
        atr = rnd.uniform(1.0, 25.0)
        family = rnd.choice(["CONT", "REV"])
        # rungs on BOTH sides (adversarial) + some None/zero
        rungs = []
        for _r in range(rnd.randint(0, 6)):
            rungs.append(rnd.choice([None, 0.0,
                                     round(rnd.uniform(entry - 40, entry + 40) / TICK) * TICK]))
        res = resolve_stop(direction=direction, entry_price=entry, rungs=rungs,
                           rung_names=[f"r{i}" for i in range(len(rungs))],
                           atr_5m=atr, family=family)
        assert res is not None
        # floor/cap are consistent
        assert res.floor_pts <= res.cap_pts, (entry, atr, family)
        if res.in_band and not res.rejected:
            # INVARIANT 1: stop on the protective side of entry
            if direction == "LONG":
                assert res.stop_price < entry, ("LONG stop not below entry", entry, res)
            else:
                assert res.stop_price > entry, ("SHORT stop not above entry", entry, res)
            # INVARIANT 2: risk within [floor, cap]
            assert res.floor_pts - 1e-6 <= res.risk_points <= res.cap_pts + 1e-6, res
            # INVARIANT 3: grid-aligned
            assert _on_grid(res.stop_price), res.stop_price


# ------------------------------------------------------------------ target_zones
def test_cluster_partition_invariants_fuzz():
    rnd = random.Random(42)
    for _ in range(N_ITER):
        n = rnd.randint(0, 12)
        levels = [(round(rnd.uniform(7400, 7700) / TICK) * TICK, f"l{i}") for i in range(n)]
        tol = rnd.uniform(0.25, 10.0)
        zones = cluster_levels(levels, tol_pts=tol)
        # INVARIANT 1: every input level accounted for exactly once
        assert sum(z.strength for z in zones) == len(levels), (levels, tol)
        # INVARIANT 2: zones sorted ascending and non-overlapping (gap > tol)
        for a, b in zip(zones, zones[1:]):
            assert b.low > a.high, (a, b)
            assert (b.low - a.high) > tol - 1e-9, (a, b, tol)
        # INVARIANT 3: low <= center <= high, strength >= 1
        for z in zones:
            assert z.low <= z.center <= z.high and z.strength >= 1, z
            # every member price lies inside [low, high]
            assert z.high - z.low <= (z.strength - 1) * tol + 1e-9 or z.strength == 1


def test_select_zones_beyond_t1_fuzz():
    rnd = random.Random(43)
    for _ in range(N_ITER):
        direction = rnd.choice(["LONG", "SHORT"])
        entry = round(rnd.uniform(7400, 7700) / TICK) * TICK
        t1 = entry + (rnd.uniform(2, 12) if direction == "LONG" else -rnd.uniform(2, 12))
        levels = [(round(rnd.uniform(7350, 7750) / TICK) * TICK, f"l{i}")
                  for i in range(rnd.randint(0, 8))]
        zones = cluster_levels(levels, tol_pts=rnd.uniform(0.5, 6.0))
        sel = select_target_zones(direction=direction, entry_price=entry,
                                  t1_price=t1, zones=zones)
        for k in ("c2", "c3"):
            px = sel[k]
            if px is None:
                continue
            assert _on_grid(px), px
            # INVARIANT: every chosen target is strictly beyond T1 in profit dir
            if direction == "LONG":
                assert px > t1, (direction, t1, px)
            else:
                assert px < t1, (direction, t1, px)
        # INVARIANT: C3 is farther from T1 than C2 (when both exist)
        if sel["c2"] is not None and sel["c3"] is not None:
            if direction == "LONG":
                assert sel["c3"] >= sel["c2"]
            else:
                assert sel["c3"] <= sel["c2"]


# ----------------------------------------------------------------- day_direction
def test_halt_proof_invariants_fuzz():
    rnd = random.Random(44)
    for _ in range(N_ITER):
        exp = rnd.choice(["UP", "DOWN", "SIDE"])
        level = rnd.choice([None, round(rnd.uniform(7400, 7700), 2)])
        closes = [round(rnd.uniform(7350, 7750), 2) for _ in range(rnd.randint(0, 5))]
        k = rnd.randint(1, 3)
        out = halt_proof_met(expansion_dir=exp, expansion_level=level,
                             recent_closes=closes, min_closes=k)
        assert out in (True, False)
        # INVARIANT 1: no level or too few closes → never True
        if level is None or len([c for c in closes if c is not None]) < k:
            assert out is False
        # INVARIANT 2: True ⇒ the last k closes are all on the re-entry side
        if out and exp == "UP":
            assert all(c < level for c in closes[-k:])
        if out and exp == "DOWN":
            assert all(c > level for c in closes[-k:])
        # INVARIANT 3: unknown expansion direction never proves a halt
        if exp == "SIDE":
            assert out is False


# --------------------------------------------------------------------- reconcile
def test_reconcile_invariants_fuzz():
    rnd = random.Random(45)
    _MISMATCHES = {MISMATCH_ORPHAN_DB, MISMATCH_ORPHAN_TM, MISMATCH_PHANTOM_SLOT}
    for _ in range(N_ITER):
        slot = rnd.choice([True, False])
        db = [rnd.randint(1, 999)] if rnd.random() < 0.5 else []
        tm = rnd.choice([True, False, None])
        status = rnd.choice([None, "MODIFY_STOP_OK", "ENTRY_REJECTED", "PLACE_STOP_OK"])
        age = rnd.choice([None, rnd.uniform(0, 2000)])
        v = reconcile_positions(slot_occupied=slot, db_open_ids=db,
                                tm_in_position=tm, last_result_status=status,
                                last_result_age_s=age)
        # INVARIANT 1: mismatch flag ⇔ verdict is a mismatch verdict
        assert (v.verdict in _MISMATCHES) == v.mismatch, v
        # INVARIANT 2: AGREED_FLAT ⇒ genuinely flat across all sources
        if v.verdict == AGREED_FLAT:
            assert (not slot) and (not db) and (tm is not True), v
        # INVARIANT 3: an open DB row with a flat slot is ALWAYS caught (safety)
        if db and not slot:
            assert v.mismatch, v
        # INVARIANT 4: naked-stop flag ⇔ that verdict
        assert v.naked_stop_suspect == (v.verdict == NAKED_STOP_SUSPECT)
        # INVARIANT 5: IN_POSITION_OK ⇒ there really is a position belief
        if v.verdict == IN_POSITION_OK:
            assert v.in_position_belief
