# MEMS26 — Data Validation Protocol

## Purpose
Standard procedures for verifying data integrity, system health,
and trade quality across all CC chat sessions.

## When to Use
- Start of every chat session (PULSE)
- Before deploying changes (full validation)
- After any code change (regression check)
- Daily during LIVE trading (continuous)
- When user requests trade review (detailed)

---

## Layer 1: System Health Check (PULSE)

### Trigger
- Start of any new chat
- User says "בדיקת דופק" or "PULSE"
- Before any operational task

### Action
```bash
source ~/.mems26_env
./scripts/daily_check.sh
```

### Required Output Format
```
═══════════════════════════════════
  בדיקת דופק - MEMS26 Health Check
═══════════════════════════════════

🟢/🔴 Backend:    [status]
🟢/🔴 Frontend:   [status]
🟢/🟡 Bridge:     [status] [context]
🟢/🟡 DB:         [last activity]

Verdict: All operational ✅
או: Issues detected ⚠️
   - [issue 1]
   - [issue 2]
   Suggested action: [fix]

═══════════════════════════════════
```

### Status Codes
- 🟢 = healthy
- 🟡 = expected anomaly (e.g., weekend Bridge stopped)
- 🔴 = problem requiring action

### If Issues Detected
- Don't proceed with task
- Report to user
- Suggest specific fix
- Wait for user approval

---

## Layer 2: Data Quality Validation (MDS)

### Trigger
- User says "RETRO" or "V2-SIM"
- Weekly review
- Before V2/V3 deployment
- Investigation of anomalies

### Standard MDS Validation Sequence

#### Step 1: Data Coverage Check
```python
import os, psycopg2
url = os.environ.get('DATABASE_URL')
if not url:
    print("⚠️  DATABASE_URL not loaded — run: source ~/.mems26_env")
    exit(1)

conn = psycopg2.connect(url)
cur = conn.cursor()

for table in ['trades', 'setups', 'setup_attempts', 'setup_observations']:
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    count = cur.fetchone()[0]
    cur.execute(f"SELECT MAX(created_at) FROM {table}")
    latest = cur.fetchone()[0]
    print(f"{table}: {count} rows, latest: {latest}")
```

#### Step 2: Tick Data Sanity
```python
from tools.multidim_sim.retro.scid_reader import ScidReader, get_default_scid_path

reader = ScidReader(get_default_scid_path())
total_ticks = reader.count_ticks()
date_range = reader.get_date_range()
print(f"Ticks: {total_ticks}, Range: {date_range}")
```

#### Step 3: Multi-Target Retro
```bash
python3 -m tools.multidim_sim retro --recent-days 7
```

Expected outputs:
- Outcome distribution
- Per-day-type win rate
- Per-killzone metrics
- Sequential vs parallel comparison

#### Step 4: V2 Grid Validation
```bash
python3 -m tools.multidim_sim grid --quick
```

Should produce:
- Top 5 configs by net PnL
- Comparison to V2_SPEC_FINAL.md baseline

---

## Layer 3: Trade Manual Review

### Trigger
- User asks "show me trades" / "TRADES" / "תראה עסקאות"
- Weekly trade review
- Investigation of specific trade

### REQUIRED Format Per Trade

For EVERY trade shown, include ALL of these fields:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Trade #N  [emoji_status]  PnL: $XXX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📅 Date:        YYYY-MM-DD
🕐 Entry:       HH:MM:SS (Sierra time)
🏁 Closed:      HH:MM:SS (overall exit)
⏱️ Duration:    X min Y sec

📍 Direction:   LONG / SHORT
🎯 Day Type:    NORMAL / RANGE / TREND / DEVELOPING / GAP_FILL
⏰ Killzone:    NY_Open / London / Asia / etc.

💰 Price Ladder:
    Entry:      X.XX
    Stop:       X.XX (X.Xpt risk)
    T1:         X.XX (+Xpt = 1R)
    T2:         X.XX (+Xpt = 2R)
    T3:         X.XX (+Xpt = 3R)

⏱️ Per-Contract Exits:
    C1 → T1:    HH:MM:SS  →  +$XX
    C2 → T2:    HH:MM:SS  →  +$XX
    C3 → T3:    HH:MM:SS  →  +$XX
    Stop:       HH:MM:SS or — →  -$XX or —

📊 Outcome:     HIT_C1 / HIT_C2 / HIT_C3 / HIT_STOP / PARTIAL
💵 Total PnL:   $XXX

📈 Quality Score: XX/100
    Vegas:     XX
    TPO:       XX
    FVG:       XX
    Footprint: XX
📍 VWAP side:  above / below

📝 Sierra Chart: open MES 1m at YYYY-MM-DD HH:MM
```

### Why This Format
User verifies trades manually on Sierra Chart.
Without precise per-contract exit timestamps, can't validate.

### Database Query Template

```sql
SELECT 
    sa.created_at,
    sa.direction, sa.entry_price, sa.stop_price,
    sa.c1_target, sa.c2_target, sa.c3_target,
    sa.day_type, sa.killzone_at_entry,
    sa.score, sa.vegas_score, sa.tpo_score,
    sa.fvg_score, sa.footprint_score, sa.vwap_side,
    s.t1_hit_ts, s.t2_hit_ts, s.t3_hit_ts,
    s.stop_hit_ts, s.closed_ts,
    t.realized_pnl_usd, t.outcome
FROM trades t
JOIN setup_attempts sa ON t.setup_id_hash = sa.setup_id_hash
LEFT JOIN setups s ON t.setup_id_hash = s.setup_id_hash
ORDER BY t.created_at DESC
LIMIT 10
```

---

## Critical Validation Rules

### Rule 1: Never Skip PULSE
Every chat session starts with PULSE.
No exceptions. Even "quick" tasks need health check first.

### Rule 2: Verify Before Deploy
Any code change requires:
1. PULSE (system healthy)
2. MDS retro on recent data (no regression)
3. Manual trade review (sanity check)

### Rule 3: Document Anomalies
Any anomaly found:
- Document in chat
- Add to outstanding issues list
- Include in next handoff document

### Rule 4: User Verification Loop
For destructive operations (deploys, deletes, schema changes):
- Show plan first
- Wait for explicit "approved"
- Then execute
- Verify after

### Rule 5: Backup Before Major Changes
Before any DB schema change or deployment:
- Run backup script
- Verify backup completeness
- Document baseline metrics

---

## Common Validation Scenarios

### Scenario A: Start of Day
```
1. PULSE
2. Check Bridge running (or scheduled to start)
3. Verify last setup time recent
4. Confirm no pending alerts
→ Ready to monitor day
```

### Scenario B: After Deployment
```
1. PULSE (post-deploy)
2. Compare row counts before/after
3. Verify no regression in test setups
4. Run quick MDS validation
5. Monitor first hour live
```

### Scenario C: Investigation
```
1. PULSE (current state)
2. Identify specific timeframe
3. Pull trades with full timestamps
4. Cross-reference with Sierra Chart
5. Document findings
```

### Scenario D: Weekly Review
```
1. PULSE
2. Full MDS retro on past 7 days
3. Per-day-type analysis
4. V2 spec validation (still holds?)
5. Identify improvements queue
6. Update master log
```

---

## Cross-Chat Continuity

### Starting New Chat
Always begin with:
1. Read most recent handoff document
2. Run PULSE
3. Confirm understanding of current state
4. Then proceed with task

### Ending Chat
Before closing:
1. Update master log with session changes
2. Add to outstanding issues if any
3. Note next steps for handoff
4. Push commits

---

## Security During Validation

### Never Expose
- DATABASE_URL values in commands
- API keys in commits
- Passwords in any output
- Personal data in logs

### Always Use
- ${DATABASE_URL} via shell substitution or os.environ in Python
- ~/.mems26_env for credentials
- chmod 600 for secrets files

### Report Immediately
- Found credentials in code → flag and remove
- Suspicious access patterns → alert user
- Failed auth attempts → log and notify
