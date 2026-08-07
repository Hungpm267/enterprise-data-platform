import os
import glob
from sqlalchemy import text
from src.utils.db_connector import PostgresConnector
from src.utils.logger import logger

def run_in_warehouse_transformations(sql_dir: str = "src/transform/sql"):
    """
    Runs in-warehouse SQL transformation scripts to build Data Marts (Transform Step in ELT).
    Compatible with both SQLAlchemy 1.4 and 2.0.
    """
    connector = PostgresConnector()
    engine = connector.get_engine()
    
    sql_files = glob.glob(os.path.join(sql_dir, "*.sql"))
    sql_files.sort()

    logger.info(f"Starting In-Warehouse Transformations (T Step)... Found {len(sql_files)} SQL models.")

    with engine.begin() as conn:
        for file_path in sql_files:
            model_name = os.path.basename(file_path)
            
            with open(file_path, "r", encoding="utf-8") as f:
                sql_script = f.read()
                
            if not sql_script.strip():
                logger.info(f"Skipping empty transform model: '{model_name}'.")
                continue

            logger.info(f"Executing transform model: '{model_name}'...")
            conn.execute(text(sql_script))
            logger.info(f"Model '{model_name}' executed successfully.")

    logger.info("All In-Warehouse Transformations completed successfully!")

if __name__ == "__main__":
    run_in_warehouse_transformations()
