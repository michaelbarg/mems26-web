# Bridge Operations — Screen-Based Management

Bridge runs in a detached `screen` session. Survives terminal close, CC restart, and logout.

## Start

```bash
screen -dmS mems26_bridge bash /tmp/start_bridge.sh
```

## View Live Log (attach/detach)

```bash
screen -r mems26_bridge       # attach to session
# Press Ctrl+A then D          # detach (Bridge keeps running)
```

## Stop

```bash
screen -S mems26_bridge -X quit
```

## View Log File

```bash
tail -f /tmp/bridge.log
```

## Verify

```bash
screen -ls                              # list sessions
ps aux | grep json_bridge | grep -v grep  # check PID
curl -s https://mems26-web.onrender.com/health | python3 -m json.tool
```

## Startup Script Location

`/tmp/start_bridge.sh` — sets env vars and launches `bridge/json_bridge.py`.

Note: UPSTASH_REDIS_REST_TOKEN must be set in `.env` or the startup script for Redis push to work.
