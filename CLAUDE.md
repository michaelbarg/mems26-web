# MEMS26 Agent Guardrails

This repository controls the local MEMS26 trading stack. Treat post-reboot
stability settings as production safety controls.

## LaunchAgent Stability

- Do not change `~/Library/LaunchAgents/com.mems26.bridge.plist` back to
  `KeepAlive=true`.
- The bridge LaunchAgent must use conditional KeepAlive:

```xml
<key>KeepAlive</key>
<dict>
    <key>SuccessfulExit</key>
    <false/>
</dict>
```

- The bridge LaunchAgent command must export:

```bash
export V9_DISABLE_WATCHDOG="${V9_DISABLE_WATCHDOG:-1}"
```

## Service Bring-Up

- Do not start MEMS26 services unless explicitly asked.
- Do not run `npm run dev`, `next dev`, or `scripts/start_all.sh` during a
  stability audit.
- Before starting services, check for existing listeners on `127.0.0.1:3000`
  and `127.0.0.1:8000` to avoid duplicate frontend/backend instances.

## Generated Files

- Do not commit Python bytecode (`*.pyc`) or `__pycache__/` files.
- If bytecode appears in git status, treat it as generated state unless the
  user explicitly asks to preserve it.
