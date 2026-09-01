"""T-10 — fill `v9_trades.pnl_sierra` from the Sierra fills journal.

`pnl_usd` is **our own arithmetic**; it is the claim, not the evidence. Until a
trade also carries `pnl_sierra` there is nothing to check it against, and a
books-vs-broker divergence stays invisible until someone reads a journal by
hand. That is how #749 shipped a $52.50 error into the money-research numbers,
and how 2026-08-14 got there before it (books -$135 vs broker +$120).

**Correlation needs no DLL change.** The journal's ENTRY line already carries
the parent order id *and* every per-contract child id, and the backend already
persists exactly those ids in `v9_trades.quality` (`sierra_order_id`,
`c1_target_id` … `c4_stop_id`) when Sierra acks the order. So a fill's
`order_id` resolves to a trade id through the books themselves — adding a
`trade_id` field to the journal (the original T-10 plan) would have meant
touching the DLL, i.e. a trading-surface change, for no extra information.

Money is read from Sierra ONLY (entry price, direction and every exit fill come
from the journal). The DB is used for identity, never for value.

Honest failure (CLAUDE.md Rule 1): a trade whose fills do not add up to its
entry quantity gets `pnl_sierra = None` and is reported as `incomplete`. A
partial sum written into the column would look like a verified number and would
be worse than an empty one.

Read-only by default — nothing is written unless the caller asks.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

POINT_VALUE = 5.0  # MES = $5 / point / contract

DEFAULT_JOURNAL = Path(os.getenv(
    "TRADE_FILLS_JOURNAL_PATH",
    os.path.expanduser("~/SierraChart_Data/v9_export/trade_fills_journal.jsonl"),
))

# T-193 1ג: "EXIT" added — the DLL's op=EXIT kind unrecognized by both readers.
EXIT_KINDS = ("T0", "T1", "T2", "T3", "T4", "STOP", "FLATTEN", "BE", "EXIT")

#: Every per-contract child order-id key the backend persists on a trade.
#: Four OCO groups cover every ruled size (contract_size.LADDER, 1/2/2/1 at six);
#: c5/c6 are accepted so a future DLL cannot silently drop out of the map.
_CHILD_ID_KEYS = ["sierra_order_id"] + [
    f"c{i}_{side}_id" for i in range(1, 7) for side in ("target", "stop")
]


# --------------------------------------------------------------- journal io

def load_journal(path: Optional[Path] = None) -> List[dict]:
    """Parse the append-only fills journal. Bad lines are skipped, not fatal."""
    p = Path(path) if path is not None else DEFAULT_JOURNAL
    if not p.exists():
        return []
    out: List[dict] = []
    with open(p, "r", encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            try:
                obj = json.loads(ln)
            except (ValueError, TypeError):
                continue
            if isinstance(obj, dict) and obj.get("kind"):
                out.append(obj)
    return out


# ------------------------------------------------------------- correlation

def order_index(rows: Iterable[Any]) -> Dict[int, int]:
    """`sierra order id → trade id`, built from what the backend already stored.

    Every id the DLL handed us at submit/entry time is registered, so a fill on
    any leg of the bracket resolves to its trade.
    """
    idx: Dict[int, int] = {}
    for r in rows:
        tid = _get(r, "id")
        q = _get(r, "quality")
        if tid is None or not isinstance(q, dict):
            continue
        for k in _CHILD_ID_KEYS:
            v = q.get(k)
            if v in (None, 0, "0"):
                continue
            try:
                idx[int(v)] = int(tid)
            except (TypeError, ValueError):
                continue
    return idx


def sierra_pnl_by_trade(fills: List[dict],
                        rows: Iterable[Any]) -> Dict[int, dict]:
    """Realized P&L per trade id, computed from Sierra fills alone.

    Returns `{trade_id: {pnl, contracts, covered, complete, entry_price,
    direction, legs}}`. `pnl` is None whenever the legs do not account for the
    whole entry quantity — see the module docstring on honest failure.
    """
    idx = order_index(rows)
    acc: Dict[int, dict] = {}

    for f in fills:
        kind = str(f.get("kind", "")).upper()
        oid = f.get("order_id")
        try:
            oid = int(oid) if oid is not None else None
        except (TypeError, ValueError):
            oid = None
        tid = idx.get(oid) if oid is not None else None
        if tid is None:
            continue  # manual / pre-registration fill — never guessed at

        if kind == "ENTRY":
            acc[tid] = {
                "entry_price": _f(f.get("price")),
                "direction": str(f.get("direction", "")).upper() or None,
                "contracts": _i(f.get("contracts")) or 0,
                "entry_order_id": oid,
                "legs": [],
            }
        elif kind in EXIT_KINDS:
            t = acc.get(tid)
            if t is None:
                continue  # exit with no ENTRY in this journal window
            t["legs"].append({
                "kind": kind, "order_id": oid,
                "price": _f(f.get("price")),
                "qty": _i(f.get("contracts")) or 0,
                "ts": f.get("ts"),
            })

    out: Dict[int, dict] = {}
    for tid, t in acc.items():
        entry, direction = t["entry_price"], t["direction"]
        legs = [l for l in t["legs"] if l["price"] is not None and l["qty"] > 0]
        covered = sum(l["qty"] for l in legs)
        complete = bool(t["contracts"]) and covered == t["contracts"]
        pnl = None
        if entry is not None and direction in ("LONG", "SHORT") and complete:
            sign = 1.0 if direction == "LONG" else -1.0
            pnl = round(sum((l["price"] - entry) * sign * POINT_VALUE * l["qty"]
                            for l in legs), 2)
        out[tid] = {
            "pnl": pnl, "entry_price": entry, "direction": direction,
            "contracts": t["contracts"], "covered": covered,
            "complete": complete, "entry_order_id": t["entry_order_id"],
            "legs": legs,
        }
    return out


# --------------------------------------------------------------- reconcile

def reconcile(rows: Iterable[Any], fills: Optional[List[dict]] = None,
              tol: float = 0.01) -> List[dict]:
    """Compare each trade's books against Sierra's fills.

    Pure — takes rows + journal lines, returns findings. `tol` is in dollars.
    """
    rows = list(rows)
    if fills is None:
        fills = load_journal()
    by_trade = sierra_pnl_by_trade(fills, rows)

    findings: List[dict] = []
    for r in rows:
        tid = _get(r, "id")
        s = by_trade.get(tid)
        if s is None:
            continue  # no Sierra fills correlate to this trade at all
        books = _f(_get(r, "pnl_usd"))
        delta = None if (s["pnl"] is None or books is None) else round(
            books - s["pnl"], 2)
        findings.append({
            "trade_id": tid,
            "mode": _get(r, "mode"),
            "exit_reason": _get(r, "exit_reason"),
            "pnl_books": books,
            "pnl_sierra": s["pnl"],
            "delta": delta,
            "contracts": s["contracts"],
            "covered": s["covered"],
            "status": ("incomplete" if not s["complete"]
                       else "MATCH" if (delta is not None and abs(delta) <= tol)
                       else "DIVERGENT"),
            "legs": s["legs"],
        })
    return findings


def divergence_summary(rows: Iterable[Any], fills: Optional[List[dict]] = None,
                       tol: float = 0.01) -> dict:
    """The one-call check a daily report / EOD can render.

    `ok` is False as soon as ANY reconcilable trade's books disagree with the
    broker — that is the alarm this whole module exists to raise.

    `ok` is **None**, never True, when nothing could be checked at all. During
    development this exact function answered `{"ok": true, "checked": 0}` after
    `db.read` silently fell back to a stale SQLite file with no `pnl_sierra`
    column: a green light nobody earned, which is the failure class this whole
    task exists to end.
    """
    f = reconcile(rows, fills=fills, tol=tol)
    div = [x for x in f if x["status"] == "DIVERGENT"]
    inc = [x for x in f if x["status"] == "incomplete"]
    matched = [x for x in f if x["status"] == "MATCH"]
    worst = max(div, key=lambda x: abs(x["delta"] or 0), default=None)
    # A6: incomplete trades are a reconciliation FAILURE (not a skip).
    # 08-21: 4/7 trades had missing exit fills → phantom-heal → blocked entries.
    return {
        "ok": (not div and not inc) if f else None,
        "checked": len(f),
        "matched": len(matched),
        "divergent": len(div),
        "incomplete": len(inc),
        "books_total": round(sum(x["pnl_books"] or 0 for x in f
                                 if x["pnl_sierra"] is not None), 2),
        "sierra_total": round(sum(x["pnl_sierra"] or 0 for x in f), 2),
        "net_error": round(sum(x["delta"] or 0 for x in f), 2),
        # T-193 4: unpriced_contracts — the money that disappeared contributes
        # 0.00 to net_error because delta=None. This counter makes the gap
        # visible: "net_error=+0.00 BUT 13 contracts have no Sierra price."
        "unpriced_contracts": sum(
            (x.get("contracts") or 0) - (x.get("covered") or 0)
            for x in inc),
        "worst": ({"trade_id": worst["trade_id"], "delta": worst["delta"],
                   "books": worst["pnl_books"], "sierra": worst["pnl_sierra"]}
                  if worst else None),
        "divergent_trades": [x["trade_id"] for x in div],
    }


def write_pnl_sierra(db, findings: List[dict]) -> int:
    """Persist `pnl_sierra` for every trade whose fills fully account for it.

    Only ever writes the `pnl_sierra` column — the books (`pnl_usd`) are left
    exactly as the trading path recorded them, so this can never launder an
    error into looking correct. Returns the number of rows changed.
    """
    from backend.v9.db.models.trades import V9Trade
    n = 0
    for f in findings:
        if f["pnl_sierra"] is None:
            continue
        t = db.query(V9Trade).filter(V9Trade.id == f["trade_id"]).first()
        if t is None or t.pnl_sierra == f["pnl_sierra"]:
            continue
        t.pnl_sierra = f["pnl_sierra"]
        n += 1
    if n:
        db.commit()
    return n


# ----------------------------------------------------------------- helpers

def _get(row, key):
    if isinstance(row, dict):
        return row.get(key)
    return getattr(row, key, None)


def _f(v) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _i(v) -> Optional[int]:
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None
