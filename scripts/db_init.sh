#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# MEMS26 DB Init — creates tables via SQLAlchemy create_all
#
# Usage: ./scripts/db_init.sh
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# Load .env
if [[ -f .env ]]; then
    set -a; source .env; set +a
fi

# Default to SQLite for local dev
export DATABASE_URL="${DATABASE_URL:-sqlite:///./data/mems26_local.db}"

# Create data dir
mkdir -p data data/backups

echo "DB Init: DATABASE_URL=$DATABASE_URL"

python3 -c "
import os
os.environ.setdefault('DATABASE_URL', '$DATABASE_URL')
from backend.v9.db.session import init_db, DATABASE_URL
init_db()
print(f'DB ready: {DATABASE_URL}')

# Report table count
from backend.v9.db.session import engine
from sqlalchemy import inspect
insp = inspect(engine)
tables = insp.get_table_names()
print(f'Tables: {len(tables)}')
for t in sorted(tables):
    print(f'  - {t}')
"

echo "DB init complete."
