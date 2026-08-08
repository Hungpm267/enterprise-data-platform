import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from prefect import task, flow
from src.extract.extract_db import extract_all_tables
from src.load.load_to_gcs import upload_landing_to_gcs
from src.load.load_to_bigquery import load_gcs_to_bigquery_staging
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

@task(name="1. Extract Step", retries=2, retry_delay_seconds=10)
def extract_step_task():
    logger.info("\n--- STEP 1: EXTRACT (Postgres -> Parquet) ---")
    extracted_files = extract_all_tables(TABLES_TO_EXTRACT)
    logger.info(f"Extract step finished. {len(extracted_files)} parquet files written to landing zone.")
    return extracted_files

@task(name="2. Load GCS Step", retries=2, retry_delay_seconds=10)
def load_gcs_step_task():
    logger.info("\n--- STEP 2A: LOAD GCS (Parquet -> GCS Data Lake) ---")
    gcs_uris = upload_landing_to_gcs()
    logger.info(f"GCS Load finished. {len(gcs_uris)} Parquet files uploaded to GCS Bucket.")
    return gcs_uris

@task(name="3. Load BigQuery Step", retries=2, retry_delay_seconds=10)
def load_bigquery_step_task():
    logger.info("\n--- STEP 2B: LOAD BIGQUERY (GCS -> BigQuery Staging) ---")
    loaded_tables = load_gcs_to_bigquery_staging()
    logger.info(f"BigQuery Staging Load finished. Loaded {len(loaded_tables)} staging tables.")
    return loaded_tables

@task(name="4. dbt Transform Step", retries=2, retry_delay_seconds=10)
def transform_step_task():
    logger.info("\n--- STEP 3: TRANSFORM (dbt-bigquery -> BigQuery Marts) ---")
    run_in_warehouse_transformations()
    logger.info("Transform step finished. Data Marts built in BigQuery.")

@flow(name="E-Commerce ELT Pipeline", log_prints=True)
def run_elt_pipeline():
    logger.info("==================================================")
    logger.info("  STARTING FULL GCP MODERN DATA STACK ELT PIPELINE")
    logger.info("==================================================")

    extracted_files = extract_step_task()
    gcs_uris = load_gcs_step_task(wait_for=[extracted_files])
    loaded_tables = load_bigquery_step_task(wait_for=[gcs_uris])
    transform_step_task(wait_for=[loaded_tables])

    logger.info("\n==================================================")
    logger.info("  GCP ELT PIPELINE COMPLETED SUCCESSFULLY!        ")
    logger.info("==================================================")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--serve":
        logger.info("Registering deployment and serving flow on Prefect Cloud...")
        run_elt_pipeline.serve(name="ecommerce-deployment")
    else:
        run_elt_pipeline()
