@echo off
REM ============================================================
REM  MEMS26 (Windows) - install dependencies. Run this ONCE.
REM  Adjust REPO below if your repo is not at C:\mems26_web_git
REM ============================================================
set REPO=C:\mems26_web_git

echo === Installing Python dependencies ===
cd /d %REPO%
pip install -r requirements.txt

echo.
echo === Installing frontend dependencies (this can take a few minutes) ===
cd /d %REPO%\frontend\v9
call npm install

echo.
echo === Done. Next: double-click  2_START_run_each_time.bat ===
pause
