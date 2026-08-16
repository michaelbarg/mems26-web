"""Sierra command file writer for DEMO/LIVE execution paths.

Writes the command format consumed by the Bridge/DLL through
`trade_command.json`. This module has no network or broker side effects.

Pipeline 5 Phase 2: extended with op-based dispatch:
  PLACE     — entry bracket (existing BUY/SELL)
  MODIFY_STOP   — move stop on tracked order
  MODIFY_TARGET — move target on tracked order
  EXIT          — market exit N contracts (partial or full)
  CANCEL        — kill working orders / flatten
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("sierra_command")

DEFAULT_SIGNALS_DIR = Path("/tmp/mems26_signals")


def signals_dir() -> Path:
    return Path(os.getenv("MEMS26_SIGNALS_DIR", str(DEFAULT_SIGNALS_DIR)))


def command_file() -> Path:
    return signals_dir() / "trade_command.json"


LIVE_SIGNALS_DIR = Path(os.path.expanduser("~/SierraChart_Data/v9_export"))


def _assert_not_a_test_writing_live(out: Path) -> None:
    """Refuse to arm the live wire from inside a test run.

    2026-07-28: the regression suite placed REAL orders on the live account.
    MEMS26_SIGNALS_DIR was unset in tests, so it defaulted to the live export
    folder, and `trade_command.json` is not a log — the Sierra DLL polls it and
    submits whatever it finds. Sierra's log for that day carries six broker
    rejections ("Insufficient Account Value (NLV) for margin"); the account being
    under-margined is the only reason none of them filled.

    tests/conftest.py now redirects the signals dir, which is the fix. This is
    the second lock, at the single choke point every command passes through, so
    that a hard-coded path or a conftest that gets edited later cannot quietly
    re-arm the wire. Pytest sets PYTEST_CURRENT_TEST for every test it runs.
    """
    if not os.getenv("PYTEST_CURRENT_TEST"):
        return
    try:
        same = out.resolve().parent == LIVE_SIGNALS_DIR.resolve()
    except OSError:
        same = str(out.parent) == str(LIVE_SIGNALS_DIR)
    if same:
        raise RuntimeError(
            f"REFUSING to write a trade command to the LIVE signals dir ({out}) "
            "from a test process. The Sierra DLL executes this file. Point "
            "MEMS26_SIGNALS_DIR at a tmp_path."
        )


_cmd_seq = 0
_cmd_lock = __import__("threading").Lock()


def _command_queue_dir() -> Path:
    return signals_dir() / "command_queue"


def _archived_stale_dir() -> Path:
    return _command_queue_dir() / "archived_stale"


def _cmd_ttl_s() -> float:
    """Backend-side command TTL. The DLL op-path has NO TTL/dedup (only the
    legacy C5 checksum path does), so a stale queue file replayed later would
    EXECUTE — including CANCEL (= FlattenAndCancelAllOrders) and PLACE with
    contracts<=0 (DLL defaults it to 3, merged.cpp:2870). Friday 08-07 left a
    PLACE+CANCEL from hours earlier sitting in the queue; this TTL is the root
    protection that they can never auto-send (K1c, 2026-08-08)."""
    try:
        return float(os.getenv("SIERRA_CMD_TTL_S", "90"))
    except (TypeError, ValueError):
        return 90.0


def _ack_grace_s() -> float:
    """How long a SENT command may wait for a DLL ACK before it is archived.
    We never RESEND a sent command: a missing ACK cannot be distinguished from
    'executed but trade_result.json write failed' (a known silent-failure mode,
    merged.cpp:3040) — resending could double-place. Archive + WARNING."""
    try:
        return float(os.getenv("SIERRA_CMD_ACK_GRACE_S", "15"))
    except (TypeError, ValueError):
        return 15.0


def pending_command_count() -> int:
    """Number of queue files awaiting the drainer (cheap gate for the host loop)."""
    queue_dir = _command_queue_dir()
    if not queue_dir.exists():
        return 0
    try:
        return sum(1 for _ in queue_dir.glob("cmd_*.json"))
    except OSError:
        return 0


def _seed_seq_from_disk_locked(queue_dir: Path) -> None:
    """Continue the on-disk numbering after a backend restart (call under _cmd_lock).

    _cmd_seq starts at 0 in every new process; without this, the first command
    after a restart would be cmd_000001.json and OVERWRITE an unsent file left
    from the previous run."""
    global _cmd_seq
    if _cmd_seq != 0:
        return
    top = 0
    for d in (queue_dir, _archived_stale_dir()):
        try:
            if not d.exists():
                continue
            for f in d.glob("cmd_*.json"):
                try:
                    top = max(top, int(f.stem.split("_")[1]))
                except (IndexError, ValueError):
                    continue
        except OSError:
            continue
    _cmd_seq = top


def _write_command(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Write a command to the sequenced queue (P0-1 fix, #633/#643).

    Instead of overwriting a single file (race: MODIFY_STOP clobbered by
    MODIFY_TARGET), each command gets its own numbered file in command_queue/.
    The drainer (drain_command_queue, hosted by the FillPoller loop) sends the
    oldest unsent file to trade_command.json, waits for the DLL ACK, then
    removes it.

    Fast path (latency): when the queue is EMPTY, the command is also written
    to trade_command.json immediately and the queue file is stamped
    `_sent_ts`, so a lone fire/emergency command does not wait for a poller
    tick. The drainer then only ACK-tracks it — it never re-sends a stamped
    file (re-sending an already-executed PLACE would double-place; the DLL
    op-path has no dedup).

    2026-08-08 (K1a root): the old fast path checked the queue AFTER writing
    its own file (`len(pending) <= 1`) and nothing ever drained — after
    Friday's first command the queue held a file forever, so every later
    command (PLACE #652, CANCEL #652) was queued and never reached the DLL.
    """
    global _cmd_seq
    out = command_file()
    _assert_not_a_test_writing_live(out)
    out.parent.mkdir(parents=True, exist_ok=True)

    with _cmd_lock:
        queue_dir = _command_queue_dir()
        queue_dir.mkdir(parents=True, exist_ok=True)
        _seed_seq_from_disk_locked(queue_dir)
        _cmd_seq += 1
        payload["_seq"] = _cmd_seq
        payload["_ts_queued"] = time.time()

        # Fast-path decision BEFORE writing our own queue file: only when no
        # other command is pending may we write the live file directly.
        others_pending = sum(1 for _ in queue_dir.glob("cmd_*.json"))
        fast_path = others_pending == 0
        if fast_path:
            payload["_sent_ts"] = time.time()

        queue_file = queue_dir / f"cmd_{_cmd_seq:06d}.json"
        queue_file.write_text(json.dumps(payload, indent=2))
        if fast_path:
            out.write_text(json.dumps(payload, indent=2))

    logger.warning(
        "[SierraCmd] COMMAND QUEUED #%d → %s (op=%s, pending_before=%d, fast_path=%s)",
        _cmd_seq, queue_file, payload.get("op") or payload.get("action"),
        others_pending, fast_path)

    # F1 (2026-08-12, ORDER_FAILED retry-once): remember the last PLACE payload
    # per trade_id so the FillPoller can resubmit it exactly once when Sierra
    # returns a synchronous ORDER_FAILED (r<=0 → no order exists, resend-safe).
    # In-memory only — a restart forgets, which is the safe direction.
    if payload.get("op") == "PLACE" and payload.get("trade_id") is not None:
        clean = {k: v for k, v in payload.items() if not k.startswith("_")}
        _LAST_PLACE[str(payload["trade_id"])] = clean
        while len(_LAST_PLACE) > _LAST_PLACE_CAP:
            _LAST_PLACE.pop(next(iter(_LAST_PLACE)))
    return payload


# F1 (2026-08-12): last PLACE payload per trade_id — see note in _write_command.
_LAST_PLACE: Dict[str, Dict[str, Any]] = {}
_LAST_PLACE_CAP = 50


def get_last_place_command(trade_id) -> Optional[Dict[str, Any]]:
    """The clean (no queue metadata) PLACE payload last sent for trade_id, or None."""
    return _LAST_PLACE.get(str(trade_id))


def resubmit_place(trade_id) -> Optional[Dict[str, Any]]:
    """Re-queue the remembered PLACE for trade_id (fresh seq/ts). None if unknown.

    Only safe after a SYNCHRONOUS ORDER_FAILED (BuyEntry/SellEntry returned <= 0,
    so no order exists at Sierra). Callers enforce the once-only policy.
    """
    cmd = get_last_place_command(trade_id)
    if cmd is None:
        return None
    payload = dict(cmd)
    payload["ts_submitted"] = time.time()
    payload["_retry_of"] = str(trade_id)
    return _write_command(payload)


def drain_command_queue(*, timeout_s: float = 2.0) -> int:
    """Drain the command queue → trade_command.json, one command at a time.

    Runtime host: the FillPoller loop (backend/v9/services/fill_poller.py, the
    0.25s always-alive task that already shepherds trade_command/trade_result).
    Offloaded to a worker thread there because the ACK wait blocks.

    Per queue file, oldest first:
      • sent (`_sent_ts`) + ACKed (trade_result.json mtime > _sent_ts) → remove.
      • sent + no ACK, within SIERRA_CMD_ACK_GRACE_S → STOP draining (the wire
        is busy; never overwrite an in-flight command).
      • sent + no ACK past grace → archive to archived_stale/ + WARNING. Never
        resent: 'no ACK' is indistinguishable from 'executed, result write
        failed' — a resend could double-place.
      • unsent + older than SIERRA_CMD_TTL_S → archive + WARNING, never sent
        (stale trading commands must not fire later; the DLL op-path has no TTL).
      • unsent + fresh → mark `_sent_ts` (under _cmd_lock, so the fast path
        cannot double-send it), write to trade_command.json, wait up to
        timeout_s for ACK. ACKed → remove + continue; no ACK yet → STOP (next
        cycle re-checks; grace expiry above eventually archives).

    Returns the number of queue files completed (ACKed+removed or archived).
    Exceptions on one file never propagate — WARNING + stop, retry next cycle.
    """
    queue_dir = _command_queue_dir()
    if not queue_dir.exists():
        return 0

    out = command_file()
    _assert_not_a_test_writing_live(out)
    result_file = signals_dir() / "trade_result.json"
    now = time.time()
    drained = 0

    def _result_mtime() -> float:
        try:
            return result_file.stat().st_mtime if result_file.exists() else 0.0
        except OSError:
            return 0.0

    def _archive(cmd_file: Path, why: str) -> None:
        dest_dir = _archived_stale_dir()
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / cmd_file.name
        cmd_file.rename(dest)
        logger.warning("[SierraCmd] ARCHIVED %s → archived_stale/ (%s) — NOT sent",
                       cmd_file.name, why)

    for cmd_file in sorted(queue_dir.glob("cmd_*.json")):
        try:
            payload = json.loads(cmd_file.read_text())
            queued_ts = float(payload.get("_ts_queued") or payload.get("ts_submitted")
                              or cmd_file.stat().st_mtime)
            sent_ts = payload.get("_sent_ts")

            if sent_ts is not None:
                # Already on the wire (fast path or a previous drain cycle).
                if _result_mtime() > float(sent_ts):
                    cmd_file.unlink(missing_ok=True)
                    drained += 1
                    logger.info("[SierraCmd] ACK confirmed for %s — removed from queue",
                                cmd_file.name)
                    continue
                if (now - float(sent_ts)) > _ack_grace_s():
                    _archive(cmd_file, f"sent {now - float(sent_ts):.0f}s ago, no DLL ACK "
                                       f"(grace {_ack_grace_s():.0f}s) — will not resend")
                    drained += 1
                    continue
                break  # in-flight, wire busy — never overwrite it

            if (now - queued_ts) > _cmd_ttl_s():
                _archive(cmd_file, f"queued {now - queued_ts:.0f}s ago > TTL "
                                   f"{_cmd_ttl_s():.0f}s (op={payload.get('op')}, "
                                   f"trade_id={payload.get('trade_id')})")
                drained += 1
                continue

            # Fresh + unsent → send now. Re-check under the lock so a racing
            # fast-path write of THIS file cannot lead to a double-send.
            with _cmd_lock:
                payload = json.loads(cmd_file.read_text())
                if payload.get("_sent_ts") is not None:
                    continue  # fast path beat us to it — next cycle ACK-tracks
                payload["_sent_ts"] = time.time()
                cmd_file.write_text(json.dumps(payload, indent=2))
                out.write_text(json.dumps(payload, indent=2))
            write_ts = payload["_sent_ts"]
            logger.info("[SierraCmd] DRAIN %s → trade_command.json (op=%s, trade_id=%s)",
                        cmd_file.name, payload.get("op"), payload.get("trade_id"))

            deadline = write_ts + timeout_s
            acked = False
            while time.time() < deadline:
                if _result_mtime() > write_ts:
                    acked = True
                    break
                time.sleep(0.1)

            if acked:
                cmd_file.unlink(missing_ok=True)
                drained += 1
                logger.info("[SierraCmd] ACK received for %s", cmd_file.name)
                continue
            logger.warning("[SierraCmd] no ACK for %s within %.1fs — holding queue "
                           "(re-check next cycle, archive after %.0fs grace)",
                           cmd_file.name, timeout_s, _ack_grace_s())
            break

        except Exception as e:
            logger.warning("[SierraCmd] drain error on %s: %s", cmd_file.name, e)
            break  # don't remove on error — retry next cycle

    return drained


def write_trade_command(
    *,
    action: str,
    trade_id: Optional[str],
    direction: Optional[str] = None,
    price: Optional[float] = None,
    contracts: Optional[int] = None,
    stop_price: Optional[float] = None,
    target_price: Optional[float] = None,
    account: Optional[str] = None,
    mode: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Write a PLACE (entry bracket) Sierra command."""
    action = action.upper()
    payload = {
        "op": "PLACE",
        "action": action,
        "trade_id": trade_id,
        "direction": direction,
        "price": price,
        "contracts": contracts,
        "stop_price": stop_price,
        "target_price": target_price,
        "account": account,
        "mode": mode,
        "context": context or {},
        "ts_submitted": time.time(),
    }
    return _write_command(payload)


def write_modify_stop(
    *,
    trade_id: str,
    order_id: int,
    new_stop: float,
    stop_ids: Optional[list] = None,
    mode: str = "demo",
) -> Dict[str, Any]:
    """Write a MODIFY_STOP command — trail/re-anchor the protective stop.

    stop_ids: per-contract stop order IDs [c1_stop, c2_stop, c3_stop].
    The DLL reads these directly instead of relying on persistent slots
    (which Pipeline 5 may clear). Falls back to order_id if absent.
    """
    payload: Dict[str, Any] = {
        "op": "MODIFY_STOP",
        "trade_id": trade_id,
        "order_id": order_id,
        "new_stop": new_stop,
        "mode": mode,
        "ts_submitted": time.time(),
    }
    if stop_ids:
        payload["stop_ids"] = stop_ids
    return _write_command(payload)


def write_modify_target(
    *,
    trade_id: str,
    order_id: int,
    new_target: float,
    mode: str = "demo",
) -> Dict[str, Any]:
    """Write a MODIFY_TARGET command — re-anchor the next target."""
    return _write_command({
        "op": "MODIFY_TARGET",
        "trade_id": trade_id,
        "order_id": order_id,
        "new_target": new_target,
        "mode": mode,
        "ts_submitted": time.time(),
    })


def write_place_bracket(
    *,
    qty: int,
    stop: float,
    side: str,
    target: Optional[float] = None,
) -> Dict[str, Any]:
    """Write a PLACE_BRACKET command — a resting stop (+ optional target) on an
    EXISTING position.

    W8 v3 (Michael 2026-07-28: "המערכת כן תוכל לנהל עסקה שאני מבצע ולהוסיף לה
    סטופ ונקודות מימוש"). v2 wrote op=PLACE_STOP for a DLL handler that called
    sc.SubmitOrder — a symbol that does not exist in ACSIL. The DLL now uses the
    Exit family with SCT_ORDERTYPE_OCO_LIMIT_STOP (target given) or
    SCT_ORDERTYPE_STOP (stop only).

    `side` is the side of the POSITION being protected (LONG/SHORT), not the
    order side — the DLL derives the order side from the live position sign and
    refuses on mismatch. No account field is ever sent: the DLL uses
    sc.SelectedTradeAccount, which was the root cause of every r=-1 on 07-27.

    Price sanity is enforced DLL-side against the live market price, but a
    wrong-sided request is rejected here too so it never reaches the wire.
    """
    side = side.upper()
    if side not in ("LONG", "SHORT"):
        raise ValueError(f"PLACE_BRACKET side must be LONG or SHORT, got {side!r}")
    if qty <= 0:
        raise ValueError(f"PLACE_BRACKET qty must be >0, got {qty}")
    if stop <= 0:
        raise ValueError(f"PLACE_BRACKET stop must be >0, got {stop}")
    if target is not None:
        if target <= 0:
            raise ValueError(f"PLACE_BRACKET target must be >0, got {target}")
        # long: stop below, target above. short: the reverse. Equal is invalid.
        if side == "LONG" and not (stop < target):
            raise ValueError(
                f"PLACE_BRACKET LONG needs stop < target, got stop={stop} target={target}")
        if side == "SHORT" and not (target < stop):
            raise ValueError(
                f"PLACE_BRACKET SHORT needs target < stop, got stop={stop} target={target}")
    payload: Dict[str, Any] = {
        "op": "PLACE_BRACKET",
        "qty": qty,
        "stop": round(stop, 2),
        "side": side,
        "ts_submitted": time.time(),
    }
    if target is not None:
        payload["target"] = round(target, 2)
    # NO account field — the DLL uses sc.SelectedTradeAccount.
    return _write_command(payload)


def write_flatten_orphan(
    *,
    qty: int,
    side: str,
    account: Optional[str] = None,
) -> Dict[str, Any]:
    """Write a FLATTEN_ORPHAN command — market-exit for orphan position.

    Michael ruling 2026-07-20. Backend monitors a virtual stop; when price
    crosses it, sends this command → DLL executes market-exit via proven
    SellExit/BuyExit + SCT_ORDERTYPE_MARKET path.
    side: "LONG" or "SHORT" (the POSITION side being flattened).
    """
    side = side.upper()
    if side not in ("LONG", "SHORT"):
        raise ValueError(f"FLATTEN_ORPHAN side must be LONG or SHORT, got {side!r}")
    if qty <= 0:
        raise ValueError(f"FLATTEN_ORPHAN qty must be >0, got {qty}")
    payload: Dict[str, Any] = {
        "op": "FLATTEN_ORPHAN",
        "qty": qty,
        "side": side,
        "ts_submitted": time.time(),
    }
    if account:
        payload["account"] = account
    return _write_command(payload)


def write_flatten_account(
    *,
    trade_id: Optional[str] = None,
    source: str = "",
    reason: str = "",
    account: Optional[str] = None,
) -> Dict[str, Any]:
    """Write a FLATTEN_ACCOUNT command — flatten the NET position + cancel all.

    ROOT-FIX 2026-08-15. Every FLATTEN_ACCOUNT caller used
    `write_trade_command(action="FLATTEN_ACCOUNT", context={...})`, but that
    function declares `trade_id` as a REQUIRED keyword-only argument — the
    callers passed it inside `context` instead, so every call raised TypeError
    before a byte was written. Live cost (Michael, 14.08): S6 announced
    MAE_SCRATCH on trade #682 and closed the books at $0 while Sierra kept
    SHORT 4 @7799.25 for ~58 minutes and finally stopped out at −$83.75. The
    same defect silently disabled TARGET_APPROACH_REALIZE (never executed once)
    and the phone FLATTEN button.

    This helper exists so the exit path cannot be mis-called: no required
    positional/keyword trap, explicit `op` (the old call shipped op="PLACE"
    with a FLATTEN action — the DLL only matched by substring), and one place
    to audit. DLL handler: MES_AI_DataExport_merged.cpp:3605.
    """
    payload: Dict[str, Any] = {
        "op": "FLATTEN_ACCOUNT",
        "action": "FLATTEN_ACCOUNT",
        "trade_id": trade_id,
        "context": {"source": source, "reason": reason,
                    **({"trade_id": trade_id} if trade_id else {})},
        "ts_submitted": time.time(),
    }
    if account:
        payload["account"] = account
    return _write_command(payload)


def write_exit(
    *,
    trade_id: str,
    order_id: int,
    contracts: int,
    direction: Optional[str] = None,
    mode: str = "demo",
) -> Dict[str, Any]:
    """Write an EXIT command — market exit N contracts (partial or full).

    D1 fix: include direction so DLL can determine exit side even when
    GetTradePosition returns 0 and persistent slot 107 is unset.
    """
    payload: Dict[str, Any] = {
        "op": "EXIT",
        "trade_id": trade_id,
        "order_id": order_id,
        "contracts": contracts,
        "mode": mode,
        "ts_submitted": time.time(),
    }
    if direction:
        payload["direction"] = direction.upper()
    return _write_command(payload)


def write_cancel(
    *,
    trade_id: str,
    order_id: Optional[int] = None,
    mode: str = "demo",
) -> Dict[str, Any]:
    """Write a CANCEL command — kill working orders / flatten."""
    return _write_command({
        "op": "CANCEL",
        "trade_id": trade_id,
        "order_id": order_id,
        "mode": mode,
        "ts_submitted": time.time(),
    })


def _effective_contracts_raw(setup: Dict[str, Any]) -> int:
    """The LIVE contract count for a setup — single source of truth (L7, 2026-07-08).

    Extracted verbatim from command_from_setup so accept_setup can persist the
    SAME number the Sierra command sends (symmetry: bracket = DB = display).

    Contract count lives in metadata.sizing (numeric) for the firing systems; the old
    top-level "contracts"/"size" lookup missed it → demo placed 1 contract instead of the
    N-contract per-contract bracket (verified 06-29: trade 257 placed C1 only).

    FIXED_CONTRACTS_3 (Michael 2026-07-01): single command choke point — guarantee
    every fire sends 3 contracts to Sierra for BOTH S2 and S4, demo + live. Belt-and-
    suspenders over the sizing-source overrides (quality_tier / compute_v2_sizing) so
    no path can send !=3 when the flag is on. Only setups that reached command-write
    have already passed the fire decision, so the count is always >0 here.
    FIXED_CONTRACTS_2 (Michael 2026-07-06): 2-contract choke point, PRECEDENCE over _3.
    SIZE_CAP_OVER_FIXED_V1 (default OFF): when ON, a downward SIZE_CAP_CUT_V1 reduction
    already baked into the setup (e.g. metadata.sizing="half"→2) survives the FIXED
    override — the fixed count becomes a cap that can only REDUCE (min(fixed, cut)),
    never re-force back up to 3. See the inline comment for the ruling reference.
    """
    _sz = setup.get("contracts") or setup.get("size") or (setup.get("metadata") or {}).get("sizing")
    try:
        _contracts = max(1, int(_sz))
    except (TypeError, ValueError):
        _contracts = {"full": 3, "half": 2, "quarter": 1}.get(str(_sz).lower().strip(), 1)
    # CONFLUENCE_RI_ZLR exemption (spec docs/handoff/CONFLUENCE_PATTERN_SPEC_
    # 2026-07-17.md §4.3): the combined S2×S4 pattern trades EXACTLY its own
    # count — 2 contracts, sizing "tactical" (mode_caps.tactical in
    # config/stop_anchors.yaml) — and is EXEMPT from the FIXED_CONTRACTS_*
    # force below (FIXED_CONTRACTS_4 would ship 4, violating the pattern
    # definition). Scoped by the per-setup metadata flag, which ONLY the
    # confluence builder sets (backend/v9/systems/confluence/confluence_ri_
    # zlr.py) — S2/S4/regular setups never carry it, so every other path is
    # byte-identical (regular ZLR under FIXED_CONTRACTS_4=1 still ships 4).
    # A downward SIZE_CAP_CUT is honored upstream (already baked into the
    # setup's own count before it reaches here). Regression:
    # tests/v9/regression/test_confluence_ri_zlr.py.
    if (setup.get("metadata") or {}).get("fixed_contracts_exempt"):
        return _contracts
    import os as _fc3_os
    _fc4_on = _fc3_os.environ.get("FIXED_CONTRACTS_4", "0").lower() in ("1", "true", "yes")  # Michael 07-15, top precedence
    _fc2_on = _fc3_os.environ.get("FIXED_CONTRACTS_2", "0").lower() in ("1", "true", "yes")
    _fc3_on = _fc3_os.environ.get("FIXED_CONTRACTS_3", "0").lower() in ("1", "true", "yes")

    # SIZE_CAP_OVER_FIXED_V1 (default OFF — Michael sign-off required to enable;
    # trading-risk-surface change per Pre-LIVE Discipline).
    # RULED SIZE_CAP_CUT_V1 (Michael 2026-07-09): the judgment size-cut "still
    # overrides downward, even under FIXED_CONTRACTS" (config/RULED_FLAGS.yaml
    # FIXED_CONTRACTS_3 note; docs/FLAG_INDEX.md SIZE_CAP_CUT_V1). Upstream
    # compute_v2_sizing already applies that cut, so the setup arrives here with
    # an already-reduced count (S4/woodies collapses it to metadata.sizing="half"
    # → 2; S2/five_min passes numeric sizing_contracts). But the FIXED_CONTRACTS_*
    # override just below re-forces 2/3 whenever the count is >0 — CLOBBERING the
    # cut, so a wide-stop trade that should carry 1-2 contracts still ships 3.
    # When this flag is ON we HONOR the setup's own (already-cut) count as an
    # upper cap FIXED can only REDUCE toward, never raise: min(fixed, cut). A
    # full SKIP (explicit 0 / "reject" / "skip") stays 0; a *missing* sizing
    # field means "no cut info" → keep the fixed count (never a spurious cut to
    # the floor-1 default). When OFF the result is byte-identical to the historic
    # force-2 / force-3 behavior below.
    if _fc3_os.environ.get("SIZE_CAP_OVER_FIXED_V1", "0").lower() in ("1", "true", "yes"):
        _fixed = 4 if _fc4_on else (2 if _fc2_on else (3 if _fc3_on else _contracts))
        # None-aware read (NOT the truthy or-chain above, which masks an explicit
        # 0) so a real SKIP is distinguishable from a missing field.
        _raw = setup.get("contracts")
        if _raw is None:
            _raw = setup.get("size")
        if _raw is None:
            _raw = (setup.get("metadata") or {}).get("sizing")
        if _raw is None:
            return _fixed  # no sizing info → keep fixed count, do not cut
        if _raw == 0 or str(_raw).strip().lower() in ("0", "reject", "skip"):
            return 0  # explicit full SKIP preserved (never forced up to fixed)
        try:
            _cut = max(1, int(_raw))
        except (TypeError, ValueError):
            # 07-15: "full" means FULL RULED SIZE — it is not a cut. The old
            # literal 3 silently capped the 4-contract ruling back to 3
            # (caught by fire_drill on deploy day).
            _cut = {"full": _fixed, "half": 2, "quarter": 1}.get(str(_raw).strip().lower(), _fixed)
        return min(_fixed, _cut)  # cap can only REDUCE below fixed, never increase

    if _fc4_on and _contracts > 0:
        _contracts = 4  # Michael 2026-07-15
    elif _fc2_on and _contracts > 0:
        _contracts = 2
    elif _fc3_on and _contracts > 0:
        _contracts = 3
    return _contracts



def effective_contracts(setup: Dict[str, Any]) -> int:
    """Sizing decision, then the account's own limit — in that order.

    MARGIN_AWARE_SIZING_V1 (Michael 2026-07-28). The Account Monitor went live
    today and immediately showed the system asking for four contracts
    ($1,104.84 of margin) against $97.68 of available funds. Every such fire is
    rejected by the broker: the signal is consumed, the slot churns, the books
    fill with ORDER_FAILED, and nothing is traded. Sierra's log already held six
    "Insufficient Account Value (NLV) for margin" rejections that morning.

    Wrapping every return path of the sizing logic guarantees the cap cannot be
    bypassed by whichever branch produced the number. It can only REDUCE — a
    smaller real trade instead of a guaranteed rejection — and when the account
    data is missing or stale it changes nothing rather than guessing (Rule 1).
    """
    n = _effective_contracts_raw(setup)
    if n <= 0:
        return n
    try:
        from backend.v9.services.margin_sizing import cap_contracts, cap_to_bracketable
        # Protection first: a contract the DLL cannot bracket must never be sent.
        # This cap is unconditional — it is not behind MARGIN_AWARE_SIZING_V1,
        # because an unprotected contract is a safety defect, not a sizing policy.
        allowed, why = cap_to_bracketable(n)
        if allowed != n:
            logger.warning("[SierraCmd] BRACKET-SLOT CAP %d → %d — %s", n, allowed, why)
            n = allowed
        allowed, why = cap_contracts(n)
    except Exception as e:                       # never block a fire on a bug
        logger.warning("[SierraCmd] margin sizing errored (size unchanged): %s", e)
        return n
    if allowed != n:
        logger.warning("[SierraCmd] MARGIN SIZING %d → %d — %s", n, allowed, why)
    return allowed

def _zlr_mgmt_enabled() -> bool:
    """ZLR_MGMT_V1 (Michael 2026-07-14) — default OFF, no env var needed for the
    code default. When unset the ZLR bracket/allocation is byte-identical to every
    other pattern. Enabling is Michael's call (trading-risk-surface change)."""
    return os.getenv("ZLR_MGMT_V1", "0").strip().lower() in ("1", "true", "yes")


def _is_zlr_setup(setup: Dict[str, Any]) -> bool:
    """True ONLY for a System-4 (woodies) ZLR setup.

    woodies_system stamps the fire with classification == metadata.pattern ==
    pattern_id == "ZLR" (woodies_system.py) and firing_system == 4; accept_setup
    then carries trigger == "ZLR" as well. No other system/pattern uses the "ZLR"
    id (S2 uses REACTIVE_/INITIATIVE_…), so a plain case-insensitive string match
    is unambiguous and scopes the change to ZLR alone."""
    if not isinstance(setup, dict):
        return False
    meta = setup.get("metadata") if isinstance(setup.get("metadata"), dict) else {}
    for _v in (setup.get("classification"), setup.get("trigger"),
               meta.get("pattern"), meta.get("signal")):
        if isinstance(_v, str) and _v.strip().upper() == "ZLR":
            return True
    return False


def command_from_setup(
    setup: Dict[str, Any],
    *,
    trade_id: str,
    account: str,
    mode: str,
) -> Dict[str, Any]:
    direction = (setup.get("direction") or "").upper()
    if direction not in {"LONG", "SHORT"}:
        raise ValueError(f"Unsupported direction for Sierra command: {direction}")
    action = "BUY" if direction == "LONG" else "SELL"
    # L7 (2026-07-08): count comes from effective_contracts — same source accept_setup
    # persists, so the Sierra bracket and the DB row can never disagree.
    _contracts = effective_contracts(setup)
    # K1e (#652, 2026-08-07): a PLACE with contracts<=0 must NEVER reach the
    # wire. The margin cap legitimately returns 0 ("no margin"), but the
    # deployed DLL DEFAULTS contracts<=0 → 3 (MES_AI_DataExport_merged.cpp:2870)
    # — a zero-size command becomes a REAL 3-contract order. The gateway skips
    # the fire upstream when effective contracts <= 0; this raise is the belt
    # at the single choke point every PLACE passes through.
    if _contracts <= 0:
        raise ValueError(
            f"PLACE refused for trade {trade_id}: effective contracts={_contracts} "
            "(margin cap / explicit SKIP) — the fire must be aborted, not sent")

    # Per-contract targets → the DLL PLACE handler (MES_AI_DataExport.cpp) builds
    # three 1-lot OCO groups and reads target_price for C1, context.t2 for C2,
    # context.t3 for C3. Default = the 1/1/1 ladder (C1→T1, C2→T2, C3→T3).
    _c1_target = setup.get("t1") or setup.get("target_price")
    _c2_target = setup.get("t2")
    _c3_target = setup.get("t3")

    # ZLR_MGMT_V1 (Michael 2026-07-14 — ZLR / System-4 ONLY, default OFF): allocate
    # 2 contracts to T1 and 1 to T2, no T3 runner. Each DLL OCO group is a single
    # lot with its OWN target, so 2×T1 + 1×T2 is expressed as the per-contract
    # target sequence [T1, T1, T2]: C1→T1, C2→T1 (was T2), C3→T2 (was T3). When the
    # flag is OFF or the setup is not ZLR this block is skipped → byte-identical
    # 1/1/1 ladder for every other pattern. (Assumes the 3-contract allocation that
    # is the current ruling; with <3 contracts C3 is simply absent DLL-side.)
    if _zlr_mgmt_enabled() and _is_zlr_setup(setup):
        _c2_target = _c1_target       # second contract also exits at T1
        _c3_target = setup.get("t2")  # the lone runner exits at T2 (no T3 runner)

    # T0 (Michael 2026-07-15, with FIXED_CONTRACTS_4): a fast first take at
    # entry ± T0_TARGET_PTS (3.5) for contract 1; the ladder shifts one leg out:
    # C1→T0 · C2→T1 · C3→T2 · C4→T3. Wire contract: target_price=C1(T0),
    # context.t2=C2, context.t3=C3, context.t4=C4 — the DLL builds a 4th 1-lot
    # OCO when t4 is present (>0). With 3 contracts (or T0_TARGET_PTS unset)
    # this block is skipped and t4 is None → byte-identical 3-pair behavior.
    _c4_target = None
    _t0_pts = 0.0
    try:
        _t0_pts = float(os.getenv("T0_TARGET_PTS", "0") or 0)
    except (TypeError, ValueError):
        _t0_pts = 0.0
    if _contracts >= 4 and _t0_pts > 0 and setup.get("entry_price"):
        _e = float(setup["entry_price"])
        _t0 = _e + _t0_pts if direction == "LONG" else _e - _t0_pts
        _t0 = round(round(_t0 / 0.25) * 0.25, 2)
        _c4_target = _c3_target          # old T3 leg → C4 (runner)
        _c3_target = _c2_target          # T2 → C3
        _c2_target = _c1_target          # T1 → C2
        _c1_target = _t0                 # T0 → C1 (fast take)
        setup["t0"] = _t0                # observability + trade record

        # C4_RULING6_V1 (Michael ruling 2026-07-21): resolve t4 per day-type
        # when the old T3 leg (now _c4_target) is None.
        # cursor 09:45 fix of CC ab8e3807: (1) `context` was UNDEFINED here
        # (NameError on every no-T3 fire — the param belongs to
        # write_trade_command); day_type comes from the setup itself.
        # (2) Normal_Variation matched startswith("Normal") and got the
        # opposite-edge branch — Michael's ruling maps Variation to
        # stop-only/trail-with-T3. Normalize the alias FIRST.
        if os.getenv("C4_RULING6_V1", "0").lower() in ("1", "true", "yes") and _c4_target is None:
            _meta = setup.get("metadata") or {}
            _dt = (setup.get("day_type_at_entry")
                   or _meta.get("day_type")
                   or setup.get("day_type")
                   or "")
            _dt = {"Normal_Variation": "Variation"}.get(_dt, _dt)
            if _dt == "Variation":
                pass  # stays None → DLL builds stop-only; C4 trails with T3
            elif _dt.startswith(("Normal", "Neutral")):
                # Opposite edge ("הקצה השני"): VAL for SHORT / VAH for LONG,
                # IB edge as fallback. Missing levels → honest None (stop-only).
                try:
                    _ibh = float(_meta.get("ib_high") or 0) or None
                    _ibl = float(_meta.get("ib_low") or 0) or None
                    _vah = float(_meta.get("vah") or 0) or None
                    _val = float(_meta.get("val") or 0) or None
                    if direction == "SHORT":
                        _c4_target = _val if _val else _ibl
                    else:
                        _c4_target = _vah if _vah else _ibh
                    if _c4_target and _c4_target > 0:
                        _c4_target = round(round(_c4_target / 0.25) * 0.25, 2)
                    else:
                        _c4_target = None
                except (TypeError, ValueError):
                    _c4_target = None
            elif _dt.startswith("Trend"):
                # Trend: t4 = same as T3 (4R). Runner until 15:45 flatten.
                _c4_target = _c3_target  # the shifted C3 (was old T2)
            # unknown/missing day_type: stays None → stop-only (honest)

    return write_trade_command(
        action=action,
        trade_id=trade_id,
        direction=direction,
        price=setup.get("entry_price"),
        contracts=_contracts,
        stop_price=setup.get("stop") or setup.get("stop_price"),
        target_price=_c1_target,
        account=account,
        mode=mode,
        context={
            "firing_system": setup.get("firing_system"),
            "classification": setup.get("classification"),
            "confidence": setup.get("confidence"),
            "t2": _c2_target,
            "t3": _c3_target,
            "t4": _c4_target,  # 4th 1-lot OCO (Michael 07-15); None → 3-pair behavior
            "metadata": setup.get("metadata", {}),
        },
    )

