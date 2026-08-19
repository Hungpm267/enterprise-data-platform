import os
import uuid
from datetime import datetime
from typing import Optional
from google.cloud import bigquery
from src.utils.gcp_client import get_bigquery_client
from src.utils.config import Config
from src.utils.logger import logger
from src.utils.timezone import get_vietnam_now_str

class StateManager:
    """
    Dual-layer State Management & Observability Engine in BigQuery:
    1. `_pipeline_state`: Key-value store tracking current Watermark cursor for incremental queries.
    2. `_pipeline_audit_log`: Append-only audit trail recording every run's metrics, row volume, and status.
    """
    def __init__(self):
        self.client = get_bigquery_client()
        self.project_id = Config.GCP_PROJECT_ID
        self.dataset_id = Config.GCP_STAGING_DATASET
        self.location = "asia-southeast1"
        self.state_table_id = f"{self.project_id}.{self.dataset_id}._pipeline_state"
        self.audit_table_id = f"{self.project_id}.{self.dataset_id}._pipeline_audit_log"
        self._ensure_tables()

    def _ensure_tables(self):
        """Creates the state tracking table and audit log table if they do not exist."""
        # 1. State Table (1 row per connector)
        state_schema = [
            bigquery.SchemaField("connector_name", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("last_sync_timestamp", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("last_run_mode", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("records_extracted", "INT64", mode="NULLABLE"),
            bigquery.SchemaField("updated_at", "TIMESTAMP", mode="REQUIRED"),
        ]
        state_table = bigquery.Table(self.state_table_id, schema=state_schema)
        try:
            self.client.create_table(state_table, exists_ok=True)
        except Exception as e:
            logger.warning(f"Could not verify/create state table '{self.state_table_id}': {e}")

        # 2. Audit Log Table (Append-only history)
        audit_schema = [
            bigquery.SchemaField("run_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("connector_name", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("run_mode", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("status", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("watermark_start", "TIMESTAMP", mode="NULLABLE"),
            bigquery.SchemaField("watermark_end", "TIMESTAMP", mode="NULLABLE"),
            bigquery.SchemaField("records_extracted", "INT64", mode="NULLABLE"),
            bigquery.SchemaField("tables_count", "INT64", mode="NULLABLE"),
            bigquery.SchemaField("duration_sec", "FLOAT64", mode="NULLABLE"),
            bigquery.SchemaField("error_message", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("executed_at", "TIMESTAMP", mode="REQUIRED"),
        ]
        audit_table = bigquery.Table(self.audit_table_id, schema=audit_schema)
        try:
            self.client.create_table(audit_table, exists_ok=True)
        except Exception as e:
            logger.warning(f"Could not verify/create audit table '{self.audit_table_id}': {e}")

    def get_watermark(self, connector_name: str) -> Optional[datetime]:
        """
        Retrieves the last successful watermark timestamp for a given connector.
        """
        query = f"""
        SELECT last_sync_timestamp 
        FROM `{self.state_table_id}` 
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
        Persists the newly achieved watermark timestamp idempotently in BigQuery _pipeline_state.
        """
        formatted_sync_time = sync_timestamp.strftime("%Y-%m-%d %H:%M:%S")
        formatted_now = get_vietnam_now_str()

        merge_query = f"""
        MERGE `{self.state_table_id}` T
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
            logger.info(f"Watermark state committed for '{connector_name}': {formatted_sync_time} (Mode: {mode}, Rows: {records_extracted})")
        except Exception as e:
            logger.error(f"Failed to commit watermark for '{connector_name}': {e}")
            raise e

    def log_audit_trail(
        self,
        connector_name: str,
        run_mode: str,
        status: str,
        watermark_start: Optional[str] = None,
        watermark_end: Optional[str] = None,
        records_extracted: int = 0,
        tables_count: int = 0,
        duration_sec: float = 0.0,
        error_message: Optional[str] = None,
        run_id: Optional[str] = None
    ):
        """
        Appends an execution audit record into BigQuery `_pipeline_audit_log`
        for enterprise-grade Data Observability and pipeline monitoring.
        """
        if not run_id:
            run_id = os.getenv("GITHUB_RUN_ID") or str(uuid.uuid4())[:8]

        formatted_now = get_vietnam_now_str()

        insert_query = f"""
        INSERT INTO `{self.audit_table_id}` (
            run_id,
            connector_name,
            run_mode,
            status,
            watermark_start,
            watermark_end,
            records_extracted,
            tables_count,
            duration_sec,
            error_message,
            executed_at
        ) VALUES (
            @run_id,
            @connector_name,
            @run_mode,
            @status,
            TIMESTAMP(@watermark_start),
            TIMESTAMP(@watermark_end),
            @records_extracted,
            @tables_count,
            @duration_sec,
            @error_message,
            TIMESTAMP(@executed_at)
        )
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("run_id", "STRING", run_id),
                bigquery.ScalarQueryParameter("connector_name", "STRING", connector_name),
                bigquery.ScalarQueryParameter("run_mode", "STRING", run_mode),
                bigquery.ScalarQueryParameter("status", "STRING", status),
                bigquery.ScalarQueryParameter("watermark_start", "STRING", watermark_start),
                bigquery.ScalarQueryParameter("watermark_end", "STRING", watermark_end),
                bigquery.ScalarQueryParameter("records_extracted", "INT64", records_extracted),
                bigquery.ScalarQueryParameter("tables_count", "INT64", tables_count),
                bigquery.ScalarQueryParameter("duration_sec", "FLOAT64", duration_sec),
                bigquery.ScalarQueryParameter("error_message", "STRING", error_message),
                bigquery.ScalarQueryParameter("executed_at", "STRING", formatted_now),
            ]
        )
        try:
            query_job = self.client.query(insert_query, job_config=job_config, location=self.location)
            query_job.result()
            logger.info(f"Audit log persisted in '{self.audit_table_id}' [Run ID: {run_id}, Status: {status}]")
        except Exception as e:
            logger.warning(f"Could not persist audit log to BigQuery: {e}")

    def reset_watermark(self, connector_name: str):
        """
        Resets/deletes the watermark for full-refresh resets.
        """
        delete_query = f"""
        DELETE FROM `{self.state_table_id}` WHERE connector_name = @connector_name
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