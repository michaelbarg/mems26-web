# Anthropic API Key Setup — MEMS26

Securely stores and validates an Anthropic API key for MEMS26 agent infrastructure.
Decision reference: **D-048** (MEMS26_FIRST.md V2)

## Prerequisites

1. Anthropic Console account at [console.anthropic.com](https://console.anthropic.com)
2. API key created (`sk-ant-api03-...`) under API Keys
3. Monthly spending cap set (recommended: $150)
4. Python 3.10+

## Setup

```bash
cd tools/anthropic-setup
pip install -r requirements.txt
chmod +x setup_anthropic_key.sh
./setup_anthropic_key.sh
```

## Validate

```bash
python3 validate_key.py
```

Reports: key validity, latency, model used, estimated cost (~$0.000005).

## Troubleshooting

| Error | Fix |
|-------|-----|
| `authentication_error` (401) | Key invalid or revoked. Regenerate at console.anthropic.com → API Keys |
| `permission_error` (403) | Key lacks permissions. Check workspace assignment |
| `rate_limit_error` (429) | Rate-limited. Wait 30s and retry |
| `anthropic not installed` | Run `pip install -r requirements.txt` |

## Cost Monitoring

Track usage at [console.anthropic.com/usage](https://console.anthropic.com/usage)

## Key Rotation

1. Go to console.anthropic.com → API Keys
2. Create new key → copy it
3. Revoke old key
4. Re-run `./setup_anthropic_key.sh` with new key

## Files

- `setup_anthropic_key.sh` — Interactive key capture + API validation
- `validate_key.py` — Standalone validation (Python)
- `.env.example` — Template with placeholder (committed)
- `.env` — Real key (gitignored, chmod 600)
