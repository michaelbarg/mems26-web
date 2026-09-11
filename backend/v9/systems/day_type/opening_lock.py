"""T-314: Opening type lock + negation (single owner).

Called by BOTH main.py and fwd_harness.py — one definition, not two.
The day_type_machine carries the state attributes; this module is
pure logic + side-effects on the machine object.
"""
import logging
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


def update_opening_lock(
    machine: Any,
    rth_bars: List[dict],
    ib_locked: bool,
    now_iso: str,
) -> None:
    """Run the opening lock + negation check on the current bar.

    Mutates `machine` attrs: _opening_type_locked, _opening_locked_val,
    _opening_locked_dir, _opening_locked_at, _opening_negated,
    _opening_negated_at.

    Args:
        machine: day_type_machine (or any object that carries the attrs).
        rth_bars: list of RTH bar dicts with o/h/l/c/v keys.
        ib_locked: whether IB is locked.
        now_iso: current ET time as ISO string (for timestamps).
    """
    n_rth = len(rth_bars)

    # ── Phase 1: Initial lock ──────────────────────────────────────────
    # Lock at bar 4 (bar 3 close is available as a closed bar).
    # AUCTION_IN/OUT: keep reading until IB lock.
    if n_rth >= 4 and not getattr(machine, "_opening_type_locked", False):
        try:
            from backend.v9.systems.day_type.opening_detector_v2 import (
                detect_opening_type)
            # Use CLOSED bars (exclude developing bar) for detection
            closed = rth_bars[:-1] if len(rth_bars) > 1 else rth_bars
            det_bars = [{"o": b["o"], "h": b["h"], "l": b["l"],
                         "c": b["c"], "v": b.get("v", 0)}
                        for b in closed[:6]]
            result = detect_opening_type(det_bars, rth_bars[0]["o"])
            ot_val = str(result.get("opening_type") or "UNKNOWN")
            ot_dir = result.get("direction")
            if ot_val in ("OPEN_AUCTION_IN", "OPEN_AUCTION_OUT"):
                if ib_locked:
                    machine._opening_type_locked = True
                    machine._opening_locked_val = ot_val
                    machine._opening_locked_dir = ot_dir
                    machine._opening_locked_at = now_iso
                    logger.info("[S1-OPENING] T-314: locked opening=%s dir=%s at IB lock",
                                ot_val, ot_dir)
                # else: keep reading (no lock yet)
            else:
                machine._opening_type_locked = True
                machine._opening_locked_val = ot_val
                machine._opening_locked_dir = ot_dir
                machine._opening_locked_at = now_iso
                logger.info("[S1-OPENING] T-314: locked opening=%s dir=%s at bar %d",
                            ot_val, ot_dir, n_rth)
        except Exception as e:
            logger.warning("[S1-OPENING] T-314: lock failed (continuing): %s", e)

    # ── Phase 2: Negation ──────────────────────────────────────────────
    # ORR/DRIVE: negated when ANY bar close goes beyond the rejected extreme.
    # UP → negated on close < rej_low (reversal failed, market resumes down).
    # DOWN → negated on close > rej_high (reversal failed, market resumes up).
    if getattr(machine, "_opening_type_locked", False):
        ot_locked = getattr(machine, "_opening_locked_val", "")
        if (ot_locked in ("OPEN_REJECTION_REVERSE", "OPEN_DRIVE", "OPEN_TEST_DRIVE")
                and not getattr(machine, "_opening_negated", False)
                and n_rth >= 4):
            try:
                neg_closes = [b["c"] for b in rth_bars[3:]]
                open_bars = rth_bars[:3]
                rej_high = max(b["h"] for b in open_bars)
                rej_low = min(b["l"] for b in open_bars)
                ot_dir = getattr(machine, "_opening_locked_dir", None)
                negated = False
                if ot_dir in ("UP", "LONG"):
                    if any(c < rej_low for c in neg_closes):
                        negated = True
                elif ot_dir in ("DOWN", "SHORT"):
                    if any(c > rej_high for c in neg_closes):
                        negated = True
                if negated:
                    machine._opening_negated = True
                    machine._opening_negated_at = now_iso
                    # Re-read once with closed bars → new lock
                    from backend.v9.systems.day_type.opening_detector_v2 import (
                        detect_opening_type)
                    neg_bars = rth_bars[:-1] if len(rth_bars) > 1 else rth_bars
                    det_bars = [{"o": b["o"], "h": b["h"], "l": b["l"],
                                 "c": b["c"], "v": b.get("v", 0)}
                                for b in neg_bars[:6]]
                    new_result = detect_opening_type(det_bars, rth_bars[0]["o"])
                    machine._opening_locked_val = str(
                        new_result.get("opening_type") or "UNKNOWN")
                    machine._opening_locked_dir = new_result.get("direction")
                    logger.warning(
                        "[S1-OPENING] T-314: NEGATED %s → re-read=%s dir=%s "
                        "(rej_high=%.2f rej_low=%.2f)",
                        ot_locked, machine._opening_locked_val,
                        machine._opening_locked_dir, rej_high, rej_low)
            except Exception as e:
                logger.warning("[S1-OPENING] T-314: negation check failed: %s", e)
