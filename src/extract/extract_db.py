import os
import glob
import pandas as pd
from typing import List, Optional
from datetime import datetime
from sqlalchemy import text
from src.utils.db_connector import PostgresConnector
from src.utils.config import Config
from src.utils.logger import logger

def clear_landing_zone():
    """
    Cleans up existing parquet files in landing zone before running a new extraction
    to prevent duplicate files accumulation.
    """
    if os.path.exists(Config.LANDING_DIR):
        files = glob.glob(os.path.join(Config.LANDING_DIR, "*.parquet"))
        for f in files:
            try:
                os.remove(f)
                logger.info(f"Cleaned up old landing file: {f}")
            except Exception as e:
                logger.warning(f"Could not remove {f}: {e}")

def extract_table_to_parquet(
    table_name: str,
    query: Optional[str] = None,
    timestamp_suffix: bool = False,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> str:
    """
    Extracts raw data from PostgreSQL table and saves it directly to Landing Zone as Parquet (EL Step).
    Supports granular date-range filtering for backfilling historical partitions.
    """
    connector = PostgresConnector()
    engine = connector.get_engine()
    
    if query:
        sql_query = query
    elif table_name == "raw_orders" and (start_date or end_date):
        conditions = []
        if start_date:
            conditions.append(f"order_purchase_timestamp >= '{start_date}'")
        if end_date:
            conditions.append(f"order_purchase_timestamp <= '{end_date}'")
        where_clause = " AND ".join(conditions)
        sql_query = f'SELECT * FROM "{Config.DB_SCHEMA}"."raw_orders" WHERE {where_clause}'
        logger.info(f"Backfill mode active for table '{table_name}' with filter: {where_clause}")
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
    
    if timestamp_suffix:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{table_name}_{timestamp}.parquet"
    else:
        filename = f"{table_name}.parquet"

    file_path = os.path.join(Config.LANDING_DIR, filename)
    df.to_parquet(file_path, index=False)
    logger.info(f"Saved: {file_path}")
    
    return file_path

def extract_all_tables(
    table_list: Optional[List[str]] = None,
    clean_landing: bool = True,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[str]:
    """
    Extracts multiple tables from PostgreSQL in batch.
    Supports granular date-range backfill parameters.
    """
    if clean_landing:
        clear_landing_zone()

    if table_list is None:
        table_list = [
            "raw_customers",
            "raw_orders",
            "raw_order_items",
            "raw_payments",
            "raw_reviews",
            "raw_products"
        ]

    if start_date or end_date:
        logger.info(f"--- BACKFILL INGESTION: Range [{start_date or 'BEGIN'} to {end_date or 'NOW'}] ---")

    logger.info(f"Starting batch extraction for {len(table_list)} tables: {table_list}")
    extracted_files = []
    
    for table_name in table_list:
        try:
            file_path = extract_table_to_parquet(
                table_name,
                timestamp_suffix=False,
                start_date=start_date,
                end_date=end_date
            )
            extracted_files.append(file_path)
        except Exception as e:
            logger.error(f"Error extracting table '{table_name}': {e}")
            raise e
            
    logger.info(f"Batch extraction completed. {len(extracted_files)}/{len(table_list)} tables extracted successfully.")
    return extracted_files

if __name__ == "__main__":
    extract_all_tables()