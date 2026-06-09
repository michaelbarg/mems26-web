# CC — write the flag-check result to a file (so Cowork can read it)

Run exactly this. It writes the result into the repo so Cowork can open it.

```bash
cd /Users/michael/Downloads/mems26_web_git
{
  echo "=== flags in the RUNNING backend process (ps eww) ==="
  ps eww $(pgrep -f "uvicorn backend.main") | tr ' ' '\n' \
    | grep -E "S2_ATR_RELATIVE|S3_RELATIVE|S1_CVD_OPENING|S1_IB_WIDTH_ATR|S1_DAYTYPE_STAGING|S2_VSA_VOLUME|S3_MUTE" \
    | sort
  echo
  echo "=== health ==="
  curl -s localhost:8000/health
  echo
  echo "=== listeners on :8000 (expect ONE uvicorn) ==="
  lsof -i :8000 | grep -i listen
  echo
  echo "=== backend start log tail ==="
  tail -15 /tmp/backend.log
} > docs/reports/FLAG_CHECK_2026-06-07.txt 2>&1
echo "written to docs/reports/FLAG_CHECK_2026-06-07.txt"
```

That's it — once it prints "written to ...", tell Cowork "done" and Cowork
reads the file directly.
