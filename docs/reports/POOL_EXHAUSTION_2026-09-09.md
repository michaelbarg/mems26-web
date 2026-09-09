# T-284 · QueuePool exhaustion — evidence snapshot

נלכד ע"י cowork ב-2026-09-09 12:39:35 IDT **לפני** כל ריסטארט, כדי שהראיה תשרוד את התיקון.

## pg_stat_activity — mems26
```
  pid  |        state        |       wait        | xact_s | idle_s |                                                       q                                                        
-------+---------------------+-------------------+--------+--------+----------------------------------------------------------------------------------------------------------------
 98551 | idle in transaction | Client/ClientRead |   1655 |     19 | SELECT v9_trades.id AS v9_trades_id, v9_trades.mode AS v9_trades_mode, v9_trades.firing_system AS v9_trades_fi
 98777 | idle in transaction | Client/ClientRead |   1596 |     35 | SELECT v9_bars_5min.id AS v9_bars_5min_id, v9_bars_5min.ts AS v9_bars_5min_ts, v9_bars_5min.symbol AS v9_bars_
 98793 | idle in transaction | Client/ClientRead |   1591 |     38 | SELECT v9_bars_5min.id AS v9_bars_5min_id, v9_bars_5min.ts AS v9_bars_5min_ts, v9_bars_5min.symbol AS v9_bars_
 98782 | idle in transaction | Client/ClientRead |   1585 |     50 | SELECT v9_bars_5min.id AS v9_bars_5min_id, v9_bars_5min.ts AS v9_bars_5min_ts, v9_bars_5min.symbol AS v9_bars_
 98786 | idle in transaction | Client/ClientRead |   1571 |      2 | SELECT v9_bars_5min.id AS v9_bars_5min_id, v9_bars_5min.ts AS v9_bars_5min_ts, v9_bars_5min.symbol AS v9_bars_
 98711 | idle in transaction | Client/ClientRead |   1527 |      2 | SELECT v9_bars_5min.id AS v9_bars_5min_id, v9_bars_5min.ts AS v9_bars_5min_ts, v9_bars_5min.symbol AS v9_bars_
 98760 | idle in transaction | Client/ClientRead |   1518 |      2 | SELECT v9_bars_5min.id AS v9_bars_5min_id, v9_bars_5min.ts AS v9_bars_5min_ts, v9_bars_5min.symbol AS v9_bars_
 98827 | idle in transaction | Client/ClientRead |   1510 |     35 | SELECT v9_bars_5min.id AS v9_bars_5min_id, v9_bars_5min.ts AS v9_bars_5min_ts, v9_bars_5min.symbol AS v9_bars_
 98771 | idle in transaction | Client/ClientRead |   1503 |      2 | SELECT v9_bars_5min.id AS v9_bars_5min_id, v9_bars_5min.ts AS v9_bars_5min_ts, v9_bars_5min.symbol AS v9_bars_
 98714 | idle in transaction | Client/ClientRead |   1465 |     36 | SELECT v9_bars_5min.id AS v9_bars_5min_id, v9_bars_5min.ts AS v9_bars_5min_ts, v9_bars_5min.symbol AS v9_bars_
 98801 | idle in transaction | Client/ClientRead |   1454 |      2 | SELECT v9_bars_5min.id AS v9_bars_5min_id, v9_bars_5min.ts AS v9_bars_5min_ts, v9_bars_5min.symbol AS v9_bars_
 98846 | idle in transaction | Client/ClientRead |   1408 |   1408 | SELECT v9_bars_5min.id AS v9_bars_5min_id, v9_bars_5min.ts AS v9_bars_5min_ts, v9_bars_5min.symbol AS v9_bars_
 98823 | idle in transaction | Client/ClientRead |    758 |      2 | SELECT v9_bars_5min.id AS v9_bars_5min_id, v9_bars_5min.ts AS v9_bars_5min_ts, v9_bars_5min.symbol AS v9_bars_
 98773 | idle in transaction | Client/ClientRead |    154 |      2 | SELECT v9_bars_5min.id AS v9_bars_5min_id, v9_bars_5min.ts AS v9_bars_5min_ts, v9_bars_5min.symbol AS v9_bars_
 98741 | idle in transaction | Client/ClientRead |     62 |     62 | SELECT v9_bars_5min.id AS v9_bars_5min_id, v9_bars_5min.ts AS v9_bars_5min_ts, v9_bars_5min.symbol AS v9_bars_
  1157 | active              |                   |      0 |      0 | SELECT pid, state, wait_event_type||'/'||coalesce(wait_event,'-') AS wait, round(EXTRACT(EPOCH FROM (now()-xac
 98841 | idle                | Client/ClientRead |        |      2 | SELECT high, low, ts FROM v9_bars_5min_woodies WHERE symbol='MES' AND ts < '2026-09-09T09:10:00+00:00' AND ts 
 99425 | idle                | Client/ClientRead |        |      2 | SELECT zlr_detected, zlr_direction FROM v9_bars_5min_woodies WHERE ts = '2026-09-09T09:10:00+00:00' AND symbol
 98848 | idle                | Client/ClientRead |        |      2 | SELECT high, low, ts FROM v9_bars_5min_woodies WHERE symbol='MES' AND ts < '2026-09-09T09:05:00+00:00' AND ts 
(19 rows)

```

## מונים
```
QueuePool limit reached (today total): 1837
first occurrence: 2026-09-09 12:14:02
bridge push timeouts 12:00-12:xx: 1163
bridge push timeouts 11:00-11:59: 0
newest woodies bar: 2026-09-09 12:10:00+03 age_min=29.8
backend pid/lstart: 48888 Tue Sep  8 18:42:39 2026    
load: load averages: 87.36 107.00 120.49
```
