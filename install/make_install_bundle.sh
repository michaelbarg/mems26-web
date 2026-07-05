#!/usr/bin/env bash
# ============================================================================
# make_install_bundle.sh — run on THIS (dev) Mac. Produces ONE file you carry
# to your other Mac:  ~/mems26_install_<stamp>.tar.gz
#
# Inside: the whole repo (git bundle, incl. UNPUSHED commits), your live .env,
# and a double-click RUN_ME.command that installs everything. Read-only — does
# NOT touch the running system.
#
# Options:
#   --with-db   also include a Postgres dump (default: OFF — schema is rebuilt
#               fresh on the new machine; past data is disposable).
#   --no-env    do NOT include .env (new machine writes one from env.template).
# ============================================================================
set -uo pipefail
WITH_DB=0; WITH_ENV=1
while [ $# -gt 0 ]; do
  case "$1" in
    --with-db) WITH_DB=1 ;;
    --no-env)  WITH_ENV=0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac; shift
done

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M)"
STAGE="/tmp/mems26_install_${STAMP}"
OUT="$HOME/mems26_install_${STAMP}.tar.gz"
say() { printf '\033[1;36m[bundle]\033[0m %s\n' "$*"; }
mkdir -p "$STAGE"
cd "$REPO" || { echo "repo not found"; exit 1; }

say "[1/5] code → git bundle (incl. unpushed commits)"
git bundle create "$STAGE/mems26.gitbundle" --all
{ git rev-parse HEAD; git rev-parse --abbrev-ref HEAD; } > "$STAGE/GIT_HEAD.txt"

if [ "$WITH_ENV" = 1 ]; then
  say "[2/5] .env → env.copy (contains your token/flags — keep the tarball private)"
  cp .env "$STAGE/env.copy" 2>/dev/null && echo "  ok" || echo "  (.env missing)"
else
  say "[2/5] skipping .env (--no-env) — new machine will use install/env.template"
fi

if [ "$WITH_DB" = 1 ]; then
  say "[3/5] Postgres dump"
  PGDUMP="$(ls /Applications/Postgres.app/Contents/Versions/*/bin/pg_dump 2>/dev/null | tail -1)"
  [ -n "$PGDUMP" ] && "$PGDUMP" -Fc mems26 > "$STAGE/mems26.dump" 2>/dev/null && echo "  ok ($(du -h "$STAGE/mems26.dump" | cut -f1))" || echo "  (dump skipped — schema rebuilt fresh on new machine)"
else
  say "[3/5] no DB dump (default) — schema is rebuilt fresh by the installer"
fi

say "[4/5] RUN_ME.command (the one-touch entry point)"
cp "$REPO/install/RUN_ME.command.tmpl" "$STAGE/RUN_ME.command"
chmod +x "$STAGE/RUN_ME.command"
cat > "$STAGE/READ_ME_FIRST.txt" <<EOF
MEMS26 — one-file install for your other Mac (Sierra already installed there).
Built $(date) from $(hostname).
GIT HEAD: $(git rev-parse --short HEAD)  branch: $(git rev-parse --abbrev-ref HEAD)

HOW TO INSTALL (on the other Mac):
  1. Copy this whole .tar.gz over and unpack it (double-click, or: tar xzf <file>).
  2. Open the unpacked folder → double-click  RUN_ME.command
     (first time: right-click → Open, to get past macOS Gatekeeper).
  3. Follow the short Sierra-study steps it prints at the end.

Contents: mems26.gitbundle (all code, incl. unpushed) · env.copy (your .env) ·
RUN_ME.command (installer) · GIT_HEAD.txt. The installer itself lives inside the
code bundle at install/install_mems26.sh.
EOF

say "[5/5] tar → $OUT"
tar -czf "$OUT" -C "$(dirname "$STAGE")" "$(basename "$STAGE")" && rm -rf "$STAGE"
echo
say "DONE → $OUT  ($(du -h "$OUT" 2>/dev/null | cut -f1))"
say "Copy that ONE file to the other Mac, unpack, double-click RUN_ME.command."
