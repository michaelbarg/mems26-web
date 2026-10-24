#!/usr/bin/env python3
# read-only: dump phone-thread messages in the audit window, Michael's first
import json, sys, collections
src = "docs/handoff/PHONE_THREAD.jsonl"
lo = sys.argv[1] if len(sys.argv) > 1 else "2026-10-16T21:00"
mode = sys.argv[2] if len(sys.argv) > 2 else "michael"
W = int(sys.argv[3]) if len(sys.argv) > 3 else 1500
keys = collections.Counter()
senders = collections.Counter()
rows = []
with open(src, encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception as e:
            print("BAD", i, e)
            continue
        for k in d.keys():
            keys[k] += 1
        s = str(d.get("sender", d.get("author", "?")))
        senders[s] += 1
        rows.append((i, d))
if mode == "keys":
    print(keys.most_common())
    print(senders.most_common())
    sys.exit()
for i, d in rows:
    ts = str(d.get("ts", ""))
    if ts < lo:
        continue
    s = str(d.get("sender", ""))
    a = str(d.get("author", ""))
    is_m = s in ("מייקל", "michael", "Michael") or a.lower() == "michael"
    if mode == "michael" and not is_m:
        continue
    txt = str(d.get("text", d.get("message", d.get("body", ""))))
    print(f"--- L{i} ts={ts} sender={s} author={a} id={d.get('id','')} status={d.get('status','')} len={len(txt)}")
    print(txt[:W])
