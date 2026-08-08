from google.cloud import bigquery
from src.utils.gcp_client import get_bigquery_client
from src.utils.config import Config
from src.utils.logger import logger

TABLE_MAPPING = {
    "raw_customers.parquet": "stg_raw_customers",
    "raw_orders.parquet": "stg_raw_orders",
    "raw_order_items.parquet": "stg_raw_order_items",
    "raw_payments.parquet": "stg_raw_payments",
    "raw_products.parquet": "stg_raw_products",
    "raw_reviews.parquet": "stg_raw_reviews",
}

def load_gcs_to_bigquery_staging(gcs_uris: list = None) -> list:
    """
    Bulk loads raw Parquet files from GCS Data Lake into BigQuery staging dataset.
    Auto-creates BigQuery 'staging' dataset if not exists.
    """
    client = get_bigquery_client()
    project_id = Config.GCP_PROJECT_ID
    bucket_name = Config.GCP_GCS_BUCKET
    staging_dataset_id = Config.GCP_STAGING_DATASET

    dataset_ref = bigquery.DatasetReference(project_id, staging_dataset_id)

    try:
        dataset = client.get_dataset(dataset_ref)
        logger.info(f"BigQuery dataset '{staging_dataset_id}' found.")
    except Exception:
        logger.info(f"Creating BigQuery dataset '{staging_dataset_id}' in location 'asia-southeast1'...")
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "asia-southeast1"
        dataset = client.create_dataset(dataset)
        logger.info(f"Created BigQuery dataset '{staging_dataset_id}' successfully.")

    loaded_tables = []

    for parquet_file, target_table in TABLE_MAPPING.items():
        gcs_uri = f"gs://{bucket_name}/landing/{parquet_file}"
        table_ref = dataset_ref.table(target_table)

        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.PARQUET,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            autodetect=True
        )

        logger.info(f"Loading '{gcs_uri}' into BigQuery table '{staging_dataset_id}.{target_table}'...")
        load_job = client.load_table_from_uri(gcs_uri, table_ref, job_config=job_config)
        load_job.result()  # Wait for job to complete

        table = client.get_table(table_ref)
        logger.info(f"Successfully loaded {table.num_rows} rows into BigQuery '{staging_dataset_id}.{target_table}'.")
        loaded_tables.append(target_table)

    logger.info(f"BigQuery Staging Load completed. {len(loaded_tables)} tables loaded successfully.")
    return loaded_tables

if __name__ == "__main__":
    load_gcs_to_bigquery_staging()
