#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract the live gateway decisions of 22.10 and 23.10 from /tmp/backend.err.log (read-only grep; the iMac log
starts 21.10 23:11, so 19–21.10 are not in it). Writes log_tree.json:
  tree    : [ts, pattern, dir, entry, leaf, path]            ← "[Gateway] TREE_V3 <pat> <dir> <entry> → <LEAF> [<path>]"
  blocked : [ts, system, pattern, dir, entry, blocked_by, ot, hint] ← "[Gateway] BLOCKED system=… blocked_by=… ot=… hint=…"
  other   : selected evidence lines (S2-EVIDENCE, TREE-DIFF, StopResolver, wait_for_test, ELQ) with ts
"""
import re, json, subprocess, os
LOG = "/tmp/backend.err.log"
OUT = "/Users/michael/Downloads/mems26_web_git/harness_out/t645/examiner/log_tree.json"
pat_day = r"^2026-10-2[23] (1[6-9]|2[0-2]):"
txt = subprocess.run(["grep", "-E", pat_day, LOG], capture_output=True, text=True).stdout.splitlines()
tree, blocked, other = [], [], []
rt = re.compile(r"^(\S+ \S+) .*\[Gateway\] TREE_V3 (\S+) (LONG|SHORT) ([\d.]+) → (\w+) \[(.*)\]")
rb = re.compile(r"^(\S+ \S+) .*\[Gateway\] BLOCKED system=(\d+) pattern=(\S+) dir=(LONG|SHORT) entry=([\d.]+) blocked_by=(\S+)(?: ot=(\S+))?(?: hint=(\S+))?")
keys = ("S2-EVIDENCE", "TREE-DIFF", "StopResolver", "wait_for_test", "entry_location_quality", "FIRE", "OPENED", "ib_ext_accepted",
        "T-628", "rr_entry_gate", "mid_value_no_edge_test", "entry_not_confirmed")
for ln in txt:
    m = rt.match(ln)
    if m:
        tree.append(list(m.groups())); continue
    m = rb.match(ln)
    if m:
        blocked.append(list(m.groups())); continue
    if any(k in ln for k in keys):
        other.append(ln[:400])
json.dump(dict(tree=tree, blocked=blocked, other=other), open(OUT, "w"), ensure_ascii=False)
print("lines", len(txt), "tree", len(tree), "blocked", len(blocked), "other", len(other))
