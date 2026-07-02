# MEMS26 — Firing-Readiness Protocol (all paths, S2 + S4)

**Purpose:** when Michael asks *"are the systems firing?"*, run this to check **every path** in the fire pipeline and pinpoint exactly where (if anywhere) a fire is blocked. Built from the 2026-06-30 live debugging — every failure mode found that day is encoded here.
**DB:** `postgresql://localhost/mems26` (psql at `/Applications/Postgres.app/Contents/Versions/*/bin/psql`, LOCAL only). **Logs:** `/tmp/backend.err.log`. **Repo:** `/Users/michael/Downloads/mems26_web_git`.

---

## The pipeline — a fire must pass ALL of these, in order
A pattern that "fired" in the log is only step 3. It becomes a **trade** only if every downstream step passes. Check them in order; the first failing step is the blocker.

| # | Path step | Live check | PASS condition | Failure mode seen 06-30 |
|---|-----------|-----------|----------------|--------------------------|
| 0 | **Feed fresh** | `psql … SELECT max(ts) FROM v9_bars_5min_woodies` | within ~6 min of now (RTH) | — (was fresh) |
| 1 | **Day-type — single live source** | `psql … v9_day_type_history WHERE date=CURRENT_DATE` + `/api/v9/day_type/current` | both agree; **`DAYTYPE_GATE_LIVE_V1=1`**; **not "Normal" if IB broke** | gate read stale "Normal"/UNKNOWN while live=Variation (I-44/I-50) → **fixed** |
| 2 | **Backend boot is PRE-OPEN** | `ps -o etime,lstart` of uvicorn + `grep "[env_loader] applied" /tmp/backend.err.log \| tail -1` | started **before RTH open**; env_loader shows the expected var-count | **mid-RTH restart ⇒ IB-lock can't re-lock ⇒ `lock_state=PENDING` ⇒ S4 `ready_to_route=False` for the rest of the day** |
| 3 | **Detection** | S2: `grep "S2-DL"`; S4: `grep "Woodies] Pattern .* fired"` | a pattern forms | S2 INITIATIVE `b1_exp=0` (bars < expansion floor ~8-16pt) → no setup (market) |
| 4 | **S2 Auth Table** (S2 only) | `grep "Auth Table"` | `(pattern × day_type)` ≠ SKIP; **day_type ≠ UNKNOWN** | `day_type=UNKNOWN → Neutral_Center → SKIP` (I-44 auth half) → **fixed** (`bc1a1fd`) |
| 5 | **S4 sizing + RISK CAP** (S4 only) | `grep "V2 sizing\|RISK_CAP_STRICT_SKIP"` | sizing ≠ reject; **risk ≤ cap** (ZLR 15pt) | `risk=16.5 > 15 → SKIP` — stop anchored to a **stale dip** (`cluster_low w4`); fix = **breakout-bar stop** |
| 6 | **S4 signal write** (S4 only) | `grep "execute failed.*v9_woodies_signals"` | no write error | `NotNullViolation is_synthetic` → **fixed** (DB default 0; root code fix pending) |
| 7 | **S4 ready_to_route** (S4 only) | decision_tree (`decision_tree.py:434`) | `not failed AND not pending AND patterns AND sizing≠reject` | **PENDING stage (needs IB locked)** after mid-RTH restart → no route |
| 8 | **Gateway gates** | `grep "BLOCKED by\|blocked_by"` | day-type position gate (family×day-type), CONT_TREND_FILTER, DIRECTION_LSMA_VETO, cooldown(2-stop), cluster, SSV, risk-breakers all pass | day-type position gate read stale day_type → blocked CONT → **fixed** |
| 9 | **Demo execution** | `/api/v9/gateway/status` | `DEMO_EXECUTION_ENABLED=1`; `demo_enabled_systems=[2,4]`; demo slot free | — |
| 10 | **Sierra dispatch** | `ls -lt ~/SierraChart_Data/v9_export/*command*` ; Sierra running | PLACE command written → DLL executes on Sim | — (per-contract path built, Pipeline 5) |

---

## Quick run (one shot)
```bash
cd /Users/michael/Downloads/mems26_web_git
PSQL="$(ls /Applications/Postgres.app/Contents/Versions/*/bin/psql | head -1)"
echo "[NOW] $(TZ=America/Chicago date '+%H:%M CT')"
# 0 feed
"$PSQL" postgresql://localhost/mems26 -t -c "SELECT 'feed woodies='||max(ts) FROM v9_bars_5min_woodies;"
# 1 day-type + flag
"$PSQL" postgresql://localhost/mems26 -t -c "SELECT 'daytype='||day_type||'/'||status FROM v9_day_type_history WHERE date=CURRENT_DATE;"
grep -q "DAYTYPE_GATE_LIVE_V1=1" .env && echo "gate_live=ON" || echo "gate_live=OFF"
# 2 backend boot (must be pre-open)
ps -eo etime,lstart,command | grep "uvicorn backend.main" | grep -v grep | head -1
# 7 + 8 recent fires + where blocked
grep -aE "Pattern .* fired|FIRE:|BLOCKED by|Auth Table|RISK_CAP|execute failed.*woodies|ready_to_route" /tmp/backend.err.log | grep -avE "Redis|write-guard" | tail -12
# 9 + 5 gateway/trades
curl -s -m5 http://127.0.0.1:8000/api/v9/gateway/status | python3 -c "import sys,json;d=json.load(sys.stdin);print('demo=',d.get('demo_enabled_systems'),'trades_today=',d.get('trades_today'))"
"$PSQL" postgresql://localhost/mems26 -t -c "SELECT 'trades_today='||count(*) FROM v9_trades WHERE entry_ts::date=CURRENT_DATE;"
```

---

## Known failure modes (the 06-30 catalogue — check these first)
1. **Day-type not single-source (I-44/I-50):** gate/auth read a *different* day_type than the live S1 engine → flicker Normal↔Variation → family gate blocks everything. Invariant: **one S1 (`classify_session` live in `app.state`) defines day_type; everyone READS it.** Fix live = `DAYTYPE_GATE_LIVE_V1=1` + `bc1a1fd`.
2. **Mid-RTH restart breaks S4 (operational rule):** a backend restart **during** RTH leaves `lock_state=PENDING` (IB can't re-lock mid-session) → woodies `ready_to_route=False` → **S4 won't route for the rest of the day.** Only restart **before the open**; if a mid-session restart is unavoidable, S4 is down until tomorrow's clean boot.
3. **`is_synthetic` NOT NULL (no default):** every `v9_woodies_signals` write failed. Patched with a column default; root fix = make the INSERT explicit.
4. **Risk-cap SKIP from a stale-dip stop:** `cluster_low(window 4)` reaches back to a pre-rejection dip → wide stop → `risk > cap → SKIP`. Fix = **stop on the breakout bar** (Michael 06-30).
5. **S2 not forming:** `b1_exp=0` — bars smaller than the expansion floor; no INITIATIVE. Market-dependent, not a bug.

---

## Today's snapshot (2026-06-30 ~11:00 CT)
- 0 feed ✅ fresh · 1 day-type ✅ Variation, `gate_live=ON` · 9 demo `[2,4]` ✅
- 🔴 **S4 blocked at step 7** (`ready_to_route=False`, IB-lock PENDING after the mid-RTH restart) → ZLR fires but doesn't route → **0 trades**.
- 🟡 S2 step 3 — no INITIATIVE forming (small bars).
- **Persisted fixes** (good for tomorrow's clean boot): `DAYTYPE_GATE_LIVE_V1=1`, `is_synthetic` default, day-type single-source (`bc1a1fd`).
