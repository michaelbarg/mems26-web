"""S6 Invariant-10: target command reconciliation (FIX #633).

Detects divergence between DB targets and Sierra command targets.
Gap > 0.25 ticks → ALERT + AUTO correction via MODIFY_TARGET.
"""

import pytest
from backend.v9.systems.system6_supervisor import diagnose_trade


def _trade(direction="LONG", entry=7600.0, stop=7594.0, t1=7606.0,
           t2=7612.0, t3=7620.0, sierra_targets=None):
    d = {"direction": direction, "entry_price": entry, "stop": stop,
         "t1": t1, "t2": t2, "t3": t3}
    if sierra_targets is not None:
        d["sierra_targets"] = sierra_targets
    return d


class TestTargetReconciliation:

    def test_no_divergence_is_healthy(self):
        """When DB == Sierra targets, no issue raised."""
        report = diagnose_trade(
            trade=_trade(sierra_targets={"t1": 7606.0, "t2": 7612.0, "t3": 7620.0}),
            atr=10.0,
        )
        target_issues = [i for i in report.issues if "target_divergence" in i.code]
        assert len(target_issues) == 0

    def test_t2_divergence_detected(self):
        """Trade #633 scenario: DB t2 != Sierra t2 → issue raised."""
        report = diagnose_trade(
            trade=_trade(
                direction="SHORT", entry=7774.5, stop=7785.0,
                t1=7759.5, t2=7757.25, t3=7743.0,
                sierra_targets={"t1": 7759.5, "t2": 7656.0, "t3": 7600.0},
            ),
            atr=10.0,
        )
        target_issues = [i for i in report.issues if "target_divergence" in i.code]
        assert len(target_issues) >= 1, "Should detect t2 divergence"
        t2_issue = [i for i in target_issues if "t2" in i.code]
        assert len(t2_issue) == 1
        assert t2_issue[0].correction["op"] == "MODIFY_TARGET"
        assert t2_issue[0].correction["price"] == 7757.25

    def test_small_gap_ignored(self):
        """Gap < 0.25 ticks should be ignored (rounding noise)."""
        report = diagnose_trade(
            trade=_trade(sierra_targets={"t1": 7606.0, "t2": 7612.1, "t3": 7620.0}),
            atr=10.0,
        )
        target_issues = [i for i in report.issues if "target_divergence" in i.code]
        assert len(target_issues) == 0

    def test_missing_sierra_targets_silent(self):
        """When sierra_targets not provided, no issue raised (Rule 1)."""
        report = diagnose_trade(
            trade=_trade(),
            atr=10.0,
        )
        target_issues = [i for i in report.issues if "target_divergence" in i.code]
        assert len(target_issues) == 0

    def test_all_three_targets_checked(self):
        """All t1/t2/t3 divergences detected independently."""
        report = diagnose_trade(
            trade=_trade(
                t1=7606.0, t2=7612.0, t3=7620.0,
                sierra_targets={"t1": 7600.0, "t2": 7600.0, "t3": 7600.0},
            ),
            atr=10.0,
        )
        target_issues = [i for i in report.issues if "target_divergence" in i.code]
        assert len(target_issues) == 3
