#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# MEMS26 post-commit hook
# Detects which prompt was committed, runs matching UAT, posts to Slack.
#
# Install:
#   cp scripts/post-commit-hook.sh .git/hooks/post-commit
#   chmod +x .git/hooks/post-commit
#
# Or symlink:
#   ln -sf ../../scripts/post-commit-hook.sh .git/hooks/post-commit
# ═══════════════════════════════════════════════════════════════

REPO_ROOT="$(git rev-parse --show-toplevel)"
SCRIPTS_DIR="$REPO_ROOT/scripts"
SLACK_WEBHOOK="${SLACK_UAT_WEBHOOK:-}"

# ── Extract prompt number from commit message ────────────────
COMMIT_MSG="$(git log -1 --pretty=%B)"
PROMPT_NUM=""

# Match patterns: "feat(event-bus):", "Prompt 1", "prompt_1", "(P1)", etc.
# Primary: look for "Prompt N" or "prompt N" or "prompt-N" or "prompt_N"
if [[ "$COMMIT_MSG" =~ [Pp]rompt[[:space:]_-]?([0-9]+) ]]; then
    PROMPT_NUM="${BASH_REMATCH[1]}"
fi

# Fallback: parse from feat() tag conventions
if [[ -z "$PROMPT_NUM" ]]; then
    # Map known commit prefixes to prompt numbers
    case "$COMMIT_MSG" in
        *"feat(event-bus)"*|*"feat(bridge): live_price"*|*"feat(backend): WebSocket"*|*"feat(frontend): usePriceStream"*)
            PROMPT_NUM=1 ;;
        *"feat(uat)"*)
            PROMPT_NUM="1_5" ;;
    esac
fi

if [[ -z "$PROMPT_NUM" ]]; then
    # No prompt detected — send a lightweight commit summary if Slack is enabled.
    if [[ -x "$SCRIPTS_DIR/slack_notify.sh" ]]; then
        COMMIT_SHORT=$(git log -1 --pretty=%h)
        BRANCH=$(git branch --show-current)
        "$SCRIPTS_DIR/slack_notify.sh" \
            "MEMS26 commit" \
            "Branch: \`${BRANCH}\` Commit: \`${COMMIT_SHORT}\`\nNo prompt number detected; UAT skipped." \
            "info"
    fi
    exit 0
fi

# ── Find matching UAT script ─────────────────────────────────
UAT_SCRIPT="$SCRIPTS_DIR/uat_prompt_${PROMPT_NUM}.sh"

if [[ ! -x "$UAT_SCRIPT" ]]; then
    echo "[post-commit] No UAT script for Prompt $PROMPT_NUM ($UAT_SCRIPT)"
    if [[ -x "$SCRIPTS_DIR/slack_notify.sh" ]]; then
        COMMIT_SHORT=$(git log -1 --pretty=%h)
        BRANCH=$(git branch --show-current)
        "$SCRIPTS_DIR/slack_notify.sh" \
            "Prompt ${PROMPT_NUM} committed — no UAT script" \
            "Branch: \`${BRANCH}\` Commit: \`${COMMIT_SHORT}\`\nMissing executable: \`${UAT_SCRIPT}\`" \
            "warn"
    fi
    exit 0
fi

# ── Run UAT ───────────────────────────────────────────────────
echo "[post-commit] Running UAT for Prompt $PROMPT_NUM..."
UAT_OUTPUT=$("$UAT_SCRIPT" --skip-sierra --skip-wait 2>&1)
UAT_EXIT=$?

# Extract summary line
SUMMARY_LINE=$(echo "$UAT_OUTPUT" | grep -E "UAT RESULT" | sed 's/\x1b\[[0-9;]*m//g' | sed 's/^ *//')

echo "$UAT_OUTPUT"

# ── Post to Slack ─────────────────────────────────────────────
if [[ -n "$SLACK_WEBHOOK" ]]; then
    COMMIT_SHORT=$(git log -1 --pretty=%h)
    BRANCH=$(git branch --show-current)

    if (( UAT_EXIT == 0 )); then
        EMOJI="white_check_mark"
        STATUS_TEXT="ALL PASS"
    else
        EMOJI="x"
        # Find first failure
        FIRST_FAIL=$(echo "$UAT_OUTPUT" | grep -m1 "\[FAIL\]" | sed 's/\x1b\[[0-9;]*m//g' | sed 's/^ *//')
        STATUS_TEXT="FAILED at: $FIRST_FAIL"
    fi

    SLACK_PAYLOAD=$(cat <<SLACKEOF
{
  "text": ":${EMOJI}: *Prompt ${PROMPT_NUM} UAT* — ${STATUS_TEXT}\nBranch: \`${BRANCH}\` Commit: \`${COMMIT_SHORT}\`\n${SUMMARY_LINE}"
}
SLACKEOF
)

    curl -s -X POST "$SLACK_WEBHOOK" \
        -H "Content-Type: application/json" \
        -d "$SLACK_PAYLOAD" >/dev/null 2>&1 || true
fi

exit 0
