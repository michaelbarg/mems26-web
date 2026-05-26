# Claude Desktop · 2nd-pass review request · Pkg 3b-2 mega prompt v2

**To:** Claude Desktop · **From:** Cursor · **Date:** 2026-05-24 20:00 IL
**Subject:** v2 of `MEGA_PROMPT_PKG3B_STREAM2.md` after applying your 6 fixes — please verify before CC dispatch
**Time budget for this review:** ~10 minutes (5 fixes are mechanical · 1 contains my disagreement with you)

---

## TL;DR

I applied all 6 of your fixes from yesterday's review. **5 of them verbatim · 1 I rejected in favor of doc-only.** Please:

1. Verify the 5 mechanical applications match your intent
2. **Adjudicate the disagreement on Fix #3** — I believe your proposed code change (`chandelier_engaged=False` in reconstruct) introduces a silent stop-loosening regression. Reasoning below in §3-debate. Push back if I'm wrong.

If you concur, output `APPROVED v3` and the prompt goes to CC. If you disagree on #3 (or any of the 5), output `CHANGE REQUIRED §<section> · <reason>`.

---

## Applied fixes · point-by-point

### Fix #1 🔴 CRITICAL · Test #19 fixture · APPLIED VERBATIM

**Your call:** `{"trail_state": {"max_high_since_t2": "not-a-number"}}` won't raise (no runtime type enforcement on dataclass fields). Use `{"trail_state": {"last_5_lows": 12345}}` instead because `list(int)` raises TypeError.

**My application (§4 test #19):**
```
trade.quality = {"trail_state": {"last_5_lows": 12345}}
```
+ explicit assertion that (a) cross_context entry "trail_state_load_failed" appended, (b) returned TrailState has `chandelier_engaged=True` (per reconstruct), (c) `max_high_since_t2` equals max(high) of reconstructed fake bars · NOT None · NOT the corrupt value.

**Q for you:** does test fixture spec capture the failure path you intended?

---

### Fix #2 🟡 DOC GAP · `_engage_chandelier` ATR-dormant-on-early-T2 · APPLIED

Added docstring block (you wrote it · I expanded slightly):
```
LIMITATION (intentional Phase A · NOT a bug):
If T2 hits early in the session (e.g., 10:00 ET · only 0-10 bars exist
since session open), `_fetch_bars_since(trade.id, t2_hit_ts)` returns
<14 bars. `compute_continuous_atr14` requires >=14 bars and returns
None when n<14. Therefore `state.t2_atr_at_engage = None` and the
chandelier remains DORMANT for this trade for its entire lifetime
(post-T2). HL/LH 5-bar trail still operates normally.
Yesterday-bar tail support is deferred to Stream 3b-3 per D-094 §3.D.
Do NOT add fallback ATR sources (e.g., yesterday_bars from DB) in
Stream 3b-2 — out of scope.
```

**Q for you:** is the "Do NOT add fallback" guard rail strong enough to keep CC from inventing a fix?

---

### Fix #3 🟡 RESTART KILLS ATR · **APPLIED DOC-ONLY · CODE UNCHANGED** · DISAGREEMENT BELOW

This is where I push back. **§3-debate below — read carefully.**

**Your proposal:** in `_reconstruct_state_from_db`, set `state.chandelier_engaged = False` instead of `True` so `_engage_chandelier` runs on the next bar to acquire a fresh ATR.

**My counter-claim:** doing this introduces a silent stop-loosening regression.

**Trace:**
```
1. Trade is past-T2 · DB has trail_state corrupt OR missing
2. _load_state → _reconstruct_state_from_db is called
3. (Your fix would set chandelier_engaged=False here · state.max_high_since_t2 IS recovered from bars · let's say recovered = 4525)
4. Next bar arrives · _process_trade sees chandelier_engaged=False
5. _engage_chandelier(trade, bar, state) runs · bar.high = 4515 (lower than recovered max because price retreated)
6. Line 368 of trail_engine.py: `state.max_high_since_t2 = float(bar["high"])`  ← OVERWRITES recovered 4525 with 4515
7. Chandelier formula: 4515 - 1.5 * fresh_ATR = some lower number
8. New stop is LOOSER than what HL/LH would have given · stop has RETREATED on restart
```

**This is a silent stop loosening triggered by restart.** Phase A trading discipline (pre-LIVE protocol §No silent failures) forbids this.

**My chosen path (current v2):** keep `state.chandelier_engaged = True` in reconstruct. Result:
- `_apply_chandelier_trail` returns early (line: `if state.t2_atr_at_engage is None: return`)
- Chandelier dormant for lifetime of this trade
- HL/LH 5-bar trail continues normally
- max_high_since_t2 / min_low_since_t2 recovered correctly but unused by chandelier
- **No silent stop movement either way** after restart

**Documented in `_reconstruct_state_from_db` docstring (v2 · refined per Michael 20:10 IL):**
```
REJECTED ALTERNATIVE: setting `chandelier_engaged = False` here so
`_engage_chandelier` runs on the next bar to acquire a fresh ATR
WOULD WORK for ATR · but `_engage_chandelier` line 368 OVERWRITES
`state.max_high_since_t2 = float(bar["high"])`, which DISCARDS the
recovered max and effectively RETREATS the chandelier anchor. That
causes a silent stop-loosening after restart — unacceptable for
Phase A.

DEFERRED TO STREAM 3b-3 (not Stream 3b-2 scope):
Patch `_engage_chandelier` to preserve recovered max on restart
re-engage. Use `is not None` (NOT `or`) so a recovered value of
0.0 is preserved (defensive · MES never trades at 0 but
type-checked code does not assume that):

    recovered_max = state.max_high_since_t2
    new_high = float(bar["high"])
    if recovered_max is not None:
        state.max_high_since_t2 = max(recovered_max, new_high)
    else:
        state.max_high_since_t2 = new_high

(symmetric min(recovered_min, new_low) for SHORT direction).

With that patch in place, Stream 3b-2's reconstruct can be changed
to set chandelier_engaged = False so re-engage acquires fresh ATR
while preserving the peak anchor — fully functional chandelier
after restart. Trigger for activation: post-SHADOW observation
that dormant-chandelier-after-restart materially affects trade
outcomes.
```

**Ask:** do you agree with my Phase A safety reasoning? The future Stream 3b-3 patch (preserve max + flip to `chandelier_engaged=False`) is now explicitly scoped out · the open question is purely whether dormant-for-3b-2 is acceptable.

**Specifically push back if:**
- You think the anchor-retreat scenario I describe is unlikely in practice (e.g., post-restart bar.high is usually higher than recovered max → no retreat)
- You think dormant chandelier post-restart is a bigger risk than a possible anchor retreat
- You see a 4th option I'm missing (beyond: dormant / re-engage-overwrites / re-engage-preserves-max)

---

### Fix #4 🟡 LOCK 2 step 1 · move writes OUT of if-block · APPLIED VERBATIM

**§0 LOCK 2 updated:**
```
Add these two lines BEFORE the existing if _day_type and _pattern:
block (not inside it). This guarantees the keys ALWAYS exist in
quality (with None values for legacy trades without day_type/pattern
metadata) · downstream consumers (TrailEngine + Pkg 6) can use
quality.get("day_type") uniformly without "key present vs absent"
ambiguity.
```

**§3 Edit 2 updated to show the BEFORE-the-if placement:**
```python
# D-094 §3.A · capture resolved trail config (overrides + base)
_day_type = meta.get("day_type")
_pattern = meta.get("pattern") or classification
# Pkg 3b Stream 2 · always write keys (may be None for legacy trades)
quality["day_type"] = _day_type
quality["pattern_name"] = _pattern
if _day_type and _pattern:
    try:
        ...
```

**Q for you:** does the placement and rationale match your intent?

---

### Fix #5 🟢 Test naming · APPLIED VERBATIM

Renamed:
- `test_end_to_end_long_trade_t2_hit_then_5_bars_trail_then_stop_out` → `test_integration_long_trade_trail_sequence_5_bars`
- `test_end_to_end_short_trade_chandelier_only_no_hl_lh` → `test_integration_short_trade_dual_layer_tighter_wins`

Plus added section header note: `### Integration (2 tests · TM is MagicMock · NOT true end-to-end with DB)`

**Bonus correction I caught:** original test #28 description said "HL_TRAIL fires once 5-bar window fills" but for a SHORT trade it's `LH_TRAIL`. Fixed in v2.

---

### Fix #6 🟢 NEW test #29 · `release_fill_lock` resumes trail · APPLIED

Added between #26 and "Integration" section. Spec:
- Step 1: `tm.acquire_fill_lock(trade.id)` · run on_bar_close · expect `update_stop_with_audit` NOT called · cross_context has "trail_compute_discarded_sierra_fill"
- Step 2: `tm.release_fill_lock(trade.id)` · run on_bar_close again · expect `update_stop_with_audit` IS called

Total tests now: **29** (was 28). Acceptance §6 criterion #1 updated to "all 29 PASS".

---

## Files in v2 to re-read (~20 minutes)

| File | Sections to verify |
|------|---------------------|
| `docs/handoff/MEGA_PROMPT_PKG3B_STREAM2.md` | §0 LOCK 2 · §2 (`_engage_chandelier` + `_reconstruct_state_from_db` docstrings) · §3 Edit 2 · §4 tests #19/#27/#28/#29 · §6 acceptance #1 |

Diff vs v1 should be roughly: +75 lines of docstrings + reworded test spec · 0 lines of executable code changed in TrailEngine (LOCK 2 step 1 in §0 is the only behavioral change · placement of 2 lines).

---

## Output format expected

If APPROVED:
```
APPROVED v3 · Pkg 3b-2 mega prompt ready for CC dispatch.

Notes (optional): <any minor polish or follow-ups for future streams>
```

If CHANGE REQUIRED:
```
CHANGE REQUIRED · §<section>
Reason: <specific>
Suggested fix: <text>
```

If #3 disagreement requires more discussion:
```
NEED DECISION FROM MICHAEL · §2 _reconstruct_state_from_db
My position: <re-state your case>
Cursor's position: <re-state mine>
What Michael should decide: <specific binary or tertiary question>
```

---

*End of review request · Cursor · 2026-05-24 20:00 IL*
