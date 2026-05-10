"""V9 auth — BRIDGE_TOKEN check (same pattern as V8)."""

import os
from fastapi import Header, HTTPException

BRIDGE_TOKEN = os.getenv("BRIDGE_TOKEN", "")
if not BRIDGE_TOKEN:
    raise RuntimeError(
        "BRIDGE_TOKEN env var is required but not set. "
        "Set it in .env or your hosting provider's environment variables."
    )



def verify_bridge_token(authorization: str = Header(...)):
    """Verify Bearer token from Bridge."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header")
    token = authorization.removeprefix("Bearer ")
    if token != BRIDGE_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid bridge token")
    return token
