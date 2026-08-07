import os
import glob
import pandas as pd
from typing import List, Optional
from datetime import datetime
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

def extract_table_to_parquet(table_name: str, query: Optional[str] = None, timestamp_suffix: bool = False) -> str:
    """
    Extracts raw data from PostgreSQL table and saves it directly to Landing Zone as Parquet (EL Step).
    If timestamp_suffix is False, overwrites table_name.parquet to avoid duplicate files.
    """
    connector = PostgresConnector()
    engine = connector.get_engine()
    
    sql_query = query if query else f'SELECT * FROM "{Config.DB_SCHEMA}"."{table_name}"'
    
    logger.info(f"Executing extraction for table '{table_name}'...")
    df = pd.read_sql(sql_query, con=engine)
    logger.info(f"Extracted {len(df)} rows from table '{table_name}'.")

    os.makedirs(Config.LANDING_DIR, exist_ok=True)
    
    if timestamp_suffix:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{table_name}_{timestamp}.parquet"
    else:
        filename = f"{table_name}.parquet"

    file_path = os.path.join(Config.LANDING_DIR, filename)
    
    # Save raw data without transformation to landing zone (overwriting deterministic file)
    df.to_parquet(file_path, index=False)
    logger.info(f"Saved: {file_path}")
    
    return file_path

def extract_all_tables(table_list: Optional[List[str]] = None, clean_landing: bool = True) -> List[str]:
    """
    Extracts multiple tables from PostgreSQL in batch.
    If clean_landing is True, clears old parquet files in landing zone first.
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

    logger.info(f"Starting batch extraction for {len(table_list)} tables: {table_list}")
    extracted_files = []
    
    for table_name in table_list:
        try:
            file_path = extract_table_to_parquet(table_name, timestamp_suffix=False)
            extracted_files.append(file_path)
        except Exception as e:
            logger.error(f"Error extracting table '{table_name}': {e}")
            
    logger.info(f"Batch extraction completed. {len(extracted_files)}/{len(table_list)} tables extracted successfully.")
    return extracted_files

if __name__ == "__main__":
    extract_all_tables()
