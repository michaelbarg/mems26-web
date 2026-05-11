"""GET /api/v9/spec/status — returns last compliance report."""

import os
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(tags=["v9-spec"])

REPORT_PATH = Path(__file__).resolve().parent.parent.parent.parent / "docs" / "SPEC_COMPLIANCE_REPORT.md"


@router.get("/api/v9/spec/status")
def spec_status():
    """Returns the latest spec compliance status."""
    if not REPORT_PATH.exists():
        return {"compliant": None, "message": "No compliance report found. Run scripts/spec_compliance/run_all.sh"}

    content = REPORT_PATH.read_text()
    # Parse result line
    compliant = "FAIL" not in content.split("Result:**")[1].split("\n")[0] if "Result:**" in content else None

    return {
        "compliant": compliant,
        "report_path": str(REPORT_PATH),
        "summary": content.split("\n")[3] if len(content.split("\n")) > 3 else "",
    }
