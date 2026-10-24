#!/bin/bash
# T-646 read-only data inventory #2 (SELECT only)
export PATH=/Library/Frameworks/Python.framework/Versions/3.9/bin:/usr/local/bin:$PATH
P=/Applications/Postgres.app/Contents/Versions/latest/bin/psql
echo "=== databases"
$P -d postgres -Atc "select datname, pg_size_pretty(pg_database_size(datname)) from pg_database where not datistemplate order by 1"
echo "=== woodies bars: per month: dates with >=70 RTH-ish bars / partial"
$P -d mems26 -Atc "
with b as (select (ts at time zone 'Asia/Jerusalem')::date d, count(*) n, min(ts at time zone 'Asia/Jerusalem') mn, max(ts at time zone 'Asia/Jerusalem') mx from v9_bars_5min_woodies where symbol='MES' group by 1)
select to_char(d,'YYYY-MM') m, count(*) days, sum((n>=70)::int) full, sum((n<70)::int) partial, min(d), max(d) from b group by 1 order by 1"
echo "=== woodies partial days list"
$P -d mems26 -Atc "
with b as (select (ts at time zone 'Asia/Jerusalem')::date d, count(*) n from v9_bars_5min_woodies where symbol='MES' group by 1)
select d||':'||n from b where n<70 order by d" | tr '\n' ' '
echo
echo "=== woodies full days >= 2026-06-01 count and list gaps (weekdays missing)"
$P -d mems26 -Atc "
with b as (select (ts at time zone 'Asia/Jerusalem')::date d, count(*) n from v9_bars_5min_woodies where symbol='MES' group by 1),
cal as (select g::date d from generate_series('2026-06-15'::date,'2026-10-23'::date,'1 day') g where extract(isodow from g) between 1 and 5)
select cal.d||':'||coalesce(b.n,0) from cal left join b using(d) where coalesce(b.n,0)<70 order by 1" | tr '\n' ' '
echo
echo "=== v9_bars_5min (non-woodies) range"
$P -d mems26 -Atc "
with b as (select (ts at time zone 'Asia/Jerusalem')::date d, count(*) n from v9_bars_5min group by 1)
select min(d), max(d), count(*), sum((n>=70)::int) from b"
