"""Regression: P1.2 orphan-fill protection (Michael 2026-07-07).

A Sierra fill with no trade to attribute (unmapped order_id AND no active demo/live trade)
is a possible naked/untracked position (the I-62 orphan class — 07-03 trade 290, and the
07-07 order_id=8394 that was silently 'fill dropped'). It must NEVER be silent:
  * raise to CRITICAL (not WARNING) so Michael sees it,
  * record it (count + list) so the reconcile-live / System 6 orphan invariant can act,
  * do NOT fabricate a trade from a bare fill.
"""
import logging
from backend.v9.services.fill_poller import FillPoller


class _TM:
    def __init__(self, active=None):
        self._active = active or []

    def get_active_trades(self):
        return self._active


def test_orphan_fill_is_critical_and_recorded(caplog):
    fp = FillPoller(trade_manager=_TM(active=[]))          # no trade to attribute
    with caplog.at_level(logging.CRITICAL):
        fp._process_fill({"kind": "ENTRY", "order_id": 8394, "price": 7578.5, "ts": 1783421136})
    assert fp.get_stats()["orphan_fills"] == 1
    orphans = fp.get_orphan_fills()
    assert orphans and orphans[0]["order_id"] == 8394 and orphans[0]["price"] == 7578.5
    assert any(r.levelno == logging.CRITICAL and "ORPHAN FILL" in r.getMessage()
               for r in caplog.records), "orphan must log at CRITICAL"


def test_orphan_list_capped_but_count_cumulative():
    fp = FillPoller(trade_manager=_TM(active=[]))
    for i in range(60):
        fp._process_fill({"kind": "STOP", "order_id": i, "price": 7500, "ts": 1})
    assert fp.get_stats()["orphan_fills"] == 60      # count is cumulative (never loses one)
    assert len(fp.get_orphan_fills()) == 50          # list is bounded (no unbounded growth)


def test_get_orphan_fills_returns_copy():
    fp = FillPoller(trade_manager=_TM(active=[]))
    fp._process_fill({"kind": "ENTRY", "order_id": 1, "price": 7500, "ts": 1})
    fp.get_orphan_fills().clear()                     # caller mutation must not wipe internal state
    assert len(fp.get_orphan_fills()) == 1
