import os
import glob
import pandas as pd
from sqlalchemy import text
from src.utils.db_connector import PostgresConnector
from src.utils.config import Config
from src.utils.logger import logger

def load_landing_to_dw(target_schema: str = "staging", archive_processed: bool = False) -> dict:
    """
    Loads raw Parquet files from data/landing/ into Data Warehouse staging tables (Load Step in ELT).
    Compatible with both SQLAlchemy 1.4 and 2.0.
    """
    connector = PostgresConnector()
    engine = connector.get_engine()
    
    # Ensure target schema exists in Data Warehouse using engine.begin() for auto-commit
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {target_schema};"))

    landing_files = glob.glob(os.path.join(Config.LANDING_DIR, "*.parquet"))
    
    if not landing_files:
        logger.warning(f"No parquet files found in landing zone: {Config.LANDING_DIR}")
        return {}

    logger.info(f"Found {len(landing_files)} parquet files in landing zone. Starting Load step into schema '{target_schema}'...")
    loaded_summary = {}

    for file_path in landing_files:
        filename = os.path.basename(file_path)
        base_name = os.path.splitext(filename)[0]
        if "_" in base_name and base_name.rsplit("_", 2)[-1].isdigit():
            table_name = base_name.rsplit("_", 2)[0]
        else:
            table_name = base_name

        staging_table_name = f"stg_{table_name}"
        
        logger.info(f"Loading '{filename}' into '{target_schema}.{staging_table_name}'...")
        df = pd.read_parquet(file_path)
        
        # Load raw data into staging table in DW using active connection context
        with engine.begin() as conn:
            df.to_sql(
                name=staging_table_name,
                con=conn,
                schema=target_schema,
                if_exists="replace",
                index=False
            )
        
        loaded_summary[staging_table_name] = len(df)
        logger.info(f"Successfully loaded {len(df)} rows into '{target_schema}.{staging_table_name}'.")

        if archive_processed:
            archive_dir = os.path.join(Config.LANDING_DIR, "archive")
            os.makedirs(archive_dir, exist_ok=True)
            os.rename(file_path, os.path.join(archive_dir, filename))

    return loaded_summary

if __name__ == "__main__":
    load_landing_to_dw()
