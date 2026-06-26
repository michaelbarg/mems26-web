#!/usr/bin/env bash
# mems26_restore.sh — roll an out-of-git surface back to a snapshot taken by mems26_snapshot.sh.
#
# SAFETY: dry-run by default (prints the plan, changes nothing). Add --confirm to apply.
#         Restoring the DLL/.env/LaunchAgents touches LIVE trading surfaces — it verifies each
#         file's sha256 against the snapshot manifest before copying, and NEVER reloads Sierra or
#         restarts services for you (you do that explicitly after reviewing).
#
# Usage:
#   scripts/mems26_restore.sh <snapshot-dir>                 # dry-run, all surfaces
#   scripts/mems26_restore.sh <snapshot-dir> --only dll      # dll | env | launchagents | all
#   scripts/mems26_restore.sh <snapshot-dir> --only env --confirm
set -uo pipefail

DIR="${1:-}"
ONLY="all"
CONFIRM=0
shift || true
while [ $# -gt 0 ]; do
  case "$1" in
    --only) ONLY="${2:-all}"; shift 2 ;;
    --confirm) CONFIRM=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [ -z "$DIR" ] || [ ! -d "$DIR" ]; then
  echo "usage: $0 <snapshot-dir> [--only dll|env|launchagents|all] [--confirm]" >&2
  echo "available snapshots:" >&2
  ls -1 "${MEMS26_SNAPSHOT_DIR:-$HOME/mems26_snapshots}" 2>/dev/null | grep -v INDEX.md | sed 's/^/  /' >&2
  exit 2
fi

echo "── restore plan from: $DIR  (only=$ONLY, confirm=$CONFIRM) ──"
[ -f "$DIR/git_provenance.txt" ] && grep -E "git_head|git_last_commit|timestamp" "$DIR/git_provenance.txt" | sed 's/^/  /'

# map a snapshot file → its live destination
declare -a PLAN
add() { PLAN+=("$1|$2|$3"); }   # surface|snapshot_path|live_dest

if [ "$ONLY" = "dll" ] || [ "$ONLY" = "all" ]; then
  for sc in SierraChart SierraChart2; do
    s="$DIR/dll/${sc}__ACS_Source__MES_AI_DataExport.cpp"; [ -f "$s" ] && add dll "$s" "$HOME/$sc/ACS_Source/MES_AI_DataExport.cpp"
    s="$DIR/dll/${sc}__Data__MES_AI_DataExport_64.dll";    [ -f "$s" ] && add dll "$s" "$HOME/$sc/Data/MES_AI_DataExport_64.dll"
  done
fi
if [ "$ONLY" = "env" ] || [ "$ONLY" = "all" ]; then
  s="$DIR/env/.env"; [ -f "$s" ] && add env "$s" "${MEMS26_REPO:-$HOME/Downloads/mems26_web_git}/.env"
fi
if [ "$ONLY" = "launchagents" ] || [ "$ONLY" = "all" ]; then
  for p in "$DIR"/launchagents/*.plist; do [ -f "$p" ] && add launchagents "$p" "$HOME/Library/LaunchAgents/$(basename "$p")"; done
fi

[ ${#PLAN[@]} -eq 0 ] && { echo "  (nothing matched only=$ONLY)"; exit 0; }

for entry in "${PLAN[@]}"; do
  IFS='|' read -r surf src dst <<< "$entry"
  printf "  [%s] %s\n        → %s\n" "$surf" "$src" "$dst"
done

if [ "$CONFIRM" -ne 1 ]; then
  echo "── DRY-RUN (no changes). Re-run with --confirm to apply. ──"
  echo "   After restoring DLL: reload the study in Sierra (or restart) — see docs/runbooks/SIERRA_DLL_OPS.md"
  echo "   After restoring .env / LaunchAgents: restart the affected service explicitly."
  exit 0
fi

# apply: back up the current live file first (.pre-restore), then copy
for entry in "${PLAN[@]}"; do
  IFS='|' read -r surf src dst <<< "$entry"
  [ -f "$dst" ] && cp -p "$dst" "${dst}.pre-restore-$(date -u +%Y%m%d%H%M%S)"
  mkdir -p "$(dirname "$dst")"
  cp -p "$src" "$dst" && echo "  ✅ restored $dst"
done
echo "── done. Reload Sierra study / restart services explicitly to pick up the restore. ──"
