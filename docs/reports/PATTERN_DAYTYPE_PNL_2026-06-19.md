# Pattern × Day-Type — P&L behavior (SHADOW)
**Data:** 145 closed SHADOW trades, 2026-06-05 → 2026-06-18. **Directional, not statistically robust** (few days, small per-cell samples, I-34 sizing bug skews some $).

## Per-pattern totals (sorted by net)
| pattern | n | W% | net$ | avg$ | read |
|---|---|---|---|---|---|
| TLB | 44 | 75% | **+1,189** | +27 | workhorse — best on Trend_Normal |
| HTLB | 3 | 100% | +720 | +240 | tiny sample |
| GB100 | 3 | 100% | +228 | +76 | tiny sample |
| INITIATIVE_SHORT | 8 | 88% | +205 | +26 | solid on trend |
| GHOST | 2 | 100% | +35 | +17 | tiny |
| INITIATIVE_LONG | 3 | 67% | −109 | −36 | tiny |
| ZLR | 30 | 70% | −118 | −4 | wins on Trend/Variation, bleeds on Normal |
| BULL_FLAG_LONG | 1 | 0% | −128 | −128 | tiny |
| FAMIR | 2 | 50% | −148 | −74 | tiny |
| VEGAS | 2 | 50% | −284 | −142 | tiny |
| REACTIVE_SHORT | 12 | 58% | −662 | −55 | bad on Trend_Normal |
| REACTIVE_LONG | 14 | 36% | −959 | −68 | 0% win on Variation |
| **HFE** | 21 | 38% | **−2,640** | −126 | the big bleeder, worst on Variation |

## Pattern × day-type — standout cells (n · W% · net$)
| pattern | Trend_Normal | Variation | Normal | (unclassified) |
|---|---|---|---|---|
| TLB | 20 · 75% · **+547** | 15 · 67% · −216 | 2 · 100% · +346 | 7 · 86% · +512 |
| ZLR | 13 · 69% · +409 | 11 · 73% · +297 | 4 · 50% · **−902** | 2 · +78 |
| HFE | 4 · 25% · −445 | 12 · 42% · **−2,260** | 2 · 0% · −56 | 3 · +122 |
| REACTIVE_LONG | 9 · 56% · −164 | 5 · 0% · **−795** | — | — |
| REACTIVE_SHORT | 7 · 43% · **−482** | 2 · 100% · +62 | 1 · 0% · −326 | 2 · +85 |
| INITIATIVE_SHORT | 3 · 100% · +128 | 3 · 67% · +14 | — | 2 · +62 |

## Per-day-type totals
| day-type | n | W% | net$ |
|---|---|---|---|
| (unclassified, early-session) | 19 | 89% | +1,565 |
| Trend_Normal | 60 | 63% | −165 |
| Normal | 9 | 44% | −939 |
| Variation | 57 | 60% | **−3,132** |

## Takeaways → playbook config (`config/daytype_playbook.yaml`)
1. **HFE** — biggest loser everywhere, catastrophic on Variation (−$2,260). Already SKIP on Trend; data says **make `HFE.Variation: SKIP`** too (currently REDUCED).
2. **ZLR** — strong on Trend/Variation, loses on Normal (−$902). Consider **`ZLR.Normal: SKIP`** (currently REDUCED).
3. **TLB** — keep FULL on Trend/Variation; the reliable money-maker.
4. **REACTIVE** — net losers; keep `require_with_trend` and watch Variation (REACTIVE_LONG 0% there).
5. **Variation** is the worst day overall — driven entirely by HFE + REACTIVE_LONG. Tightening those two flips it.

**Caveats:** small per-cell samples; SHADOW (with the I-34 half-sizing bug not applied to PnL); 6 trading days only. Use as direction for config tuning + a walk-forward, not as final truth.
