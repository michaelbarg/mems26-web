"""T-422 (F19) — the opening confirmation bar must be a CLOSED bar.

ROOT (measured 2026-09-18): `opening_first_trade_ok` judged `session_bars[-1]`,
and `five_min_system._oe_bars` holds ONE FROZEN snapshot per 5-min bar taken on
that bar's FIRST push (`process_bar` returns early on every duplicate push:
`if not is_new_bar: return`). So the judged bar was the DEVELOPING bar (o≈c,
~3s in) ⇒ "last bar did not confirm" nearly always ⇒ the drive was held
bar-after-bar. The code contradicted its own docstring ("the LAST *closed* bar
must close in the trigger direction").

Raw live evidence, /tmp/backend.err.log 2026-09-18 (the whole opening held):
    16:35:06 held DRIVE SHORT — only 2 bars < 3
    16:40:03 held DRIVE SHORT — last bar did not confirm SHORT (o=7705.25 c=7705.25)
    16:45:08 held DRIVE SHORT — last bar did not confirm SHORT (o=7705.0 c=7705.25)
    16:50:12 held DRIVE SHORT — last bar did not confirm SHORT (o=7700.75 c=7701.0)
    16:55:02 held DRIVE SHORT — last bar did not confirm SHORT (o=7695.0 c=7695.5)
    17:00:10 LIVE #1916 OPENING_DRIVE SHORT @7691.25 (25 of the 26 points gone)
while the canonical closed bars (v9_bars_5min_woodies) for the same session are
    16:30 o 7710    c 7707       16:45 o 7705    c 7700.75
    16:35 o 7706.75 c 7705.25    16:50 o 7700.75 c 7695
    16:40 o 7705.25 c 7705       16:55 o 7695    c 7693
— i.e. 16:40 DID confirm SHORT (c < o), 5 minutes before the live entry.

Litmus: if the gate goes back to judging the developing bar — or if the frozen
`[-2]` snapshot is accepted as a "closed" bar — these go RED.
"""
from datetime import datetime, timedelta, timezone

from backend.v9.systems.opening_entry import (
    DEVELOPING_BAR_MAX_AGE_S,
    confirmation_bars,
    opening_first_trade_ok,
)

NOW = datetime(2026, 9, 18, 13, 45, 8, tzinfo=timezone.utc)   # 16:45:08 IL


def _snap(il_hhmm, o, c):
    """A FROZEN first-push snapshot exactly as _oe_bars stores it."""
    h, m = il_hhmm
    ts = datetime(2026, 9, 18, h - 3, m, tzinfo=timezone.utc)  # IL = UTC+3
    return {"ts": ts.isoformat(), "o": o, "h": max(o, c), "l": min(o, c), "c": c, "v": 100}


# The four frozen snapshots the live gate actually saw on 18.09 (o≈c every time).
OE_BARS_1845 = [_snap((16, 30), 7710, 7710.25), _snap((16, 35), 7706.75, 7706.75),
                _snap((16, 40), 7705.25, 7705.25), _snap((16, 45), 7705.0, 7705.25)]

# The canonical CLOSED bars available at 16:45:08 (ts <= now - 5min).
CLOSED_1845 = [{"ts": "2026-09-18T13:30:00+00:00", "o": 7710, "h": 7714.5, "l": 7706.25, "c": 7707},
               {"ts": "2026-09-18T13:35:00+00:00", "o": 7706.75, "h": 7708, "l": 7701.75, "c": 7705.25},
               {"ts": "2026-09-18T13:40:00+00:00", "o": 7705.25, "h": 7710.25, "l": 7703.25, "c": 7705}]


# ── the age rule: a young last bar is the developing bar ────────────────────
def test_young_last_bar_is_dropped():
    """ts = now ⇒ developing ⇒ judge [-2], not [-1]."""
    bars = [_snap((16, 30), 1, 1), _snap((16, 35), 2, 2), _snap((16, 40), 3, 3)]
    bars[-1]["ts"] = NOW.isoformat()                      # last bar is "now"
    got, src = confirmation_bars(bars, None, now_utc=NOW)
    assert src == "age"
    assert len(got) == 2 and got[-1] is bars[-2]


def test_closed_last_bar_is_kept():
    """A bar older than the developing window is a closed bar — keep it."""
    bars = [_snap((16, 30), 1, 1), _snap((16, 35), 2, 2)]
    bars[-1]["ts"] = (NOW - timedelta(seconds=DEVELOPING_BAR_MAX_AGE_S + 1)).isoformat()
    got, src = confirmation_bars(bars, None, now_utc=NOW)
    assert src == "age" and len(got) == 2 and got[-1] is bars[-1]


def test_unreadable_ts_is_not_silently_discarded():
    bars = [{"o": 1, "c": 1}, {"o": 2, "c": 2}]
    got, src = confirmation_bars(bars, None, now_utc=NOW)
    assert src == "age-unknown" and len(got) == 2


def test_canonical_closed_bars_win():
    got, src = confirmation_bars(OE_BARS_1845, CLOSED_1845, now_utc=NOW)
    assert src == "canonical" and got == CLOSED_1845


# ── min_bars counts CLOSED bars only ───────────────────────────────────────
def test_min_bars_counts_closed_bars_only():
    """3 collected bars, the last still developing ⇒ only 2 closed ⇒ hold."""
    bars = [_snap((16, 30), 7710, 7707), _snap((16, 35), 7706.75, 7705.25),
            _snap((16, 40), 7705.25, 7705.0)]
    bars[-1]["ts"] = NOW.isoformat()
    ok, why = opening_first_trade_ok(bars, "SHORT", None, now_utc=NOW)
    assert ok is False
    assert "only 2 closed bars < 3" in why, why


# ── the 18.09 golden ───────────────────────────────────────────────────────
def test_golden_18_09_confirms_short_at_1645_on_canonical_closed_bars():
    """With the canonical closed bars the 16:40 bar (o 7705.25 > c 7705.0)
    confirms SHORT at 16:45:08 — 3 closed bars, 15 minutes before the live
    entry at 17:00 @7691.25."""
    ok, why = opening_first_trade_ok(
        OE_BARS_1845, "SHORT", None, closed_bars=CLOSED_1845, now_utc=NOW)
    assert ok is True, why
    assert "3 closed bars" in why and "src=canonical" in why, why


def test_golden_18_09_frozen_snapshots_alone_cannot_confirm():
    """Documents WHY the canonical source is required: the frozen `[-2]`
    snapshot of the 16:40 bar reads c == o == 7705.25, so the age rule alone
    (the literal `[-2]` fix) still cannot confirm this drive."""
    ok, why = opening_first_trade_ok(OE_BARS_1845, "SHORT", None, now_utc=NOW)
    assert ok is False
    assert "did not confirm SHORT" in why and "src=age" in why, why


def test_golden_17_09_confirms_short_on_the_1640_close():
    """17.09 canonical bars: 16:40 o 7693 > c 7690.75 confirms SHORT once three
    bars are closed (16:30/16:35/16:40)."""
    closed = [{"ts": "2026-09-17T13:30:00+00:00", "o": 7713.5, "c": 7695.75},
              {"ts": "2026-09-17T13:35:00+00:00", "o": 7695.75, "c": 7692.75},
              {"ts": "2026-09-17T13:40:00+00:00", "o": 7693, "c": 7690.75}]
    ok, why = opening_first_trade_ok([], "SHORT", None, closed_bars=closed,
                                     now_utc=datetime(2026, 9, 17, 13, 45, tzinfo=timezone.utc))
    assert ok is True, why


# ── direction is still judged, and the binary veto still runs ──────────────
def test_wrong_direction_still_held():
    ok, why = opening_first_trade_ok(
        OE_BARS_1845, "LONG", None, closed_bars=CLOSED_1845, now_utc=NOW)
    assert ok is False and "did not confirm LONG" in why, why


def test_binary_veto_still_precedes_the_bar_check():
    ok, why = opening_first_trade_ok(
        OE_BARS_1845, "SHORT", None, closed_bars=CLOSED_1845, now_utc=NOW,
        opening_type="OPEN_DRIVE_UP")
    assert ok is False and "binary veto" in why, why
