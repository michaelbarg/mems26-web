# -*- coding: utf-8 -*-
"""Apply the n2rsNx package to the demo .env + RULED_FLAGS — ONLY after Michael's explicit decision.
usage: python3 harness_out/t621/t622_apply_n2rsNx.py --dry-run [--five]     (prints the planned changes, writes nothing)
       python3 harness_out/t621/t622_apply_n2rsNx.py --ruling "<Michael's words + time>" [--five]
       --five = n2rs3k: the same package WITHOUT T1_FRONT_RUN_TICKS (78 sessions +3,959.90$ / 31 better / 17 worse)
The snapshot (scripts/mems26_snapshot.sh) is taken BEFORE this script; the restart and the verification after it."""
import argparse
import re
import sys

import os
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV = REPO + "/.env"
RF = REPO + "/config/RULED_FLAGS.yaml"
PKG = [("DAYTYPE_SIDES_ACCEPTED_V1", "single"), ("NORMAL_DAY_RUNNER_OTHER_SIDE_V1", "1"),
       ("OPENING_DRIVE_STRICT_V1", "1"), ("STRUCTURAL_ANCHOR_STOP_AUTHORITY_V1", "1"),
       ("TOUCH2_EDGE_TOL_MAX_ATR", "0.5"), ("T1_FRONT_RUN_TICKS", "2")]
MEASURED = ("n2rsNx 78 סשנים בהרצה הנאמנה (harness_out/t621/days): +4,161.15$ ברוטו / +4,249.55$ נטו מול base, "
            "32 טובים / 20 רעים, כל חודש חיובי (06 +99 · 07 +719 · 08 +2,250 · 09 +519 · 10 +573), 10 אחרונים +863.75")

ap = argparse.ArgumentParser()
ap.add_argument("--dry-run", action="store_true")
ap.add_argument("--ruling", default="")
ap.add_argument("--five", action="store_true", help="n2rs3k — without T1_FRONT_RUN_TICKS")
a = ap.parse_args()
if a.five:
    PKG = [p for p in PKG if p[0] != "T1_FRONT_RUN_TICKS"]
    MEASURED = ("n2rs3k 78 סשנים בהרצה הנאמנה (harness_out/t621/days): +3,959.90$ ברוטו / +4,058.70$ נטו מול base, "
                "31 טובים / 17 רעים, כל חודש חיובי (06 +102 · 07 +722 · 08 +2,199 · 09 +527 · 10 +411)")
if not a.dry_run and not a.ruling.strip():
    sys.exit("refused: no ruling text — this script writes the demo .env only on Michael's explicit decision")

env = open(ENV, encoding="utf-8").read()
lines = env.split("\n")
plan = []
for key, val in PKG:
    rx = re.compile(r"^\s*" + re.escape(key) + r"\s*=")
    idx = [i for i, ln in enumerate(lines) if rx.match(ln)]
    if idx:
        for i in idx:
            old = lines[i]
            lines[i] = f"{key}={val}"
            plan.append(f".env {key}: {old.split('=', 1)[1]!r} → {val!r}")
    else:
        lines.append(f"# {key} — n2rsNx package (Michael 21.10, stage 4 of the 20.10 plan)")
        lines.append(f"{key}={val}")
        plan.append(f".env {key}: (absent) → {val!r}")

rf = open(RF, encoding="utf-8").read()
note = (f"מייקל 21.10 {a.ruling.strip() or '<DRY-RUN>'} — שלב 4 של תוכנית-20.10: חבילת n2rsNx בדמו. {MEASURED}.")
note = note.replace("'", "''")
for key, val in PKG:
    new_line = f'  {key}: {{expected: "{val}", ruled_by: "מייקל", date: "2026-10-21", note: \'{note}\'}}'
    rx = re.compile(r"^  " + re.escape(key) + r": \{.*\}\s*$", re.M)
    if rx.search(rf):
        rf = rx.sub(new_line.replace("\\", "\\\\"), rf, count=1)
        plan.append(f"RULED_FLAGS {key}: → expected {val!r}")
    else:
        rf = rf.rstrip("\n") + "\n" + new_line + "\n"
        plan.append(f"RULED_FLAGS {key}: (new) expected {val!r}")
print("\n".join(plan))
if a.dry_run:
    print("DRY-RUN — nothing written")
    sys.exit(0)
open(ENV, "w", encoding="utf-8").write("\n".join(lines))
open(RF, "w", encoding="utf-8").write(rf)
print("written: .env + config/RULED_FLAGS.yaml")
