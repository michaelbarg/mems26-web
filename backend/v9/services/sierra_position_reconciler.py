"""SYS-3: Sierra position reconciler — "records ≠ reality" killer.

FIX-6 (incident 333, Michael's explicit demand): the system must always know
what Sierra actually holds. Runs every ≤30s (fill_poller cycle or standalone),
compares TM open trades vs TradeActivityLog position state.

Divergence → WARNING (noisy) + freeze auto-actions on the trade.
Auto-adopt = next phase (Michael's ruling), not this version.

ORPHAN_AUTO_STOP_V1 (Michael ruling 07-17): when an orphan position is naked
(no working orders) and all safety conditions hold, attempt to place a
protective stop. Currently BLOCKED — no DLL op exists to place a standalone
stop order (sc.SubmitOrder not implemented). The gating logic is wired so that
when a PLACE_STOP DLL op is added, only the _place_orphan_stop() stub needs
to be replaced. Flag default OFF; enabling requires Michael sign-off.
"""
import json
import logging
import os
import time as _time_mod
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

EVENTS_FILE = Path(os.path.expanduser(
    "~/SierraChart_Data/v9_export/trade_activity_events.jsonl"))
STATE_FILE = Path(os.path.expanduser(
    "~/SierraChart_Data/v9_export/sierra_state.json"))
STATE_MAX_AGE_S = 10.0  # fresher than this → authoritative

import re as _re
def _safe_json_loads(raw: str) -> dict:
    """Parse JSON tolerating Sierra's -inf/inf (high/low_during_pos when flat)."""
    return json.loads(_re.sub(r':\s*-?inf\b', ':null', raw))

# ── ORPHAN_AUTO_STOP_V1 constants ─────────────────────────────────────────────
def _orphan_max_qty() -> int:
    return int(os.getenv("ORPHAN_AUTO_STOP_MAX_QTY", "10"))

def _orphan_cooldown_s() -> float:
    return float(os.getenv("ORPHAN_AUTO_STOP_COOLDOWN_S", "60"))

# Idempotency: tracks (qty, avg_price) → timestamp of last placement attempt.
# Reset when position changes (different qty). Module-level to survive across
# reconcile_position() calls within the same process.
_orphan_stop_placed: dict = {}   # {(qty, avg_price): float_timestamp}
_orphan_stop_last_attempt: float = 0.0  # monotonic timestamp of last attempt


def _sierra_state_qty() -> Optional[int]:
    """FIX-13: read the net position from the DLL's sierra_state.json —
    second-fresh native truth, immune to the activity-log parsing family
    (wrong account file, duplicate feeders, sim files without position
    lines — all three bit on 07-10). Only trusted when the file is fresh
    (≤10s); stale/missing → None so the caller falls back to the events
    journal. Honest None on any parse gap (Rule 1)."""
    try:
        if not STATE_FILE.exists():
            return None
        if (_time_mod.time() - STATE_FILE.stat().st_mtime) > STATE_MAX_AGE_S:
            return None
        data = _safe_json_loads(STATE_FILE.read_text().strip() or "{}")
        qty = data.get("position_qty")
        return int(qty) if qty is not None else None
    except (OSError, ValueError, TypeError):
        return None


def _sierra_state_working() -> Optional[int]:
    """working_orders from the fresh state file; None if stale/absent (Rule 1)."""
    try:
        if not STATE_FILE.exists():
            return None
        if (_time_mod.time() - STATE_FILE.stat().st_mtime) > STATE_MAX_AGE_S:
            return None
        data = _safe_json_loads(STATE_FILE.read_text().strip() or "{}")
        w = data.get("working_orders")
        return int(w) if w is not None else None
    except (OSError, ValueError, TypeError):
        return None


def _sierra_state_avg_price() -> Optional[float]:
    """avg_price from the fresh state file; None if stale/absent (Rule 1)."""
    try:
        if not STATE_FILE.exists():
            return None
        if (_time_mod.time() - STATE_FILE.stat().st_mtime) > STATE_MAX_AGE_S:
            return None
        data = _safe_json_loads(STATE_FILE.read_text().strip() or "{}")
        ap = data.get("avg_price")
        return float(ap) if ap not in (None, "", 0, 0.0) else None
    except (OSError, ValueError, TypeError):
        return None


def _sierra_state_orders() -> Optional[list]:
    """orders[] from the fresh state file; None if stale/absent (Rule 1)."""
    try:
        if not STATE_FILE.exists():
            return None
        if (_time_mod.time() - STATE_FILE.stat().st_mtime) > STATE_MAX_AGE_S:
            return None
        data = _safe_json_loads(STATE_FILE.read_text().strip() or "{}")
        o = data.get("orders")
        return list(o) if isinstance(o, list) else None
    except (OSError, ValueError, TypeError):
        return None


def _has_protective_stop(qty: int, orders: Optional[list],
                         avg_price: Optional[float]) -> Optional[bool]:
    """MANUAL_POSITION_GUARD_V1: does a working order protect this position?
    LONG (qty>0): a SELL (bs=2) at/below avg = the stop. SHORT: a BUY (bs=1)
    at/above avg. avg missing → None (unknown — honest, no alert; Rule 1).
    NOTE: orders[] only lists GetOrderByIndex-visible orders — a held bracket
    may be invisible (known false-naked class); the grace window absorbs it."""
    if not orders:
        return False
    try:
        saw_typed = False
        for o in orders:
            bs = int(o.get("bs", 0))
            typ = o.get("type")
            if typ is not None:
                saw_typed = True
                # Sierra order types observed live 07-24: 1=limit(target),
                # 2/3=stop varieties. A STOP on the closing side = protection,
                # price-agnostic (covers locked-profit stops beyond avg).
                if int(typ) in (2, 3) and (
                        (qty > 0 and bs == 2) or (qty < 0 and bs == 1)):
                    return True
        if saw_typed:
            return False  # typed orders present, none is a closing-side stop
        # typeless feed → price-vs-avg proxy (legacy fallback)
        if avg_price is None:
            return None
        for o in orders:
            bs = int(o.get("bs", 0))
            price = float(o.get("price", 0) or 0)
            if qty > 0 and bs == 2 and price <= float(avg_price):
                return True
            if qty < 0 and bs == 1 and price >= float(avg_price):
                return True
    except (TypeError, ValueError):
        return None
    return False


#: PROTECTED_QTY_GUARD_V1 state — consecutive checks the shortfall has held.
_prot_short_streak: int = 0
_prot_last_alert: float = 0.0


def _unprotected_contracts(sierra_qty: Optional[int]) -> Optional[str]:
    """Is EVERY contract behind a stop, or only the first few?

    The existing guard asks "is there A protective stop?" and answers yes/no.
    That question cannot see the failure Michael found on 2026-07-28 — "העסקה
    היא על 6 חוזים והסטופ והמימוש על חוזה 1" — because with a partial bracket
    there IS a stop, so the boolean says protected while the rest of the
    position is naked.

    This counts instead. The study builds four OCO groups whose quantities sum
    to the order quantity (the 08-16 ladder: 1/2/2/1 at six). If the working
    stops cover fewer contracts than the position holds, the difference is
    entering with no stop at all. That gap is the whole risk of moving above
    four, and until a live fire proves the compiled ladder, it is the only
    thing standing between a wrong ladder and an unprotected contract.

    Alert-only, and deliberately reluctant:
      * unknown (no state, no typed orders) → None. Never an alarm from
        absence of evidence (Rule 1) — the held-bracket class makes a real
        bracket temporarily invisible to GetOrderByIndex.
      * must hold for PROTECTED_QTY_STREAK consecutive checks (~60s at the
        30s cadence) so a bracket still being attached is not an alarm.
      * never touches an order or a position.
    """
    global _prot_short_streak, _prot_last_alert
    if not _mg_os_env("PROTECTED_QTY_GUARD_V1"):
        return None
    if not sierra_qty:
        _prot_short_streak = 0
        return None
    orders = _sierra_state_orders()
    if not orders:
        _prot_short_streak = 0
        return None            # unknown, not unprotected
    held = abs(int(sierra_qty))
    covered, saw_typed = 0, False
    try:
        for o in orders:
            typ, bs = o.get("type"), int(o.get("bs", 0))
            if typ is None:
                continue
            saw_typed = True
            if int(typ) in (2, 3) and (
                    (sierra_qty > 0 and bs == 2) or (sierra_qty < 0 and bs == 1)):
                covered += abs(int(o.get("qty", 0) or 0))
    except (TypeError, ValueError):
        _prot_short_streak = 0
        return None
    if not saw_typed:
        _prot_short_streak = 0
        return None            # typeless feed — the qty is not trustworthy
    if covered >= held:
        _prot_short_streak = 0
        return None
    _prot_short_streak += 1
    try:
        need = int(os.getenv("PROTECTED_QTY_STREAK", "2"))
    except (TypeError, ValueError):
        need = 2
    if _prot_short_streak < need:
        return None
    naked = held - covered
    text = (f"\U0001f6a8 UNPROTECTED CONTRACTS: position {held}c, stops cover "
            f"{covered}c → {naked}c with NO stop "
            f"(streak {_prot_short_streak})")
    now = _time_mod.time()
    if (now - _prot_last_alert) > 300.0:
        _prot_last_alert = now
        logger.critical("[Reconciler] %s", text)
        try:
            from backend.v9.services.phone_alert import push as _pp
            _pp("unprotected_qty", "\U0001f6a8 MEMS26: contracts with no stop",
                text, priority=1)
        except Exception:
            pass
    return text


def _mg_os_env(name: str) -> bool:
    """Truthy env read for the manual-guard family (module-local, no imports at call site)."""
    import os as _e
    return _e.getenv(name, "0").lower() in ("1", "true", "yes")


# MANUAL_POSITION_GUARD_V1 episode state (module-level; reset on protected/flat)
_manual_guard = {"first_naked_ts": None, "last_alert_ts": 0.0}


def _manual_position_guard(sierra_qty: int) -> Optional[str]:
    """Michael ruling 2026-07-25 ("התראה-בלבד"): a MANUAL position with no
    working protective stop for >= grace seconds → CRITICAL + phone push.
    ALERT-ONLY — never places/modifies orders, never touches the position
    (12:20 ownership ruling fully preserved). Returns the alert text when
    alerting, else None. Fail-quiet on any error."""
    import os as _mg_os
    if _mg_os.getenv("MANUAL_POSITION_GUARD_V1", "0").lower() not in ("1", "true", "yes"):
        return None
    try:
        _grace = float(_mg_os.getenv("MANUAL_GUARD_GRACE_S", "60"))
        _throttle = float(_mg_os.getenv("MANUAL_GUARD_REALERT_S", "300"))
        _now = _time_mod.time()
        _prot = _has_protective_stop(
            sierra_qty, _sierra_state_orders(), _sierra_state_avg_price())
        if _prot is not False:  # protected, or unknown (avg missing) → no alert
            _manual_guard["first_naked_ts"] = None
            return None
        if _manual_guard["first_naked_ts"] is None:
            _manual_guard["first_naked_ts"] = _now
            return None
        if (_now - _manual_guard["first_naked_ts"]) < _grace:
            return None
        if (_now - _manual_guard["last_alert_ts"]) < _throttle:
            return None
        _manual_guard["last_alert_ts"] = _now
        _naked_for = int(_now - _manual_guard["first_naked_ts"])
        _txt = (f"🔴 MANUAL POSITION NAKED: {sierra_qty}c with NO working stop "
                f"for {_naked_for}s — place a stop in Sierra NOW (alert-only, "
                f"system will not touch your position)")
        try:
            # Found by scripts/wire_guard.py, 2026-08-17. This was
            # `_mg_push("MANUAL NAKED", _txt)` — two positional arguments against
            # `push(key, title, msg, priority)`, so `msg` was missing and every
            # call raised TypeError into the bare `except` below. The alert has
            # NEVER reached the phone.
            # This is the alarm that exists because a naked manual position cost
            # Michael more than half the account on 07-27, and he is holding a
            # manual position today. Same class as #682: the code looked right,
            # the failure was swallowed, and nobody was told.
            from backend.v9.services.phone_alert import push as _mg_push
            _mg_push("manual_naked", "\U0001f534 MEMS26: פוזיציה ידנית ללא סטופ",
                     _txt, priority=1)
        except Exception:
            pass  # phone unavailable — the CRITICAL log still fires
        return _txt
    except Exception:
        return None


def recommend_orphan_stop(sierra_qty: Optional[int],
                          avg_price: Optional[float]) -> Optional[dict]:
    """Conservative protective stop for an untracked (orphan) Sierra position.

    P3 (2026-07-16): an orphan (Sierra holds a position the backend does not
    track) must never sit naked. We cannot auto-place a standalone stop safely
    yet — that path is the deferred "auto-adopt" (Michael's ruling) — but we can
    always compute the exact protective stop and surface it in the CRITICAL
    alert so it can be placed instantly.

    LONG (qty>0) → stop below entry; SHORT (qty<0) → stop above. Distance =
    ORPHAN_STOP_POINTS (default 10pt), tick-snapped (0.25). Returns None when
    inputs are unusable (Rule 1: honest None, never a synthetic price).
    """
    if not sierra_qty or avg_price is None:
        return None
    try:
        avg = float(avg_price)
    except (TypeError, ValueError):
        return None
    if avg <= 0:
        return None
    pts = float(os.getenv("ORPHAN_STOP_POINTS", "10"))
    long_ = sierra_qty > 0
    raw = (avg - pts) if long_ else (avg + pts)
    tick = 0.25
    stop = round(round(raw / tick) * tick, 2)
    return {
        "side": "LONG" if long_ else "SHORT",
        "qty": abs(int(sierra_qty)),
        "entry": round(avg, 2),
        "stop": stop,
        "points": pts,
    }


def _read_place_bracket_result(pre_mtime: float, timeout_s: float = 5.0) -> Tuple[bool, str]:
    """Poll trade_result.json for a PLACE_STOP result newer than pre_mtime.

    W8 v2 (2026-07-28). Returns (True, "PLACE_STOP_OK") on success,
    (False, status_string) on failure or timeout.
    """
    result_path = Path(os.path.expanduser(
        os.getenv("MEMS26_SIGNALS_DIR", "~/SierraChart_Data/v9_export")
    )) / "trade_result.json"
    deadline = _time_mod.time() + timeout_s
    while _time_mod.time() < deadline:
        try:
            if result_path.exists():
                mtime = result_path.stat().st_mtime
                if mtime > pre_mtime:
                    data = _safe_json_loads(result_path.read_text().strip() or "{}")
                    status = data.get("status", "")
                    if "PLACE_BRACKET" in status or "PLACE_STOP" in status:
                        return status in ("PLACE_BRACKET_OK", "PLACE_STOP_OK"), status
        except (OSError, json.JSONDecodeError):
            pass
        _time_mod.sleep(0.25)
    return False, "PLACE_BRACKET_TIMEOUT: no result within {:.0f}s".format(timeout_s)


def _read_flatten_result(pre_mtime: float, timeout_s: float = 5.0) -> Tuple[bool, str]:
    """Poll trade_result.json for a FLATTEN_ORPHAN result newer than pre_mtime."""
    result_path = Path(os.path.expanduser(
        os.getenv("MEMS26_SIGNALS_DIR", "~/SierraChart_Data/v9_export")
    )) / "trade_result.json"
    deadline = _time_mod.time() + timeout_s
    while _time_mod.time() < deadline:
        try:
            if result_path.exists():
                mtime = result_path.stat().st_mtime
                if mtime > pre_mtime:
                    data = json.loads(result_path.read_text().strip() or "{}")
                    status = data.get("status", "")
                    if "FLATTEN_ORPHAN" in status:
                        return status == "FLATTEN_ORPHAN_OK", status
        except (OSError, json.JSONDecodeError):
            pass
        _time_mod.sleep(0.25)
    return False, "FLATTEN_ORPHAN_TIMEOUT: no result within {:.0f}s".format(timeout_s)


# ── Virtual stop state: tracks the orphan structural stop being monitored ──
# {(qty, entry): {"stop": float, "side": str, "set_ts": float}}
_virtual_stop: dict = {}

# MES tick value: $12.50 per point per contract
_MES_DOLLAR_PER_POINT = 12.50
def _orphan_max_loss_usd() -> float:
    return float(os.getenv("ORPHAN_MAX_LOSS_USD", "200"))


def _orphan_current_price() -> Optional[float]:
    """Read the latest price from sierra_state.json (last_price or last_trade_price)."""
    try:
        if not STATE_FILE.exists():
            return None
        data = _safe_json_loads(STATE_FILE.read_text().strip() or "{}")
        lp = data.get("last_price") or data.get("last_trade_price")
        return float(lp) if lp is not None else None
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _check_orphan_flatten_trigger(rec: dict) -> Optional[str]:
    """Check if the orphan should be flattened now.

    Michael ruling 2026-07-20 (redesign): hold the orphan with a structural
    stop — only flatten when:
      (1) price crosses the structural stop level, OR
      (2) unrealized loss >= _orphan_max_loss_usd() (default $200)

    Returns a reason string if triggered, None if still holding.
    """
    last_price = _orphan_current_price()
    if last_price is None:
        return None  # no price data → hold (Rule 1)

    stop = rec["stop"]
    entry = rec["entry"]
    qty = rec["qty"]

    # Trigger 1: price crossed structural stop
    if rec["side"] == "LONG" and last_price <= stop:
        return f"STOP_CROSSED: price {last_price:.2f} <= stop {stop:.2f}"
    if rec["side"] == "SHORT" and last_price >= stop:
        return f"STOP_CROSSED: price {last_price:.2f} >= stop {stop:.2f}"

    # Trigger 2: unrealized loss >= max loss
    if rec["side"] == "LONG":
        unrealized_pts = entry - last_price  # positive = loss for LONG
    else:
        unrealized_pts = last_price - entry  # positive = loss for SHORT
    unrealized_usd = unrealized_pts * qty * _MES_DOLLAR_PER_POINT
    if unrealized_usd >= _orphan_max_loss_usd():
        return (f"MAX_LOSS: unrealized ${unrealized_usd:.0f} >= "
                f"${_orphan_max_loss_usd():.0f} ({unrealized_pts:.2f}pt × {qty}c)")

    return None  # still within tolerance — hold


def _flatten_orphan(rec: dict) -> Tuple[bool, str]:
    """Execute a market-exit for an orphan position via FLATTEN_ORPHAN DLL op.

    Uses proven FlattenAndCancelAllOrders path. Only called when a trigger
    fires (structural stop crossed or max loss exceeded).

    Returns (True, "FLATTEN_ORPHAN_OK") on success, (False, reason) on failure.
    """
    from backend.v9.services.sierra_command import write_flatten_orphan

    result_path = Path(os.path.expanduser(
        os.getenv("MEMS26_SIGNALS_DIR", "~/SierraChart_Data/v9_export")
    )) / "trade_result.json"
    try:
        pre_mtime = result_path.stat().st_mtime if result_path.exists() else 0.0
    except OSError:
        pre_mtime = 0.0

    account = None
    try:
        if STATE_FILE.exists():
            data = _safe_json_loads(STATE_FILE.read_text().strip() or "{}")
            account = data.get("account") or data.get("trade_account")
    except (OSError, json.JSONDecodeError):
        pass

    write_flatten_orphan(qty=rec["qty"], side=rec["side"], account=account)
    return _read_flatten_result(pre_mtime)


def _place_bracket_enabled() -> bool:
    """PLACE_BRACKET_OP_V1 — default OFF until the DLL op is sim-verified."""
    return os.getenv("PLACE_BRACKET_OP_V1", "0").strip().lower() in ("1", "true", "yes")


def _bracket_target_for(rec: dict) -> Optional[float]:
    """Optional take-profit for the protective bracket.

    OFF by default: protection must never wait on a profit decision. When
    PLACE_BRACKET_TARGET_R is set, the target sits that many R from entry,
    where R is the entry-to-stop distance. Returns None when it cannot be
    computed honestly (Rule 1)."""
    try:
        rr = float(os.getenv("PLACE_BRACKET_TARGET_R", "0"))
    except (TypeError, ValueError):
        return None
    if rr <= 0:
        return None
    entry, stop = rec.get("entry"), rec.get("stop")
    if entry is None or stop is None:
        return None
    risk = abs(float(entry) - float(stop))
    if risk <= 0:
        return None
    tgt = (float(entry) + rr * risk) if rec.get("side") == "LONG" else (float(entry) - rr * risk)
    return round(round(tgt * 4) / 4, 2)          # snap to the 0.25 tick


def _submit_real_bracket(rec: dict) -> Tuple[bool, str]:
    """Send PLACE_BRACKET to the DLL and wait for its result.

    The DLL owns the hard safety checks (position sign, price vs the live
    market, reduce-only clamp) because only it sees the live position at
    execution time. This function must not second-guess them — it only
    submits and reports."""
    from backend.v9.services.sierra_command import write_place_bracket
    import time as _t

    result_path = Path(os.path.expanduser(
        os.getenv("MEMS26_SIGNALS_DIR", "~/SierraChart_Data/v9_export")
    )) / "trade_result.json"
    pre_mtime = result_path.stat().st_mtime if result_path.exists() else 0.0

    write_place_bracket(qty=int(rec["qty"]), stop=float(rec["stop"]),
                        side=str(rec["side"]), target=_bracket_target_for(rec))
    return _read_place_bracket_result(pre_mtime)


def _auto_flatten_enabled() -> bool:
    """ORPHAN_AUTO_FLATTEN_V1 — default OFF (Michael ruling 2026-07-28).

    The system no longer market-exits a position it could not protect. It still
    watches and still alerts; the decision returns to Michael. Turning this back
    on is a trading-risk change and needs a new written ruling."""
    return os.getenv("ORPHAN_AUTO_FLATTEN_V1", "0").strip().lower() in ("1", "true", "yes")


def _place_orphan_stop(rec: dict) -> Tuple[bool, str]:
    """Monitor an orphan position with a virtual structural stop.

    Michael ruling 2026-07-20 (redesign): do NOT flatten immediately.
    Hold the orphan with a structural stop (from recommend_orphan_stop).
    FLATTEN_ORPHAN only when:
      (1) price crosses the structural stop, OR
      (2) unrealized loss >= _orphan_max_loss_usd() ($200 default)

    On first call: registers the virtual stop → VIRTUAL_STOP_SET.
    On subsequent calls: checks triggers → FLATTEN if triggered, else MONITORING.
    """
    key = (rec["qty"], rec["entry"])

    # Check if virtual stop already set for this position
    if key in _virtual_stop:
        # Check flatten triggers
        trigger = _check_orphan_flatten_trigger(rec)
        if trigger and not _auto_flatten_enabled():
            # RULING (Michael 2026-07-28): "תבטל את הכלי שיוצא מעסקאות פתוחות.
            # אם אי אפשר לשים סטופ במקום אסטרטגי — לא לסגור עסקה."
            #
            # This flatten existed only because ACSIL cannot place a resting stop
            # on a position it did not open — proven in sim the same day. But a
            # market exit fired by a virtual line is an exit at the WORST
            # location by construction: it triggers exactly where the market is
            # moving against the position, with no regard for structure. Being
            # unable to protect a trade properly is not a reason to close it
            # badly.
            #
            # The watch REMAINS: the breach is still detected and still shouts.
            # What is removed is the system deciding for Michael.
            msg = (f"ORPHAN STOP BREACHED ({trigger}) — NOT flattening "
                   f"(ruling 07-28). {rec['side']} {rec['qty']}c @ {rec['entry']}, "
                   f"virtual stop {rec['stop']}. Decide manually.")
            logger.critical("[Reconciler] %s", msg)
            try:
                from scripts.ops_log import log_event
                log_event("reconciler", "CRITICAL", msg)
            except Exception:
                pass
            try:
                from backend.v9.services.phone_alert import push as _pp
                _pp("orphan_breach", "\U000026a0 MEMS26: STOP LEVEL BREACHED",
                    f"{rec['side']} {rec['qty']}c @ {rec['entry']} — not closed, your call",
                    priority=1)
            except Exception:
                pass
            return True, f"BREACH_ALERT_ONLY({trigger}) — position left open per ruling"
        if trigger:
            logger.critical("[Reconciler] ORPHAN FLATTEN TRIGGER: %s → FLATTEN_ORPHAN", trigger)
            ok, status = _flatten_orphan(rec)
            if ok:
                del _virtual_stop[key]
            try:
                from scripts.ops_log import log_event
                log_event("reconciler", "CRITICAL",
                          f"ORPHAN FLATTENED: {trigger} → {status}")
            except Exception:
                pass
            try:
                from backend.v9.services.phone_alert import push as _pp
                _pp("orphan_flatten", "\U0001f6a8 MEMS26: ORPHAN FLATTENED",
                    f"{trigger} → {status}", priority=1)
            except Exception:
                pass
            return ok, f"FLATTEN_TRIGGERED({trigger} → {status})"
        else:
            lp = _orphan_current_price()
            return True, (f"VIRTUAL_STOP_MONITORING: {rec['side']} stop @ {rec['stop']}, "
                         f"price={lp}, max_loss=${_orphan_max_loss_usd():.0f}, "
                         f"watching since {_virtual_stop[key]['set_ts']:.0f}")

    # ── W8 v3 (Michael 2026-07-28) — try a REAL resting bracket first ────────
    # "המערכת כן תוכל לנהל עסקה שאני מבצע ולהוסיף לה סטופ ונקודות מימוש".
    # A real order rests on Sierra's book: it survives a backend crash, a
    # restart, and a gap. The virtual stop below cannot — it needs this process
    # alive and a tick to cross the level. So the virtual stop stops being the
    # design and becomes the FALLBACK for when the real order is refused.
    if _place_bracket_enabled():
        try:
            ok_r, status_r = _submit_real_bracket(rec)
            if ok_r:
                _virtual_stop[key] = {
                    "stop": rec["stop"], "side": rec["side"],
                    "set_ts": _time_mod.time(), "real": True,
                }
                logger.critical(
                    "[Reconciler] REAL BRACKET PLACED: %s stop @ %.2f for %dc @ %.2f (%s)",
                    rec["side"], rec["stop"], rec["qty"], rec["entry"], status_r)
                try:
                    from scripts.ops_log import log_event
                    log_event("reconciler", "CRITICAL",
                              f"REAL BRACKET PLACED: {rec['side']} stop @ {rec['stop']} "
                              f"for {rec['qty']}c @ {rec['entry']} ({status_r})")
                except Exception:
                    pass
                try:
                    from backend.v9.services.phone_alert import push as _pp
                    _pp("real_bracket", "\U0001f6e1 MEMS26: STOP PLACED",
                        f"{rec['side']} {rec['qty']}c stop @ {rec['stop']}", priority=1)
                except Exception:
                    pass
                return True, (f"REAL_BRACKET_PLACED: {rec['side']} stop @ {rec['stop']} "
                              f"for {rec['qty']}c ({status_r})")
            # Refused: say so loudly, then fall through to the virtual stop.
            logger.warning("[Reconciler] real bracket refused (%s) — "
                           "falling back to the virtual stop", status_r)
        except Exception as e:
            logger.warning("[Reconciler] real bracket errored (%s) — "
                           "falling back to the virtual stop", e)

    # Fallback — register the virtual stop
    _virtual_stop[key] = {
        "stop": rec["stop"],
        "side": rec["side"],
        "set_ts": _time_mod.time(),
    }
    logger.warning("[Reconciler] VIRTUAL STOP SET: %s @ %.2f for %dc @ %.2f "
                   "(flatten on stop-cross or loss >= $%.0f)",
                   rec["side"], rec["stop"], rec["qty"], rec["entry"], _orphan_max_loss_usd())
    try:
        from scripts.ops_log import log_event
        log_event("reconciler", "WARNING",
                  f"ORPHAN VIRTUAL STOP SET: {rec['side']} stop @ {rec['stop']} "
                  f"for {rec['qty']}c @ {rec['entry']}")
    except Exception:
        pass
    return True, (f"VIRTUAL_STOP_SET: {rec['side']} stop @ {rec['stop']} for "
                 f"{rec['qty']}c @ {rec['entry']} (flatten on cross or loss >= ${_orphan_max_loss_usd():.0f})")


def _try_orphan_auto_stop(sierra_qty: int, src: str) -> Optional[str]:
    """ORPHAN_AUTO_STOP_V1 gating logic.

    Checks all 8 safety conditions. On success, attempts placement via
    _place_orphan_stop(). Returns a status string for the log, or None if
    the flag is OFF (caller falls through to the existing alert-only path).

    Conditions (ALL must hold — fail-safe: any miss → alert-only):
      1. ORPHAN_AUTO_STOP_V1=1
      2. (caller already verified: orphan — TM=0, Sierra!=0)
      3. working_orders == 0 (naked — no existing protection)
      4. state file fresh (<= STATE_MAX_AGE_S) — guaranteed by src=="state"
      5. recommend_orphan_stop() returned a valid dict
      6. abs(qty) <= _orphan_max_qty() (sanity cap)
      7. idempotency: not already placed for this (qty, avg_price)
      8. cooldown: at least _orphan_cooldown_s() since last attempt
    """
    global _orphan_stop_last_attempt

    # Condition 1: flag ON
    flag_on = os.getenv("ORPHAN_AUTO_STOP_V1", "0").lower() in ("1", "true", "yes")
    if not flag_on:
        return None  # flag OFF → caller uses existing alert-only path

    # Condition 4: state file freshness (only state source is trusted)
    if src != "state":
        return "SKIP(stale-source): orphan auto-stop requires fresh sierra_state.json"

    # Condition 3: working orders == 0 (naked)
    working = _sierra_state_working()
    if working is None:
        return "SKIP(working-unknown): cannot read working_orders from state file"
    if working > 0:
        return f"SKIP(protected): {working} working orders already exist"

    # Condition 5: recommend_orphan_stop valid
    avg_price = _sierra_state_avg_price()
    rec = recommend_orphan_stop(sierra_qty, avg_price)
    if rec is None:
        return "SKIP(no-recommendation): recommend_orphan_stop returned None"

    # Condition 6: qty sanity cap
    if abs(sierra_qty) > _orphan_max_qty():
        return (f"SKIP(qty-too-large): |{sierra_qty}| > {_orphan_max_qty()} "
                f"— refusing (possible bad read)")

    # Condition 7: idempotency — only blocks if this position was already FLATTENED
    key = (sierra_qty, rec["entry"])
    if key in _orphan_stop_placed:
        return (f"SKIP(already-flattened): orphan already flattened for "
                f"qty={sierra_qty} entry={rec['entry']} "
                f"at {_orphan_stop_placed[key]:.0f}")

    # Condition 8: cooldown — only on FLATTEN attempts, not monitoring
    now = _time_mod.time()
    # Skip cooldown if we're just monitoring (virtual stop already set)
    _monitoring = key in _virtual_stop
    if not _monitoring and (now - _orphan_stop_last_attempt) < _orphan_cooldown_s():
        return (f"SKIP(cooldown): {now - _orphan_stop_last_attempt:.0f}s "
                f"< {_orphan_cooldown_s():.0f}s cooldown")

    # All conditions met — monitor orphan with virtual stop
    _orphan_stop_last_attempt = now
    try:
        ok, reason = _place_orphan_stop(rec)
    except Exception as exc:
        logger.error("[Reconciler] ORPHAN_AUTO_STOP exception: %s", exc)
        return f"ERROR(placement-exception): {exc}"

    if ok:
        if "FLATTEN_TRIGGERED" in reason:
            # Actual flatten happened — record idempotency + log critical
            _orphan_stop_placed[key] = now
            logger.critical("[Reconciler] ORPHAN FLATTENED: %s", reason)
            return f"FLATTENED: {reason}"
        else:
            # Virtual stop set or monitoring — return status (re-enter next cycle)
            return reason
    else:
        logger.warning("[Reconciler] ORPHAN_AUTO_STOP failed: %s", reason)
        return f"FAILED({reason})"


# Phantom-heal: consecutive checks where TM is in-position but Sierra is
# definitively flat (qty=0, working=0). Reset on any other outcome.
_phantom_flat_streak = 0
# T5b alert throttle: last (tm_qty, sierra_qty, src) and when it was announced
_last_div_state = None
_last_div_ts = 0.0


def _sierra_position_qty() -> Optional[int]:
    """Read the latest position quantity from trade_activity_events.jsonl.

    Returns the most recent POSITION_CHANGE new_qty, or None if no data.
    """
    if not EVENTS_FILE.exists():
        return None
    try:
        last_pos = None
        with open(EVENTS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                    if ev.get("type") == "POSITION_CHANGE":
                        last_pos = ev.get("new_qty")
                except json.JSONDecodeError:
                    continue
        return int(last_pos) if last_pos is not None else None
    except OSError:
        return None


def reconcile_position(tm, *, fill_poller=None) -> Tuple[bool, str]:
    """Compare TM open trades vs Sierra's actual position.

    Returns (ok, message). ok=False means divergence detected.
    """
    # FIX-13: prefer the DLL's native state export when fresh; fall back to
    # the parsed activity journal only when sierra_state.json is absent/stale.
    src = "state"
    sierra_qty = _sierra_state_qty()
    if sierra_qty is None:
        src = "events"
        sierra_qty = _sierra_position_qty()
    if sierra_qty is None:
        return True, "no Sierra position data (state file + events file empty)"

    # Count TM open contracts (demo + live, not shadow)
    tm_qty = 0
    tm_trades = []
    try:
        active = tm.get_active_trades() if hasattr(tm, "get_active_trades") else []
        for t in (active or []):
            mode = getattr(t, "mode", "shadow")
            if mode not in ("demo", "live"):
                continue
            state = getattr(t, "state", "")
            if state in ("CLOSED", "CANCELLED"):
                continue
            direction = str(getattr(t, "direction", "")).upper()
            from backend.v9.services.trade_manager.manager import trade_contract_count
            n = trade_contract_count(t)
            # Subtract hit targets
            for tgt in ("t1_hit_ts", "t2_hit_ts", "t3_hit_ts", "t4_hit_ts"):
                if getattr(t, tgt, None) is not None:
                    n -= 1
            n = max(0, n)
            if direction == "LONG":
                tm_qty += n
            elif direction == "SHORT":
                tm_qty -= n
            if n > 0:
                tm_trades.append(f"#{t.id}({mode},{direction},{n}c)")
    except Exception as e:
        logger.warning("[Reconciler] TM query error: %s", e)
        return True, f"TM query error: {e}"

    global _phantom_flat_streak
    if tm_qty == sierra_qty:
        _phantom_flat_streak = 0
        _short = _unprotected_contracts(sierra_qty)
        if _short:
            return True, (f"MATCH: TM={tm_qty} Sierra={sierra_qty} (src={src}) "
                          f"{_short}")
        return True, f"MATCH: TM={tm_qty} Sierra={sierra_qty} (src={src})"

    # ── PHANTOM-HEAL (Michael 07-13, PHANTOM_HEAL_V1) ──────────────────────
    # A trade FILLED in the backend with NO real Sierra fill (op=PLACE that
    # recorded an ENTRY-fill but never opened a position) stays active forever:
    # target-hit detection awaits real Sierra fills (I-62-FULL), none come, the
    # slot is blocked, and no new trades can fire (the 07-13 sim-day loss).
    # When Sierra is DEFINITIVELY flat (state-file qty=0 AND working=0) for
    # >=N consecutive checks while the backend is in-position, the backend is
    # wrong → close the phantom trade(s) and free the slot. Conservative to
    # avoid the OPPOSITE (07-10 phantom-CLOSE of a REAL trade): requires the
    # FRESH state file (not the events journal), zero working orders, and a
    # sustained streak — a momentary flat never triggers it. Flag default OFF.
    _heal_on = os.getenv("PHANTOM_HEAL_V1", "0").lower() in ("1", "true", "yes")
    _cancel_detect = os.getenv("MANUAL_CANCEL_DETECT_V1", "0").lower() in ("1", "true", "yes")
    _need = int(os.getenv("PHANTOM_HEAL_STREAK", "3"))
    _working = _sierra_state_working()
    if (_heal_on or _cancel_detect) and src == "state" and sierra_qty == 0 and _working == 0 and tm_qty != 0:
        _phantom_flat_streak += 1
        if _phantom_flat_streak >= _need:
            healed = []
            _reason = "manual_cancel" if _cancel_detect else "phantom_reconcile"
            try:
                for t in (tm.get_active_trades() or []):
                    if getattr(t, "mode", "shadow") not in ("demo", "live"):
                        continue
                    if getattr(t, "state", "") in ("CLOSED", "CANCELLED"):
                        continue
                    tid = getattr(t, "id", None)
                    if tid is None:
                        continue
                    if hasattr(tm, "close_trade"):
                        tm.close_trade(int(tid), reason=_reason)
                        healed.append(int(tid))
                    # MANUAL_CANCEL_DETECT_V1: mark CANCELLED + release slot
                    if _cancel_detect:
                        try:
                            if hasattr(t, "state"):
                                t.state = "CANCELLED"
                            if hasattr(t, "outcome"):
                                t.outcome = "CANCELLED"
                        except Exception:
                            pass
                        # Signal gateway to release slot immediately
                        try:
                            from backend.v9.gateway.trading_gateway import get_gateway
                            _gw = get_gateway()
                            if _gw and hasattr(_gw, "on_trade_close"):
                                _gw.on_trade_close(int(tid))
                        except Exception as _gwe:
                            logger.debug("[Reconciler] slot release signal: %s", _gwe)
            except Exception as _he:
                logger.warning("[Reconciler] phantom-heal/cancel close error: %s", _he)
            _phantom_flat_streak = 0
            _label = "MANUAL-CANCEL" if _cancel_detect else "PHANTOM-HEAL"
            hmsg = (f"{_label}: Sierra flat {_need}x (qty=0,working=0) but backend "
                    f"held {tm_trades} → {'cancelled' if _cancel_detect else 'closed'} "
                    f"{healed}, slot freed.")
            logger.warning("[Reconciler] SYS-3 %s", hmsg)
            try:
                from scripts.ops_log import log_event
                log_event("reconciler", "WARNING", hmsg)
            except Exception:
                pass
            try:
                from backend.v9.services.phone_alert import push as _pp
                _pp("phantom_heal", "\u267b\ufe0f MEMS26: %s" % _label, hmsg, priority=0)
            except Exception:
                pass
            return True, hmsg
    elif sierra_qty != 0:
        # Sierra is definitively NOT flat — the phantom condition is genuinely
        # over.  Reset.  (Michael 07-15 fix: only reset when Sierra proves it's
        # not flat.  A stale state file / heal-flag-off / momentary working!=0
        # should NOT wipe accumulated evidence — that caused 0/3 stuck loops.)
        _phantom_flat_streak = 0

    msg = (f"DIVERGENCE: TM says {tm_qty} contracts {tm_trades}, "
           f"Sierra says {sierra_qty} (src={src}). Records \u2260 reality!"
           + (f" [phantom-heal streak {_phantom_flat_streak}/{_need}]" if _heal_on else ""))

    # T5b (Michael 15.08: "\u05d0\u05ea\u05d4 \u05de\u05e7\u05e4\u05d9\u05e5 \u05dc\u05d9 \u05de\u05dc\u05d0 \u05d4\u05ea\u05e8\u05d0\u05d5\u05ea \u05d3\u05e4\u05d5\u05e7\u05d5\u05ea"). The reconciler
    # runs every 30s, so a single unchanged condition produced a WARNING every
    # 30s all evening. Alert on STATE CHANGE, then at most once every 10 min
    # while the same state persists; unchanged repeats drop to debug. Nothing
    # is suppressed \u2014 a NEW or CHANGED divergence is still immediate.
    global _last_div_state, _last_div_ts
    _div_state = (tm_qty, sierra_qty, src)
    _div_now = _time_mod.time()
    _div_changed = (_div_state != _last_div_state)
    _div_due = (_div_now - _last_div_ts) > 600.0
    _div_loud = _div_changed or _div_due
    if _div_loud:
        _last_div_state = _div_state
        _last_div_ts = _div_now

    # RECONCILER_OWNERSHIP_AWARE_V1 (Michael ruling 07-24, Phase 7.1):
    # Mixed account — Michael trades manually alongside the system. A Sierra
    # position with TM=0 could be Michael's manual trade, not an orphan.
    # Check: if no system-placed orders exist in the fill_poller order_map
    # (no sierra_order_id → trade_id mapping), the position is manual →
    # INFO only, not CRITICAL/NAKED/auto-stop. Flag OFF = byte-identical
    # to pre-V1 behavior.
    _ownership_aware = os.getenv(
        "RECONCILER_OWNERSHIP_AWARE_V1", "0").lower() in ("1", "true", "yes")
    _orphan_naked = (tm_qty == 0 and sierra_qty != 0)
    if _orphan_naked and _ownership_aware:
        _is_system_position = False
        _fp = fill_poller
        if _fp is None:
            try:
                import backend.main as _main_mod
                _main_app = getattr(_main_mod, "app", None)
                _fp = getattr(getattr(_main_app, "state", None),
                              "fill_poller", None)
            except Exception:
                pass  # fail-safe
        if _fp is not None:
            # T5 ROOT-FIX (2026-08-15). This was `len(_order_map) > 0` — a
            # GLOBAL test. The order map is a HISTORICAL order_id→trade_id
            # index, so the moment the system placed its first trade of the day
            # every later MANUAL position of Michael's was classified
            # "system-owned" → NAKED-ORPHAN. Measured 14.08: 113 false alarms,
            # and a DIVERGENCE warning every 30s while he scaled out by hand.
            # The correct test is per-position: the system owns a position only
            # if it currently HOLDS one. tm_qty==0 (this branch's precondition)
            # means the books hold nothing, so whatever Sierra shows is not ours
            # — unless the map still points at an OPEN trade.
            _omap = getattr(_fp, "_order_map", {})
            _open_ids = set()
            try:
                _tm_ref = getattr(_fp, "_tm", None) or getattr(_fp, "trade_manager", None)
                for _t in (getattr(_tm_ref, "get_active_trades", lambda: [])() or []):
                    _tid = getattr(_t, "id", None)
                    if _tid is not None:
                        _open_ids.add(int(_tid))
            except Exception:
                _open_ids = set()
            _is_system_position = any(
                int(v) in _open_ids for v in (_omap or {}).values()
                if str(v).isdigit()
            )
        if not _is_system_position:
            # Honest wording (Rule 1). With tm_qty==0 the books hold nothing, so
            # the system CANNOT prove whose position this is: "Michael opened it
            # by hand" and "the system's own exit never executed" look identical
            # from here. Claiming either with confidence is a synthesis. What is
            # certain is the actionable part — nothing is managing it — and that
            # the system will not touch it (12:20 ownership ruling). When the
            # order map still holds today's history the ambiguity is named
            # explicitly instead of being resolved by guess.
            _had_history = bool(_omap) if _fp is not None else False
            _manual_msg = (
                f"POSITION NOT IN BOOKS: Sierra {sierra_qty}c, no open system "
                f"trade → the system is NOT managing it and will not touch it."
            )
            if _had_history:
                _manual_msg += (
                    " (ambiguous: manual trade, or a system exit that never "
                    "executed — check the fills journal.)"
                )
            msg += f" \u2139\ufe0f {_manual_msg}"
            # MANUAL_POSITION_GUARD_V1 (Michael ruling 07-25 "התראה-בלבד"):
            # alert-only naked-stop watch on the MANUAL position. Never touches
            # orders/position — the 12:20 ownership ruling stays fully intact.
            _mg_alert = _manual_position_guard(sierra_qty)
            if _mg_alert:
                msg += f" {_mg_alert}"
                # MANUAL_GUARD_AUTOPROTECT_V1 (Michael ruling 2026-07-27, after a
                # >½-account loss on a naked manual position: "המערכת הייתה צריכה
                # להציב לי סטופ ... וזה לא קרה"). SUPERSEDES the 07-25 alert-only
                # ruling for the NAKED case only:
                #   • position HAS a working stop  → system never touches it (12:20 ruling)
                #   • position is NAKED past grace → arm the same virtual structural
                #     stop machinery used for orphans (recommend_orphan_stop +
                #     _place_orphan_stop): monitor, and FLATTEN_ORPHAN only when the
                #     structural stop is breached OR unrealized loss >= the cap.
                # Flag OFF → alert-only, byte-identical to 07-25.
                if _mg_os_env("MANUAL_GUARD_AUTOPROTECT_V1"):
                    try:
                        _mp_rec = recommend_orphan_stop(sierra_qty,
                                                        _sierra_state_avg_price())
                        if _mp_rec:
                            _mp_ok, _mp_status = _place_orphan_stop(_mp_rec)
                            msg += f" 🛡️ AUTOPROTECT[{_mp_status}]"
                            try:
                                from backend.v9.services.phone_alert import push as _mp_push
                                _mp_push("manual_autoprotect",
                                         "MANUAL AUTOPROTECT",
                                         f"פוזיציה-ידנית {sierra_qty}c ללא סטופ — "
                                         f"המערכת מגנה: {_mp_status} "
                                         f"(סטופ-מבני {_mp_rec.get('stop')})")
                            except Exception:
                                pass
                        else:
                            msg += " 🛡️ AUTOPROTECT[NO_RECOMMENDATION:avg missing]"
                    except Exception as _mp_err:
                        msg += f" 🛡️ AUTOPROTECT[ERROR:{type(_mp_err).__name__}]"
                        logger.warning("[Reconciler] manual autoprotect failed: %s", _mp_err)
                if _div_loud:
                    logger.critical("[Reconciler] SYS-3 %s", msg)
                else:
                    logger.debug("[Reconciler] SYS-3 (repeat) %s", msg)
            elif _div_loud:
                logger.info("[Reconciler] SYS-3 %s", msg)
            else:
                logger.debug("[Reconciler] SYS-3 (repeat) %s", msg)
            return True, msg  # ok=True — not a divergence, just manual

    # P3 (orphan): Sierra holds a position the backend does not track (TM=0,
    # Sierra!=0) → NAKED orphan. Compute the exact protective stop and surface it
    # so it can be placed instantly.
    #
    # ORPHAN_AUTO_STOP_V1 (Michael ruling 07-17): when flag ON + all safety
    # conditions hold → attempt to place a protective stop automatically.
    # When flag OFF (default) → alert-only, identical to pre-V1 behavior.
    if _orphan_naked:
        # Try auto-stop first (returns None when flag OFF → falls through)
        _auto_result = _try_orphan_auto_stop(sierra_qty, src)
        if _auto_result is not None:
            msg += f" \U0001f6e1\ufe0f ORPHAN_AUTO_STOP: {_auto_result}"
        else:
            # Flag OFF — existing alert-only behavior (byte-identical to pre-V1)
            _rec = recommend_orphan_stop(sierra_qty, _sierra_state_avg_price())
            if _rec:
                msg += (f" \U0001f534 NAKED ORPHAN {_rec['side']} {_rec['qty']}c @ {_rec['entry']}"
                        f" \u2192 PLACE PROTECTIVE STOP @ {_rec['stop']} ({_rec['points']:.0f}pt).")
            else:
                msg += (" \U0001f534 NAKED ORPHAN \u2014 avg_price unavailable; FLATTEN_ACCOUNT "
                        "immediately (cannot compute a protective stop).")
    if _div_loud:
        logger.warning("[Reconciler] SYS-3 %s", msg)
    else:
        logger.debug("[Reconciler] SYS-3 (repeat, unchanged) %s", msg)
    # IDEA-2 (Michael 07-13): records≠reality is exactly what he must know about
    # when away from the screen. Rate-limited inside push(); never raises.
    # T5 (Michael 08-15 "אתה מקפיץ לי מלא התראות דפוקות"): only push when the
    # divergence is NEW/CHANGED or the 10-minute reminder is due. An unchanged
    # divergence repeating every 30s must not become 120 pushes an hour.
    if _div_loud:
        try:
            from backend.v9.services.phone_alert import push as _phone_push
            _phone_push("reconciler_divergence", "\U0001f534 MEMS26: DIVERGENCE", msg, priority=1)
        except Exception:
            pass
    return False, msg
