#!/bin/bash
# package_for_migration.sh — bundle the FULL MEMS26 stack for the second (Sierra) machine.
#
# Run this on the SOURCE MacBook. It produces one tarball you copy to the trading
# machine, plus a restore script inside it. Handles the three migration gotchas:
#   1) 96+ UNPUSHED commits → uses `git bundle --all` (NOT clone-from-remote, which
#      would pull stale code).
#   2) current flags incl. DAYTYPE_PLAYBOOK → copies the live .env verbatim.
#   3) September contract → manifest reminds you to roll the Sierra studies to MESU26.
#
# It does NOT touch the running system (read-only snapshot). Safe any time.
set -uo pipefail

REPO="/Users/michael/Downloads/mems26_web_git"
STAMP="$(date +%Y%m%d_%H%M)"
STAGE="/tmp/mems26_migration_${STAMP}"
OUT="${HOME}/mems26_migration_${STAMP}.tar.gz"
mkdir -p "$STAGE"
cd "$REPO" || { echo "repo not found: $REPO"; exit 1; }

echo "[1/6] git history (incl. unpushed commits) → bundle"
git bundle create "$STAGE/mems26.gitbundle" --all
git rev-parse HEAD > "$STAGE/GIT_HEAD.txt"
git rev-parse --abbrev-ref HEAD >> "$STAGE/GIT_HEAD.txt"
git status --short > "$STAGE/GIT_uncommitted.txt" 2>/dev/null

echo "[2/6] .env (flags + connection strings) → copy verbatim"
cp .env "$STAGE/env.copy" 2>/dev/null && echo "  ok" || echo "  (.env missing!)"

echo "[3/6] LaunchAgents (backend + bridge)"
cp "$HOME/Library/LaunchAgents/com.mems26.backend.plist" "$STAGE/" 2>/dev/null && echo "  backend plist ok" || echo "  backend plist missing"
cp "$HOME/Library/LaunchAgents/com.mems26.bridge.plist"  "$STAGE/" 2>/dev/null && echo "  bridge plist ok"  || echo "  bridge plist missing"

echo "[4/6] Postgres dump (mems26)"
PGDUMP="$(ls /Applications/Postgres.app/Contents/Versions/*/bin/pg_dump 2>/dev/null | tail -1)"
if [ -n "$PGDUMP" ]; then "$PGDUMP" -Fc mems26 > "$STAGE/mems26.dump" 2>/dev/null && echo "  ok ($(du -h "$STAGE/mems26.dump" | cut -f1))" || echo "  dump failed (DB data is disposable — can start fresh)"; else echo "  pg_dump not found"; fi

echo "[5/6] manifest + restore script"
cat > "$STAGE/MANIFEST.txt" <<EOF
MEMS26 migration bundle — $(date)
SOURCE: $(hostname) : $REPO
GIT HEAD:   $(git rev-parse HEAD)
GIT branch: $(git rev-parse --abbrev-ref HEAD)
GIT ahead of remote: $(git rev-list --count '@{u}..HEAD' 2>/dev/null || echo '?') commits  (bundle carries these)
--- flags ON (.env) ---
$(grep -E '=(1|true|yes)$' .env 2>/dev/null)
--- standing-decisions (must stay OFF) ---
LAYER0_CHOP_GATE / S2_CHOPPINESS_GATE / S2_REQUIRE_COT_AMT  → leave unset
--- Sierra (do on the trading machine) ---
* Contract is SEPTEMBER (MESU26) — set every chart/study to MESU26, NOT June.
* Deploy MES_AI_DataExport + woodies/5min/cumulative_delta/tpo studies.
* Set study Input-4 export dir = ~/SierraChart_Data/v9_export/ on the new machine.
* Bridge must push to http://localhost:8000 ONLY (never a cloud URL).
EOF

cat > "$STAGE/RESTORE_on_trading_machine.sh" <<'RESTORE'
#!/bin/bash
# Run on the TRADING MACHINE, from the unpacked bundle dir. Edit DEST first.
set -uo pipefail
DEST="$HOME/Downloads/mems26_web_git"        # <-- where to place the repo
echo "1) repo from bundle (carries unpushed commits)"
git clone mems26.gitbundle "$DEST" && cd "$DEST" && git checkout "$(sed -n 2p GIT_HEAD.txt 2>/dev/null || echo main)"
echo "2) .env"; cp ../env.copy "$DEST/.env" 2>/dev/null || cp env.copy "$DEST/.env"
echo "3) Postgres"; createdb mems26 2>/dev/null; PGR="$(ls /Applications/Postgres.app/Contents/Versions/*/bin/pg_restore | tail -1)"; [ -f mems26.dump ] && "$PGR" -d mems26 mems26.dump
echo "4) LaunchAgents → ~/Library/LaunchAgents/  (EDIT absolute paths inside first!)"
echo "   cp com.mems26.*.plist ~/Library/LaunchAgents/ ; then fix WorkingDirectory + Python path + StandardOutPath"
echo "5) frontend: cd $DEST/frontend/v9 && npm install && npx next build"
echo "6) Sierra: set all studies to MESU26 + Input-4 export dir (see MANIFEST.txt)"
echo "7) verify: docs/runbooks/PRE_TRADE_PROTOCOL.md  +  curl localhost:8000/health"
RESTORE
chmod +x "$STAGE/RESTORE_on_trading_machine.sh"

echo "[6/6] tar"
tar -czf "$OUT" -C "$(dirname "$STAGE")" "$(basename "$STAGE")" && rm -rf "$STAGE"
echo
echo "DONE → $OUT  ($(du -h "$OUT" 2>/dev/null | cut -f1))"
echo "Copy it to the trading machine, unpack, read MANIFEST.txt, run RESTORE_on_trading_machine.sh."
