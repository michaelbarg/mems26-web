"""Anti-tautological verification for BOOT_DAYTYPE_REPLAY_V1.

Verifies the boot-replay fix added to ``backend/main.py`` inside ``_startup()``
(``_boot_replay_day_type_session``, gated behind ``BOOT_DAYTYPE_REPLAY_V1``,
guarded by ``bar_count == 0``). The fix replays today's already-persisted RTH
5-min bars from ``v9_bars_5min_woodies`` through the SAME pure engine entry
point (``DayTypeStateMachine.process_bar``), deriving each bar's ``session_min``
from that bar's real ET time via ``minutes_since_rth_open`` — so a LATE boot
reconstructs the SAME day-type state an EARLY boot would have built.

This test proves BOTH halves, with no DB / app / network:

  (a) LIVE            — every bar fed one-by-one with per-bar session_min
                        (early boot that saw the whole session).
  (b) LATE_NO_REPLAY  — only the last 3 bars (the buggy late boot).
  (c) LATE_WITH_REPLAY— all bars via the replay-style loop, mirroring
                        ``_boot_replay_day_type_session`` (main.py L661-683):
                        parse each stored UTC ts -> ET -> session_min, gate
                        Sierra IB to session_min >= 60.

Assertions:
  * LATE_NO_REPLAY DIVERGES from LIVE (bug reproduced) — here on day_type
    (Normal vs Trend_Normal, because the opening is (mis)detected from the
    last 3 bars) AND on bar_count (3 vs full session).
  * LATE_WITH_REPLAY EQUALS LIVE on stage, day_type, ib_high, ib_low,
    bar_count (fix proven).

Anti-tautology: the test can genuinely fail. If the engine were insensitive
to how many bars it saw, (b) would match LIVE and the divergence assertion
would fail. If the replay derived session_min from ``now()`` (or used a wrong
IB gate / TZ), (c) would NOT match LIVE and the equality assertion would fail.
"""

from datetime import date, datetime, time as dtime, timedelta
from zoneinfo import ZoneInfo

import pytest

from backend.v9.systems.day_type import detector as _detector
from backend.v9.systems.day_type.schemas import BarInput, DayType, Stage
from backend.v9.systems.day_type.state_machine import DayTypeStateMachine
from backend.v9.services.market_clock import minutes_since_rth_open

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

# Fixed, holiday-agnostic weekday. minutes_since_rth_open() and the is_rth
# check are pure functions of the bar's ET clock time, so the calendar date
# only needs to be a normal weekday.
SESSION_DATE = date(2026, 7, 13)  # Monday

IB_LOCK_MIN = 60  # Sierra IB locks at session_min 60 (10:30 ET) — matches config.ib_period_min

# Previous-day context (fed on every bar exactly as the live path feeds pd_ctx).
# Wide enough that every bar's open sits INSIDE [pd_low, pd_high] so the late
# rotational bars read as OPEN_AUCTION_IN (not _OUT) when detected in isolation.
_PD = dict(pd_high=5200.0, pd_low=4900.0, pd_close=4990.0)


@pytest.fixture(autouse=True)
def _neutralize_flags(monkeypatch):
    """Pin every classification-affecting flag to its documented default so the
    test reflects the engine's real default behaviour and is hermetic against
    the ambient shell environment.

    - os.environ-read flags used INSIDE process_bar / its stages.
    - detector module-level constants (bound at import from shared.atr.flag()).
    """
    monkeypatch.setenv("S1_PROVISIONAL_DAYTYPE", "0")  # _maybe_provisional_classify
    monkeypatch.setenv("DAYTYPE_RTH_RESET_V1", "0")    # process_bar FIX-9 reset
    monkeypatch.setenv("DAYTYPE_CONFIRM_BARS", "1")    # _stage_b6 anti-noise (1 = default)
    monkeypatch.setattr(_detector, "S1_CVD_OPENING", False)     # detect_opening_type_cvd
    monkeypatch.setattr(_detector, "S1_DAYTYPE_STAGING", False)  # cap_confidence_staged


# ── Deterministic synthetic session ──────────────────────────────────────

def _et_at(session_min: int) -> datetime:
    """ET datetime for a bar `session_min` minutes after the 09:30 open."""
    return datetime.combine(SESSION_DATE, dtime(9, 30), tzinfo=ET) + timedelta(minutes=session_min)


def _session_rows():
    """Build a full deterministic RTH session (session_min 0..180, 5-min bars).

    Shape:
      * Phase 1 (0..55): a clean OPEN_DRIVE up + the IB window -> opening_type
        resolves to OPEN_DRIVE and (with a wide first-hour range) IB EXTREME
        -> DECISION_MATRIX (OPEN_DRIVE, *) = Trend_Normal.
      * Phase 2 (60..165): gentle drift up; no extension flags set, so behavior
        stays DEVELOPING and the day_type holds at Trend_Normal.
      * Phase 3 (170..180): three balanced/rotational bars. Harmless mid-trend
        for LIVE, but when fed ALONE they detect as OPEN_AUCTION_IN -> Normal,
        which is what makes the late-boot bug visible on day_type.

    Returns rows shaped like a v9_bars_5min_woodies read: each carries a stored
    UTC ISO `ts` (as Postgres timestamptz would) plus the ET datetime for the
    live path.
    """
    ohlc = []  # (session_min, open, high, low, close)
    base = 5000.0

    # Phase 1 — opening drive up + IB window (12 bars, session_min 0..55)
    for i, sm in enumerate(range(0, IB_LOCK_MIN, 5)):
        o = base + i * 4.0
        ohlc.append((sm, o, o + 6.0, o - 1.0, o + 4.0))

    # Phase 2 — gentle drift up (session_min 60..165)
    o = ohlc[-1][4]
    for sm in range(IB_LOCK_MIN, 170, 5):
        o = o + 1.0
        ohlc.append((sm, o, o + 3.0, o - 2.0, o + 1.0))

    # Phase 3 — three balanced rotational bars (session_min 170..180).
    mid = o + 1.0
    ohlc.append((170, mid, mid + 3.0, mid - 3.0, mid - 1.0))
    ohlc.append((175, mid - 1.0, mid + 2.0, mid - 4.0, mid + 1.0))
    ohlc.append((180, mid + 1.0, mid + 4.0, mid - 2.0, mid))

    rows = []
    for (sm, o, h, l, c) in ohlc:
        et = _et_at(sm)
        rows.append({
            "ts": et.astimezone(UTC).isoformat(),  # stored UTC ts, like the DB
            "et": et,
            "session_min": sm,
            "open": o, "high": h, "low": l, "close": c, "volume": 500.0,
        })
    return rows


def _ib_from_first_hour(rows):
    """Sierra IB = the 09:30-10:30 (session_min < 60) high/low range."""
    fh = [r for r in rows if r["session_min"] < IB_LOCK_MIN]
    return max(r["high"] for r in fh), min(r["low"] for r in fh)


def _make_bar(session_min, is_rth, row, ib_high, ib_low):
    """Build a BarInput the way BOTH main.py paths do: Sierra IB is None until
    it locks at session_min >= 60, then the locked value (main.py L669-670 /
    the live A3 accumulation)."""
    ib_h = ib_high if session_min >= IB_LOCK_MIN else None
    ib_l = ib_low if session_min >= IB_LOCK_MIN else None
    return BarInput(
        ts=1_000_000.0 + session_min * 60,
        session_min=session_min,
        is_rth=is_rth,
        open=row["open"], high=row["high"], low=row["low"], close=row["close"],
        volume=row["volume"],
        ib_high=ib_h, ib_low=ib_l,
        **_PD,
    )


# ── The three machines ───────────────────────────────────────────────────

def _run_live(rows, ib_high, ib_low):
    """(a) Early boot: feed every bar one-by-one, session_min from the bar's
    ET wall-clock (what now_et() returns as each live bar arrives)."""
    m = DayTypeStateMachine()
    for r in rows:
        et = r["et"]
        session_min = minutes_since_rth_open(et)
        is_rth = dtime(9, 30) <= et.time() < dtime(16, 0)
        m.process_bar(_make_bar(session_min, is_rth, r, ib_high, ib_low))
    return m


def _run_replay(rows, ib_high, ib_low):
    """(c) Replay-style loop mirroring _boot_replay_day_type_session (main.py
    L661-683): each stored UTC ts -> ET -> session_min, IB gated at >= 60."""
    m = DayTypeStateMachine()
    for r in rows:
        ts = r["ts"]
        bet = (datetime.fromisoformat(ts) if isinstance(ts, str) else ts).astimezone(ET)
        session_min = minutes_since_rth_open(bet)
        is_rth = dtime(9, 30) <= bet.time() < dtime(16, 0)
        m.process_bar(_make_bar(session_min, is_rth, r, ib_high, ib_low))
    return m


@pytest.fixture
def machines():
    rows = _session_rows()
    ib_high, ib_low = _ib_from_first_hour(rows)
    return {
        "rows": rows,
        "ib": (ib_high, ib_low),
        "live": _run_live(rows, ib_high, ib_low),
        "late_no_replay": _run_replay(rows[-3:], ib_high, ib_low),   # buggy late boot: last 3 bars
        "late_with_replay": _run_replay(rows, ib_high, ib_low),      # fix: replay whole session
    }


# ── Tests ────────────────────────────────────────────────────────────────

def test_baseline_live_reaches_nontrivial_daytype(machines):
    """Setup guard: the full session must produce a NON-trivial, locked
    classification (else the divergence/equality below would be meaningless)."""
    live = machines["live"]
    assert live.ib_locked is True
    assert live.bar_count == len(machines["rows"]) == 37
    assert live.day_type != DayType.UNKNOWN
    # Non-trivial = a real trend classification, not the Normal/UNKNOWN fallback.
    assert live.day_type == DayType.Trend_Normal
    assert live.opening is not None and live.opening.opening_type.value == "OPEN_DRIVE"


def test_bug_reproduced_late_boot_diverges_from_live(machines):
    """(a) vs (b): a late boot that only sees the last ~3 bars classifies the
    session DIFFERENTLY than an early boot — the divergence the fix targets."""
    live = machines["live"]
    late = machines["late_no_replay"]

    # Required assertion (task): diverges on day_type OR bar_count.
    assert (late.day_type != live.day_type) or (late.bar_count != live.bar_count)

    # Stronger, and both hold here — document exactly HOW it diverges:
    assert late.bar_count == 3 and live.bar_count == 37            # fewer bars
    assert late.day_type == DayType.Normal                        # wrong label
    assert live.day_type == DayType.Trend_Normal
    assert late.day_type != live.day_type
    # Root of the wrong label: opening (mis)detected from the late bars.
    assert late.opening.opening_type.value == "OPEN_AUCTION_IN"
    assert live.opening.opening_type.value == "OPEN_DRIVE"


def test_fix_replay_matches_full_session(machines):
    """(a) vs (c): replaying today's bars through process_bar with each bar's
    real ET time reconstructs the SAME state as the early boot."""
    live = machines["live"]
    replay = machines["late_with_replay"]

    assert replay.stage == live.stage
    assert replay.day_type == live.day_type
    assert replay.ib_high == live.ib_high
    assert replay.ib_low == live.ib_low
    assert replay.bar_count == live.bar_count

    # And it recovered the non-trivial label the truncated late boot got wrong.
    assert replay.day_type == DayType.Trend_Normal
    assert replay.day_type != machines["late_no_replay"].day_type


def test_process_bar_is_pure_no_db_no_network(monkeypatch):
    """Side-effect proof: a full replay through process_bar opens ZERO sockets
    (no DB-over-TCP, no phone/push, no publish). process_bar mutates only
    in-memory machine state and returns a DayTypeState."""
    rows = _session_rows()
    ib_high, ib_low = _ib_from_first_hour(rows)
    # Pre-warm zoneinfo (file reads, not sockets) before arming the guard.
    _ = minutes_since_rth_open(rows[0]["et"])

    import socket

    def _no_socket(*a, **k):
        raise AssertionError(
            "process_bar opened a socket — that means a DB/network/phone side-effect"
        )

    monkeypatch.setattr(socket, "socket", _no_socket)

    m = DayTypeStateMachine()
    last_state = None
    for r in rows:
        bet = datetime.fromisoformat(r["ts"]).astimezone(ET)
        session_min = minutes_since_rth_open(bet)
        is_rth = dtime(9, 30) <= bet.time() < dtime(16, 0)
        last_state = m.process_bar(_make_bar(session_min, is_rth, r, ib_high, ib_low))

    assert m.bar_count == len(rows)
    assert last_state is not None and last_state.day_type == DayType.Trend_Normal
