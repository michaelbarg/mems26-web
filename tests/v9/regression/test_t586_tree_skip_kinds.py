# -*- coding: utf-8 -*-
"""T-586 (18.10) — TREE_SKIP_KINDS kind policy: a TAKE leaf whose candidate kind is listed becomes SKIP; unset ⇒ inert.
Pure function backend.v9.services.decision_tree.kind_policy (the gateway calls it right after the tree walk)."""
import pytest
from backend.v9.services.decision_tree import kind_policy

LEAF = {"leaf": "TAKE", "id": "take_with_hint", "note": "with the hint"}


@pytest.mark.parametrize("env", [None, "", "   ", ","])
def test_unset_or_empty_is_inert(env):
    assert kind_policy("TAKE", LEAF, "REVERSAL", env) == ("TAKE", LEAF)


def test_listed_kind_on_take_leaf_becomes_skip():
    action, leaf = kind_policy("TAKE", LEAF, "REVERSAL", "REVERSAL,EDGE_FADE")
    assert action == "SKIP"
    assert leaf["leaf"] == "SKIP" and leaf["id"] == "kind_policy"
    assert "REVERSAL" in leaf["note"]
    assert LEAF["leaf"] == "TAKE"  # the input leaf is not mutated


def test_unlisted_kind_unchanged():
    assert kind_policy("TAKE", LEAF, "BREAK", "REVERSAL,EDGE_FADE") == ("TAKE", LEAF)
    assert kind_policy("TAKE", LEAF, "WITH_DRIVE", "REVERSAL,EDGE_FADE") == ("TAKE", LEAF)


def test_skip_and_shadow_leaves_untouched():
    skip = {"leaf": "SKIP", "id": "stand_down"}
    assert kind_policy("SKIP", skip, "REVERSAL", "REVERSAL") == ("SKIP", skip)
    shadow = {"leaf": "SHADOW", "id": "sh"}
    assert kind_policy("SHADOW", shadow, "REVERSAL", "REVERSAL") == ("SHADOW", shadow)


def test_case_and_whitespace_tolerant():
    assert kind_policy("TAKE", LEAF, "edge_fade", " reversal , Edge_Fade ")[0] == "SKIP"
    assert kind_policy("take", LEAF, "REVERSAL", "REVERSAL")[0] == "SKIP"


def test_missing_kind_never_skips():
    assert kind_policy("TAKE", LEAF, None, "REVERSAL,EDGE_FADE") == ("TAKE", LEAF)
    assert kind_policy("TAKE", LEAF, "", "REVERSAL,EDGE_FADE") == ("TAKE", LEAF)
