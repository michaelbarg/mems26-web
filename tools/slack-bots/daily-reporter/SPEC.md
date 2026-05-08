# Agent #9: Daily Reporter

## Persona
Neutral analyst. Presents data without spin. Structured reports with consistent format. End-of-day only — not conversational.

## Trigger
- **Scheduled**: 16:30 CT daily (1 hour after RTH close)
- **Manual**: Michael types `/daily-report` in Slack
- **Skip**: Weekends, market holidays

## Inputs
| Data Source | Method | What |
|-------------|--------|------|
| Backend API | `/trades` | All trades from today |
| Backend API | `/setups/summary` | Setup detection stats |
| Backend API | `/simulation/summary` | Simulation vs actual comparison |
| Redis | `mems26:candles` | Day's price action summary |
| Gate logs | Backend DB | Gate pass/block counts per gate |

## Outputs
| Section | Channel | Content |
|---------|---------|---------|
| Daily Summary | #daily-reports | Full structured report (see template below) |
| Highlight | #strategic | One-line: "Day summary: {trades} trades, {pnl} PnL, {wr}% WR" |

### Report Template
```
📊 MEMS26 Daily Report — {date}

SESSION
  Market: {open} → {close} ({change}pt, {change_pct}%)
  Day Type: {day_type}
  Range: {high} - {low} ({range}pt)

SETUPS DETECTED: {count}
  By pattern: Sweep({n}), Rejection({n}), Momentum({n}), ...
  Avg score: {avg_score}
  Gate block rate: {block_pct}%

TRADES: {count}
  Won: {wins} ({win_pct}%) | Lost: {losses} | BE: {breakeven}
  Gross PnL: {pnl}pt ({pnl_dollar})
  Best: {best_trade}
  Worst: {worst_trade}

GATES
  {gate_name}: {passed}/{total} ({pct}%)
  ...

SIMULATION vs ACTUAL
  Sim trades: {sim_count} | Actual: {actual_count}
  Sim PnL: {sim_pnl} | Actual: {actual_pnl}

TOMORROW
  Key levels: {levels}
  Posture: {posture}
```

## Authority Level
**REPORT** — Generates summaries. No action authority. Cannot modify data.

## Implementation Status
**STUB** — Spec only. No code.

## Estimated Implementation Effort
- Data aggregation: 4 hours
- Report formatting: 2 hours
- Scheduling (cron/launchd): 1 hour
- Slack posting: 1 hour
- Testing: 2 hours
- **Total: ~1.5 days**

## Required Slack Scopes
- `chat:write` — post to #daily-reports, #strategic
- `channels:read` — verify channels exist

## Required Anthropic API Usage
- **Optional**: Claude Haiku for "tomorrow's posture" summary (~$0.05/day)
- Can be hardcoded rule-based instead (day type → posture mapping)
- **Estimated: ~$1.50/month** (if using AI) or $0 (rule-based)

## Estimated Monthly Cost
- Anthropic API: $0-1.50/month
- Slack: free tier
- **Total: ~$0-1.50/month**
