from datetime import date, datetime
from zoneinfo import ZoneInfo

BOGOTA = ZoneInfo("America/Bogota")


def today_in_bogota() -> date:
    """Today's business date. "Today" is always the day in Colombia, never in UTC."""
    return datetime.now(BOGOTA).date()
