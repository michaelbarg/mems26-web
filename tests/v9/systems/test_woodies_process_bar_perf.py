"""Regression: WoodiesSystem.process_bar must not block the BarRouter for 10s.

2026-05-20 (P30 SLOW handler fix). Before this fix, WoodiesSystem.process_bar
was logged by BarRouter as ``SLOW handler ... took 10054ms-12241ms`` whenever
a Woodies pattern fired. Root cause: ``decision_tree._load_touchpoints``
issued 5 sequential synchronous ``requests.get`` calls to localhost:8000 with
a 2s timeout each, all from inside the BarRouter's async event loop, causing
the FastAPI server to self-deadlock on its own touch-point endpoints.

This test pins the regression by exercising the worst-case (every touch-point
endpoint hangs the full timeout) and the typical-case (endpoints respond
fast) and asserting that ``process_bar`` never spends more than the documented
budget. Both cases run with a forced ``ZLR`` pattern so that decision-tree
stage A4 is exercised (the no-pattern path short-circuits before A4).

See: ``docs/reports/PROMPT_P30_WOODIES_SYSTEM_SLOW_HANDLER.md``.
"""
from __future__ import annotations

import asyncio
import sys
import time
from typing import Dict, List
from unittest.mock import MagicMock, patch

sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")

from backend.v9.systems.woodies.schemas import PatternResult
from backend.v9.systems.woodies.woodies_system import WoodiesSystem

# Legacy constant removed — chop_score background refresher replaced the budget cap
_TOUCHPOINTS_PREFETCH_BUDGET_S = 3.0


_NONEXISTENT_DB = "/tmp/test_woodies_process_bar_perf_should_not_exist.db"


def _build_system_with_history(bars: int = 50) -> WoodiesSystem:
    """Construct a WoodiesSystem prefilled with `bars` synthetic OHLC bars.

    Avoids touching the real SQLite file by skipping ``hydrate()`` — the
    in-memory OHLCV buffers are seeded directly so that ``compute_all_studies``
    has enough history to return non-zero CCI/EMA values.
    """
    sys_ = WoodiesSystem(db_path=_NONEXISTENT_DB)
    base = 7400.0
    for i in range(bars):
        sys_._highs.append(base + 1.0)
        sys_._lows.append(base - 1.0)
        sys_._closes.append(base + (i % 3) * 0.25)
        base += 0.5
    sys_.current_state["hydrated"] = True
    sys_.current_state["running"] = True
    return sys_


def _sample_bar() -> Dict:
    """A non-LIVE bar payload that does not trigger DB persists in process_bar."""
    return {
        "ts": "2026-05-20T15:00:00",
        "open": 7450.0,
        "high": 7451.0,
        "low": 7449.0,
        "close": 7450.5,
        "volume": 1000,
        "mode": "REPLAY",
    }


def _forced_pattern() -> List[PatternResult]:
    return [
        PatternResult(
            detected=True,
            pattern_id="ZLR",
            direction="LONG",
            confidence=0.8,
            group="CONTINUATION",
            entry_price=7450.0,
            stop=7448.0,
            targets=[7452.0, 7454.0],
        )
    ]


def _fake_touchpoint_response(_url, timeout=None, **_kw):
    """Mimic a healthy local touch-point endpoint with ~10ms latency."""
    time.sleep(0.01)
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "classified": True,
        "running": True,
        "data": {"day_type": "Normal"},
        "state": "EXPANDING",
        "current_zone": {"name": "NY_OPEN", "edge_class": "high"},
        "poc": 7450,
        "vah": 7460,
        "val": 7440,
        "veto_active": False,
    }
    return resp


def _hanging_touchpoint_response(_url, timeout=None, **_kw):
    """Simulate an endpoint that hangs until its caller's timeout fires."""
    time.sleep(float(timeout) if timeout else 0.5)
    raise Exception("mocked endpoint hang")


def test_process_bar_under_1s_when_touchpoints_respond_fast():
    """Typical case: endpoints respond in ~10ms → process_bar < 1000ms.

    This guards against any reintroduction of synchronous HTTP fetches that
    accidentally end up on the BarRouter's event-loop critical path. The
    BarRouter's own SLOW threshold is 100ms; 1000ms gives generous headroom.
    """
    sys_ = _build_system_with_history()

    with patch(
        "backend.v9.systems.woodies.woodies_system.detect_all_patterns",
        return_value=_forced_pattern(),
    ), patch("requests.get", side_effect=_fake_touchpoint_response):
        start = time.perf_counter()
        asyncio.run(sys_.process_bar(_sample_bar()))
        elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 1000.0, (
        f"process_bar took {elapsed_ms:.0f}ms with responsive touch-points; "
        f"the P30 SLOW handler regression bounds it at <1000ms. If you are "
        f"seeing this fail, check that decision_tree._load_touchpoints is not "
        f"making blocking HTTP calls from inside an event loop."
    )


def test_process_bar_bounded_when_all_touchpoints_hang():
    """Worst case: every touch-point endpoint hangs.

    Before the fix this was 10s+ inside the event loop. After the fix the
    HTTP work runs in a worker thread and is capped at the documented
    asyncio.wait_for budget; the bar handler must complete within that budget
    plus a small overhead for pattern detection and decision-tree evaluation.
    """
    sys_ = _build_system_with_history()

    with patch(
        "backend.v9.systems.woodies.woodies_system.detect_all_patterns",
        return_value=_forced_pattern(),
    ), patch("requests.get", side_effect=_hanging_touchpoint_response):
        start = time.perf_counter()
        asyncio.run(sys_.process_bar(_sample_bar()))
        elapsed_ms = (time.perf_counter() - start) * 1000

    # 5 endpoints * 0.5s per-request timeout + 1.0s budget headroom for the
    # rest of process_bar (compute_all_studies, pattern detection, DB writes).
    upper_bound_ms = (_TOUCHPOINTS_PREFETCH_BUDGET_S + 1.0) * 1000
    assert elapsed_ms < upper_bound_ms, (
        f"process_bar took {elapsed_ms:.0f}ms with all touch-points hung; "
        f"expected bounded by asyncio.wait_for budget "
        f"({_TOUCHPOINTS_PREFETCH_BUDGET_S:.1f}s) + 1s margin = "
        f"{upper_bound_ms:.0f}ms. Before the P30 fix this was 10000ms+."
    )


def test_process_bar_skips_touchpoint_fetch_when_no_patterns():
    """No-pattern path must not touch the network at all (A4 SKIP)."""
    sys_ = _build_system_with_history()

    with patch("requests.get") as mock_get:
        start = time.perf_counter()
        asyncio.run(sys_.process_bar(_sample_bar()))
        elapsed_ms = (time.perf_counter() - start) * 1000

    assert mock_get.call_count == 0, (
        f"process_bar made {mock_get.call_count} HTTP call(s) when no "
        f"patterns were detected; the no-pattern path must short-circuit "
        f"before touch-point fetch."
    )
    assert elapsed_ms < 500.0, (
        f"process_bar took {elapsed_ms:.0f}ms with no patterns and no HTTP; "
        f"expected <500ms."
    )


def test_load_touchpoints_refuses_sync_http_in_event_loop():
    """Sanity: _load_touchpoints inside an event loop returns degraded markers.

    This is the belt-and-suspenders guard inside decision_tree itself; even if
    process_bar forgets to pre-fetch, _load_touchpoints must never block the
    event loop on synchronous HTTP self-calls.
    """
    from backend.v9.systems.woodies.decision_tree import (
        TOUCHPOINT_ENDPOINTS,
        WoodiesDecisionContext,
        _load_touchpoints,
    )

    ctx = WoodiesDecisionContext(
        bars=[],
        studies={},
        patterns=[],
        classification="NO_SETUP",
        direction=None,
        sizing="reject",
        current_state={},
        touchpoints=None,
    )

    async def _call():
        with patch("requests.get") as mock_get:
            fetched, unavailable = _load_touchpoints(ctx)
            return fetched, unavailable, mock_get.call_count

    fetched, unavailable, http_calls = asyncio.run(_call())

    assert fetched == {}, "should return empty dict inside event loop"
    assert http_calls == 0, "must NOT issue HTTP calls inside an event loop"
    for name in TOUCHPOINT_ENDPOINTS:
        assert any(name in marker and "in_event_loop" in marker for marker in unavailable), (
            f"expected '{name}:in_event_loop' marker in unavailable={unavailable}"
        )
