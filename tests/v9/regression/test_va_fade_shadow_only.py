"""VA_FADE_V1 — shadow_only contract (T-161, cowork-night 2026-08-30).

Why this test exists
--------------------
`VA_FADE_V1` was moved from absent-in-.env to `=shadow` so Michael's
"one shadow day, then an evening gate" ruling (30.08 05:37) has something to
measure. The flag's own detector DOES call `gateway.route_setup(...)`, so the
ONLY thing standing between shadow mode and a live order is the hardcoded
`metadata.shadow_only = True` in `build_va_fade_setup` plus the gateway branch
that honours it and returns BEFORE any demo/live routing.

That invariant is load-bearing and was previously asserted nowhere. Mirrors
`tests/v9/regression/test_failed_break.py:89`, which locks the identical
contract for the FAILED_BREAK_VA_V1 precedent.

If either half of this breaks, VA_FADE goes from "measured" to "trading" with
no flag change and no review — exactly the silent-enable class the pre-LIVE
protocol forbids.
"""
import ast
import os

from backend.v9.systems.va_fade import build_va_fade_setup

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

_TRIGGER_SHORT = {
    "type": "VA_FADE_HIGH",
    "direction": "SHORT",
    "entry": 7770.00,
    "stop": 7774.00,
    "vah": 7771.50,
    "val": 7755.50,
    "poc": 7763.50,
    "probe_extreme": 7773.00,
    "target_mid": 7763.50,
}

_TRIGGER_LONG = {
    "type": "VA_FADE_LOW",
    "direction": "LONG",
    "entry": 7757.00,
    "stop": 7753.00,
    "vah": 7771.50,
    "val": 7755.50,
    "poc": 7763.50,
    "probe_extreme": 7754.00,
    "target_mid": 7763.50,
}


def test_short_setup_is_shadow_only():
    setup = build_va_fade_setup(_TRIGGER_SHORT)
    assert setup["metadata"]["shadow_only"] is True


def test_long_setup_is_shadow_only():
    setup = build_va_fade_setup(_TRIGGER_LONG)
    assert setup["metadata"]["shadow_only"] is True


def test_shadow_only_is_unconditional_not_flag_derived():
    """The guard must not depend on the flag value — a future
    `VA_FADE_V1=live` must still be non-trading until a real ruling
    rebuilds the setup builder."""
    for val in ("0", "shadow", "live", "1", "yes"):
        os.environ["VA_FADE_V1"] = val
        try:
            setup = build_va_fade_setup(_TRIGGER_SHORT)
            assert setup["metadata"]["shadow_only"] is True, (
                f"shadow_only collapsed under VA_FADE_V1={val}")
        finally:
            os.environ.pop("VA_FADE_V1", None)


def test_gateway_honours_metadata_shadow_only_before_routing():
    """The consumer half: trading_gateway must read the SAME nested path
    (`setup['metadata']['shadow_only']`) and return before demo/live.

    Asserted on source text rather than by driving the whole gateway,
    because the point is the path + the early return, and a live-routing
    gateway run is not something a regression test should attempt.
    """
    src = open(os.path.join(ROOT, "backend/v9/gateway/trading_gateway.py"),
               encoding="utf-8").read()
    assert '(setup.get("metadata") or {}).get("shadow_only")' in src, (
        "gateway no longer reads the nested metadata.shadow_only path — "
        "VA_FADE/FAILED_BREAK shadow setups would route to demo/live")
    # the branch must return, not merely tag the result
    idx = src.index('(setup.get("metadata") or {}).get("shadow_only")')
    branch = src[idx:idx + 400]
    assert "return result" in branch, (
        "shadow_only branch no longer returns early — routing continues")


def test_builder_module_parses_and_declares_shadow_only_literally():
    """AST guard: shadow_only must be a literal True in the builder, not a
    computed/env-derived expression that could evaluate falsey."""
    path = os.path.join(ROOT, "backend/v9/systems/va_fade.py")
    tree = ast.parse(open(path, encoding="utf-8").read())
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value == "shadow_only":
                    found.append(v)
    assert found, "shadow_only key vanished from va_fade.py"
    for v in found:
        assert isinstance(v, ast.Constant) and v.value is True, (
            "shadow_only is no longer a literal True")
