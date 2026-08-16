import sys
import os
import argparse
from typing import Optional, List

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from prefect import task, flow
from connectors._base.schemas import RunArgs, RunMode
from connectors.postgres_db.connector import PostgresConnector
from src.load.load_to_gcs import upload_landing_to_gcs
from src.load.load_to_bigquery import load_gcs_to_bigquery_staging
from src.transform.run_transform import run_in_warehouse_transformations
from src.utils.logger import logger

# Active Connectors Registry
AVAILABLE_CONNECTORS = {
    "postgres_db": PostgresConnector(),
    "postgres": PostgresConnector(),
}

@task(name="1. Connector Extract Step", retries=2, retry_delay_seconds=10)
def extract_connector_task(connector_name: str, args: RunArgs) -> List[str]:
    logger.info(f"\n--- STEP 1: EXTRACT (Connector: '{connector_name}') ---")
    if connector_name not in AVAILABLE_CONNECTORS:
        raise ValueError(f"Unknown connector '{connector_name}'. Available: {list(AVAILABLE_CONNECTORS.keys())}")
    
    connector = AVAILABLE_CONNECTORS[connector_name]
    extracted_files = connector.run(args)
    logger.info(f"Extract step finished for '{connector_name}'. {len(extracted_files)} files in landing zone.")
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
def transform_step_task(full_refresh: bool = False, select_models: Optional[str] = None):
    logger.info("\n--- STEP 3: TRANSFORM & TEST (dbt-bigquery -> Marts & Data Quality) ---")
    run_in_warehouse_transformations(full_refresh=full_refresh, select_models=select_models)
    logger.info("Transform & Test step finished. Data Marts validated successfully.")

@flow(name="Enterprise Data Platform ELT", log_prints=True)
def run_elt_pipeline(
    connector_name: str = "postgres_db",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    full_refresh: bool = False
):
    mode = RunMode.FULL_REFRESH if full_refresh else RunMode.INCREMENTAL
    run_args = RunArgs(
        start_date=start_date,
        end_date=end_date,
        mode=mode,
        clean_landing=True
    )

    logger.info("==================================================")
    logger.info(f"  ENTERPRISE DATA PLATFORM (Connector: {connector_name})")
    logger.info(f"  Mode: {mode.value.upper()} | Range: [{start_date or 'BEGIN'} -> {end_date or 'NOW'}]")
    logger.info("==================================================")

    extracted_files = extract_connector_task(connector_name, run_args)
    gcs_uris = load_gcs_step_task(wait_for=[extracted_files])
    loaded_tables = load_bigquery_step_task(wait_for=[gcs_uris])
    
    # Run dbt transformations & tests
    transform_step_task(full_refresh=full_refresh, wait_for=[loaded_tables])

    logger.info("\n==================================================")
    logger.info(f"  PIPELINE FOR '{connector_name}' COMPLETED SUCCESSFULLY! ")
    logger.info("==================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enterprise Data Platform Master Orchestrator")
    parser.add_argument("--connector", type=str, default="postgres_db", help="Target connector name (default: postgres_db)")
    parser.add_argument("--start-date", type=str, default=None, help="Start date for backfill (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default=None, help="End date for backfill (YYYY-MM-DD)")
    parser.add_argument("--full-refresh", action="store_true", help="Force full-refresh rebuild of incremental models")
    parser.add_argument("--serve", action="store_true", help="Register deployment and serve flow on Prefect Cloud")
    
    args = parser.parse_args()

    if args.serve:
        logger.info("Registering deployment and serving flow on Prefect Cloud...")
        run_elt_pipeline.serve(name="enterprise-deployment")
    else:
        run_elt_pipeline(
            connector_name=args.connector,
            start_date=args.start_date,
            end_date=args.end_date,
            full_refresh=args.full_refresh
        )