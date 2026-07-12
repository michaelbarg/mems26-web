"""P0-1 v2 — acceptance-driven reclassification at ALL reference levels (Michael 2026-07-12).

Doctrine (DALTON_DOCTRINE.md §4 P0-1, pp.37-38/278-293): a committed reference break
(IB edge, prior-day range, prior value-area) WITH acceptance (≥2 consecutive closes +
volume-accept beyond) reclassifies immediately; a return back inside = rejection →
failed_breakout tag + revert. v1 wired IB only; v2 adds PDH/PDL + prior-VA + rejection.

Anti-tautological: the volume gate and the flag-OFF identity are each proven by a
case that would FAIL if the mechanism were a no-op.
"""
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from backend.v9.systems.day_type.relative_features import level_acceptance  # noqa: E402
from backend.v9.systems.day_type.classifier_core import classify_session  # noqa: E402

FLAG = "S1_ACCEPTANCE_RECLASS_V1"


def _bar(o, h, l, c, v=100.0):
    return {"o": o, "h": h, "l": l, "c": c, "v": v}


def _flat_bars(n, px=5000.0, v=100.0):
    return [_bar(px, px + 1, px - 1, px, v) for _ in range(n)]


# ───────────────────────── level_acceptance (unit) ─────────────────────────

def test_accept_up_needs_hold_and_volume():
    # 6 bars: 4 inside below level, 2 closes above WITH real volume above
    lvl = 5010.0
    bars = _flat_bars(4, 5000) + [_bar(5011, 5014, 5010.8, 5012, 400),
                                  _bar(5012, 5015, 5011.5, 5013, 400)]
    a = level_acceptance(bars, lvl, "UP")
    assert a["accepted"] is True and a["rejected_after_accept"] is False
    assert a["accept_bar"] == 5


def test_thin_poke_blocked_by_volume_gate():
    # SAME price path but the 2 bars beyond carry ~1% of session volume →
    # anti-tautological proof the volume gate does the blocking.
    lvl = 5010.0
    bars = _flat_bars(4, 5000, v=1000.0) + [_bar(5011, 5014, 5010.8, 5012, 20),
                                            _bar(5012, 5015, 5011.5, 5013, 20)]
    a = level_acceptance(bars, lvl, "UP")
    assert a["accepted"] is False and a["accept_bar"] is not None  # held, but volume said no


def test_single_close_is_not_acceptance():
    lvl = 5010.0
    bars = _flat_bars(3, 5000) + [_bar(5011, 5014, 5010.8, 5012, 400)] + _flat_bars(2, 5000)
    a = level_acceptance(bars, lvl, "UP")
    assert a["accepted"] is False and a["accept_bar"] is None


def test_accept_then_return_inside_is_rejection():
    lvl = 5010.0
    bars = (_flat_bars(3, 5000)
            + [_bar(5011, 5014, 5010.8, 5012, 400), _bar(5012, 5015, 5011.5, 5013, 400),
               _bar(5013, 5015, 5011, 5012.5, 300)]
            + [_bar(5009, 5010, 5004, 5006, 300), _bar(5006, 5008, 5003, 5005, 300)])
    a = level_acceptance(bars, lvl, "UP")
    assert a["rejected_after_accept"] is True and a["accepted"] is False


def test_down_side_mirror():
    lvl = 4990.0
    bars = _flat_bars(4, 5000) + [_bar(4989, 4990, 4985, 4988, 400),
                                  _bar(4988, 4989, 4984, 4986, 400)]
    a = level_acceptance(bars, lvl, "DOWN")
    assert a["accepted"] is True


# ───────────────────── classify_session wiring (integration) ─────────────────────

def _gap_and_go_bars(n=8, pdh=5010.0):
    """Opens above PDH and stair-steps up — never looks back. IB will be the
    session's own first hour, so the IB is NOT broken; only PDH is."""
    bars = []
    px = pdh + 4
    for i in range(n):
        bars.append(_bar(px, px + 3, px - 1, px + 2, 500))
        px += 2.5
    return bars


def test_gap_and_go_reclass_names_pdh_before_ib_lock(monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    bars = _gap_and_go_bars(8)  # 8 bars = 40 min < 60-min IB lock
    ib_h = max(b["h"] for b in bars[:12])
    ib_l = min(b["l"] for b in bars[:12])
    r = classify_session(bars=bars, ib_high=ib_h, ib_low=ib_l,
                         pdh=5010.0, pdl=4980.0, prior_vah=5005.0, prior_val=4990.0)
    assert r.get("reclass") is True, r
    assert r.get("reclass_ref") == "PDH", r          # outermost ref wins the name
    assert r["day_type"] in ("Trend_Normal", "Normal_Variation"), r
    assert r.get("break_dir") == "UP", r


def test_flag_off_is_byte_identical_on_same_bars(monkeypatch):
    """Anti-tautological: the SAME gap-and-go that reclasses under the flag must
    fall back to plain FORMING when the flag is unset."""
    monkeypatch.delenv(FLAG, raising=False)
    monkeypatch.delenv("S1_COMMITTED_PROVISIONAL_V1", raising=False)
    bars = _gap_and_go_bars(8)
    ib_h = max(b["h"] for b in bars[:12])
    ib_l = min(b["l"] for b in bars[:12])
    r = classify_session(bars=bars, ib_high=ib_h, ib_low=ib_l,
                         pdh=5010.0, pdl=4980.0, prior_vah=5005.0, prior_val=4990.0)
    assert r["day_type"] == "FORMING" and "reclass" not in r, r


def test_va_edge_acceptance_inside_ib(monkeypatch):
    """Close held above prior VAH with volume while the session IB is NOT broken
    → the prior_VA reference alone drives the reclass (v1 could never do this)."""
    monkeypatch.setenv(FLAG, "1")
    vah = 5006.0
    # 14 bars (past IB lock): first 12 define a wide IB 4995-5015; last bars sit above VAH
    bars = [_bar(5000, 5015, 4995, 5002, 300) for _ in range(6)]
    bars += [_bar(5004, 5012, 5002, 5008, 500) for _ in range(8)]  # closes 5008 > VAH+buf
    r = classify_session(bars=bars, ib_high=5015.0, ib_low=4995.0,
                         pdh=5030.0, pdl=4970.0, prior_vah=vah, prior_val=4985.0)
    assert r.get("reclass") is True and r.get("reclass_ref") == "prior_VA", r
    assert r.get("break_dir") == "UP", r


def test_failed_breakout_reverts_and_tags(monkeypatch):
    """Accepted above PDH, then last two closes back inside → NO reclass
    promotion + failed_breakout tag on the regular-path output."""
    monkeypatch.setenv(FLAG, "1")
    pdh = 5010.0
    bars = (_flat_bars(4, 5000, v=300)
            + [_bar(5011, 5014, 5010.5, 5012, 500), _bar(5012, 5016, 5011, 5013.5, 500),
               _bar(5013, 5015, 5010.5, 5012, 400)]
            + [_bar(5009, 5011, 5002, 5004, 400), _bar(5004, 5006, 5000, 5002, 400)])
    ib_h = max(b["h"] for b in bars)   # wide IB — IB itself never accepted
    ib_l = min(b["l"] for b in bars)
    r = classify_session(bars=bars, ib_high=ib_h + 5, ib_low=ib_l - 5,
                         pdh=pdh, pdl=4980.0, prior_vah=5005.0, prior_val=4990.0)
    assert r.get("reclass") is None or r.get("reclass") is not True, r
    assert r.get("failed_breakout") is True, r


def test_two_sided_acceptance_no_directional_reclass(monkeypatch):
    """Accepted beyond PDH earlier AND beyond PDL later (both held+volume) →
    two-sided, accepted_break must resolve to None (no directional promotion)."""
    monkeypatch.setenv(FLAG, "1")
    bars = ([_bar(5012, 5016, 5011, 5013, 500), _bar(5013, 5017, 5012, 5014, 500),
             _bar(5013, 5015, 5011, 5012.5, 300)]
            + [_bar(4988, 4990, 4984, 4986, 500), _bar(4986, 4988, 4982, 4984, 500),
               _bar(4985, 4987, 4981, 4983, 300)])
    r = classify_session(bars=bars, ib_high=5020.0, ib_low=4978.0,
                         pdh=5010.0, pdl=4990.0, prior_vah=5006.0, prior_val=4994.0)
    assert r.get("reclass") is not True, r
