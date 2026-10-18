#!/usr/bin/env python3
# T-586 package records: TASK_LOG rows (top of the cowork table, after T-587), STATUS_BOARD line, LIVE_CHANNEL block (prepend), INBOX block (prepend)
import io, sys
R = "/Users/michael/Downloads/mems26_web_git/"
def rd(p): return io.open(R + p, encoding="utf-8").read()
def wr(p, s): io.open(R + p, "w", encoding="utf-8").write(s)
rows = rd("harness_out/t586/row_t586.md").rstrip("\n") + "\n"
tl = rd("docs/plans/TASK_LOG.md")
for t in ("T-586 |", "T-588 |", "T-590 |", "T-591 |"):
    assert ("| " + t) not in tl, t + " already present"
hdr = "| # | משימה | סטטוס | מי | הצעד הבא |\n|---|---|---|---|---|\n"
i = tl.find(hdr + "| T-587 ")
assert i >= 0, "anchor (T-587 at the top of the cowork table) not found"
tl = tl[: i + len(hdr)] + rows + tl[i + len(hdr):]
wr("docs/plans/TASK_LOG.md", tl)
sb = rd("docs/plans/STATUS_BOARD.md")
if not sb.endswith("\n"): sb += "\n"
wr("docs/plans/STATUS_BOARD.md", sb + rd("harness_out/t586/board.md"))
wr("docs/handoff/LIVE_CHANNEL.md", rd("harness_out/t586/channel.md") + "\n" + rd("docs/handoff/LIVE_CHANNEL.md"))
wr("docs/handoff/MICHAEL_INBOX.md", rd("harness_out/t586/inbox.md") + rd("docs/handoff/MICHAEL_INBOX.md"))
print("ok: 4 TASK_LOG rows inserted, STATUS_BOARD appended, LIVE_CHANNEL + INBOX prepended")
