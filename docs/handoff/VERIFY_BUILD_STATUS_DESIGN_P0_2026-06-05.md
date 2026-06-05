# VERIFY — Build Status Design P0 · 2026-06-05

## B-11: bridge_inspector.py ORDER BY rowid → {ts_col}

### Fix
`bridge_inspector.py:82,204` — both `ORDER BY rowid DESC` replaced with `ORDER BY {ts_col} DESC`.

### Command + raw output
```
$ grep -n "ORDER BY" backend/v9/systems/build_status/bridge_inspector.py
82:            f"SELECT {ts_col} FROM {table} ORDER BY {ts_col} DESC LIMIT 1"
204:            f"SELECT {ts_col} FROM {table} ORDER BY {ts_col} DESC LIMIT 1"
```

### Regression test (revert → RED)
```
$ BRIDGE_TOKEN=test python3 -m pytest tests/v9/systems/test_bridge_inspector_b11.py -v --no-header
tests/v9/systems/test_bridge_inspector_b11.py::test_no_rowid_in_order_by PASSED [ 50%]
tests/v9/systems/test_bridge_inspector_b11.py::test_order_by_uses_ts_col PASSED [100%]
======================== 2 passed, 2 warnings in 0.07s =========================
```

Test `test_no_rowid_in_order_by` asserts zero `ORDER BY rowid` matches — revert → RED.
Test `test_order_by_uses_ts_col` asserts exactly 2 `ORDER BY {ts_col} DESC` — revert → RED.

### Verification
- Streams will show live (FRESH/WARMING) when bridge is running and DB is Postgres.
- Bridge will not show OFFLINE/DEAD/0-armed falsely.
- **No live screenshot** — backend not running in this session. Cowork should verify at next RTH.

---

## Stale-handling: Root cause + UI distinction

### Root cause
`state_fresh` in `woodies_inspector.py:224-225` is anchored at `last_bar_ts` — the timestamp of the latest valid 5-min bar in `v9_bars_5min_woodies`. Between bar boundaries, this timestamp ages from 0→~300s (5 minutes). All Woodies components (`pattern_specific`, `r_t1`, `stop`, `targets`, `ready_to_route`) use `state_fresh`, so they show stale ~5m between bars.

Meanwhile, `day_type_gate` (line 300) uses `eval_fresh = freshness_now("inspector_eval")` — wall-clock, always <1s.

**This is correct behavior** — Woodies data genuinely hasn't changed since the last 5-min bar. The problem was purely UI: binary fresh/stale without explaining expected aging.

### UI fix
- **3-tier freshness system**: FRESH (<60s, green), WARMING (60s–threshold, amber), STALE (>threshold, red)
- `SourcesStrip`: each system card shows tier color + "ממתין לבר הבא — נתון תקין" for WARMING
- `SystemBranch` header: lag colored by tier, ⏳ icon for WARMING
- `SystemBranch` source step: WARMING step shows "wait" icon, explains "נתון 5-דקות מתיישן בין ברים"
- `ComponentTable`: new "freshness" column showing per-component lag with tier-colored pill

### Command + raw output (typecheck)
```
$ npx tsc --noEmit --pretty 2>&1 | grep "build_tree"
(no output — zero errors in BuildTreeView.tsx)
```

Pre-existing errors (not introduced by this change):
- `PriceDebugConsole.tsx:90` — correlation_id
- `api.ts:47` — type cast

---

## P0: pre_fire_validator + risk_checks — structured rendering

### Change
Replaced generic `GateCard` placeholder with structured `GlobalFirewall` component:
- **pre_fire_validator**: 7 checks rendered as individual table rows (side_match, ordering, r_r_gate, confidence, time_stop, not_provisional, dedup) with spec/required/status/source columns
- **risk_checks**: 6 caps rendered as individual table rows (daily_loss <$250, max_trades ≤5, max_contracts ≤2, cutoff 14:30 ET, consec_losses <2, news_block ±10m)
- Each row shows ⧗ (pending) when no live data, or ✓/✕ when backend exposes the component
- Removed dead `GateCard` component

### Typecheck: 0 new errors (same 2 pre-existing)

---

## P0: Day-Type Matrix S4 verdict

### Change
New `DayTypeMatrixVerdict` component rendered between gates and verdict steps for S4 (Woodies):
- Shows active day type + entry_hint + t1_ref
- Per-pattern verdict: ✅/⚠️/❌ based on pattern×day_type compatibility from targets_table config
- Prefers live `day_type_matrix` component from backend when available
- Falls back to static config-derived verdict with note "verdict מחושב מטבלת-אפיון סטטית"
- All 9 Woodies patterns shown: ZLR, GB100, GB50, RB100, RB50, TLB, HFE, FAMIR, GHOST

### Typecheck: 0 new errors

---

## P0: S5 (TPO) + S6 (Killzone) wiring

### Change
`ObserverCards` now accepts `data: BuildStatusResponse` and wires S5/S6:
- **S5 TPO**: When `tpo` system exists in response, renders live gates (✓/✕ per gate). When not wired, shows pending with inspector creation path. **A5 marked as advisory** — "A5 = advisory בלבד (לא חוסם ירי)" shown in both wired and unwired states.
- **S6 Killzone**: When `killzone` system exists in response, renders live gates + interpretations. When not wired, shows pending.
- Both fall back gracefully when inspectors don't exist yet.

### Typecheck: 0 new errors

---

## NOT-DONE

1. **S5/S6 full inspector creation** — `tpo_inspector.py` and `killzone_inspector.py` don't exist yet in backend. UI is ready to consume them when they're wired to the aggregator.
2. **S2/S3 full decision tree** — building the complete A1-A7 tree per system (I-10) is a separate task.
3. **Live screenshot** — backend not running in this session; Cowork must verify visually at next RTH.
4. **pre_fire_validator/risk_checks live data** — backend doesn't expose these through the endpoint yet (gap-list P0). UI is wired to show live status when exposed.
5. **A7 anti-patterns / dispatch** — noted as pending in gates step for S4.
