# Agent #7: Infrastructure Monitor

## Persona
System watchdog. No personality — pure operational alerting. Terse, factual messages.

## Trigger
- **Continuous**: Polls every 30 seconds during RTH (Regular Trading Hours: 8:30-15:15 CT)
- **Reduced**: Every 5 minutes outside RTH
- **Immediate**: On any P1 threshold breach

## Inputs
| Data Source | Method | What |
|-------------|--------|------|
| Redis (Upstash) | REST API ping | `mems26:latest` timestamp freshness |
| Bridge process | Local process check | `json_bridge.py` running? |
| Sierra export | File mtime check | `mes_ai_data.json` age |
| Render backend | HTTP health check | `/market/latest` response time |
| Netlify frontend | HTTP check | Site reachable? |

## Outputs
| Condition | Channel | Message |
|-----------|---------|---------|
| Bridge down > 60s | #alerts-critical | `BRIDGE DOWN — no data for {n}s` |
| Redis stale > 120s | #alerts-critical | `REDIS STALE — last update {timestamp}` |
| Backend 5xx or timeout > 10s | #alerts-critical | `BACKEND ERROR — {status_code}` |
| Sierra export stale > 5 min | #alerts-info | `Sierra export stale — {age}` |
| Backend latency > 3s | #alerts-info | `Backend slow — {latency}ms` |
| All systems normal (hourly) | #alerts-info | `Systems OK — bridge:{age}s redis:{age}s api:{latency}ms` |

## Authority Level
**ALERT** — Can send notifications to Slack. Cannot restart services or modify config.

## Implementation Status
**STUB** — Spec only. No code.

## Estimated Implementation Effort
- Python script: 4 hours
- Slack integration: 2 hours
- Testing: 2 hours
- **Total: ~1 day**

## Required Slack Scopes
- `chat:write` — post to #alerts-critical, #alerts-info
- `channels:read` — verify channels exist

## Required Anthropic API Usage
**None** — pure monitoring, no AI needed.

## Estimated Monthly Cost
- Upstash API calls: ~86,400/month (during RTH) — within free tier
- Render: no extra cost (existing backend)
- Slack API: free tier sufficient
- **Total: ~$0/month**
