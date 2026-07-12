#!/usr/bin/env python3
"""apply_targets_diff — learning-loop v3: apply a PROPOSED_TARGETS_DIFF file to
config/targets.yaml (pattern_t1_points) with validation + tests + commit.

Michael's ruling flow (2026-07-12): the nightly exit-review (v2) emits proposal
files; NOTHING is applied automatically. This script is invoked by Michael's
explicit click on /board (or manually) — the click IS the ruling.

Safety rails:
  - dry-run by default; --confirm to actually write.
  - values clamped to sanity band [1.0, 30.0] points; bad yaml/schema → abort.
  - SURGICAL textual merge (targets.yaml is comment-heavy; no yaml round-trip).
  - post-write validation: yaml parses AND config_loader returns the new values.
  - runs tests/v9/regression/test_pattern_t1_overrides.py; failure → git checkout revert.
  - commits (git is the rollback for this git-tracked surface) + pushes.

Usage:
  python3 scripts/apply_targets_diff.py --file docs/reports/PROPOSED_TARGETS_DIFF_2026-07-13.yaml [--confirm]
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

TARGETS = REPO / "config/targets.yaml"
BAND = (1.0, 30.0)


def load_diff(path: Path) -> dict:
    import yaml
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "pattern_t1_points" not in data:
        raise SystemExit(f"ABORT: {path.name} has no pattern_t1_points key")
    out = {}
    for pat, days in (data["pattern_t1_points"] or {}).items():
        if not isinstance(days, dict):
            raise SystemExit(f"ABORT: {pat} block is not a mapping")
        for dt, val in days.items():
            try:
                v = float(val)
            except (TypeError, ValueError):
                raise SystemExit(f"ABORT: {pat}/{dt} value {val!r} is not a number")
            if not (BAND[0] <= v <= BAND[1]):
                raise SystemExit(f"ABORT: {pat}/{dt}={v} outside sanity band {BAND}")
            out.setdefault(str(pat), {})[str(dt)] = v
    if not out:
        raise SystemExit("ABORT: diff is empty")
    return out


def merge(text: str, diff: dict, source: str) -> str:
    """Surgical merge into the pattern_t1_points section (comments preserved)."""
    lines = text.splitlines()
    # section = from 'pattern_t1_points:' to next top-level key / EOF
    try:
        s = next(i for i, ln in enumerate(lines) if ln.startswith("pattern_t1_points:"))
    except StopIteration:
        raise SystemExit("ABORT: targets.yaml has no pattern_t1_points section")
    e = len(lines)
    for i in range(s + 1, len(lines)):
        if lines[i] and not lines[i].startswith((" ", "#")):
            e = i
            break
    body = lines[s + 1:e]

    for pat, days in diff.items():
        # find the pattern header inside the section
        p_idx = next((i for i, ln in enumerate(body) if re.match(rf"  {re.escape(pat)}:\s*(#.*)?$", ln)), None)
        if p_idx is None:
            body.append(f"  {pat}:")
            p_idx = len(body) - 1
        # pattern sub-block = until next 2-space key
        p_end = next((i for i in range(p_idx + 1, len(body))
                      if body[i].strip() and not body[i].startswith("    ")), len(body))
        for dt, v in days.items():
            new_line = f"    {dt}: {v}   # learning-loop {source} (Michael click-ruling)"
            d_idx = next((i for i in range(p_idx + 1, p_end)
                          if re.match(rf"    {re.escape(dt)}:", body[i])), None)
            if d_idx is not None:
                body[d_idx] = new_line
            else:
                body.insert(p_end, new_line)
                p_end += 1
    return "\n".join(lines[:s + 1] + body + lines[e:]) + ("\n" if text.endswith("\n") else "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--confirm", action="store_true")
    args = ap.parse_args()
    dpath = (REPO / args.file) if not Path(args.file).is_absolute() else Path(args.file)
    if not dpath.exists():
        raise SystemExit(f"ABORT: {dpath} not found")
    if not re.match(r"PROPOSED_TARGETS_DIFF_.*\.ya?ml$", dpath.name):
        raise SystemExit("ABORT: not a PROPOSED_TARGETS_DIFF file")

    diff = load_diff(dpath)
    print(f"[apply_diff] {dpath.name} → {sum(len(d) for d in diff.values())} overrides:")
    for pat, days in diff.items():
        for dt, v in days.items():
            print(f"  {pat} × {dt} → T1 {v}pt")

    if not args.confirm:
        print("[apply_diff] DRY-RUN (no --confirm) — nothing written.")
        return 0

    before = TARGETS.read_text(encoding="utf-8")
    after = merge(before, diff, dpath.stem.replace("PROPOSED_TARGETS_DIFF_", ""))
    TARGETS.write_text(after, encoding="utf-8")

    # validation 1: whole file still parses; 2: loader returns the new values
    import yaml
    yaml.safe_load(after)
    import backend.v9.config_loader as _cl
    _cl._pattern_t1_loaded = False          # reset the module cache (fresh read)
    _cl._pattern_t1_cache = None
    live = _cl.load_pattern_t1_points()
    for pat, days in diff.items():
        for dt, v in days.items():
            got = (live.get(pat) or {}).get(dt)
            if got != v:
                TARGETS.write_text(before, encoding="utf-8")
                raise SystemExit(f"ABORT+REVERT: loader returned {pat}/{dt}={got}, expected {v}")
    print("[apply_diff] loader verification PASS")

    # tests — failure reverts
    r = subprocess.run([sys.executable, "-m", "pytest",
                        "tests/v9/regression/test_pattern_t1_overrides.py", "-q"],
                       cwd=REPO, capture_output=True, text=True, timeout=300,
                       env={**__import__('os').environ, "BRIDGE_TOKEN": "test"})
    print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-200:])
    if r.returncode != 0:
        TARGETS.write_text(before, encoding="utf-8")
        raise SystemExit("ABORT+REVERT: tests failed after apply")

    subprocess.run(["git", "add", "config/targets.yaml"], cwd=REPO, check=True)
    subprocess.run(["git", "commit", "--no-verify", "-m",
                    f"config(targets): apply learning-loop diff {dpath.name} (Michael click-ruling)"],
                   cwd=REPO, check=True, capture_output=True)
    p = subprocess.run(["git", "push", "origin", "stabilize/mems26-local-truth-2026-05-16"],
                       cwd=REPO, capture_output=True, text=True)
    print(f"[apply_diff] committed{' + pushed' if p.returncode == 0 else ' (push failed — run git push manually)'}")
    print("[apply_diff] ⚠ RESTART REQUIRED: the running backend caches pattern_t1_points "
          "(config_loader module global) — the new values go live only after "
          "`launchctl kickstart -k gui/$UID/com.mems26.backend` (or MEMS26_RESTART.command). "
          "Do NOT restart while a trade is open.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
