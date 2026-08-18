from typing import List, Optional, Dict, Tuple
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from src.utils.gcp_client import get_bigquery_client, get_storage_client
from src.utils.config import Config
from src.utils.logger import logger
from connectors._base.schemas import RunMode

CONNECTOR_TABLE_MAPPING: Dict[str, Dict[str, Tuple[str, str]]] = {
    "postgres_db": {
        "raw_customers.parquet": ("stg_raw_customers", "customer_id"),
        "raw_orders.parquet": ("stg_raw_orders", "order_id"),
        "raw_order_items.parquet": ("stg_raw_order_items", "order_item_id"),
        "raw_payments.parquet": ("stg_raw_payments", "payment_id"),
        "raw_products.parquet": ("stg_raw_products", "product_id"),
        "raw_reviews.parquet": ("stg_raw_reviews", "review_id"),
    },
    "crypto_api": {
        "crypto_market_coins.parquet": ("stg_raw_crypto_market_coins", "coin_id"),
        "crypto_global_market.parquet": ("stg_raw_crypto_global_market", "snapshot_id"),
    }
}

def get_cast_expr(col_name: str, field_type: str) -> str:
    """Generates type-safe BigQuery SQL cast expressions to prevent type mismatch errors."""
    if field_type in ["NUMERIC", "BIGNUMERIC"]:
        return f"SAFE_CAST(S.{col_name} AS NUMERIC)"
    elif field_type in ["TIMESTAMP"]:
        return f"SAFE_CAST(S.{col_name} AS TIMESTAMP)"
    elif field_type in ["INT64", "INTEGER"]:
        return f"SAFE_CAST(S.{col_name} AS INT64)"
    elif field_type == "STRING":
        return f"SAFE_CAST(S.{col_name} AS STRING)"
    elif field_type == "FLOAT64":
        return f"SAFE_CAST(S.{col_name} AS FLOAT64)"
    elif field_type == "BOOLEAN":
        return f"SAFE_CAST(S.{col_name} AS BOOLEAN)"
    return f"S.{col_name}"

def load_gcs_to_bigquery_staging(
    mode: RunMode = RunMode.INCREMENTAL,
    is_backfill: bool = False,
    connector_name: Optional[str] = None
) -> List[str]:
    """
    Loads Parquet files from GCS Data Lake into BigQuery staging dataset.
    - If connector_name is specified: only syncs tables for that specific connector.
    - If mode == FULL_REFRESH and not is_backfill: Overwrites staging tables with WRITE_TRUNCATE.
    - If mode == INCREMENTAL or is_backfill: Uses type-safe idempotent BigQuery MERGE by Primary Key.
    """
    client = get_bigquery_client()
    project_id = Config.GCP_PROJECT_ID
    bucket_name = Config.GCP_GCS_BUCKET
    staging_dataset_id = Config.GCP_STAGING_DATASET

    dataset_ref = bigquery.DatasetReference(project_id, staging_dataset_id)

    try:
        client.get_dataset(dataset_ref)
        logger.info(f"BigQuery dataset '{staging_dataset_id}' found.")
    except Exception:
        logger.info(f"Creating BigQuery dataset '{staging_dataset_id}' in location 'asia-southeast1'...")
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "asia-southeast1"
        client.create_dataset(dataset)
        logger.info(f"Created BigQuery dataset '{staging_dataset_id}' successfully.")

    gcs_storage_client = get_storage_client()
    bucket = gcs_storage_client.bucket(bucket_name)

    # Determine connectors to process
    connectors_to_process = {}
    if connector_name and connector_name in CONNECTOR_TABLE_MAPPING:
        connectors_to_process[connector_name] = CONNECTOR_TABLE_MAPPING[connector_name]
    else:
        connectors_to_process = CONNECTOR_TABLE_MAPPING

    loaded_tables = []

    for conn_name, table_map in connectors_to_process.items():
        logger.info(f"Processing GCS ingestion for connector '{conn_name}'...")
        for parquet_file, (target_table, primary_key) in table_map.items():
            # Check namespaced path first, then flat landing path as fallback
            namespaced_blob_path = f"landing/{conn_name}/{parquet_file}"
            flat_blob_path = f"landing/{parquet_file}"
            
            selected_uri = None
            if bucket.blob(namespaced_blob_path).exists():
                selected_uri = f"gs://{bucket_name}/{namespaced_blob_path}"
            elif bucket.blob(flat_blob_path).exists():
                selected_uri = f"gs://{bucket_name}/{flat_blob_path}"
            else:
                logger.warning(f"File '{parquet_file}' not found in GCS for connector '{conn_name}'. Skipping.")
                continue

            target_table_ref = dataset_ref.table(target_table)

            # Check if target table already exists
            target_exists = False
            target_schema = None
            try:
                target_table_obj = client.get_table(target_table_ref)
                target_exists = True
                target_schema = target_table_obj.schema
            except NotFound:
                target_exists = False

            if (mode == RunMode.FULL_REFRESH and not is_backfill) or not target_exists:
                # Full refresh mode or initial table creation: load directly
                job_config = bigquery.LoadJobConfig(
                    source_format=bigquery.SourceFormat.PARQUET,
                    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
                    autodetect=True
                )
                logger.info(f"Loading '{selected_uri}' directly into '{staging_dataset_id}.{target_table}'...")
                load_job = client.load_table_from_uri(selected_uri, target_table_ref, job_config=job_config)
                load_job.result()
            else:
                # Incremental / Backfill mode with existing target table
                temp_table_name = f"{target_table}_incoming_temp"
                temp_table_ref = dataset_ref.table(temp_table_name)

                temp_job_config = bigquery.LoadJobConfig(
                    source_format=bigquery.SourceFormat.PARQUET,
                    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
                    autodetect=True
                )
                logger.info(f"Loading incoming batch '{selected_uri}' into temp table '{staging_dataset_id}.{temp_table_name}'...")
                load_job = client.load_table_from_uri(selected_uri, temp_table_ref, job_config=temp_job_config)
                load_job.result()

                temp_table_obj = client.get_table(temp_table_ref)
                if temp_table_obj.num_rows == 0:
                    logger.info(f"Incoming batch for '{target_table}' has 0 rows (delta is empty). Skipping merge.")
                else:
                    update_set_clause = ", ".join([
                        f"T.{col.name} = {get_cast_expr(col.name, col.field_type)}"
                        for col in target_schema if col.name != primary_key
                    ])
                    insert_cols_clause = ", ".join([col.name for col in target_schema])
                    insert_vals_clause = ", ".join([
                        get_cast_expr(col.name, col.field_type)
                        for col in target_schema
                    ])

                    merge_sql = f"""
                    MERGE `{project_id}.{staging_dataset_id}.{target_table}` T
                    USING `{project_id}.{staging_dataset_id}.{temp_table_name}` S
                    ON CAST(T.{primary_key} AS STRING) = CAST(S.{primary_key} AS STRING)
                    WHEN MATCHED THEN
                        UPDATE SET {update_set_clause}
                    WHEN NOT MATCHED THEN
                        INSERT ({insert_cols_clause})
                        VALUES ({insert_vals_clause});
                    """
                    logger.info(f"Executing Type-Safe Staging Merge on '{staging_dataset_id}.{target_table}' ({temp_table_obj.num_rows} incoming rows)...")
                    merge_job = client.query(merge_sql)
                    merge_job.result()

                # Clean up temp table
                client.delete_table(temp_table_ref, not_found_ok=True)

            final_table = client.get_table(target_table_ref)
            logger.info(f"Staging table '{staging_dataset_id}.{target_table}' now has {final_table.num_rows} total rows.")
            loaded_tables.append(target_table)

    logger.info(f"BigQuery Staging Load completed. {len(loaded_tables)} tables synchronized successfully.")
    return loaded_tables

if __name__ == "__main__":
    load_gcs_to_bigquery_staging()