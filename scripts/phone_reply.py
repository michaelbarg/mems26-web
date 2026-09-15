#!/usr/bin/env python3
"""phone_reply.py — append an agent reply to the durable phone thread.

Usage: python3 scripts/phone_reply.py <sender> "<text>"
Writes docs/handoff/PHONE_THREAD.jsonl (the source of truth the relay pushes
to Render every cycle) and best-effort POSTs /reply for instant display.
Display-only; never touches trading.

{NOW} token (added 08.09, cowork): any occurrence of {NOW} in <text> is replaced
at SEND time with the local wall clock (HH:MM). Agents compose the message body
before the send call and had been estimating "נמדד HH:MM" forward by a few
minutes — it happened three times in two days (07.09 15:50, 07.09 19:15,
08.09 11:09). Writing "נמדד {NOW}" makes the stamp a measurement instead of a
guess. No behaviour change when the token is absent.
"""
import json, os, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "docs", "handoff", "PHONE_THREAD.jsonl")

def main():
    # Switch guard (added 15.09, cowork). `text = argv[-1]` means ANY single
    # argument becomes the message body — so `phone_reply.py --help` SENDS the
    # word "--help" to Michael's phone instead of printing usage. That happened
    # three times: 03.09 09:15, 04.09 15:44, 15.09 15:09 (all three are in
    # PHONE_THREAD.jsonl / the Render feed; Render has no delete endpoint, and a
    # correction message is itself a phone-rule violation). A bare switch token
    # is never a real message, so refuse it and print the docstring instead.
    argv = sys.argv[1:]
    if not argv or argv[-1].strip() in ("-h", "--help", "help", "-?", "/?"):
        sys.exit(__doc__)
    sender = argv[0] if len(argv) > 1 else "cowork"
    text = argv[-1].strip()
    if not text:
        sys.exit("empty text")
    if text.startswith("-") and not text[1:].strip().startswith(" ") and len(text.split()) == 1:
        sys.exit(f"refusing to send bare switch token {text!r} as a message body\n{__doc__}")
    # Stamp the clock at send time, not at compose time (see module docstring).
    text = text.replace("{NOW}", time.strftime("%H:%M", time.localtime()))
    item = {"sender": sender, "text": text,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "status": ""}
    with open(P, "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
    key = ""
    try:
        for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
            if line.startswith("MOBILE_ACCESS_KEY="):
                key = line.split("=", 1)[1].strip()
    except Exception:
        pass
    if key:
        try:
            req = urllib.request.Request(
                f"https://mems26-mobile.onrender.com/reply?key={key}",
                data=json.dumps({"sender": sender, "text": text}).encode(),
                method="POST", headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10).read()
        except Exception:
            pass
    print("ok")

if __name__ == "__main__":
    main()
