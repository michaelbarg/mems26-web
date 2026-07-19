#!/usr/bin/env python3
"""Stage E: replay real RTH setups through read-only, pure readiness gates.

No gateway method is called and no state is mutated. Historical trade rows are
the setup source; replay bars/levels provide point-in-time market context.

Exit codes: 0=GO, 1=NO-GO, 2=INDETERMINATE.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any, Callable, Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts.flag_guard import parse_env  # noqa: E402

for _key, _value in parse_env(os.path.join(ROOT, ".env")).items():
    os.environ.setdefault(_key, _value)

ET = ZoneInfo("America/New_York")
RTH_START = time(9, 30)
RTH_END = time(16, 0)
API_BASE = os.getenv("MEMS26_API_URL", "http://127.0.0.1:8000").rstrip("/")


def _on(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes"}


def _dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value), tz=ZoneInfo("UTC"))
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=ZoneInfo("UTC")) if parsed.tzinfo is None else parsed
    except (TypeError, ValueError):
        return None


def _epoch(row: Dict[str, Any]) -> Optional[float]:
    if row.get("ts_unix") is not None:
        try:
            return float(row["ts_unix"])
        except (TypeError, ValueError):
            pass
    parsed = _dt(row.get("ts"))
    return parsed.timestamp() if parsed else None


def _api_json(path: str, timeout: int = 12) -> Any:
    headers = {}
    token = os.getenv("BRIDGE_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{API_BASE}{path}", headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


@dataclass(frozen=True)
class GateVerdict:
    gate: str
    status: str  # PASS | BLOCK | OFF | NOT_EVALUATED
    detail: str
    required: bool = True


@dataclass
class SetupVerdict:
    setup: Dict[str, Any]
    gates: List[GateVerdict] = field(default_factory=list)
    would_fire: bool = False
    blocked_by: Optional[str] = None
    unresolved_by: Optional[str] = None


@dataclass
class ReadinessResult:
    status: str  # GO | NO-GO | INDETERMINATE
    setups: List[SetupVerdict]
    reason: str

    @property
    def exit_code(self) -> int:
        return {"GO": 0, "NO-GO": 1, "INDETERMINATE": 2}[self.status]


def _normalise_pattern(pattern: Any) -> str:
    p = str(pattern or "").upper().strip()
    for suffix in ("_LONG", "_SHORT"):
        if p.endswith(suffix):
            p = p[: -len(suffix)]
    aliases = {
        "BEAR_FLAG": "FLAGS",
        "BULL_FLAG": "FLAGS",
        "FLAG": "FLAGS",
        "S2_REACTIVE": "REACTIVE",
        "S2_INITIATIVE": "INITIATIVE",
    }
    return aliases.get(p, p)


def _bars_before(rows: Iterable[Dict[str, Any]], entry_ts: Any) -> List[Dict[str, Any]]:
    entry = _dt(entry_ts)
    if entry is None:
        return []
    cutoff = entry.timestamp()
    out = []
    for row in rows:
        ts = _epoch(row)
        if ts is not None and ts <= cutoff:
            out.append(row)
    return sorted(out, key=lambda row: _epoch(row) or 0)


def _playbook_gate(setup: Dict[str, Any]) -> GateVerdict:
    from backend.v9.systems.daytype_playbook import decide

    decision = decide(
        pattern=setup.get("pattern_id"),
        day_type=setup.get("day_type"),
        direction=setup.get("direction"),
        trend_state=setup.get("woodies_trend"),
        max_contracts=4,
    )
    return GateVerdict(
        "daytype_playbook",
        "PASS" if decision.allow else "BLOCK",
        decision.reason,
    )


def _historical_daytype_gate(setup: Dict[str, Any], no_live: bool) -> GateVerdict:
    # get_live_day_type() reads today's app.state. Calling it for yesterday would
    # silently substitute current state for historical truth. The stamped value
    # is still used by the pure downstream gates.
    stamped = setup.get("day_type")
    detail = (
        "not-evaluated (historical replay cannot call today's app.state"
        f"; stamped day_type={stamped or 'missing'})"
    )
    if no_live:
        detail += " [--no-live]"
    return GateVerdict("get_live_day_type", "NOT_EVALUATED", detail, required=False)


def _position_gate(setup: Dict[str, Any], levels: Dict[str, Any]) -> GateVerdict:
    if not _on("DAYTYPE_POSITION_GATE"):
        return GateVerdict("daytype_position_gate", "OFF", "DAYTYPE_POSITION_GATE=0")

    # Replay exposes only the final session snapshot. It is valid for direction
    # checks only when the gate is OFF; using it at an earlier entry would be
    # look-ahead. Refuse to fake a point-in-time TPO snapshot.
    return GateVerdict(
        "daytype_position_gate",
        "NOT_EVALUATED",
        "not-evaluated (chart replay exposes final-day levels, not entry-time TPO)",
    )


def _direction_gates(
    setup: Dict[str, Any],
    replay_bars: List[Dict[str, Any]],
    woodies_bars: List[Dict[str, Any]],
    levels: Dict[str, Any],
) -> List[GateVerdict]:
    from backend.v9.systems.daytype_position_gate import _pattern_family

    pattern = setup.get("pattern_id") or ""
    family = _pattern_family(pattern)
    want = "UP" if str(setup.get("direction")).upper() == "LONG" else "DOWN"
    upto_replay = _bars_before(replay_bars, setup.get("entry_ts"))
    upto_woodies = _bars_before(woodies_bars, setup.get("entry_ts"))
    k = max(2, int(os.getenv("LSMA_SUSTAIN_BARS", "3") or "3"))
    lsma_rows = [
        {
            "close": row.get("close", row.get("c")),
            "lsma_value": row.get("lsma_value"),
            "trend_state": row.get("trend_state", row.get("trend")),
        }
        for row in reversed(upto_woodies)
        if row.get("lsma_value") is not None
        and row.get("close", row.get("c")) is not None
    ]
    verdicts: List[GateVerdict] = []

    if not _on("CONT_TREND_FILTER"):
        verdicts.append(GateVerdict("cont_trend_filter", "OFF", "CONT_TREND_FILTER=0"))
    elif family != "CONT":
        verdicts.append(GateVerdict("cont_trend_filter", "PASS", f"family={family or 'unknown'} exempt"))
    elif len(lsma_rows) < k:
        verdicts.append(GateVerdict(
            "cont_trend_filter",
            "NOT_EVALUATED",
            f"not-evaluated (need {k} entry-time LSMA bars; found {len(lsma_rows)})",
        ))
    else:
        from backend.v9.systems.direction_context_live import sustained_lsma_side

        sustained = sustained_lsma_side(lsma_rows, k)
        verdicts.append(GateVerdict(
            "cont_trend_filter",
            "PASS" if sustained == want else "BLOCK",
            f"setup={want} dir_sustained={sustained} k={k}",
        ))

    if not _on("DIRECTION_CONTEXT"):
        verdicts.append(GateVerdict("direction_context", "OFF", "DIRECTION_CONTEXT=0"))
        return verdicts

    if not upto_replay:
        verdicts.append(GateVerdict(
            "direction_context",
            "NOT_EVALUATED",
            "not-evaluated (no replay bars at entry)",
        ))
        return verdicts

    lsma_veto = _on("DIRECTION_LSMA_VETO")
    if lsma_veto and not lsma_rows:
        verdicts.append(GateVerdict(
            "direction_lsma_veto",
            "NOT_EVALUATED",
            "not-evaluated (entry-time lsma_value unavailable)",
        ))
        return verdicts

    from backend.v9.systems.direction_context import compute_direction

    market_bars = [
        {
            "high": row.get("h", row.get("high")),
            "low": row.get("l", row.get("low")),
            "close": row.get("c", row.get("close")),
            "cumulative_delta": row.get("cum_delta"),
        }
        for row in upto_replay
        if row.get("h", row.get("high")) is not None
        and row.get("l", row.get("low")) is not None
        and row.get("c", row.get("close")) is not None
    ]
    lsma_side = None
    if lsma_veto:
        latest = lsma_rows[0]
        lsma_side = 1 if float(latest["close"]) > float(latest["lsma_value"]) else -1
    direction = compute_direction(
        bars=market_bars,
        ib_high=levels.get("ib_high"),
        ib_low=levels.get("ib_low"),
        poc=levels.get("poc"),
        day_type=setup.get("day_type"),
        lsma_side=lsma_side,
        lsma_veto=lsma_veto,
    )
    actual = direction.get("dir")
    exempt = (
        _on("NEUTRAL_RESPONSIVE_V1")
        and family == "REV"
        and str(setup.get("day_type") or "").startswith(
            ("Neutral", "Variation", "Normal_Variation", "Normal")
        )
    )
    allowed = actual not in {"UP", "DOWN"} or actual == want or exempt
    gate_name = "direction_lsma_veto" if lsma_veto else "direction_context"
    verdicts.append(GateVerdict(
        gate_name,
        "PASS" if allowed else "BLOCK",
        f"setup={want} context={actual}; {direction.get('reason')}"
        + ("; responsive exemption" if exempt and actual != want else ""),
    ))
    return verdicts


def _entry_confirm_gate(setup: Dict[str, Any], replay_bars: List[Dict[str, Any]]) -> GateVerdict:
    if not _on("S4_ENTRY_CONFIRM_V1"):
        return GateVerdict("entry_confirm", "OFF", "S4_ENTRY_CONFIRM_V1=0")
    rows = _bars_before(replay_bars, setup.get("entry_ts"))
    if not rows:
        return GateVerdict(
            "entry_confirm",
            "NOT_EVALUATED",
            "not-evaluated (no signal bar at entry)",
        )
    latest = rows[-1]
    prior = rows[-15:-1]
    ranges = [
        float(row.get("h", row.get("high"))) - float(row.get("l", row.get("low")))
        for row in prior
        if row.get("h", row.get("high")) is not None
        and row.get("l", row.get("low")) is not None
    ]
    frac = float(os.getenv("ENTRY_CONFIRM_TOL_ATR_FRAC", "0.10") or 0)
    floor = float(os.getenv("ENTRY_CONFIRM_TOL_MIN_PTS", "0.5") or 0)
    tolerance = max(frac * (sum(ranges) / len(ranges)), floor) if ranges else floor
    from backend.v9.systems.entry_confirm import entry_confirmed

    allowed, reason = entry_confirmed(
        direction=str(setup.get("direction") or "").upper(),
        bars=[latest],
        tol_points=tolerance,
    )
    return GateVerdict(
        "entry_confirm",
        "PASS" if allowed else "BLOCK",
        f"{reason}; tol={tolerance:.2f}",
    )


def _pre_fire_gate(setup: Dict[str, Any]) -> GateVerdict:
    fields = ("entry_price", "stop", "t1")
    missing = [name for name in fields if setup.get(name) is None]
    if missing:
        return GateVerdict(
            "pre_fire_validator",
            "NOT_EVALUATED",
            f"not-evaluated (missing {','.join(missing)})",
        )
    from backend.v9.shared.pre_fire_validator import FireRequest, validate_fire

    system = "T2_WOODIES" if int(setup.get("system") or 0) == 4 else "T1_NUMBER_BAR"
    try:
        response = validate_fire(FireRequest(
            system_id=system,
            direction=str(setup.get("direction") or "").upper(),
            entry_price=float(setup["entry_price"]),
            stop_price=float(setup["stop"]),
            t1_price=float(setup["t1"]),
            t2_price=float(setup["t2"]) if setup.get("t2") is not None else None,
            time_stop_minutes=90,
            confidence=int(float(setup.get("confidence") or 70)),
        ))
    except Exception as exc:
        return GateVerdict("pre_fire_validator", "BLOCK", f"{type(exc).__name__}: {exc}")
    return GateVerdict(
        "pre_fire_validator",
        "PASS" if response.valid else "BLOCK",
        response.fail_reason or "valid",
    )


def _sizing_gate(_: Dict[str, Any]) -> GateVerdict:
    from backend.v9.services.sierra_command import effective_contracts

    count = int(effective_contracts({"size": "full"}))
    return GateVerdict(
        "effective_contracts",
        "PASS" if count > 0 else "BLOCK",
        f"contracts={count} (count-only; no order path invoked)",
    )


def evaluate_setup(
    setup: Dict[str, Any],
    *,
    replay_bars: List[Dict[str, Any]],
    woodies_bars: List[Dict[str, Any]],
    levels: Dict[str, Any],
    no_live: bool,
) -> SetupVerdict:
    verdict = SetupVerdict(setup=setup)
    gates: List[GateVerdict] = [
        _playbook_gate(setup),
        _historical_daytype_gate(setup, no_live),
        _position_gate(setup, levels),
    ]
    gates.extend(_direction_gates(setup, replay_bars, woodies_bars, levels))
    gates.extend([
        _entry_confirm_gate(setup, replay_bars),
        _pre_fire_gate(setup),
        _sizing_gate(setup),
    ])
    verdict.gates = gates
    blocked = next((gate for gate in gates if gate.status == "BLOCK"), None)
    unresolved = next(
        (gate for gate in gates if gate.status == "NOT_EVALUATED" and gate.required),
        None,
    )
    verdict.blocked_by = blocked.gate if blocked else None
    verdict.unresolved_by = unresolved.gate if unresolved else None
    verdict.would_fire = blocked is None and unresolved is None
    return verdict


def evaluate_readiness(
    setups: List[Dict[str, Any]],
    *,
    replay_bars: Optional[List[Dict[str, Any]]] = None,
    woodies_bars: Optional[List[Dict[str, Any]]] = None,
    levels: Optional[Dict[str, Any]] = None,
    no_live: bool = True,
    evaluator: Callable[..., SetupVerdict] = evaluate_setup,
) -> ReadinessResult:
    if not setups:
        return ReadinessResult(
            "INDETERMINATE",
            [],
            "0 real RTH setups found (never a silent GO)",
        )
    verdicts = [
        evaluator(
            setup,
            replay_bars=replay_bars or [],
            woodies_bars=woodies_bars or [],
            levels=levels or {},
            no_live=no_live,
        )
        for setup in setups
    ]
    if any(item.would_fire for item in verdicts):
        count = sum(item.would_fire for item in verdicts)
        return ReadinessResult("GO", verdicts, f"{count}/{len(verdicts)} real setups would_fire")
    if all(item.blocked_by for item in verdicts):
        return ReadinessResult("NO-GO", verdicts, "all real setups blocked by an evaluated gate")
    return ReadinessResult(
        "INDETERMINATE",
        verdicts,
        "no setup would_fire and at least one active gate could not be evaluated honestly",
    )


def _real_rth_setups(date: str, replay: Dict[str, Any], trades_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    replay_ids = {row.get("id") for row in replay.get("trades", [])}
    details = {
        row.get("id"): row
        for row in trades_payload.get("trades", [])
        if row.get("id") in replay_ids and not row.get("is_synthetic")
    }
    out: List[Dict[str, Any]] = []
    seen = set()
    for replay_trade in replay.get("trades", []):
        row = details.get(replay_trade.get("id"), {})
        entry_ts = row.get("entry_ts") or replay_trade.get("entry_ts")
        entered = _dt(entry_ts)
        if entered is None:
            continue
        entered_et = entered.astimezone(ET)
        if entered_et.date().isoformat() != date or not (RTH_START <= entered_et.time() <= RTH_END):
            continue
        pattern = row.get("pattern_id") or replay_trade.get("pattern")
        direction = row.get("direction") or replay_trade.get("direction")
        entry = row.get("entry_price") or replay_trade.get("entry_price")
        # Shadow/live duplicates are the same detector setup a few seconds apart.
        dedup = (
            entered_et.strftime("%Y-%m-%dT%H:%M"),
            _normalise_pattern(pattern),
            str(direction).upper(),
            round(float(entry), 2) if entry is not None else None,
        )
        if dedup in seen:
            continue
        seen.add(dedup)
        out.append({
            "id": replay_trade.get("id"),
            "entry_ts": entry_ts,
            "system": row.get("system") or replay_trade.get("firing_system"),
            "direction": str(direction or "").upper(),
            "pattern_id": pattern,
            "day_type": row.get("day_type"),
            "entry_price": entry,
            "stop": row.get("stop_initial") or replay_trade.get("stop"),
            "t1": row.get("t1") or replay_trade.get("t1"),
            "t2": row.get("t2") or replay_trade.get("t2"),
            "confidence": row.get("confidence"),
            "woodies_trend": row.get("woodies_trend"),
        })
    return out


def load_inputs(date: str) -> tuple[List[Dict[str, Any]], Dict[str, Any], List[Dict[str, Any]]]:
    replay = _api_json(f"/api/v9/chart/replay?date={date}")
    trades = _api_json("/api/v9/trades?limit=1000")
    # This display endpoint is the only read-only API exposing historical
    # lsma_value. Its limited rolling window is handled honestly per setup.
    try:
        woodies = (_api_json("/api/v9/woodies/chart?limit=200") or {}).get("bars", [])
    except Exception:
        woodies = []
    return _real_rth_setups(date, replay, trades), replay, woodies


def print_result(date: str, result: ReadinessResult) -> None:
    print(f"🔥 FIRE READINESS REAL · stage E · {date}")
    print(f"setups={len(result.setups)} · verdict={result.status} · {result.reason}")
    print()
    if result.setups:
        print("id   time(ET)  pattern               dir    would_fire  blocked_by")
        print("---  --------  --------------------  -----  ----------  ------------------------")
    for item in result.setups:
        setup = item.setup
        entered = _dt(setup.get("entry_ts"))
        shown_time = entered.astimezone(ET).strftime("%H:%M") if entered else "?"
        blocker = item.blocked_by or (
            f"not-evaluated:{item.unresolved_by}" if item.unresolved_by else "—"
        )
        print(
            f"{str(setup.get('id')):<3}  {shown_time:<8}  "
            f"{str(setup.get('pattern_id') or '?')[:20]:<20}  "
            f"{str(setup.get('direction') or '?'):<5}  "
            f"{str(item.would_fire).lower():<10}  {blocker}"
        )
        for gate in item.gates:
            print(f"     · {gate.gate}: {gate.status} — {gate.detail}")
    print()
    icon = {"GO": "🟢", "NO-GO": "🔴", "INDETERMINATE": "🟡"}[result.status]
    print(f"{icon} {result.status} — {result.reason}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="ET RTH date YYYY-MM-DD")
    parser.add_argument(
        "--no-live",
        action="store_true",
        help="do not inspect current app.state (historical read-only APIs still used)",
    )
    args = parser.parse_args(argv)
    try:
        datetime.strptime(args.date, "%Y-%m-%d")
        setups, replay, woodies = load_inputs(args.date)
        result = evaluate_readiness(
            setups,
            replay_bars=replay.get("bars", []),
            woodies_bars=woodies,
            levels=replay.get("levels", {}),
            no_live=args.no_live,
        )
    except Exception as exc:
        result = ReadinessResult(
            "INDETERMINATE",
            [],
            f"input error: {type(exc).__name__}: {exc}",
        )
    print_result(args.date, result)
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
