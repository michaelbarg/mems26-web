#!/usr/bin/env python3
"""MEMS26 mobile relay — pushes the pocket-monitor snapshot to Render.

07-21 (Michael): mobile link via Render, display-only, trading stays local.
Loop: GET local /api/v9/mobile/data → POST Render /api/v9/mobile/snapshot.
Outbound HTTPS only. Quiet backoff when either side is down. No trading ops.

Run by LaunchAgent com.mems26.mobile_relay. Log: /tmp/mobile_relay.log.
"""
import json
import os
import sys
import time
import urllib.request

ENV_PATH = os.path.expanduser("~/Downloads/mems26_web_git/.env")
LOCAL = "http://localhost:8000/api/v9/mobile/data"
INTERVAL_OK = 5
INTERVAL_BAD = 30


def _env() -> dict:
    out = {}
    try:
        for line in open(ENV_PATH, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.split(" #")[0].strip()
    except Exception as e:
        print(f"[relay] .env read failed: {e}", flush=True)
    return out


def main() -> None:
    env = _env()
    access_key = env.get("MOBILE_ACCESS_KEY", "")
    push_key = env.get("MOBILE_PUSH_KEY", "")
    render = (env.get("RENDER_MOBILE_URL", "") or "").rstrip("/")
    if not (access_key and push_key and render):
        print("[relay] missing MOBILE_ACCESS_KEY/MOBILE_PUSH_KEY/RENDER_MOBILE_URL — exit", flush=True)
        sys.exit(1)
    print(f"[relay] start → {render} (interval {INTERVAL_OK}s)", flush=True)
    fails = 0
    while True:
        try:
            with urllib.request.urlopen(f"{LOCAL}?key={access_key}", timeout=4) as r:
                data = r.read()
            req = urllib.request.Request(
                f"{render}/api/v9/mobile/snapshot", data=data, method="POST",
                headers={"Content-Type": "application/json", "X-Push-Key": push_key})
            with urllib.request.urlopen(req, timeout=15) as r:
                json.loads(r.read().decode())
            if fails:
                print(f"[relay] recovered after {fails} fails", flush=True)
            fails = 0
            time.sleep(INTERVAL_OK)
        except Exception as e:
            fails += 1
            if fails in (1, 5) or fails % 60 == 0:
                print(f"[relay] fail #{fails}: {str(e)[:90]}", flush=True)
            time.sleep(INTERVAL_BAD if fails >= 5 else INTERVAL_OK)


if __name__ == "__main__":
    main()
