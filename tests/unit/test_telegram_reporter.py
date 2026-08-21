from src.utils.telegram_reporter import _clean_error_summary, build_telegram_report

def test_clean_error_summary_concise():
    """Verify error summary extracts meaningful single-line message and sanitizes markdown."""
    raw_error = "RuntimeError: dbt run failed:\nSTDOUT:\nDatabase Error: Table raw_orders was not found in location asia-southeast1\n..."
    cleaned = _clean_error_summary(raw_error)
    assert "❌" in cleaned
    assert "was not found" in cleaned
    assert "_" not in cleaned
    assert "*" not in cleaned

def test_telegram_message_length_capping():
    """Verify telegram message is capped at 3500 chars (well under Telegram's 4096 limit)."""
    # Build report for success
    report = build_telegram_report("success")
    assert len(report) <= 3500
    assert "DATA PLATFORM | BATCH REPORT: SUCCESS" in report

    # Build report for failure
    report_fail = build_telegram_report("failure")
    assert len(report_fail) <= 3500
    assert "DATA PLATFORM | BATCH REPORT: FAILED" in report_fail
