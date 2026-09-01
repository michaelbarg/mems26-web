#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Post to the inter-agent channel with an id, so a reply can cite it.

Michael 2026-09-01: *"אני רוצה שתשפר את התקשורת שאכן יהיה תקשורת בינך, קלוד קוד
והפלאפון."*

The three channels are not equally usable, and today showed exactly why:

    PHONE_THREAD.jsonl    every message carries an `id`  → a guard can ask
                          "was this ever answered?" and get a real answer
    LIVE_CHANNEL.md       free-form markdown, no ids     → nothing can

So CC's two open questions ("S2 may bypass the sizer", "flag_guard check
NOT-DONE") sat for an hour while cowork appended six more entries above them.
Not malice and not forgetfulness — there was no way to notice. The last six
headers in the channel all read `cowork-dev → cc-macbook`: a broadcast, not a
conversation.

This tool gives channel entries the one thing the phone thread already had.

    channel_post.py --to cc-macbook --subject "FIX-8 verified" --body-file b.md
    channel_post.py --to cc-macbook --subject "..." --re a1b2c3d4 < body.md

`--re` marks the new entry as a reply to that id, which is what clears it in
`channel_guard.py`. Replying without `--re` is not a reply — it is another
broadcast, and the guard will keep asking.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANNEL = os.path.join(ROOT, "docs", "handoff", "LIVE_CHANNEL.md")

AGENTS = ("cowork-dev", "cc-macbook", "cc-imac", "phone-claude", "מייקל")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", required=True, choices=AGENTS)
    ap.add_argument("--frm", default="cowork-dev", choices=AGENTS)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--re", dest="reply_to", default=None,
                    help="id of the entry this answers — what clears the guard")
    ap.add_argument("--body-file", default=None,
                    help="file with the body; omit to read stdin")
    a = ap.parse_args()

    body = (open(a.body_file, encoding="utf-8").read() if a.body_file
            else sys.stdin.read())
    if not body.strip():
        sys.exit("empty body — refusing to post a header with nothing under it")

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    eid = hashlib.sha1(f"{ts}{a.frm}{a.to}{a.subject}".encode()).hexdigest()[:8]

    parts = [f"\n---\n### [{ts}] {a.frm} → {a.to} · [id:{eid}] {a.subject}\n"]
    if a.reply_to:
        parts.append(f"**re:{a.reply_to}**\n\n")
    parts.append(body.rstrip() + f"\n\n— {a.frm}\n")

    with open(CHANNEL, "a", encoding="utf-8") as fh:
        fh.write("".join(parts))

    print(f"posted [id:{eid}] → {a.to}"
          + (f"  (re:{a.reply_to})" if a.reply_to else ""))
    print(f"the addressee clears it with:  --re {eid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
