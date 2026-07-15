"""Decision 3/6 (Michael 07-15): every setup entering the gateway carries `pattern`.
07-14: producers filled only `classification` → pattern=None on every fire →
t1-overrides/playbook/records silently degraded."""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))


def _normalize(setup):  # mirror of route_setup's entry normalization
    if not setup.get("pattern"):
        p = setup.get("classification") or (setup.get("metadata") or {}).get("pattern")
        if p:
            setup["pattern"] = p
    return setup


def test_classification_fills_pattern():
    s = _normalize({"classification": "REACTIVE_LONG", "direction": "LONG"})
    assert s["pattern"] == "REACTIVE_LONG"


def test_metadata_fallback():
    s = _normalize({"metadata": {"pattern": "ZLR"}, "direction": "LONG"})
    assert s["pattern"] == "ZLR"


def test_existing_pattern_untouched():
    s = _normalize({"pattern": "TLB", "classification": "OTHER"})
    assert s["pattern"] == "TLB"
