@echo off
REM ============================================================
REM  MEMS26 (Windows) - start backend + frontend.
REM  Double-click this each time you want the dashboard up.
REM  Adjust REPO below if your repo is not at C:\mems26_web_git
REM ============================================================
set REPO=C:\mems26_web_git

start "MEMS26 BACKEND (keep open)" cmd /k "cd /d %REPO% && set V9_DISABLE_WATCHDOG=1 && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"

start "MEMS26 FRONTEND (keep open)" cmd /k "cd /d %REPO%\frontend\v9 && npx next dev"

echo.
echo Two windows opened: BACKEND and FRONTEND. Keep BOTH open.
echo.
echo When the FRONTEND window shows:   Ready - http://localhost:3000
echo open your browser at:             http://localhost:3000
echo.
echo If a window shows a red error, copy it and send it to Claude.
pause
