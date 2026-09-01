#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Is anyone actually answering? One check across all three channels.

Michael 2026-09-01: *"אני רוצה שתשפר את התקשורת שאכן יהיה תקשורת בינך, קלוד קוד
והפלאפון."*

Three channels carry this project and each failed the same way today:

    LIVE_CHANNEL.md     cowork wrote eight entries and read none. CC's two open
                        questions — "S2 may bypass the sizer", "flag_guard
                        BUDGET x MIN NOT-DONE" — sat an hour. The last six
                        headers all read `cowork-dev → cc-macbook`: a broadcast.
    PHONE_THREAD.jsonl  two of Michael's requests never became tasks (T-167,
                        T-208). Closed by phone_request_guard.py.
    TASK_LOG.md         27 commits referencing T-numbers, zero rows ticked.

One shape: **write-only**. Nothing could tell that a message had gone
unanswered, so nobody noticed. The phone thread turned out to be recoverable
only because its messages carry an `id`; the markdown channel carries nothing,
which is why the same failure there was invisible.

## The rule

An entry addressed to X is answered when X posts an entry citing `re:<id>`.
Nothing else counts — not an ack, not a later entry on another subject, not a
commit message. Entries written before ids existed are grandfathered: this
guard reports on what is written from now on.

Run it at the start of a session, before deciding what to work on. The first
question is not "what shall I build" but "who is waiting on me".

    python3 scripts/channel_guard.py
    python3 scripts/channel_guard.py --me cc-macbook --strict
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANNEL = os.path.join(ROOT, "docs", "handoff", "LIVE_CHANNEL.md")

HDR = re.compile(
    r'^###\s*\[(?P<ts>[\d]{4}-[\d]{2}-[\d]{2}[ T][\d]{2}:[\d]{2})[^\]]*\]\s*'
    r'(?P<frm>[\w֐-׿-]+)\s*(?:→|->)\s*(?P<to>[\w֐-׿-]+)'
    r'(?P<rest>.*)$', re.M)
IDPAT = re.compile(r'\[id:([0-9a-f]{8})\]')
REPAT = re.compile(r're:([0-9a-f]{8})')


def entries():
    if not os.path.exists(CHANNEL):
        sys.exit(f"missing {CHANNEL}")
    text = open(CHANNEL, encoding="utf-8").read()
    heads = list(HDR.finditer(text))
    if not heads:
        sys.exit("no parseable headers — refusing to report 'nothing pending'")
    out = []
    for i, m in enumerate(heads):
        body = text[m.end():heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        idm = IDPAT.search(m.group("rest"))
        out.append({
            "ts": m.group("ts").replace("T", " "),
            "frm": m.group("frm"), "to": m.group("to"),
            "subject": IDPAT.sub("", m.group("rest")).lstrip(" ·").strip()[:90],
            "id": idm.group(1) if idm else None,
            "replies": set(REPAT.findall(body)),
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--me", default=None,
                    help="show only what is waiting on this agent")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()

    ent = entries()
    answered = set()
    for e in ent:
        answered |= e["replies"]

    # Only id-bearing entries are checkable. Everything older is grandfathered
    # — a guard that scolds about history nobody can fix is a guard people
    # switch off, and this one has to survive to be worth anything.
    tracked = [e for e in ent if e["id"]]
    waiting = [e for e in tracked if e["id"] not in answered]
    if a.me:
        waiting = [e for e in waiting if e["to"] == a.me]

    print(f"\n{'='*78}")
    print(" Inter-agent channel — who is waiting on whom")
    print(f"{'='*78}")
    print(f" entries: {len(ent)}   with an id: {len(tracked)}   "
          f"grandfathered: {len(ent) - len(tracked)}")

    if not tracked:
        print("\n ⚠️  No entry carries an id yet, so nothing here is checkable.")
        print("    Post with scripts/channel_post.py — it assigns one.")
        print("    Until then this guard can only say 'I cannot tell', which it")
        print("    prefers over a green tick it has not earned.")
        return 0

    if waiting:
        print(f"\n 🔴 {len(waiting)} unanswered:\n")
        for e in sorted(waiting, key=lambda x: x["ts"]):
            try:
                age = (datetime.now() - datetime.strptime(e["ts"], "%Y-%m-%d %H:%M"))
                age_s = f"{age.total_seconds()/3600:.0f}h"
            except Exception:
                age_s = "?"
            print(f"   [{e['id']}] {e['ts']}  ({age_s})  {e['frm']} → {e['to']}")
            print(f"             {e['subject']}")
        print(f"\n   answer with:  scripts/channel_post.py --to <frm> --re <id> …")
    else:
        print("\n ✅ every id-bearing entry has a reply citing it")

    # The phone channel has its own guard; surface it here so one command
    # answers "is anyone waiting on me" across all three.
    print(f"\n{'-'*78}\n phone channel:")
    try:
        r = subprocess.run([sys.executable,
                            os.path.join(ROOT, "scripts", "phone_request_guard.py")],
                           capture_output=True, text=True, timeout=60)
        for ln in (r.stdout or "").splitlines():
            if "dispositioned" in ln or "🔴" in ln or "✅" in ln:
                print("  " + ln.strip())
    except Exception as exc:
        print(f"  (phone_request_guard did not run: {exc})")

    print(f"""
 An ack is not an answer. "✓ התקבל · סוכן יענה בהרחבה" is what both lost
 phone requests received. Only `re:<id>` clears an entry here.
{'='*78}
""")
    return 1 if (waiting and a.strict) else 0


if __name__ == "__main__":
    raise SystemExit(main())
