"""FIX-2 · STOP_WINDOW_COMPLETED_V1 — the S2 structural-stop window must read the
COMPLETED-bar buffer, not the live buffer whose last element is the just-opened
PARTIAL/opening bar (window off-by-one).

Bug (audit-confirmed): in `five_min_system.process_bar`, entry is taken from the
COMPLETED detection bar (`_det_buf[-1]`), but the STOP-anchor window used the LIVE
buffer: `window_bars = self._bar_buffer[-a["window"]:]`. `self._bar_buffer[-1]` is
the partial bar the bridge just opened (range ~= 0). For `window: 1` families
(Flag / OFA_Initiative / ZLR) the window is then ONLY that partial bar, so the
structural distance collapses to ~the 3-tick offset -> the ATR floor always binds
-> too-tight stops / premature wick-outs. `_det_buf` (= `self._bar_buffer[:-1]`
when >= 8 bars) already excludes the partial bar; the fix routes the window through
it under the new default-OFF flag `STOP_WINDOW_COMPLETED_V1`.

What these tests prove, using the REAL production primitives the call site invokes
(`resolver.resolve_anchor_from_window` at line ~1239 + `adaptive_stop.compute_stop_v2`
at line ~1252) and the REAL config (`load_stop_anchors` -> Flag window/offset) and
the REAL flag reader (`shared.atr.flag`):

  (a) flag OFF -> window = the PARTIAL bar -> tiny structural distance -> ATR floor
      binds (today's behavior, and byte-identical to `self._bar_buffer[-window:]`);
  (b) flag ON  -> window = the COMPLETED bar -> real structural distance (wider,
      correct, structural stop wins over the floor).

RED-on-revert: `test_production_source_wires_completed_bar_window` reads
five_min_system.py and fails if the flag branch is removed, tying the behavioral
proof above to the actual production line (not a private re-implementation).

Runnable standalone: `python3 backend/v9/tests/test_stop_window_completed_bar.py`
or `python3 -m pytest backend/v9/tests/test_stop_window_completed_bar.py -v`.
"""
import contextlib
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

# Real production primitives — the exact functions process_bar calls at the site
# being fixed. No re-implementation of the stop math.
from backend.v9.config_loader import load_stop_anchors  # noqa: E402
from backend.v9.systems.stop_anchors.resolver import resolve_anchor_from_window  # noqa: E402
from backend.v9.systems.five_min.adaptive_stop import (  # noqa: E402
    compute_stop_v2,
    compute_today_typical,
    get_floor_ticks,
    MES_TICK,
)
from backend.v9.shared.atr import flag  # noqa: E402

_FLAG = "STOP_WINDOW_COMPLETED_V1"


@contextlib.contextmanager
def _env(value):
    """Set/clear the FIX-2 flag for the duration of a block, then restore.

    value=None clears it (default OFF); value="1" turns it ON.
    """
    saved = os.environ.get(_FLAG)
    try:
        if value is None:
            os.environ.pop(_FLAG, None)
        else:
            os.environ[_FLAG] = value
        yield
    finally:
        if saved is None:
            os.environ.pop(_FLAG, None)
        else:
            os.environ[_FLAG] = saved


def _flag_anchor():
    """Real config for a window:1 family (Flag = breakout_bar, window 1, offset 3T)."""
    cfg = load_stop_anchors()
    assert cfg is not None, "config/stop_anchors.yaml must load (14 anchors, valid schema)"
    a = cfg["anchors"]["Flag"]
    assert a.get("window") == 1 and a["type"] == "breakout_bar", (
        f"test premise: Flag must be a window:1 breakout_bar anchor, got {a}"
    )
    offset = cfg["principles"]["anchor_offset_ticks"]
    return a, offset, a["window"]


def _long_buffer():
    """20-bar buffer: 18 flat completed bars, 1 completed bar with a REAL structural
    low (4990, ~11pt below entry), then a tiny PARTIAL/opening bar (range 0 at entry).

    Mirrors the live `_bar_buffer` (cap 20); `_det_buf` is the production expression
    `buffer[:-1]` (>= 8 bars) which drops the partial bar.
    """
    buf = [{"o": 5000, "h": 5000.5, "l": 4999.5, "c": 5000, "v": 300, "ts": i}
           for i in range(18)]
    buf.append({"o": 5000, "h": 5001, "l": 4990, "c": 5000, "v": 2000, "ts": 18})  # last COMPLETED
    buf.append({"o": 5000, "h": 5000, "l": 5000, "c": 5000, "v": 5, "ts": 19})     # PARTIAL opening
    det = buf[:-1] if len(buf) >= 8 else buf                                        # production expr
    entry = det[-1]["c"]                                                            # entry = completed close
    today_typical = compute_today_typical(buf)
    return buf, det, entry, today_typical


def _short_buffer():
    """Mirror of _long_buffer for SHORT: last completed bar has a REAL structural
    high (5010, ~10pt above entry); partial bar is tiny at entry."""
    buf = [{"o": 5000, "h": 5000.5, "l": 4999.5, "c": 5000, "v": 300, "ts": i}
           for i in range(18)]
    buf.append({"o": 5000, "h": 5010, "l": 4999.5, "c": 5000, "v": 2000, "ts": 18})  # last COMPLETED
    buf.append({"o": 5000, "h": 5000, "l": 5000, "c": 5000, "v": 5, "ts": 19})       # PARTIAL opening
    det = buf[:-1] if len(buf) >= 8 else buf
    entry = det[-1]["c"]
    today_typical = compute_today_typical(buf)
    return buf, det, entry, today_typical


def _select_window_like_production(buffer, det_buf, window):
    """Byte-for-byte mirror of the fixed call site (five_min_system.py ~L1236-1240):

        if _flag("STOP_WINDOW_COMPLETED_V1"):
            window_bars = _det_buf[-a["window"]:]
        else:
            window_bars = self._bar_buffer[-a["window"]:]

    Uses the REAL `flag()` reader so the env toggle drives the branch exactly as
    production does. `test_production_source_wires_completed_bar_window` pins the
    production source to this same branch (RED-on-revert).
    """
    if flag(_FLAG):
        return det_buf[-window:]
    return buffer[-window:]


def _resolve_and_stop(win, direction, entry, today_typical, offset, family="Flag"):
    """Run the window through the REAL resolver + REAL V2 stop, as process_bar does."""
    struct = resolve_anchor_from_window(win, direction, offset)
    return compute_stop_v2(
        entry_price=entry,
        direction=direction,
        structural_stop_price=struct,
        family=family,
        today_typical=today_typical,
    )


# ── (0) flag defaults OFF ────────────────────────────────────────────────────
def test_flag_defaults_off():
    with _env(None):
        assert flag(_FLAG) is False, "STOP_WINDOW_COMPLETED_V1 must default OFF (opt-in)"


# ── (a) flag OFF -> window is the PARTIAL bar -> ATR floor binds (today) ──────
def test_off_selects_partial_bar_and_floor_binds():
    _a, offset, window = _flag_anchor()
    buf, det, entry, tt = _long_buffer()
    floor = get_floor_ticks(None)  # atr_5m=None path, matching the call site

    with _env(None):  # OFF (default)
        win = _select_window_like_production(buf, det, window)
        # OFF must select exactly the live-buffer tail (byte-identical to today).
        assert win == buf[-window:] == [buf[-1]], "OFF must window the live buffer (partial bar)"
        assert win[0]["l"] == 5000, "the partial/opening bar has range ~0 at entry"
        comp = _resolve_and_stop(win, "LONG", entry, tt, offset)

    assert comp.floor_applied is True, "partial-bar window collapses distance -> ATR floor binds"
    assert comp.risk_ticks == floor, f"floor should bind at {floor}t, got {comp.risk_ticks}t"
    # ~offset-only structural distance (well under a point) — the too-tight stop.
    assert abs(entry - comp.stop_price) <= (floor * MES_TICK) + 1e-9


# ── (b) flag ON -> window is the COMPLETED bar -> structural wins (wider) ─────
def test_on_selects_completed_bar_and_structural_wins():
    _a, offset, window = _flag_anchor()
    buf, det, entry, tt = _long_buffer()
    floor = get_floor_ticks(None)

    with _env("1"):  # ON
        win = _select_window_like_production(buf, det, window)
        # ON must select the completed-bar tail (excludes the partial bar).
        assert win == det[-window:] == [det[-1]] == [buf[-2]], "ON must window the completed buffer"
        assert win[0]["l"] == 4990, "the completed bar carries the real structural low"
        comp = _resolve_and_stop(win, "LONG", entry, tt, offset)

    assert comp.floor_applied is False, "real structural distance must exceed the floor (no floor-bind)"
    assert comp.risk_ticks > floor, f"structural risk must beat the {floor}t floor, got {comp.risk_ticks}t"
    # struct = 4990 - 3T = 4989.25 -> 10.75pt = 43 ticks from entry 5000.
    assert comp.risk_ticks == 43 and comp.stop_price == 4989.25


# ── (c) the money test: same buffer, OFF vs ON stop distance differs ─────────
def test_on_vs_off_stop_distance_differs_long():
    _a, offset, window = _flag_anchor()
    buf, det, entry, tt = _long_buffer()
    floor = get_floor_ticks(None)

    with _env(None):
        off = _resolve_and_stop(_select_window_like_production(buf, det, window),
                                "LONG", entry, tt, offset)
    with _env("1"):
        on = _resolve_and_stop(_select_window_like_production(buf, det, window),
                               "LONG", entry, tt, offset)

    off_dist = abs(entry - off.stop_price)
    on_dist = abs(entry - on.stop_price)

    # OFF binds the floor (tiny); ON honors the real structure (wide).
    assert off.floor_applied is True and off.risk_ticks == floor
    assert on.floor_applied is False and on.risk_ticks > floor
    # The fix widens the stop: ON must be strictly wider than OFF, and (LONG) deeper.
    assert on.risk_ticks > off.risk_ticks, (on.risk_ticks, off.risk_ticks)
    assert on_dist > off_dist, (on_dist, off_dist)
    assert on.stop_price < off.stop_price, "LONG: ON stop sits below (further from) entry"
    # Concrete magnitudes (verified against the real primitives): 1.0pt vs 10.75pt.
    assert round(off_dist, 2) == 1.0 and round(on_dist, 2) == 10.75


# ── (d) SHORT mirror ─────────────────────────────────────────────────────────
def test_on_vs_off_stop_distance_differs_short():
    _a, offset, window = _flag_anchor()
    buf, det, entry, tt = _short_buffer()
    floor = get_floor_ticks(None)

    with _env(None):
        off = _resolve_and_stop(_select_window_like_production(buf, det, window),
                                "SHORT", entry, tt, offset)
    with _env("1"):
        on = _resolve_and_stop(_select_window_like_production(buf, det, window),
                               "SHORT", entry, tt, offset)

    assert off.floor_applied is True and off.risk_ticks == floor
    assert on.floor_applied is False and on.risk_ticks > floor
    assert abs(entry - on.stop_price) > abs(entry - off.stop_price)
    assert on.stop_price > off.stop_price, "SHORT: ON stop sits above (further from) entry"
    assert on.stop_price == 5010.75  # 5010 + 3T offset


# ── (e) RED-on-revert: production really wires the completed-bar window ───────
def test_production_source_wires_completed_bar_window():
    src_path = os.path.abspath(os.path.join(
        _HERE, "..", "systems", "five_min", "five_min_system.py"))
    with open(src_path, encoding="utf-8") as fh:
        src = fh.read()
    # The flag must gate the window selection.
    assert _FLAG in src, "five_min_system.py must reference STOP_WINDOW_COMPLETED_V1"
    # ON path routes through the completed-bar buffer.
    assert '_det_buf[-a["window"]:]' in src, "ON path must window _det_buf (completed bars)"
    # OFF path preserved (byte-identical to today's live-buffer window).
    assert 'self._bar_buffer[-a["window"]:]' in src, "OFF path must keep the live-buffer window"


if __name__ == "__main__":
    _tests = [v for k, v in sorted(globals().items())
              if k.startswith("test_") and callable(v)]
    _failed = 0
    for _t in _tests:
        try:
            _t()
            print(f"  ok   - {_t.__name__}")
        except Exception as e:  # noqa: BLE001
            _failed += 1
            print(f"  FAIL - {_t.__name__}: {e!r}")
    print(f"\ntest_stop_window_completed_bar.py: {len(_tests) - _failed}/{len(_tests)} passed")
    sys.exit(1 if _failed else 0)
