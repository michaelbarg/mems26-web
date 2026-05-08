#!/usr/bin/env bash
# MEMS26 Restore Script
# Restores from a specific backup timestamp
# Usage: ./restore_from_backup.sh <timestamp> [--component bridge|sierra|all]

set -euo pipefail

BACKUP_ROOT="$HOME/mems26-backups"
MEMS26_REPO="$HOME/Documents/GitHub/mems26-web"
SIERRA_DATA="$HOME/SierraChart2"

# --- Args ---
if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <timestamp> [--component bridge|sierra|all]"
    echo ""
    echo "Available backups:"
    ls -1d "$BACKUP_ROOT"/20* 2>/dev/null | while read -r dir; do
        size=$(du -sh "$dir" 2>/dev/null | cut -f1)
        echo "  $(basename "$dir")  ($size)"
    done
    exit 1
fi

TIMESTAMP="$1"
COMPONENT="${3:-all}"
BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"

if [[ ! -d "$BACKUP_DIR" ]]; then
    echo "ERROR: Backup not found: $BACKUP_DIR"
    exit 1
fi

log() {
    echo "[$(date '+%H:%M:%S')] $1"
}

restore_dir() {
    local src="$1"
    local dest="$2"
    local label="$3"

    if [[ ! -d "$src" ]]; then
        log "SKIP: $label — not in backup"
        return 0
    fi

    log "Restoring $label: $src → $dest"
    mkdir -p "$dest"
    rsync -a --backup --suffix=".pre-restore-$(date +%Y%m%d)" "$src/" "$dest/"
}

restore_file() {
    local src="$1"
    local dest="$2"
    local label="$3"

    if [[ ! -f "$src" ]]; then
        log "SKIP: $label — not in backup"
        return 0
    fi

    log "Restoring $label: $src → $dest"
    if [[ -f "$dest" ]]; then
        cp "$dest" "$dest.pre-restore-$(date +%Y%m%d)"
    fi
    cp "$src" "$dest"
}

# --- Confirmation ---
echo ""
echo "=== MEMS26 Restore ==="
echo "Backup:    $BACKUP_DIR"
echo "Component: $COMPONENT"
echo ""
echo "WARNING: This will overwrite current files. Existing files get .pre-restore suffix."
echo ""
read -p "Continue? (yes/no): " confirm
if [[ "$confirm" != "yes" ]]; then
    echo "Aborted."
    exit 0
fi

# --- Restore ---
case "$COMPONENT" in
    bridge)
        restore_dir "$BACKUP_DIR/bridge" "$MEMS26_REPO/bridge" "Bridge"
        ;;
    sierra)
        restore_dir "$BACKUP_DIR/sierra/Data" "$SIERRA_DATA/Data" "Sierra Data"
        restore_file "$BACKUP_DIR/sierra/SierraChart.ini" "$SIERRA_DATA/SierraChart.ini" "Sierra Config"
        restore_dir "$BACKUP_DIR/sierra/Studies" "$SIERRA_DATA/Studies" "Sierra Studies"
        restore_file "$BACKUP_DIR/sierra/mes_ai_data.json" "$SIERRA_DATA/mes_ai_data.json" "Sierra AI Export"
        ;;
    all)
        restore_dir "$BACKUP_DIR/bridge" "$MEMS26_REPO/bridge" "Bridge"
        restore_dir "$BACKUP_DIR/sierra/Data" "$SIERRA_DATA/Data" "Sierra Data"
        restore_file "$BACKUP_DIR/sierra/SierraChart.ini" "$SIERRA_DATA/SierraChart.ini" "Sierra Config"
        restore_dir "$BACKUP_DIR/sierra/Studies" "$SIERRA_DATA/Studies" "Sierra Studies"
        restore_file "$BACKUP_DIR/sierra/mes_ai_data.json" "$SIERRA_DATA/mes_ai_data.json" "Sierra AI Export"
        ;;
    *)
        echo "Unknown component: $COMPONENT. Use: bridge, sierra, or all"
        exit 1
        ;;
esac

log "=== Restore Complete ==="
echo ""
echo "Next steps:"
echo "  1. Verify restored files"
echo "  2. Restart bridge if bridge was restored: cd bridge && python3 json_bridge.py"
echo "  3. Restart Sierra Chart if Sierra config was restored"
