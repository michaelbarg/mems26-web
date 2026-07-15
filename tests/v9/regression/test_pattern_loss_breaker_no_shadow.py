"""07-15 21:00 (Michael: "למה אין עסקאות לא בדמו ולא בלייב — לתקן מייד").

PATTERN_LOSS_BREAKER counted SHADOW losses → 2 shadow-ZLR losses killed ZLR for
the whole session on both machines (same shadow-noise poisoning as SSV, decision
1/6 — this pipe was missed). Pin: the breaker query must exclude shadow mode.
Source-pin test: guards against an accidental revert of the mode filter.
"""
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[3] / "backend/v9/systems/woodies/woodies_system.py"


def test_loss_breaker_query_excludes_shadow():
    src = SRC.read_text(encoding="utf-8")
    m = re.search(
        r"PATTERN_LOSS_BREAKER.*?_lb_losses = _lb_rs\((.*?)\{\"pid\"", src, re.S)
    assert m, "loss-breaker query not found"
    q = m.group(1)
    assert "pnl_usd < 0" in q
    assert "mode != 'shadow'" in q, "breaker must count REAL (demo/live) losses only"
