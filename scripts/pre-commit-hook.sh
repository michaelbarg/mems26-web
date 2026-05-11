#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# MEMS26 pre-commit hook — catches common mistakes before commit
#
# Install:
#   ln -sf ../../scripts/pre-commit-hook.sh .git/hooks/pre-commit
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
FAIL=0

# ── Get list of staged files ─────────────────────────────────
STAGED=$(git diff --cached --name-only --diff-filter=ACM)
if [[ -z "$STAGED" ]]; then
    exit 0
fi

# ═══════════════════════════════════════════════════════════════
# CHECK 1: Test mock values in production code
#   5412. is the canonical test price used in event_bus tests.
#   Must not appear in backend/, bridge/, or frontend/v9/src/.
# ═══════════════════════════════════════════════════════════════
PROD_FILES=$(echo "$STAGED" | grep -E "^(backend|bridge|frontend/v9/src)/" | grep -v "^tests/" | grep -v "__pycache__" || true)
if [[ -n "$PROD_FILES" ]]; then
    MOCK_HITS=$(echo "$PROD_FILES" | xargs grep -l "5412\." 2>/dev/null || true)
    if [[ -n "$MOCK_HITS" ]]; then
        echo "ERROR: Test mock value '5412.' found in production files:"
        echo "$MOCK_HITS" | sed 's/^/  /'
        echo "Remove test data before committing."
        FAIL=1
    fi
fi

# ═══════════════════════════════════════════════════════════════
# CHECK 2: TODO/FIXME/XXX in committed code
#   Allowed in: docs/, scripts/, tests/, *.md, CLAUDE.md
#   Blocked in: backend/, bridge/, frontend/v9/src/
# ═══════════════════════════════════════════════════════════════
CODE_FILES=$(echo "$STAGED" | grep -E "^(backend|bridge|frontend/v9/src)/" | grep -vE "\.(md|txt|yaml|yml)$" | grep -v "__pycache__" || true)
if [[ -n "$CODE_FILES" ]]; then
    TODO_HITS=""
    for f in $CODE_FILES; do
        if [[ -f "$REPO_ROOT/$f" ]]; then
            hits=$(grep -nE "(TODO|FIXME|XXX)" "$REPO_ROOT/$f" 2>/dev/null || true)
            if [[ -n "$hits" ]]; then
                TODO_HITS="${TODO_HITS}${f}:\n${hits}\n"
            fi
        fi
    done
    if [[ -n "$TODO_HITS" ]]; then
        echo "WARNING: TODO/FIXME/XXX found in production code:"
        echo -e "$TODO_HITS" | head -20
        echo "Consider creating a GitHub issue instead."
        # Warning only — don't block commit
    fi
fi

# ═══════════════════════════════════════════════════════════════
# CHECK 3: Secrets detection (basic)
# ═══════════════════════════════════════════════════════════════
if [[ -n "$PROD_FILES" ]]; then
    SECRET_HITS=$(echo "$PROD_FILES" | xargs grep -lE "(sk-[a-zA-Z0-9]{20,}|AKIA[A-Z0-9]{16}|ghp_[a-zA-Z0-9]{36})" 2>/dev/null || true)
    if [[ -n "$SECRET_HITS" ]]; then
        echo "ERROR: Possible secrets detected in:"
        echo "$SECRET_HITS" | sed 's/^/  /'
        FAIL=1
    fi
fi

if (( FAIL )); then
    echo ""
    echo "Pre-commit checks FAILED. Fix issues above or use --no-verify to bypass."
    exit 1
fi

exit 0
