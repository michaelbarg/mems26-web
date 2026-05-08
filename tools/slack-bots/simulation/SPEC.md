# Agent #11: Simulation Agent — דה וינצ'י (Da Vinci)

## Persona
Da Vinci — methodical researcher. Tests theories against historical data. Reports with scientific rigor: hypothesis, method, results, verdict. Speaks in data, not opinion.

Hebrew example: "תיאוריה #7 — Suffering Side Veto: 1,973 סטאפים, 34% נחסמו, WR של חסומים 38% vs 52% — VALIDATED"

## Trigger
- **On-demand**: Michael or CC Master requests a theory validation
- **Queued**: Picks up validation tasks from #simulations backlog
- **Scheduled**: Re-runs all active theories weekly (Sunday night)

## Inputs
| Data Source | Method | What |
|-------------|--------|------|
| Backend DB | PostgreSQL query | Historical setups (1,973+ records) |
| Backend DB | PostgreSQL query | Trade outcomes (PnL, WR) |
| Spec files | Read `docs/specs/` | Theory definitions and parameters |
| Gate configs | Backend code | Current gate logic for comparison |

## Outputs
| Output | Channel | Content |
|--------|---------|---------|
| Validation report | #simulations | Full statistical report |
| Verdict | #simulations | `VALIDATED` / `REJECTED` / `INCONCLUSIVE` |
| Summary | #methodology | One-line result for methodology records |

### Report Template
```
🔬 Simulation Report — {theory_name}

HYPOTHESIS: {description}
METHOD: Applied to {n} setups from {date_range}

RESULTS
  Total setups: {n}
  Blocked by rule: {blocked} ({block_pct}%)
  Non-blocked: {passed}

  Blocked group:
    Win rate: {wr_blocked}%
    Avg PnL: {avg_pnl_blocked}pt
    
  Non-blocked group:
    Win rate: {wr_passed}%
    Avg PnL: {avg_pnl_passed}pt

  Difference: {delta_wr}pp WR, {delta_pnl}pt avg PnL

STATISTICAL SIGNIFICANCE
  Chi-squared: {chi2} (p={p_value})
  Sample size adequate: {yes/no}

VERDICT: {VALIDATED/REJECTED/INCONCLUSIVE}
RECOMMENDATION: {action}
```

## Authority Level
**EXECUTE** — Can run queries against historical data. Cannot modify production data or live trading.

## Implementation Status
**STUB** — Spec only. Existing simulation infrastructure in `backend/main.py` (sequential simulation endpoint) provides foundation.

## Estimated Implementation Effort
- Query builder: 4 hours
- Statistical analysis: 4 hours
- Report generation: 2 hours
- Slack integration: 2 hours
- Testing: 4 hours
- **Total: ~2 days**

## Required Slack Scopes
- `chat:write` — post to #simulations, #methodology
- `channels:read` — verify channels exist

## Required Anthropic API Usage
- Claude Sonnet for interpreting results and generating recommendations
- ~2-3 calls per theory validation
- **Estimated: ~$5-10/month** (depends on validation frequency)

## Estimated Monthly Cost
- Anthropic API: $5-10/month
- Database queries: minimal (existing Supabase/PostgreSQL)
- **Total: ~$5-10/month**
