from datetime import date, datetime
from zoneinfo import ZoneInfo

PK_TZ = ZoneInfo("Asia/Karachi")


def today_pk() -> date:
    """Today's date in Pakistan, whatever timezone the server runs in."""
    return datetime.now(PK_TZ).date()
