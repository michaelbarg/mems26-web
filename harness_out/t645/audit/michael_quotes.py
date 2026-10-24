#!/usr/bin/env python3
# read-only: pull "Michael <date> ... "quote"" fragments (17-24.10) out of TASK_LOG + RULED_FLAGS + reports
import re, sys, glob
srcs = ["docs/plans/TASK_LOG.md", "config/RULED_FLAGS.yaml", "docs/plans/STATUS_BOARD.md"]
srcs += sorted(glob.glob("docs/reports/*2026-10-1[7-9]*.md")) + sorted(glob.glob("docs/reports/*2026-10-2[0-4]*.md"))
srcs += sorted(glob.glob("docs/reports/day_reviews/*2026-10-2*.md")) + sorted(glob.glob("docs/handoff/*2026-10-2*.md"))
pat = re.compile(r"(מייקל|מיכאל|Michael)[^\"“”]{0,40}?\b((1[7-9]|2[0-4])\.10)[^\"“”]{0,25}?[\"“]([^\"”]{6,260})[\"”]")
seen = set()
for s in srcs:
    try:
        txt = open(s, encoding="utf-8").read()
    except Exception:
        continue
    for m in pat.finditer(txt):
        q = m.group(4).strip()
        key = (m.group(2), q[:60])
        if key in seen:
            continue
        seen.add(key)
        print(f"{m.group(2)} | {q[:230]} | {s}")
