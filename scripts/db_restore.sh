#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# MEMS26 DB Restore — restore from backup
#
# Usage: ./scripts/db_restore.sh <backup_file>
#        ./scripts/db_restore.sh latest
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DB_FILE="$REPO_ROOT/data/mems26_local.db"
BACKUP_DIR="$REPO_ROOT/data/backups"

BACKUP="${1:-}"
if [[ -z "$BACKUP" ]]; then
    echo "Usage: $0 <backup_file|latest>"
    echo "Available backups:"
    ls -la "$BACKUP_DIR"/mems26_*.db 2>/dev/null || echo "  (none)"
    exit 1
fi

if [[ "$BACKUP" == "latest" ]]; then
    BACKUP=$(ls -t "$BACKUP_DIR"/mems26_*.db 2>/dev/null | head -1)
    if [[ -z "$BACKUP" ]]; then
        echo "ERROR: No backups found in $BACKUP_DIR"
        exit 1
    fi
fi

if [[ ! -f "$BACKUP" ]]; then
    echo "ERROR: Backup file not found: $BACKUP"
    exit 1
fi

# Stop audit consumer if running
if [[ -f /tmp/mems26_audit.pid ]]; then
    PID=$(cat /tmp/mems26_audit.pid)
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping audit consumer (PID $PID)..."
        kill "$PID"
        sleep 1
    fi
fi

echo "Restoring from: $BACKUP"
cp "$BACKUP" "$DB_FILE"
echo "Restore complete: $DB_FILE"
echo "Restart backend and audit consumer to use restored DB."
