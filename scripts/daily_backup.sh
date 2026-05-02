#!/bin/bash
set -e

# Daily backup script for MEMS26
# Run nightly at 23:00 IL

BACKUP_ROOT=~/backups/mems26
DATE=$(date +%Y%m%d)
DATE_TIME=$(date +%Y%m%d_%H%M%S)

echo "=== MEMS26 Daily Backup ==="
echo "Date: $(date)"
echo "Backup root: $BACKUP_ROOT"
echo ""

# 1. Database backup
echo "--- 1. Database backup ---"
if [ -z "$DATABASE_URL" ]; then
    echo "WARNING: DATABASE_URL not set — skipping DB backup"
else
    mkdir -p "$BACKUP_ROOT/db"
    DB_DIR="$BACKUP_ROOT/db"
    # Use Python for DB export (pg_dump not always available on Mac)
    python3 - "$DB_DIR" "$DATE_TIME" << 'DBEOF'
import os, sys, json, psycopg2
db_dir, ts = sys.argv[1], sys.argv[2]
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
summary = {}
for tbl in ['trades', 'setup_attempts', 'setups']:
    cur.execute(f'SELECT COUNT(*) FROM {tbl}')
    count = cur.fetchone()[0]
    cur.execute(f'SELECT * FROM {tbl} ORDER BY created_at DESC LIMIT 5000')
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    summary[tbl] = {'count': count, 'exported': len(rows)}
    with open(f'{db_dir}/{tbl}_{ts}.json', 'w') as f:
        json.dump(rows, f, default=str)
cur.close(); conn.close()
with open(f'{db_dir}/summary_{ts}.json', 'w') as f:
    json.dump(summary, f, indent=2)
print('DB export complete')
for t, info in summary.items():
    print(f'  {t}: {info["count"]} total, {info["exported"]} exported')
DBEOF
    if [ $? -eq 0 ]; then
        gzip "$DB_DIR"/*_${DATE_TIME}.json 2>/dev/null
        echo "DB files compressed"
    else
        echo "WARNING: DB export failed"
    fi
fi

# 2. Bridge log
echo ""
echo "--- 2. Bridge logs ---"
mkdir -p "$BACKUP_ROOT/logs"
if [ -f /tmp/bridge.log ]; then
    cp /tmp/bridge.log "$BACKUP_ROOT/logs/bridge_${DATE_TIME}.log"
    echo "Bridge log saved"
else
    echo "No bridge.log found (normal if Bridge not running)"
fi

# 3. DLL source (if changed)
echo ""
echo "--- 3. DLL source ---"
mkdir -p "$BACKUP_ROOT/dll"
DLL_SRC=/Users/michael/SierraChart2/ACS_Source/MES_AI_DataExport.cpp
if [ -f "$DLL_SRC" ]; then
    # Only copy if newer than last backup
    LATEST=$(ls -t "$BACKUP_ROOT/dll"/MES_AI_DataExport_*.cpp 2>/dev/null | head -1)
    if [ -z "$LATEST" ] || [ "$DLL_SRC" -nt "$LATEST" ]; then
        cp "$DLL_SRC" "$BACKUP_ROOT/dll/MES_AI_DataExport_${DATE}.cpp"
        echo "DLL source backed up (changed)"
    else
        echo "DLL source unchanged — skipped"
    fi
else
    echo "DLL source not found"
fi

# 4. Verify GitHub sync
echo ""
echo "--- 4. GitHub sync check ---"
cd /Users/michael/Downloads/mems26_web_git
BRANCH=$(git rev-parse --abbrev-ref HEAD)
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH" 2>/dev/null || echo "no-remote")
if [ "$LOCAL" = "$REMOTE" ]; then
    echo "Branch '$BRANCH' in sync with origin ($LOCAL)"
else
    echo "WARNING: '$BRANCH' not in sync — push pending changes!"
    echo "  Local:  $LOCAL"
    echo "  Remote: $REMOTE"
fi

# 5. Cleanup old backups (keep last 30 days for DB/logs, 90 for DLL)
echo ""
echo "--- 5. Cleanup old backups ---"
find "$BACKUP_ROOT/db" -name "*.sql.gz" -mtime +30 -delete 2>/dev/null
find "$BACKUP_ROOT/logs" -name "bridge_*.log" -mtime +30 -delete 2>/dev/null
find "$BACKUP_ROOT/dll" -name "MES_AI_DataExport_*.cpp" -mtime +90 -delete 2>/dev/null
echo "Old backups cleaned (DB/logs >30d, DLL >90d)"

# 6. Summary
echo ""
echo "--- Summary ---"
TOTAL_SIZE=$(du -sh "$BACKUP_ROOT" | cut -f1)
DB_COUNT=$(ls "$BACKUP_ROOT/db"/*.sql.gz 2>/dev/null | wc -l | tr -d ' ')
LOG_COUNT=$(ls "$BACKUP_ROOT/logs"/bridge_*.log 2>/dev/null | wc -l | tr -d ' ')
echo "Total backup size: $TOTAL_SIZE"
echo "DB backups: $DB_COUNT"
echo "Log backups: $LOG_COUNT"
echo ""
echo "=== Backup Complete ==="
