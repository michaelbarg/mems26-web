#!/usr/bin/env python3
"""MICHAEL_INBOX — append a text entry to the inbox for Michael's review.

This is a tracking tool, not a command interface. Entries are
informational — status updates, questions, findings.

Usage: python3 scripts/inbox_update.py "message text"
"""
import datetime as dt
import os
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

INBOX = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "docs" / "MICHAEL_INBOX.md"
ET = ZoneInfo("America/New_York")
IL = ZoneInfo("Asia/Jerusalem")


def append(message: str, source: str = "cc-macbook"):
    now_il = dt.datetime.now(IL)
    now_et = dt.datetime.now(ET)
    entry = (f"### [{now_il.strftime('%Y-%m-%d %H:%M')} IL / "
             f"{now_et.strftime('%H:%M')} ET] {source}\n{message}\n\n")
    if not INBOX.exists():
        INBOX.write_text("# MICHAEL INBOX\n\nטקסט למעקב — לא פקודות.\n\n")
    with open(INBOX, "a", encoding="utf-8") as f:
        f.write(entry)
    print(f"Added to {INBOX}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/inbox_update.py 'message'")
        sys.exit(1)
    append(" ".join(sys.argv[1:]))
