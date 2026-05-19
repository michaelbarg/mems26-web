# P30 → SHADOW 100% — Claude Code Mega Prompt (copy §1–§12)

**Date:** 2026-05-19  
**Branch:** `stabilize/mems26-local-truth-2026-05-16`  
**Repo:** `/Users/michael/Downloads/mems26_web_git`  
**Michael's goal today:** All phases through **SHADOW mode** working at 100% — data, chart visual parity, cockpit systems, soak — **no LIVE trading**.

---

## §1 — Mission

Close every **BLOCKED** item from P30.0–P30.9c so Michael can run **SHADOW** with confidence:

1. Cockpit loads chart + TPO + CVD + price **without manual Max click or backend restart**
2. Visual parity with Sierra **5m screen** (not Woodies — that's P30.10)
3. Backend **does not hang** (uvicorn must respond <2s on heartbeat always)
4. SHADOW mode: gateway, systems snapshot, FiveMin/Footprint/Woodies signals, soak strip — **verified live**
5. Update all `docs/reports/PROMPT30_*.md` + `P30_ROADMAP.md` with evidence

**Cursor already shipped (verify in `fdd73ed` + latest):** inline CVD, TPO overlay, live_price poll, chart height 720 default, scroll-back guard.

---

## §2 — Safety (non-negotiable)

- `CLOUD_URL=http://localhost:8000` only. Never cloud Render URL.
- No full 12-stream bridge without Michael's explicit OK. OK: `--bars-5min-only`, `V9_SKIP_HISTORY=1`.
- **No LIVE trading.** SHADOW/DEMO only. No `trade_command.json` unless Michael approves shadow fire test.
- Do not change LaunchAgent `KeepAlive=true` or plist without Michael.
- Check ports 3000/8000 before duplicate start.
- Do not regenerate Sierra monolith from modular sources.

---

## §3 — Phase gate table (update when DONE)

| Phase | Gate | Owner today | Done when |
|-------|------|-------------|-----------|
| P30.8 | 5min.json → DB → chart | CC verify | 600 bars, 4-axis UAT GREEN |
| P30.9 | TPO API + overlay | CC autonomous UAT | Sierra 5m match ±0.25 (`PROMPT30_AUTONOMOUS_PARITY_CC_MEGA_PROMPT.md`) |
| P30.9b/c | CVD inline + TPO today/yesterday | Cursor done | CVD on time axis, lines visible |
| P30.10 | Woodies 5m panel | CC | CCI panel OR defer with Michael OK |
| **P30.SHADOW** | SHADOW end-to-end | **GREEN** (2026-05-19) | 22/22 soak probes; see `PROMPT30_SHADOW_READY.md` |
| P30.11 | Full bridge | **DEFER** unless Michael says go |

---

## §4 — CRITICAL: Backend hang (P0)

**Symptom:** Port 8000 listens but `heartbeat`, `bars5min`, `tpo/current` **timeout 5s+**. `live_price` may work. Chart empty, console `ChartV5b load error: Failed to fetch`.

**CC must:**

1. Reproduce: `curl -m 3 http://127.0.0.1:8000/api/v9/cockpit/heartbeat`
2. If hang → `py-spy dump` or stack trace on PID; check SQLite lock, blocking `post_bars_5min`, BarRouter on main thread, systems-snapshot deadlock
3. Fix smallest root cause (likely: move blocking work off event loop, WAL busy_timeout, or dedupe lock)
4. Add regression: `tests/v9/api/test_backend_responsive_under_load.py` — heartbeat <2s while simulated POST /bars/5min
5. Document in `docs/reports/PROMPT30_BACKEND_HANG.md`

**Workaround script for Michael until fixed:**

```bash
lsof -tiTCP:8000 | xargs kill -TERM; sleep 2
cd /Users/michael/Downloads/mems26_web_git && set -a && source .env && set +a
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

---

## §5 — Visual parity (CC autonomous — see `PROMPT30_AUTONOMOUS_PARITY_CC_MEGA_PROMPT.md`)

Michael does **not** run screenshot QA. CC runs API 4-axis + numeric Sierra parity + browser checklist; Michael only gets SHADOW soak go/no-go when all rows PASS.

### Sierra reference (Michael's screens)

- **5m:** candles + stepped POC/VAH/VAL + IB cyan + CVD bars below on **same time axis**
- **3m:** separate TF — Cockpit default **5m**; compare 5m to 5m only
- **Woodies CCI:** separate P30.10 — do not block SHADOW on this

### Cockpit checklist (`http://127.0.0.1:3000`, Cmd+Shift+R)

- [ ] Chart visible without clicking Max (height ≥720)
- [ ] CVD **inside** chart bottom (not separate pane)
- [ ] Magenta stepped POC + per-period VAH/VAL dashed
- [ ] Silver dashed yesterday POC/VAH/VAL (`/tpo/previous_day`)
- [ ] White prior-day high/low
- [ ] Cyan IB when `curl …/tpo/current` shows `ib_locked: true`
- [ ] Connection: **LIVE** or **STALE** (not DISCONNECTED) when Sierra `live_price.json` fresh

### API probes

```bash
curl -s -m 2 http://127.0.0.1:8000/api/v9/cockpit/heartbeat | python3 -m json.tool | head -20
curl -s -m 2 http://127.0.0.1:8000/api/v9/tpo/current | python3 -c "import json,sys;d=json.load(sys.stdin);print(d.get('source'),d.get('poc'),d.get('ib_locked'))"
curl -s -m 2 http://127.0.0.1:8000/api/v9/chart/bars5min?limit=5 | python3 -c "import json,sys;print(len(json.load(sys.stdin)))"
curl -s -m 2 http://127.0.0.1:8000/api/v9/cumulative_delta/current | python3 -c "import json,sys;d=json.load(sys.stdin);print(len(d.get('points',[])))"
```

---

## §6 — Sierra DLL gaps (coordinate with Michael)

| Export | Issue | CC action |
|--------|-------|-----------|
| `tpo.json` | `ib.found: false` during globex / pre-IB | Verify RTH 10:30–16:00 ET; if still false → ACSIL fix in merged study |
| `cumulative_delta.json` | points use `i` not `ts` | Interim: tail-align (done); ideal: add `ts` per point in DLL |
| `tpo.json` | no native `periods[]` | Interim: DB `v9_tpo_sessions`; ideal: export `periods[]` |

Do **not** fake IB in Python if Sierra says `found: false`.

---

## §7 — SHADOW mode verification (P30.SHADOW)

**Read:** `frontend/v9/src/v9/components/layout/TopBar.tsx` (mode SHADOW), shadow routes, `FiveMinSystem` auto-route to gateway.

### Live UAT

```bash
# Mode
curl -s http://127.0.0.1:8000/api/v9/cockpit/heartbeat | python3 -c "import json,sys;print(json.load(sys.stdin).get('mode'))"

# Systems snapshot < 3s
time curl -s -m 3 http://127.0.0.1:8000/api/v9/cockpit/systems-snapshot -o /dev/null

# Shadow soak
curl -s http://127.0.0.1:8000/api/v9/shadow/soak_progress | python3 -m json.tool

# Gateway status
curl -s http://127.0.0.1:8000/api/v9/gateway/status | python3 -m json.tool
```

### Browser

- TopBar shows **SHADOW** (yellow), not LIVE
- Side panel: systems 1–6 show plausible states (not all `---`)
- Shadow soak strip: Day N/30 progress
- **No** accidental LIVE arm

### Tests

```bash
pytest tests/v9/db/test_api.py -q -k shadow
pytest tests/v9/api/ -q --timeout=30
```

---

## §8 — Redis / WebSocket (P1, not P0 if live_price poll works)

Log shows: `Redis publish failed … Connection refused` on 6379.

- CC: confirm SHADOW works **without** Redis OR document Redis required
- If optional: ensure `ws_manager` does not block request thread (already rate-limited warnings)
- Price WS `/ws/v9/price` — fix or document that **live_price poll** is fallback (Cursor added `useLivePricePoll`)

---

## §9 — Bridge (narrow only)

```bash
# Michael approval assumed for bars-only
cd /Users/michael/Downloads/mems26_web_git
CLOUD_URL=http://localhost:8000 V9_SKIP_HISTORY=1 python3 bridge/json_bridge.py --bars-5min-only
```

Verify: `POST /api/v9/bars/5min` 200, chart latest bar advances, **backend stays responsive** (heartbeat <2s during POST).

---

## §10 — Files to create/update

| File | Action |
|------|--------|
| `docs/reports/PROMPT30_BACKEND_HANG.md` | CREATE if hang fixed |
| `docs/reports/PROMPT30_9_SIERRA_SCREEN_PARITY.md` | UPDATE status + Michael visual sign-off |
| `docs/reports/P30_ROADMAP.md` | UPDATE all rows through SHADOW |
| `docs/reports/PROMPT30_SHADOW_READY.md` | CREATE — single SHADOW GREEN checklist |
| `tests/v9/api/test_backend_responsive_under_load.py` | CREATE if hang fixed |

---

## §11 — Deliverables for Michael (end of CC run)

Reply with:

1. **P0 backend hang:** root cause + fix Y/N + pytest output
2. **Visual:** PASS/FAIL vs checklist §5 (need Michael screenshot if FAIL)
3. **SHADOW:** PASS/FAIL table (heartbeat, snapshot, soak, mode, gateway)
4. **Roadmap:** updated `P30_ROADMAP.md` paste
5. **Single blocker** if not 100% today
6. **Exact commands** Michael runs tomorrow morning (start backend, bridge, open URL)

---

## §12 — Order of execution (one thread)

```
P0 backend hang → P0 heartbeat/bars5min <2s → visual API probes →
SHADOW UAT → bridge bars-only soak 5min → docs → Michael visual sign-off
```

Do **not** start P30.10 Woodies until P30.9 visual GREEN or Michael explicitly defers.

---

*End mega prompt — paste §1–§12 to Claude Code.*
