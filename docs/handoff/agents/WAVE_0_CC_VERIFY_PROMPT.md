# Wave 0 — CC-OPS: P0.5 Runtime Verify

**Role:** CC-OPS (Claude Code terminal)  
**Type:** VERIFY ONLY — no code edits  
**Precondition:** P0.5 commits local (`8dd1ffb`, `a9138ce`); backend on `127.0.0.1:8000`  
**Deliverable:** `docs/reports/P30_WAVE_0_CC_VERIFY.md`  
**Signal file (optional):** `/tmp/p30_wave0_cc_go` with single line `GO` or `NO-GO`

---

## Authority (read first)

1. `docs/reports/P30_CURSOR_P05_REPORT.md`
2. `docs/reports/P30_DECISION_D086_S3_FIRING.md` — S3 SHADOW fire is **tolerated**, not a NO-GO for soak
3. `docs/reports/P30_REGISTRY_STATE.md` — §18 FAIL is **not** CC blocker if D-087 signed

---

## Hard bans

- Do not edit repo files
- Do not change LaunchAgent, `CLOUD_URL`, bridge plist
- Do not restart stack unless Michael asked
- Bridge must remain `http://localhost:8000` only

---

## Checklist (all required)

| # | Check | PASS criterion | Evidence |
|---|--------|----------------|----------|
| 1 | Backend up | `lsof -i :8000` or PID known | paste |
| 2 | Latency | `curl` snapshot + gateway/risk each **&lt; 500ms** | timings |
| 3 | Four axes sample | One bars/history endpoint: quality, recency, cardinality, latency | one table row |
| 4 | FP journal | 0 SQLite thread errors in last 30m logs | grep excerpt |
| 5 | Woodies SHADOW | RTH log line or journal entry `SHADOW` from S4 path | excerpt |
| 6 | S3 SHADOW (D-086) | If fires: **record only** in SHADOW DB — note count, not spec fix | excerpt |
| 7 | S2 path | Confirm `pre_fire` still in chain (read-only grep OK) | `setup_emitter.py:81` |
| 8 | GW-CHOP | No self-HTTP loop in gateway logs post-fix | excerpt |
| 9 | Sierra match | `sierra_match_tool` or inbox baseline **29/29** if run | output |
| 10 | pytest | `pytest tests/v9/gateway/test_gw02_record_attempt.py -q` | pass/fail |

---

## Commands (adapt paths)

```bash
# Latency
curl -o /dev/null -s -w '%{time_total}\n' http://127.0.0.1:8000/api/v9/cockpit/systems-snapshot
curl -o /dev/null -s -w '%{time_total}\n' http://127.0.0.1:8000/api/v9/gateway/status

# Day type / clock sanity
curl -s http://127.0.0.1:8000/api/v9/day_type/v9/current | head -c 500
curl -s http://127.0.0.1:8000/api/v9/clock/now | head -c 500

# Tests
cd /Users/michael/Downloads/mems26_web_git && pytest tests/v9/gateway/test_gw02_record_attempt.py -q

# Logs (examples — adjust)
tail -n 80 /tmp/bridge.err.log 2>/dev/null || true
# journal / uvicorn log per Michael's setup
```

---

## Verdict template

```markdown
# P30 Wave 0 — CC Verify

**Date:** …
**Verdict:** GO / NO-GO / GO-WITH-NOTES

## Results
| # | Check | PASS/FAIL | Notes |
|---|--------|-----------|-------|

## Blockers (if NO-GO)
- …

## Notes for Michael
- D-086 S3: …
- Registry §18: defer to D-087
```

---

## Handoff to Cursor Parent

- **GO** → Michael may sign D-087 → start Wave 1 prompts
- **NO-GO** → list blockers; Parent does **not** open S1/CLOCK agents

---

*CC only · Wave 0 · 2026-05-20*
