#!/usr/bin/env bash
# mems26_snapshot.sh — snapshot every out-of-git surface BEFORE a change, for rollback.
#
# WHY: git versions the repo, but the things that actually run/broke live OUTSIDE git:
#   - the deployed DLL  (monolith source in ~/SierraChart*/ACS_Source + compiled .dll in Data/)
#   - .env              (live flag config, gitignored)
#   - LaunchAgents      (~/Library/LaunchAgents/com.mems26.*.plist)
# The 2026-06-25 incident was exactly a deployed-DLL problem with no rollback point.
# Run this BEFORE any deploy / .env edit / LaunchAgent change → instant, verifiable rollback.
#
# Usage:  scripts/mems26_snapshot.sh "why-label"      e.g. "pre-pipeline5-deploy"
# Restore with scripts/mems26_restore.sh <snapshot-dir>
set -uo pipefail

LABEL="${1:-manual}"
SAFE_LABEL=$(printf '%s' "$LABEL" | tr ' /' '__' | tr -cd 'A-Za-z0-9_.-')
TS=$(date -u +%Y%m%dT%H%M%SZ)
ROOT="${MEMS26_SNAPSHOT_DIR:-$HOME/mems26_snapshots}"
DIR="$ROOT/${TS}_${SAFE_LABEL}"
REPO="${MEMS26_REPO:-$HOME/Downloads/mems26_web_git}"

mkdir -p "$DIR/dll" "$DIR/env" "$DIR/launchagents"

# 1. git provenance (which committed code was live at snapshot time)
{
  echo "timestamp_utc: $TS"
  echo "label: $LABEL"
  if [ -d "$REPO/.git" ]; then
    echo "git_head: $(git -C "$REPO" rev-parse HEAD 2>/dev/null)"
    echo "git_branch: $(git -C "$REPO" rev-parse --abbrev-ref HEAD 2>/dev/null)"
    echo "git_last_commit: $(git -C "$REPO" log -1 --oneline 2>/dev/null)"
    echo "git_status_short:"
    git -C "$REPO" status --short 2>/dev/null | sed 's/^/  /'
  fi
} > "$DIR/git_provenance.txt"

# 2. DLL — deployed monolith source + compiled binary, for BOTH Sierra installs
for sc in SierraChart SierraChart2; do
  src="$HOME/$sc/ACS_Source/MES_AI_DataExport.cpp"
  bin="$HOME/$sc/Data/MES_AI_DataExport_64.dll"
  [ -f "$src" ] && cp -p "$src" "$DIR/dll/${sc}__ACS_Source__MES_AI_DataExport.cpp"
  [ -f "$bin" ] && cp -p "$bin" "$DIR/dll/${sc}__Data__MES_AI_DataExport_64.dll"
done

# 3. .env (live flags — local only, never committed)
[ -f "$REPO/.env" ] && cp -p "$REPO/.env" "$DIR/env/.env"

# 4. LaunchAgents
cp -p "$HOME/Library/LaunchAgents/com.mems26."*.plist "$DIR/launchagents/" 2>/dev/null || true

# 5. checksums (the rollback-integrity manifest)
( cd "$DIR" && find . -type f ! -name manifest.sha256 -print0 | xargs -0 shasum -a 256 ) \
  | sed "s#$DIR/##" > "$DIR/manifest.sha256"

# 6. one-line index entry
GIT_SHORT=$(git -C "$REPO" rev-parse --short HEAD 2>/dev/null || echo "nogit")
SIZE=$(du -sh "$DIR" 2>/dev/null | awk '{print $1}')
printf -- "- %s  [%s]  git=%s  size=%s  -> %s/\n" \
  "$TS" "$LABEL" "$GIT_SHORT" "$SIZE" "${TS}_${SAFE_LABEL}" >> "$ROOT/INDEX.md"

echo "✅ snapshot saved: $DIR  (git=$GIT_SHORT, size=$SIZE)"
echo "   files:"; ( cd "$DIR" && find . -type f | sed 's/^/     /' )
echo "   rollback: scripts/mems26_restore.sh \"$DIR\""
