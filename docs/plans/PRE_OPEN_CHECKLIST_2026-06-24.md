# MEMS26 — Pre-Open Checklist · 2026-06-24
_Prepared 2026-06-23 EOD (Cowork). SHADOW session — no real orders._

## ✅ DONE + VERIFIED today (independent agent audit — all green)
- **DIRECTION_CONTEXT** ✅ ON — blocks fires AGAINST the live CVD+breakout direction. Backtest +$2,817 (excl in-progress); blocks 19 losers / 12 winners.
- **HTLB_DIRECTION_GATE** ✅ ON — HTLB's zoned break sets the directional bias for ALL Woodies patterns (latched until next HTLB). Backtest +$1,769.
- **TLB_SPEC_V2** ✅ ON — fire TLB per your source spec (±200/SWI extreme + CONT partner). **Michael override** of the negative backtest → SHADOW-observe.
- Canonical **flag index** (50 flags, 0 drift) · **9 regression tests pass** · **fire-compliance monitor** (matches DB 1:1, 13 fires today) · **full-Woodies replay** (CCI/TCCI/SWI/CZI/±200 + LSMA/EMA/Proj).
- Patterns implemented per your characterization: **TLB** (v2), **HTLB** (direction signal).

## 🔧 MUST FIX before open — day-type / trend system
- **Root (diagnosed):** the S1-NEW-CLS promotion (→ correct **Normal**) needs ≥12 live RTH bars in an in-memory buffer (`_cls_rth_bars`). Today's restarts wiped it; the post-close restart left it empty → the OLD engine's **Trend_Normal** leaked into `direction_now`. The canonical classifier itself is correct (Normal in all 67 windows of 06-23).
- **Fix:** rehydrate `_cls_rth_bars` from the DB (`v9_bars_5min_woodies`, today's RTH) when IB is locked but the buffer is short — at `backend/main.py:391`, mirroring the existing `maybe_seed_ib_from_tpo` restart-seed. + regression test (post-restart persisted day_type == classify_replay.final). **Trading-surface → Michael sign-off.**
- **Operational rule until the fix lands:** **do NOT restart the backend mid-session** (it starves the promotion). Without a mid-session restart, the day-type classifies correctly tomorrow as-is.

## 📋 PATTERNS — go over ALL per your spec (goal: before open)
Done: **TLB** ✅ · **HTLB** ✅. Next: **HFE** (add the level-confluence gate — "hook without a daily level = trap"). Remaining (source-vs-code gaps in `docs/spec_authority/WOODIES_PATTERNS_SOURCE_VS_CODE_2026-06-23.md`):
- **ZLR** — code floor ±100, spec wants ±200; no SWI/CZI/TCCI confirm.
- **TT** — missing EMA-34 close-confirm + Stage-2 pause.
- **GB100** — missing mandatory CZI alignment; stop should be 1.2×ATR.
- **VEGAS** — only divergence (no ±200→cup→handle→break); no day-type gate.
- **GHOST** — no diagonal neckline; no ZL containment; no day-type gate.
- **FAMIR** — no "prior ZLR Stage-3 fire" precondition; no ±50 qualifier.
- _(DBDT is NOT a Woodies pattern — it's an S1 day-type bucket.)_

## 🩺 PRE-OPEN HEALTH (T-30 · per docs/runbooks/PRE_TRADE_PROTOCOL.md)
- Bridge + backend(:8000) + frontend(:3000) up (`bash scripts/start_all.sh` — idempotent). **Don't restart mid-session.**
- `curl localhost:8000/health` → ok; all `~/SierraChart_Data/v9_export/*.json` fresh (<5s); `direction_now` sane.
- Flags live in `.env`: DIRECTION_CONTEXT, HTLB_DIRECTION_GATE, TLB_SPEC_V2 (+ the S1 calibration flags).

## 🧹 EOD / housekeeping
- Disable the `fire-compliance-monitor-2026-06-23` scheduled task (today-only) or repoint to 06-24.
- **Commit** today's work — branch is uncommitted (CC to commit + push).
