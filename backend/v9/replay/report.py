"""Canonical Replay Kernel validation report."""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Optional

from .manifest import canonical_result_hash, manifest_hash
from .types import ReplayManifest, ReplaySession, SessionQuality


def build_validation_report(
    manifest: ReplayManifest,
    *,
    session: Optional[ReplaySession] = None,
    quality: Optional[SessionQuality] = None,
) -> Dict[str, Any]:
    if quality is None:
        if session is None:
            raise ValueError("validation report requires session or quality")
        quality = session.quality
    payload: Dict[str, Any] = {
        "schema_version": "1",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "manifest": manifest,
        "manifest_hash": manifest_hash(manifest),
        "status": "PASS" if quality.judgeable else "NOT_JUDGEABLE",
        "quality": quality.to_dict(),
        "source_hashes": session.source_hashes if session else {},
    }
    payload["result_hash"] = canonical_result_hash(payload)
    return payload
