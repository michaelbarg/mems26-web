# -*- coding: utf-8 -*-
"""fix-agent 18.10 11:3x — second ID collision of the morning: cowork took T-588 at 10:59:40 (39f7f1c8,
CLS_RESULT_SESSION_GUARD_V1) while this run's item was being written as T-588 (grep at 10:50 was clean).
Renumber ONLY this run's ZLR-permit item to T-589, file by file, leaving every other agent's T-588 alone.
Idempotent (refuses when nothing is left to change)."""
import io, os, sys
ROOT = "/Users/michael/Downloads/mems26_web_git"; os.chdir(ROOT)
def sub(path, pairs):
    s = io.open(path, encoding="utf-8").read(); n = 0
    for a, b in pairs:
        c = s.count(a); n += c; s = s.replace(a, b)
    io.open(path, "w", encoding="utf-8").write(s); print("%s: %d replacements" % (path, n)); return n
total = 0
# the report (renamed by the shell before this runs)
total += sub("docs/reports/T589_ALLOW_ZLR_SHORT_NORMAL_1819_2026-10-18.md",
             [("# T-588 ·", "# T-589 ·"), ("**מזהה:** T-588 —", "**מזהה:** T-589 —"),
              ("המזהה שלי הוחלף ל-T-588", "המזהה שלי הוחלף ל-T-589 (ושוב: cowork לקח גם את T-588 ב-10:59, קומיט 39f7f1c8)"),
              ("T588_ALLOW", "T589_ALLOW")])
total += sub("config/decision_tree_v3.t587_allow.yaml", [("T-588", "T-589")])
for f in ("make_variant_zlr.py", "zlr_vectors.py", "run.sh", "run2.sh", "two_holdouts.py", "task_log_edit.py",
          "live_channel_entries.py", "inbox_entry.py"):
    total += sub("harness_out/t587/" + f, [("T-588", "T-589"), ("T588_ALLOW", "T589_ALLOW")])
# TASK_LOG: my row + my header line only (anchored strings)
total += sub("docs/plans/TASK_LOG.md",
             [("| T-588 | 🔵 **היתר ZLR SHORT", "| T-589 | 🔵 **היתר ZLR SHORT"),
              ("מזהה: T-588 (תג-ההרנס t587* הוקצה 10:03; cowork-dev לקח T-587 ב-10:18)",
               "מזהה: T-589 (תג-ההרנס t587* הוקצה 10:03; cowork-dev לקח T-587 ב-10:18 ו-cowork את T-588 ב-10:59 — שתי התנגשויות באותו בוקר)"),
              ("T-588 היתר ZLR SHORT/Normal/18–19h לבדו", "T-589 היתר ZLR SHORT/Normal/18–19h לבדו"),
              ("T588_ALLOW", "T589_ALLOW")])
# LIVE_CHANNEL: my entry header + my report path only
total += sub("docs/handoff/LIVE_CHANNEL.md", [("[fix-agent · T-588 ·", "[fix-agent · T-589 ·"), ("T588_ALLOW", "T589_ALLOW")])
# INBOX: my line only
total += sub("docs/handoff/MICHAEL_INBOX.md", [("T-588, BRIEF §2.2 #3", "T-589, BRIEF §2.2 #3")])
print("total", total)
sys.exit(0 if total else 1)
