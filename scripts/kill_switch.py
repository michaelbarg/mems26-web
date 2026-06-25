#!/usr/bin/env python3
"""Kill-switch CLI — engage/disengage/status via the backend API.

Usage:
  python3 scripts/kill_switch.py engage [reason]
  python3 scripts/kill_switch.py disengage
  python3 scripts/kill_switch.py status
"""
import json
import sys
import urllib.request

BASE = "http://localhost:8000"


def main():
    if len(sys.argv) < 2:
        print("Usage: kill_switch.py engage|disengage|status [reason]")
        sys.exit(1)

    action = sys.argv[1].lower()

    if action == "engage":
        reason = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "manual_cli"
        url = f"{BASE}/api/v9/admin/kill?reason={urllib.request.quote(reason)}&by=cli"
        req = urllib.request.Request(url, method="POST")
    elif action in ("disengage", "resume"):
        url = f"{BASE}/api/v9/admin/resume?by=cli"
        req = urllib.request.Request(url, method="POST")
    elif action == "status":
        url = f"{BASE}/api/v9/admin/kill"
        req = urllib.request.Request(url, method="GET")
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
