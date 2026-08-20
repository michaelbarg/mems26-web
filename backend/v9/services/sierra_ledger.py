"""Sierra-sourced LIVE ledger (journal L8) — the ground truth for real money.

Michael (2026-07-07): the LIVE record must reflect **only what Sierra actually
EXECUTED** — reconstructed from Sierra fills, NOT from the backend's calculated
entry/stop/pnl (those are the CLAIM being verified). And a change Sierra shows
that the system did NOT command = a MANUAL intervention → detect, adopt, and tag
it (for learning). "Records ≠ reality" is the bug this module exists to catch.

Pure + stdlib-only so it is trivially unit-testable with fixtures. The route
layer (live_ledger_routes.py) feeds it the real `trade_fills.json` lines + the
backend DB rows; this module does the reconstruction, the reconcile, and the
manual-intervention tagging.

Source of truth (per the spec CC_SIERRA_LIVE_LEDGER_2026-07-07.md):
  trade_fills.json — one JSON object per line:
    {kind: ENTRY|T1|T2|T3|STOP|FLATTEN, order_id, price, ts(epoch),
     [c1_target_id..c3_stop_id on ENTRY], [account], [contracts|qty]}
  ENTRY establishes the position + its per-contract child order-ids; every later
  child fill (T1/T2/T3/STOP) shares the chain via those ids.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional

# MES micro E-mini S&P = $5 / point. Override per instrument if needed.
DEFAULT_POINT_VALUE = 5.0
EXIT_KINDS = ("T1", "T2", "T3", "STOP", "FLATTEN")


@dataclass
class Exit:
    kind: str
    price: Optional[float]
    ts: Optional[float]
    qty: Optional[int] = None


@dataclass
class LedgerTrade:
    """A trade reconstructed from Sierra fills ALONE (no backend fields)."""
    entry_order_id: Any
    account: Optional[str]
    entry_price: Optional[float]
    entry_ts: Optional[float]
    contracts: Optional[int]
    direction: Optional[str]           # inferred LONG/SHORT
    direction_source: str              # t_fill | stop_fill | unknown
    exits: list[Exit] = field(default_factory=list)
    realized_pnl: Optional[float] = None
    pnl_basis: str = "none"            # fill_qty | assumed_qty | none
    closed: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        d["exits"] = [asdict(e) for e in self.exits]
        return d


# ---------------------------------------------------------------- parsing

def parse_fills(lines: list[str]) -> list[dict]:
    """Parse JSONL trade-fills lines defensively — skip blank/garbage lines."""
    import json
    out: list[dict] = []
    for ln in lines:
        ln = (ln or "").strip()
        if not ln:
            continue
        try:
            obj = json.loads(ln)
            if isinstance(obj, dict) and obj.get("kind"):
                out.append(obj)
        except (ValueError, TypeError):
            continue
    return out


#: Every per-contract child order-id key an ENTRY line can carry. The ladder has
#: FOUR OCO groups at every ruled size (contract_size.LADDER — 1/2/2/1 at six),
#: so c1..c4 is the complete set; c5/c6 are listed only so a future DLL that
#: exports them cannot silently fall out of the chain.
_CHAIN_ID_KEYS = tuple(
    f"c{i}_{side}_id" for i in range(1, 7) for side in ("target", "stop")
)


def _entry_chain_ids(fill: dict) -> set:
    """The per-contract child order-ids that belong to an ENTRY's bracket.

    T-62 (2026-08-20): this stopped at c3 while the DLL has exported c4 since
    the 4-contract ruling, so the FOURTH contract's target/stop ids were never
    in the chain. On #749 that dropped the last stop fill (1 @ 7732.50) out of
    the trade entirely — the ledger reported realized_pnl **+26.25** instead of
    the true **+1.25**, and the orphaned fill was re-attributed to whatever
    chain happened to still be open. A ground-truth ledger that silently loses
    a contract cannot be used to check the books, which is what T-10 needs it
    for.
    """
    ids = set()
    for k in _CHAIN_ID_KEYS:
        v = fill.get(k)
        if v is not None:
            ids.add(v)
    return ids


def _infer_direction(entry: float, exits: list[Exit]) -> tuple[Optional[str], str]:
    """LONG if a target sits above entry (or the stop below it); else SHORT."""
    for e in exits:
        if e.kind in ("T1", "T2", "T3") and e.price is not None:
            return ("LONG" if e.price > entry else "SHORT"), "t_fill"
    for e in exits:
        if e.kind == "STOP" and e.price is not None:
            # a hit stop sits on the losing side: below entry ⇒ LONG
            return ("LONG" if e.price < entry else "SHORT"), "stop_fill"
    return None, "unknown"


# ------------------------------------------------------------- ledger build

def build_ledger(fills: list[dict], live_account: Optional[str] = None,
                 point_value: float = DEFAULT_POINT_VALUE) -> list[LedgerTrade]:
    """Reconstruct each trade from its fills alone.

    Grouping: each ENTRY starts a chain; its own order_id + its per-contract
    child ids map subsequent T1/T2/T3/STOP/FLATTEN fills back to that entry.
    `live_account` (when the fills carry an `account` field) filters to the LIVE
    account only — demo/shadow fills are excluded (spec test 7).
    """
    trades: list[LedgerTrade] = []
    chain_of: dict = {}   # any order_id in a chain -> index in `trades`

    for f in fills:
        acct = f.get("account")
        if live_account is not None and acct is not None and str(acct) != str(live_account):
            continue
        kind = str(f.get("kind", "")).upper()
        oid = f.get("order_id")
        price = _as_float(f.get("price"))
        ts = f.get("ts")
        qty = _as_int(f.get("contracts") if f.get("contracts") is not None else f.get("qty"))

        if kind == "ENTRY":
            lt = LedgerTrade(
                entry_order_id=oid, account=acct, entry_price=price, entry_ts=ts,
                contracts=qty, direction=None, direction_source="unknown",
            )
            idx = len(trades)
            trades.append(lt)
            chain_of[oid] = idx
            for cid in _entry_chain_ids(f):
                chain_of[cid] = idx
        elif kind in EXIT_KINDS:
            idx = chain_of.get(oid)
            if idx is None:
                # unmapped exit — attribute to the most recent open chain (loud
                # elsewhere; here we keep the ledger from silently dropping a real fill)
                idx = _most_recent_open(trades)
            if idx is not None:
                trades[idx].exits.append(Exit(kind=kind, price=price, ts=ts, qty=qty))
                if kind in ("STOP", "FLATTEN"):
                    trades[idx].closed = True

    for lt in trades:
        if lt.entry_price is not None:
            lt.direction, lt.direction_source = _infer_direction(lt.entry_price, lt.exits)
            _compute_pnl(lt, point_value)
    return trades


def _most_recent_open(trades: list[LedgerTrade]) -> Optional[int]:
    for i in range(len(trades) - 1, -1, -1):
        if not trades[i].closed:
            return i
    return None


def _compute_pnl(lt: LedgerTrade, point_value: float) -> None:
    """Realized P&L from fill prices only.

    If exits carry qty, use it (basis=fill_qty). Otherwise assume 1 contract per
    T-fill and the remainder closes at STOP/FLATTEN (basis=assumed_qty), bounded
    by the entry contract count when known.
    """
    if lt.entry_price is None or lt.direction is None:
        lt.realized_pnl, lt.pnl_basis = None, "none"
        return
    sign = 1.0 if lt.direction == "LONG" else -1.0
    have_qty = all(e.qty is not None for e in lt.exits) and len(lt.exits) > 0
    total = lt.contracts
    pnl = 0.0
    if have_qty:
        for e in lt.exits:
            if e.price is not None:
                pnl += (e.price - lt.entry_price) * sign * point_value * int(e.qty)
        lt.realized_pnl, lt.pnl_basis = round(pnl, 2), "fill_qty"
        return
    # assumed model
    remaining = total if isinstance(total, int) and total > 0 else None
    for e in lt.exits:
        if e.price is None:
            continue
        if e.kind in ("STOP", "FLATTEN"):
            q = remaining if remaining is not None else 1
        else:
            q = 1
        pnl += (e.price - lt.entry_price) * sign * point_value * q
        if remaining is not None:
            remaining = max(0, remaining - q)
    lt.realized_pnl, lt.pnl_basis = round(pnl, 2), "assumed_qty"


# --------------------------------------------------------------- reconcile

@dataclass
class Divergence:
    field: str
    sierra: Any
    backend: Any
    severity: str = "CRITICAL"


def reconcile(ledger: LedgerTrade, backend_row: dict,
              sierra_stop: Optional[float] = None,
              price_tol: float = 0.01, pnl_tol: float = 0.5) -> list[Divergence]:
    """Diff the Sierra-truth ledger against the backend DB row.

    Every differing field (entry · stop · last-exit · P&L · state · contracts) is a
    CRITICAL divergence — this is what catches L2 ("stop recorded-moved but Sierra
    didn't") and L3 (shadow shown as live). Empty list = MATCH.

    `sierra_stop` = the stop Sierra actually holds (from the TradeActivityLog
    modify history, supplied by the route/CC). When given, it is compared against
    the backend's recorded `stop` — the direct L2 check.
    """
    out: list[Divergence] = []

    if sierra_stop is not None:
        b_stop = _as_float(backend_row.get("stop"))
        if b_stop is not None and abs(sierra_stop - b_stop) > price_tol:
            out.append(Divergence("stop", sierra_stop, b_stop))

    b_entry = _as_float(backend_row.get("entry_price"))
    if ledger.entry_price is not None and b_entry is not None \
            and abs(ledger.entry_price - b_entry) > price_tol:
        out.append(Divergence("entry_price", ledger.entry_price, b_entry))

    # last exit price Sierra actually filled vs backend exit_price
    last_exit = next((e.price for e in reversed(ledger.exits) if e.price is not None), None)
    b_exit = _as_float(backend_row.get("exit_price"))
    if last_exit is not None and b_exit is not None and abs(last_exit - b_exit) > price_tol:
        out.append(Divergence("exit_price", last_exit, b_exit))

    if ledger.realized_pnl is not None and backend_row.get("pnl_usd") is not None:
        b_pnl = _as_float(backend_row.get("pnl_usd"))
        if b_pnl is not None and abs(ledger.realized_pnl - b_pnl) > pnl_tol:
            out.append(Divergence("pnl_usd", ledger.realized_pnl, b_pnl))

    b_contracts = _as_int(backend_row.get("contracts"))
    if ledger.contracts is not None and b_contracts is not None \
            and ledger.contracts != b_contracts:
        out.append(Divergence("contracts", ledger.contracts, b_contracts))

    # state: Sierra closed but backend still open ⇒ divergence (naked/records-lag)
    b_state = str(backend_row.get("state", "")).upper()
    sierra_closed = ledger.closed
    backend_closed = b_state in ("CLOSED", "STOPPED", "TARGET")
    if sierra_closed != backend_closed:
        out.append(Divergence("state", "CLOSED" if sierra_closed else "OPEN",
                              b_state or ("CLOSED" if backend_closed else "OPEN")))
    return out


# ----------------------------------------------------- manual intervention

@dataclass
class ManualEvent:
    kind: str            # MANUAL_STOP_MOVE | MANUAL_CLOSE
    detail: str
    price: Optional[float] = None
    tag: str = "MANUAL"


def detect_manual(ledger: LedgerTrade, backend_row: dict,
                  commanded_stops: Optional[list[float]] = None,
                  sierra_stop: Optional[float] = None) -> list[ManualEvent]:
    """Detect a change Sierra shows that the system did NOT initiate.

    · Sierra flat (a STOP/FLATTEN fill) but the backend still open ⇒ MANUAL_CLOSE,
      adopt Sierra's fill price.
    · Sierra's current stop ≠ any stop the backend commanded ⇒ MANUAL_STOP_MOVE,
      adopt Sierra's stop. (`sierra_stop` + `commanded_stops` come from the
      TradeActivityLog / management log — supplied by the route/CC.)
    Never overwrite silently; tag MANUAL vs SYSTEM.
    """
    events: list[ManualEvent] = []
    b_state = str(backend_row.get("state", "")).upper()
    backend_open = b_state not in ("CLOSED", "STOPPED", "TARGET", "CANCELLED")

    if ledger.closed and backend_open:
        px = next((e.price for e in reversed(ledger.exits) if e.price is not None), None)
        events.append(ManualEvent("MANUAL_CLOSE",
                                  f"Sierra flat @ {px} but backend {b_state or 'OPEN'}", px))

    if sierra_stop is not None:
        commanded = commanded_stops or []
        if not any(abs(sierra_stop - c) <= 0.01 for c in commanded):
            events.append(ManualEvent(
                "MANUAL_STOP_MOVE",
                f"Sierra stop {sierra_stop} not among commanded {commanded}",
                sierra_stop))
    return events


# --------------------------------------------------------------- helpers

def _as_float(v) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _as_int(v) -> Optional[int]:
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None
