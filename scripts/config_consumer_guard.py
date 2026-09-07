#!/usr/bin/env python3
"""§9א config_consumer_guard — every YAML config field must have ≥1 consumer.

Same shape as flag_guard liveness: for each field in daytype_playbook.yaml,
targets.yaml, and stop_anchors.yaml, grep backend/ for at least one read-site.
Fields that exist in config but are never read are dead weight — they create
the illusion of control without affecting behavior.

    python3 scripts/config_consumer_guard.py

Exit 0 = PASS.  Exit 1 = fields found with no consumer.
"""
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"

YAML_FILES = [
    ROOT / "config" / "daytype_playbook.yaml",
    ROOT / "config" / "targets.yaml",
    ROOT / "config" / "stop_anchors.yaml",
]

# Fields that are documentation-only (note, cells) or structural (the pattern/
# day-type keys themselves) — not expected to have a code consumer.
EXEMPT = {"note", "cells"}


def load_fields(yaml_path: Path) -> set:
    """Return all leaf-level field names from the YAML config."""
    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    fields = set()

    def _walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                fields.add(k)
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(data)
    return fields - EXEMPT


def has_consumer(field: str) -> bool:
    """Check if 'field' appears as a string key read in backend/ code."""
    # Search for the field name in Python files under backend/
    # Patterns: .get("field"), ["field"], .field (attribute access)
    try:
        result = subprocess.run(
            ["grep", "-rn", "--include=*.py", field, str(BACKEND)],
            capture_output=True, text=True, timeout=10,
        )
        # Filter for actual read-sites (not just the YAML itself)
        for line in result.stdout.splitlines():
            # Skip config/ references, tests, comments
            if "/config/" in line or "test_" in line:
                continue
            if f'"{field}"' in line or f"'{field}'" in line or f".{field}" in line:
                return True
    except Exception:
        pass
    return False


def main():
    missing = []
    all_fields = set()

    for yf in YAML_FILES:
        if not yf.exists():
            print(f"⚠️  {yf.name} not found — skipped")
            continue
        fields = load_fields(yf)
        all_fields |= fields
        for f in sorted(fields):
            if not has_consumer(f):
                missing.append((yf.name, f))

    if missing:
        print(f"🔴 CONFIG_CONSUMER_GUARD: {len(missing)} fields with NO consumer:\n")
        for yf_name, field in missing:
            print(f"  {yf_name}: {field}")
        print(f"\n  Total fields checked: {len(all_fields)}")
        sys.exit(1)
    else:
        print(f"✅ CONFIG_CONSUMER_GUARD: all {len(all_fields)} fields have ≥1 consumer")
        sys.exit(0)


if __name__ == "__main__":
    main()
