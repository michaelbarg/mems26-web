#!/usr/bin/env python3
"""flag_guard — אימות שדגלים שנפסקו לא זזו (מייקל 2026-07-08).

משווה את .env מול config/RULED_FLAGS.yaml. כל סטייה = NO-GO (exit 1) עם פירוט.
רץ בשלב 0 של LIVE_MORNING_PROTOCOL ובתוך fire_drill; אפשר ידנית בכל רגע:
    python3 scripts/flag_guard.py [--env PATH]
"""
import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULED = os.path.join(ROOT, "config", "RULED_FLAGS.yaml")


def parse_env(path):
    envs = {}
    if not os.path.exists(path):
        return envs
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        envs[k.strip()] = v.strip().strip('"').strip("'")
    return envs


def parse_ruled(path):
    """Minimal YAML subset parser (flat `KEY: {expected: "..", ...}` under `ruled:`)."""
    ruled = {}
    in_ruled = False
    rx = re.compile(r'^\s{2}([A-Z0-9_]+):\s*\{(.*)\}\s*$')
    for line in open(path, encoding="utf-8"):
        if line.startswith("ruled:"):
            in_ruled = True
            continue
        if not in_ruled:
            continue
        m = rx.match(line)
        if not m:
            continue
        key, body = m.group(1), m.group(2)
        em = re.search(r'expected:\s*"([^"]*)"', body)
        nm = re.search(r'note:\s*"([^"]*)"', body)
        if em:
            ruled[key] = {"expected": em.group(1), "note": nm.group(1) if nm else ""}
    return ruled


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default=os.path.join(ROOT, ".env"))
    args = ap.parse_args()

    envs = parse_env(args.env)
    ruled = parse_ruled(RULED)
    if not ruled:
        print("FLAG-GUARD: ERROR — RULED_FLAGS.yaml empty/unparsable")
        return 1

    bad = []
    for flag, spec in sorted(ruled.items()):
        want = spec["expected"]
        have = envs.get(flag)
        if want == "unset_or_0":
            ok = have is None or have == "0" or have == ""
            shown = "unset" if have is None else have
        else:
            ok = have == want
            shown = "MISSING" if have is None else have
        mark = "✓" if ok else "✗"
        print(f"  {mark} {flag}: expected={want} actual={shown}" + ("" if ok else f"  ← {spec['note']}"))
        if not ok:
            bad.append(flag)

    if bad:
        print(f"\nFLAG-GUARD: NO-GO — {len(bad)} ruled flag(s) drifted: {', '.join(bad)}")
        print("שינוי דגל שנפסק = פסיקת מייקל בכתב + עדכון config/RULED_FLAGS.yaml באותו קומיט.")
        return 1
    print(f"\nFLAG-GUARD: PASS — all {len(ruled)} ruled flags match.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
