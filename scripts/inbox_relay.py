#!/usr/bin/env python3
"""INBOX relay — polls Render for Michael's instructions, writes to MICHAEL_INBOX.md.

Runs locally, pulls from the Render relay, appends to the inbox file.
The local agents (cc/cowork) read the inbox at session start.

Usage: python3 scripts/inbox_relay.py [--once] [--interval 30]
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INBOX = ROOT / "docs" / "handoff" / "MICHAEL_INBOX.md"
RELAY_URL = os.getenv("MOBILE_RELAY_URL", "https://mems26-mobile.onrender.com")
ACCESS_KEY = os.getenv("MOBILE_ACCESS_KEY", "")
IL = ZoneInfo("Asia/Jerusalem")


def _ensure_inbox():
    if not INBOX.exists():
        INBOX.write_text("# MICHAEL INBOX\n\nהוראות ממייקל — טקסט למעקב, לא פקודות מסחר.\n\n")


def poll_and_write(once=False):
    """Poll Render for pending instructions, write to MICHAEL_INBOX.md."""
    import urllib.request
    import urllib.error

    url = f"{RELAY_URL}/instruction/pending?key={ACCESS_KEY}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f"Poll failed: {e}", file=sys.stderr)
        return 0

    items = data.get("items", [])
    if not items:
        return 0

    _ensure_inbox()
    written = 0
    for item in items:
        if item["status"] == "done":
            continue
        now_il = dt.datetime.now(IL)
        entry = (f"### [{now_il.strftime('%Y-%m-%d %H:%M')} IL] מייקל (מהפלאפון)\n"
                 f"{item['text']}\n"
                 f"*סטטוס: {item['status']} · ID: {item['id']}*\n\n")
        with open(INBOX, "a", encoding="utf-8") as f:
            f.write(entry)
        written += 1

        # Mark as in_progress
        try:
            ack_url = f"{RELAY_URL}/instruction/status?key={ACCESS_KEY}"
            ack_data = json.dumps({"id": item["id"], "status": "in_progress"}).encode()
            ack_req = urllib.request.Request(ack_url, data=ack_data,
                                             headers={"Content-Type": "application/json"},
                                             method="POST")
            urllib.request.urlopen(ack_req, timeout=10)
        except Exception:
            pass

    if written:
        print(f"Wrote {written} instructions to {INBOX}")
    return written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=int, default=30)
    args = ap.parse_args()

    if args.once:
        poll_and_write(once=True)
        return

    print(f"Polling {RELAY_URL} every {args.interval}s...")
    while True:
        poll_and_write()
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
