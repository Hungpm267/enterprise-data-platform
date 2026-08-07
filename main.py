import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.extract.extract_db import extract_all_tables
from src.load.load_to_dw import load_landing_to_dw
from src.transform.run_transform import run_in_warehouse_transformations
from src.utils.logger import logger

TABLES_TO_EXTRACT = [
    "raw_customers",
    "raw_orders",
    "raw_order_items",
    "raw_payments",
    "raw_reviews",
    "raw_products"
]

def run_elt_pipeline():
    logger.info("==================================================")
    logger.info("  STARTING FULL END-TO-END ELT PIPELINE           ")
    logger.info("==================================================")

    # STEP 1: EXTRACT (E)
    logger.info("\n--- STEP 1: EXTRACT (E) ---")
    extracted_files = extract_all_tables(TABLES_TO_EXTRACT)
    logger.info(f"Extract step finished. {len(extracted_files)} parquet files written to landing zone.")

    # STEP 2: LOAD (L)
    logger.info("\n--- STEP 2: LOAD (L) ---")
    loaded_tables = load_landing_to_dw(target_schema="staging")
    logger.info(f"Load step finished. Loaded {len(loaded_tables)} staging tables in Data Warehouse.")

    # STEP 3: TRANSFORM (T)
    logger.info("\n--- STEP 3: TRANSFORM (T) ---")
    run_in_warehouse_transformations()
    logger.info("Transform step finished. Data Marts (Dimension & Fact tables) built inside Data Warehouse.")

    logger.info("\n==================================================")
    logger.info("  ELT PIPELINE COMPLETED SUCCESSFULLY!            ")
    logger.info("==================================================")

if __name__ == "__main__":
    run_elt_pipeline()
