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
  * N4(a) rescue-tier (2026-07-17, ALERT-only): counter-signal fired before T1,
    stuck trade (open >=N bars with barely any favorable progress), reversing
    runner leg after T1. All three are advisory signals computed by the
    caller and passed in — this module stays pure and never recomputes bar
    history. Promoting any of these to an AUTO-executed correction is a
    SEPARATE, flag-gated, sim-verified capability pending Michael's morning
    ruling on the exact tighten-to/flatten thresholds — not built here.

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

# ── central ops log (N12) — GUARDED: a logging failure must NEVER affect the
# supervisor (diagnosis stays pure; only the live scan wrapper logs).
try:
    from scripts.ops_log import log_event
except Exception:  # pragma: no cover
    def log_event(*_a, **_k):  # type: ignore[misc]
        return False

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
    price: Optional[float] = None,
    reconcile_verdict: Optional[str] = None,
    reconcile_mismatch: bool = False,
    expected_contracts: Optional[int] = None,
    now_ct_min: Optional[int] = None,
    eod_cutoff_ct_min: int = 14 * 60 + 15,   # 14:15 CT (item-21)
    cap_mult: float = 1.5,
    hard_cap_pts: float = 25.0,
    # ── N4 rescue-tier ALERT checks (2026-07-17, NIGHT_PROMPT §N4a) — all
    # advisory (ALERT), computed by the caller and passed in as pre-computed
    # signals (mirrors reconcile_mismatch below). Never auto-applied here:
    # promoting any of these to an executed correction is the SEPARATE
    # AUTO-tier (flag-gated, sim-verified, Michael's morning ruling on the
    # exact tighten-to/flatten thresholds — not built yet, by design). ──
    counter_signal_pre_t1: bool = False,
    bars_since_entry: Optional[int] = None,
    progress_pts: Optional[float] = None,
    stuck_bars_threshold: int = 12,
    stuck_progress_frac: float = 0.25,
    runner_reversal: bool = False,
    # T16 — SYSTEM6_REVERSAL_TIGHTEN_V1: CVD-flip + ≥2 adverse closes after T1.
    # Conservative reversal signal computed by caller. Default False = byte-identical.
    cvd_reversal: bool = False,
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
        # 2. stop on the protective side of ENTRY (not current price).
        # An INITIAL protective stop must sit on the loss-protective side of
        # entry — LONG below entry, SHORT above entry — independent of where
        # price has since travelled. The old code referenced CURRENT PRICE,
        # which let a genuinely wrong-side initial stop ESCAPE detection the
        # moment price ran past it (a LONG stop ABOVE entry looked "fine" once
        # price rose above the stop, then fell through to the BE/band branch —
        # a defence-in-depth gap). After T1 a stop AT/beyond entry is the
        # DESIRED profit-lock, governed by the BE-after-T1 check below, so the
        # wrong-side veto is pre-T1 only (the t1_hit gate preserves the
        # profit-locked-stop case). Advisory only — this reports, never executes.
        wrong_side = (not t1_hit) and (
            (d == "LONG" and stop > entry) or (d == "SHORT" and stop < entry)
        )
        if wrong_side:
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

    # 9. N4(a) — counter-signal fired before T1: a fresh opposite-direction
    # pattern firing while this trade is still unproven is the earliest
    # "falling trade" tell (Dalton: don't fight new evidence). Caller detects
    # the opposing fire elsewhere (S2/S4) and passes the bool in.
    if counter_signal_pre_t1 and not t1_hit:
        issues.append(Issue("counter_signal_pre_t1", WARN, ALERT,
                            f"opposite-direction signal fired before {d} trade reached T1 — "
                            f"consider tightening the stop or flattening"))

    # 10. N4(a) — stuck trade: open >= stuck_bars_threshold bars with barely any
    # favorable progress (< stuck_progress_frac of the entry-stop risk) and T1
    # not yet hit. "אם עסקה לא זזה זה סימן" — time decay without progress is
    # itself information. Needs both bars_since_entry AND progress_pts from the
    # caller (silent when either is missing — Rule 1, never guess progress).
    if (not t1_hit and bars_since_entry is not None and progress_pts is not None
            and stop is not None and entry is not None
            and bars_since_entry >= stuck_bars_threshold):
        _risk = abs(entry - stop)
        if _risk > 0 and progress_pts < stuck_progress_frac * _risk:
            issues.append(Issue("stuck_trade", WARN, ALERT,
                                f"{bars_since_entry} bars since entry, progress {progress_pts:.2f}pt "
                                f"< {stuck_progress_frac:.0%} of risk {_risk:.2f}pt — "
                                f"consider tightening the stop"))

    # 11. N4(a) — reversing leg on the runner: after T1, price action turns
    # against the still-open runner contract(s). Caller detects the reversal
    # (e.g. N consecutive adverse closes) and passes the bool in — this
    # function stays pure and doesn't recompute bar-by-bar price action.
    if runner_reversal and t1_hit:
        issues.append(Issue("runner_reversal", WARN, ALERT,
                            f"runner leg reversing after T1 on {d} trade — "
                            f"consider tightening the stop or flattening the runner"))

    # 12. T16 — SYSTEM6_REVERSAL_TIGHTEN_V1: on a significant reversal
    # (CVD-flip + ≥2 closes against the trade, after T1), tighten stop toward
    # entry and bring target closer. NOT op=EXIT (forbidden per CLAUDE.md).
    # Conservative: requires both CVD-flip AND structural close evidence.
    # Caller detects and passes the bool in — this module stays pure.
    # Michael ruling 2026-07-20: default OFF; W1 will decide enabling.
    if (cvd_reversal and t1_hit
            and os.getenv("SYSTEM6_REVERSAL_TIGHTEN_V1", "0").lower() in ("1", "true", "yes")):
        # Tighten stop: move to entry (BE) — the conservative minimum
        _tighten_stop = _be_target(d, entry)
        issues.append(Issue("reversal_tighten_stop", WARN, AUTO,
                            f"CVD reversal after T1 on {d} trade — tightening stop to BE {_tighten_stop}",
                            correction={"op": "MODIFY_STOP", "price": _tighten_stop}))
        # Bring target closer: move the next open target to 50% of its current
        # distance from entry. This reduces exposure without op=EXIT.
        for _tk in ("t2", "t3", "t4"):
            _tv = trade.get(_tk)
            if _tv is not None and _tv > 0:
                _dist = abs(_tv - entry)
                if _dist > 0:
                    _new_tgt = entry + (_dist * 0.5) * (1 if d == "LONG" else -1)
                    issues.append(Issue("reversal_tighten_target", WARN, AUTO,
                                        f"CVD reversal — closer {_tk}: {_tv:.2f} → {_new_tgt:.2f}",
                                        correction={"op": "MODIFY_TARGET", "price": _new_tgt}))
                    break  # only the next open target

    # 13. Invariant-10 — target command reconciliation (FIX #633, 2026-08-05):
    # detect divergence between DB targets and what Sierra was actually sent.
    # The caller passes in the last sierra command context (target prices from
    # the PLACE or most recent MODIFY_TARGET). Any gap > 0.25 ticks → ALERT +
    # correction via MODIFY_TARGET path. Silent when sierra_targets missing
    # (Rule 1 — honest skip when we can't read Sierra's command state).
    _sierra_tgts = trade.get("sierra_targets")
    if isinstance(_sierra_tgts, dict) and entry is not None:
        for _tk in ("t1", "t2", "t3"):
            _db_val = trade.get(_tk)
            _sierra_val = _sierra_tgts.get(_tk)
            if _db_val is not None and _sierra_val is not None:
                if abs(float(_db_val) - float(_sierra_val)) > 0.25:
                    issues.append(Issue(
                        f"target_divergence_{_tk}", WARN, AUTO,
                        f"DB {_tk}={_db_val} != Sierra {_tk}={_sierra_val} "
                        f"(gap {abs(float(_db_val)-float(_sierra_val)):.2f}pt)",
                        correction={"op": "MODIFY_TARGET", "target": _tk,
                                    "price": float(_db_val)}))

    return SupervisorReport(healthy=(len(issues) == 0), issues=issues,
                            reconcile_verdict=reconcile_verdict)


def _enabled() -> bool:
    return os.getenv("SYSTEM6_SUPERVISOR", "0").lower() in ("1", "true", "yes")


def _autocorrect_enabled() -> bool:
    # 07-15 Michael decision 6/6 ("מערכת 6 תתחיל לעבוד", protective tier):
    # value "protective" enables applying the AUTO set — which is by
    # construction the risk-REDUCING set only (stop→BE completion, wrong-side
    # target drop). Everything risky stays ALERT (naked stop, wrong-side stop,
    # width anomalies). "1" kept for the future full tier.
    return os.getenv("SYSTEM6_AUTOCORRECT", "0").lower() in ("1", "true", "yes", "protective")


def scan_active_trade(
    *,
    trade: Optional[Dict],
    atr: float,
    t1_hit: bool = False,
    price: Optional[float] = None,
    reconcile_verdict: Optional[str] = None,
    reconcile_mismatch: bool = False,
    expected_contracts: Optional[int] = None,
    now_ct_min: Optional[int] = None,
    executor: Optional[Callable[[Dict], bool]] = None,
    # N4(a) rescue-tier ALERT signals — all optional, all pass straight through
    # to diagnose_trade; None/False (the defaults) reproduce today's behavior.
    counter_signal_pre_t1: bool = False,
    bars_since_entry: Optional[int] = None,
    progress_pts: Optional[float] = None,
    runner_reversal: bool = False,
    cvd_reversal: bool = False,
) -> Optional[SupervisorReport]:
    """Diagnose the active trade, log loudly, and (if SYSTEM6_AUTOCORRECT and an
    executor is given) apply AUTO corrections. Returns None when disabled or flat.

    `executor(correction) -> bool` applies one correction (MODIFY_STOP /
    DROP_TARGET) against the live position; System 6 never writes to Sierra
    directly — it hands the correction to the injected exec layer."""
    if not _enabled() or not trade:
        return None
    report = diagnose_trade(
        trade=trade, atr=atr, t1_hit=t1_hit, price=price,
        reconcile_verdict=reconcile_verdict,
        reconcile_mismatch=reconcile_mismatch, expected_contracts=expected_contracts,
        now_ct_min=now_ct_min,
        counter_signal_pre_t1=counter_signal_pre_t1, bars_since_entry=bars_since_entry,
        progress_pts=progress_pts, runner_reversal=runner_reversal,
        cvd_reversal=cvd_reversal,
    )
    for iss in report.alerts:
        logger.warning("[System6] %s ALERT: %s", iss.code, iss.detail)
        try:  # N12 central ops log — one line per ALERT issue; never breaks the scan
            log_event("system6", iss.severity, f"{iss.code} ALERT: {iss.detail}")
        except Exception:
            pass
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
