# Bridge Autostart · launchd

## Status
- Service: com.mems26.bridge
- Plist: ~/Library/LaunchAgents/com.mems26.bridge.plist
- Wrapper: inline bash -c in plist (secrets from .env)
- Logs: /tmp/bridge.log · /tmp/bridge.err.log
- KeepAlive: true (always restart, ThrottleInterval=30s)
- Autorestart: VERIFIED (SIGKILL → restart in <35s)

## Commands
- Status: `launchctl list | grep com.mems26.bridge`
- Start: `launchctl load ~/Library/LaunchAgents/com.mems26.bridge.plist`
- Stop: `launchctl unload ~/Library/LaunchAgents/com.mems26.bridge.plist`
- Restart: unload then load

## Troubleshooting
- /tmp/bridge.err.log = stderr, check first if not running
- If "Operation not permitted": the plist uses inline bash -c to avoid FDA issues
- Sierra Chart must be running for bridge to feed data
- After Mac reboot: launchd auto-starts (RunAtLoad=true)
- If secrets change: update .env file (bridge sources it on start)

## Created
Phase A.1 · 16 May 2026 · verified with SIGKILL autorestart test.
