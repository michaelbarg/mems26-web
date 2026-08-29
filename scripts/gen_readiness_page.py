#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_readiness_page — תיק-המוכנות, מיוצר ממקור-האמת ולא נכתב ביד.

מייקל 2026-08-29: "העמוד היפה שיצרת monday readiness — אפשר שזה יהיה לינק
באפליקציה ובמערכת פרונטאנד, ושיהיה לך כל פעם שתיצור משימות תשים שם ותאנדקס
מה בוצע ומה מאורכב."

שלושה דברים, ולכן שלושה כללים:

  1. **מתעדכן ממקור-האמת.** הטבלאות נקראות מ-`docs/plans/TASK_LOG.md` בכל
     ריצה. שום פריט לא נכתב כאן ביד. הפרקים הסטטיים (פרוטוקול-ההצלחה,
     סריקת-29.08, עצירת-הכיוון, טבלת-הדגלים, לוח-הזמנים) מסומנים במפורש
     כפרקים-נערכים-ביד — כדי שלא ייקרא כאילו הם נמדדו הרגע.
  2. **נגיש בקליק** — נכתב לשלושה יעדים: docs/plans (הקנוני) ·
     frontend/v9/public (הדשבורד) · render_mobile_relay/static (הטלפון).
  3. **מאונדקס** — פתוח / בוצע / מאורכב, ומה שלא מסווג מוצג כ"לא-מסווג"
     במקום להיבלע.

כנות (CLAUDE.md § Source-of-Truth Discipline, כלל-1): פריט בלי סטטוס מזוהה
אינו מומצא ואינו נמחק — הוא מקבל מדור משלו. שורה שבורה (פייפ בתוך התיאור)
נקראת מהסוף (שלוש העמודות האחרונות הן סטטוס/בעלים/הצעד-הבא) במקום להיזרק.

    python3 scripts/gen_readiness_page.py            # כותב את שלושת היעדים
    python3 scripts/gen_readiness_page.py --check    # לא כותב; מדפיס מונים
    python3 scripts/gen_readiness_page.py --quiet    # בלי פלט (ל-hook)
"""
from __future__ import annotations

import argparse
import datetime as _dt
import html
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
TASK_LOG = ROOT / "docs" / "plans" / "TASK_LOG.md"
BOARD = ROOT / "docs" / "plans" / "STATUS_BOARD.md"

TARGETS = [
    ROOT / "docs" / "plans" / "MONDAY_READINESS.html",
    ROOT / "frontend" / "v9" / "public" / "readiness.html",
    ROOT / "render_mobile_relay" / "static" / "readiness.html",
]

ARCHIVE_AFTER_DAYS = 7

# ── סטטוסים ──────────────────────────────────────────────────────────────
# המקרא ב-TASK_LOG: 🔴 חוסם · 🟠 פער-נכונות · 🟡 ממתין-לפסיקה · 🔵 חוב · ✅ נסגר
# 🟢 אינו במקרא אך מופיע בפועל (T-102 "0B COMPLETE · commit hygiene פתוח") —
# ולכן הוא פתוח, לא סגור: ✅ הוא סימן-הסגירה היחיד.
SEV = {"🔴": (0, "s-crit", "חוסם"),
       "🟠": (1, "s-high", "פער-נכונות"),
       "🟡": (2, "s-med", "ממתין-פסיקה"),
       "🔵": (3, "s-low", "חוב"),
       "🟢": (3, "s-low", "בתהליך")}
OPEN_MARKS = tuple(SEV.keys())
DONE_MARK = "✅"

# מילות-סטטוס לשורות שאין בהן אימוג'י כלל (סובלנות, לא ניחוש):
OPEN_WORDS = ("פתוח", "חלקי", "ממתין", "חסום", "בבנייה", "בתהליך",
              "IN-PROGRESS", "BLOCKED", "WIP")


# ── קריאת מקור-האמת ─────────────────────────────────────────────────────

ROW_RE = re.compile(r"^\s*\|\s*(T-\d+)\b")
HEAD_RE = re.compile(r"^\s{0,3}(#{1,4})\s+(.*?)\s*$")


class Task(dict):
    """שורת-משימה. dict כדי שיהיה קל להדפיס ב---check."""


OWNER_TOKENS = ("cowork", "cc", "cursor", "מייקל", "—", "-")


def _looks_status(c: str) -> bool:
    """תא-סטטוס: קצר, ונושא סימן מהמקרא (או מילת-סטטוס, אם אין אימוג'י)."""
    if not c or len(c) > 90:
        return False
    return any(m in c for m in OPEN_MARKS) or DONE_MARK in c or any(w in c for w in OPEN_WORDS)


def _looks_owner(c: str) -> bool:
    """תא-בעלים: קצר, ומכיל שם-סוכן. ריק גם הוא בעלים חוקי (T-18)."""
    if len(c) > 80:
        return False
    if not c:
        return True
    low = c.lower()
    return any(tok.lower() in low for tok in OWNER_TOKENS)


def parse_task_log(text: str) -> List[Task]:
    """כל שורת-טבלה שנושאת מזהה T-xx — סובלנית לשלוש צורות-כשל אמיתיות.

    1. מזהה ממופה-מחדש: ``| T-128 (היה T-37) |`` — הרג'קס של task_log_guard
       דורש ``|`` מיד אחרי המספר ולכן מפספס אותן; כאן המזהה נלקח מהתחילית.
    2. **פייפ בתוך תא**, ומשני הצדדים: בתיאור (``position_qty||0`` ב-T-125,
       ``+5 / +4 / −2`` ב-T-74) *וגם* בהצעד-הבא (``` `… | grep -ci sierra` ```
       ב-T-43, ``` `wc -l` ``` ב-T-68). לכן אי-אפשר לספור לא מההתחלה ולא
       מהסוף — מאתרים את הצמד **סטטוס+בעלים**, ששניהם קצרים ומוגבלי-אוצר-מילים,
       וכל מה שלפניו הוא התיאור וכל מה שאחריו הוא הצעד-הבא. (ספירה-מהסוף
       סיווגה את T-43/T-68/T-87 כ"לא-מסווג" — הבעלים נקרא כסטטוס.)
    3. מזהה כפול (T-28/T-29/…/T-124/T-125 חוזרים בשני מדורים). לא ממזגים —
       כל שורה היא פריט, והכפילות מסומנת בדף במקום להסתיר אחת מהן.
    """
    tasks: List[Task] = []
    section = ""
    for i, line in enumerate(text.split("\n"), start=1):
        h = HEAD_RE.match(line)
        if h:
            section = h.group(2).strip()
            continue
        m = ROW_RE.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        while cells and not cells[-1]:
            cells.pop()

        desc = status = owner = nxt = ""
        si = None
        for j in range(2, len(cells)):
            nxt_cell = cells[j + 1] if j + 1 < len(cells) else ""
            if _looks_status(cells[j]) and _looks_owner(nxt_cell):
                si = j
                break
        if si is not None:
            desc = " | ".join(cells[1:si])
            status = cells[si]
            owner = cells[si + 1] if si + 1 < len(cells) else ""
            nxt = " | ".join(cells[si + 2:])
        else:
            # לא נמצא צמד — לא מנחשים. התיאור נשמר, הסטטוס נשאר ריק,
            # והפריט ייצא ב"לא-מסווג" במקום להיבלע או להיקרא לא-נכון.
            desc = " | ".join(cells[1:])

        tasks.append(Task(id=m.group(1), id_raw=cells[0], desc=desc, status=status,
                          owner=owner, next=nxt, line=i, section=section))
    return tasks


def classify(t: Task, today: _dt.date) -> Tuple[str, int, str, Optional[_dt.date]]:
    """→ (bucket, sev_rank, sev_class, done_date)

    כלל-הכרעה: סימן-פתוח גובר על ✅. שורה שנושאת את שניהם אינה גמורה —
    ``🟠 true-up בוצע; תיקון פתוח`` היא פתוחה, לא סגורה.
    """
    st = t["status"]
    for mark in OPEN_MARKS:
        if mark in st:
            rank, cls, _ = SEV[mark]
            return "open", rank, cls, None
    if DONE_MARK in st:
        d = _parse_done_date(st, today)
        explicit_archive = ("ארכיון" in st or "ארכיון" in t["section"]
                            or t["section"].strip().startswith("✅"))
        if explicit_archive or d is None or (today - d).days > ARCHIVE_AFTER_DAYS:
            return "archived", 9, "s-low", d
        return "done", 8, "s-low", d
    if any(w in st for w in OPEN_WORDS):
        return "open", 4, "s-low", None
    return "unclassified", 5, "s-low", None


def _parse_done_date(status: str, today: _dt.date) -> Optional[_dt.date]:
    """``✅ 28.08 16:12`` → date. שנה לא נכתבת בלוג — נגזרת מהיום."""
    m = re.search(r"(\d{1,2})\.(\d{1,2})(?!\d)", status)
    if not m:
        return None
    day, month = int(m.group(1)), int(m.group(2))
    for year in (today.year, today.year - 1):
        try:
            d = _dt.date(year, month, day)
        except ValueError:
            return None
        if d <= today:
            return d
    return None


def board_index(text: str) -> Dict[str, str]:
    """מזהה → השורה הראשונה ב-STATUS_BOARD שמזכירה אותו (ראיית-אימות)."""
    idx: Dict[str, str] = {}
    for line in text.split("\n"):
        s = line.strip()
        if not s or len(s) < 8:
            continue
        for mid in set(re.findall(r"\bT-\d+\b", s)):
            idx.setdefault(mid, re.sub(r"\s+", " ", s)[:400])
    return idx


# ── מרקדאון → HTML (תת-קבוצה, מה שבאמת מופיע בלוג) ─────────────────────

def md(s: str) -> str:
    """מרקדאון → HTML, עם קוד מוגן מהדגשה.

    ההגנה אינה קוסמטית: ``tests/v9/**`` בתוך גרשיים-הפוכים הפך ל-``<b>``
    שנפתח בתוך ``<span class="mono">`` ונסגר אחריו ⇒ HTML לא-תקין (נתפס
    בבודק-האיזון). לכן מפצלים קודם לקטעי-קוד, ומדגישים רק את מה שביניהם.
    """
    out = []
    for i, part in enumerate(re.split(r"(`[^`]+`)", s)):
        if i % 2:  # קטע-קוד — נשמר כלשונו
            out.append('<span class="mono">' + html.escape(part[1:-1], quote=True)
                       + "</span>")
            continue
        e = html.escape(part, quote=True)
        e = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", e)
        e = re.sub(r"(?<![\w*])\*([^*\n]+?)\*(?![\w*])", r"<em>\1</em>", e)
        out.append(e)
    return "".join(out)


def _plain_len(s: str) -> int:
    return len(re.sub(r"[*`]", "", s))


def cell(s: str, limit: int) -> str:
    """טקסט ארוך אינו נחתך — הוא מתקפל. אף פריט לא נבלע."""
    if not s.strip():
        return '<span class="dim">—</span>'
    if _plain_len(s) <= limit:
        return md(s)
    head = re.sub(r"[*`]", "", s)[:limit].rstrip()
    return ('<details><summary>' + html.escape(head) + '…</summary>'
            '<div class="more">' + md(s) + '</div></details>')


OWNER_CHIPS = (("cowork", "cowork", "c-cw"), ("cc", "cc", "c-cc"),
               ("cursor", "cursor", "c-cu"), ("מייקל", "מייקל", "c-mi"))


def owner_html(raw: str) -> str:
    if not raw.strip():
        return '<span class="dim">—</span>'
    low = raw.lower()
    chips = [f'<span class="chip {cls}">{lbl}</span>'
             for key, lbl, cls in OWNER_CHIPS
             if key.lower() in low]
    if not chips:
        return f'<span class="chip c-mi">{md(raw)[:40]}</span>'
    return ('<span title="' + html.escape(re.sub(r"[*`]", "", raw)) + '">'
            + " ".join(chips) + "</span>")


def verify_html(mid: str, idx: Dict[str, str]) -> str:
    line = idx.get(mid)
    if not line:
        return '<span class="dim" title="אין שורה ב-STATUS_BOARD עם המזהה הזה">—</span>'
    return ('<span class="ok" title="' + html.escape(re.sub(r"[*`]", "", line))
            + '">✓</span>')


# ── עיצוב ────────────────────────────────────────────────────────────────
# הטוקנים, הגופנים והשבבים הם בדיוק אלה של MONDAY_READINESS.html מ-29.08 —
# הדף הזה מחליף אותו, ולכן הוא חייב להיראות כמוהו. מה שנוסף מסומן "חדש".

CSS = r""":root{
  --ground:#f5f4f1; --panel:#ffffff; --panel-2:#efeee9; --line:#dcd9d1; --line-soft:#e8e6e0;
  --ink:#1b2028; --ink-2:#4e5661; --ink-3:#7d8590;
  --amber:#a8720d; --amber-soft:#f3e5c8; --teal:#0f6d6a; --teal-soft:#d6ebe9;
  --up:#166b3e; --up-soft:#d9ecdf; --down:#a32d24; --down-soft:#f6dedb;
  --warn:#8a5a08;
  --stripe-crit:#a32d24; --stripe-high:#a8720d; --stripe-med:#0f6d6a; --stripe-low:#7d8590;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --ground:#0e1319; --panel:#151c24; --panel-2:#1b232c; --line:#2a343f; --line-soft:#222b34;
    --ink:#e7e9ec; --ink-2:#a9b2bd; --ink-3:#75808c;
    --amber:#e2ac4e; --amber-soft:#33280f; --teal:#4fc4bd; --teal-soft:#10312f;
    --up:#54c281; --up-soft:#12301f; --down:#e5756a; --down-soft:#341715;
    --warn:#e2ac4e;
    --stripe-crit:#e5756a; --stripe-high:#e2ac4e; --stripe-med:#4fc4bd; --stripe-low:#75808c;
  }
}
:root[data-theme="dark"]{
  --ground:#0e1319; --panel:#151c24; --panel-2:#1b232c; --line:#2a343f; --line-soft:#222b34;
  --ink:#e7e9ec; --ink-2:#a9b2bd; --ink-3:#75808c;
  --amber:#e2ac4e; --amber-soft:#33280f; --teal:#4fc4bd; --teal-soft:#10312f;
  --up:#54c281; --up-soft:#12301f; --down:#e5756a; --down-soft:#341715;
  --warn:#e2ac4e;
  --stripe-crit:#e5756a; --stripe-high:#e2ac4e; --stripe-med:#4fc4bd; --stripe-low:#75808c;
}
*{box-sizing:border-box}
body{
  margin:0; background:var(--ground); color:var(--ink); direction:rtl;
  font-family:"Assistant",-apple-system,"Segoe UI",sans-serif; font-weight:400;
  font-size:16px; line-height:1.65; padding:0 0 72px; overflow-x:hidden;
}
.wrap{max-width:1080px; margin:0 auto; padding:0 22px}
h1,h2,h3{font-family:"Frank Ruhl Libre",Georgia,serif; text-wrap:balance; margin:0}
h1{font-weight:900; font-size:clamp(30px,5vw,46px); line-height:1.15; letter-spacing:-.01em}
h2{font-weight:700; font-size:clamp(21px,3vw,27px); line-height:1.25}
h3{font-weight:700; font-size:17px}
.mono{font-family:"IBM Plex Mono",ui-monospace,monospace; font-variant-numeric:tabular-nums}
.eyebrow{
  font-family:"IBM Plex Mono",monospace; font-size:11px; letter-spacing:.14em;
  text-transform:uppercase; color:var(--ink-3); font-weight:500;
}

/* header */
header{border-bottom:1px solid var(--line); background:var(--panel); padding:34px 0 26px; margin-bottom:34px}
.hgrid{display:flex; flex-wrap:wrap; gap:26px; align-items:flex-end; justify-content:space-between}
.sub{color:var(--ink-2); font-size:17px; max-width:60ch; margin-top:10px}
.verdict{
  display:flex; flex-direction:column; gap:3px; padding:14px 20px; border-radius:4px;
  background:var(--amber-soft); border:1px solid var(--amber); min-width:210px;
}
.verdict .big{font-family:"Frank Ruhl Libre",serif; font-weight:900; font-size:23px; color:var(--amber)}
.verdict .small{font-size:13px; color:var(--ink-2); line-height:1.4}

/* sections */
section{margin-bottom:44px}
.shead{display:flex; align-items:baseline; gap:14px; border-bottom:2px solid var(--ink); padding-bottom:8px; margin-bottom:20px; flex-wrap:wrap}
.shead .note{font-size:13.5px; color:var(--ink-3); margin-inline-start:auto}

/* evidence strip */
.days{display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px}
.day{background:var(--panel); border:1px solid var(--line); border-radius:4px; padding:14px 16px}
.day .d{font-size:12.5px; color:var(--ink-3); letter-spacing:.04em}
.day .v{font-family:"IBM Plex Mono",monospace; font-variant-numeric:tabular-nums; font-size:24px; font-weight:600; margin:4px 0 2px}
.day .m{font-size:12.5px; color:var(--ink-2)}
.pos{color:var(--up)} .neg{color:var(--down)}
.total{background:var(--up-soft); border-color:var(--up)}

.claim{background:var(--panel); border:1px solid var(--line); border-inline-start:3px solid var(--teal); border-radius:4px; padding:16px 18px; margin-top:16px}
.claim p{margin:0 0 9px} .claim p:last-child{margin:0}

/* tables */
.tbl-wrap{overflow-x:auto; border:1px solid var(--line); border-radius:4px; background:var(--panel)}
table{width:100%; border-collapse:collapse; font-size:14.5px; min-width:640px}
th{
  text-align:start; font-family:"IBM Plex Mono",monospace; font-size:11px; letter-spacing:.1em;
  text-transform:uppercase; color:var(--ink-3); font-weight:500; padding:11px 14px;
  border-bottom:1px solid var(--line); background:var(--panel-2); white-space:nowrap;
}
td{padding:12px 14px; border-bottom:1px solid var(--line-soft); vertical-align:top;
   overflow-wrap:anywhere; word-break:break-word}
tr:last-child td{border-bottom:none}
td.num{font-family:"IBM Plex Mono",monospace; font-variant-numeric:tabular-nums; white-space:nowrap}
.id{font-family:"IBM Plex Mono",monospace; font-size:12.5px; color:var(--ink-3); white-space:nowrap}
.stripe{border-inline-start:3px solid var(--stripe-low)}
.s-crit{border-inline-start-color:var(--stripe-crit)}
.s-high{border-inline-start-color:var(--stripe-high)}
.s-med{border-inline-start-color:var(--stripe-med)}

/* chips */
.chip{
  display:inline-block; padding:2px 9px; border-radius:3px; font-size:12px; font-weight:600;
  white-space:nowrap; font-family:"IBM Plex Mono",monospace;
}
.c-cc{background:var(--amber-soft); color:var(--amber); border:1px solid var(--amber)}
.c-cw{background:var(--teal-soft); color:var(--teal); border:1px solid var(--teal)}
.c-mi{background:var(--panel-2); color:var(--ink-2); border:1px solid var(--line)}
.c-cu{background:var(--panel-2); color:var(--ink-3); border:1px dashed var(--line)}  /* חדש — cursor */
.c-yes{background:var(--down-soft); color:var(--down); border:1px solid var(--down)}
.c-no{background:var(--panel-2); color:var(--ink-3); border:1px solid var(--line)}
.c-kill{background:var(--down-soft); color:var(--down)}
.c-keep{background:var(--up-soft); color:var(--up)}
.c-fix{background:var(--amber-soft); color:var(--amber)}

/* frequency bar */
.bar{display:flex; align-items:center; gap:8px}
.bar .track{flex:1; min-width:54px; height:6px; background:var(--panel-2); border-radius:3px; overflow:hidden}
.bar .fill{height:100%; background:var(--amber); border-radius:3px}
.bar .n{font-family:"IBM Plex Mono",monospace; font-size:12.5px; color:var(--ink-2); width:22px; text-align:end}

/* mechanism */
.mech{display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:14px; margin-top:8px}
.step{background:var(--panel); border:1px solid var(--line); border-radius:4px; padding:16px 18px; position:relative}
.step .n{font-family:"IBM Plex Mono",monospace; font-size:11px; color:var(--amber); letter-spacing:.1em; font-weight:600}
.step h3{margin:6px 0 7px}
.step p{margin:0; font-size:14px; color:var(--ink-2)}
.trigger{background:var(--panel-2); border:1px solid var(--line); border-radius:4px; padding:15px 18px; margin-bottom:16px}
.trigger .mono{font-size:13.5px; color:var(--ink); line-height:2}

/* timeline */
.tl{list-style:none; margin:0; padding:0; display:grid; gap:2px}
.tl li{display:flex; gap:16px; align-items:baseline; background:var(--panel); border:1px solid var(--line); padding:13px 16px}
.tl li:first-child{border-radius:4px 4px 0 0} .tl li:last-child{border-radius:0 0 4px 4px}
.tl .when{font-family:"IBM Plex Mono",monospace; font-size:12.5px; color:var(--amber); font-weight:600; white-space:nowrap; min-width:96px}
.tl .what{flex:1}
.tl .what b{font-weight:600}

.foot{border-top:1px solid var(--line); padding-top:18px; color:var(--ink-3); font-size:13.5px}
a{color:var(--amber)}
:focus-visible{outline:2px solid var(--amber); outline-offset:2px}

/* ── חדש: מונים · קיפול · מדור-ארכיון ── */
.counts{display:grid; grid-template-columns:repeat(auto-fit,minmax(132px,1fr)); gap:12px; margin-bottom:18px}
.count{background:var(--panel); border:1px solid var(--line); border-radius:4px; padding:14px 16px}
.count .v{font-family:"IBM Plex Mono",monospace; font-variant-numeric:tabular-nums; font-size:30px; font-weight:600; line-height:1.1}
.count .d{font-size:12.5px; color:var(--ink-3); margin-top:4px}
.count.crit{border-color:var(--down)} .count.crit .v{color:var(--down)}
.count.good{border-color:var(--up)} .count.good .v{color:var(--up)}
.count.warnb{border-color:var(--amber)} .count.warnb .v{color:var(--amber)}
.blockers{display:grid; gap:2px; margin-top:6px}
.blockers li{display:flex; gap:14px; align-items:baseline; background:var(--panel);
  border:1px solid var(--line); border-inline-start:3px solid var(--stripe-crit); padding:11px 15px}
.blockers{list-style:none; padding:0; margin:6px 0 0}
.blockers .bid{font-family:"IBM Plex Mono",monospace; font-size:12.5px; color:var(--down); font-weight:600; min-width:66px}
.blockers .bt{flex:1; font-size:14.5px}
details{margin:0}
summary{cursor:pointer; color:var(--ink-2)}
summary::marker{color:var(--ink-3)}
.more{margin-top:8px; padding-inline-start:10px; border-inline-start:2px solid var(--line-soft); color:var(--ink-2); font-size:13.5px}
.dim{color:var(--ink-3)}
.ok{color:var(--up); font-weight:700}
.archive-note{color:var(--ink-3); font-size:13.5px; margin:0 0 12px}
.staticnote{font-size:12px; color:var(--ink-3); border:1px dashed var(--line); border-radius:3px;
  padding:2px 8px; display:inline-block}
@media (max-width:620px){
  .verdict{min-width:0; width:100%}
  .wrap{padding:0 14px}
  table{min-width:520px; font-size:13.5px}
  td,th{padding:9px 10px}
  .blockers li{flex-direction:column; gap:2px}
}
"""


# ── פרקים סטטיים ────────────────────────────────────────────────────────
# מועתקים מ-MONDAY_READINESS.html של 29.08 ונערכים כאן ביד. הם *לא* נגזרים
# מ-TASK_LOG, ולכן כל אחד נושא תג "פרק-נערך-ביד" בכותרת — כדי שלא ייקרא
# כאילו המספרים שבו נמדדו בריצה הזו. פערי-הסריקה (SA-x/UX-x) נשמרים כאן
# כי אין להם מזהה T-xx בלוג; מחיקתם הייתה מאבדת אותם.

HAND = '<span class="staticnote">פרק נערך-ביד · לא נגזר מהלוג</span>'

STATIC_SECTIONS = r"""
<section>
  <div class="shead">
    <h2>הפרוטוקול: מה המערכת הוכיחה</h2>
    <span class="note">__HAND__ · מקור: <span class="mono">v9_trades</span> · לייב בלבד · אחרי התאמת-ברוקר</span>
  </div>
  <div class="days">
    <div class="day"><div class="d">26.08 · יום ראשון אוטונומי</div><div class="v neg">−$1.25</div><div class="m">4 עסקאות · 50%</div></div>
    <div class="day"><div class="d">27.08</div><div class="v pos">+$123.75</div><div class="m">5 עסקאות · 80%</div></div>
    <div class="day"><div class="d">28.08</div><div class="v pos">+$348.75</div><div class="m">8 עסקאות · 75%</div></div>
    <div class="day total"><div class="d">סך שלושת הימים</div><div class="v pos">+$471.25</div><div class="m">17 עסקאות · שיפור יומי רצוף</div></div>
  </div>
  <div class="claim">
    <p><b>מה נלקח בחשבון נכון.</b> המערכת סחרה שלושה ימים ברצף בלי יד אנושית על ההדק, והגדילה רווח בכל יום. היא זיהתה נכון את כיוון-היום (ב-28.08 ירתה עם צד-השורט בבוקר וניצחה, ואת רגל-הלונג של אחה"צ סימנה בזמן), הפעילה מימושים בשלבים, והגנה על עסקה שנקלעה לצרה במקום להפסיד בה.</p>
    <p><b>ומה שהמספרים גם אומרים, ביושר.</b> תיק-הצל — כלומר כל מה שהמערכת <em>הייתה</em> מבצעת בלי שערי-הסינון — היה שלילי כמעט בכל יום. כלומר: לא הזיהוי לבדו מרוויח, אלא הזיהוי בתוספת סינון. זו בדיוק הסיבה שכל שינוי-שער נמדד לפני שהוא נדלק, ולמה החזרנו שערים שהיו חוסמים כניסות טובות אבל לא נגענו באלה שחוסמים כניסות רעות.</p>
    <p><b>תיקון לפרוטוקול — ביקורת-עצמית 29.08.</b> בפסקה הזו הופיע קודם משפט שאמר שארבע כניסות-לונג טובות נחסמו ב-28.08 ושהפסד-ההזדמנות הוא כ-32 נקודות לכניסה. <b>המשפט הזה היה שגוי ותוקן.</b> ביקורת בלתי-תלויה מצאה שרשומת-ההחלטה של אותו מועמד נשאה סטופ ב-7738.00, והשוק לקח אותו חמש דקות אחרי הכניסה — כלומר ‎−$176.25 ולא ‎+$491. השיא הגיע 55 דקות מאוחר יותר, אחרי נסיגה של 23 נקודות שהסולם שלנו לא היה שורד. בבדיקה על כל שבע הכניסות שאותם שערים חסמו: <b>שלוש היו מנצחות, ארבע היו סטופים</b> — לא תמונה חד-צדדית.</p>
    <p><b>מה זה משנה בפועל.</b> ביטול שני השערים נשאר בתוקף — הם באמת חסמו כניסות במיקום טוב — אבל הוא נשען כעת על מדידה מלאה ולא על מספר יחיד. <b>והלקח החשוב יותר:</b> כל הצדקה לשינוי-מסחר חייבת להימדד מול הסטופ שהמערכת עצמה הציבה לאותה עסקה, לא מול השיא שהמחיר הגיע אליו אחר-כך. הכלל הזה נכנס לפרוטוקול-המדידה.</p>
</div>
</section>

<section>
  <div class="shead">
    <h2>פערים שנוספו בסריקת 29.08</h2>
    <span class="note">__HAND__ · שלוש ביקורות: עצמית · דשבורד · טלפון</span>
  </div>
  <p class="archive-note">לפערים האלה אין מזהה <span class="mono">T-xx</span> בלוג-המשימות, ולכן הם אינם מופיעים בטבלאות שלמעלה. הם נשמרים כאן במלואם כדי שלא ייעלמו.</p>
  <div class="tbl-wrap">
    <table>
      <thead><tr><th>#</th><th>הפער</th><th>הראיה</th><th>מבצע</th><th>חוסם שני?</th></tr></thead>
      <tbody>
        <tr class="stripe s-crit"><td class="id">SA-4</td>
          <td><b>פקודת-חירום מהטלפון פגה בשקט</b> — משיכת-הפקודות ישבה אחרי היציאה מענף-המנוחה</td>
          <td>שבתות ולילות 23:30–10:00: ‏FLATTEN היה מציג "נשלחה" ולא נמשך</td>
          <td><span class="chip c-cw">cowork</span> ✅ תוקן</td><td><span class="chip c-no">נסגר</span></td></tr>
        <tr class="stripe s-crit"><td class="id">SA-6</td>
          <td><b>ספר-הפסיקות הכיל רשומות כפולות סותרות</b> — 3 שערי-מסחר</td>
          <td>מיון-מחדש היה מהפך את שלוש הפסיקות הקבועות בחזרה למצב דלוק</td>
          <td><span class="chip c-cw">cowork</span> ✅ תוקן</td><td><span class="chip c-no">נסגר</span></td></tr>
        <tr class="stripe s-crit"><td class="id">SA-3</td>
          <td><b>ביטול וטו-הכיוון סגר בטעות 196 שורות</b> — כולל מסנן-ההמשך ומצפן-הכיוון, שניהם פסוקים-דלוקים</td>
          <td>ארבעה דגלים פסוקים איבדו את מסלול-הביצוע היחיד שלהם</td>
          <td><span class="chip c-cc">cc</span></td><td><span class="chip c-yes">כן</span></td></tr>
        <tr class="stripe s-crit"><td class="id">SA-7</td>
          <td><b>שער-הפתיחה הבינארי אינרטי</b> — הוא משווה למחרוזות שהייצור לא מייצר</td>
          <td>הווטו חוסם אפס מקרים; הטסט שאישר אותו ממציא את הקלט</td>
          <td><span class="chip c-cc">cc</span></td><td><span class="chip c-yes">כן</span></td></tr>
        <tr class="stripe s-high"><td class="id">SA-5</td>
          <td><b>שלושה טסטי-רגרסיה אדומים</b> — שניים מהם מקבעים פסיקה שלך מ-12.08</td>
          <td>נשברו בשינוי-הפלייבוק ולא עודכנו</td>
          <td><span class="chip c-cc">cc</span></td><td><span class="chip c-no">לפני הדלקה</span></td></tr>
        <tr class="stripe s-high"><td class="id">SA-8</td>
          <td><b>ריצוד-תווית אחרי ביטול שער-היציבות</b> — 15 שינויי-סיווג ב-35 שורות ב-28.08</td>
          <td>הפלייבוק קורא את התווית החיה ⇒ אותו סטאפ מותר או נחסם לפי השנייה</td>
          <td><span class="chip c-cc">cc</span></td><td><span class="chip c-yes">כן</span></td></tr>
        <tr class="stripe s-med"><td class="id">UX-1</td>
          <td><b>פאנל מערכת-6 מציג "אין נתונים"</b> בזמן שהמפקח מדווח תקין</td>
          <td>אי-התאמת-חוזה בין הצד השרת לצד הלקוח</td>
          <td><span class="chip c-cc">cc</span></td><td><span class="chip c-no">לא</span></td></tr>
        <tr class="stripe s-med"><td class="id">UX-2</td>
          <td><b>אפס מצבי-פוקוס בכל הפרונטאנד</b> — כולל כפתור-הסגירה ההרסני</td>
          <td>‏grep על כל הקוד: אפס</td>
          <td><span class="chip c-cc">cc</span></td><td><span class="chip c-no">לא</span></td></tr>
        <tr class="stripe s-med"><td class="id">חדש</td>
          <td><b>חלונית-נרות בטלפון</b> — תמונת-מצב ויזואלית של המחיר מול הרמות</td>
          <td>בקשת-מייקל 29.08 · אין תלות במסחר, קל להוסיף</td>
          <td><span class="chip c-cw">cowork</span></td><td><span class="chip c-no">רצוי</span></td></tr>
      </tbody>
    </table>
  </div>
</section>

<section>
  <div class="shead">
    <h2>עצירת-כיוון מוקדמת</h2>
    <span class="note">__HAND__ · הפסיקה שלך: "תקרה כפולה שלא מתקדמת — עוצרים ומחפשים את הצד השני"</span>
  </div>
  <div class="trigger">
    <div class="eyebrow" style="margin-bottom:8px">הטריגר — בינארי, בלי אחוזי-ביטחון</div>
    <div class="mono">
      נגיעה בקצה (אזור-ערך עליון · שיא-סשן · קצה-שעה-ראשונה) ← נרשם שיא ראשון<br>
      דחייה: סגירה חזרה מתחת לקצה<br>
      נגיעה שנייה באותו אזור, בטווח רבע-תנודתיות, ואינה סוגרת מעל הראשון<br>
      בר-אישור: סגירה מתחת לשפל שבין השיאים ← <b>כישלון-תקרה</b>
    </div>
  </div>
  <div class="mech">
    <div class="step"><div class="n">פעולה א</div><h3>לבנק את הרווח</h3><p>הסטופ נדחף מתחת לשפל בר-האישור. ברווח משמעותי — סגירה מלאה. דרך מנגנוני-היציאה המאומתים בלבד.</p></div>
    <div class="step"><div class="n">פעולה ב</div><h3>לנעול את הקצה</h3><p>אסורה כניסה חדשה באותו כיוון מעל אותה תקרה, עד שהיא נפרצת בקבלה אמיתית. זה בדיוק מה שמנע את ארבע הקניות-לתוך-התקרה.</p></div>
    <div class="step"><div class="n">פעולה ג</div><h3>לחמש את הצד השני</h3><p>שורט בבר-האישור עצמו — לא אחרי שהמחיר כבר ירד. סטופ מעל השיא, יעד ראשון נקודת-הערך המרכזית.</p></div>
  </div>
  <p style="color:var(--ink-2); font-size:14.5px; margin-top:16px">
    שלוש הפעולות נבנות ככבויות, נמדדות מול כל הימים ההיסטוריים כולל עמלות, ונדלקות בסדר: נעילת-הקצה ראשונה (מונעת הפסד), אחריה הבנק, ולבסוף ההיפוך. <b>עוגן-האימות הוא 28.08 עצמו</b> — הכניסות בתקרה חייבות להיפסל, והשורט חייב להיפתח ברגע-הכישלון.
  </p>
</section>

<section>
  <div class="shead">
    <h2>הדגלים שחוסמים מסחר</h2>
    <span class="note">__HAND__ · ספירה מהליגר החי · 25–28.08</span>
  </div>
  <div class="tbl-wrap">
    <table>
      <thead><tr><th>החוסם</th><th style="width:130px">תדירות</th><th>מה הוא עושה</th><th>פסק</th></tr></thead>
      <tbody>
        <tr><td class="mono">daytype_playbook</td><td><div class="bar"><div class="track"><div class="fill" style="width:100%"></div></div><span class="n">18</span></div></td><td>סוג-היום אוסר את משפחת-התבנית</td><td><span class="chip c-fix">לתקן</span> ‏ZLR שוחרר; לבדוק את שאר התאים מול התוצאות</td></tr>
        <tr><td class="mono">live_slot_occupied</td><td><div class="bar"><div class="track"><div class="fill" style="width:78%"></div></div><span class="n">14</span></div></td><td>עסקה חיה כבר פתוחה</td><td><span class="chip c-fix">לתקן</span> נכון כרעיון — אך משתחרר מוקדם מדי (T-43)</td></tr>
        <tr><td class="mono">awaiting_release</td><td><div class="bar"><div class="track"><div class="fill" style="width:67%"></div></div><span class="n">12</span></div></td><td>המחיר עדיין באזור-הקיצון בלי שחרור מבני</td><td><span class="chip c-fix">לתקן</span> שומר אמיתי, אך עיוור לימי-היפוך</td></tr>
        <tr><td class="mono">eod_entry_cutoff</td><td><div class="bar"><div class="track"><div class="fill" style="width:44%"></div></div><span class="n">8</span></div></td><td>אין כניסות ב-45 הדקות האחרונות</td><td><span class="chip c-keep">להשאיר</span></td></tr>
        <tr><td class="mono">lsma_flat</td><td><div class="bar"><div class="track"><div class="fill" style="width:39%"></div></div><span class="n">7</span></div></td><td>אין שיפוע-מגמה</td><td><span class="chip c-kill">בוטל</span> לצמיתות ב-28.08</td></tr>
        <tr><td class="mono">rr_hard_floor</td><td><div class="bar"><div class="track"><div class="fill" style="width:17%"></div></div><span class="n">3</span></div></td><td>יחס סיכוי-סיכון מתחת לרצפה</td><td><span class="chip c-keep">להשאיר</span></td></tr>
        <tr><td class="mono">cold_start_guard</td><td><div class="bar"><div class="track"><div class="fill" style="width:11%"></div></div><span class="n">2</span></div></td><td>המערכת עלתה הרגע — ממתינה לברים</td><td><span class="chip c-keep">להשאיר</span></td></tr>
        <tr><td class="mono">location_gate</td><td><div class="bar"><div class="track"><div class="fill" style="width:11%"></div></div><span class="n">2</span></div></td><td>מיקום-הכניסה לא מתאים לסוג-היום</td><td><span class="chip c-keep">להשאיר</span> — משלים את מדד-איכות-המיקום</td></tr>
        <tr><td class="mono">direction_context</td><td><div class="bar"><div class="track"><div class="fill" style="width:6%"></div></div><span class="n">1</span></div></td><td>וטו-כיוון מבוסס-LSMA</td><td><span class="chip c-kill">בוטל</span> לצמיתות ב-28.08</td></tr>
        <tr><td class="mono">structural_targets_wrong_side</td><td><div class="bar"><div class="track"><div class="fill" style="width:6%"></div></div><span class="n">1</span></div></td><td>כל היעדים המבניים בצד ההפוך</td><td><span class="chip c-fix">הוחרג</span> בימי-מגמה; נשאר בימי-דשדוש</td></tr>
        <tr><td class="mono">entry_not_confirmed</td><td><div class="bar"><div class="track"><div class="fill" style="width:6%"></div></div><span class="n">1</span></div></td><td>אין בר-אישור בכיוון</td><td><span class="chip c-keep">להשאיר</span></td></tr>
      </tbody>
    </table>
  </div>
  <p style="color:var(--ink-2); font-size:14.5px; margin-top:14px">
    <b>מצב ספר-הדגלים:</b> 214 דגלים פסוקים, כולם תואמים את מה שנפסק, וכל דגל דלוק מוכח כנקרא בקוד-הייצור. הבודק רץ לפני כל סשן ונכשל על סטייה. <b>מה שנותר לא-תקני</b> אינו "דגל שקרי" אלא ספים מוחלטים שצריכים להפוך ליחסיים — זה T-42.
  </p>
</section>

<section>
  <div class="shead"><h2>חסימת דגל ליום מסחר</h2><span class="note">__HAND__ · קיים חלקית — צריך השלמה</span></div>
  <div class="tbl-wrap">
    <table>
      <thead><tr><th>יכולת</th><th>היום</th><th>הנדרש</th></tr></thead>
      <tbody>
        <tr><td>ביטול חוסם מהטלפון</td><td>✅ כפתור ליד כל חסימה</td><td>נשאר</td></tr>
        <tr><td>תוקף</td><td>עד הפעלה-מחדש של המערכת</td><td><b>ליום-מסחר, עם פקיעה אוטומטית בסגירה</b></td></tr>
        <tr><td>כיסוי</td><td>9 שערים</td><td>כל השערים החוסמים, למעט קבוצת-הבטיחות</td></tr>
        <tr><td>מהמחשב</td><td>❌ לא קיים</td><td>אותם כפתורים בפאנל-הצד</td></tr>
        <tr><td>תיעוד</td><td>שורת-לוג בלבד</td><td>יומן: מי חסם, מתי, ומה זה שינה באותו יום</td></tr>
      </tbody>
    </table>
  </div>
</section>

<section>
  <div class="shead"><h2>לוח-זמנים עד הפתיחה</h2><span class="note">__HAND__</span></div>
  <ul class="tl">
    <li><span class="when">שבת · 29.08</span><span class="what"><b>cc</b> — שלושת החוסמים: מודל-הפוזיציה, הזנת-הוולום, מקור-הכיוון. כל אחד עם טסט שמשחזר את הכשל של 28.08.</span></li>
    <li><span class="when">שבת · ערב</span><span class="what"><b>cowork</b> — אימות עצמאי של כל תיקון: הרצת הטסטים בעצמי, קריאת הדיף, ובדיקה שהמסלול-הכבוי לא השתנה.</span></li>
    <li><span class="when">ראשון</span><span class="what"><b>cc</b> — הבנייה-לצל: עצירת-הכיוון, איכות-המיקום, המרת-הספים, וחסימת-דגל-ליום. <b>cowork</b> — מדידה על כל הימים ההיסטוריים כולל עמלות.</span></li>
    <li><span class="when">ראשון · ערב</span><span class="what"><b>הכרעה</b> — מה נדלק חי ומה נשאר בצל. גודל-עסקה לפי המרג'ין בפועל. <b>מייקל מאשר.</b></span></li>
    <li><span class="when">שני · 15:40</span><span class="what">שער-הבוקר האוטומטי: בדיקת-מוכנות מלאה, קביעת גודל, ודיווח לטלפון לפני הפתיחה.</span></li>
  </ul>
</section>
""".replace("__HAND__", HAND)


# ── בניית הדף ────────────────────────────────────────────────────────────

def _num(mid: str) -> int:
    m = re.search(r"\d+", mid)
    return int(m.group()) if m else 0


def _id_cell(t: Task, dupes: Dict[str, int]) -> str:
    extra = ""
    if dupes.get(t["id"], 0) > 1:
        # אותו מזהה מופיע פעמיים בלוג (T-28/T-29/T-124/T-125 ועוד). לא ממזגים
        # ולא מסתירים — מסמנים את מספר-השורה כדי שאפשר יהיה לפתוח את הנכונה.
        extra = ('<br><span class="dim" title="המזהה הזה מופיע יותר מפעם אחת '
                 'ב-TASK_LOG — זו השורה בקובץ">שורה ' + str(t["line"]) + "</span>")
    label = html.escape(t["id_raw"]) if t["id_raw"] != t["id"] else html.escape(t["id"])
    return label + extra


def _open_table(rows: List[Tuple[Task, int, str]], idx: Dict[str, str],
                dupes: Dict[str, int]) -> str:
    out = ['<div class="tbl-wrap"><table>',
           "<thead><tr><th>#</th><th>המשימה</th><th>בעלים</th>"
           "<th>הצעד הבא</th><th title=\"שורה תואמת ב-STATUS_BOARD\">אימות</th>"
           "</tr></thead><tbody>"]
    for t, _rank, cls in rows:
        out.append(
            '<tr class="stripe ' + cls + '">'
            '<td class="id">' + _id_cell(t, dupes) + "</td>"
            "<td>" + cell(t["desc"], 230) + "</td>"
            "<td>" + owner_html(t["owner"]) + "</td>"
            "<td>" + cell(t["next"], 170) + "</td>"
            '<td class="num">' + verify_html(t["id"], idx) + "</td></tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def _done_table(rows: List[Tuple[Task, Optional[_dt.date]]], idx: Dict[str, str],
                dupes: Dict[str, int]) -> str:
    out = ['<div class="tbl-wrap"><table>',
           "<thead><tr><th>#</th><th>המשימה</th><th>נסגר</th><th>בעלים</th>"
           "<th title=\"שורה תואמת ב-STATUS_BOARD\">אימות</th>"
           "</tr></thead><tbody>"]
    for t, d in rows:
        when = d.strftime("%d.%m") if d else '<span class="dim">ללא תאריך</span>'
        out.append(
            '<tr class="stripe s-low">'
            '<td class="id">' + _id_cell(t, dupes) + "</td>"
            "<td>" + cell(t["desc"], 200) + "</td>"
            '<td class="num">' + when + "</td>"
            "<td>" + owner_html(t["owner"]) + "</td>"
            '<td class="num">' + verify_html(t["id"], idx) + "</td></tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def build(task_text: str, board_text: str, stamp: str, commit: str,
          today: _dt.date) -> Tuple[str, Dict[str, int]]:
    tasks = parse_task_log(task_text)
    idx = board_index(board_text)
    dupes: Dict[str, int] = {}
    for t in tasks:
        dupes[t["id"]] = dupes.get(t["id"], 0) + 1

    op: List[Tuple[Task, int, str]] = []
    dn: List[Tuple[Task, Optional[_dt.date]]] = []
    ar: List[Tuple[Task, Optional[_dt.date]]] = []
    un: List[Task] = []
    for t in tasks:
        bucket, rank, cls, d = classify(t, today)
        if bucket == "open":
            op.append((t, rank, cls))
        elif bucket == "done":
            dn.append((t, d))
        elif bucket == "archived":
            ar.append((t, d))
        else:
            un.append(t)

    op.sort(key=lambda x: (x[1], _num(x[0]["id"]), x[0]["line"]))
    dn.sort(key=lambda x: (-(x[1].toordinal() if x[1] else 0), _num(x[0]["id"])))
    ar.sort(key=lambda x: (-(x[1].toordinal() if x[1] else 0), _num(x[0]["id"])))

    blockers = [t for t, rank, _ in op if rank == 0]
    counts = {"open": len(op), "done": len(dn), "archived": len(ar),
              "unclassified": len(un), "blockers": len(blockers),
              "total": len(tasks)}

    verdict_big = (str(counts["blockers"]) + " חוסמים פתוחים"
                   if counts["blockers"] else "אין חוסם פתוח")
    unc_extra = ("" if not un else
                 " · " + str(counts["unclassified"]) + " לא-מסווגים")

    h = []
    h.append('<!doctype html>\n<html lang="he" dir="rtl">\n<head>\n'
             '<meta charset="utf-8">\n'
             '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
             "<title>תיק מוכנות · MEMS26</title>\n"
             '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
             "family=Frank+Ruhl+Libre:wght@500;700;900&family=Assistant:wght@300;400;600;700"
             '&family=IBM+Plex+Mono:wght@400;500;600&display=swap">\n'
             "<style>\n" + CSS + "</style>\n</head>\n<body>")

    h.append(
        "<header><div class=\"wrap hgrid\"><div>"
        '<div class="eyebrow">MEMS26 · תיק-מוכנות · מיוצר מ-TASK_LOG</div>'
        "<h1>תיק המוכנות</h1>"
        '<p class="sub">אינדקס חי של כל משימה בלוג — מה פתוח, מה בוצע, ומה מאורכב. '
        "הטבלאות נקראות מ-<span class=\"mono\">docs/plans/TASK_LOG.md</span> בכל ריצה; "
        "הפרקים שמסומנים <em>נערך-ביד</em> הם ניתוח, לא מדידה של הרגע.</p></div>"
        '<div class="verdict"><div class="eyebrow">מצב</div>'
        '<div class="big">' + html.escape(verdict_big) + "</div>"
        '<div class="small">' + str(counts["open"]) + " פתוחים · "
        + str(counts["done"]) + " נסגרו בשבוע האחרון · "
        + str(counts["archived"]) + " מאורכבים" + unc_extra
        + "</div></div></div></header>")

    h.append('<div class="wrap">')

    # ── מונים + חוסמים ──
    h.append('<section><div class="shead"><h2>מונים</h2>'
             '<span class="note">' + str(counts["total"])
             + " שורות-משימה בלוג · חוסם = פריט פתוח בדרגה 🔴</span></div>")
    h.append('<div class="counts">'
             '<div class="count crit"><div class="v">' + str(counts["blockers"])
             + '</div><div class="d">חוסמי-שני (🔴 פתוח)</div></div>'
             '<div class="count warnb"><div class="v">' + str(counts["open"])
             + '</div><div class="d">פתוח · כל הדרגות</div></div>'
             '<div class="count good"><div class="v">' + str(counts["done"])
             + '</div><div class="d">בוצע · ' + str(ARCHIVE_AFTER_DAYS)
             + ' ימים אחרונים</div></div>'
             '<div class="count"><div class="v">' + str(counts["archived"])
             + '</div><div class="d">מאורכב</div></div>'
             '<div class="count"><div class="v">' + str(counts["unclassified"])
             + '</div><div class="d">לא-מסווג</div></div></div>')
    if blockers:
        h.append("<h3>החוסמים, לפי סדר-מזהה</h3><ul class=\"blockers\">")
        for t in blockers:
            first = re.sub(r"[*`]", "", t["desc"]).strip()
            first = re.split(r"(?<=[.。])\s", first)[0][:150] or "(אין תיאור)"
            h.append('<li><span class="bid">' + html.escape(t["id"])
                     + '</span><span class="bt">' + html.escape(first)
                     + "</span>" + owner_html(t["owner"]) + "</li>")
        h.append("</ul>")
    h.append("</section>")

    # ── פתוח ──
    h.append('<section><div class="shead"><h2>פתוח</h2>'
             '<span class="note">מיון: חומרה 🔴→🟠→🟡→🔵 ואז מזהה</span></div>')
    h.append(_open_table(op, idx, dupes) if op
             else '<p class="archive-note">אין פריטים פתוחים בלוג.</p>')
    h.append("</section>")

    # ── בוצע ──
    h.append('<section><div class="shead"><h2>בוצע</h2>'
             '<span class="note">' + str(ARCHIVE_AFTER_DAYS)
             + " הימים האחרונים · מיון: תאריך יורד</span></div>")
    h.append(_done_table(dn, idx, dupes) if dn
             else '<p class="archive-note">לא נסגר פריט בשבוע האחרון.</p>')
    h.append("</section>")

    # ── מאורכב ──
    h.append('<section><div class="shead"><h2>מאורכב</h2>'
             '<span class="note">✅ מעל ' + str(ARCHIVE_AFTER_DAYS)
             + " ימים, או במדור-הסגורים של הלוג</span></div>"
             '<p class="archive-note">מקופל כברירת-מחדל — נשמר כדי שהאינדקס '
             "יהיה מלא, לא כדי שייקרא כל יום.</p>")
    if ar:
        h.append("<details><summary>הצג " + str(len(ar))
                 + " פריטים מאורכבים</summary><div style=\"margin-top:12px\">"
                 + _done_table(ar, idx, dupes) + "</div></details>")
    else:
        h.append('<p class="archive-note">אין פריטים מאורכבים.</p>')
    h.append("</section>")

    # ── לא-מסווג ──
    if un:
        h.append('<section><div class="shead"><h2>לא-מסווג</h2>'
                 '<span class="note">אין סימן-סטטוס מזוהה בשורה</span></div>'
                 '<p class="archive-note">הפריטים האלה לא נבלעו ולא נוחשו. '
                 "התיקון הוא בלוג עצמו: להוסיף לשורה סימן מ-🔴 🟠 🟡 🔵 ✅.</p>")
        h.append(_open_table([(t, 5, "s-low") for t in un], idx, dupes))
        h.append("</section>")

    h.append(STATIC_SECTIONS)

    h.append('<div class="foot">'
             "הטבלאות <b>פתוח / בוצע / מאורכב</b> נגזרו אוטומטית מ-"
             '<span class="mono">docs/plans/TASK_LOG.md</span>; עמודת-האימות '
             'מצליבה מול <span class="mono">docs/plans/STATUS_BOARD.md</span>. '
             "הפרקים המסומנים <em>נערך-ביד</em> נכתבו ב-29.08 ואינם מתעדכנים "
             'מעצמם. מיוצר ע"י <span class="mono">scripts/gen_readiness_page.py</span>.'
             '<br>עודכן: <span class="mono">' + html.escape(stamp)
             + '</span> · קומיט <span class="mono">' + html.escape(commit)
             + "</span></div>")

    h.append("</div>\n</body>\n</html>\n")
    return "\n".join(h), counts


# ── ריצה ─────────────────────────────────────────────────────────────────

def _il_now() -> _dt.datetime:
    try:
        from zoneinfo import ZoneInfo
        return _dt.datetime.now(ZoneInfo("Asia/Jerusalem"))
    except Exception:
        return _dt.datetime.now()


def _commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="מייצר את תיק-המוכנות מ-TASK_LOG")
    ap.add_argument("--check", action="store_true", help="לא כותב — רק מונים")
    ap.add_argument("--quiet", action="store_true", help="בלי פלט")
    args = ap.parse_args(argv)

    if not TASK_LOG.exists():
        print("gen_readiness_page: אין " + str(TASK_LOG.relative_to(ROOT))
              + " — אין ממה לייצר", file=sys.stderr)
        return 1

    now = _il_now()
    stamp = now.strftime("%Y-%m-%d %H:%M") + " IL"
    board_text = BOARD.read_text(encoding="utf-8", errors="replace") if BOARD.exists() else ""
    page, counts = build(TASK_LOG.read_text(encoding="utf-8", errors="replace"),
                         board_text, stamp, _commit(), now.date())

    if not args.check:
        for p in TARGETS:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(page, encoding="utf-8")

    if not args.quiet:
        print("readiness · פתוח {open} (חוסמים {blockers}) · בוצע-השבוע {done} · "
              "מאורכב {archived} · לא-מסווג {unclassified} · סה\"כ {total}"
              .format(**counts))
        if not args.check:
            for p in TARGETS:
                print("  → " + str(p.relative_to(ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
