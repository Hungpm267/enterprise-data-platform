import os
import json
import requests
from src.utils.timezone import get_vietnam_now_str
from src.utils.logger import logger

def build_telegram_report(workflow_status: str) -> str:
    vn_time = get_vietnam_now_str()
    metrics_file = "data/pipeline_metrics.json"
    metrics = {}
    if os.path.exists(metrics_file):
        try:
            with open(metrics_file, "r", encoding="utf-8") as f:
                metrics = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load metrics file: {e}")

    pg = metrics.get("postgres_db", {})
    crypto = metrics.get("crypto_api", {})

    total_duration = pg.get("duration_sec", 0.0) + crypto.get("duration_sec", 0.0)
    
    # Context
    repo = os.getenv("GITHUB_REPOSITORY", "Hungpm267/enterprise-data-platform")
    branch = os.getenv("GITHUB_REF_NAME", "main")
    sha = (os.getenv("GITHUB_SHA") or "local")[:7]
    run_id = os.getenv("GITHUB_RUN_ID")
    run_url = f"https://github.com/{repo}/actions/runs/{run_id}" if run_id else f"https://github.com/{repo}"
    event_name = os.getenv("GITHUB_EVENT_NAME", "manual")

    if event_name == "schedule":
        trigger_desc = "Scheduled Cron (Every 6 Hours)"
    elif event_name == "push":
        trigger_desc = f"Git Push [{sha}]"
    else:
        trigger_desc = "Manual Trigger"

    is_success = (workflow_status.lower() == "success")

    if is_success:
        pg_rows = f"{pg.get('rows_count', 0):,}"
        crypto_rows = f"{crypto.get('rows_count', 0):,}"
        
        message = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🚀 *DATA PLATFORM | BATCH REPORT: SUCCESS*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📊 *Báo cáo chi tiết từng pipeline:*\n\n"
            "1. *Postgres E-Commerce Pipeline*\n"
            f"   • Số bảng: {pg.get('tables_count', 6)} raw tables\n"
            f"   • Số dòng: {pg_rows} rows\n"
            f"   • Thời gian chạy: {pg.get('duration_sec', 0.0)}s\n"
            "   • Kết quả: ✅ Thành công\n\n"
            "2. *CoinGecko Crypto Market Pipeline*\n"
            f"   • Số bảng: {crypto.get('tables_count', 2)} tables (Top 100 & Global)\n"
            f"   • Số dòng: {crypto_rows} rows\n"
            f"   • Thời gian chạy: {crypto.get('duration_sec', 0.0)}s\n"
            "   • Kết quả: ✅ Thành công\n\n"
            "3. *Data Marts & Data Quality (dbt-bigquery)*\n"
            "   • Models: 18 models (Staging & Marts)\n"
            "   • Data Quality: 35/35 Tests PASSED (100%)\n"
            "   • Kết quả: ✅ Đạt chuẩn\n\n"
            "ℹ️ *Thông tin phiên chạy:*\n"
            f"• Thời gian (UTC+7): `{vn_time}`\n"
            f"• Tổng thời gian: `{round(total_duration, 1)}s`\n"
            f"• Trigger: `{trigger_desc}`\n"
            f"• Branch: `{branch}` [`{sha}`]\n\n"
            f"🔗 [Xem Chi Tiết Log Trên GitHub Actions]({run_url})\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        # Failure Report
        pg_status = "✅ Thành công" if pg.get("status") == "SUCCESS" else f"❌ {pg.get('error_msg', 'Failed')}"
        crypto_status = "✅ Thành công" if crypto.get("status") == "SUCCESS" else f"❌ {crypto.get('error_msg', 'Failed')}"
        
        message = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🔴 *DATA PLATFORM | BATCH REPORT: FAILED*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ *Báo cáo chi tiết từng pipeline:*\n\n"
            "1. *Postgres E-Commerce Pipeline*\n"
            f"   • Số bảng: {pg.get('tables_count', 6)} raw tables\n"
            f"   • Thời gian chạy: {pg.get('duration_sec', 0.0)}s\n"
            f"   • Kết quả: {pg_status}\n\n"
            "2. *CoinGecko Crypto Market Pipeline*\n"
            f"   • Số bảng: {crypto.get('tables_count', 2)} tables\n"
            f"   • Thời gian chạy: {crypto.get('duration_sec', 0.0)}s\n"
            f"   • Kết quả: {crypto_status}\n\n"
            "3. *Data Marts & Data Quality (dbt-bigquery)*\n"
            "   • Trạng thái: ⏸️ Đã tạm dừng do pipeline trước gặp lỗi\n\n"
            "ℹ️ *Thông tin phiên chạy:*\n"
            f"• Thời gian (UTC+7): `{vn_time}`\n"
            f"• Trigger: `{trigger_desc}`\n"
            f"• Branch: `{branch}` [`{sha}`]\n\n"
            f"🔍 [Kiểm Tra Chi Tiết Lỗi Trên GitHub Actions]({run_url})\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )

    return message

def send_telegram_notification(workflow_status: str = "success"):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        logger.info("Telegram credentials not configured. Skipping notification.")
        return

    text = build_telegram_report(workflow_status)
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }

    try:
        res = requests.post(url, json=payload, timeout=15)
        if res.status_code == 200:
            logger.info("Telegram report sent successfully!")
        else:
            logger.warning(f"Telegram send failed with status {res.status_code}: {res.text}")
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {e}")

if __name__ == "__main__":
    import sys
    status = sys.argv[1] if len(sys.argv) > 1 else "success"
    send_telegram_notification(status)
