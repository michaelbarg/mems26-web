"""T-637 (23.10) · opening type v2 — Dalton's four openings on closed bars, in ATR units.

Michael 23.10: "תקרא שוב דלתון איך צריך לסווג … עד הפתיחה אתה כבר צריך לדעת להגדיר בצורה מצוינת סוג פתיחה
ושלא יהיה בקלות מדי שיהיה נכון". The bars below are the real first 8 RTH bars (relative to the open) of the
days read by hand in docs/reports/OPENING_V2_STUDY_2026-10-23.md.
"""
import datetime as dt

from backend.v9.systems.opening_classifier_v2 import classify_opening_v2 as C, OpeningLock


def B(o, rel):
    """rel = [(h, l, c), …] relative to the open; the open of bar i+1 = close of bar i."""
    out, prev_c = [], o
    for h, l, c in rel:
        out.append({"o": prev_c, "h": o + h, "l": o + l, "c": o + c}); prev_c = o + c
    return out


# 21.09 — a clean drive up (gap above yesterday's range), EOD +72.50
D_2109 = B(7760.5, [(4, -2.25, 1.5), (4.5, .75, 4), (5.75, 1.75, 5.75), (8.75, 5.25, 7.25), (12.75, 6.75, 12.5), (14.5, 10, 14.25), (15.5, 11.5, 11.75), (12.25, 7.25, 11)])
P_2109 = {"high": 7718.25, "low": 7675.0, "vah": 7706.25, "val": 7683.25, "on_high": 7770.75, "on_low": 7713.75}
# 22.10 — two-sided rotation below yesterday's range (#3749's "drive" was a one-tick close), EOD −22.75
D_2210 = B(7729.0, [(11.75, -4, 9.25), (10.25, 3, 9), (9.25, .5, 3), (2.75, -8.75, -.25), (-.25, -10, -1.25), (9.75, -3.25, 8), (13.5, 4.5, 10.25), (11.25, -3.25, -2)])
P_2210 = {"high": 7811.75, "low": 7751.0, "vah": 7811.0, "val": 7776.5, "on_high": 7806.0, "on_low": 7710.25}
# 20.10 — first leg down 16.5 (no reference within reach), reversal through the open, EOD +32 (the ORR long +550)
D_2010 = B(7726.75, [(.25, -8.25, -3.5), (4.25, -6.75, -1.25), (-.5, -15.5, -13.75), (4.5, -16.5, 2.25), (11, 0, 5.75), (21.5, 5.75, 21.25), (26, 16.5, 20.75), (31.25, 18.25, 29)])
P_2010 = {"high": 7773.25, "low": 7727.5, "vah": 7754.5, "val": 7735.75, "on_high": 7752.75, "on_low": 7704.5}
# 14.09 — test of yesterday's VAL, failed, drive up through the open, EOD +19
D_1409 = B(7673.5, [(2.5, -4.25, -3), (-.75, -5.5, -4.25), (5.25, -5.5, 4), (16, 4, 13), (16.25, 10.75, 12), (12.5, 7.75, 9.75), (15.75, 8.75, 14.5), (21.25, 12.75, 18.5)])
P_1409 = {"high": 7682.0, "low": 7653.25, "vah": 7680.0, "val": 7666.25, "on_high": 7682.0, "on_low": 7592.75}
# 19.10 — rotation inside value; the T-314 label said ORR and the 16:50 DRIVE SHORT lost 210
D_1910 = B(7741.5, [(8.25, -3.25, 1.5), (6, -4.5, -.25), (4, -4.25, -3.25), (.25, -6.5, -4.25), (-1.25, -9.5, -7.25), (-2.75, -10.25, -6.5), (-4.25, -14, -9.25), (-4.75, -10.5, -6)])
P_1910 = {"high": 7803.0, "low": 7676.0, "vah": 7761.25, "val": 7679.0, "on_high": 7768.5, "on_low": 7677.5}
# 13.10 — drive up 14 pts by bar 3 … and a close back through the open at bar 8 (revocation)
D_1310 = B(7849.0, [(5.75, -2, 3.5), (13, 1.25, 12), (14.25, 9.25, 10.5), (12, 8.75, 10.25), (11.75, 5.5, 11), (11.25, 4.5, 7), (7.25, .25, 2), (2.25, -2.75, -1)])
P_1310 = {"high": 7870.0, "low": 7846.25, "vah": 7860.5, "val": 7849.5, "on_high": 7864.0, "on_low": 7835.75}
# 25.09 — a 16-pt first leg beyond yesterday's high, then a violent reversal: ORR at bar 7, upgraded to TEST_DRIVE at bar 8
D_2509 = B(7777.5, [(8, -10, 7.25), (10.75, 5, 10), (13.25, 5.75, 7.5), (9.5, 2.5, 7.75), (15.5, 6.5, 13.75), (16.25, 7.75, 10), (11, -12.25, -11.25), (-9.75, -22.5, -10.5)])
P_2509 = {"high": 7783.5, "low": 7725.25, "vah": 7778.0, "val": 7745.0, "on_high": 7800.75, "on_low": 7747.75}


def run(bars, prev, atr):
    L = OpeningLock(); seq = [L.update(bars[:k], prev, atr) for k in range(1, len(bars) + 1)]
    return L, seq


def test_2109_is_a_drive_up_locked_at_bar_4():
    L, seq = run(D_2109, P_2109, 4.69)
    assert seq[2]["type"] == "OPEN_AUCTION_OUT" and not seq[2]["locked"]        # bar 3: 5.75 pts is not yet a drive
    assert L.locked["type"] == "OPEN_DRIVE" and L.locked["direction"] == "up" and L.locked_bar == 4
    assert seq[-1]["type"] == "OPEN_DRIVE" and seq[-1].get("kept")


def test_2210_is_an_auction_out_never_a_drive():
    L, seq = run(D_2210, P_2210, 6.35)
    assert all(r["type"] == "OPEN_AUCTION_OUT" for r in seq[2:])
    assert L.locked_bar == 8 and not seq[3]["locked"]                            # bar 4 (16:50, #3749) is provisional
    assert seq[3]["metrics"]["max_up_u"] >= 1.0 and seq[3]["metrics"]["max_dn_u"] >= 1.0   # two-sided


def test_2010_is_a_rejection_reverse_up_at_bar_5():
    L, seq = run(D_2010, P_2010, 6.42)
    assert L.locked["type"] == "OPEN_REJECTION_REVERSE" and L.locked["direction"] == "up" and L.locked_bar == 5
    assert "no reference" in L.locked["why"]


def test_1409_is_a_test_drive_up_of_the_val_at_bar_4():
    L, seq = run(D_1409, P_1409, 5.4)
    assert L.locked["type"] == "OPEN_TEST_DRIVE" and L.locked["direction"] == "up" and L.locked_bar == 4
    assert "val" in L.locked["why"]


def test_1910_is_an_auction_in_not_a_rejection_reverse():
    L, seq = run(D_1910, P_1910, 7.3)
    assert L.locked["type"] == "OPEN_AUCTION_IN" and L.locked_bar == 8
    assert not any(r["type"] == "OPEN_REJECTION_REVERSE" for r in seq)        # the 8.25-pt opening wick is not a rejected drive


def test_1310_drive_is_revoked_by_the_close_through_the_open_at_bar_8():
    L, seq = run(D_1310, P_1310, 3.21)
    assert seq[3]["type"] == "OPEN_DRIVE" and seq[3]["locked"]
    assert seq[7]["revoked_from"] == "OPEN_DRIVE" and seq[7]["type"] == "OPEN_AUCTION_IN"
    assert L.revoked == [(8, "OPEN_DRIVE")]


def test_2509_orr_is_upgraded_to_a_test_drive_when_the_drive_develops():
    L, seq = run(D_2509, P_2509, 7.92)
    assert seq[6]["type"] == "OPEN_REJECTION_REVERSE" and seq[6]["direction"] == "down"
    assert seq[7]["type"] == "OPEN_TEST_DRIVE" and seq[7]["upgraded_from"] == "OPEN_REJECTION_REVERSE"
    assert "high" in seq[7]["why"]


def test_bad_input_and_no_prev_are_safe():
    assert C([], None, None)["type"] == "UNKNOWN"
    assert C([{"o": "x"}], None, None)["type"] == "UNKNOWN"
    r = C(D_2210[:8], None, None)
    assert r["type"] == "OPEN_AUCTION" and r["unit"] == 3.0


def test_live_reader_uses_the_seeded_inputs_without_the_db():
    from backend.v9.services import opening_v2_live as live
    live.reset_state()
    today = live._session_date_et(dt.datetime(2026, 10, 20, 14, 0, tzinfo=dt.timezone.utc))
    live._STATE.update({"date": today, "prev": P_2010, "atr": 6.42, "lock": OpeningLock(), "last_n": -1, "last": None})
    now = dt.datetime(2026, 10, 20, 14, 0, tzinfo=dt.timezone.utc)
    r4 = live.read_opening_v2(now=now, bars=D_2010[:4]); r5 = live.read_opening_v2(now=now, bars=D_2010[:5])
    assert r4["type"] == "OPEN_AUCTION_OUT" and r5["type"] == "OPEN_REJECTION_REVERSE" and r5["locked"]
    assert live.read_opening_v2(now=now, bars=D_2010[:5]) is r5          # cached per bar count
    live.reset_state()
