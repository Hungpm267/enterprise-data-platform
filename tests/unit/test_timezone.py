from datetime import datetime, timezone, timedelta
from src.utils.timezone import VIETNAM_TZ, get_vietnam_now, get_vietnam_now_str

def test_vietnam_timezone_offset():
    """Verify Vietnam timezone is exactly UTC+7."""
    assert VIETNAM_TZ.utcoffset(None).total_seconds() == 7 * 3600

def test_get_vietnam_now_is_naive_vietnam_wall_clock():
    """Verify get_vietnam_now returns a naive datetime 7h ahead of UTC."""
    now_vn = get_vietnam_now()
    assert now_vn.tzinfo is None
    utc_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    assert abs((now_vn - utc_naive) - timedelta(hours=7)) < timedelta(seconds=5)

def test_get_vietnam_now_str_format():
    """Verify string output adheres to YYYY-MM-DD HH:MM:SS format."""
    now_str = get_vietnam_now_str()
    # Should parse cleanly with strptime
    parsed = datetime.strptime(now_str, "%Y-%m-%d %H:%M:%S")
    assert isinstance(parsed, datetime)
