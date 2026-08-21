import os
import sys
import pytest
from unittest.mock import MagicMock

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

@pytest.fixture(autouse=True)
def set_test_env_vars(monkeypatch):
    """Sets standard mock environment variables for unit tests."""
    monkeypatch.setenv("DB_HOST", "mock-postgres-host")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "mock-db")
    monkeypatch.setenv("DB_USER", "mock-user")
    monkeypatch.setenv("DB_PASSWORD", "mock-pass")
    monkeypatch.setenv("DB_SCHEMA", "public")
    monkeypatch.setenv("GCP_PROJECT_ID", "data-engineering-504901")
    monkeypatch.setenv("GCP_GCS_BUCKET", "ecommerce-data-lake-504901")
    monkeypatch.setenv("GCP_STAGING_DATASET", "staging")
    monkeypatch.setenv("GCP_MARTS_DATASET", "marts")
    monkeypatch.setenv("COINGECKO_API_KEY", "CG-mock-api-key")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "mock-bot-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-100mockchatid")
