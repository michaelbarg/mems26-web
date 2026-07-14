"""SIZE_CAP_OVER_FIXED_V1 — a SIZE_CAP_CUT_V1 downward cut must survive the
effective_contracts() FIXED_CONTRACTS_* choke point (Michael ruling 2026-07-09:
the judgment size-cut "still overrides downward, even under FIXED_CONTRACTS").

Bug (audit-confirmed): effective_contracts() re-forces the count to 2/3 whenever
it is >0, which CLOBBERS a cut already baked into the setup — S4/woodies collapses
a wide-stop cut to metadata.sizing="half" (→2), S2/five_min passes a numeric
sizing_contracts, and both get re-forced to 3. A wide-stop trade that should carry
1-2 contracts then ships full 3-contract risk.

Anti-tautological: every ON assertion below returns 3 on the pre-fix code (which
force-3s any >0 setup) and only passes once min(fixed, cut) is honored; the OFF
tests fail if the new flag path leaks into the default. Runnable standalone:
`python3 backend/v9/tests/test_size_cap_over_fixed.py`.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from backend.v9.services.sierra_command import effective_contracts  # noqa: E402

# Flags this module toggles — snapshot + restore so nothing leaks between cases
# or into sibling test modules (test_l7_two_contract_symmetry, test_size_cap_cut).
_FLAGS = ("FIXED_CONTRACTS_2", "FIXED_CONTRACTS_3", "SIZE_CAP_OVER_FIXED_V1")


def _ec(setup, **env):
    """Call effective_contracts under an explicit, isolated flag environment."""
    saved = {k: os.environ.get(k) for k in _FLAGS}
    for k in _FLAGS:
        os.environ.pop(k, None)
    os.environ.update(env)
    try:
        return effective_contracts(setup)
    finally:
        for k in _FLAGS:
            os.environ.pop(k, None)
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v


# ── (a) flag OFF → current behavior preserved (force 3) ──────────────────────
def test_flag_off_preserves_force_three():
    # woodies collapses a wide-stop cut to metadata.sizing="half" (→2). With the
    # flag OFF the historic choke point still re-forces 3 — unchanged.
    assert _ec({"metadata": {"sizing": "half"}}, FIXED_CONTRACTS_3="1") == 3
    assert _ec({"contracts": 2}, FIXED_CONTRACTS_3="1") == 3
    assert _ec({"metadata": {"sizing": 2}}, FIXED_CONTRACTS_3="1") == 3  # S2 numeric cut
    # FIXED_CONTRACTS_2 path unchanged too.
    assert _ec({"contracts": 3}, FIXED_CONTRACTS_2="1") == 2
    # No fixed flag at all → legacy parse is byte-identical to today.
    assert _ec({"contracts": 2}) == 2
    assert _ec({"size": "half"}) == 2
    assert _ec({}) == 1  # unknown → floor 1


def test_flag_off_bug_is_reproduced():
    # Prove the clobber exists in the default (OFF) path: the honest cut-to-2 is
    # forced back to full 3-contract risk. This is the bug the flag fixes.
    assert _ec({"metadata": {"sizing": "half"}}, FIXED_CONTRACTS_3="1") == 3


# ── (b) flag ON → honor the downward cut ─────────────────────────────────────
def test_flag_on_honors_cut_to_two():
    on = {"SIZE_CAP_OVER_FIXED_V1": "1", "FIXED_CONTRACTS_3": "1"}
    assert _ec({"contracts": 2}, **on) == 2                    # numeric cut
    assert _ec({"metadata": {"sizing": "half"}}, **on) == 2    # woodies string cut
    assert _ec({"metadata": {"sizing": 2}}, **on) == 2         # S2 numeric cut
    assert _ec({"size": "half"}, **on) == 2


def test_flag_on_honors_cut_to_one():
    on = {"SIZE_CAP_OVER_FIXED_V1": "1", "FIXED_CONTRACTS_3": "1"}
    assert _ec({"contracts": 1}, **on) == 1
    assert _ec({"metadata": {"sizing": 1}}, **on) == 1
    assert _ec({"metadata": {"sizing": "quarter"}}, **on) == 1


def test_flag_on_no_cut_keeps_fixed_three():
    on = {"SIZE_CAP_OVER_FIXED_V1": "1", "FIXED_CONTRACTS_3": "1"}
    assert _ec({"contracts": 3}, **on) == 3
    assert _ec({"metadata": {"sizing": "full"}}, **on) == 3
    assert _ec({"metadata": {"sizing": 3}}, **on) == 3
    # A *missing* sizing field is "no cut info" → keep fixed, NOT a cut to floor-1.
    assert _ec({}, **on) == 3


def test_flag_on_preserves_full_skip_zero():
    on = {"SIZE_CAP_OVER_FIXED_V1": "1", "FIXED_CONTRACTS_3": "1"}
    assert _ec({"contracts": 0}, **on) == 0
    assert _ec({"metadata": {"sizing": 0}}, **on) == 0        # real S2 SKIP encoding
    assert _ec({"metadata": {"sizing": "reject"}}, **on) == 0  # real S4 SKIP encoding
    assert _ec({"size": "skip"}, **on) == 0


# ── (c) flag ON never INCREASES above the fixed value ────────────────────────
def test_flag_on_never_increases_above_fixed():
    # A setup asking for MORE than the fixed cap is still capped AT the fixed
    # count — the flag only ever reduces.
    assert _ec({"contracts": 5}, SIZE_CAP_OVER_FIXED_V1="1", FIXED_CONTRACTS_3="1") == 3
    assert _ec({"contracts": 3}, SIZE_CAP_OVER_FIXED_V1="1", FIXED_CONTRACTS_2="1") == 2
    assert _ec({"metadata": {"sizing": "full"}},
               SIZE_CAP_OVER_FIXED_V1="1", FIXED_CONTRACTS_2="1") == 2
    # FIXED_CONTRACTS_2 precedence preserved; a cut below the 2-cap still honored.
    assert _ec({"contracts": 1}, SIZE_CAP_OVER_FIXED_V1="1",
               FIXED_CONTRACTS_2="1", FIXED_CONTRACTS_3="1") == 1
    # Sweep: for every requested size the result never exceeds the fixed cap.
    for req in range(0, 6):
        for fixed_flag, cap in (("FIXED_CONTRACTS_2", 2), ("FIXED_CONTRACTS_3", 3)):
            got = _ec({"contracts": req}, SIZE_CAP_OVER_FIXED_V1="1", **{fixed_flag: "1"})
            assert 0 <= got <= cap, (req, fixed_flag, got)


def test_flag_flips_the_clobbered_cut():
    # The money test: OFF clobbers to 3, ON honors the cut to 2 — same setup.
    cut = {"metadata": {"sizing": "half"}}  # woodies wide-stop cut → 2
    assert _ec(cut, FIXED_CONTRACTS_3="1") == 3
    assert _ec(cut, FIXED_CONTRACTS_3="1", SIZE_CAP_OVER_FIXED_V1="1") == 2


if __name__ == "__main__":
    _tests = [v for k, v in sorted(globals().items())
              if k.startswith("test_") and callable(v)]
    _failed = 0
    for _t in _tests:
        try:
            _t()
            print(f"  ok   - {_t.__name__}")
        except Exception as e:  # noqa: BLE001
            _failed += 1
            print(f"  FAIL - {_t.__name__}: {e!r}")
    print(f"\ntest_size_cap_over_fixed.py: {len(_tests) - _failed}/{len(_tests)} passed")
    sys.exit(1 if _failed else 0)
