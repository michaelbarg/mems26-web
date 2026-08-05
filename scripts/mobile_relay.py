#!/usr/bin/env python3
"""MEMS26 mobile relay — pushes snapshot + polls emergency commands from Render.

07-21 (Michael): mobile link via Render, display-only, trading stays local.
08-04 (Michael): emergency commands (FLATTEN/PAUSE/RESUME) via pull-based relay.

Loop every ~5s:
  1. GET local /api/v9/mobile/data → POST Render /api/v9/mobile/snapshot (display)
  2. GET Render /cmd/pending → if command: execute locally → POST Render /cmd/ack

Run by LaunchAgent com.mems26.mobile_relay. Log: /tmp/mobile_relay.log.
"""
import json
import os
import sys
import time
import urllib.request

ENV_PATH = os.path.expanduser("~/Downloads/mems26_web_git/.env")
LOCAL = "http://localhost:8000/api/v9/mobile"
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


def _push_snapshot(access_key, push_key, render):
    """Push local snapshot to Render."""
    with urllib.request.urlopen(f"{LOCAL}/data?key={access_key}", timeout=4) as r:
        data = r.read()
    req = urllib.request.Request(
        f"{render}/api/v9/mobile/snapshot", data=data, method="POST",
        headers={"Content-Type": "application/json", "X-Push-Key": push_key})
    with urllib.request.urlopen(req, timeout=15) as r:
        json.loads(r.read().decode())


def _poll_commands(access_key, render):
    """Poll Render for pending emergency commands and execute locally."""
    try:
        with urllib.request.urlopen(
            f"{render}/cmd/pending?key={access_key}", timeout=5
        ) as r:
            resp = json.loads(r.read().decode())
        cmd = resp.get("cmd")
        if cmd is None:
            return
        action = cmd.get("action", "").upper()
        cmd_id = cmd.get("id")
        print(f"[relay] COMMAND RECEIVED: {action} (id={cmd_id})", flush=True)

        # Execute locally
        ok = _execute_local(action, access_key)

        # ACK to Render (clears queue)
        ack_data = json.dumps({"id": cmd_id}).encode()
        ack_req = urllib.request.Request(
            f"{render}/cmd/ack?key={access_key}",
            data=ack_data, method="POST",
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(ack_req, timeout=5) as r:
            json.loads(r.read().decode())
        print(f"[relay] COMMAND ACK sent (ok={ok})", flush=True)

    except Exception as e:
        # Command polling failures are non-fatal
        if "HTTP Error 401" not in str(e):
            print(f"[relay] cmd poll: {str(e)[:80]}", flush=True)


def _execute_local(action, access_key):
    """Execute command on the local trading machine."""
    try:
        if action == "FLATTEN":
            data = json.dumps({"confirm": "FLATTEN"}).encode()
            req = urllib.request.Request(
                f"{LOCAL}/flatten?key={access_key}",
                data=data, method="POST",
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as r:
                resp = json.loads(r.read().decode())
            print(f"[relay] FLATTEN result: {resp}", flush=True)
            return resp.get("ok", False)

        elif action == "PAUSE":
            data = json.dumps({"confirm": "PAUSE"}).encode()
            req = urllib.request.Request(
                f"{LOCAL}/pause?key={access_key}",
                data=data, method="POST",
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as r:
                resp = json.loads(r.read().decode())
            print(f"[relay] PAUSE result: {resp}", flush=True)
            return resp.get("ok", False)

        elif action == "RESUME":
            data = json.dumps({"confirm": "RESUME"}).encode()
            req = urllib.request.Request(
                f"{LOCAL}/resume?key={access_key}",
                data=data, method="POST",
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as r:
                resp = json.loads(r.read().decode())
            print(f"[relay] RESUME result: {resp}", flush=True)
            return resp.get("ok", False)

        else:
            print(f"[relay] unknown action: {action}", flush=True)
            return False

    except Exception as e:
        print(f"[relay] local exec failed: {str(e)[:80]}", flush=True)
        return False


def main() -> None:
    env = _env()
    access_key = env.get("MOBILE_ACCESS_KEY", "")
    push_key = env.get("MOBILE_PUSH_KEY", "")
    render = (env.get("RENDER_MOBILE_URL", "") or "").rstrip("/")
    if not (access_key and push_key and render):
        print("[relay] missing MOBILE_ACCESS_KEY/MOBILE_PUSH_KEY/RENDER_MOBILE_URL — exit", flush=True)
        sys.exit(1)
    print(f"[relay] start → {render} (interval {INTERVAL_OK}s, cmd relay enabled)", flush=True)
    fails = 0
    while True:
        try:
            _push_snapshot(access_key, push_key, render)
            if fails:
                print(f"[relay] recovered after {fails} fails", flush=True)
            fails = 0
        except Exception as e:
            fails += 1
            if fails in (1, 5) or fails % 60 == 0:
                print(f"[relay] fail #{fails}: {str(e)[:90]}", flush=True)

        # Poll commands from Render (even if snapshot push failed)
        _poll_commands(access_key, render)

        time.sleep(INTERVAL_BAD if fails >= 5 else INTERVAL_OK)


if __name__ == "__main__":
    main()
