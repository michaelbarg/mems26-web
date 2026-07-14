"""System 6 — invariant #2 (stop_wrong_side) must reference ENTRY, not price.

Audit finding (2026-07-14): the wrong-side check compared the stop against the
CURRENT PRICE. So a genuinely wrong-side INITIAL stop — a LONG whose stop is
ABOVE entry, or a SHORT whose stop is BELOW entry — ESCAPED detection the moment
price ran past that stop, then fell through to the BE/band branch (a
defence-in-depth gap). The fix references ENTRY: a LONG stop must be BELOW entry
and a SHORT stop must be ABOVE entry, independent of where price has travelled.

The wrong-side veto is gated to PRE-T1 (initial stop): after T1 a stop AT/beyond
entry is the DESIRED profit-lock, governed by the separate BE-after-T1 check —
so that case must NOT be flagged (guards against reverting to a naive
entry-vs-price comparison; see the incident-07-10 profit-lock test below).

System 6 is diagnose-only: these assertions check what the supervisor REPORTS.
Nothing here (and nothing the report drives) executes an exit — the only
corrections the supervisor ever emits are MODIFY_STOP / DROP_TARGET, never the
broken op=EXIT path.
"""
from backend.v9.systems.system6_supervisor import (
    diagnose_trade, CRITICAL, ALERT,
)

ATR = 8.0


def _codes(rep):
    return {i.code for i in rep.issues}


# ── (a) the previously-ESCAPING case: LONG stop ABOVE entry, price ABOVE stop ──
def test_long_stop_above_entry_flagged_even_when_price_ran_past_it():
    """LONG entry 7600, initial stop 7620 (ABOVE entry = wrong side), and price
    has already RUN PAST the stop to 7625 (price > stop). Under the old
    price-referenced check `stop > price` was 7620 > 7625 = False, so it
    ESCAPED. Referenced to entry it is unambiguously wrong: stop 7620 > entry
    7600."""
    trade = {"direction": "LONG", "entry_price": 7600.0, "stop": 7620.0,
             "contracts": 3}
    rep = diagnose_trade(trade=trade, atr=ATR, price=7625.0)  # price ABOVE stop
    assert "stop_wrong_side" in _codes(rep)
    iss = next(i for i in rep.issues if i.code == "stop_wrong_side")
    assert iss.severity == CRITICAL and iss.action == ALERT  # advisory, never auto


# ── (b) a correct LONG (stop BELOW entry) is NOT flagged, regardless of price ──
def test_correct_long_stop_below_entry_not_flagged():
    trade = {"direction": "LONG", "entry_price": 7600.0, "stop": 7592.0,
             "contracts": 3}
    # even with price well above, a protective stop below entry is correct
    rep = diagnose_trade(trade=trade, atr=ATR, price=7625.0)
    assert "stop_wrong_side" not in _codes(rep)


# ── (c) SHORT mirror: stop BELOW entry, price BELOW stop → still flagged ──────
def test_short_stop_below_entry_flagged_even_when_price_ran_past_it():
    """SHORT entry 7600, initial stop 7580 (BELOW entry = wrong side), price has
    RUN PAST the stop to 7575 (price < stop). Old check `stop < price` was
    7580 < 7575 = False → escaped. Referenced to entry: stop 7580 < entry
    7600 → wrong."""
    trade = {"direction": "SHORT", "entry_price": 7600.0, "stop": 7580.0,
             "contracts": 3}
    rep = diagnose_trade(trade=trade, atr=ATR, price=7575.0)  # price BELOW stop
    assert "stop_wrong_side" in _codes(rep)
    iss = next(i for i in rep.issues if i.code == "stop_wrong_side")
    assert iss.severity == CRITICAL and iss.action == ALERT


def test_correct_short_stop_above_entry_not_flagged():
    trade = {"direction": "SHORT", "entry_price": 7600.0, "stop": 7608.0,
             "contracts": 3}
    rep = diagnose_trade(trade=trade, atr=ATR, price=7575.0)
    assert "stop_wrong_side" not in _codes(rep)


# ── preserve invariant #3: post-T1 profit-locked stop is NOT wrong_side ───────
def test_post_t1_profit_locked_long_stop_not_flagged():
    """Incident 07-10: LONG entry 7608.5, stop moved to 7611.25 (ABOVE entry)
    AFTER T1 = profit-lock = DESIRED. It must NOT be flagged wrong_side — the
    t1_hit gate lets it flow to the BE-after-T1 check. If someone drops the gate
    (naive entry-vs-stop), this goes RED."""
    trade = {"direction": "LONG", "entry_price": 7608.5, "stop": 7611.25,
             "t1": 7617.5, "contracts": 3}
    rep = diagnose_trade(trade=trade, atr=ATR, t1_hit=True, price=7614.0)
    assert "stop_wrong_side" not in _codes(rep)


def test_post_t1_profit_locked_short_stop_not_flagged():
    """SHORT mirror of the profit-lock: entry 7600, stop 7595 (BELOW entry) after
    T1 = profit-locked = DESIRED, not wrong_side."""
    trade = {"direction": "SHORT", "entry_price": 7600.0, "stop": 7595.0,
             "t1": 7590.0, "contracts": 3}
    rep = diagnose_trade(trade=trade, atr=ATR, t1_hit=True, price=7593.0)
    assert "stop_wrong_side" not in _codes(rep)
