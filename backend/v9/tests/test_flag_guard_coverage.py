"""Every key in RULED_FLAGS.yaml must appear in flag_guard output.

T-219 bug: BLOCKED_TWIN_V1 was in RULED but invisible to flag_guard
because the parser only matched double-quoted expected values, and
T-168 converted some to single quotes. Result: a ruled flag drifted
without anyone knowing.
"""
import os
import sys

import pytest

# Navigate from backend/v9/tests/ up to repo root
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)


def test_all_ruled_keys_parsed():
    """Every key under 'ruled:' in RULED_FLAGS.yaml must be returned
    by parse_ruled. If one is missing, the parser has a quoting bug."""
    import re
    from scripts.flag_guard import parse_ruled

    path = os.path.join(ROOT, "config", "RULED_FLAGS.yaml")
    ruled = parse_ruled(path)

    # Also count keys by regex (the ground truth)
    rx = re.compile(r'^\s{2}([A-Z0-9_]+):\s*\{')
    yaml_keys = set()
    in_ruled = False
    for line in open(path, encoding="utf-8"):
        if line.startswith("ruled:"):
            in_ruled = True
            continue
        if not in_ruled:
            continue
        m = rx.match(line)
        if m:
            yaml_keys.add(m.group(1))

    missing = yaml_keys - set(ruled.keys())
    assert not missing, (
        f"flag_guard parser MISSED {len(missing)} ruled key(s): {missing}. "
        f"Parsed {len(ruled)}, YAML has {len(yaml_keys)}. "
        f"Likely a quoting mismatch (single vs double quotes).")


def test_parse_ruled_handles_single_quotes():
    """expected: 'value' (single-quoted) must be parsed correctly."""
    from scripts.flag_guard import parse_ruled

    path = os.path.join(ROOT, "config", "RULED_FLAGS.yaml")
    ruled = parse_ruled(path)

    # BLOCKED_TWIN_V1 uses single quotes
    assert "BLOCKED_TWIN_V1" in ruled, (
        "BLOCKED_TWIN_V1 missing from parsed ruled flags")
    assert ruled["BLOCKED_TWIN_V1"]["expected"] == "shadow", (
        f"BLOCKED_TWIN_V1 expected should be 'shadow', "
        f"got {ruled['BLOCKED_TWIN_V1']['expected']!r}")
