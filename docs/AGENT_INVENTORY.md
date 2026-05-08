# MEMS26 Agent Inventory

Source: D-043 (Agent Architecture) + D-060 (Slack Integration Plan)

## Agent Registry

| # | Agent | Persona | Channel | Authority | Status |
|---|-------|---------|---------|-----------|--------|
| 1 | CC Master | Coordinator | #cc-master | DISPATCH — assigns tasks to workers | PLANNED |
| 2 | DLL Worker | — | #dev-dll | EXECUTE — C++ Sierra Chart code | PLANNED |
| 3 | Backend Worker | — | #dev-backend | EXECUTE — Python/FastAPI | PLANNED |
| 4 | Frontend Worker | — | #dev-frontend | EXECUTE — Next.js UI | PLANNED |
| 5 | QA Agent | — | #qa | BLOCK — can reject commits | PLANNED |
| 6 | Methodology Guardian | — | #methodology | ADVISE — source compliance checks | PLANNED |
| 7 | Infrastructure Monitor | — | #alerts-critical, #alerts-info | ALERT — monitors system health | STUB |
| 8 | Live Trading Monitor | סטארק (Stark) | #live-trading | OBSERVE + ALERT — live trade events | STUB |
| 9 | Daily Reporter | — | #daily-reports | REPORT — EOD summaries | STUB |
| 10 | Trump (Strategic) | טראמפ | #strategic | ADVISE — architecture decisions | PLANNED |
| 11 | Simulation Agent | דה וינצ'י (Da Vinci) | #simulations | EXECUTE — theory validation | STUB |
| 12 | Nixon (System Validation) | Nixon | #checkpoints | VALIDATE — pre-deploy checks | STUB |

## Authority Levels

- **DISPATCH**: Can assign tasks to other agents. Cannot execute directly.
- **EXECUTE**: Can write code, run tests, make changes within scope.
- **BLOCK**: Can prevent merges/deploys. Override requires Michael's approval.
- **ALERT**: Can send notifications. Cannot take action.
- **OBSERVE**: Read-only monitoring. Reports findings.
- **ADVISE**: Can recommend. Cannot enforce.
- **REPORT**: Generates summaries. No action authority.
- **VALIDATE**: Runs checks. Can flag issues. Cannot fix.

## Automated Bots (Spec Stubs Created)

These 5 agents run autonomously (no human trigger needed):

1. **Infrastructure Monitor** (`tools/slack-bots/infrastructure-monitor/`)
   - Monitors: bridge uptime, Redis latency, Sierra data freshness
   - Channels: #alerts-critical (P1), #alerts-info (P2)

2. **Live Trading Monitor — סטארק** (`tools/slack-bots/live-monitor/`)
   - Monitors: live setups, gate decisions, trade executions
   - Channel: #live-trading

3. **Daily Reporter** (`tools/slack-bots/daily-reporter/`)
   - Generates: EOD summary with trades, PnL, gate stats
   - Channel: #daily-reports

4. **Simulation Agent — דה וינצ'י** (`tools/slack-bots/simulation/`)
   - Runs: theory validations on historical data
   - Channel: #simulations

5. **Nixon (System Validation)** (`tools/slack-bots/nixon/`)
   - Runs: pre-deploy validation checks
   - Channel: #checkpoints

## CC-Operated Agents (No Spec Stubs Yet)

Agents #1-6 and #10 are operated by Claude Code within conversation context. They don't need separate bot infrastructure — they're roles CC assumes based on task type. Future work may add Slack bot wrappers for status reporting.

## Implementation Priority

1. Infrastructure Monitor — most critical for reliability
2. Live Trading Monitor — needed for trade oversight
3. Daily Reporter — low risk, high value
4. Nixon — needed before any automated deploys
5. Simulation Agent — research tool, lower urgency
