import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from prefect import task, flow
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

@task(name="Extract Step", retries=2, retry_delay_seconds=10)
def extract_step_task():
    logger.info("\n--- STEP 1: EXTRACT (E) ---")
    extracted_files = extract_all_tables(TABLES_TO_EXTRACT)
    logger.info(f"Extract step finished. {len(extracted_files)} parquet files written to landing zone.")
    return extracted_files

@task(name="Load Step", retries=2, retry_delay_seconds=10)
def load_step_task():
    logger.info("\n--- STEP 2: LOAD (L) ---")
    loaded_tables = load_landing_to_dw(target_schema="staging")
    logger.info(f"Load step finished. Loaded {len(loaded_tables)} staging tables in Data Warehouse.")
    return loaded_tables

@task(name="Transform Step", retries=2, retry_delay_seconds=10)
def transform_step_task():
    logger.info("\n--- STEP 3: TRANSFORM (T) ---")
    run_in_warehouse_transformations()
    logger.info("Transform step finished. Data Marts (Dimension & Fact tables) built inside Data Warehouse.")

@flow(name="E-Commerce ELT Pipeline", log_prints=True)
def run_elt_pipeline():
    logger.info("==================================================")
    logger.info("  STARTING FULL END-TO-END PREFECT ELT PIPELINE   ")
    logger.info("==================================================")

    extracted_files = extract_step_task()
    loaded_tables = load_step_task(wait_for=[extracted_files])
    transform_step_task(wait_for=[loaded_tables])

    logger.info("\n==================================================")
    logger.info("  PREFECT ELT PIPELINE COMPLETED SUCCESSFULLY!    ")
    logger.info("==================================================")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--serve":
        logger.info("Registering deployment and serving flow on Prefect Cloud...")
        run_elt_pipeline.serve(name="ecommerce-deployment")
    else:
        run_elt_pipeline()
