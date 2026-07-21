"""Regression: trade_activity_feed parses Sim1 log lines (2026-07-21).

Root cause: Sim1 TradeActivityLogs contain NONE of the live-account patterns
("Closed Trade Profit/Loss", "Updated Internal Position Quantity", ...) —
verified 0/5 matches on a real 49KB Sim1 session log. On sim days the feed
appended nothing and trade_activity_events.jsonl looked stalled (S124).

Fixture lines below are copied VERBATIM from
TradeActivityLog_2026-07-21_UTC.Sim1.simulated.data (via `strings`),
including the trailing binary-garbage characters — anti-tautological: the
regexes must survive the real format, not a sanitized one.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from trade_activity_feed import _parse_events  # noqa: E402

REAL_SIM_LINES = [
    "AAMichael_lap25.Cht",
    "MESU26_FUT_CMEh",
    "Trade simulation fill. Bid: 7520.25 Ask: 7520.75 Last: 7520.50i",
    "9258k",
    "Marketl",
    "Auto-sent child from parent filli",
    ("Auto-trade: MESU26_FUT_CME[M]  5 Min  #8 | MES AI Data Export "
     "v9.4.3-chart5 | Source: ACSIL Flatten & Cancel | Bar start date-time: "
     "2026-07-20  15:55:00.000. Flatten&CancelAllOrders | Last: 7519. "
     "Current Position quantity: -4 | AOE=false | AOU=falsei"),
    "MESU26_FUT_CME[M] #2 | User order entry | Unable to Flatten/Reverse. Position does not existq",
]


def test_sim_fill_parsed():
    events, off = _parse_events(REAL_SIM_LINES, 0, account="Sim1")
    fills = [e for e in events if e["type"] == "SIM_FILL"]
    assert len(fills) == 1
    assert fills[0]["bid"] == 7520.25
    assert fills[0]["ask"] == 7520.75
    assert fills[0]["last"] == 7520.5
    assert fills[0]["is_sim"] is True
    assert fills[0]["account"] == "Sim1"
    assert off == len(REAL_SIM_LINES)


def test_sim_flatten_parsed():
    events, _ = _parse_events(REAL_SIM_LINES, 0, account="Sim1")
    flats = [e for e in events if e["type"] == "SIM_FLATTEN"]
    assert len(flats) == 1
    assert flats[0]["last"] == 7519.0
    assert flats[0]["position_qty"] == -4


def test_sim_patterns_gated_to_sim_accounts():
    # A live account must NOT emit SIM_* events even if the text appeared.
    events, _ = _parse_events(REAL_SIM_LINES, 0, account="37138283")
    assert not [e for e in events if e["type"].startswith("SIM_")]


def test_offset_respected():
    # Re-run from end offset → no duplicate events.
    events, off = _parse_events(REAL_SIM_LINES, len(REAL_SIM_LINES), account="Sim1")
    assert events == []
    assert off == len(REAL_SIM_LINES)
