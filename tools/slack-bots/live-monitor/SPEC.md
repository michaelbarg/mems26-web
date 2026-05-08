# Agent #8: Live Trading Monitor — סטארק (Stark)

## Persona
Stark — cold, precise, emotionless observer. Reports trades like a military radio operator. Short messages. No opinions. Facts only.

Hebrew example: "סטאפ #142 — LONG sweep @ 5732, score 78, C1 target 5738"

## Trigger
- **Active**: RTH only (8:30-15:15 CT)
- **Events**: New setup detected (score >= 60), gate decision, trade execution, target hit, stop hit, setup expiry

## Inputs
| Data Source | Method | What |
|-------------|--------|------|
| Backend API | Poll `/market/analyze` | Current setups, scores |
| Backend API | Poll `/trades` | Trade executions, fills |
| Redis | Subscribe pattern | `mems26:latest` — live market state |
| Setup accumulator | Backend endpoint | Lifecycle events (detected → C1 → C2 → stopped) |

## Outputs
| Event | Channel | Message Format |
|-------|---------|----------------|
| Setup detected | #live-trading | `🔵 SETUP #{id} — {direction} {pattern} @ {price}, score {score}, level: {level_name}` |
| Gate blocked | #live-trading | `🚫 SETUP #{id} BLOCKED — {gate_name}: {reason}` |
| Trade entered | #live-trading | `🟢 TRADE #{id} ENTERED — {direction} @ {entry}, stop @ {stop}, risk {risk}pt` |
| C1 hit | #live-trading | `✅ C1 HIT — +{pts}pt, stop → BE` |
| C2 hit | #live-trading | `✅ C2 HIT — +{pts}pt` |
| C3 hit | #live-trading | `🏆 FULL TARGET — +{pts}pt total` |
| Stopped out | #live-trading | `🔴 STOPPED — -{pts}pt` |
| Setup expired | #live-trading | `⏰ EXPIRED #{id} — no entry in 90min` |

## Authority Level
**OBSERVE + ALERT** — Read-only monitoring. Reports to Slack. Cannot modify trades or setups.

## Implementation Status
**STUB** — Spec only. No code.

## Estimated Implementation Effort
- Python bot: 6 hours
- Event detection logic: 4 hours
- Message formatting: 2 hours
- Testing with historical data: 4 hours
- **Total: ~2 days**

## Required Slack Scopes
- `chat:write` — post to #live-trading
- `channels:read` — verify channel exists

## Required Anthropic API Usage
**None** — pure event forwarding, no AI analysis.

## Estimated Monthly Cost
- Slack API calls: ~200/day during RTH — free tier
- Backend polling: minimal (existing infrastructure)
- **Total: ~$0/month**
