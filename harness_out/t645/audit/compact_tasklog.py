#!/usr/bin/env python3
# read-only: compact view of TASK_LOG rows T-585..T-699
import re, sys
src = "docs/plans/TASK_LOG.md"
lo = int(sys.argv[1]) if len(sys.argv) > 1 else 585
hi = int(sys.argv[2]) if len(sys.argv) > 2 else 699
tw = int(sys.argv[3]) if len(sys.argv) > 3 else 700
nw = int(sys.argv[4]) if len(sys.argv) > 4 else 400
rows = []
with open(src, encoding="utf-8") as f:
    for ln, line in enumerate(f, 1):
        m = re.match(r"^\|\s*T-(\d+)\s*\|", line)
        if not m:
            continue
        n = int(m.group(1))
        if n < lo or n > hi:
            continue
        rows.append((n, ln, line.rstrip("\n")))
rows.sort()
for n, ln, line in rows:
    cells = [c.strip() for c in line.split("|")]
    task = cells[2] if len(cells) > 2 else ""
    rest = " | ".join(cells[3:])
    print("=" * 80)
    print(f"T-{n} (L{ln}) len={len(line)}")
    print("TASK:", task[:tw])
    print("REST:", rest[:nw])
