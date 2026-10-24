#!/bin/bash
# T-646 read-only data inventory #3 (SELECT only): day-type tables
export PATH=/Library/Frameworks/Python.framework/Versions/3.9/bin:/usr/local/bin:$PATH
P=/Applications/Postgres.app/Contents/Versions/latest/bin/psql
for T in v9_day_type_history v9_day_type_state v9_day_type_archive v9_decision_vectors v9_trades v9_tpo_sessions v9_tpo_history v9_shadow_ledger v9_day_type_shadow_transitions; do
echo "=== columns $T"
$P -d mems26 -Atc "select string_agg(column_name||':'||data_type, ', ' order by ordinal_position) from information_schema.columns where table_name='$T'" | cut -c1-900
done
echo "=== counts"
$P -d mems26 -Atc "select 'history', count(*), min(date), max(date), count(opening_type), count(*) filter (where locked_at is not null) from v9_day_type_history"
$P -d mems26 -Atc "select 'archive', count(*) from v9_day_type_archive"
$P -d mems26 -Atc "select 'state', count(*), min(ts), max(ts), count(distinct ts::date) from v9_day_type_state"
$P -d mems26 -Atc "select 'decision_vectors', kind, count(*), min(ts), max(ts), count(distinct ts::date) from v9_decision_vectors group by kind order by 2"
$P -d mems26 -Atc "select 'trades', mode, count(*), min(entry_ts)::date, max(entry_ts)::date, count(distinct entry_ts::date), sum(case when state='CLOSED' then 1 else 0 end) from v9_trades group by mode order by 2"
$P -d mems26 -Atc "select 'tpo_sessions', session_type, count(*), min(date), max(date) from v9_tpo_sessions group by 2"
