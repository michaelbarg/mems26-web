# ============================================================================
#  MEMS26 — One-shot Windows setup.  Run in PowerShell.
#  Beginner steps:
#    1. Start menu → type "PowerShell" → right-click → "Run as administrator".
#    2. Paste:   Set-ExecutionPolicy -Scope Process Bypass -Force
#    3. Run this file:   .\setup_all.ps1      (or paste the blocks below one by one)
# ============================================================================

Write-Host "==== MEMS26 setup — PART 1: install tools ====" -ForegroundColor Cyan

# Install Git, Python, PostgreSQL, Node — all via Windows' built-in winget.
$pkgs = @("Git.Git", "Python.Python.3.11", "PostgreSQL.PostgreSQL.16", "OpenJS.NodeJS.LTS")
foreach ($p in $pkgs) {
    Write-Host ">> installing $p ..." -ForegroundColor Yellow
    winget install --id $p -e --source winget --accept-package-agreements --accept-source-agreements
}

Write-Host ""
Write-Host "PART 1 done. NOW: close this PowerShell, open a NEW one (so the new tools are found)," -ForegroundColor Green
Write-Host "then run PART 2 below (copy-paste the block)." -ForegroundColor Green
Write-Host ""
Write-Host @'
# ==== PART 2 — paste this into a NEW PowerShell window ====
git clone https://github.com/michaelbarg/mems26-web.git C:\mems26_web_git
# (a browser opens → log into your GitHub → approve. one time.)
cd C:\mems26_web_git
git checkout stabilize/mems26-local-truth-2026-05-16
pip install -r requirements.txt
cd frontend\v9 ; npm install ; cd ..\..
# database:
& "C:\Program Files\PostgreSQL\16\bin\createdb.exe" -U postgres mems26
# .env: download "env_for_windows (rename to .env).txt" from your Google Drive folder
#       "MEMS26_to_Windows", put it at C:\mems26_web_git\.env  (remove the .txt).
#       Then open it and set V9_EXPORT_DIR to your Sierra export folder.
Write-Host "Setup done. Next: Sierra (MESU26 + chartbook) and run — see docs\runbooks\WINDOWS_SETUP.md"
'@ -ForegroundColor White
