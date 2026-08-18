import os
import glob
import pandas as pd
from typing import List, Optional, Dict, Any
from sqlalchemy import text
from src.utils.db_connector import PostgresConnector
from src.utils.config import Config
from src.utils.logger import logger
from connectors._base.schemas import RunArgs, RunMode

TABLES_LIST = [
    "raw_customers",
    "raw_orders",
    "raw_order_items",
    "raw_payments",
    "raw_reviews",
    "raw_products"
]

def clear_landing_zone():
    pg_landing = os.path.join(Config.LANDING_DIR, "postgres_db")
    if os.path.exists(pg_landing):
        files = glob.glob(os.path.join(pg_landing, "*.parquet"))
        for f in files:
            try:
                os.remove(f)
                logger.info(f"Cleaned up old landing file: {f}")
            except Exception as e:
                logger.warning(f"Could not remove {f}: {e}")

def extract_single_table(
    table_name: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> str:
    """
    Extracts a single table from PostgreSQL using secure parameterized queries.
    Uses pd.read_sql_query to preserve exact schema datatypes even on empty delta batches.
    Saves to namespaced landing path: data/landing/postgres_db/{table_name}.parquet
    """
    connector = PostgresConnector()
    engine = connector.get_engine()
    
    params: Dict[str, Any] = {}
    
    if table_name == "raw_orders" and (start_date or end_date):
        conditions = []
        if start_date:
            conditions.append("order_purchase_timestamp >= :start_date")
            params["start_date"] = start_date
        if end_date:
            conditions.append("order_purchase_timestamp <= :end_date")
            params["end_date"] = end_date
        where_clause = " AND ".join(conditions)
        sql_query = f'SELECT * FROM "{Config.DB_SCHEMA}"."raw_orders" WHERE {where_clause}'
        logger.info(f"Parameterized filter active for '{table_name}': {where_clause} with params={params}")
    else:
        sql_query = f'SELECT * FROM "{Config.DB_SCHEMA}"."{table_name}"'
    
    logger.info(f"Executing secure parameterized extraction for table '{table_name}'...")
    with engine.connect() as conn:
        df = pd.read_sql_query(text(sql_query), conn, params=params)

    # Ensure timestamp columns are properly typed
    if "order_purchase_timestamp" in df.columns:
        df["order_purchase_timestamp"] = pd.to_datetime(df["order_purchase_timestamp"])
    if "order_estimated_delivery_date" in df.columns:
        df["order_estimated_delivery_date"] = pd.to_datetime(df["order_estimated_delivery_date"])

    logger.info(f"Extracted {len(df)} rows from table '{table_name}'.")

    target_dir = os.path.join(Config.LANDING_DIR, "postgres_db")
    os.makedirs(target_dir, exist_ok=True)
    filename = f"{table_name}.parquet"
    file_path = os.path.join(target_dir, filename)
    df.to_parquet(file_path, index=False)
    logger.info(f"Saved: {file_path}")
    
    return file_path

def extract_postgres_tables(args: RunArgs) -> List[str]:
    if args.clean_landing:
        clear_landing_zone()

    tables = args.tables if args.tables else TABLES_LIST
    if args.start_date or args.end_date:
        logger.info(f"--- POSTGRES CONNECTOR: Filter Range [{args.start_date or 'BEGIN'} -> {args.end_date or 'NOW'}] ---")

    logger.info(f"Starting extraction for {len(tables)} tables: {tables}")
    extracted_files = []
    
    for table_name in tables:
        try:
            file_path = extract_single_table(
                table_name,
                start_date=args.start_date,
                end_date=args.end_date
            )
            extracted_files.append(file_path)
        except Exception as e:
            logger.error(f"Error extracting table '{table_name}': {e}")
            raise e
            
    logger.info(f"Postgres extraction completed. {len(extracted_files)}/{len(tables)} tables extracted successfully.")
    return extracted_files