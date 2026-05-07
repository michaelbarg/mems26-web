#!/usr/bin/env python3
"""Standalone Anthropic key validator. Exit 0 = valid, exit 1 = invalid."""
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
if not env_path.exists():
    print("❌ .env not found. Run setup_anthropic_key.sh first.")
    sys.exit(1)

load_dotenv(env_path)
key = os.getenv("ANTHROPIC_API_KEY", "")
if not key.startswith("sk-ant-"):
    print("❌ ANTHROPIC_API_KEY not in .env or invalid format.")
    sys.exit(1)

try:
    from anthropic import Anthropic
except ImportError:
    print("❌ anthropic package not installed. Run: pip install anthropic")
    sys.exit(1)

client = Anthropic(api_key=key)
start = time.time()
try:
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1,
        messages=[{"role": "user", "content": "ok"}],
    )
    latency_ms = int((time.time() - start) * 1000)
    print(f"✅ Key valid")
    print(f"   Latency: {latency_ms}ms")
    print(f"   Model: {resp.model}")
    print(f"   Validation cost: ~$0.000005 (1 input token, 1 output token)")
    sys.exit(0)
except Exception as e:
    print(f"❌ Validation failed: {type(e).__name__}: {e}")
    sys.exit(1)
