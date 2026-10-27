from datetime import datetime, timezone, timedelta

# Vietnam Standard Time (Indochina Time - UTC+7 / Asia/Ho_Chi_Minh)
VIETNAM_TZ = timezone(timedelta(hours=7))

def get_vietnam_now() -> datetime:
    """
    Returns current datetime in Vietnam Timezone (UTC+7) as a naive datetime 
    (or aware if needed) for standard DB/BigQuery/GCS timestamp consistency.
    """
    return datetime.now(VIETNAM_TZ).replace(tzinfo=None)

def get_vietnam_now_str(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Returns formatted string of current Vietnam Time (UTC+7).
    """
    return datetime.now(VIETNAM_TZ).strftime(fmt)
