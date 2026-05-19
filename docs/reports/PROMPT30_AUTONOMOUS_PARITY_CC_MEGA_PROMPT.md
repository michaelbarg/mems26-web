# P30 — Autonomous Sierra Parity + SHADOW (CC Mega Prompt)

**Date:** 2026-05-19  
**Repo:** `/Users/michael/Downloads/mems26_web_git`  
**Branch:** `stabilize/mems26-local-truth-2026-05-16`  
**Michael does NOT run visual QA.** CC owns bring-up, bridge, API 4-axis UAT, browser checklist, and numeric parity vs Sierra exports + design spec.

**Last autonomous run (Cursor 2026-05-19):** §4–§6 GREEN; bridge bars-only running; P30.SHADOW PARTIAL (soak go pending 10+ min evidence). G1 IB deferred until Sierra `ib.found=true` at RTH.

---

## §0 — What Michael is NOT doing

- No “does it look right?” screenshots for Michael unless **all automated checks pass** and you need a **single strategic** sign-off for SHADOW soak start.
- No manual Max-click workaround as acceptance — chart must load at default height (≥720) without user ritual.
- No full 12-stream bridge without explicit written OK from Michael.

**Acceptance = PASS on every row in §7 tables.** FAIL → fix in repo, re-run §6, update reports. Do not ask Michael to eyeball magenta vs cyan.

---

## §1 — Design authority (read first)

| Doc | Role |
|-----|------|
| `docs/design/MEMS26_COCKPIT_V5_DESIGN_SPEC.md` | Visual tokens, hierarchy, chart overlay behavior |
| `docs/reports/PROMPT30_9_SIERRA_SCREEN_PARITY.md` | P30.9 scope + Sierra data path |
| `docs/reports/PROMPT30_9c_CHART_SIERRA_ALIGNMENT_CC.md` | Chart checklist (G1–G5) |
| `docs/reports/PROMPT30_SHADOW_GATE_CC_MEGA_PROMPT.md` | SHADOW end-to-end gate |

**Compare Cockpit 5m to Sierra 5m only.** Woodies CCI panel = P30.10 (defer for SHADOW gate unless trivial).

---

## §2 — Safety

- `CLOUD_URL=http://localhost:8000` only (`bridge/v9_streams/base_stream.py` enforces).
- Bridge: `--bars-5min-only`, `V9_SKIP_HISTORY=1`, `V9_DISABLE_WATCHDOG=1`.
- No LIVE, no `trade_command.json`, no LaunchAgent plist edits.
- Check `lsof -nP -iTCP:8000` and `:3000` before starting duplicates.

---

## §3 — Bring-up (CC runs all of this)

```bash
REPO=/Users/michael/Downloads/mems26_web_git
SIERRA=/Users/michael/SierraChart_Data/v9_export

# 1) Sierra files fresh (<120s during RTH; OK pre-market if market closed)
ls -la "$SIERRA/5min.json" "$SIERRA/tpo.json" "$SIERRA/cumulative_delta.json"

# 2) Backend responsive (<2s) — if ANY curl hangs or http=000, restart P0 first
curl -m 2 -s -o /dev/null -w "heartbeat %{http_code} %{time_total}s\n" \
  http://127.0.0.1:8000/api/v9/cockpit/heartbeat
curl -m 5 -s "http://127.0.0.1:8000/api/v9/chart/bars5min?limit=3" | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print('bars',len(d), d[-1]['ts'] if d else 'EMPTY')"

# 3) If backend dead/hung:
lsof -tiTCP:8000 | xargs kill -TERM 2>/dev/null; sleep 2
cd "$REPO" && set -a && source .env && set +a
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
sleep 3
# Re-run heartbeat + bars5min until both <2s / 200

# 4) Frontend (only if 3000 down)
# cd "$REPO/frontend/v9" && npm run dev  # if needed

# 5) Bridge bars-only (if not already running)
cd "$REPO/bridge"
set -a && source ../.env && set +a
export CLOUD_URL=http://localhost:8000
export V9_DISABLE_WATCHDOG=1
export V9_SKIP_HISTORY=1
pgrep -fl "json_bridge.py --bars-5min-only" || \
  exec python3 json_bridge.py --bars-5min-only
```

**P0 deliverable:** Root-cause backend hang + `tests/v9/api/test_backend_responsive_under_load.py` — see `PROMPT30_SHADOW_GATE_CC_MEGA_PROMPT.md` §4.

---

## §4 — API 4-axis (every endpoint, scripted)

For each: **Quality** (schema + no garbage), **Recency** (`latest == MAX(ts)` in DB or Sierra file mtime), **Cardinality** (`len == limit`), **Latency** (`<2s`).

```bash
LIMIT=600
# bars5min
curl -m 5 -s "http://127.0.0.1:8000/api/v9/chart/bars5min?limit=$LIMIT" | python3 <<'PY'
import json,sys,sqlite3
from pathlib import Path
raw=json.load(sys.stdin)
bars=raw if isinstance(raw,list) else raw.get("bars",[])
print("cardinality", len(bars), "want", 600)
if bars:
  print("recency_endpoint", bars[-1].get("ts"))
db=Path("/Users/michael/Downloads/mems26_web_git/data/mems26_local.db")
if db.exists():
  c=sqlite3.connect(db).execute("SELECT MAX(ts) FROM v9_bars_5min").fetchone()[0]
  print("recency_db_max", c)
PY

# tpo/current — source must be sierra_tpo_json; ib_* null when ib.found false
curl -m 5 -s http://127.0.0.1:8000/api/v9/tpo/current | python3 -m json.tool | head -40

# tpo/previous_day
curl -m 5 -s http://127.0.0.1:8000/api/v9/tpo/previous_day | python3 -m json.tool

# cumulative_delta/current
curl -m 5 -s http://127.0.0.1:8000/api/v9/cumulative_delta/current | python3 -c \
  "import json,sys;d=json.load(sys.stdin);print('points',len(d.get('points',[])),'source',d.get('source'))"

pytest tests/v9/api/test_tpo_routes_sierra_contract.py \
       tests/v9/api/test_cumulative_delta_routes.py \
       tests/v9/api/test_chart_bars5min_integrity.py -q
```

---

## §5 — Numeric parity vs Sierra files (no screenshots)

Read Sierra JSON and API; assert **±0.25** on MES prices:

```bash
python3 <<'PY'
import json, urllib.request
from pathlib import Path

sierra = Path("/Users/michael/SierraChart_Data/v9_export/tpo.json")
tpo = json.loads(sierra.read_text())
api = json.loads(urllib.request.urlopen("http://127.0.0.1:8000/api/v9/tpo/current", timeout=5).read())

def close(a, b, tol=0.25):
    if a is None and b is None: return True
    if a is None or b is None: return False
    return abs(float(a)-float(b)) <= tol

sess = tpo.get("session", {})
for k in ("poc", "vah", "val"):
    sk, ak = k, {"poc":"poc","vah":"vah","val":"val"}[k]
    sv = sess.get(sk) or sess.get(sk+"_price")
    av = api.get(ak)
    ok = close(sv, av)
    print(f"session.{k}", "sierra", sv, "api", av, "PASS" if ok else "FAIL")

ib = tpo.get("ib", {})
if ib.get("found"):
    for k in ("high","low"):
        print(f"ib.{k}", ib.get(k), api.get(f"ib_{k}"), "PASS" if close(ib.get(k), api.get(f"ib_{k}")) else "FAIL")
else:
    print("ib.found false — expect api ib_* null:", api.get("ib_high"), api.get("ib_low"))
PY
```

**Do not fake IB in backend** when Sierra has `ib.found: false`. G1 = Sierra DLL / RTH only.

---

## §6 — Browser UAT (CC, not Michael)

1. Open `http://127.0.0.1:3000` — hard refresh once.
2. Confirm **5m** selected; chart area non-empty (candles visible) without clicking Max.
3. DevTools console: **zero** `ChartV5b load error`.
4. Structural checklist (PASS/FAIL each):
   - CVD histogram **inside** chart (same pan/zoom as candles), no separate pane below.
   - Stepped POC segments (magenta family per overlay code).
   - Today VAH/VAL dashed; yesterday from `/tpo/previous_day` (silver dashed).
   - Prior-day high/low white.
   - Cyan IB **only** when API `ib_high`/`ib_low` non-null.
5. Optional screenshot **only on FAIL** → attach to report with failing checklist row.

**DISCONNECTED** in top bar: document separately (WS/Redis). Does not block P30.9 chart parity if `live_price` poll works.

---

## §7 — SHADOW gate (after P30.9 GREEN)

From `PROMPT30_SHADOW_GATE_CC_MEGA_PROMPT.md`:

- TopBar mode SHADOW visible
- Systems snapshot / soak strip respond <2s
- 10+ min soak: heartbeat + bars5min never exceed 2s
- Update `P30_ROADMAP.md`, `PROMPT30_9_*.md`, `PROMPT30_SHADOW_GATE_CC_MEGA_PROMPT.md` with evidence tables

Michael involvement: **one message** “SHADOW soak go” only when §4–§6 all GREEN.

---

## §8 — Code map (if fixes needed)

| Layer | Path |
|-------|------|
| Chart | `frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx`, `SierraLevelsOverlay.tsx`, `cvdMapping.ts` |
| TPO API | `backend/v9/api/v9/tpo_routes.py` |
| CVD API | `backend/v9/api/v9/cumulative_delta_routes.py` |
| Bars ingest | `backend/v9/api/v9/bars.py`, bridge `json_bridge.py --bars-5min-only` |
| Sierra DLL | `sc_study/MES_AI_DataExport_merged.cpp` (IB export, CVD `ts`) |

---

## §9 — Deliverables

1. `docs/reports/PROMPT30_9_SIERRA_SCREEN_PARITY.md` — status GREEN/PARTIAL with §4–§6 evidence
2. `docs/reports/PROMPT30_BACKEND_HANG.md` — if P0 touched
3. `P30_ROADMAP.md` — P30.9c visual = CC verified (not “pending Michael”)
4. Paste terminal + pytest summary in report; screenshot only if FAIL

*End — copy §0–§9 to Claude Code and execute without asking Michael to compare screenshots.*
