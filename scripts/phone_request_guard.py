#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Requests Michael sent from the phone that no task log ever recorded. (T-208)

Twice now a request typed into the phone thread has vanished:

    T-167  "בקשתי גם גרף קטן פה"                    — never opened as a task
    T-208  three notes on the trade card (IMG_3375) — `grep IMG_3375` on the
           task log returns 0

The failure is not forgetfulness. It is that **no route exists** from the phone
thread to `docs/plans/TASK_LOG.md`. A message arrives, an agent answers it in
conversation, the conversation ends, and the request is gone. Nothing in the
system can tell that it happened.

And note how the last search failed: phone-Claude grepped for IMG_3375, the
image NAME. Every message in the thread already carries a stable `id`; content
is not a key and never was. This guard uses the id.

## The rule

Every message from מייקל that reads as a request must be DISPOSITIONED — its
`id` cited either

  * in `docs/plans/TASK_LOG.md` (it became a task), or
  * in `docs/handoff/PHONE_DISPOSITION.md` (answered in conversation, declined,
    duplicate — with the one-line reason)

Both are cheap. Neither is optional. An `-ack` reply in the thread is RECEIPT,
not disposition: "✓ התקבל · סוכן יענה בהרחבה" is exactly what the two lost
requests received.

## What this deliberately does not do

It does not create tasks. A guard that files tasks by keyword would fill the log
with noise and make the real ones harder to see — and the log is the single
source of truth for what is open. It reports; a human dispositions.

Nor can it judge whether something IS a request. It uses Hebrew request markers,
so it over-reports rather than under-reports: a false positive costs one line in
the disposition file, a false negative costs another lost request.

    python3 scripts/phone_request_guard.py
    python3 scripts/phone_request_guard.py --days 14 --strict
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREAD = os.path.join(ROOT, "docs", "handoff", "PHONE_THREAD.jsonl")
TASK_LOG = os.path.join(ROOT, "docs", "plans", "TASK_LOG.md")
DISPO = os.path.join(ROOT, "docs", "handoff", "PHONE_DISPOSITION.md")

# Hebrew request markers. Over-inclusive on purpose — see the docstring.
MARKERS = (
    "אני רוצה", "רוצה ש", "תבנה", "תתקן", "בקשתי", "מבקש", "צריך ש",
    "תוסיף", "תעשה", "תכין", "תשנה", "תסדר", "אפשר ש", "למה לא",
    "חסר", "לא עובד", "לא רואה", "תבדוק", "תדאג",
)

# Pure acknowledgements and one-word approvals are not requests.
NOT_A_REQUEST = {"מאשר", "מאשר ומאשר", "כן", "לא", "תמשיך", "אוקיי", "ok", "תודה"}


def load_thread():
    if not os.path.exists(THREAD):
        sys.exit(f"missing {THREAD}")
    out = []
    for ln in open(THREAD, encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 when anything is undispositioned")
    a = ap.parse_args()

    rows = load_thread()
    if not rows:
        sys.exit("thread parsed to zero rows — refusing to report 'all clear'")

    log = open(TASK_LOG, encoding="utf-8").read() if os.path.exists(TASK_LOG) else ""
    dispo = open(DISPO, encoding="utf-8").read() if os.path.exists(DISPO) else ""
    if not log:
        sys.exit("TASK_LOG.md unreadable — a green report here would be a lie")

    cutoff = datetime.now(timezone.utc) - timedelta(days=a.days)
    pending, done = [], 0

    for r in rows:
        if r.get("sender") != "מייקל":
            continue
        text = (r.get("text") or "").strip()
        rid = r.get("id") or ""
        if not rid or text in NOT_A_REQUEST or len(text) < 8:
            continue
        if not any(m in text for m in MARKERS):
            continue
        try:
            ts = datetime.fromisoformat(str(r["ts"]).replace("Z", "+00:00"))
        except Exception:
            continue
        if ts < cutoff:
            continue
        if rid in log or rid in dispo:
            done += 1
        else:
            pending.append((ts, rid, text, bool(r.get("att"))))

    print(f"\n{'='*80}")
    print(f" Phone requests from מייקל, last {a.days} days — is each one recorded?")
    print(f"{'='*80}")
    print(f" dispositioned: {done}    undispositioned: {len(pending)}")

    if pending:
        print(f"\n 🔴 no task and no disposition — cite the id in TASK_LOG.md or")
        print(f"    add one line to docs/handoff/PHONE_DISPOSITION.md:\n")
        for ts, rid, text, att in sorted(pending):
            age = (datetime.now(timezone.utc) - ts).total_seconds() / 3600.0
            flag = " 📎" if att else ""
            print(f"   [{rid}] {ts:%m-%d %H:%M}Z  ({age:.0f}h ago){flag}")
            print(f"          {text[:110]}")
    else:
        print("\n ✅ every request in the window is either a task or dispositioned")

    print(f"""
 An -ack in the thread is RECEIPT, not disposition. "✓ התקבל · סוכן יענה
 בהרחבה" is precisely what T-167 and T-208 received before they were lost.
 The id is the key — content is not. `grep IMG_3375` returning 0 is what
 made this guard necessary.
{'='*80}
""")
    return 1 if (pending and a.strict) else 0


if __name__ == "__main__":
    raise SystemExit(main())
