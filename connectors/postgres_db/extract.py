import os
import glob
import pandas as pd
from typing import List, Optional
from datetime import datetime
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
    if os.path.exists(Config.LANDING_DIR):
        files = glob.glob(os.path.join(Config.LANDING_DIR, "*.parquet"))
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
    connector = PostgresConnector()
    engine = connector.get_engine()
    
    if table_name == "raw_orders" and (start_date or end_date):
        conditions = []
        if start_date:
            conditions.append(f"order_purchase_timestamp >= '{start_date}'")
        if end_date:
            conditions.append(f"order_purchase_timestamp <= '{end_date}'")
        where_clause = " AND ".join(conditions)
        sql_query = f'SELECT * FROM "{Config.DB_SCHEMA}"."raw_orders" WHERE {where_clause}'
        logger.info(f"Backfill filter active for '{table_name}': {where_clause}")
    else:
        sql_query = f'SELECT * FROM "{Config.DB_SCHEMA}"."{table_name}"'
    
    logger.info(f"Executing extraction for table '{table_name}'...")
    with engine.connect() as conn:
        result = conn.execute(text(sql_query))
        rows = result.fetchall()
        cols = result.keys()
        df = pd.DataFrame(rows, columns=cols)

    logger.info(f"Extracted {len(df)} rows from table '{table_name}'.")

    os.makedirs(Config.LANDING_DIR, exist_ok=True)
    filename = f"{table_name}.parquet"
    file_path = os.path.join(Config.LANDING_DIR, filename)
    df.to_parquet(file_path, index=False)
    logger.info(f"Saved: {file_path}")
    
    return file_path

def extract_postgres_tables(args: RunArgs) -> List[str]:
    if args.clean_landing:
        clear_landing_zone()

    tables = args.tables if args.tables else TABLES_LIST
    if args.start_date or args.end_date:
        logger.info(f"--- POSTGRES CONNECTOR: Backfill Range [{args.start_date or 'BEGIN'} -> {args.end_date or 'NOW'}] ---")

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