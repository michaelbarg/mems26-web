# Wave 3 — SHADOW Soak (Michael + CC)

**Role:** SHADOW-OPS — **no Cursor code**  
**Precondition:** G0 + (P1/P1.5 optional per Michael) + Michael **P-S0** sign-off  
**Duration:** 5–10 RTH trading days  
**Deliverables:** `docs/reports/shadow/SHADOW_SOAK_DAY_XX.md` → `SHADOW_SOAK_FINAL.md`

---

## What runs in SHADOW

| System | Behavior | Note |
|--------|----------|------|
| S2 Five-Min | T1 → gateway → SHADOW record | pre_fire verified |
| S4 Woodies | T2 → SHADOW | HFE tuning deferred (D-084) |
| S3 Footprint | May fire → SHADOW record only | **D-086 tolerated** — not full TM lifecycle |
| S1 Day Type | Classification / Plan context | observer |
| S5/S6 | Observer / gates | no LIVE |

## What does NOT run

- LIVE / DEMO execution
- V6 §11 Analyst agent (`shadow_analyst.py` — not built)
- V6 §8 Pre-flight UI
- S3 spec fix (post-SHADOW)
- DLL / bridge / frontend changes without Michael

---

## Michael (daily EOD, ~10 min)

| # | Action |
|---|--------|
| 1 | Export or note SHADOW trades / journal rows for the session |
| 2 | Compare Plan vs snapshot for S1/S4 anomalies |
| 3 | One line: GO / WATCH / STOP for next day |
| 4 | File `SHADOW_SOAK_DAY_XX.md` (template below) |

---

## CC (morning health, ~15 min)

| # | Check |
|---|--------|
| 1 | `127.0.0.1:8000` up, snapshot &lt; 500ms |
| 2 | Bridge heartbeat / streams (baseline 12/12 or documented gap) |
| 3 | No `API push FAILED to https://` in `/tmp/bridge.err.log` |
| 4 | Footprint journal 0 new SQLite thread errors |
| 5 | `sierra_match_tool` if Michael requests |

Paste results into day file or `P30_SHADOW_HEALTH_YYYY-MM-DD.md`.

---

## Day file template

`docs/reports/shadow/SHADOW_SOAK_DAY_01.md`:

```markdown
# SHADOW Soak — Day 01 (YYYY-MM-DD)

**Session verdict:** GO / WATCH / STOP

## Michael EOD
- SHADOW fires observed (S2/S3/S4): …
- Manual notes: …

## CC morning
- HTTP latency: …
- Bridge: …
- Registry: unchanged / …

## Incidents
- …

## D-086 S3
- Count / sample ids: …
```

---

## Stop criteria (escalate to Michael + Parent)

- Gateway latency &gt; 2s sustained
- SHADOW DB write failures
- Unexpected LIVE path or `V9_PAPER_MODE` drift
- Bridge pushing non-localhost

---

## End of soak

Michael reviews all day files → `SHADOW_SOAK_FINAL.md` → decides:

- Open Wave 4 (6 parallel audits)
- D-086 Option A/B/V4
- L4 risk audit
- Registry triage (if D-087 was waiver A)

---

*Ops only · Wave 3 · 2026-05-20*
