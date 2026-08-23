import time
from typing import List, Optional, Dict, Tuple
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from src.utils.gcp_client import get_bigquery_client, get_storage_client
from src.utils.config import Config
from src.utils.logger import logger
from connectors._base.schemas import RunMode

def wait_for_table_schema(
    client, table_ref, expected_columns: set, table_label: str,
    max_attempts: int = 5, delay_sec: float = 3.0
) -> None:
    """Polls a table's schema via the Tables API (not the query engine) until
    it contains every expected column, or raises after exhausting retries.

    Observed in production: BigQuery's query engine can plan a SEPARATE query
    job (a dbt CREATE VIEW, or a CREATE OR REPLACE TABLE ... AS SELECT) against
    a table moments after a Load/Copy job reports DONE, and silently omit a
    column that was just added — a metadata-propagation lag between the Jobs
    API (immediately consistent) and the query engine's own schema cache. The
    Tables API itself (client.get_table) has been reliable in every
    observation so far, so polling it is the trustworthy check.
    """
    for attempt in range(1, max_attempts + 1):
        actual_columns = {f.name for f in client.get_table(table_ref).schema}
        if expected_columns.issubset(actual_columns):
            return
        missing = expected_columns - actual_columns
        if attempt == max_attempts:
            raise RuntimeError(
                f"{table_label}: schema still missing {missing} after "
                f"{max_attempts} verification attempts ({(max_attempts - 1) * delay_sec:.0f}s). "
                f"Refusing to proceed with a stale/incomplete schema."
            )
        logger.warning(
            f"{table_label}: schema missing {missing} on attempt {attempt}/{max_attempts}, "
            f"retrying in {delay_sec}s..."
        )
        time.sleep(delay_sec)

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

            if target_exists and mode == RunMode.FULL_REFRESH and not is_backfill:
                # Two prior approaches both failed intermittently in
                # production for 2 of 6 tables each time (a different pair
                # each run): (1) WRITE_TRUNCATE directly against the
                # pre-existing table kept its old schema; (2) deleting the
                # table then reloading under the SAME NAME, and later,
                # loading to a temp table then `CREATE OR REPLACE TABLE ...
                # AS SELECT` from it — both of which hand a freshly-written
                # table to a SEPARATE QUERY JOB moments later. The common
                # thread across every failure is a query-engine read
                # (a dbt CREATE VIEW, or our own CREATE OR REPLACE ... AS
                # SELECT) of a table another job just finished writing,
                # which the Tables API (get_table) has never once shown
                # stale in on-the-spot diagnosis — only the query engine's
                # own schema cache has lagged.
                #
                # Fix: load into a temp table, then use the Table Copy API
                # (client.copy_table) to replace the destination — a
                # metadata/storage-level operation, not a query-engine read
                # of the temp table's rows — and verify both the temp
                # table's and the destination's schema via the Tables API
                # (with retry) before proceeding, so any remaining
                # propagation lag surfaces as a loud, actionable error
                # instead of a silently incomplete schema.
                temp_table_name = f"{target_table}_full_refresh_temp"
                temp_table_ref = dataset_ref.table(temp_table_name)
                temp_job_config = bigquery.LoadJobConfig(
                    source_format=bigquery.SourceFormat.PARQUET,
                    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
                    autodetect=True
                )
                logger.info(
                    f"Full-refresh: loading '{selected_uri}' into temp table "
                    f"'{staging_dataset_id}.{temp_table_name}'..."
                )
                load_job = client.load_table_from_uri(selected_uri, temp_table_ref, job_config=temp_job_config)
                load_job.result()

                temp_columns = {f.name for f in client.get_table(temp_table_ref).schema}
                wait_for_table_schema(
                    client, temp_table_ref, temp_columns,
                    table_label=f"{staging_dataset_id}.{temp_table_name}"
                )

                logger.info(
                    f"Full-refresh: copying temp table into "
                    f"'{staging_dataset_id}.{target_table}' via Table Copy API..."
                )
                copy_job_config = bigquery.CopyJobConfig(
                    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
                )
                copy_job = client.copy_table(temp_table_ref, target_table_ref, job_config=copy_job_config)
                copy_job.result()

                wait_for_table_schema(
                    client, target_table_ref, temp_columns,
                    table_label=f"{staging_dataset_id}.{target_table}"
                )
                client.delete_table(temp_table_ref, not_found_ok=True)
            elif (mode == RunMode.FULL_REFRESH and not is_backfill) or not target_exists:
                # Full refresh with no pre-existing table, or initial table
                # creation: load directly. No same-name race here since the
                # table doesn't exist yet — the load's CREATE is the first
                # write under this name.
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

                    # Extract exact row-level mutation metrics from BigQuery DML statistics
                    dml_stats = getattr(merge_job, "dml_stats", None)
                    ins_cnt = getattr(dml_stats, "inserted_row_count", 0) if dml_stats else 0
                    upd_cnt = getattr(dml_stats, "updated_row_count", 0) if dml_stats else 0
                    del_cnt = getattr(dml_stats, "deleted_row_count", 0) if dml_stats else 0
                    
                    logger.info(f"Merge DML Stats for '{target_table}': +{ins_cnt} inserted, ~{upd_cnt} updated, -{del_cnt} deleted.")

                # Clean up temp table
                client.delete_table(temp_table_ref, not_found_ok=True)

            final_table = client.get_table(target_table_ref)
            logger.info(f"Staging table '{staging_dataset_id}.{target_table}' now has {final_table.num_rows} total rows.")
            loaded_tables.append(target_table)

    logger.info(f"BigQuery Staging Load completed. {len(loaded_tables)} tables synchronized successfully.")
    return loaded_tables

if __name__ == "__main__":
    load_gcs_to_bigquery_staging()