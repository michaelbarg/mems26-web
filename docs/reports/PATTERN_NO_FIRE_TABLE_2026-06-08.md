# Pattern No-Fire Table — 2026-06-08 (RTH session, ~20:10 IL)

**Day Type:** Trend_Normal (LOCKED, conf=0.38)  
**S4 Trend State:** GRAY (end of day, lost direction after RED→GRAY transition)  
**Session:** RTH active, last hour  
**Readiness:** DEGRADED (was BLOCKED before chop+stream fix)

---

## Full 19-Pattern Table

| # | תבנית | מערכת | סטטוס | **החוסם הקובע** | ערך חי | **REAL / DISPLAY** | מה חסר כדי לירות |
|---|--------|-------|--------|-----------------|--------|-------------------|-----------------|
| 1 | Reactive Long | S2 | armed | b1_sellers | b1 bullish (need bearish) | REAL — detection | Bar 1 must be bearish (seller expansion) |
| 2 | Reactive Short | S2 | armed | b3_sellers | b3 bullish (need bearish) | REAL — detection | Bar 3 must show seller dominance |
| 3 | Initiative Long | S2 | armed | b1_expansion | range=8.25, need [11.4,21.9] | REAL — detection | Bar 1 range must be 1.3× avg (expansion bar) |
| 4 | Initiative Short | S2 | armed | b1_expansion | range=8.25, need [11.4,21.9] | REAL — detection | Bar 1 range must be 1.3× avg (expansion bar) |
| 5 | Inverse H&S Long | S2 | blocked | auth_table_cell | SKIP 0/0/0 | REAL — doctrine | Auth Table SKIPs H&S on Trend_Normal day |
| 6 | H&S Top Short | S2 | blocked | auth_table_cell | SKIP 0/0/0 | REAL — doctrine | Auth Table SKIPs H&S on Trend_Normal day |
| 7 | Double Bottom EE Long | S2 | blocked | auth_table_cell | SKIP 0/0/0 | REAL — doctrine | Auth Table SKIPs Double on Trend_Normal day |
| 8 | Double Top AA Short | S2 | blocked | auth_table_cell | SKIP 0/0/0 | REAL — doctrine | Auth Table SKIPs Double on Trend_Normal day |
| 9 | Bull Flag Long | S2 | armed | pole_found | no valid pole (need ≥5 bars) | REAL — detection | Need 5+ bullish bars forming a pole |
| 10 | Bear Flag Short | S2 | armed | pole_found | no valid pole (need ≥5 bars) | REAL — detection | Need 5+ bearish bars forming a pole |
| 11 | ZLR | S4 | blocked | strategic_gate | trend_state=GRAY | REAL — doctrine | CCI trend must be BLUE or RED (Stage A1) |
| 12 | TLB | S4 | blocked | strategic_gate | trend_state=GRAY | REAL — doctrine | CCI trend must be BLUE or RED |
| 13 | TT | S4 | blocked | strategic_gate | trend_state=GRAY | REAL — doctrine | CCI trend must be BLUE or RED |
| 14 | GB100 | S4 | blocked | strategic_gate | trend_state=GRAY | REAL — doctrine | CCI trend must be BLUE or RED |
| 15 | VEGAS | S4 | blocked | strategic_gate | trend_state=GRAY | REAL — doctrine | CCI trend must be BLUE or RED |
| 16 | GHOST | S4 | blocked | strategic_gate | trend_state=GRAY | REAL — doctrine | CCI trend must be BLUE or RED |
| 17 | FAMIR | S4 | blocked | strategic_gate | trend_state=GRAY | REAL — doctrine | CCI trend must be BLUE or RED |
| 18 | HTLB | S4 | blocked | strategic_gate | trend_state=GRAY | REAL — doctrine | CCI trend must be BLUE or RED |
| 19 | HFE | S4 | blocked | strategic_gate | trend_state=GRAY | REAL — doctrine | CCI trend must be BLUE or RED |

---

## Summary

| Category | Count | Patterns |
|----------|-------|---------|
| **REAL — detection** (no setup) | 6 | Reactive L/S, Initiative L/S, Bull Flag, Bear Flag |
| **REAL — doctrine** (auth SKIP) | 4 | Inv H&S, H&S Top, Double Bottom, Double Top |
| **REAL — doctrine** (trend GRAY) | 9 | All S4 (ZLR, TLB, TT, GB100, VEGAS, GHOST, FAMIR, HTLB, HFE) |
| **DISPLAY-only** | 0 | — |

**0 patterns blocked by DISPLAY-only issues.** After the chop gate + non-critical stream fixes, all "BLOCKED" are genuine REAL blockers.

### Most common REAL blockers:
1. **S4 trend_state=GRAY** (9/19) — CCI lost direction after the BLUE→RED→GRAY transition. The market went from trending to neutral toward end of day. This is doctrine — S4 patterns require established trend.
2. **Auth Table SKIP** (4/19) — Reversal chart patterns (H&S, Double) are correctly SKIPped on a Trend_Normal day per the Auth Matrix.
3. **Detection conditions not met** (6/19) — S2 patterns are armed and scanning, but current bar geometry doesn't match pattern requirements (no expansion bar, no seller bar, no flag pole).

### S4 Trend Timeline Today:
```
18:05-18:20  BLUE (CCI +131→+68) — trending up
18:25        GRAY (CCI -3.6, zero-line cross)
18:30-18:45  GRAY (CCI -107→-30, volatile but no established trend)
18:50-19:10  RED (CCI -28→-87, brief red trend)
19:15-19:25  RED (CCI -9→-16, CCI returning to zero)
19:30+       GRAY (CCI near zero, trend lost)
```
S4 was armed and scanning during the BLUE (18:05-18:20) and RED (18:50-19:10) windows, but CCI never formed a complete Woodies pattern (ZLR needs ≤-100 extreme; closest was -98.2).

### Conclusion
**The system is not broken — it's a market day without patterns.** All 19 patterns are either armed-and-scanning (S2) or blocked by legitimate doctrine (S4 trend GRAY, Auth SKIP). Zero DISPLAY-only blocks remain after today's fixes.
