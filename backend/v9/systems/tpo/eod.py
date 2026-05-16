"""TPO Stage F end-of-day processing hook."""


def compute_eod_report(profile) -> dict:
    return {
        "shape": getattr(getattr(profile, "shape", None), "value", getattr(profile, "shape", None)),
        "naked_pocs": list(getattr(profile, "naked_pocs", []) or []),
        "incomplete_letters": list(getattr(profile, "incomplete_letters", []) or []),
        "status": "READY",
    }


def process_eod(profile) -> dict:
    return compute_eod_report(profile)

