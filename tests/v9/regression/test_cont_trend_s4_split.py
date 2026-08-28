"""cont_trend_filter scope split — S4/Woodies patterns SHADOW, INITIATIVE enforced.

Ruling f4bf481d (Michael, phone 2026-08-28, "לגביי ההחלטות בשלושתם מאושר לפי
ההמלצה", approving proposal 2ג of LIVE_CHANNEL 2026-08-28 04:45):

  On S4/Woodies CONT patterns (ZLR / TLB / TT / GB100) the filter was
  NET-DESTRUCTIVE — on 25-26.08 it killed 47.75pt of winners (ZLR-SHORT
  09:35 MFE-1h 32.75pt, GB100-SHORT 11:55 MFE 15.0pt) to save 10.25pt
  (ZLR-LONG 12:55). It therefore no longer BLOCKS those patterns — it
  SHADOW-logs the would-block for the nightly counterfactual (+ T-114).
  INITIATIVE (S2) keeps the filter (T-93 evidence, 34 sessions), and so do
  BULL_FLAG / BEAR_FLAG / CONFLUENCE_RI_ZLR (the filter's original 06-25
  purpose; not part of the ruling). CONT_TREND_FILTER_FULL_SCOPE=1 is the
  written-ruling rollback that restores full-scope blocking.

Style note: like test_d3_leg_replaces_sustained.py this file tests the pure
scope predicate + pins the gateway source contract (the gateway block is not
importable in isolation); the live-behavior proof is the S4-SHADOW log line
on the next session's would-blocks.

if reverted → RED because: the S4 base-pattern set / rollback flag / shadow
branch disappear from trading_gateway.py and the scope predicate below no
longer matches the ruled behavior.
"""

import inspect
import os
import re

_S4_BASES = ("ZLR", "TLB", "TT", "GB100")


def _s4_shadow(pattern: str, full_scope_flag: bool) -> bool:
    """Pure mirror of the gateway predicate: True ⇒ would-block becomes
    SHADOW (no block); False ⇒ filter blocks as before."""
    base = pattern
    for sfx in ("_LONG", "_SHORT"):
        if base.endswith(sfx):
            base = base[: -len(sfx)]
    return base in _S4_BASES and not full_scope_flag


# ── scope predicate (the ruled table) ─────────────────────────────────────

def test_s4_patterns_are_shadow_not_blocked():
    for pat in ("ZLR", "ZLR_LONG", "ZLR_SHORT", "GB100", "GB100_SHORT",
                "TLB", "TT", "TT_LONG"):
        assert _s4_shadow(pat, full_scope_flag=False), pat


def test_initiative_keeps_the_filter():
    for pat in ("INITIATIVE", "INITIATIVE_LONG", "INITIATIVE_SHORT"):
        assert not _s4_shadow(pat, full_scope_flag=False), pat


def test_flags_and_confluence_keep_the_filter():
    # Not part of the ruling — BULL_FLAG chop fires were the filter's
    # original purpose (06-25); CONFLUENCE carries the ZLR name but is the
    # S2×S4 combined pattern and must not be caught by suffix-stripping.
    for pat in ("BULL_FLAG", "BULL_FLAG_LONG", "BEAR_FLAG_SHORT",
                "CONFLUENCE_RI_ZLR"):
        assert not _s4_shadow(pat, full_scope_flag=False), pat


def test_full_scope_rollback_restores_blocking():
    for pat in ("ZLR_SHORT", "GB100", "TLB_LONG"):
        assert not _s4_shadow(pat, full_scope_flag=True), pat


# ── gateway source contract ───────────────────────────────────────────────

def _gateway_source() -> str:
    import backend.v9.gateway.trading_gateway as tg
    return inspect.getsource(tg)


def test_gateway_has_s4_shadow_branch_inside_cont_trend_block():
    src = _gateway_source()
    # the split lives between the displacement-bypass log and the compass
    seg = src.split("cont-trend-filter DISPLACEMENT BYPASS", 1)[1]
    seg = seg.split("F1 DIRECTION_COMPASS_V1: same single INPUT", 1)[0]
    assert "S4-SHADOW" in seg
    assert "CONT_TREND_FILTER_FULL_SCOPE" in seg
    assert re.search(r'\(\s*"ZLR",\s*"TLB",\s*"TT",\s*"GB100"\s*\)', seg)
    # the shadow branch must come BEFORE (and gate) the block assignment
    assert seg.index("S4-SHADOW") < seg.index('result["blocked_by"] = "cont_trend_filter"')


def test_ruled_flags_carries_the_rollback_flag():
    root = os.path.join(os.path.dirname(__file__), "..", "..", "..")
    p = os.path.join(root, "config", "RULED_FLAGS.yaml")
    text = open(p, encoding="utf-8").read()
    assert "CONT_TREND_FILTER_FULL_SCOPE" in text
    assert "f4bf481d" in text
