#!/usr/bin/env bash
# ============================================================================
# MEMS26 uninstall — stop + remove the LaunchAgents. Leaves code + DB in place
# by default (add --purge-db to drop the database, --purge-repo to delete code).
#
# Usage: install/uninstall_mems26.sh [--purge-db] [--purge-repo] [--yes]
# ============================================================================
set -uo pipefail
PURGE_DB=0; PURGE_REPO=0; YES=0
while [ $# -gt 0 ]; do
  case "$1" in
    --purge-db) PURGE_DB=1 ;;
    --purge-repo) PURGE_REPO=1 ;;
    --yes|-y) YES=1 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac; shift
done
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLIST_DIR="$HOME/Library/LaunchAgents"
say() { printf '\033[1;36m[uninstall]\033[0m %s\n' "$*"; }

for svc in backend bridge export_promoter; do
  dest="$PLIST_DIR/com.mems26.${svc}.plist"
  if [ -f "$dest" ]; then
    launchctl unload -w "$dest" 2>/dev/null || true
    rm -f "$dest"
    say "removed com.mems26.${svc}"
  fi
done
# Belt-and-suspenders: kill any stragglers on the ports.
for pid in $(lsof -tnP -iTCP:8000 -sTCP:LISTEN 2>/dev/null; lsof -tnP -iTCP:3000 -sTCP:LISTEN 2>/dev/null); do
  kill "$pid" 2>/dev/null || true
done
say "services stopped."

if [ "$PURGE_DB" = 1 ]; then
  [ "$YES" = 1 ] || { read -r -p "Drop database 'mems26'? [y/N] " a; [ "$a" = y ] || exit 0; }
  DROPDB="$(ls /Applications/Postgres.app/Contents/Versions/*/bin/dropdb 2>/dev/null | tail -1 || command -v dropdb)"
  "$DROPDB" mems26 2>/dev/null && say "database dropped." || say "dropdb failed/absent."
fi
if [ "$PURGE_REPO" = 1 ]; then
  [ "$YES" = 1 ] || { read -r -p "Delete repo at $REPO ? [y/N] " a; [ "$a" = y ] || exit 0; }
  say "NOTE: not deleting the dir you're running from. Remove manually: rm -rf '$REPO'"
fi
say "done. (code + snapshots in ~/mems26_snapshots preserved)"
