from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TIMEZONE = "Asia/Makassar"

def get_zoneinfo(timezone_name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name or DEFAULT_TIMEZONE)
    except ZoneInfoNotFoundError:
        return ZoneInfo(DEFAULT_TIMEZONE)

def local_now(timezone_name: str | None) -> datetime:
    return datetime.now(timezone.utc).astimezone(get_zoneinfo(timezone_name))

def to_local_datetime(value: datetime, timezone_name: str | None) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(get_zoneinfo(timezone_name))
