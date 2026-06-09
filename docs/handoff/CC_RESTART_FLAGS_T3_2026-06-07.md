# CC — restart backend + verify flags ON + T3 fix loaded (2026-06-07)

Two committed fixes need a backend restart to go live:
`bcdf43e` (.env flag loading) and `4d79a2d` (T3 None). Read-only verify after.
Paste raw output for each step (Rule 5).

## 1 — confirm commits are checked out
```
cd /Users/michael/Downloads/mems26_web_git
git log --oneline -4    # expect bcdf43e, 56a6a9c, 0be56ab, 4d79a2d among recent
```

## 2 — restart backend only (don't touch bridge/Sierra)
```
lsof -i :8000                       # note current pid(s)
pkill -f "uvicorn backend.main:app"
sleep 3
lsof -i :8000                       # expect EMPTY
cd /Users/michael/Downloads/mems26_web_git
screen -dmS mems26_backend bash -c 'ulimit -n 10240 2>/dev/null; [ -f .env ] && set -a && source .env && set +a; python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 2>&1 | tee /tmp/backend.log'
sleep 6
lsof -i :8000                       # expect a SINGLE uvicorn
curl -s localhost:8000/health       # expect status ok, alive
```

## 3 — verify the FLAGS are actually ON in the running process (the Friday bug)
```
ps eww $(pgrep -f "uvicorn backend.main") | tr ' ' '\n' \
  | grep -E "S2_ATR_RELATIVE|S3_RELATIVE|S1_CVD_OPENING|S1_IB_WIDTH_ATR|S1_DAYTYPE_STAGING|S2_VSA_VOLUME|S3_MUTE"
```
Expect all 7 present (`=true` / `=1`). If any are missing → stop and report.
(This is the whole point: even a LaunchAgent restart must now show these,
because main.py loads .env in-code.)

## 4 — verify backend started clean
```
tail -30 /tmp/backend.log           # no import errors / tracebacks
```

## NOT-DONE
- T3 live proof (S2 fires on a Trend day with t3≠0.0) verifies at Monday RTH — not now (market closed). Already unit+integration verified in code.
- If anything in step 2/3 fails, report raw output; do not "confirm" without it.
```
```
