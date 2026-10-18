#!/usr/bin/env python3
# T-585 records: TASK_LOG row (top of the cowork table), STATUS_BOARD line, LIVE_CHANNEL block (prepend), INBOX block (prepend)
import io, re, sys
R = "/Users/michael/Downloads/mems26_web_git/"
def rd(p): return io.open(R + p, encoding="utf-8").read()
def wr(p, s): io.open(R + p, "w", encoding="utf-8").write(s)
row = rd("harness_out/t585/row.md").rstrip("\n") + "\n"
tl = rd("docs/plans/TASK_LOG.md")
assert "T-585" not in tl, "T-585 already present"
hdr = "| # | משימה | סטטוס | מי | הצעד הבא |\n|---|---|---|---|---|\n"
i = tl.find(hdr + "| T-574 ")
assert i >= 0, "anchor (T-574 table) not found"
tl = tl[: i + len(hdr)] + row + tl[i + len(hdr):]
wr("docs/plans/TASK_LOG.md", tl)
sb = rd("docs/plans/STATUS_BOARD.md")
if not sb.endswith("\n"): sb += "\n"
wr("docs/plans/STATUS_BOARD.md", sb + rd("harness_out/t585/board.md"))
lc = rd("docs/handoff/LIVE_CHANNEL.md")
wr("docs/handoff/LIVE_CHANNEL.md", rd("harness_out/t585/channel.md") + lc)
ib = rd("docs/handoff/MICHAEL_INBOX.md")
wr("docs/handoff/MICHAEL_INBOX.md", rd("harness_out/t585/inbox.md") + ib)
print("ok: TASK_LOG row inserted, STATUS_BOARD appended, LIVE_CHANNEL + INBOX prepended")
