"""Mirror of `frontend/v9/src/v9/lib/tradeAuxStatus.ts` aggregation.

Keep in sync with the TS implementation — if the JS algorithm changes,
update both here and in the source file. The 3 filters on /trades
(Overlap, LIVE-eligible, Confluence) rely on this math being correct;
mistakes show up as the cockpit lying about what would have fired LIVE.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

NOW_FALLBACK_SKEW_S = 5
MAX_OPEN_WINDOW_S = 2 * 60 * 60  # 2h cap — mirror of tradeAuxStatus.ts


def _parse_iso(ts: Optional[str]) -> Optional[float]:
    if not ts:
        return None
    try:
        # Match JS Date.parse behaviour: ISO 8601 → epoch seconds.
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


@dataclass
class AuxStatus:
    is_parallel: bool
    live_eligible: bool
    confluence: str  # "agree" | "disagree" | "neutral"
    blocked_by: Optional[int]


def _classify_confluence(trade: Dict[str, Any]) -> str:
    sys = trade.get("systems_agreement") or []
    if not sys:
        return "neutral"
    agrees = sum(1 for s in sys if s.get("agree") is True)
    disagrees = sum(1 for s in sys if s.get("agree") is False)
    if disagrees > 0:
        return "disagree"
    if agrees > 0:
        return "agree"
    return "neutral"


def _windows(trades: List[Dict[str, Any]], now: float) -> List[Tuple[int, float, float]]:
    out: List[Tuple[int, float, float]] = []
    for t in trades:
        start = _parse_iso(t.get("entry_ts"))
        if start is None:
            continue
        exit_ = _parse_iso(t.get("exit_ts"))
        # Mirror of tradeAuxStatus.ts: all trades without exit_ts capped at 2h.
        if exit_ is not None:
            end = max(exit_, start)
        else:
            end = min(start + MAX_OPEN_WINDOW_S, now)
        out.append((t["id"], start, end))
    return out


def compute_aux_status(
    trades: List[Dict[str, Any]],
    now: Optional[float] = None,
) -> Dict[int, AuxStatus]:
    if now is None:
        now = datetime.now(tz=timezone.utc).timestamp() + NOW_FALLBACK_SKEW_S
    windows = _windows(trades, now)
    win_by_id = {w[0]: w for w in windows}

    out: Dict[int, AuxStatus] = {}
    for t in trades:
        tid = t["id"]
        w_a = win_by_id.get(tid)
        is_parallel = False
        if w_a:
            _, a_start, a_end = w_a
            for w_b in windows:
                if w_b[0] == tid:
                    continue
                _, b_start, b_end = w_b
                if a_start < b_end and a_end > b_start:
                    is_parallel = True
                    break
        out[tid] = AuxStatus(
            is_parallel=is_parallel,
            live_eligible=False,
            confluence=_classify_confluence(t),
            blocked_by=None,
        )

    sorted_windows = sorted(windows, key=lambda w: (w[1], w[0]))
    active_end = float("-inf")
    active_id: Optional[int] = None
    for tid, start, end in sorted_windows:
        aux = out.get(tid)
        if aux is None:
            continue
        if start >= active_end:
            aux.live_eligible = True
            aux.blocked_by = None
            active_end = end
            active_id = tid
        else:
            aux.live_eligible = False
            aux.blocked_by = active_id
    return out


# ── helpers / fixtures ──────────────────────────────────────────────────────


def _t(
    id_: int,
    entry: Optional[str],
    exit_: Optional[str] = None,
    *,
    sa: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    return {
        "id": id_,
        "entry_ts": entry,
        "exit_ts": exit_,
        "systems_agreement": sa or [],
    }


_NOW = _parse_iso("2026-05-21T20:00:00Z") or 0.0


# ── overlap (time) ──────────────────────────────────────────────────────────


def test_overlap_marks_concurrent_trades_as_parallel() -> None:
    trades = [
        _t(1, "2026-05-21T10:00:00Z", "2026-05-21T10:30:00Z"),
        _t(2, "2026-05-21T10:15:00Z", "2026-05-21T10:45:00Z"),  # overlaps 1
        _t(3, "2026-05-21T11:00:00Z", "2026-05-21T11:30:00Z"),  # alone
    ]
    aux = compute_aux_status(trades, now=_NOW)
    assert aux[1].is_parallel is True
    assert aux[2].is_parallel is True
    assert aux[3].is_parallel is False


def test_back_to_back_trades_are_not_parallel() -> None:
    """Trade B starts exactly when A exits — strict inequality means not overlap."""
    trades = [
        _t(1, "2026-05-21T10:00:00Z", "2026-05-21T10:30:00Z"),
        _t(2, "2026-05-21T10:30:00Z", "2026-05-21T10:45:00Z"),
    ]
    aux = compute_aux_status(trades, now=_NOW)
    assert aux[1].is_parallel is False
    assert aux[2].is_parallel is False


def test_open_trade_uses_now_as_exit_for_overlap() -> None:
    """OPEN trade (no state=PARTIAL) with no exit_ts → window extends to now.
    Trade 2 starts at 19:00, now=20:00; trade 1 window=18:00-20:00 → overlap."""
    trades = [
        _t(1, "2026-05-21T18:00:00Z", None),          # OPEN (no state)
        _t(2, "2026-05-21T19:00:00Z", "2026-05-21T19:30:00Z"),
    ]
    aux = compute_aux_status(trades, now=_NOW)
    assert aux[1].is_parallel is True
    assert aux[2].is_parallel is True


def test_partial_trade_no_exit_ts_capped_at_30min() -> None:
    """PARTIAL trades with no exit_ts are capped at 30 min — they should NOT
    mark trades from hours later as parallel. (Reproduces the real bug where
    stuck PARTIAL trades from 11:29 marked S2 trade at 14:32 as parallel.)"""
    # Trade 1: PARTIAL, 11:29, no exit_ts → window 11:29-11:59 (capped 30 min)
    # Trade 2: S2, 14:32-14:35 → window 14:32-14:35 (no overlap with trade 1)
    t1_entry = "2026-05-21T11:29:00Z"
    t2_entry = "2026-05-21T14:32:00Z"
    t2_exit  = "2026-05-21T14:35:00Z"
    trades = [
        {**_t(1, t1_entry, None), "state": "PARTIAL"},
        _t(2, t2_entry, t2_exit),
    ]
    aux = compute_aux_status(trades, now=_NOW)
    assert aux[2].is_parallel is False, (
        "S2 trade at 14:32 should NOT be parallel with stale PARTIAL at 11:29"
    )


# ── LIVE-eligible (sequential gating) ───────────────────────────────────────


def test_live_eligible_only_actually_taken_trades_block_later_ones() -> None:
    """Critical LIVE-gating invariant: if T2 was skipped (blocked by T1),
    T2 doesn't occupy the slot. So T3 can fire as soon as T1 closes,
    even if T2's shadow window is still 'open' on paper.
    """
    trades = [
        _t(1, "2026-05-21T10:00:00Z", "2026-05-21T10:30:00Z"),
        _t(2, "2026-05-21T10:15:00Z", "2026-05-21T10:45:00Z"),  # overlap of 1 → skipped
        _t(3, "2026-05-21T10:31:00Z", "2026-05-21T10:50:00Z"),  # T1 already closed → eligible
        _t(4, "2026-05-21T10:40:00Z", "2026-05-21T11:30:00Z"),  # blocked by 3
    ]
    aux = compute_aux_status(trades, now=_NOW)
    assert aux[1].live_eligible is True
    assert aux[2].live_eligible is False
    assert aux[2].blocked_by == 1
    assert aux[3].live_eligible is True
    assert aux[3].blocked_by is None  # T2 was skipped, so didn't occupy the slot
    assert aux[4].live_eligible is False
    assert aux[4].blocked_by == 3


def test_live_eligible_resumes_after_gap() -> None:
    trades = [
        _t(1, "2026-05-21T09:00:00Z", "2026-05-21T09:30:00Z"),
        _t(2, "2026-05-21T10:00:00Z", "2026-05-21T10:30:00Z"),
        _t(3, "2026-05-21T11:00:00Z", "2026-05-21T11:30:00Z"),
    ]
    aux = compute_aux_status(trades, now=_NOW)
    assert all(aux[i].live_eligible for i in (1, 2, 3))
    assert all(aux[i].blocked_by is None for i in (1, 2, 3))


def test_live_eligible_handles_out_of_order_input() -> None:
    """Trades from /api/v9/trades come back DESC; the algorithm must still
    process them in chronological order."""
    trades = [
        _t(3, "2026-05-21T11:00:00Z", "2026-05-21T11:30:00Z"),
        _t(2, "2026-05-21T10:15:00Z", "2026-05-21T10:45:00Z"),
        _t(1, "2026-05-21T10:00:00Z", "2026-05-21T10:30:00Z"),
    ]
    aux = compute_aux_status(trades, now=_NOW)
    assert aux[1].live_eligible is True
    assert aux[2].live_eligible is False
    assert aux[3].live_eligible is True


def test_open_trade_blocks_all_later_starts() -> None:
    """If the first trade never closed, every later trade should be skipped."""
    trades = [
        _t(1, "2026-05-21T08:00:00Z", None),
        _t(2, "2026-05-21T08:30:00Z", "2026-05-21T08:45:00Z"),
        _t(3, "2026-05-21T09:00:00Z", "2026-05-21T09:30:00Z"),
    ]
    aux = compute_aux_status(trades, now=_NOW)
    assert aux[1].live_eligible is True
    assert aux[2].live_eligible is False
    assert aux[2].blocked_by == 1
    assert aux[3].live_eligible is False
    assert aux[3].blocked_by == 1


# ── confluence (systems_agreement) ──────────────────────────────────────────


def test_confluence_all_agree_when_no_system_opposes() -> None:
    sa = [
        {"id": 1, "agree": True},
        {"id": 2, "agree": True},
        {"id": 3, "agree": None},  # neutral — doesn't disqualify
    ]
    aux = compute_aux_status([_t(1, "2026-05-21T10:00:00Z", sa=sa)], now=_NOW)
    assert aux[1].confluence == "agree"


def test_confluence_disagree_if_any_system_opposes() -> None:
    sa = [
        {"id": 1, "agree": True},
        {"id": 2, "agree": True},
        {"id": 3, "agree": False},  # one opposer is enough
    ]
    aux = compute_aux_status([_t(1, "2026-05-21T10:00:00Z", sa=sa)], now=_NOW)
    assert aux[1].confluence == "disagree"


def test_confluence_neutral_when_no_signal_at_all() -> None:
    sa = [{"id": i, "agree": None} for i in range(1, 7)]
    aux = compute_aux_status([_t(1, "2026-05-21T10:00:00Z", sa=sa)], now=_NOW)
    assert aux[1].confluence == "neutral"


def test_confluence_neutral_when_systems_agreement_missing() -> None:
    aux = compute_aux_status([_t(1, "2026-05-21T10:00:00Z")], now=_NOW)
    assert aux[1].confluence == "neutral"


# ── integration: realistic shadow burst ─────────────────────────────────────


def test_three_axis_combination_on_a_realistic_shadow_burst() -> None:
    """Two shadow trades fire 2 seconds apart (both Woodies) while a third
    runs an hour later. Only one would actually run in LIVE."""
    sa_strong = [
        {"id": 1, "agree": True},
        {"id": 4, "agree": True},
        {"id": 6, "agree": None},
    ]
    sa_opposed = [
        {"id": 1, "agree": True},
        {"id": 4, "agree": True},
        {"id": 6, "agree": False},
    ]
    trades = [
        _t(101, "2026-05-21T10:00:00Z", "2026-05-21T10:30:00Z", sa=sa_strong),
        _t(102, "2026-05-21T10:00:02Z", "2026-05-21T10:25:00Z", sa=sa_opposed),
        _t(103, "2026-05-21T12:00:00Z", "2026-05-21T12:15:00Z", sa=sa_strong),
    ]
    aux = compute_aux_status(trades, now=_NOW)

    assert aux[101].is_parallel is True
    assert aux[102].is_parallel is True
    assert aux[103].is_parallel is False

    assert aux[101].live_eligible is True
    assert aux[102].live_eligible is False
    assert aux[102].blocked_by == 101
    assert aux[103].live_eligible is True

    assert aux[101].confluence == "agree"
    assert aux[102].confluence == "disagree"
    assert aux[103].confluence == "agree"
