#!/bin/bash
# scripts/credentials_self_test.sh — verifies CC can access all needed credentials
set -e

echo "═══ Master CC Credentials Self-Test ═══"
PASS=0
FAIL=0
WARN=0

# 1. .env present + readable
if [ -r /Users/michael/Downloads/mems26_web_git/.env ]; then
    echo "✅ .env readable"
    PASS=$((PASS + 1))
else
    echo "🔴 .env missing or unreadable"
    FAIL=$((FAIL + 1))
fi

# 2. Required env vars (without echoing values)
source /Users/michael/Downloads/mems26_web_git/.env 2>/dev/null
TOTAL_VARS=0
SET_VARS=0
for var in BRIDGE_TOKEN UPSTASH_REDIS_REST_URL UPSTASH_REDIS_REST_TOKEN CLOUD_URL V9_EXPORT_DIR; do
    TOTAL_VARS=$((TOTAL_VARS + 1))
    eval val=\$$var
    if [ -n "$val" ]; then
        echo "✅ $var set"
        SET_VARS=$((SET_VARS + 1))
    else
        echo "🔴 $var missing"
        FAIL=$((FAIL + 1))
    fi
done
echo "   Env vars: $SET_VARS/$TOTAL_VARS"

# 3. SSH key for GitHub
if [ -r ~/.ssh/mesmclaude ]; then
    echo "✅ GitHub SSH key (~/.ssh/mesmclaude)"
    PASS=$((PASS + 1))
else
    echo "🔴 GitHub SSH key missing"
    FAIL=$((FAIL + 1))
fi

# 4. Keychain items (non-blocking)
for item in MEMS26_ANTHROPIC_API_KEY MEMS26_RENDER_API_KEY MEMS26_UPSTASH_TOKEN; do
    if security find-generic-password -s "$item" >/dev/null 2>&1; then
        echo "✅ Keychain: $item"
        PASS=$((PASS + 1))
    else
        echo "🟡 Keychain: $item not found (optional)"
        WARN=$((WARN + 1))
    fi
done

# 5. Render reachable
if curl -s -m 5 https://mems26-web.onrender.com/health >/dev/null 2>&1; then
    echo "✅ Render reachable"
    PASS=$((PASS + 1))
else
    echo "🔴 Render unreachable"
    FAIL=$((FAIL + 1))
fi

# 6. Redis reachable
if [ -n "$UPSTASH_REDIS_REST_TOKEN" ] && [ -n "$UPSTASH_REDIS_REST_URL" ]; then
    if curl -s -m 5 -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN" \
        "$UPSTASH_REDIS_REST_URL/get/test" >/dev/null 2>&1; then
        echo "✅ Redis reachable"
        PASS=$((PASS + 1))
    else
        echo "🔴 Redis unreachable"
        FAIL=$((FAIL + 1))
    fi
else
    echo "🔴 Redis credentials missing"
    FAIL=$((FAIL + 1))
fi

# Cleanup
unset BRIDGE_TOKEN UPSTASH_REDIS_REST_TOKEN UPSTASH_REDIS_REST_URL DATABASE_URL

echo ""
echo "═══ Results: ✅ $PASS passed · 🔴 $FAIL failed · 🟡 $WARN warnings ═══"
[ "$FAIL" -eq 0 ] && echo "Credentials: READY" || echo "Credentials: INCOMPLETE"
