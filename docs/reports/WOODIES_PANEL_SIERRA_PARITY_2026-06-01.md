# Woodies Panel ↔ Sierra Chart 12 Parity · 2026-06-01

**Date:** 2026-06-01 · **Author:** CC · **Mode:** READ-ONLY diagnosis + smallest fix

---

## Root Cause

**Chart 12 is RTH-only.** The DLL exports `woodies_5min.json` every ~3s (`export_ts` is current), BUT all **study values** (CCI, TCCI, SWI, CZI, LSMA, EMA, Projections, trend_state) are **frozen at the last RTH bar** (May 29 15:55 ET). This is because:

1. Chart 12 has RTH session → its bar array stops at RTH close
2. The Woodies studies (CCI-14, TCCI-6, etc.) are computed on chart bars → they freeze
3. The DLL correctly reads these frozen values → exports them to JSON
4. The file mtime updates (DLL writes every 3s) but **content doesn't change**

**The existing stale detection only checked file mtime** — which was always fresh (< 30s). It didn't detect that the CONTENT was from a different session.

## Field Map: Panel → Export → Sierra

| Panel Field | Export Key | Current Value | Sierra Chart 12 (Michael) | Match? |
|-------------|-----------|---------------|---------------------------|--------|
| Price (Last) | `current_bar.close` | **7609.62** (live midpoint injected) | 7610.00 | ✅ ~match |
| CCI-14 | `cci_14` | 74.85 | -103.86 | ❌ **STALE** (May 29 RTH) |
| TCCI (CCI-6) | `cci_6_tcci` | 127.42 | (live, different) | ❌ **STALE** |
| CCIDiff | computed: cci_14 - tcci | -52.57 | 54.29 | ❌ **STALE** |
| Trend State | `trend_state` | RED | (live) | ❌ **STALE** |
| SWI | `swi_value` | 72.05 | (live) | ❌ **STALE** |
| CZI | `czi_value` | -4.0 | (live) | ❌ **STALE** |
| LSMA | `lsma_value` | 7422.17 | (live) | ❌ **STALE** |
| EMA-34 | `ema_34` | 7427.25 | (live) | ❌ **STALE** |
| Proj Hi | `proj_hi` | 7653.25 | 7909.00 | ❌ **STALE** |
| Proj Lo | `proj_lo` | 7545.50 | 7310.25 | ❌ **STALE** |
| Timeline | `bars[].ts` | May 29 11:50-14:55 | June 1 (live) | ❌ **STALE** |

**All study fields are exported by the DLL** — nothing is missing from the export. The issue is that chart 12's studies are RTH-only.

## Fix Applied

### Content-based staleness detection (backend)
`woodies_chart_routes.py`: Added check — if latest bar is >1h old (different session), mark studies as stale:

```python
content_age_s = time.time() - latest_ts
if content_age_s > 3600:  # >1h = previous session
    out["studies_stale"] = True
    out["studies_badge"] = f"Last RTH · {bar_date}"
```

**Result:**
```json
{
  "stale": false,           // file is fresh (mtime)
  "studies_stale": true,    // content is from previous RTH
  "studies_badge": "Last RTH · 2026-05-29",
  "live_price": 7609.62     // current market price (live)
}
```

The frontend panel can now distinguish "file fresh + studies stale" and show the badge.

## Why Not Get Live Woodies from Chart #5?

Chart #5 exports OHLCV + CVD but **does not have Woodies studies** (CCI-14, TCCI, SWI, etc.) loaded. To get live Woodies during overnight would require:

1. **Add Woodies studies to chart #5 in Sierra** (CCI, TCCI, LSMA, SWI, CZI, EMA, Pivot Points)
2. **Add cross-chart study reading** in the DLL (like existing Woodies reading from chart 12, but from chart #5)

This is a **Sierra configuration + DLL change** — feasible but requires Michael's decision. The benefit is limited: Woodies patterns (D-092) are RTH-gated, so overnight CCI is for **context only**, not for firing.

## Classification

| Finding | Type |
|---------|------|
| Study values frozen overnight | **Expected** (chart 12 = RTH session) |
| File mtime stale detection missed content | **BUG** (fixed: content-based check) |
| Panel showed "fresh" data that was actually from May 29 | **UX** (fixed: `studies_badge`) |
| No live Woodies during overnight | **GAP-IN-SPEC** (needs Sierra config change for chart #5) |

## Verification During RTH

At RTH open (09:30 ET / 16:30 IL):
- [ ] `woodies_5min.json` bars should have TODAY's timestamps
- [ ] `studies_stale` should become `false`
- [ ] CCI/TCCI/SWI values should change bar-to-bar (not frozen)
- [ ] Panel should match Sierra chart 12 values (Michael compares)

---

*No DLL change needed. Content staleness detection added. Full RTH parity verification deferred to 16:30 IL.*
