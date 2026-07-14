"""Real-time Google-Sheets logger for LIVE trades — Sierra-truth only (L8+).

Michael (2026-07-14): "real-time in Google Sheets on every LIVE trade executed —
the data MUST come from Sierra." This module pushes one row per LIVE trade (kept
current as ENTRY → T1 → T2 → T3 → STOP/FLATTEN fills arrive) to a Google Apps
Script webhook. The row is reconstructed from **Sierra fills alone** via
`sierra_ledger.LedgerTrade` — never from backend entry/stop/pnl claims (those are
the CLAIM the ledger exists to verify; see sierra_ledger.py + CLAUDE.md
§Source-of-Truth Discipline).

Design contracts:
  * **Non-blocking (critical):** a slow/broken Sheets endpoint must NEVER stall or
    crash the trading loop. `log_live_fill` does the journal read + reconstruction
    + HTTP POST on a daemon thread (fire-and-forget). The fill loop only spawns the
    thread and returns.
  * **Fail-soft:** every path swallows every exception. Nothing here can raise into
    the caller.
  * **LIVE-only + flag-gated:** off unless `GSHEETS_TRADE_LOG` is truthy AND
    `GSHEETS_TRADE_LOG_URL` is set. Only `mode == "live"` fills are pushed
    (shadow/demo/SIM are skipped). Default = complete no-op.
  * **stdlib only** (`urllib.request`) — no OAuth, no third-party deps.

Idempotency: each row carries `entry_order_id` + `fill_kind`. The bundled Apps
Script UPSERTS by `entry_order_id` (one live row per trade, updated in real time);
flip its `UPSERT` const to append-only for a per-fill audit log. See the report /
module docstring in the handoff for the doPost(e) + setup steps.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import urllib.request
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("gsheets_trade_logger")

# MES micro E-mini S&P = $5 / point (mirror sierra_ledger.DEFAULT_POINT_VALUE).
DEFAULT_POINT_VALUE = 5.0

# Gating env vars — written as string literals in _flag_on()/_get_url() below so
# scripts/gen_flag_index.py discovers them:
#   GSHEETS_TRADE_LOG      — master on/off, default OFF (registered in FLAG_REGISTRY)
#   GSHEETS_TRADE_LOG_URL  — the Apps Script /exec webhook (infra → INFRA_EXCLUDE)
FILLS_PATH_ENV = "TRADE_FILLS_PATH"     # shared with fill_poller / live_ledger
LIVE_ACCOUNT_ENV = "SIERRA_LIVE_ACCOUNT"
TIMEOUT_S = 3.0

_TRUTHY = ("1", "true", "yes", "on")

# Column order for the pushed row == the Apps Script header row. Insertion order is
# preserved (py3.7+), so this dict order IS the sheet column order.
ROW_COLUMNS = (
    "entry_order_id", "ts", "fill_kind", "direction", "entry", "contracts",
    "t1", "t2", "t3", "stop", "exit", "realized_pnl", "pnl_basis", "closed",
    "account", "source", "manual_tag", "direction_source", "entry_ts_epoch",
    "logged_at",
)


# ------------------------------------------------------------------ gating

def _flag_on() -> bool:
    return os.getenv("GSHEETS_TRADE_LOG", "0").strip().lower() in _TRUTHY


def _get_url() -> str:
    return (os.getenv("GSHEETS_TRADE_LOG_URL", "") or "").strip()


def is_enabled() -> bool:
    """True only when the flag is truthy AND a webhook URL is configured.

    Cheap gate the fill poller checks before doing any work — default OFF → no-op.
    """
    return _flag_on() and bool(_get_url())


# ------------------------------------------------------------------ helpers

def _g(obj: Any, name: str) -> Any:
    """Duck-typed getter: works for a LedgerTrade/Exit dataclass OR its dict form."""
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _iso(epoch: Any) -> str:
    try:
        if epoch is None:
            return ""
        return datetime.fromtimestamp(float(epoch), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return ""


def _exit_price_for_kind(exits: list, kind: str) -> Optional[float]:
    """Price of the LAST exit fill of a given kind (T1/T2/T3/STOP/FLATTEN)."""
    px = None
    for e in exits or []:
        if str(_g(e, "kind") or "").upper() == kind and _g(e, "price") is not None:
            px = _g(e, "price")
    return px


# ------------------------------------------------------------ row formatting

def format_trade_row(ledger_trade: Any, *, fill_kind: Optional[str] = None,
                     mode: str = "live") -> dict:
    """Map a Sierra-reconstructed `LedgerTrade` → an ordered, sheet-friendly row.

    Every value comes from the ledger (i.e. from Sierra fills). `manual_tag` is
    derived from Sierra alone: a **FLATTEN** exit is not something the normal
    bracket (T1/T2/T3/STOP) produces → tag it MANUAL (opposite/operator close).
    `fill_kind` is the current fill that triggered the push (for idempotency +
    an audit trail); `mode` is stamped for clarity (always "live" in practice).
    """
    exits = _g(ledger_trade, "exits") or []
    last_exit = None
    for e in reversed(exits):
        if _g(e, "price") is not None:
            last_exit = _g(e, "price")
            break
    manual = any(str(_g(e, "kind") or "").upper() == "FLATTEN" for e in exits)

    row = {
        "entry_order_id": _g(ledger_trade, "entry_order_id"),
        "ts": _iso(_g(ledger_trade, "entry_ts")),
        "fill_kind": (str(fill_kind).upper() if fill_kind else None),
        "direction": _g(ledger_trade, "direction"),
        "entry": _g(ledger_trade, "entry_price"),
        "contracts": _g(ledger_trade, "contracts"),
        "t1": _exit_price_for_kind(exits, "T1"),
        "t2": _exit_price_for_kind(exits, "T2"),
        "t3": _exit_price_for_kind(exits, "T3"),
        "stop": _exit_price_for_kind(exits, "STOP"),
        "exit": last_exit,
        "realized_pnl": _g(ledger_trade, "realized_pnl"),
        "pnl_basis": _g(ledger_trade, "pnl_basis"),
        "closed": bool(_g(ledger_trade, "closed")),
        "account": _g(ledger_trade, "account"),
        "source": "sierra",
        "manual_tag": "MANUAL" if manual else "",
        "direction_source": _g(ledger_trade, "direction_source"),
        "entry_ts_epoch": _g(ledger_trade, "entry_ts"),
        "logged_at": datetime.now(timezone.utc).isoformat(),
    }
    # Guarantee stable column order (== Apps Script header order).
    return {k: row.get(k) for k in ROW_COLUMNS}


# --------------------------------------------------------------- transport

def push_row(url: str, row: dict, *, timeout: float = TIMEOUT_S) -> bool:
    """POST `row` as JSON to the webhook. Swallows EVERY exception, never raises.

    Returns True on an apparent 2xx/3xx, False on any error or empty url. This is
    the raw transport — gating/mode checks live in `log_live_fill`.
    """
    if not url:
        return False
    try:
        body = json.dumps(row, default=str).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", None) or resp.getcode()
            resp.read()  # drain so the connection can be reused/closed cleanly
            ok = 200 <= int(status) < 400
            if not ok:
                logger.warning("[gsheets] push non-2xx status=%s", status)
            return ok
    except Exception as e:  # noqa: BLE001 — a Sheets outage must never reach trading
        logger.warning("[gsheets] push failed (non-fatal): %s", e)
        return False


# --------------------------------------------------- Sierra reconstruction

def _default_journal_path() -> str:
    fills = os.getenv(FILLS_PATH_ENV,
                      "/Users/michael/SierraChart_Data/v9_export/trade_fills.json")
    return os.path.join(os.path.dirname(fills), "trade_fills_journal.jsonl")


def _load_sierra_ledger():
    """Import sierra_ledger tolerant of package vs. standalone execution."""
    try:
        from backend.v9.services import sierra_ledger as sl  # normal package path
        return sl
    except Exception:  # noqa: BLE001
        import importlib.util
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sierra_ledger.py")
        spec = importlib.util.spec_from_file_location("sierra_ledger", path)
        sl = importlib.util.module_from_spec(spec)
        import sys as _sys
        _sys.modules.setdefault("sierra_ledger", sl)
        spec.loader.exec_module(sl)  # type: ignore[union-attr]
        return sl


def _fill_key(f: dict) -> tuple:
    return (str(f.get("kind", "")).upper(), f.get("order_id"), f.get("ts"), f.get("price"))


def reconstruct_trade(fill: dict, *, entry_order_id: Any = None,
                      journal_path: Optional[str] = None,
                      live_account: Optional[str] = None,
                      point_value: float = DEFAULT_POINT_VALUE):
    """Rebuild the LedgerTrade this `fill` belongs to, from Sierra fills alone.

    Reads the durable journal (all history) + the unconsumed trade_fills file, adds
    the just-arrived `fill` if the journal doesn't already carry it (the poller
    journals AFTER processing), dedupes, then `build_ledger`. Returns the matching
    LedgerTrade or None. Pure Sierra reconstruction — no backend fields.
    """
    sl = _load_sierra_ledger()
    if live_account is None:
        live_account = os.getenv(LIVE_ACCOUNT_ENV) or None

    lines: list[str] = []
    jp = journal_path or _default_journal_path()
    fills_file = os.getenv(FILLS_PATH_ENV,
                           "/Users/michael/SierraChart_Data/v9_export/trade_fills.json")
    for p in (jp, fills_file):
        try:
            with open(p, "r", encoding="utf-8") as fh:
                lines.extend(fh.readlines())
        except (FileNotFoundError, OSError):
            continue

    fills = sl.parse_fills(lines)
    # Include the live fill if the journal hasn't captured it yet (dedup by key).
    if isinstance(fill, dict) and fill.get("kind"):
        seen = {_fill_key(f) for f in fills}
        if _fill_key(fill) not in seen:
            fills.append(dict(fill))

    ledger = sl.build_ledger(fills, live_account=live_account, point_value=point_value)
    if not ledger:
        return None

    # Prefer the explicit entry parent id (poller passes quality["sierra_order_id"]).
    if entry_order_id is not None:
        for lt in ledger:
            if str(_g(lt, "entry_order_id")) == str(entry_order_id):
                return lt
    # Else: this fill's order_id may itself be the ENTRY id.
    oid = fill.get("order_id") if isinstance(fill, dict) else None
    if oid is not None:
        for lt in ledger:
            if str(_g(lt, "entry_order_id")) == str(oid):
                return lt
    # Else: the trade whose exits contain this exact fill.
    fk = _fill_key(fill) if isinstance(fill, dict) else None
    if fk is not None:
        for lt in ledger:
            for e in _g(lt, "exits") or []:
                if (str(_g(e, "kind") or "").upper(), oid, _g(e, "ts"), _g(e, "price")) == fk:
                    return lt
    # Fallback: the most recent reconstructed trade.
    return ledger[-1]


# ------------------------------------------------------- fire-and-forget API

def _safe_call(fn) -> None:
    try:
        fn()
    except Exception as e:  # noqa: BLE001
        logger.warning("[gsheets] worker error (non-fatal): %s", e)


def _spawn(fn) -> None:
    threading.Thread(target=_safe_call, args=(fn,), daemon=True,
                     name="gsheets-trade-logger").start()


def log_live_fill(*, fill: dict, mode: str, entry_order_id: Any = None,
                  journal_path: Optional[str] = None,
                  live_account: Optional[str] = None,
                  url: Optional[str] = None,
                  point_value: float = DEFAULT_POINT_VALUE,
                  block: bool = False) -> bool:
    """Fill-poller entry point: push the current Sierra-reconstructed row for a
    LIVE trade to Google Sheets, fire-and-forget.

    Gate: flag ON + URL set + mode == "live" (shadow/demo/SIM skipped). When gated
    out → returns False and does nothing. Otherwise reconstructs from Sierra fills
    and POSTs on a **daemon thread** (unless `block=True`, used by tests) so a slow
    or broken Sheets endpoint can never stall the trading loop. Never raises.
    """
    try:
        if not _flag_on():
            return False
        if str(mode).lower() != "live":
            return False
        target_url = (url or _get_url()).strip()
        if not target_url:
            return False

        def _work():
            lt = reconstruct_trade(
                fill, entry_order_id=entry_order_id, journal_path=journal_path,
                live_account=live_account, point_value=point_value)
            if lt is None:
                logger.warning("[gsheets] no Sierra trade reconstructed for fill %s — skipped",
                               (fill or {}).get("order_id"))
                return
            row = format_trade_row(lt, fill_kind=(fill or {}).get("kind"), mode="live")
            push_row(target_url, row)

        if block:
            _safe_call(_work)
        else:
            _spawn(_work)
        return True
    except Exception as e:  # noqa: BLE001 — belt-and-suspenders: never reach trading
        logger.warning("[gsheets] log_live_fill guard caught (non-fatal): %s", e)
        return False
