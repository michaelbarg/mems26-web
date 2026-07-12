"""P1-8 — Nonconviction 8th type (Dalton pp.300-302, doctrine contradiction-8).

A day that LOOKS like Normal/NV/Neutral but carries no OTF footprints:
Open-Auction rotating inside prior value, zero RE bars, sides=0, mid close.
No reference points → stand aside entirely.

Full-wiring rule coverage: classifier emits the type (flag-gated) → position
gate blocks unconditionally → playbook cells SKIP for all 13 patterns.
Anti-tautological: flag OFF → same fixture classifies as before (not Nonconviction).
"""
import yaml
from pathlib import Path

from backend.v9.systems.day_type.daytype_classifier import classify, load_plan
from backend.v9.systems.daytype_position_gate import decide

REPO = Path(__file__).resolve().parents[4]


def _dead_day_feat():
    """OA-in-value dead day (the 07-03 holiday shape: 12.5pt, no RE, mid close)."""
    return {
        "n_bars": 30, "sides": 0, "rib": 1.05, "one_tf": None,
        "cvd_pos": 0.5, "close_pos": 0.48, "vol_ratio": 0.9,  # normal volume!
        "opening_type": "OPEN_AUCTION_IN", "open_location": "in_value",
        "ext_up_bars": 0, "ext_dn_bars": 0, "ib_width": 12.0, "ib_pctile": 40,
        "dd_second_dist": None, "returned_through_open": False,
        "stair_steps_up": 0, "stair_steps_dn": 0, "session_range": 12.5,
    }


def test_flag_on_dead_day_is_nonconviction(monkeypatch):
    monkeypatch.setenv("S1_NONCONVICTION_V1", "1")
    r = classify(_dead_day_feat(), load_plan(), is_eod=True)
    assert r["day_type"] == "Nonconviction", r
    assert "stand aside" in r["reason"]


def test_flag_off_unchanged(monkeypatch):
    monkeypatch.delenv("S1_NONCONVICTION_V1", raising=False)
    r = classify(_dead_day_feat(), load_plan(), is_eod=True)
    assert r["day_type"] != "Nonconviction", r


def test_real_conviction_day_not_tagged(monkeypatch):
    """Anti-tautology: same open type but WITH range extension → not Nonconviction."""
    monkeypatch.setenv("S1_NONCONVICTION_V1", "1")
    f = _dead_day_feat()
    f["ext_up_bars"] = 4
    f["sides"] = 1
    r = classify(f, load_plan(), is_eod=True)
    assert r["day_type"] != "Nonconviction", r


def test_position_gate_blocks_nonconviction(monkeypatch):
    monkeypatch.setenv("DAYTYPE_POSITION_GATE", "1")
    allow, reason = decide(pattern="ZLR", direction="LONG", day_type="Nonconviction",
                           entry_price=7600.0, tpo_ctx={"poc": 7600, "vah": 7605, "val": 7595})
    assert allow is False
    assert "Nonconviction" in reason


def test_playbook_cells_all_skip():
    cfg = yaml.safe_load((REPO / "config/daytype_playbook.yaml").read_text())
    pats = cfg.get("patterns") or {}
    assert pats, "patterns section missing"
    for name, row in pats.items():
        cells = row.get("cells") or {}
        assert cells.get("Nonconviction") == "SKIP", f"{name} missing Nonconviction SKIP"
