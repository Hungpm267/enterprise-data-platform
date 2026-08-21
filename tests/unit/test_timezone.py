from datetime import datetime, timezone
from src.utils.timezone import VIETNAM_TZ, get_vietnam_now, get_vietnam_now_aware, get_vietnam_now_str, to_vietnam_time

def test_vietnam_timezone_offset():
    """Verify Vietnam timezone is exactly UTC+7."""
    now_vn = get_vietnam_now_aware()
    assert now_vn.tzinfo is not None
    # 7 hours offset = 25200 seconds
    assert now_vn.utcoffset().total_seconds() == 7 * 3600

def test_get_vietnam_now_str_format():
    """Verify string output adheres to YYYY-MM-DD HH:MM:SS format."""
    now_str = get_vietnam_now_str()
    # Should parse cleanly with strptime
    parsed = datetime.strptime(now_str, "%Y-%m-%d %H:%M:%S")
    assert isinstance(parsed, datetime)

def test_to_vietnam_time_conversion():
    """Verify UTC datetime converts accurately to Vietnam UTC+7 time."""
    utc_dt = datetime(2026, 8, 21, 3, 0, 0, tzinfo=timezone.utc)
    vn_dt = to_vietnam_time(utc_dt)
    assert vn_dt.hour == 10
    assert vn_dt.day == 21
