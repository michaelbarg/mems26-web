#!/usr/bin/env bash
# MEMS26 Local Backup Script
# Backs up bridge/, Sierra Chart config, and local data
# Usage: ./backup_local.sh [--dry-run]

set -euo pipefail

# --- Configuration ---
BACKUP_ROOT="$HOME/mems26-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"
MAX_BACKUPS=14  # Keep 2 weeks of daily backups

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "[DRY RUN] No files will be copied or deleted."
fi

# --- Source directories ---
MEMS26_REPO="$HOME/Documents/GitHub/mems26-web"
SIERRA_DATA="$HOME/SierraChart2"
BRIDGE_DIR="$MEMS26_REPO/bridge"

# --- Functions ---
log() {
    echo "[$(date '+%H:%M:%S')] $1"
}

backup_dir() {
    local src="$1"
    local dest="$2"
    local label="$3"

    if [[ ! -d "$src" ]]; then
        log "SKIP: $label — source not found: $src"
        return 0
    fi

    local file_count
    file_count=$(find "$src" -type f 2>/dev/null | wc -l | tr -d ' ')
    log "Backing up $label ($file_count files): $src → $dest"

    if [[ "$DRY_RUN" == "false" ]]; then
        mkdir -p "$dest"
        rsync -a --exclude='__pycache__' --exclude='.DS_Store' --exclude='node_modules' "$src/" "$dest/"
    fi
}

backup_file() {
    local src="$1"
    local dest="$2"
    local label="$3"

    if [[ ! -f "$src" ]]; then
        log "SKIP: $label — file not found: $src"
        return 0
    fi

    log "Backing up $label: $src → $dest"
    if [[ "$DRY_RUN" == "false" ]]; then
        mkdir -p "$(dirname "$dest")"
        cp "$src" "$dest"
    fi
}

cleanup_old() {
    if [[ ! -d "$BACKUP_ROOT" ]]; then
        return 0
    fi

    local count
    count=$(ls -1d "$BACKUP_ROOT"/20* 2>/dev/null | wc -l | tr -d ' ')

    if [[ "$count" -le "$MAX_BACKUPS" ]]; then
        log "Backup count ($count) within limit ($MAX_BACKUPS). No cleanup needed."
        return 0
    fi

    local to_remove=$((count - MAX_BACKUPS))
    log "Cleaning up $to_remove old backup(s)..."

    if [[ "$DRY_RUN" == "false" ]]; then
        ls -1d "$BACKUP_ROOT"/20* | head -n "$to_remove" | while read -r dir; do
            log "  Removing: $dir"
            rm -rf "$dir"
        done
    else
        ls -1d "$BACKUP_ROOT"/20* | head -n "$to_remove" | while read -r dir; do
            log "  Would remove: $dir"
        done
    fi
}

# --- Main ---
log "=== MEMS26 Backup Starting ==="
log "Backup destination: $BACKUP_DIR"

# 1. Bridge directory (Python scripts, config)
backup_dir "$BRIDGE_DIR" "$BACKUP_DIR/bridge" "Bridge"

# 2. Sierra Chart data & config
backup_dir "$SIERRA_DATA/Data" "$BACKUP_DIR/sierra/Data" "Sierra Data"
backup_file "$SIERRA_DATA/SierraChart.ini" "$BACKUP_DIR/sierra/SierraChart.ini" "Sierra Config"
backup_dir "$SIERRA_DATA/Studies" "$BACKUP_DIR/sierra/Studies" "Sierra Studies"

# 3. Local data files (mes_ai_data.json, etc.)
backup_file "$SIERRA_DATA/mes_ai_data.json" "$BACKUP_DIR/sierra/mes_ai_data.json" "Sierra AI Export"

# 4. Git state snapshot
if [[ "$DRY_RUN" == "false" ]]; then
    mkdir -p "$BACKUP_DIR/git-state"
    (cd "$MEMS26_REPO" && git log --oneline -20 > "$BACKUP_DIR/git-state/recent_commits.txt" 2>/dev/null || true)
    (cd "$MEMS26_REPO" && git branch -v > "$BACKUP_DIR/git-state/branches.txt" 2>/dev/null || true)
    (cd "$MEMS26_REPO" && git stash list > "$BACKUP_DIR/git-state/stashes.txt" 2>/dev/null || true)
fi
log "Saved git state snapshot"

# 5. Cleanup old backups
cleanup_old

# 6. Summary
if [[ "$DRY_RUN" == "false" ]]; then
    total_size=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
    log "=== Backup Complete: $BACKUP_DIR ($total_size) ==="
else
    log "=== Dry Run Complete ==="
fi
