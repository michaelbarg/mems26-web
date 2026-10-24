#!/bin/bash
# T-646 read-only data inventory (SELECT only)
export PATH=/Library/Frameworks/Python.framework/Versions/3.9/bin:/usr/local/bin:$PATH
P=/Applications/Postgres.app/Contents/Versions/latest/bin/psql
for DB in mems26 mems26_hist; do
echo "=== DB $DB tables (bars/day_type/tpo/trades/decision/candidate)"
$P -d $DB -Atc "select table_name from information_schema.tables where table_schema='public' and (table_name ~ 'bars|day_type|tpo|trades|decision|candidate|opening|woodies_sig|ledger') order by 1" | tr '\n' ' '
echo
done
echo "=== mems26 bars_5min_woodies RTH coverage"
$P -d mems26 -Atc "
with b as (select (ts at time zone 'Asia/Jerusalem')::date d, count(*) n from v9_bars_5min_woodies where symbol='MES' group by 1)
select min(d), max(d), count(*), sum((n>=70)::int) full_days, sum((n<70)::int) partial_days from b"
