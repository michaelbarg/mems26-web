#!/usr/bin/env python3
"""task_log_guard — make the task log fail loudly instead of going stale.

Michael, 2026-08-17: "איך אתה דואג שיהיה לנו מקור אחד קבוע למשימות פתוחות
שכל הזמן מתעדכן?"

A markdown file plus good intentions is exactly what has already failed here:
`docs/SOURCE_OF_TRUTH.md` is 54 days stale, `docs/SYSTEM_MANIFEST.md` 32 days
and missing four LaunchAgents, and `docs/plans/` holds a dozen dated plan files
nobody reopens. Every one of them was written to be "the single source".

The one memory in this repo that has NOT drifted is `config/RULED_FLAGS.yaml` —
and the only thing that makes it different is `scripts/flag_guard.py`, which
FAILS. Not reminds. Fails, with exit 1, in the pre-open drill, every session.

So this applies the same shape to the task log:

  * stale        — untouched for more than TASK_LOG_MAX_AGE_DAYS
  * unstructured — an item without an ID, a status, or a next action
  * dishonest    — an item marked ✅ closed with no dated line in STATUS_BOARD
  * orphaned     — a dated plan file that duplicates it

    python3 scripts/task_log_guard.py          # exit 1 on any problem
    python3 scripts/task_log_guard.py --json   # for the pre-open gate
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "docs" / "plans" / "TASK_LOG.md"
BOARD = ROOT / "docs" / "plans" / "STATUS_BOARD.md"

STATUSES = ("🔴", "🟠", "🟡", "🔵", "✅")


def _max_age_days() -> float:
    return float(os.getenv("TASK_LOG_MAX_AGE_DAYS", "3"))


def _last_touched_days() -> float:
    """Days since the log was last COMMITTED — not since the file was saved.

    mtime is not evidence: an editor, a generator or a `git checkout` moves it
    without anyone having thought about the tasks. The commit is the act.
    """
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", str(LOG.relative_to(ROOT))],
            cwd=ROOT, capture_output=True, text=True, timeout=15).stdout.strip()
        if out:
            return (time.time() - float(out)) / 86400.0
    except Exception:
        pass
    return (time.time() - LOG.stat().st_mtime) / 86400.0 if LOG.exists() else 999.0


def _rows(text: str) -> List[Dict]:
    """Every table row that carries a T-xx id."""
    out = []
    for line in text.splitlines():
        m = re.match(r"\s*\|\s*(T-\d+)\s*\|(.*)$", line)
        if m:
            cells = [c.strip() for c in m.group(2).split("|")]
            # a markdown row ends with '|', so the split leaves a trailing
            # empty cell — dropping it is what makes cells[-1] the real
            # last column. (Caught by the guard reporting all 27 rows as
            # missing a next action while every one of them had it.)
            while cells and not cells[-1]:
                cells.pop()
            out.append({"id": m.group(1), "cells": cells, "line": line})
    return out


def check() -> List[str]:
    problems: List[str] = []

    if not LOG.exists():
        return [f"{LOG.relative_to(ROOT)} does not exist — there is no task log"]

    text = LOG.read_text(encoding="utf-8")

    # 1. stale
    age = _last_touched_days()
    if age > _max_age_days():
        problems.append(
            f"STALE — the task log has not been committed for {age:.1f} days "
            f"(limit {_max_age_days():.0f}). A log nobody updates is a log "
            f"nobody can trust.")

    # 2. an entry point
    if "הצעד הבא" not in text:
        problems.append(
            "no 'next step' block — a 26-row table with no entry point is a "
            "list, not a plan")

    rows = _rows(text)
    if not rows:
        problems.append("no T-xx rows found — the log has lost its structure")

    # 3. every item needs a status and a next action
    for r in rows:
        body = " ".join(r["cells"])
        if not any(s in body for s in STATUSES):
            problems.append(f"{r['id']} has no status marker ({'/'.join(STATUSES)})")
        if len(r["cells"]) < 2 or not r["cells"][-1]:
            problems.append(
                f"{r['id']} has no next action — that is what makes an item "
                f"pickable cold tomorrow")

    # 4. closed items must be verifiable
    board = BOARD.read_text(encoding="utf-8", errors="replace") if BOARD.exists() else ""
    for r in rows:
        if "✅" in " ".join(r["cells"]) and r["id"] not in board:
            problems.append(
                f"{r['id']} is marked ✅ but has no line in STATUS_BOARD.md — "
                f"'done' without a finding and a verification is not allowed "
                f"(CLAUDE.md § Reporting Workflow)")

    # 5. no competing register
    rivals = sorted(p.name for p in (ROOT / "docs" / "plans").glob("OPEN_TASKS*.md"))
    if rivals:
        problems.append(
            f"a competing open-task file exists ({', '.join(rivals)}) — two "
            f"registers means neither is the source. Fold it into TASK_LOG.md.")

    return problems


def _refresh_readiness() -> None:
    """מרענן את תיק-המוכנות מהלוג — כאן, כי כאן הלוג ממילא נקרא ונבדק.

    מייקל 2026-08-29: "שיהיה לך כל פעם שתיצור משימות תשים שם ותאנדקס מה
    בוצע ומה מאורכב." הגנרטור נתלה בבודק ולא ב-EOD, כדי שהדף לא יוכל
    להתיישן מול הלוג: כל ריצה של הבודק (וה-fire_drill מריץ אותו לפני כל
    סשן) כותבת מחדש את שלושת היעדים.

    **לעולם לא מפיל את הבודק ולא נוגע בקוד-היציאה** — תיק-המוכנות הוא
    תצוגה; כשל בו אינו סיבה לחסום סשן-מסחר. וכל פלט הולך ל-stderr, כי
    `--json` נצרך ע"י שער-הקדם-פתיחה ושורה נוספת ב-stdout הייתה שוברת אותו.
    """
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import gen_readiness_page  # noqa: WPS433 — לאזי בכוונה
        gen_readiness_page.main(["--quiet"])
    except Exception as exc:  # pragma: no cover - תצוגה בלבד
        print(f"(readiness page not refreshed: {type(exc).__name__}: {exc})",
              file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    problems = check()
    _refresh_readiness()
    age = _last_touched_days()
    n = len(_rows(LOG.read_text(encoding="utf-8"))) if LOG.exists() else 0

    if args.json:
        print(json.dumps({"ok": not problems, "items": n,
                          "age_days": round(age, 2), "problems": problems},
                         ensure_ascii=False, indent=2))
        return 1 if problems else 0

    print(f"task_log_guard — {n} items, last committed {age:.1f} days ago")
    if not problems:
        print("✅ the task log is current, structured, and the only one")
        return 0
    print(f"\n🔴 {len(problems)} problem(s):\n")
    for p in problems:
        print("  • " + p)
    print("\nThis guard exists because SOURCE_OF_TRUTH.md went 54 days stale and\n"
          "SYSTEM_MANIFEST.md 32 — both were also written to be 'the single source'.\n"
          "RULED_FLAGS.yaml is the one that held, because flag_guard FAILS.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
