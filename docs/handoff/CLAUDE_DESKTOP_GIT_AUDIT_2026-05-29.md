# Git Audit Prompt — Claude Desktop Code

**Project:** `/Users/michael/Downloads/mems26_web_git`
**Date:** 2026-05-29
**Mode:** READ-ONLY AUDIT — no commits, no pushes, no resets

---

## Instructions

Open this project in Claude Desktop and paste the prompt below.
Set permission mode to `plan` (Shift+Tab) for safe read-only exploration.

---

## Prompt — paste this into Claude Desktop

```
You are auditing the git state of the MEMS26 trading system.
Working directory: /Users/michael/Downloads/mems26_web_git

Run these commands and summarize findings in Hebrew.
Do NOT make any changes — read-only audit.

### Part 1 — Branch & Remote State

git branch -a
git remote -v
git rev-list --left-right --count origin/stabilize/mems26-local-truth-2026-05-16...HEAD
git log --oneline -25

Questions to answer:
- מה הבראנץ' הפעיל?
- כמה קומיטים קדימה מה-remote?
- האם יש בראנצ'ים לא ממורג'ים שצריך לנקות?
- מה 10 הקומיטים האחרונים ומה הם עשו?

### Part 2 — Working Tree Cleanliness

git status
git diff --stat HEAD
git stash list
git ls-files --others --exclude-standard

Questions to answer:
- האם יש שינויים שלא נעשה להם commit?
- מה הקבצים ה-untracked? האם הם צריכים commit או .gitignore?
- האם יש stashes ישנים?

### Part 3 — Recent Activity Analysis

git log --oneline --since="2026-05-25" --all
git log --format="%h %ad %s" --date=short --since="2026-05-20"

Questions to answer:
- מה קצב העבודה ב-10 ימים האחרונים?
- האם יש קומיטים גדולים שצריך לבדוק (batch commits)?
- האם יש קומיטים מסוג "fix" אחרי קומיטים מסוג "feat" — סימן לבאגים?

### Part 4 — File Hygiene

git ls-files | grep -E "\.pyc$|__pycache__|\.env|\.DS_Store|node_modules"
git log --diff-filter=D --name-only --since="2026-05-20" | head -30
find . -name "*.pyc" -o -name "__pycache__" 2>/dev/null | head -10

Questions to answer:
- האם יש קבצים שלא צריכים להיות בגיט?
- האם נמחקו קבצים לאחרונה שצריך לדעת עליהם?

### Part 5 — Safety Check

git log --oneline --all | wc -l
du -sh .git
git count-objects -v

Questions to answer:
- מה גודל הריפו?
- האם יש אובייקטים גדולים שמנפחים את ה-.git?

### Output Format

Write a summary in Hebrew with this structure:

## סיכום מצב Git — MEMS26
**תאריך:** 2026-05-29
**בראנץ':** [active branch]
**HEAD:** [short hash]

### מצב כללי
[1-2 שורות — בריא/צריך טיפול/דחוף]

### שינויים ממתינים
[טבלה של קבצים modified/untracked + המלצה: commit/ignore/delete]

### היסטוריית עבודה (שבוע אחרון)
[סיכום הקומיטים + דפוסים]

### בעיות שנמצאו
[רשימה ממוספרת, או "לא נמצאו בעיות"]

### המלצות
[1-3 פעולות מומלצות בסדר עדיפות]
```
