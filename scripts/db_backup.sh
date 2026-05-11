#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# MEMS26 DB Backup — SQLite daily backup with 30-day retention
#
# Usage: ./scripts/db_backup.sh
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DB_FILE="$REPO_ROOT/data/mems26_local.db"
BACKUP_DIR="$REPO_ROOT/data/backups"
RETENTION_DAYS=30

if [[ ! -f "$DB_FILE" ]]; then
    echo "ERROR: DB file not found: $DB_FILE"
    exit 1
fi

mkdir -p "$BACKUP_DIR"

BACKUP_FILE="$BACKUP_DIR/mems26_$(date +%Y%m%d_%H%M%S).db"
sqlite3 "$DB_FILE" ".backup '$BACKUP_FILE'"
echo "Backup created: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"

# Retention: delete backups older than N days
deleted=$(find "$BACKUP_DIR" -name "mems26_*.db" -mtime +$RETENTION_DAYS -delete -print 2>/dev/null | wc -l | tr -d ' ')
if (( deleted > 0 )); then
    echo "Cleaned up $deleted old backups (>$RETENTION_DAYS days)"
fi

echo "Current backups: $(ls "$BACKUP_DIR"/mems26_*.db 2>/dev/null | wc -l | tr -d ' ')"
