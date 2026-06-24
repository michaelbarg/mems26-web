# Per-bar simulation — 2026-06-23 (RTH 08:30–15:00 CT)

_All patterns + volume + day-type + LSMA mean-reversion (LONG below LSMA / SHORT above, one-at-a-time, exit on LSMA cross). 79 bars, 13 fires._

**LSMA strategy result: 2 trades, +2.5 pts (~$+38 @ 3 contracts).**

| time | close | vol | | day_type | LSMA | P vs LSMA | CCI | trend | fires | strategy |
|------|-------|-----|--|----------|------|-----------|-----|-------|-------|----------|
| 08:30 | 7432.50 | 49,932 |  | FORMING | 7427.35 | ABOVE | -181 | RED |  | · |
| 08:35 | 7436.75 | 40,320 |  | FORMING | 7427.36 | ABOVE | -19 | RED |  | · |
| 08:40 | 7442.50 | 27,090 |  | FORMING | 7428.49 | ABOVE | 287 | GRAY |  | · |
| 08:45 | 7457.75 | 32,700 |  | FORMING | 7432.29 | ABOVE | 345 | GRAY |  | · |
| 08:50 | 7460.00 | 22,245 |  | FORMING | 7436.31 | ABOVE | 253 | GRAY |  | · |
| 08:55 | 7465.25 | 25,291 |  | FORMING | 7441.37 | ABOVE | 175 | GRAY | TLB/S | S ENTER S@7465.25 |
| 09:00 | 7474.50 | 28,796 |  | FORMING | 7447.53 | ABOVE | 172 | GRAY |  | S |
| 09:05 | 7479.00 | 21,613 |  | FORMING | 7454.23 | ABOVE | 146 | BLUE | HFE/S | S |
| 09:10 | 7484.00 | 24,663 |  | FORMING | 7461.2 | ABOVE | 131 | BLUE | HFE/S | S |
| 09:15 | 7486.25 | 17,863 |  | FORMING | 7468.02 | ABOVE | 117 | BLUE | HFE/S | S |
| 09:20 | 7483.00 | 22,281 |  | FORMING | 7473.72 | ABOVE | 99 | BLUE |  | S |
| 09:25 | 7483.75 | 21,715 |  | FORMING | 7478.69 | ABOVE | 78 | BLUE |  | S |
| 09:30 | 7476.00 | 20,551 |  | Normal | 7482.07 | BELOW | 60 | BLUE |  | · EXIT S (-10.75) |
| 09:35 | 7470.50 | 22,556 |  | Normal | 7483.48 | BELOW | 39 | BLUE |  | · |
| 09:40 | 7468.25 | 24,433 |  | Normal | 7484.46 | BELOW | 11 | BLUE |  | · |
| 09:45 | 7467.50 | 20,511 |  | Normal | 7485.13 | BELOW | -27 | GRAY |  | · |
| 09:50 | 7466.00 | 22,187 |  | Normal | 7485.17 | BELOW | -43 | GRAY |  | · |
| 09:55 | 7464.75 | 17,391 |  | Normal | 7484.56 | BELOW | -86 | GRAY |  | · |
| 10:00 | 7459.75 | 20,562 |  | Normal | 7483.05 | BELOW | -105 | GRAY |  | · |
| 10:05 | 7453.75 | 19,381 |  | Normal | 7480.42 | BELOW | -157 | GRAY |  | · |
| 10:10 | 7455.50 | 13,271 |  | Normal | 7477.83 | BELOW | -131 | RED |  | · |
| 10:15 | 7446.50 | 15,306 |  | Normal | 7473.79 | BELOW | -137 | RED |  | · |
| 10:20 | 7440.00 | 13,795 |  | Normal | 7468.37 | BELOW | -152 | RED | BEAR_FLAG_SHORT/S,REACTIVE_SHORT/S | · |
| 10:25 | 7440.00 | 17,049 |  | Normal | 7462.89 | BELOW | -145 | RED | REACTIVE_SHORT/S | · |
| 10:30 | 7443.50 | 15,479 |  | Normal | 7457.74 | BELOW | -106 | RED |  | · |
| 10:35 | 7438.75 | 15,444 |  | Normal | 7452.0 | BELOW | -97 | RED |  | · |
| 10:40 | 7444.25 | 12,654 |  | Normal | 7447.36 | BELOW | -85 | RED |  | · |
| 10:45 | 7444.75 | 11,950 |  | Normal | 7443.19 | ABOVE | -54 | RED |  | · |
| 10:50 | 7452.75 | 14,055 |  | Normal | 7441.43 | ABOVE | -8 | RED |  | · |
| 10:55 | 7453.75 | 10,497 |  | Normal | 7440.04 | ABOVE | 13 | GRAY |  | · |
| 11:00 | 7461.25 | 10,648 |  | Normal | 7440.26 | ABOVE | 85 | GRAY |  | · |
| 11:05 | 7466.25 | 12,158 |  | Normal | 7442.01 | ABOVE | 140 | GRAY |  | · |
| 11:10 | 7469.25 | 9,552 |  | Normal | 7444.65 | ABOVE | 171 | GRAY |  | · |
| 11:15 | 7465.00 | 8,705 |  | Normal | 7447.14 | ABOVE | 125 | GRAY |  | · |
| 11:20 | 7468.25 | 9,138 |  | Normal | 7450.47 | ABOVE | 102 | BLUE |  | · |
| 11:25 | 7469.00 | 6,537 | low | Normal | 7453.83 | ABOVE | 96 | BLUE |  | · |
| 11:30 | 7466.00 | 6,286 | low | Normal | 7456.92 | ABOVE | 74 | BLUE |  | · |
| 11:35 | 7470.25 | 5,418 | low | Normal | 7460.19 | ABOVE | 76 | BLUE |  | · |
| 11:40 | 7474.00 | 8,386 |  | Normal | 7463.65 | ABOVE | 95 | BLUE |  | · |
| 11:45 | 7469.00 | 7,867 |  | Normal | 7466.14 | ABOVE | 67 | BLUE |  | · |
| 11:50 | 7468.75 | 7,210 |  | Normal | 7468.52 | ABOVE | 41 | BLUE |  | · |
| 11:55 | 7469.50 | 7,283 |  | Normal | 7470.88 | BELOW | 51 | BLUE |  | · |
| 12:00 | 7462.75 | 7,739 |  | Normal | 7472.1 | BELOW | -24 | GRAY |  | · |
| 12:05 | 7464.75 | 7,092 |  | Normal | 7473.23 | BELOW | -89 | GRAY |  | · |
| 12:10 | 7468.75 | 9,220 |  | Normal | 7474.44 | BELOW | 40 | BLUE |  | · |
| 12:15 | 7466.75 | 6,738 |  | Normal | 7475.36 | BELOW | -10 | GRAY |  | · |
| 12:20 | 7474.50 | 9,171 |  | Normal | 7476.61 | BELOW | 148 | BLUE |  | · |
| 12:25 | 7471.00 | 5,955 |  | Normal | 7476.56 | BELOW | 116 | BLUE |  | · |
| 12:30 | 7473.25 | 7,135 |  | Normal | 7476.57 | BELOW | 72 | BLUE |  | · |
| 12:35 | 7471.25 | 5,650 |  | Normal | 7476.24 | BELOW | 96 | BLUE |  | · |
| 12:40 | 7467.25 | 4,801 |  | Normal | 7474.68 | BELOW | -18 | GRAY |  | · |
| 12:45 | 7468.50 | 5,327 |  | Normal | 7473.48 | BELOW | -27 | GRAY | REACTIVE_SHORT/S | · |
| 12:50 | 7456.25 | 10,043 |  | Normal | 7470.25 | BELOW | -211 | GRAY |  | · |
| 12:55 | 7453.00 | 10,108 |  | Normal | 7467.06 | BELOW | -231 | GRAY | REACTIVE_SHORT/S | · |
| 13:00 | 7456.00 | 11,741 | HIGH | Normal | 7464.4 | BELOW | -145 | GRAY |  | · |
| 13:05 | 7453.25 | 8,250 |  | Normal | 7461.91 | BELOW | -146 | RED |  | · |
| 13:10 | 7453.75 | 6,206 |  | Normal | 7459.97 | BELOW | -108 | RED |  | · |
| 13:15 | 7451.25 | 5,784 |  | Normal | 7458.01 | BELOW | -101 | RED |  | · |
| 13:20 | 7452.75 | 7,408 |  | Normal | 7456.09 | BELOW | -91 | RED |  | · |
| 13:25 | 7449.75 | 5,725 |  | Normal | 7454.1 | BELOW | -88 | RED |  | · |
| 13:30 | 7447.00 | 5,657 |  | Normal | 7451.93 | BELOW | -95 | RED | REACTIVE_SHORT/S,ZLR/S | · |
| 13:35 | 7445.00 | 5,761 |  | Normal | 7449.42 | BELOW | -105 | RED |  | · |
| 13:40 | 7433.50 | 12,517 | HIGH | Normal | 7445.7 | BELOW | -170 | RED |  | · |
| 13:45 | 7435.50 | 12,998 | HIGH | Normal | 7442.93 | BELOW | -182 | RED |  | · |
| 13:50 | 7432.75 | 13,698 | HIGH | Normal | 7439.7 | BELOW | -146 | RED | REACTIVE_LONG/L | L ENTER L@7432.75 |
| 13:55 | 7436.25 | 11,744 |  | Normal | 7437.31 | BELOW | -116 | RED |  | L |
| 14:00 | 7446.00 | 13,429 | HIGH | Normal | 7436.75 | ABOVE | -40 | RED | FAMIR/L | · EXIT L (+13.25) |
| 14:05 | 7440.75 | 16,211 | HIGH | Normal | 7435.08 | ABOVE | -18 | RED |  | · |
| 14:10 | 7441.00 | 9,526 |  | Normal | 7433.8 | ABOVE | -34 | RED |  | · |
| 14:15 | 7434.25 | 9,239 |  | Normal | 7432.05 | ABOVE | -69 | RED |  | · |
| 14:20 | 7444.75 | 14,481 | HIGH | Normal | 7432.04 | ABOVE | -4 | RED |  | · |
| 14:25 | 7447.00 | 12,183 |  | Normal | 7433.19 | ABOVE | 59 | GRAY |  | · |
| 14:30 | 7447.00 | 12,286 |  | Normal | 7434.32 | ABOVE | 56 | GRAY |  | · |
| 14:35 | 7443.00 | 10,523 |  | Normal | 7435.25 | ABOVE | 57 | GRAY |  | · |
| 14:40 | 7442.25 | 11,357 |  | Normal | 7436.18 | ABOVE | 14 | GRAY |  | · |
| 14:45 | 7444.25 | 14,996 |  | Normal | 7437.36 | ABOVE | 25 | GRAY |  | · |
| 14:50 | 7452.50 | 20,465 | HIGH | Normal | 7440.09 | ABOVE | 146 | BLUE |  | · |
| 14:55 | 7435.00 | 32,861 | HIGH | Normal | 7439.36 | BELOW | -35 | GRAY |  | · |
| 15:00 | 7436.00 | 9,672 |  | Normal | 7438.71 | BELOW | -148 | GRAY |  | · |
