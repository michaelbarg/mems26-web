"""T-619: a circumstance ruling becomes a tree variant — copy-on-write on the exact path, verified by walking."""
import importlib.util
import pathlib

from backend.v9.services.decision_tree import walk

ROOT = pathlib.Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location("tree_rule_variant", ROOT / "scripts" / "tree_rule_variant.py")
trv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(trv)


def _tree():
    shared = {"split": "pattern", "branches": {"TOUCH2": {"leaf": "TAKE"}, "*": {"leaf": "TAKE", "id": "take_any"}}}
    return {"split": "phase", "branches": {
        "B": {"split": "day_type", "branches": {"Variation": shared, "*": {"leaf": "SKIP", "id": "stand_down"}}},
        "C": {"split": "day_type", "branches": {"Variation": shared, "*": {"leaf": "SKIP", "id": "stand_down"}}},
        "*": {"leaf": "SKIP", "id": "stand_down"}}}


VEC = {"phase": "C", "day_type": "Variation", "pattern": "TOUCH2", "zone": "mid_value", "direction": "LONG"}


def test_skip_only_on_its_path_and_value():
    root = _tree()
    leaf_id = walk(root, VEC)[0]["id"]
    rule = dict(id="abc", leaf=leaf_id, kind="split", feature="zone", value="mid_value", decision="skip", vec0=VEC)
    new, st = trv.apply_rule(root, rule)
    assert st == "applied"
    assert walk(new, VEC)[0]["id"] == "rule_abc"
    assert walk(new, dict(VEC, zone="near_val"))[0]["id"] == leaf_id          # outside the value ⇒ the old leaf
    assert walk(new, dict(VEC, phase="B"))[0]["leaf"] == "TAKE"               # the shared subtree under B is untouched
    assert walk(root, VEC)[0]["leaf"] == "TAKE"                               # the base tree object is not mutated


def test_edge_only_keeps_the_edges():
    root = _tree()
    rule = dict(id="e1", leaf=walk(root, VEC)[0]["id"], kind="leaf", feature=None, value=None, decision="edge_only", vec0=VEC)
    new, st = trv.apply_rule(root, rule)
    assert st == "applied"
    assert walk(new, dict(VEC, zone="near_val"))[0]["leaf"] == "TAKE"
    assert walk(new, dict(VEC, zone="below_value"))[0]["leaf"] == "TAKE"
    assert walk(new, dict(VEC, zone="mid_value"))[0]["id"] == "rule_e1"
    assert walk(new, dict(VEC, direction="SHORT", zone="near_vah"))[0]["leaf"] == "TAKE"
    assert walk(new, dict(VEC, direction="SHORT", zone="near_val"))[0]["id"] == "rule_e1"


def test_a_moved_leaf_is_not_touched():
    root = _tree()
    rule = dict(id="x", leaf="some_other_leaf", kind="leaf", feature=None, value=None, decision="skip", vec0=VEC)
    new, st = trv.apply_rule(root, rule)
    assert st.startswith("SKIPPED") and new is root


def test_skip_leaf_is_not_ruled():
    root = _tree()
    v = dict(VEC, phase="A")
    rule = dict(id="y", leaf=walk(root, v)[0]["id"], kind="leaf", feature=None, value=None, decision="skip", vec0=v)
    new, st = trv.apply_rule(root, rule)
    assert st.startswith("SKIPPED") and new is root
