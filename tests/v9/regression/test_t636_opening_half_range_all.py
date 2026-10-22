"""T-636 (22.10) · OPENING_HALF_RANGE_GATE_V1 = "all" — the opening losers of 19–22.10 on their real closed bars.

Michael 22.10 17:0x: "למה שוב הפסדנו כסף בפתיחה אני רוצה שתתקן פערים… סוג הפתיחה צריך לבדוק".
"""
from backend.v9.systems.opening_half_range import opening_half_range_verdict as V


def _b(*hl):
    return [{"h": h, "l": l} for h, l in hl]


# closed RTH bars at the moment of each fire (16:30 … the bar before the fire)
B_2210 = _b((7740.75, 7725.0), (7739.25, 7732.0), (7738.25, 7729.5), (7731.75, 7720.25))   # fire 16:50:05
B_2110 = _b((7780.0, 7764.5), (7777.25, 7767.5), (7778.75, 7764.75), (7780.75, 7767.75))   # fire 16:50:04
B_2010_1645 = _b((7727.0, 7718.5), (7731.0, 7720.0), (7726.25, 7711.25))                   # #3540 fire 16:45
B_2010_1650 = _b((7727.0, 7718.5), (7731.0, 7720.0), (7726.25, 7711.25), (7731.25, 7710.25))  # #3544 fire 16:50
B_1910 = _b((7749.75, 7738.25), (7747.5, 7737.0), (7745.5, 7737.25), (7741.75, 7735.0))     # fire 16:50:05


def test_2210_3749_test_drive_short_on_an_auction_open_is_a_mismatch():
    v = V("OPENING_TEST_DRIVE", "SHORT", 7727.5, "OPEN_AUCTION_IN", "B", B_2210, "all")
    assert v is not None and v[0] == "opening_type_mismatch"
    # and even as a pure location question it is the lower half of 7720.25–7740.75 (mid 7730.50)
    v2 = V("OPENING_EXTREME_REJECT", "SHORT", 7727.5, "OPEN_AUCTION_IN", "B", B_2210, "all")
    assert v2 is not None and v2[0] == "opening_half_range"


def test_2110_3637_extreme_reject_long_at_the_range_top_is_blocked():
    v = V("OPENING_EXTREME_REJECT", "LONG", 7778.5, "OPEN_AUCTION_IN", "B", B_2110, "all")
    assert v is not None and v[0] == "opening_half_range" and "upper half" in v[1]
    # the T-628 mode ("1") already blocked this one (OPEN_AUCTION) — unchanged
    assert V("OPENING_EXTREME_REJECT", "LONG", 7778.5, "OPEN_AUCTION_IN", "B", B_2110, "1")[0] == "opening_half_range"


def test_2010_3540_drive_short_at_the_drive_low_is_blocked_and_3544_orr_is_kept():
    # #3540 fired as DRIVE under the canonical OPEN_TEST_DRIVE (the live config of 20.10): lower half of 7711.25–7731
    v = V("OPENING_DRIVE", "SHORT", 7713.75, "OPEN_TEST_DRIVE", "A", B_2010_1645, "all")
    assert v is not None and v[0] == "opening_half_range"
    # with OPENING_DRIVE_STRICT_V1 it fires as TEST_DRIVE — same location, same verdict
    assert V("OPENING_TEST_DRIVE", "SHORT", 7713.0, "OPEN_TEST_DRIVE", "A", B_2010_1645, "all")[0] == "opening_half_range"
    # #3544 OPENING_ORR LONG 7729 at the top of 7710.25–7731.25 — the reversal bar IS the test: exempt in "all" mode
    assert V("OPENING_ORR", "LONG", 7729.0, "OPEN_REJECTION_REVERSE", "B", B_2010_1650, "all") is None
    # mode "1" (T-628 as measured) would not even look: the canonical type is not an auction
    assert V("OPENING_DRIVE", "SHORT", 7713.75, "OPEN_TEST_DRIVE", "A", B_2010_1645, "1") is None


def test_1910_drive_short_under_a_rejection_reverse_open_is_a_mismatch():
    v = V("OPENING_DRIVE", "SHORT", 7737.25, "OPEN_REJECTION_REVERSE", "B", B_1910, "all")
    assert v is not None and v[0] == "opening_type_mismatch"


def test_the_template_entries_pass():
    # a SHORT in the upper half of an auction range (the fade of the auction high) is what the rule wants
    assert V("OPENING_EXTREME_REJECT", "SHORT", 7738.0, "OPEN_AUCTION_IN", "B", B_2210, "all") is None
    # a LONG test-drive entry in the lower half under a canonical OPEN_TEST_DRIVE
    assert V("OPENING_TEST_DRIVE", "LONG", 7714.0, "OPEN_TEST_DRIVE", "A", B_2010_1645, "all") is None
    # phase C and non-opening producers are never judged here
    assert V("OPENING_TEST_DRIVE", "SHORT", 7727.5, "OPEN_AUCTION_IN", "C", B_2210, "all") is None
    assert V("CEILING_FLIP_TOUCH2", "SHORT", 7727.5, "OPEN_AUCTION_IN", "B", B_2210, "all") is None
    # off / no bars ⇒ never blocks
    assert V("OPENING_TEST_DRIVE", "SHORT", 7727.5, "OPEN_AUCTION_IN", "B", B_2210, "0") is None
    assert V("OPENING_EXTREME_REJECT", "SHORT", 7727.5, "OPEN_AUCTION_IN", "B", [], "all") is None


def test_live_path_the_gateway_hands_the_post_t426_label_to_t636():
    """What the gateway REALLY passes (17:5x 22.10 check of the live log): with
    OPENING_DRIVE_PROVISIONAL_V1=1 the T-426 block rewrites a lagging AUCTION
    label into the engine's drive type BEFORE the T-636 gate reads `_dp_ot`
    (16:50:03 "T-426 provisional opening type OPEN_AUCTION_IN→OPEN_TEST_DRIVE").
    So on the live path #3749 is blocked by the HALF-RANGE rule, not by the
    mismatch rule; the mismatch rule stays live for a canonical ORR (19.10) and
    for a locked AUCTION label (T-426 never touches a locked label). All four
    losers blocked, #3544 kept — the outcome is the same on both paths; only
    the reason string differs for #3749. The T-426 ruling (20.09, measured on
    56 sessions) is NOT reverted by T-636 — it is reconciled: the drive is
    admitted, the entry must still sit in the right half of the opening range."""
    from backend.v9.systems.opening_provisional import provisional_opening_type as P
    ot, _d, applied = P("OPEN_AUCTION_IN", locked=False, classification="OPENING_TEST_DRIVE", direction="SHORT")
    assert applied and ot == "OPEN_TEST_DRIVE"
    v = V("OPENING_TEST_DRIVE", "SHORT", 7727.5, ot, "B", B_2210, "all")
    assert v is not None and v[0] == "opening_half_range"
    # locked label ⇒ T-426 leaves it ⇒ the mismatch rule is what fires
    ot2, _d2, applied2 = P("OPEN_AUCTION_IN", locked=True, classification="OPENING_TEST_DRIVE", direction="SHORT")
    assert not applied2 and ot2 == "OPEN_AUCTION_IN"
    assert V("OPENING_TEST_DRIVE", "SHORT", 7727.5, ot2, "B", B_2210, "all")[0] == "opening_type_mismatch"
    # canonical ORR is not a lagging label ⇒ untouched ⇒ 19.10 DRIVE SHORT still a mismatch on the live path
    ot3, _d3, applied3 = P("OPEN_REJECTION_REVERSE", locked=False, classification="OPENING_DRIVE", direction="SHORT")
    assert not applied3
    assert V("OPENING_DRIVE", "SHORT", 7737.25, ot3, "B", B_1910, "all")[0] == "opening_type_mismatch"
