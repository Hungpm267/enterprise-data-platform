import os
import sys
import json
import shutil
import subprocess
from typing import Optional
from google.cloud import bigquery
from src.utils.gcp_client import get_bigquery_client
from src.utils.config import Config
from src.utils.logger import logger

def get_dbt_binary():
    bin_path = shutil.which("dbt")
    if bin_path:
        return bin_path

    scripts_dbt = os.path.join(os.path.dirname(sys.executable), "Scripts", "dbt.exe")
    if os.path.exists(scripts_dbt):
        return scripts_dbt

    unix_dbt = os.path.join(os.path.dirname(sys.executable), "dbt")
    if os.path.exists(unix_dbt):
        return unix_dbt

    return "dbt"

def run_in_warehouse_transformations(
    full_refresh: bool = False,
    connector_name: Optional[str] = None,
    select_models: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Runs in-warehouse SQL transformations using dbt-bigquery against BigQuery DW,
    followed by automated Data Quality testing with dbt test.
    Supports scoping dbt executions per connector via dbt tags.
    """
    client = get_bigquery_client()
    project_id = Config.GCP_PROJECT_ID
    marts_dataset_id = Config.GCP_MARTS_DATASET

    dataset_ref = bigquery.DatasetReference(project_id, marts_dataset_id)
    try:
        client.get_dataset(dataset_ref)
        logger.info(f"BigQuery dataset '{marts_dataset_id}' found.")
    except Exception:
        logger.info(f"Creating BigQuery dataset '{marts_dataset_id}' in location 'asia-southeast1'...")
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "asia-southeast1"
        client.create_dataset(dataset)
        logger.info(f"Created BigQuery dataset '{marts_dataset_id}' successfully.")

    # Ensure gcp_key.json exists for dbt service-account keyfile method
    gcp_sa_key_json = os.getenv("GCP_SA_KEY")
    key_file_path = Config.GCP_KEY_FILE
    if gcp_sa_key_json and not os.path.exists(key_file_path):
        logger.info(f"Writing temporary '{key_file_path}' from GCP_SA_KEY secret for dbt authentication...")
        with open(key_file_path, "w", encoding="utf-8") as f:
            f.write(gcp_sa_key_json)

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dbt_dir = os.path.join(base_dir, "dbt")

    env = os.environ.copy()
    env["GCP_PROJECT_ID"] = Config.GCP_PROJECT_ID
    env["GCP_STAGING_DATASET"] = Config.GCP_STAGING_DATASET
    env["GCP_KEY_FILE"] = key_file_path

    dbt_bin = get_dbt_binary()
    logger.info(f"Using dbt binary at: '{dbt_bin}'")
    logger.info(f"dbt project directory: '{dbt_dir}'")

    # Determine selector
    target_selector = select_models
    if not target_selector and connector_name:
        if "crypto" in connector_name:
            target_selector = "tag:crypto"
        elif "postgres" in connector_name:
            target_selector = "tag:postgres"

    # Step 1: dbt run (compile & execute models)
    run_cmd = [dbt_bin, "run", "--project-dir", dbt_dir, "--profiles-dir", dbt_dir]
    if full_refresh:
        logger.info("Executing dbt-bigquery transformations with FULL-REFRESH...")
        run_cmd.append("--full-refresh")
    else:
        logger.info("Executing dbt-bigquery incremental merge transformations (dbt run)...")

    if target_selector:
        logger.info(f"Targeting dbt models: --select {target_selector}")
        run_cmd.extend(["--select", target_selector])

    # Pass date vars if backfill
    dbt_vars = {}
    if start_date:
        dbt_vars["start_date"] = start_date
    if end_date:
        dbt_vars["end_date"] = end_date
    if dbt_vars:
        vars_json = json.dumps(dbt_vars)
        logger.info(f"Passing dbt execution vars: --vars '{vars_json}'")
        run_cmd.extend(["--vars", vars_json])

    run_result = subprocess.run(run_cmd, env=env, capture_output=True, text=True, shell=(os.name == 'nt'))

    if run_result.returncode != 0:
        full_run_output = f"STDOUT:\n{run_result.stdout}\nSTDERR:\n{run_result.stderr}"
        logger.error(f"dbt run failed:\n{full_run_output}")
        raise RuntimeError(f"dbt run failed:\n{full_run_output}")

    logger.info("dbt-bigquery transformations completed successfully!\n" + run_result.stdout)

    # Step 2: dbt test (automated data quality verification)
    logger.info("Executing dbt Data Quality Tests (dbt test)...")
    test_cmd = [dbt_bin, "test", "--project-dir", dbt_dir, "--profiles-dir", dbt_dir]
    if target_selector:
        test_cmd.extend(["--select", target_selector])

    test_result = subprocess.run(test_cmd, env=env, capture_output=True, text=True, shell=(os.name == 'nt'))

    if test_result.returncode != 0:
        full_test_output = f"STDOUT:\n{test_result.stdout}\nSTDERR:\n{test_result.stderr}"
        logger.error(f"dbt test FAILED:\n{full_test_output}")
        raise RuntimeError(f"dbt Data Quality Tests failed:\n{full_test_output}")

    logger.info("All dbt Data Quality Tests passed (100% PASS)!\n" + test_result.stdout)

if __name__ == "__main__":
    is_full = "--full-refresh" in sys.argv
    run_in_warehouse_transformations(full_refresh=is_full)