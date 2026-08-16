from typing import List, Optional
from google.cloud import bigquery
from src.utils.gcp_client import get_bigquery_client
from src.utils.config import Config
from src.utils.logger import logger
from connectors._base.schemas import RunMode

TABLE_MAPPING = {
    "raw_customers.parquet": ("stg_raw_customers", "customer_id"),
    "raw_orders.parquet": ("stg_raw_orders", "order_id"),
    "raw_order_items.parquet": ("stg_raw_order_items", "order_item_id"),
    "raw_payments.parquet": ("stg_raw_payments", "payment_id"),
    "raw_products.parquet": ("stg_raw_products", "product_id"),
    "raw_reviews.parquet": ("stg_raw_reviews", "review_id"),
}

def load_gcs_to_bigquery_staging(
    mode: RunMode = RunMode.INCREMENTAL,
    is_backfill: bool = False
) -> List[str]:
    """
    Loads Parquet files from GCS Data Lake into BigQuery staging dataset.
    - If mode == FULL_REFRESH and not is_backfill: Overwrites staging tables with WRITE_TRUNCATE.
    - If mode == INCREMENTAL or is_backfill: Uses idempotent BigQuery MERGE to merge incoming
      records into staging tables by Primary Key, preserving all existing historical partitions.
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

    loaded_tables = []

    for parquet_file, (target_table, primary_key) in TABLE_MAPPING.items():
        gcs_uri = f"gs://{bucket_name}/landing/{parquet_file}"
        target_table_ref = dataset_ref.table(target_table)

        if mode == RunMode.FULL_REFRESH and not is_backfill:
            # Full refresh mode: truncate and load
            job_config = bigquery.LoadJobConfig(
                source_format=bigquery.SourceFormat.PARQUET,
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
                autodetect=True
            )
            logger.info(f"Full Refresh loading '{gcs_uri}' into '{staging_dataset_id}.{target_table}'...")
            load_job = client.load_table_from_uri(gcs_uri, target_table_ref, job_config=job_config)
            load_job.result()
        else:
            # Incremental / Backfill mode: Idempotent staging merge
            temp_table_name = f"{target_table}_incoming_temp"
            temp_table_ref = dataset_ref.table(temp_table_name)

            temp_job_config = bigquery.LoadJobConfig(
                source_format=bigquery.SourceFormat.PARQUET,
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
                autodetect=True
            )
            logger.info(f"Loading incoming batch '{gcs_uri}' into temp table '{staging_dataset_id}.{temp_table_name}'...")
            load_job = client.load_table_from_uri(gcs_uri, temp_table_ref, job_config=temp_job_config)
            load_job.result()

            # Check if target table exists
            try:
                target_table_obj = client.get_table(target_table_ref)
                columns = [schema_field.name for schema_field in target_table_obj.schema]
                
                # Perform BigQuery MERGE
                update_set_clause = ", ".join([f"T.{col} = S.{col}" for col in columns if col != primary_key])
                insert_cols_clause = ", ".join(columns)
                insert_vals_clause = ", ".join([f"S.{col}" for col in columns])

                merge_sql = f"""
                MERGE `{project_id}.{staging_dataset_id}.{target_table}` T
                USING `{project_id}.{staging_dataset_id}.{temp_table_name}` S
                ON T.{primary_key} = S.{primary_key}
                WHEN MATCHED THEN
                    UPDATE SET {update_set_clause}
                WHEN NOT MATCHED THEN
                    INSERT ({insert_cols_clause})
                    VALUES ({insert_vals_clause});
                """
                logger.info(f"Executing Idempotent Staging Merge on '{staging_dataset_id}.{target_table}' via PK '{primary_key}'...")
                merge_job = client.query(merge_sql)
                merge_job.result()
            except Exception:
                # Target table does not exist yet: copy temp table to target
                logger.info(f"Target table '{target_table}' not found. Initializing from incoming batch...")
                copy_job = client.copy_table(temp_table_ref, target_table_ref)
                copy_job.result()

            # Clean up temp table
            client.delete_table(temp_table_ref, not_found_ok=True)

        table = client.get_table(target_table_ref)
        logger.info(f"Staging table '{staging_dataset_id}.{target_table}' now has {table.num_rows} total rows.")
        loaded_tables.append(target_table)

    logger.info(f"BigQuery Staging Load completed. {len(loaded_tables)} tables synchronized successfully.")
    return loaded_tables

if __name__ == "__main__":
    load_gcs_to_bigquery_staging()