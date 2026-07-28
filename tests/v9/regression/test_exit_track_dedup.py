"""EXIT_TRACK_ACTIVITY_V1 — per-contract SUM must survive, feeder duplicates must not.

Two opposite failure modes meet in this code path:

  • cursor V3 (07-27 13:36) caught it taking only `pnl_events[-1]` while Sierra
    writes ONE CLOSED_TRADE_PNL per contract → a 3-contract exit booked 1/3 of
    the loss and RISK_HALT under-counted. Fixed 07-27 14:37 (sum).
  • cowork (07-28) found the feeder re-emitted the SAME log line after any
    `strings` failure — 2363 journal events held only 309 unique ones, one
    −125.00 close repeated 117 times. Summing that batch multiplies a real loss.

The discriminator is the SOURCE LINE, not the timestamp: genuine per-contract
closes occupy different lines of one log; a re-emission repeats one line under a
new scan stamp. Keying on (ts, line) — the first proposal — would keep every
duplicate, because the timestamps differ.
"""
import json


def _collect(lines, logger=None):
    """Mirror of the collection+dedup block in fill_poller._check_activity_exits."""
    out, seen = [], set()
    for ln in lines:
        try:
            ev = json.loads(ln)
        except (ValueError, TypeError):
            continue
        if ev.get("type") != "CLOSED_TRADE_PNL":
            continue
        key = (ev.get("account"), ev.get("line"))
        if key[1] is not None:
            if key in seen:
                continue
            seen.add(key)
        out.append(ev)
    return out


def _ln(pnl, line, scan_ts="2026-07-27T17:20:00+00:00", acct="37138283"):
    return json.dumps({"type": "CLOSED_TRADE_PNL", "pnl": pnl, "line": line,
                       "scan_ts": scan_ts, "account": acct})


def test_per_contract_events_are_all_summed():
    """The 07-27 shape: a 3-contract exit = 3 lines, same scan stamp."""
    evs = _collect([_ln(-23.75, 121), _ln(-23.75, 157), _ln(-23.75, 193)])
    assert len(evs) == 3
    assert sum(e["pnl"] for e in evs) == -71.25


def test_reemitted_same_line_counted_once():
    """The feeder bug: one close, re-scanned 3× under different scan stamps."""
    evs = _collect([
        _ln(-125.0, 826, "2026-07-10T15:19:37+00:00"),
        _ln(-125.0, 826, "2026-07-10T15:20:37+00:00"),
        _ln(-125.0, 826, "2026-07-10T15:21:37+00:00"),
    ])
    assert len(evs) == 1
    assert sum(e["pnl"] for e in evs) == -125.0


def test_ts_line_key_would_have_failed():
    """Pins WHY the key is `line` alone: (ts, line) leaves all 3 duplicates."""
    raw = [json.loads(x) for x in (
        _ln(-125.0, 826, "2026-07-10T15:19:37+00:00"),
        _ln(-125.0, 826, "2026-07-10T15:20:37+00:00"),
        _ln(-125.0, 826, "2026-07-10T15:21:37+00:00"))]
    by_ts_line = {(e["scan_ts"], e["line"]) for e in raw}
    by_line = {e["line"] for e in raw}
    assert len(by_ts_line) == 3   # would NOT dedup
    assert len(by_line) == 1      # does


def test_identical_pnl_on_different_lines_kept():
    """Repeated VALUES are legitimate (per-contract) — only repeated LINES are not."""
    evs = _collect([_ln(43.75, 121), _ln(43.75, 157), _ln(43.75, 193), _ln(43.75, 193)])
    assert sum(e["pnl"] for e in evs) == 131.25


def test_events_without_line_are_not_dropped():
    """Older journal lines predate the `line` field — never silently discard."""
    a = json.dumps({"type": "CLOSED_TRADE_PNL", "pnl": -10.0})
    evs = _collect([a, a])
    assert len(evs) == 2


def test_same_line_different_accounts_both_kept():
    """Line numbers are per-file; two accounts can share one. Account is in the key."""
    evs = _collect([_ln(-10.0, 100, acct="37138283"), _ln(-20.0, 100, acct="Sim1")])
    assert len(evs) == 2


def test_fill_poller_reads_scan_ts_and_legacy_ts():
    """cowork renamed ts→scan_ts on 07-28; the consumer must read BOTH or every
    exit_ts silently falls back to now()."""
    import inspect
    import backend.v9.services.fill_poller as fp
    src = inspect.getsource(fp)
    assert 'get("scan_ts") or pnl_events[-1].get("ts")' in src
