from datetime import date, datetime
from zoneinfo import ZoneInfo

BOGOTA = ZoneInfo("America/Bogota")


def bogota_date(instant: datetime) -> date:
    """The business date of an instant: the day it is in Colombia, never in UTC."""
    return instant.astimezone(BOGOTA).date()


def today_in_bogota() -> date:
    """Today's business date."""
    return bogota_date(datetime.now(BOGOTA))
