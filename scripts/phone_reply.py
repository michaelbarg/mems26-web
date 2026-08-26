#!/usr/bin/env python3
"""phone_reply.py — append an agent reply to the durable phone thread.

Usage: python3 scripts/phone_reply.py <sender> "<text>"
Writes docs/handoff/PHONE_THREAD.jsonl (the source of truth the relay pushes
to Render every cycle) and best-effort POSTs /reply for instant display.
Display-only; never touches trading.
"""
import json, os, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "docs", "handoff", "PHONE_THREAD.jsonl")

def main():
    sender = sys.argv[1] if len(sys.argv) > 2 else "cowork"
    text = sys.argv[-1].strip()
    if not text:
        sys.exit("empty text")
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
