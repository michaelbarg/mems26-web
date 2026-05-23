# Wave 1b-delegate — D-088 Deploy + Verify (other agent)

**Role:** CC-OPS or Cursor subagent — **not** Parent  
**Precondition:** Code merged locally — `trading_gateway.py` D-088, tests pass  
**Parent continues:** Wave 1a S1-PREV (parallel)

---

## Mission

1. Restart backend on `127.0.0.1:8000` (Michael approval if needed)
2. Verify SHADOW records when `cluster_guard` active
3. Report PASS/FAIL — do **not** change gateway code unless tests fail

---

## Tests (before restart)

```bash
cd /Users/michael/Downloads/mems26_web_git
pytest tests/v9/gateway/test_gw02_record_attempt.py tests/v9/gateway/test_d088_shadow_cluster_guard.py -q
```

Expected: **4 passed**

---

## After restart

```bash
# Warm latency
curl -o /dev/null -s -w '%{time_total}\n' http://127.0.0.1:8000/api/v9/cockpit/systems-snapshot

# Gateway shadow count (baseline — note number)
curl -s http://127.0.0.1:8000/api/v9/gateway/status | jq '{shadow_count: (.shadow_trades | length), cluster: .cluster_guard}'

# Logs — during Woodies fire window
# Expect: "SHADOW recorded; DEMO/LIVE blocked by cluster guard D-037"
# NOT: early return with zero shadow during cluster block
```

---

## Deliverable

`docs/reports/P30_D088_DEPLOY_VERIFY.md`:

| Check | PASS |
|-------|------|
| pytest 4/4 | |
| backend up | |
| log line D-088 present OR shadow count increased during cluster block | |

**Verdict:** PASS / FAIL

---

## DO NOT

- Edit `trading_gateway.py` (Parent/other dev owns code)
- Touch bridge, DLL, frontend
- Change LaunchAgent / CLOUD_URL

---

*Delegate only · Parent on S1-PREV · 2026-05-20*
