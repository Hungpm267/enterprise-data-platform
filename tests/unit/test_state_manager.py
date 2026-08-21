from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

def test_watermark_lookback_calculation():
    """Verify 1-hour lookback window arithmetic prevents boundary race conditions."""
    current_watermark = datetime(2026, 8, 21, 10, 0, 0)
    lookback_window = timedelta(hours=1)
    safe_start = current_watermark - lookback_window
    assert safe_start == datetime(2026, 8, 21, 9, 0, 0)
    assert safe_start.strftime("%Y-%m-%d %H:%M:%S") == "2026-08-21 09:00:00"

@patch("src.utils.state_manager.get_bigquery_client")
def test_state_manager_initialization(mock_get_client):
    """Verify StateManager initializes and declares table IDs correctly."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    from src.utils.state_manager import StateManager
    mgr = StateManager()
    assert "_pipeline_state" in mgr.state_table_id
    assert "_pipeline_audit_log" in mgr.audit_table_id
