from datetime import datetime
from typing import Optional
from google.cloud import bigquery
from src.utils.gcp_client import get_bigquery_client
from src.utils.config import Config
from src.utils.logger import logger
from src.utils.timezone import get_vietnam_now_str

class StateManager:
    """
    Manages incremental ingestion watermarks and state tracking in BigQuery.
    Guarantees automated, persistent state tracking across scheduled executions.
    """
    def __init__(self):
        self.client = get_bigquery_client()
        self.project_id = Config.GCP_PROJECT_ID
        self.dataset_id = Config.GCP_STAGING_DATASET
        self.location = "asia-southeast1"
        self.table_id = f"{self.project_id}.{self.dataset_id}._pipeline_state"
        self._ensure_state_table()

    def _ensure_state_table(self):
        """Creates the state tracking table if it does not exist."""
        schema = [
            bigquery.SchemaField("connector_name", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("last_sync_timestamp", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("last_run_mode", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("records_extracted", "INT64", mode="NULLABLE"),
            bigquery.SchemaField("updated_at", "TIMESTAMP", mode="REQUIRED"),
        ]
        table = bigquery.Table(self.table_id, schema=schema)
        try:
            self.client.create_table(table, exists_ok=True)
        except Exception as e:
            logger.warning(f"Could not verify/create state table '{self.table_id}': {e}")

    def get_watermark(self, connector_name: str) -> Optional[datetime]:
        """
        Retrieves the last successful watermark timestamp for a given connector.
        """
        query = f"""
        SELECT last_sync_timestamp 
        FROM `{self.table_id}` 
        WHERE connector_name = @connector_name
        LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("connector_name", "STRING", connector_name)
            ]
        )
        try:
            query_job = self.client.query(query, job_config=job_config, location=self.location)
            results = list(query_job.result())
            if results and results[0].last_sync_timestamp:
                watermark = results[0].last_sync_timestamp
                logger.info(f"Retrieved active watermark for '{connector_name}': {watermark}")
                return watermark
        except Exception as e:
            logger.warning(f"Error reading watermark for '{connector_name}': {e}")
        
        logger.info(f"No prior watermark found for connector '{connector_name}'. Starting baseline sync.")
        return None

    def commit_watermark(
        self,
        connector_name: str,
        sync_timestamp: datetime,
        mode: str = "incremental",
        records_extracted: int = 0
    ):
        """
        Persists the newly achieved watermark timestamp idempotently in BigQuery.
        """
        formatted_sync_time = sync_timestamp.strftime("%Y-%m-%d %H:%M:%S")
        formatted_now = get_vietnam_now_str()

        merge_query = f"""
        MERGE `{self.table_id}` T
        USING (
            SELECT 
                @connector_name AS connector_name,
                TIMESTAMP(@sync_timestamp) AS last_sync_timestamp,
                @last_run_mode AS last_run_mode,
                @records_extracted AS records_extracted,
                TIMESTAMP(@updated_at) AS updated_at
        ) S
        ON T.connector_name = S.connector_name
        WHEN MATCHED THEN
            UPDATE SET 
                last_sync_timestamp = S.last_sync_timestamp,
                last_run_mode = S.last_run_mode,
                records_extracted = S.records_extracted,
                updated_at = S.updated_at
        WHEN NOT MATCHED THEN
            INSERT (connector_name, last_sync_timestamp, last_run_mode, records_extracted, updated_at)
            VALUES (S.connector_name, S.last_sync_timestamp, S.last_run_mode, S.records_extracted, S.updated_at);
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("connector_name", "STRING", connector_name),
                bigquery.ScalarQueryParameter("sync_timestamp", "STRING", formatted_sync_time),
                bigquery.ScalarQueryParameter("last_run_mode", "STRING", mode),
                bigquery.ScalarQueryParameter("records_extracted", "INT64", records_extracted),
                bigquery.ScalarQueryParameter("updated_at", "STRING", formatted_now),
            ]
        )
        try:
            query_job = self.client.query(merge_query, job_config=job_config, location=self.location)
            query_job.result()
            logger.info(f"Watermark successfully committed for '{connector_name}': {formatted_sync_time}")
        except Exception as e:
            logger.error(f"Failed to commit watermark for '{connector_name}': {e}")
            raise e

    def reset_watermark(self, connector_name: str):
        """
        Resets/deletes the watermark for full-refresh resets.
        """
        delete_query = f"""
        DELETE FROM `{self.table_id}` WHERE connector_name = @connector_name
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("connector_name", "STRING", connector_name)
            ]
        )
        try:
            query_job = self.client.query(delete_query, job_config=job_config, location=self.location)
            query_job.result()
            logger.info(f"Watermark reset for connector '{connector_name}'.")
        except Exception as e:
            logger.warning(f"Failed to reset watermark for '{connector_name}': {e}")