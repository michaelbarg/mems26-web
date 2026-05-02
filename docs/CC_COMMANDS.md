# MEMS26 — CC Quick Commands

When the user types one of these commands (in Hebrew or English),
perform the action exactly as defined. Don't ask for clarification —
just execute and report.

---

## בדיקת דופק / PULSE / dofek

**What it means:** Run system health check (daily_check.sh).

**Trigger phrases:** "בדיקת דופק", "PULSE", "dofek", "pulse check",
"check pulse", "תבדוק דופק"

**Action:**
1. Execute: `./scripts/daily_check.sh`
2. Parse output
3. Report findings in this format:

```
═══════════════════════════════════════
בדיקת דופק - MEMS26 Health Check
═══════════════════════════════════════
🟢 Backend:    200 (OK)
🟢 Frontend:   200 (OK)
🟡 Bridge:     STOPPED (weekend - expected)
🟢 DB:         Last setup X min ago
🟢 Today:      N setups, N trades, $X PnL

Verdict: All systems operational ✅
or:
Verdict: Issues detected ⚠️
  Bridge stopped during market hours
  Suggest: restart Bridge
═══════════════════════════════════════
```

**Status indicators:**
- 🟢 = healthy
- 🟡 = expected anomaly (e.g., weekend)
- 🔴 = problem requiring action

**Don't ask for clarification.** Just run and report.

---

## STATUS

**What it means:** Quick git/code status.

**Action:**
1. Show current branch: `git branch --show-current`
2. Show last 5 commits: `git log --oneline -5`
3. Show working tree: `git status --short`
4. Compare to origin: any unpushed commits?

Report in clean table format.

---

## TODAY

**What it means:** Show today's performance metrics.

**Action:**
Query DB for:
- Setups detected today (count, by hour)
- Trades executed today (count, PnL)
- Comparison to 7-day average
- Highlight anomalies

---

## TRADES

**What it means:** Show last 10 real trades with full context.

**Action:**
Query trades table JOINed with setup_attempts.
Show: time, direction, entry/stop/T1/T2/T3, outcome, PnL,
day_type, killzone, score.

---

## V2-SIM

**What it means:** Re-run V2 grid simulation.

**Action:**
1. Execute: `python3 -m tools.multidim_sim grid`
2. Report top 5 configs
3. Compare to V2_SPEC_FINAL.md
4. Highlight pattern shifts

---

## RETRO

**What it means:** Run full multi-target retro.

**Action:**
1. Execute: `python3 -m tools.multidim_sim retro`
2. Report outcome distribution
3. Compare to previous retro

---

## BACKUP

**What it means:** Run daily backup + verify completeness.

**Action:**
1. Execute: `./scripts/daily_backup.sh`
2. Verify backup row counts match live DB
3. Alert if partial

---

## CONVENTIONS

When user uses these commands:
- Execute immediately, don't ask for clarification
- Report in clean structured format
- Use 🟢/🟡/🔴 status indicators
- Hebrew responses for Hebrew users
- Suggest fixes when applicable
- Never push or modify without explicit approval

---

## SECURITY REMINDERS

- Never include DATABASE_URL in any command
- Use os.environ['DATABASE_URL'] in Python
- Never write secrets to files
- Never expose credentials in commit messages
