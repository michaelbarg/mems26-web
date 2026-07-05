"""System 6 — Active-Trade Supervisor (Michael 2026-07-05).

"ברגע שיש עסקה פעילה — מערכת שתסרוק, תאבחן שהיא מנוהלת נכון, ותבצע תיקונים."

While a demo/live trade is open, System 6 scans it every cycle and checks the
management invariants that failed us in real incidents:
  * reconcile: gateway slot ↔ DB ↔ Sierra agree (item-20; the I-62 orphan)
  * naked stop: an open position MUST carry a protective stop
  * stop side: stop on the protective side of entry (LONG<entry, SHORT>entry)
  * BE after T1: once T1 is hit the stop must be at break-even or better
  * target side: no t1/t2/t3 on the wrong side of entry (I-61)
  * stop band: |entry−stop| within [0.5×ATR, cap] (not financed, not absurd)
  * T1 worth: T1 distance ≥ the floor ("אם T1 קרוב לכניסה זה לא שווה כלום")
  * size: contracts == expected (FIXED_CONTRACTS_3)
  * EOD: no open position inside the flatten window

Each issue is classified AUTO (safe to auto-correct: move stop to BE, drop a
wrong-side target) or ALERT (needs a human / risky: naked stop, wrong-side stop,
orphan, flatten). Diagnosis is PURE and fully testable; the scan/apply wrappers
gather live state and (only when SYSTEM6_AUTOCORRECT=1) hand AUTO corrections to
an injected executor. Nothing is applied to a live position by default.

Flags: SYSTEM6_SUPERVISOR (scan+report, default OFF) ·
        SYSTEM6_AUTOCORRECT (apply AUTO fixes, default OFF).
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# severities
INFO, WARN, CRITICAL = "INFO", "WARN", "CRITICAL"
# actions
AUTO, ALERT = "AUTO", "ALERT"


@dataclass
class Issue:
    code: str
    severity: str
    action: str
    detail: str
    correction: Optional[Dict] = None   # e.g. {"op": "MODIFY_STOP", "price": 7557.5}


@dataclass
class SupervisorReport:
    healthy: bool
    issues: List[Issue] = field(default_factory=list)
    reconcile_verdict: Optional[str] = None

    @property
    def auto_corrections(self) -> List[Issue]:
        return [i for i in self.issues if i.action == AUTO and i.correction]

    @property
    def alerts(self) -> List[Issue]:
        return [i for i in self.issues if i.action == ALERT]


def _be_target(direction: str, entry: float) -> float:
    return entry  # break-even = entry (buffer handled by SmartBE elsewhere)


def diagnose_trade(
    *,
    trade: Dict,
    atr: float,
    t1_hit: bool = False,
    reconcile_verdict: Optional[str] = None,
    reconcile_mismatch: bool = False,
    expected_contracts: Optional[int] = None,
    now_ct_min: Optional[int] = None,
    eod_cutoff_ct_min: int = 14 * 60 + 15,   # 14:15 CT (item-21)
    cap_mult: float = 1.5,
    hard_cap_pts: float = 25.0,
) -> SupervisorReport:
    """Pure diagnosis of one active trade. `trade` = {direction, entry_price,
    stop, t1, t2, t3, contracts}. Returns a SupervisorReport. Never raises on
    missing optional fields."""
    issues: List[Issue] = []
    d = str(trade.get("direction", "")).upper()
    entry = trade.get("entry_price")
    stop = trade.get("stop")

    # 0. reconcile (item-20) — a source disagreement is CRITICAL
    if reconcile_mismatch:
        issues.append(Issue("reconcile_mismatch", CRITICAL, ALERT,
                            f"position sources disagree ({reconcile_verdict})"))

    if entry is None:
        issues.append(Issue("no_entry", CRITICAL, ALERT, "trade has no entry price"))
        return SupervisorReport(False, issues, reconcile_verdict)

    floor = max(0.5 * atr, 1.0) if atr and atr > 0 else 1.0
    cap = min(cap_mult * atr, hard_cap_pts) if atr and atr > 0 else hard_cap_pts

    # 1. naked stop
    if stop is None or stop <= 0:
        issues.append(Issue("naked_stop", CRITICAL, ALERT,
                            "open position has no protective stop",
                            correction={"op": "MODIFY_STOP", "price": _be_target(d, entry)}))
    else:
        # 2. stop on the protective side
        wrong_side = (d == "LONG" and stop >= entry) or (d == "SHORT" and stop <= entry)
        # (a stop exactly at entry AFTER T1 is BE and fine — handled in rule 3)
        if wrong_side and not (t1_hit and stop == entry):
            issues.append(Issue("stop_wrong_side", CRITICAL, ALERT,
                                f"{d} stop {stop} on the wrong side of entry {entry}"))
        else:
            risk = abs(entry - stop)
            # 3. BE after T1
            if t1_hit:
                at_be = (d == "LONG" and stop >= entry) or (d == "SHORT" and stop <= entry)
                if not at_be:
                    issues.append(Issue("stop_not_at_be", WARN, AUTO,
                                        f"T1 hit but stop {stop} not at BE ({entry})",
                                        correction={"op": "MODIFY_STOP", "price": _be_target(d, entry)}))
            else:
                # 4. stop band (pre-T1 only; post-BE the risk is ~0 by design)
                if risk < floor - 1e-9:
                    issues.append(Issue("stop_too_tight", WARN, ALERT,
                                        f"risk {risk:.2f}pt < floor {floor:.2f}pt (financed stop)"))
                elif risk > cap + 1e-9:
                    issues.append(Issue("stop_too_wide", WARN, ALERT,
                                        f"risk {risk:.2f}pt > cap {cap:.2f}pt"))

    # 5. targets on the correct side (I-61)
    for k in ("t1", "t2", "t3"):
        tv = trade.get(k)
        if tv is None:
            continue
        bad = (d == "LONG" and tv <= entry) or (d == "SHORT" and tv >= entry)
        if bad:
            issues.append(Issue(f"{k}_wrong_side", WARN, AUTO,
                                f"{k}={tv} on the wrong side of {d} entry {entry}",
                                correction={"op": "DROP_TARGET", "target": k}))

    # 6. T1 worth ("if T1 is close to entry it's worthless")
    t1 = trade.get("t1")
    if t1 is not None and not t1_hit:
        if abs(t1 - entry) < floor - 1e-9:
            issues.append(Issue("t1_too_close", WARN, ALERT,
                                f"T1 distance {abs(t1-entry):.2f}pt < floor {floor:.2f}pt"))

    # 7. contract size
    if expected_contracts is not None and trade.get("contracts") is not None:
        if int(trade["contracts"]) != int(expected_contracts):
            issues.append(Issue("contract_mismatch", WARN, ALERT,
                                f"contracts={trade['contracts']} != expected {expected_contracts}"))

    # 8. EOD open position
    if now_ct_min is not None and now_ct_min >= eod_cutoff_ct_min:
        issues.append(Issue("eod_open_position", WARN, ALERT,
                            f"position open inside the EOD window ({now_ct_min} ≥ {eod_cutoff_ct_min} CT)"))

    return SupervisorReport(healthy=(len(issues) == 0), issues=issues,
                            reconcile_verdict=reconcile_verdict)


def _enabled() -> bool:
    return os.getenv("SYSTEM6_SUPERVISOR", "0").lower() in ("1", "true", "yes")


def _autocorrect_enabled() -> bool:
    return os.getenv("SYSTEM6_AUTOCORRECT", "0").lower() in ("1", "true", "yes")


def scan_active_trade(
    *,
    trade: Optional[Dict],
    atr: float,
    t1_hit: bool = False,
    reconcile_verdict: Optional[str] = None,
    reconcile_mismatch: bool = False,
    expected_contracts: Optional[int] = None,
    now_ct_min: Optional[int] = None,
    executor: Optional[Callable[[Dict], bool]] = None,
) -> Optional[SupervisorReport]:
    """Diagnose the active trade, log loudly, and (if SYSTEM6_AUTOCORRECT and an
    executor is given) apply AUTO corrections. Returns None when disabled or flat.

    `executor(correction) -> bool` applies one correction (MODIFY_STOP /
    DROP_TARGET) against the live position; System 6 never writes to Sierra
    directly — it hands the correction to the injected exec layer."""
    if not _enabled() or not trade:
        return None
    report = diagnose_trade(
        trade=trade, atr=atr, t1_hit=t1_hit, reconcile_verdict=reconcile_verdict,
        reconcile_mismatch=reconcile_mismatch, expected_contracts=expected_contracts,
        now_ct_min=now_ct_min,
    )
    for iss in report.alerts:
        logger.warning("[System6] %s ALERT: %s", iss.code, iss.detail)
    if report.healthy:
        logger.info("[System6] active trade healthy")
        return report
    if _autocorrect_enabled() and executor is not None:
        for iss in report.auto_corrections:
            try:
                ok = executor(iss.correction)
                logger.warning("[System6] AUTO-CORRECT %s → %s (%s)",
                               iss.code, "applied" if ok else "rejected", iss.correction)
            except Exception as e:
                logger.warning("[System6] AUTO-CORRECT %s errored: %s", iss.code, e)
    elif report.auto_corrections:
        logger.warning("[System6] %d auto-correction(s) recommended (SYSTEM6_AUTOCORRECT off): %s",
                       len(report.auto_corrections),
                       [i.code for i in report.auto_corrections])
    return report
