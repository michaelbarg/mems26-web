# Extremes-Aware Realize Replay (Dalton Step 1)

Period: 2026-07-15 → 2026-08-05 (186 trades)

## Comparison

| Mode | Triggered | NET delta |
|---|---|---|
| BASE (approach-realize only) | 4 | $+258.75 |
| EXTREMES-AWARE (+EXCESS/POOR) | 8 | $+668.75 |
| **IMPROVEMENT** | | **$+410.00** |

**VERDICT: GO**

## Base Details

| ID | Mode | Dir | Actual | Realize | Delta | Reason |
|---|---|---|---|---|---|---|
| 466 | live | SHORT | $31.25 | $65.00 | $+33.75 | t2 approach-realize: 2 bars within 0.75pt of 7541. |
| 515 | live | SHORT | $60.00 | $140.00 | $+80.00 | t2 approach-realize: 2 bars within 0.50pt of 7431. |
| 518 | shadow | SHORT | $38.75 | $166.25 | $+127.50 | t2 approach-realize: 2 bars within 0.75pt of 7431. |
| 598 | live | LONG | $-7.50 | $10.00 | $+17.50 | t1 approach-realize: 2 bars within 0.25pt of 7606. |

## Extremes-Aware Details

| ID | Mode | Dir | Actual | Realize | Delta | Reason |
|---|---|---|---|---|---|---|
| 444 | shadow | SHORT | $-26.25 | $37.50 | $+63.75 | t1 EXCESS-realize: 1 bars within 1.00pt of 7541.25 |
| 445 | live | SHORT | $-30.00 | $37.50 | $+67.50 | t1 EXCESS-realize: 1 bars within 1.00pt of 7541.25 |
| 466 | live | SHORT | $31.25 | $65.00 | $+33.75 | t2 approach-realize: 2 bars within 0.75pt of 7541. |
| 488 | shadow | SHORT | $40.00 | $100.00 | $+60.00 | t1 EXCESS-realize: 1 bars within 1.00pt of 7417.50 |
| 515 | live | SHORT | $60.00 | $140.00 | $+80.00 | t2 approach-realize: 2 bars within 0.50pt of 7431. |
| 518 | shadow | SHORT | $38.75 | $166.25 | $+127.50 | t2 approach-realize: 2 bars within 0.75pt of 7431. |
| 569 | shadow | LONG | $67.50 | $20.00 | $-47.50 | t3 EXCESS-realize: 1 bars within 1.00pt of 7446.50 |
| 572 | shadow | LONG | $-285.00 | $-1.25 | $+283.75 | t1 EXCESS-realize: 1 bars within 1.00pt of 7474.75 |
