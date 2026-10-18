# -*- coding: utf-8 -*-
"""fix-agent night 18→19.10 — TASK_LOG edits: (1) the **עודכן:** line after the legend, (2) T-260's next-step cell →
the result (status untouched), (3) a new T-598 row at the top of the newest table (before T-596). Idempotent."""
import io, os, sys
ROOT = "/Users/michael/Downloads/mems26_web_git"
P = os.path.join(ROOT, "docs", "plans", "TASK_LOG.md")
lines = io.open(P, encoding="utf-8").read().split("\n")
header = io.open(os.path.join(ROOT, "harness_out/t598/task_log_header.txt"), encoding="utf-8").read().strip()
row598 = io.open(os.path.join(ROOT, "harness_out/t598/task_log_row_t598.txt"), encoding="utf-8").read().strip()
t260 = io.open(os.path.join(ROOT, "harness_out/t598/task_log_cell_t260.txt"), encoding="utf-8").read().strip()

# (1) header line right after the legend line (+ blank line), unless already there
li = next(i for i, l in enumerate(lines) if l.startswith("**מקרא:**"))
if not any("fix-agent" in l and "T-598" in l for l in lines[li:li + 4]):
    lines[li + 1:li + 1] = ["", header]

# (2) T-260: prepend the result to the next-step cell (cells: '', ' T-260 ', task, status, who, next, '')
i260 = next(i for i, l in enumerate(lines) if l.startswith("| T-260 |"))
cells = lines[i260].split("|")
assert len(cells) == 7, len(cells)
if "T-598-night" not in cells[5]:
    cells[5] = " " + t260 + " · *קודם:*" + cells[5]
    lines[i260] = "|".join(cells)

# (3) T-598 row before T-596 (the newest table, 5 columns)
if not any(l.startswith("| T-598 |") for l in lines):
    i596 = next(i for i, l in enumerate(lines) if l.startswith("| T-596 |"))
    assert lines[i596 - 1].startswith("|---|"), lines[i596 - 1]
    lines[i596:i596] = [row598]

io.open(P, "w", encoding="utf-8").write("\n".join(lines))
print("TASK_LOG edited: header, T-260 cell, T-598 row")
