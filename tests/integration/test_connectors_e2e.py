import os
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from connectors._base.schemas import RunArgs, RunMode
from connectors.postgres_db.extract import extract_single_table

def test_postgres_extract_single_table_schema(tmp_path, monkeypatch):
    """
    Integration Test: Tests that extract_single_table queries the database engine,
    preserves timestamp datatypes, and saves a valid Parquet file.
    """
    # Point landing dir to tmp_path
    monkeypatch.setattr("src.utils.config.Config.LANDING_DIR", str(tmp_path))
    
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    
    # Mock return dataframe with sample order data
    mock_df = pd.DataFrame({
        "order_id": ["ORD001", "ORD002"],
        "customer_id": ["CUST01", "CUST02"],
        "order_status": ["delivered", "shipped"],
        "order_purchase_timestamp": ["2026-08-21 08:00:00", "2026-08-21 09:00:00"],
        "order_estimated_delivery_date": ["2026-08-25 00:00:00", "2026-08-26 00:00:00"]
    })
    
    with patch("pandas.read_sql_query", return_value=mock_df):
        out_path = extract_single_table(mock_engine, "raw_orders")
        
        assert os.path.exists(out_path)
        assert out_path.endswith(".parquet")
        
        # Read back parquet and verify schema integrity
        read_df = pd.read_parquet(out_path)
        assert len(read_df) == 2
        assert "order_id" in read_df.columns
        assert pd.api.types.is_datetime64_any_dtype(read_df["order_purchase_timestamp"])
