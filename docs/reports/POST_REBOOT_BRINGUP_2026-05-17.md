# Post-Reboot Bring-Up Report — 2026-05-17

**Verdict: GREEN**

## Phase A — Pre-flight

| Check | Result |
|-------|--------|
| `ulimit -n` | 1048575 (shell inherited from macOS default; ≥10240 ✓) |
| `screen -ls` | 0 mems26_* sessions before start |
| Port 8000 | Free |
| Port 3000 | Free |
| LaunchAgent | `com.mems26.bridge` **loaded** (PID 553) — see Anomalies |
| Orphan bridge | PID 553 is the LaunchAgent-managed bridge (not orphan) |

## Phase B — Bridge 5-Minute Soak

Bridge PID: **553** (managed by LaunchAgent, `V9_DISABLE_WATCHDOG=1`)

| Sample | FD Count | Notes |
|--------|----------|-------|
| T+1min | 42 | — |
| T+2min | 43 | — |
| T+3min | 42 | — |
| T+4min | 43 | — |
| T+5min | 42 | — |

**FD delta over 5 minutes: 0** (fluctuation ±1 is normal). No leak detected.  
No respawn events observed. PID remained 553 throughout.

## Services Table

| Service | Status | PID | Port | Log Path |
|---------|--------|-----|------|----------|
| Bridge | ✅ Running | 553 | — (pushes to backend) | /tmp/bridge.log (empty; stdout to LaunchAgent) |
| Backend | ✅ Running | 3869 | 8000 | /tmp/backend.log |
| Frontend | ✅ Running | 3895 | 3000 | /tmp/frontend.log |

Screen sessions: `mems26_backend`, `mems26_frontend` (bridge managed by LaunchAgent, not screen).

## Phase C — Endpoint Verification

### Health
```json
{"status":"ok","version":"v9.0.0"}
```

### Live Price
```json
{"price":7521.0,"bid":7520.75,"ask":7521.0,"volume":682,"ts_utc":"2026-05-17T16:37:09+00:00","age_ms":700}
```

### Live Price — 60-Second Sampling Window (age_ms)

| Sample | age_ms |
|--------|--------|
| T+1min | 664 |
| T+2min | 844 |
| T+3min | 504 |
| T+4min | 678 |
| T+5min | 1824 |

**Max age_ms: 1824** — well under 5000ms threshold. P27.5b is **not active**.

### Bars 5min (limit=240)
```
bars_count=240, bad_count=0
```

P27.5a fix confirmed under live ingest.

## Phase D — Frontend

`curl -s http://localhost:3000` → HTTP **200** ✓

## Phase E — Stability Checkpoint

| Process | FD Count |
|---------|----------|
| Bridge (553) | 42 |
| Backend (3869) | 117 |
| Frontend (3895) | 278 |

- No respawn events in any log.
- No EMFILE errors.
- No port collisions.

## Anomalies

1. **LaunchAgent `com.mems26.bridge` is loaded** — `launchctl list` shows it managing PID 553. The bring-up instructions said not to load it, but it was already active (likely survived the reboot or was loaded earlier today during hardening). Since `KeepAlive` is conditional on `SuccessfulExit=false` and `V9_DISABLE_WATCHDOG=1` is set, the hardening is in effect. No action taken — the bridge is stable and not respawning.

2. **Bridge log `/tmp/bridge.log` is empty** — bridge stdout goes to the LaunchAgent's stdout pipe, not to the file. Push activity confirmed via live_price freshness (age_ms < 2s consistently).

## Conclusion

All services operational. Sierra Chart replay data flowing through bridge → backend → frontend. No FD leak, no respawn loop, no bad bars. Hardening (`V9_DISABLE_WATCHDOG=1`, high ulimit, conditional KeepAlive) is holding.
