import sys
import os
import argparse
from typing import Optional, List
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from prefect import task, flow
from connectors._base.schemas import RunArgs, RunMode
from connectors.postgres_db.connector import PostgresConnector
from src.load.load_to_gcs import upload_landing_to_gcs
from src.load.load_to_bigquery import load_gcs_to_bigquery_staging
from src.transform.run_transform import run_in_warehouse_transformations
from src.utils.state_manager import StateManager
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
def load_bigquery_step_task(mode: RunMode = RunMode.INCREMENTAL, is_backfill: bool = False):
    logger.info(f"\n--- STEP 2B: LOAD BIGQUERY (Mode: {mode.value.upper()}, Backfill: {is_backfill}) ---")
    loaded_tables = load_gcs_to_bigquery_staging(mode=mode, is_backfill=is_backfill)
    logger.info(f"BigQuery Staging Load finished. Synchronized {len(loaded_tables)} staging tables.")
    return loaded_tables

@task(name="4. dbt Transform Step", retries=2, retry_delay_seconds=10)
def transform_step_task(
    full_refresh: bool = False,
    select_models: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    logger.info("\n--- STEP 3: TRANSFORM & TEST (dbt-bigquery -> Marts & Data Quality) ---")
    run_in_warehouse_transformations(
        full_refresh=full_refresh,
        select_models=select_models,
        start_date=start_date,
        end_date=end_date
    )
    logger.info("Transform & Test step finished. Data Marts validated successfully.")

@task(name="5. Commit Watermark State Step", retries=2, retry_delay_seconds=5)
def commit_watermark_step_task(
    connector_name: str,
    sync_timestamp: datetime,
    mode: str,
    full_refresh: bool = False
):
    state_mgr = StateManager()
    if full_refresh:
        state_mgr.reset_watermark(connector_name)
    else:
        state_mgr.commit_watermark(connector_name, sync_timestamp, mode=mode)

@flow(name="Enterprise Data Platform ELT", log_prints=True)
def run_elt_pipeline(
    connector_name: str = "postgres_db",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    full_refresh: bool = False
):
    mode = RunMode.FULL_REFRESH if full_refresh else RunMode.INCREMENTAL
    is_backfill = bool(start_date or end_date)
    sync_time = datetime.utcnow()

    # Automated Watermark State Lookup
    state_mgr = StateManager()
    if mode == RunMode.INCREMENTAL and not is_backfill:
        watermark = state_mgr.get_watermark(connector_name)
        if watermark:
            # Lookback 1 hour safety offset to prevent boundary race conditions
            safe_watermark = watermark - timedelta(hours=1)
            start_date = safe_watermark.strftime("%Y-%m-%d %H:%M:%S")
            end_date = sync_time.strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"Automated Watermark Tracking Active: [{start_date} -> {end_date}]")
        else:
            logger.info("Initial sync baseline: No watermark found, extracting baseline snapshot.")

    run_args = RunArgs(
        start_date=start_date,
        end_date=end_date,
        mode=mode,
        clean_landing=True
    )

    logger.info("==================================================")
    logger.info(f"  ENTERPRISE DATA PLATFORM (Connector: {connector_name})")
    logger.info(f"  Mode: {mode.value.upper()} | Backfill: {is_backfill}")
    logger.info(f"  Effective Range: [{start_date or 'BEGIN'} -> {end_date or 'NOW'}]")
    logger.info("==================================================")

    extracted_files = extract_connector_task(connector_name, run_args)
    gcs_uris = load_gcs_step_task(wait_for=[extracted_files])
    loaded_tables = load_bigquery_step_task(mode=mode, is_backfill=is_backfill, wait_for=[gcs_uris])
    
    # Run dbt transformations & tests
    transformed = transform_step_task(
        full_refresh=full_refresh,
        start_date=start_date if is_backfill else None,
        end_date=end_date if is_backfill else None,
        wait_for=[loaded_tables]
    )

    # Persist Watermark State only on 100% pipeline success
    commit_watermark_step_task(
        connector_name=connector_name,
        sync_timestamp=sync_time,
        mode=mode.value,
        full_refresh=full_refresh,
        wait_for=[transformed]
    )

    logger.info("\n==================================================")
    logger.info(f"  PIPELINE FOR '{connector_name}' COMPLETED SUCCESSFULLY! ")
    logger.info("==================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enterprise Data Platform Master Orchestrator")
    parser.add_argument("--connector", type=str, default="postgres_db", help="Target connector name (default: postgres_db)")
    parser.add_argument("--start-date", type=str, default=None, help="Start date for backfill (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("--end-date", type=str, default=None, help="End date for backfill (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)")
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