"""Display-only Dalton brain: which family this moment belongs to. Not a trade decision."""
from backend.v9.api.v9.tree_routes import brain_of


def _ctx(**kw):
    base = dict(phase="B", opening_type="OPEN_AUCTION_IN", structure="forming", il="16:40",
                hint=None, zone="unknown")
    base.update(kw)
    return base


def test_opening_family_while_ib_forms():
    b = brain_of(_ctx())
    assert b["family"]["id"] == "opening"
    assert b["questions"][0]["q"] == "מה השוק מנסה"
    assert "אוקציה בטווח" in b["questions"][0]["a"]
    assert "נפח ודלתא" in b["questions"][1]["a"]


def test_extension_family_after_ib():
    assert brain_of(_ctx(phase="C", structure="up", il="18:10"))["family"]["id"] == "extension"
    assert brain_of(_ctx(phase="C", structure="down", il="18:10"))["family"]["id"] == "extension"


def test_inside_and_two_sided():
    assert brain_of(_ctx(phase="C", structure="none", il="18:10"))["family"]["id"] == "inside"
    assert brain_of(_ctx(phase="C", structure="two_sided", il="18:10"))["family"]["id"] == "two_sided"


def test_hour_20_cuts_entries_even_if_extended():
    assert brain_of(_ctx(phase="D", structure="up", il="20:05"))["family"]["id"] == "late"


def test_who_controls_uses_the_plan_sentence():
    b = brain_of(_ctx(hint="LONG"), {"LONG": "ייקח: פריצה", "SHORT": "נגד ההטיה של הסשן"})
    assert b["questions"][3]["a"] == "ייקח: פריצה"
