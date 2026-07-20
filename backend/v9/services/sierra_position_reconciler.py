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

# ── ORPHAN_AUTO_STOP_V1 constants ─────────────────────────────────────────────
ORPHAN_AUTO_STOP_MAX_QTY = int(os.getenv("ORPHAN_AUTO_STOP_MAX_QTY", "10"))
ORPHAN_AUTO_STOP_COOLDOWN_S = float(os.getenv("ORPHAN_AUTO_STOP_COOLDOWN_S", "60"))

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
        data = json.loads(STATE_FILE.read_text().strip() or "{}")
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
        data = json.loads(STATE_FILE.read_text().strip() or "{}")
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
        data = json.loads(STATE_FILE.read_text().strip() or "{}")
        ap = data.get("avg_price")
        return float(ap) if ap not in (None, "", 0, 0.0) else None
    except (OSError, ValueError, TypeError):
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


# ── Virtual stop state: tracks the orphan stop level being monitored ──
# {(qty, entry): {"stop": float, "side": str, "set_ts": float}}
_virtual_stop: dict = {}


def _check_virtual_stop_crossed(sierra_qty: int, rec: dict) -> bool:
    """Check if the current price has crossed the virtual stop level.

    Reads the latest bar close from sierra_state.json (already fresh at this
    point — the reconciler only runs when state is fresh). Returns True if
    the protective stop level has been breached.
    """
    try:
        if not STATE_FILE.exists():
            return False
        data = json.loads(STATE_FILE.read_text().strip() or "{}")
        # Use avg_price as proxy for current price (it's the position's avg,
        # but we also need last_price or similar). Check if the state has a
        # last_price field; otherwise fall back to checking the state file's
        # price fields.
        last_price = data.get("last_price") or data.get("last_trade_price")
        if last_price is None:
            return False
        last_price = float(last_price)
        stop = rec["stop"]
        if rec["side"] == "LONG":
            return last_price <= stop  # LONG: price fell to/below stop
        else:
            return last_price >= stop  # SHORT: price rose to/above stop
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


def _flatten_orphan(rec: dict) -> Tuple[bool, str]:
    """Execute a market-exit for an orphan position via FLATTEN_ORPHAN DLL op.

    Michael ruling 2026-07-20. ACSIL cannot place resting STOP orders.
    Architecture: backend monitors virtual stop; when crossed, sends this
    market-exit command. Uses proven SellExit/BuyExit + SCT_ORDERTYPE_MARKET.

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
            data = json.loads(STATE_FILE.read_text().strip() or "{}")
            account = data.get("account") or data.get("trade_account")
    except (OSError, json.JSONDecodeError):
        pass

    write_flatten_orphan(qty=rec["qty"], side=rec["side"], account=account)
    return _read_flatten_result(pre_mtime)


def _place_orphan_stop(rec: dict) -> Tuple[bool, str]:
    """Set up a virtual stop for an orphan position.

    Michael ruling 2026-07-20: ACSIL cannot place resting STOP orders.
    Instead, we set a virtual stop level and monitor it each reconciler cycle.
    When price crosses the virtual stop → FLATTEN_ORPHAN (market-exit).

    On first call: registers the virtual stop level → returns (True, "VIRTUAL_STOP_SET").
    On subsequent calls: checks if price crossed → if yes, sends FLATTEN_ORPHAN.
    """
    key = (rec["qty"], rec["entry"])

    # Check if virtual stop already set for this position
    if key in _virtual_stop:
        vs = _virtual_stop[key]
        # Check if price has crossed the virtual stop
        if _check_virtual_stop_crossed(rec["qty"] if rec["side"] == "LONG" else -rec["qty"], rec):
            # Price crossed — flatten!
            logger.critical("[Reconciler] VIRTUAL STOP CROSSED: %s @ %.2f → FLATTEN_ORPHAN",
                           rec["side"], rec["stop"])
            ok, status = _flatten_orphan(rec)
            if ok:
                del _virtual_stop[key]  # clear after successful flatten
            return ok, f"FLATTEN_TRIGGERED({status})"
        else:
            return True, (f"VIRTUAL_STOP_MONITORING: {rec['side']} stop @ {rec['stop']}, "
                         f"watching since {vs['set_ts']:.0f}")

    # First time — register the virtual stop
    _virtual_stop[key] = {
        "stop": rec["stop"],
        "side": rec["side"],
        "set_ts": _time_mod.time(),
    }
    return True, (f"VIRTUAL_STOP_SET: {rec['side']} stop @ {rec['stop']} for "
                 f"{rec['qty']}c @ {rec['entry']}")


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
      6. abs(qty) <= ORPHAN_AUTO_STOP_MAX_QTY (sanity cap)
      7. idempotency: not already placed for this (qty, avg_price)
      8. cooldown: at least ORPHAN_AUTO_STOP_COOLDOWN_S since last attempt
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
    if abs(sierra_qty) > ORPHAN_AUTO_STOP_MAX_QTY:
        return (f"SKIP(qty-too-large): |{sierra_qty}| > {ORPHAN_AUTO_STOP_MAX_QTY} "
                f"— refusing (possible bad read)")

    # Condition 7: idempotency
    key = (sierra_qty, rec["entry"])
    if key in _orphan_stop_placed:
        return (f"SKIP(already-placed): stop already attempted for "
                f"qty={sierra_qty} entry={rec['entry']} "
                f"at {_orphan_stop_placed[key]:.0f}")

    # Condition 8: cooldown
    now = _time_mod.time()
    if (now - _orphan_stop_last_attempt) < ORPHAN_AUTO_STOP_COOLDOWN_S:
        return (f"SKIP(cooldown): {now - _orphan_stop_last_attempt:.0f}s "
                f"< {ORPHAN_AUTO_STOP_COOLDOWN_S:.0f}s cooldown")

    # All conditions met — attempt placement
    _orphan_stop_last_attempt = now
    try:
        ok, reason = _place_orphan_stop(rec)
    except Exception as exc:
        # Safety: reconciler never crashes from this feature
        logger.error("[Reconciler] ORPHAN_AUTO_STOP placement exception: %s", exc)
        return f"ERROR(placement-exception): {exc}"

    if ok:
        # Record for idempotency
        _orphan_stop_placed[key] = now
        # Log to ops_log + phone
        _log_msg = (f"ORPHAN_AUTO_STOP PLACED: {rec['side']} stop @ {rec['stop']} "
                    f"for {rec['qty']}c @ {rec['entry']} ({rec['points']:.0f}pt)")
        logger.critical("[Reconciler] %s", _log_msg)
        try:
            from scripts.ops_log import log_event
            log_event("reconciler", "CRITICAL", _log_msg)
        except Exception:
            pass
        try:
            from backend.v9.services.phone_alert import push as _pp
            _pp("orphan_auto_stop", "\U0001f6e1\ufe0f MEMS26: ORPHAN STOP PLACED", _log_msg, priority=1)
        except Exception:
            pass
        return f"PLACED: {_log_msg}"
    else:
        # Placement failed — escalate to existing alert (don't swallow)
        logger.warning("[Reconciler] ORPHAN_AUTO_STOP failed: %s", reason)
        try:
            from scripts.ops_log import log_event
            log_event("reconciler", "WARNING", f"ORPHAN_AUTO_STOP failed: {reason}")
        except Exception:
            pass
        return f"FAILED({reason})"


# Phantom-heal: consecutive checks where TM is in-position but Sierra is
# definitively flat (qty=0, working=0). Reset on any other outcome.
_phantom_flat_streak = 0


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


def reconcile_position(tm) -> Tuple[bool, str]:
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
    _need = int(os.getenv("PHANTOM_HEAL_STREAK", "3"))
    _working = _sierra_state_working()
    if _heal_on and src == "state" and sierra_qty == 0 and _working == 0 and tm_qty != 0:
        _phantom_flat_streak += 1
        if _phantom_flat_streak >= _need:
            healed = []
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
                        tm.close_trade(int(tid), reason="phantom_reconcile")
                        healed.append(int(tid))
            except Exception as _he:
                logger.warning("[Reconciler] phantom-heal close error: %s", _he)
            _phantom_flat_streak = 0
            hmsg = (f"PHANTOM-HEAL: Sierra flat {_need}x (qty=0,working=0) but backend "
                    f"held {tm_trades} → closed phantom {healed}, slot freed.")
            logger.warning("[Reconciler] SYS-3 %s", hmsg)
            try:
                from backend.v9.services.phone_alert import push as _pp
                _pp("phantom_heal", "\u267b\ufe0f MEMS26: phantom \u05e0\u05d5\u05e7\u05d4", hmsg, priority=0)
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

    # P3 (orphan): Sierra holds a position the backend does not track (TM=0,
    # Sierra!=0) → NAKED orphan. Compute the exact protective stop and surface it
    # so it can be placed instantly.
    #
    # ORPHAN_AUTO_STOP_V1 (Michael ruling 07-17): when flag ON + all safety
    # conditions hold → attempt to place a protective stop automatically.
    # When flag OFF (default) → alert-only, identical to pre-V1 behavior.
    _orphan_naked = (tm_qty == 0 and sierra_qty != 0)
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
    logger.warning("[Reconciler] SYS-3 %s", msg)
    # IDEA-2 (Michael 07-13): records≠reality is exactly what he must know about
    # when away from the screen. Rate-limited inside push(); never raises.
    try:
        from backend.v9.services.phone_alert import push as _phone_push
        _phone_push("reconciler_divergence", "\U0001f534 MEMS26: DIVERGENCE", msg, priority=1)
    except Exception:
        pass
    return False, msg
