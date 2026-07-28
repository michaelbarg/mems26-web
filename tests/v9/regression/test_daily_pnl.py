"""Daily P&L from Sierra's per-day TradeActivityLog files (Michael 2026-07-28).

He challenged the numbers — correctly. The previous implementation summed
`trade_activity_events.jsonl`, whose feeder re-emitted the same log lines after
any `strings` failure (2363 events / 309 unique; one −125.00 close counted 117
times) and whose `ts` is the SCAN time, not the trade time. The day now comes
from the log FILENAME and each close is read once from the file itself.
"""
from backend.v9.services.daily_pnl import parse_day_log

_REAL_0727 = """
Cash Balance update | Closed Trade Profit/Loss: 90.00. Symbol: MESU26_FUT_CME. Currency: USD
Updated Internal Position Quantity to -10. Previous: 0. Fill of InternalOrderID: 9632
Cash Balance update | Closed Trade Profit/Loss: 43.75. Symbol: MESU26_FUT_CME. Currency: USD
Updated Internal Position Quantity to -7. Previous: -10. Fill of InternalOrderID: 9635
Cash Balance update | Closed Trade Profit/Loss: 15.00. Symbol: MESU26_FUT_CME. Currency: USD
Updated Internal Position Quantity to 0. Previous: -4. Fill of InternalOrderID: 9633
Updated Internal Position Quantity to 10. Previous: 0. Fill of InternalOrderID: 9638
Cash Balance update | Closed Trade Profit/Loss: -3625.00. Symbol: MESU26_FUT_CME. Currency: USD
Updated Internal Position Quantity to 0. Previous: 10. Fill of InternalOrderID: 9643
"""


def test_parses_the_real_0727_log():
    d = parse_day_log(_REAL_0727)
    assert d["pnl"] == -3476.25
    assert d["closes"] == 4 and d["wins"] == 3 and d["losses"] == 1
    assert d["biggest_loss"] == -3625.0


def test_entry_ladder_exposes_position_size():
    """Only 0→N transitions are entries. 07-27 had exactly two, both 10 lots —
    which is how we can tell the day was manual: system size is 1-5."""
    d = parse_day_log(_REAL_0727)
    assert d["entries"] == [10, 10]
    assert d["max_entry_size"] == 10


def test_no_entries_when_account_never_opened_a_position():
    """The signal that our books claim live trades Sierra never made."""
    d = parse_day_log("Cash Balance update | Current account balance data request")
    assert d["entries"] == [] and d["closes"] == 0


def test_each_close_counted_once_even_if_values_repeat():
    """Repeated identical values are separate real closes (per-contract) — but
    each LINE is counted exactly once. The old journal path counted one close
    117 times; this must not regress."""
    txt = "\n".join(["Closed Trade Profit/Loss: -23.75. Symbol: X."] * 4)
    d = parse_day_log(txt)
    assert d["closes"] == 4 and d["pnl"] == -95.0


def test_negative_and_decimal_values_parse():
    d = parse_day_log("Closed Trade Profit/Loss: -3625.00. Symbol: X.\n"
                      "Closed Trade Profit/Loss: 0.25. Symbol: X.")
    assert d["values"] == [-3625.0, 0.25]
