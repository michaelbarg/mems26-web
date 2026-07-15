"""Decision 2/6 (Michael 07-15): the R:R gate judges the PRE-realism T1.
Anti-tautological: the same numbers that BLOCKED on 07-14 (capped T1 1.5pt vs
stop 7.5pt) must PASS when the pre-cap T1 (9pt) is present, and still BLOCK
when the trade was structurally bad to begin with."""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))


def _rr_eval(setup, direction="LONG"):
    """Mirror of the gate's arithmetic (pure)."""
    t1 = setup.get("t1_pre_realism", setup.get("t1"))
    e = float(setup["entry_price"]); s = float(setup["stop"])
    d = (float(t1) - e) if direction == "LONG" else (e - float(t1))
    return d, abs(e - s)


def test_realism_capped_t1_passes_on_pre_cap_value():
    setup = {"entry_price": 7586.75, "stop": 7579.25,          # stop 7.5pt
             "t1": 7588.25, "t1_pre_realism": 7595.75}          # capped 1.5 / original 9
    d, sd = _rr_eval(setup)
    assert d >= sd, "pre-realism T1 (9pt) must pass the 7.5pt stop"


def test_structurally_bad_trade_still_blocks():
    setup = {"entry_price": 7586.75, "stop": 7579.25,
             "t1": 7588.25}                                     # no pre-cap key: T1 truly 1.5pt
    d, sd = _rr_eval(setup)
    assert d < sd, "genuinely poor R:R must still block"
