from datetime import date, datetime
from zoneinfo import ZoneInfo
_ET = ZoneInfo("America/New_York")

def et_today() -> date:
    """Calendar date in America/New_York. Use for all 'today' queries."""
    return datetime.now(_ET).date()
