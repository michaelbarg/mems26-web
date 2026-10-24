#!/bin/bash
# T-646 inventory 5 - coverage matrix of the 81 harness days vs data layers (SELECT only; timestamptz columns converted once)
export PATH=/Library/Frameworks/Python.framework/Versions/3.9/bin:/usr/local/bin:$PATH
PSQL=/Applications/Postgres.app/Contents/Versions/latest/bin/psql
cd /Users/michael/Downloads/mems26_web_git
O=harness_out/t646/index
ls harness_out/t640/days | grep -E '^live_.*json$' | sed 's/live_//; s/.json//' | sort > $O/h81.txt
q() { $PSQL -d mems26 -At -c "$1"; }
q "select d from (select (ts at time zone 'America/New_York')::date d, count(*) c from v9_bars_5min_woodies where (ts at time zone 'America/New_York')::time between '09:30' and '15:55' group by 1) x where c>=70 order by 1" > $O/bars_full.txt
q "select count(*) from (select (ts at time zone 'America/New_York')::date d, count(*) c from v9_bars_5min_woodies where (ts at time zone 'America/New_York')::time between '09:30' and '15:55' group by 1) x where c between 1 and 69" > $O/bars_partial_count.txt
q "select date from v9_day_type_history order by 1" > $O/hist_dates.txt
q "select distinct ts::date from v9_day_type_state order by 1" > $O/state_dates.txt
q "select distinct (created_at at time zone 'Asia/Jerusalem')::date from v9_decision_vectors where kind='DECISION' order by 1" > $O/dec_dates.txt
q "select distinct (created_at at time zone 'Asia/Jerusalem')::date from v9_decision_vectors where kind='BAR' order by 1" > $O/bar_vec_dates.txt
q "select distinct (coalesce(entry_ts,created_at) at time zone 'Asia/Jerusalem')::date from v9_trades where mode='demo' order by 1" > $O/demo_dates.txt
q "select distinct (coalesce(entry_ts,created_at) at time zone 'Asia/Jerusalem')::date from v9_trades where mode='live' order by 1" > $O/live_dates.txt
q "select distinct (coalesce(entry_ts,created_at) at time zone 'Asia/Jerusalem')::date from v9_trades where mode='shadow' order by 1" > $O/shadow_dates.txt
q "select distinct (created_at at time zone 'Asia/Jerusalem')::date from v9_decision_vectors where kind='TREE_SHADOW' order by 1" > $O/treeshadow_dates.txt
wc -l $O/{h81,bars_full,hist_dates,state_dates,dec_dates,bar_vec_dates,demo_dates,live_dates,shadow_dates,treeshadow_dates}.txt
cat $O/bars_partial_count.txt
