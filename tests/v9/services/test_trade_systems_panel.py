"""extract_trade_systems_panel — cockpit active trade systems."""

from types import SimpleNamespace

from backend.v9.services.trade_context import extract_trade_systems_panel


def test_systems_panel_marks_firing_and_entry_price():
    trade = SimpleNamespace(
        firing_system=4,
        entry_price=7429.25,
        cross_context=[
            {
                "trigger": "TLB",
                "systems": {
                    "woodies_system": {"classification": "TLB", "active_patterns": [{"pattern_id": "TLB"}]},
                    "footprint_system": {"last_classification": "BUYER_REACTIVE"},
                    "five_min_system": {},
                },
            }
        ],
    )
    panel = extract_trade_systems_panel(trade)
    assert panel["firing_system"] == 4
    s4 = next(s for s in panel["systems"] if s["id"] == 4)
    assert s4["is_firing"] is True
    assert s4["entry_price"] == 7429.25
    assert s4["hint"] == "TLB"
    s3 = next(s for s in panel["systems"] if s["id"] == 3)
    assert s3["involved"] is True
    assert s3["entry_price"] is None
