#!/bin/bash
# T-646 read-only data inventory #4 (SELECT only): decision vectors / label coverage
export PATH=/Library/Frameworks/Python.framework/Versions/3.9/bin:/usr/local/bin:$PATH
P=/Applications/Postgres.app/Contents/Versions/latest/bin/psql
echo "=== BAR vector keys (sample latest)"
$P -d mems26 -Atc "select string_agg(k, ',') from (select jsonb_object_keys(vector) k from v9_decision_vectors where kind='BAR' order by ts desc limit 1) t"
echo "=== DECISION vector keys (sample latest)"
$P -d mems26 -Atc "select string_agg(k, ',') from (select jsonb_object_keys(vector) k from v9_decision_vectors where kind='DECISION' order by ts desc limit 1) t"
echo "=== per-date: BAR rows w/ day_type, opening_type; DECISION rows (dates >= 09-16)"
$P -d mems26 -Atc "
select (ts at time zone 'Asia/Jerusalem')::date d,
 count(*) filter (where kind='BAR') bars,
 count(*) filter (where kind='BAR' and vector->>'day_type' is not null) bar_dt,
 count(*) filter (where kind='BAR' and vector->>'opening_type' is not null) bar_ot,
 count(*) filter (where kind='DECISION') dec,
 count(*) filter (where kind='DECISION' and vector->>'day_type' is not null) dec_dt,
 count(*) filter (where kind='TREE_SHADOW') tsh
from v9_decision_vectors group by 1 order by 1" | tr '\n' ';'
echo
echo "=== shadow transitions"
$P -d mems26 -Atc "select count(*), min(session_date), max(session_date), count(distinct session_date) from v9_day_type_shadow_transitions"
echo "=== tpo_sessions"
$P -d mems26 -Atc "select session_type, count(*), min(trading_date), max(trading_date) from v9_tpo_sessions group by 1"
echo "=== tpo_history"
$P -d mems26 -Atc "select count(*), min(ts), max(ts), count(distinct (ts at time zone 'Asia/Jerusalem')::date) from v9_tpo_history"
echo "=== day_type_history dates with locked_at; opening types; EOD labels count"
$P -d mems26 -Atc "select day_type, count(*) from v9_day_type_history group by 1 order by 2 desc" | tr '\n' ';'
echo
$P -d mems26 -Atc "select opening_type, count(*) from v9_day_type_history group by 1 order by 2 desc" | tr '\n' ';'
echo
echo "=== history weekdays-only count (exclude Sat/Sun)"
$P -d mems26 -Atc "select count(*) filter (where extract(isodow from date) between 1 and 5), count(*) filter (where extract(isodow from date) > 5) from v9_day_type_history"
echo "=== state table per date"
$P -d mems26 -Atc "select ts::date, count(*), min(ts), max(ts) from v9_day_type_state group by 1 order by 1"
