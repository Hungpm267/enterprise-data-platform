import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from connectors.postgres_db.extract import extract_single_table


@pytest.fixture
def fake_engine():
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = MagicMock()
    return engine


def test_extract_stamps_tenant_slug_column(fake_engine, tmp_path):
    source_df = pd.DataFrame({"customer_id": ["c1", "c2"], "customer_city": ["HCM", "HN"]})

    with patch("connectors.postgres_db.extract.pd.read_sql_query", return_value=source_df), \
         patch("connectors.postgres_db.extract.Config") as mock_config:
        mock_config.DB_SCHEMA = "public"
        mock_config.LANDING_DIR = str(tmp_path)

        path = extract_single_table(
            fake_engine, "raw_customers", tenant_slug="acme-coffee"
        )

    written = pd.read_parquet(path)
    assert "tenant_slug" in written.columns
    assert written["tenant_slug"].tolist() == ["acme-coffee", "acme-coffee"]


def test_extract_rejects_empty_tenant_slug(fake_engine, tmp_path):
    source_df = pd.DataFrame({"customer_id": ["c1"]})

    with patch("connectors.postgres_db.extract.pd.read_sql_query", return_value=source_df), \
         patch("connectors.postgres_db.extract.Config") as mock_config:
        mock_config.DB_SCHEMA = "public"
        mock_config.LANDING_DIR = str(tmp_path)

        with pytest.raises(ValueError, match="tenant_slug"):
            extract_single_table(fake_engine, "raw_customers", tenant_slug="")
