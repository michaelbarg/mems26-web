"""T-227 regression: one malformed line must not cost a whole trading day.

Root cause (2026-09-02): the BRACKET_MODIFY regex was
    r"Parent base price: ([\\d.]+)\\. New price: ([\\d.]+)"
`.` sits INSIDE the character class and `+` is greedy, so on the real Sierra
line the second group captured "7673.50." — sentence period included — and
`float()` raised

    ValueError: could not convert string to float: '7673.50.'

That exception escaped `_parse_events` -> `run_once` -> the process. Result:
`trade_activity_events.jsonl` stopped growing on 2026-08-27, so the ruled-ON
W2 exit tracker (EXIT_TRACK_ACTIVITY_V1=1, Michael 2026-07-27) silently became
a no-op. Every MAE_SCRATCH / FLATTEN_ACCOUNT exit stayed UNPRICED and
`pnl_sierra` was NULL on 100% of rows.

Two guarantees are pinned here:
  1. the real line parses, and both prices are floats without a trailing dot;
  2. an unparsable line is CONTAINED (feed continues) and RECORDED (never
     silent) — the surrounding good lines still produce their events.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import trade_activity_feed as taf  # noqa: E402

# Copied VERBATIM from
# ~/SierraChart/TradeActivityLogs/TradeActivityLog_2026-09-02_UTC.37138283.data
# via `strings` (line 2801) — including the trailing binary-garbage char.
REAL_BRACKET_LINE = (
    "Teton CME Routing (Order update). Info: Modifying Attached Order from "
    "parent fill. Parent base price: 7676.50. New price: 7673.50. "
    "Requested Price: 7673.50. Requested Quantity: 0. Text: Attached order. "
    "Parent: 10910i"
)
REAL_CLOSE_LINE = "Closed Trade Profit/Loss: 277.50. Symbol: MESU26_FUT_CME."


def test_bracket_modify_does_not_swallow_the_sentence_period():
    events, _ = taf._parse_events([REAL_BRACKET_LINE], 0, account="37138283")
    bm = [e for e in events if e["type"] == "BRACKET_MODIFY"]
    assert len(bm) == 1, f"BRACKET_MODIFY not parsed from the real line: {events}"
    assert bm[0]["parent_price"] == 7676.50
    assert bm[0]["new_price"] == 7673.50


def test_real_line_batch_parses_without_raising():
    """The exact crash: this batch used to raise ValueError out of the loop."""
    taf._PARSE_ERRORS.clear()
    events, offset = taf._parse_events(
        [REAL_CLOSE_LINE, REAL_BRACKET_LINE], 0, account="37138283")
    assert offset == 2
    kinds = sorted(e["type"] for e in events)
    assert kinds == ["BRACKET_MODIFY", "CLOSED_TRADE_PNL"], kinds
    assert taf._PARSE_ERRORS == []


def test_one_bad_line_is_contained_and_recorded(monkeypatch):
    """Mutation-style: force a per-line failure and prove the day survives.

    This is the guard that makes the class of bug non-fatal, independent of any
    single regex. Without the try/except in `_parse_events` the good line after
    the poisoned one is lost and the whole run dies.
    """
    taf._PARSE_ERRORS.clear()

    real_search = taf.re.search
    calls = {"n": 0}

    def exploding_search(pattern, string, *a, **kw):
        # Blow up only while scanning the FIRST line, the way a bad regex would.
        if string == "POISON":
            calls["n"] += 1
            raise ValueError("could not convert string to float: '7673.50.'")
        return real_search(pattern, string, *a, **kw)

    monkeypatch.setattr(taf.re, "search", exploding_search)
    events, offset = taf._parse_events(
        ["POISON", REAL_CLOSE_LINE], 0, account="37138283")

    # the day survived: the good line after the poison still produced its event
    assert [e["type"] for e in events] == ["CLOSED_TRADE_PNL"]
    assert events[0]["pnl"] == 277.50
    assert offset == 2
    # ...and the failure is on the record, not swallowed
    assert len(taf._PARSE_ERRORS) == 1
    assert taf._PARSE_ERRORS[0]["line"] == 0
    assert "7673.50." in taf._PARSE_ERRORS[0]["error"]


def test_mutation_old_greedy_regex_would_still_fail():
    """Anti-tautology: the OLD pattern must still capture the trailing period.

    If someone 'simplifies' the regex back to `([\\d.]+)`, this documents
    exactly what breaks — group(2) is not a float.
    """
    old = taf.re.search(r"Parent base price: ([\d.]+)\. New price: ([\d.]+)",
                        REAL_BRACKET_LINE)
    assert old is not None
    assert old.group(2) == "7673.50."
    try:
        float(old.group(2))
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected the old regex to yield a non-float")
