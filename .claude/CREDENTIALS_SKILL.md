# MEMS26 — MASTER CC CREDENTIALS & ACCESS SKILL (LOCKED)

Version: 1.0 · 2026-05-10 · 🔒 LOCKED
Drive: 1gJzthhg7WKNUWtDOphNtV8RhrsXP4b02ICZOr8FXty4

## SECURITY PRINCIPLE

CC NEVER stores or echoes actual secret values. This skill stores only
LOCATIONS + ACCESS PATTERNS. Real secrets stay in: .env (gitignored),
macOS Keychain, cloud dashboards.

## CREDENTIALS INVENTORY (locations only)

### Local .env
File: /Users/michael/Downloads/mems26_web_git/.env (chmod 600, gitignored)
Variables: BRIDGE_TOKEN, UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN,
CLOUD_URL, V9_EXPORT_DIR, SC_HISTORY_PATH, DATABASE_URL, ANTHROPIC_API_KEY,
NEXT_PUBLIC_API_URL, NEXT_PUBLIC_WS_URL, NEXT_PUBLIC_BRIDGE_TOKEN

### SSH Keys
GitHub: ~/.ssh/mesmclaude (config: github-mems26 host alias)

### macOS Keychain
MEMS26_ANTHROPIC_API_KEY, MEMS26_UPSTASH_TOKEN, MEMS26_RENDER_API_KEY

### Render Deploy Hook
curl -X POST "https://api.render.com/deploy/srv-d70kfu450q8c73a8vdg0?key=k0DuiJxZHOM"

### Access Patterns
A: source .env → run bridge/backend
B: git push via SSH (auto-loaded)
C: Render deploy via hook URL
D: Redis via UPSTASH REST API

## RULES
✅ Source .env, use SSH, deploy via hook, call Redis — without asking
🚫 Never echo secrets, write to git-tracked files, or hardcode in code
⚠️ Ask before: adding new credentials, rotating keys, LIVE trading

🔒 LOCKED. Modifications require explicit user approval.
