# -*- coding: utf-8 -*-
"""Runs the REAL `_day_type_on_bar` closure of backend/main.py against a real DayTypeStateMachine.

The closure is cut out of main.py's source with `ast` and executed in a namespace that supplies its free variables
(no app boot): the machine is real, every outside touch point is a stub -- no DB, no network, no BarRouter, no clock
but the one the test sets.  Shared by the T-595 (closed bars) and the history-live-lock regression tests, so a wiring
slip in main.py (a NameError the handler's catch-all would otherwise turn into a silent WARNING) fails here.
Not a test module (no `test_` prefix): pytest does not collect it.
"""
import ast
import asyncio
import logging
import os
import sys
import textwrap
import types
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from backend.v9.services.market_clock import minutes_since_rth_open
from backend.v9.systems.day_type.schemas import BarInput
from backend.v9.systems.day_type.state_machine import DayTypeStateMachine

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
MAIN_PY = os.path.join(ROOT, "backend", "main.py")
ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")
PD = {"pd_high": 105.0, "pd_low": 95.0, "pd_close": 100.0}

# Every flag the handler, the machine and the opening lock read -- pinned so a run is the same under a bare shell and
# under `set -a; source .env` (the conftest keeps the shell's environment as the baseline).
PINNED_ENV = {
    "APP_STATE_ROOT_FIX_V1": "0", "DAYTYPE_ACCEPTANCE_DEMOTION_V1": "0", "DAYTYPE_DEMOTION_K_BARS": "3",
    "NONCONVICTION_ACTIVE_V1": "0", "REHYDRATE_CLS_BARS": "0", "S1_BAR_REFRESH_V1": "1",
    "S1_ENGINE_NEW_CLASSIFIER": "0", "S1_LIVE_RECLASS": "0", "S1_PROVISIONAL_PUBLISH_V1": "0",
    "DAYTYPE_RTH_RESET_V1": "0", "ATR_DAILY_FIX_V1": "0", "S1_PROVISIONAL_DAYTYPE": "0", "DAYTYPE_CONFIRM_BARS": "1",
    "OPENING_LOCK_PRIOR_REFS_V1": "0",
}


def et(h, m, s=0, day=19):
    """An aware ET wall-clock instant on the test day (Mon 2026-10-19)."""
    return datetime(2026, 10, day, h, m, s, tzinfo=ET)


def payload(bar_start_et, o, h, l, c, v):
    """One push of a bar, shaped like `_flat_5min_for_router` (ts = str of the aware UTC datetime)."""
    return {"ts": str(bar_start_et.astimezone(UTC)), "o": o, "h": h, "l": l, "c": c, "vol": v,
            "open": o, "high": h, "low": l, "close": c, "volume": v, "cumulative_delta": None}


def bar_pushes(start_et, final):
    """The three pushes of a bar that opens at final[0]: the FIRST push is flat (o=h=l=c, ~1% volume) at +3 s, a
    developing one at +120 s, the LAST (final O/H/L/C/V) at +295 s.  Returns [(wall_et, payload), ...]."""
    o, h, l, c, v = final
    return [
        (start_et + timedelta(seconds=3), payload(start_et, o, o, o, o, max(1, int(v * 0.012)))),
        (start_et + timedelta(seconds=120),
         payload(start_et, o, o + 0.6 * (h - o), o - 0.6 * (o - l), (o + c) / 2.0, v // 2)),
        (start_et + timedelta(seconds=295), payload(start_et, o, h, l, c, v)),
    ]


def load_handler(namespace):
    """Compile `_day_type_on_bar` from backend/main.py's source into `namespace` (its free variables) and return it."""
    src = open(MAIN_PY, encoding="utf-8").read()
    node = next(n for n in ast.walk(ast.parse(src))
                if isinstance(n, ast.AsyncFunctionDef) and n.name == "_day_type_on_bar")
    code = textwrap.dedent(ast.get_source_segment(src, node, padded=True))
    exec(compile(code, "<_day_type_on_bar from backend/main.py>", "exec"), namespace)
    return namespace["_day_type_on_bar"]


class _Capture(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self, level=logging.WARNING)
        self.records = []

    def emit(self, record):
        self.records.append(record)


class Harness:
    """The real handler + a real machine.  `fed` = every BarInput the machine's process_bar received (in order),
    `consumed` = the events handed to the history consumer, `warnings` = WARNING+ log records of the handler."""

    def __init__(self, monkeypatch, t595=True, machine=None):
        for k, v in PINNED_ENV.items():
            monkeypatch.setenv(k, v)
        from backend.v9.systems.day_type import closed_bar_feed as cbf, detector
        monkeypatch.setattr(detector, "S1_CVD_OPENING", False)
        monkeypatch.setattr("backend.v9.systems.day_type.state_persist.persist_state_row", lambda *a, **k: None)
        fake_tpo = types.ModuleType("backend.v9.api.v9.tpo_routes")
        fake_tpo._load_sierra_tpo = lambda: {}
        monkeypatch.setitem(sys.modules, "backend.v9.api.v9.tpo_routes", fake_tpo)

        self.clock = {"now": et(9, 20)}
        self.machine = machine or DayTypeStateMachine()
        self.fed = []
        orig = self.machine.process_bar

        def _spy(bar):
            self.fed.append(bar)
            return orig(bar)

        self.machine.process_bar = _spy
        self.consumed = []
        self.published = []
        self.cls_rth_bars = []
        self.app = types.SimpleNamespace(state=types.SimpleNamespace(tpo_system=None))
        self.logger = logging.getLogger("t595.handler.%d" % id(self))
        self.logger.propagate = False
        self._capture = _Capture()
        self.logger.addHandler(self._capture)
        self.feed = cbf.ClosedBarFeed() if t595 else None

        outer = self

        class _Consumer:
            def consume(self, event):
                outer.consumed.append(event)

        class _Router:
            async def publish(self, topic, body):
                outer.published.append((topic, body))

        self.handler = load_handler({
            "BarInput": BarInput, "S1_DYNAMIC_RECLASS": False, "_cls_ctx_cache": {"loaded": False},
            "_cls_prev_neutral": {"value": None}, "_cls_rth_bars": self.cls_rth_bars,
            "_cls_session_date": {"value": None}, "_day_type_consumer": _Consumer(),
            "_load_previous_day_context_for_startup": lambda: dict(PD), "_logger": self.logger,
            "_prev_bar_ts": {"value": None}, "_prev_day_type": {"value": "UNKNOWN"},
            "_shadow_reclass": {"instance": None}, "_t595": cbf if t595 else None, "_t595_feed": self.feed,
            "app": self.app, "bar_router": _Router(), "day_type_machine": self.machine,
            "maybe_seed_ib_from_tpo": lambda **kw: None, "minutes_since_rth_open": minutes_since_rth_open,
            "now_et": lambda: outer.clock["now"],
        })

    @property
    def warnings(self):
        return list(self._capture.records)

    def push(self, wall_et, body):
        self.clock["now"] = wall_et
        asyncio.run(self.handler(dict(body)))

    def play(self, bars):
        """bars = [(bar_start_et, final_ohlcv), ...]: three pushes each, in order."""
        for start, final in bars:
            for wall, body in bar_pushes(start, final):
                self.push(wall, body)
