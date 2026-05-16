"""System 3 end-of-day analysis hook.

Observer-only placeholder for summarizing tick reversal / footprint journal
quality after the trading session.
"""


def build_eod_summary(entries: list[dict]) -> dict:
    return {
        "entries": len(entries),
        "setups": sum(1 for e in entries if e.get("classification") not in (None, "NO_SETUP")),
        "status": "READY",
    }


def compute_eod_report(entries: list[dict]) -> dict:
    """Compatibility entry point expected by V1 compliance."""
    return build_eod_summary(entries)

