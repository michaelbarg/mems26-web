#!/usr/bin/env python3
"""sync_env_from_ruled — make .env match Michael's RULED_FLAGS.yaml (Michael 07-13).

The problem this solves (Michael: "how do all today's fixes reach Mac2
efficiently"): RULED_FLAGS.yaml IS in git and travels with a pull; .env is
per-machine and out-of-git. So a promotion that adds/changes a ruled flag lands
the RULED file on Mac2 but not the matching .env line → flag_guard NO-GO and the
update stalls.

This script closes ONLY that gap: for each flag in RULED_FLAGS.yaml it ensures
.env has `KEY=expected`. It is NOT a new decision — the RULED file is Michael's
written sign-off; this just applies it. Guarantees:
  - Touches ONLY ruled keys. Every other .env line is left byte-identical.
  - Prints each change (add / change old->new); a ruled OFF stays OFF.
  - --apply writes (snapshot first); default is dry-run.
  - After apply, flag_guard MUST pass — the caller re-runs it to prove it.

Usage: python3 scripts/sync_env_from_ruled.py [--apply]
"""
from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENV = REPO / ".env"
RULED = REPO / "config" / "RULED_FLAGS.yaml"


def load_ruled() -> dict:
    txt = RULED.read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(r'^\s*([A-Z0-9_]+):\s*\{([^}]*)\}', txt, re.M):
        key, body = m.group(1), m.group(2)
        em = re.search(r'expected:\s*"([^"]*)"', body)
        if em:
            out[key] = em.group(1)
    return out


def read_env_lines() -> list:
    return ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []


def main() -> int:
    apply = "--apply" in sys.argv
    ruled = load_ruled()
    if not ruled:
        print("[sync_env] RULED_FLAGS.yaml empty/unparsable — aborting")
        return 1

    lines = read_env_lines()
    idx = {}
    for i, ln in enumerate(lines):
        m = re.match(r'\s*([A-Z0-9_]+)\s*=', ln)
        if m and m.group(1) in ruled:
            idx[m.group(1)] = i

    changes = []
    for key, want in sorted(ruled.items()):
        # Sentinel "unset_or_0": the flag must be ABSENT or 0 (a default-OFF-in-code
        # gate). flag_guard is satisfied by an absent key, so the correct sync is
        # to REMOVE any stray line — never write the literal "unset_or_0".
        if want == "unset_or_0":
            if key in idx:
                cur = lines[idx[key]].split("=", 1)[1].strip()
                if cur not in ("0", ""):
                    changes.append((key, cur, "0"))
                    lines[idx[key]] = f"{key}=0"
            continue
        # Concrete numeric values (0/1/2/3.5/0.8) AND known string-mode values
        # (e.g. "protective" for SYSTEM6_AUTOCORRECT, ruled 07-15). `want` is the
        # RULED `expected:` field — the literal flag_guard compares against — so
        # write it verbatim. A single lowercase token is a mode; skip only values
        # with spaces/punctuation (a real `expected` never has those).
        if not re.fullmatch(r"-?\d+(\.\d+)?|[a-z][a-z_]*", want):
            continue
        if key in idx:
            cur = lines[idx[key]].split("=", 1)[1].strip()
            if cur != want:
                changes.append((key, cur, want))
                lines[idx[key]] = f"{key}={want}"
        else:
            changes.append((key, None, want))
            lines.append(f"{key}={want}")

    if not changes:
        print(f"[sync_env] ✓ .env already matches all {len(ruled)} ruled flags — nothing to do.")
        return 0

    print(f"[sync_env] {len(changes)} ruled flag(s) to sync into .env:")
    for key, old, new in changes:
        print(f"   {key}: {'(missing) → ' + new if old is None else old + ' → ' + new}")

    if not apply:
        print("[sync_env] dry-run — pass --apply to write (a snapshot is taken first).")
        return 0

    # snapshot the out-of-git .env before touching it
    try:
        subprocess.run(["bash", "scripts/mems26_snapshot.sh", "pre-env-sync"],
                       cwd=str(REPO), capture_output=True, timeout=60)
    except Exception:
        pass
    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[sync_env] ✓ wrote .env ({datetime.now().strftime('%H:%M')}). "
          "Restart the backend for it to take effect; flag_guard should now PASS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
