#!/usr/bin/env python3
# read-only extractor: dumps TASK_LOG rows T-585..T-699 into a text file (audit helper)
import re, sys
src = "docs/plans/TASK_LOG.md"
out = "harness_out/t645/audit/tasklog_rows.txt"
rows = []
with open(src, encoding="utf-8") as f:
    for ln, line in enumerate(f, 1):
        m = re.match(r"^\|\s*T-(\d+)\s*\|", line)
        if not m:
            continue
        n = int(m.group(1))
        if n < 585 or n > 699:
            continue
        cells = [c.strip() for c in line.rstrip("\n").split("|")]
        # cells[0] == '' ; cells[1] = id ; cells[2] task ; cells[3] status ; cells[4] who ; cells[5] next
        rows.append((n, ln, cells))
rows.sort()
with open(out, "w", encoding="utf-8") as w:
    for n, ln, cells in rows:
        w.write("=" * 100 + "\n")
        w.write(f"T-{n}  (line {ln})  ncells={len(cells)}\n")
        labels = ["", "id", "task", "status", "who", "next"]
        for i, c in enumerate(cells[1:], 1):
            lab = labels[i] if i < len(labels) else f"c{i}"
            w.write(f"--[{lab}] ({len(c)} chars)\n{c}\n")
print("rows", len(rows), "->", out)
