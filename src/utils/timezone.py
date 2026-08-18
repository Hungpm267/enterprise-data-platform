from datetime import datetime, timezone, timedelta
from typing import Optional

# Vietnam Standard Time (Indochina Time - UTC+7 / Asia/Ho_Chi_Minh)
VIETNAM_TZ = timezone(timedelta(hours=7))

def get_vietnam_now() -> datetime:
    """
    Returns current datetime in Vietnam Timezone (UTC+7) as a naive datetime 
    (or aware if needed) for standard DB/BigQuery/GCS timestamp consistency.
    """
    return datetime.now(VIETNAM_TZ).replace(tzinfo=None)

def get_vietnam_now_aware() -> datetime:
    """
    Returns timezone-aware datetime in Vietnam Timezone (UTC+7).
    """
    return datetime.now(VIETNAM_TZ)

def get_vietnam_now_str(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Returns formatted string of current Vietnam Time (UTC+7).
    """
    return datetime.now(VIETNAM_TZ).strftime(fmt)

def to_vietnam_time(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Converts a UTC or naive datetime to Vietnam Time (UTC+7).
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Assume input was UTC if naive
        dt_utc = dt.replace(tzinfo=timezone.utc)
    else:
        dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.astimezone(VIETNAM_TZ).replace(tzinfo=None)
