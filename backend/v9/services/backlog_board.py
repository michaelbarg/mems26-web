"""backlog_board — DEV_BACKLOG.md → board JSON (single source of truth, Michael 07-12).

The /board page used to read a hand-maintained static task_board.json which went
stale (last touch 07-10 while DEV_BACKLOG.md moved on). Root fix: parse the
canonical DEV_BACKLOG.md into the board schema on demand, so the dashboard can
NEVER lag the backlog. Used by:
  - GET /api/v9/agent/backlog_board  (live, preferred by the panel)
  - scripts/gen_task_board.py        (writes the static fallback file)

Schema matches boardLogic.mjs lanes: open / in_progress / fixed_unverified /
done / blocked; priorities P0/P1/P2 rank, anything else sorts last.
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

BACKLOG = Path(os.path.expanduser("~/Downloads/mems26_web_git/docs/plans/DEV_BACKLOG.md"))

_OWNER = {"🔵": "Cowork", "🟣": "CC", "🟠": "SysChat", "⚪": "Michael"}


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _rows(section: str) -> list[list[str]]:
    """Markdown-table body rows of a section (skips header + separator)."""
    rows = []
    for ln in section.splitlines():
        if not ln.strip().startswith("|"):
            continue
        cs = _cells(ln)
        if all(set(c) <= {"-", " ", ":"} for c in cs):  # separator row
            continue
        rows.append(cs)
    return rows[1:] if rows else []  # drop header row


def _owner(cell: str) -> str:
    for emoji, name in _OWNER.items():
        if emoji in cell:
            return name
    return cell.strip() or "?"


def _prio(cell: str) -> str:
    m = re.search(r"P([0-9])", cell)
    return f"P{m.group(1)}" if m else "P2"


def _cut(s: str, n: int = 170) -> str:
    s = re.sub(r"\*\*|‏", "", s).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def build_board(md_text: str | None = None, mtime: str | None = None) -> dict:
    if md_text is None:
        md_text = BACKLOG.read_text(encoding="utf-8")
        mtime = datetime.fromtimestamp(BACKLOG.stat().st_mtime).strftime("%Y-%m-%d %H:%M")

    # split into "## ..." sections
    secs: dict[str, str] = {}
    cur, buf = "", []
    for ln in md_text.splitlines():
        if ln.startswith("## "):
            if cur:
                secs[cur] = "\n".join(buf)
            cur, buf = ln[3:].strip(), []
        else:
            buf.append(ln)
    if cur:
        secs[cur] = "\n".join(buf)

    def sec(prefix: str) -> str:
        for k, v in secs.items():
            if k.startswith(prefix):
                return v
        return ""

    tasks = []

    # טבלה 1 — לפיתוח (| # | עדיפות | משימה | הסבר | אחראי |)
    for cs in _rows(sec("טבלה 1")):
        if len(cs) < 5:
            continue
        tasks.append({
            "id": f"DEV-{cs[0]}", "title": _cut(cs[2], 90), "priority": _prio(cs[1]),
            "status": "open", "owner": _owner(cs[4]), "where": "DEV_BACKLOG טבלה 1 — לפיתוח",
            "next": _cut(cs[3]),
        })

    # טבלה 2 — ממתין לנתונים (| # | משימה | הסבר | מה מחכה | מתי |)
    for cs in _rows(sec("טבלה 2")):
        if len(cs) < 5:
            continue
        tasks.append({
            "id": f"WAIT-{cs[0]}", "title": _cut(cs[1], 90), "priority": "P2",
            "status": "fixed_unverified", "owner": "Cowork",
            "where": "DEV_BACKLOG טבלה 2 — פותח, ממתין לנתונים",
            "next": _cut(f"מחכה: {cs[3]} · {cs[4]}"),
        })

    # טבלה 3 — בוצע, נבדק אוטומטית (| # | מה בוצע | איך נבדק | מתי | בודק |)
    for cs in _rows(sec("טבלה 3")):
        if len(cs) < 5:
            continue
        tasks.append({
            "id": f"VRF-{cs[0]}", "title": _cut(cs[1], 90), "priority": "P1",
            "status": "fixed_unverified", "owner": _cut(cs[4], 20),
            "where": "DEV_BACKLOG טבלה 3 — ממתין לבדיקה אוטומטית",
            "next": _cut(f"בדיקה: {cs[2]} · {cs[3]}"),
        })

    # טבלה 4 — בוצע ואומת (| קבוצה | מה נסגר |)
    for i, cs in enumerate(_rows(sec("טבלה 4")), 1):
        if len(cs) < 2:
            continue
        tasks.append({
            "id": f"DONE-{i}", "title": _cut(cs[0], 60), "priority": "P2",
            "status": "done", "owner": "Cowork", "where": "DEV_BACKLOG טבלה 4 — בוצע ואומת",
            "next": _cut(cs[1], 200),
        })

    # טבלה 5 — רעיונות (| # | רעיון | הסבר | מאמץ |)
    for cs in _rows(sec("טבלה 5")):
        if len(cs) < 4:
            continue
        tasks.append({
            "id": f"IDEA-{cs[0]}", "title": _cut(cs[1], 90), "priority": "P3",
            "status": "open", "owner": "Michael",
            "where": "DEV_BACKLOG טבלה 5 — רעיון (טרם תועדף; לפסיקת מייקל)",
            "next": _cut(f"{cs[2]} · מאמץ: {cs[3]}"),
        })

    # פעולות-מייקל (| פעולה | זמן | דחיפות |)
    for i, cs in enumerate(_rows(sec("פעולות-מייקל")), 1):
        if len(cs) < 3:
            continue
        tasks.append({
            "id": f"MIKE-{i}", "title": _cut(cs[0], 90),
            "priority": "P1" if "גבוהה" in cs[2] else "P2",
            "status": "open", "owner": "Michael",
            "where": "DEV_BACKLOG — פעולות-מייקל (לא-פיתוח)",
            "next": _cut(f"זמן: {cs[1]} · דחיפות: {cs[2]}"),
        })

    header = md_text.splitlines()[0].lstrip("# ").strip() if md_text else ""
    return {
        "_readme": "GENERATED from docs/plans/DEV_BACKLOG.md — do not hand-edit; run scripts/gen_task_board.py or use the live endpoint.",
        "meta": {
            "title": "לוח-המשימות החי (DEV_BACKLOG)",
            "subtitle": header,
            "updated": mtime or "",
            "priority_note": "P1=גבוהה · P2=בינונית · P3=נמוכה/רעיון · מקור-אמת: docs/plans/DEV_BACKLOG.md",
        },
        "tasks": tasks,
    }
