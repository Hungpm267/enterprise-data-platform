import os
import subprocess
from google.cloud import bigquery
from src.utils.gcp_client import get_bigquery_client
from src.utils.config import Config
from src.utils.logger import logger

def run_in_warehouse_transformations():
    """
    Runs in-warehouse SQL transformations using dbt-bigquery against BigQuery DW.
    Auto-creates the BigQuery 'marts' dataset if missing.
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

    dbt_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dbt")
    logger.info("Executing dbt-bigquery transformations...")

    gcp_sa_key_json = os.getenv("GCP_SA_KEY")
    if not gcp_sa_key_json and os.path.exists(Config.GCP_KEY_FILE):
        with open(Config.GCP_KEY_FILE, "r", encoding="utf-8") as f:
            gcp_sa_key_json = f.read()

    env = os.environ.copy()
    if gcp_sa_key_json:
        env["GCP_SA_KEY_JSON"] = gcp_sa_key_json
    env["GCP_PROJECT_ID"] = Config.GCP_PROJECT_ID
    env["GCP_STAGING_DATASET"] = Config.GCP_STAGING_DATASET

    cmd = ["dbt", "run", "--project-dir", dbt_dir, "--profiles-dir", dbt_dir]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error(f"dbt run failed: {result.stderr or result.stdout}")
        raise RuntimeError(f"dbt transformation failed: {result.stderr or result.stdout}")

    logger.info("dbt-bigquery transformations executed successfully!\n" + result.stdout)

if __name__ == "__main__":
    run_in_warehouse_transformations()
