# -*- coding: utf-8 -*-
"""fix-agent 09.10 — final handoff edits: LIVE_CHANNEL cross-check entry + T-567 next-step note (idempotent)."""
import io, sys
LC = "/Users/michael/Downloads/mems26_web_git/docs/handoff/LIVE_CHANNEL.md"
TL = "/Users/michael/Downloads/mems26_web_git/docs/plans/TASK_LOG.md"

E3 = ("🔵 **[fix-agent · תור-הלילה · 09.10 00:45 IL · אימות-צולב לשבעת הווריאנטים של cowork מול t567ref — אף אחד לא עובר §2ד; שורה לכל אחד באינבוקס ל-08:30]** "
    "התור (`run_night.sh`, pid 95999, 23:07–00:37) רץ פעם אחת — לא הרצתי כפול (`ps aux | grep fwd_harness`, `tail night.out`); אימתתי מהפלטים באותם סקריפטים "
    "(`harness_out/t579/crosscheck.out`): **t567a** −76.95 נטו · 06 −115 ✗ · **t567c9** −877.75 · החזקה −48.75 ✗ · **t571b** −8.65 · החזקה +121.25 · 09 −264 ✗ · "
    "**t571a** −25.30 · 07 −84 ✗ · **t566c** +222.50 · החזקה +24.40 · 07 −144 · 10 −162 ✗ (הקרוב ביותר; רק כסטייה בכתב) · **t567b** −169.60 · החזקה −60.60 ✗ · "
    "**t567c6** −1,206.00 · החזקה −238.10 ✗. הסתייגות-מדידה ל-Cursor: `cmp_vs_live` (P&L-יומי) מול `holdout.py` (Σ pnl_usd) נבדלים בווריאנטי-שחרור-הסלוט "
    "(c9 7.5$ · c6 127$ · t571b 8$) — אותו פסק-דין. `doctrine_cells_t567ref.md` נוצר 00:37. הבקאנד pid 85469 כל הלילה; אפס נגיעה בלייב.\n\n")

T567_ADD = (" **אימות-צולב fix-agent 09.10 00:45:** שבעת הווריאנטים של התור (t567a/c9/c6/b, t571a/b, t566c) מול t567ref — אף אחד לא עובר §2ד "
    "(`harness_out/t579/crosscheck.out`, שורות-פסיקה באינבוקס 09.10); t566c הקרוב ביותר (+222.50 נטו, החזקה +24.40, 07 −144 · 10 −162).")

s = io.open(LC, encoding="utf-8").read()
if "[fix-agent · תור-הלילה · 09.10" not in s:
    io.open(LC, "w", encoding="utf-8").write(E3 + s); print("LIVE_CHANNEL: prepended cross-check entry")
else:
    print("LIVE_CHANNEL: already")
t = io.open(TL, encoding="utf-8").read()
if "אימות-צולב fix-agent 09.10 00:45" not in t:
    lines = t.split("\n"); done = False
    for i, ln in enumerate(lines):
        if ln.startswith("| T-567 |") and not done:
            assert ln.rstrip().endswith("|"); lines[i] = ln.rstrip()[:-1].rstrip() + T567_ADD + " |"; done = True
    assert done
    io.open(TL, "w", encoding="utf-8").write("\n".join(lines)); print("TASK_LOG: T-567 cell appended")
else:
    print("TASK_LOG: already")
