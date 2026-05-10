#!/usr/bin/env python3
"""MEMS26 V9 — Compliance Coverage Verification.

Parses compliance_manifest.yaml for each system and reports:
- Per-system: total, implemented, partial, missing, drift%
- Per-requirement: status breakdown
- Test file existence verification
"""
import os
import sys
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SYSTEMS = ["day_type", "chart_5min", "tick_reversal", "woodies", "tpo", "killzone"]


def load_manifest(system: str) -> dict:
    path = ROOT / "backend" / "v9" / "systems" / system / "compliance_manifest.yaml"
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f)


def check_test_file(system: str) -> bool:
    path = ROOT / "tests" / "v9" / "compliance" / f"test_{system}_compliance.py"
    return path.exists()


def main():
    print("=" * 70)
    print(" MEMS26 V9 — Compliance Coverage Report")
    print("=" * 70)
    print()

    grand_total = 0
    grand_impl = 0
    grand_partial = 0
    grand_missing = 0

    for sys in SYSTEMS:
        manifest = load_manifest(sys)
        if not manifest:
            print(f"[{sys}] NO MANIFEST FOUND")
            print()
            continue

        summary = manifest.get("summary", {})
        total = summary.get("total_requirements", 0)
        impl = summary.get("implemented", 0)
        partial = summary.get("partial", 0)
        missing = summary.get("missing", 0)
        drift = summary.get("drift_pct", 0)
        has_test = check_test_file(sys)

        grand_total += total
        grand_impl += impl
        grand_partial += partial
        grand_missing += missing

        print(f"System {manifest.get('system_id', '?')}: {sys}")
        print(f"  Spec: {manifest.get('spec_title', 'N/A')}")
        print(f"  Total requirements: {total}")
        print(f"  Implemented:        {impl}")
        print(f"  Partial:            {partial}")
        print(f"  Missing:            {missing}")
        print(f"  Drift:              {drift}%")
        print(f"  Test file:          {'OK' if has_test else 'MISSING'}")

        # Detail: list any MISSING or PARTIAL items
        missing_items = []
        partial_items = []

        for section_key in ["decision_tree_nodes", "output_fields", "config_params",
                            "anti_patterns", "studies", "patterns", "pattern_library",
                            "trade_management_matrix", "zones", "edge_cases"]:
            items = manifest.get(section_key, [])
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                status = item.get("status", "")
                name = item.get("name", item.get("id", item.get("pattern", "?")))
                if status == "MISSING":
                    missing_items.append(name)
                elif status == "PARTIAL":
                    partial_items.append(name)

        if missing_items:
            print(f"  MISSING: {', '.join(str(x) for x in missing_items)}")
        if partial_items:
            print(f"  PARTIAL: {', '.join(str(x) for x in partial_items)}")

        print()

    # Grand summary
    print("=" * 70)
    if grand_total > 0:
        overall_drift = round((grand_missing + grand_partial) / grand_total * 100, 1)
    else:
        overall_drift = 0.0

    print(f" GRAND TOTAL:  {grand_total} requirements")
    print(f" Implemented:  {grand_impl}")
    print(f" Partial:      {grand_partial}")
    print(f" Missing:      {grand_missing}")
    print(f" Overall drift: {overall_drift}%")
    print()

    # SHADOW gate
    if overall_drift < 15:
        print(" SHADOW GATE: PASS")
        return 0
    else:
        print(" SHADOW GATE: FAIL")
        return 1


if __name__ == "__main__":
    sys.exit(main())
