"""Regression test: full-refresh into a pre-existing BigQuery table must
rebuild its schema from source, without racing BigQuery's own metadata
propagation lag.

History (3 attempts):
1. WRITE_TRUNCATE alone silently kept the old schema on pre-existing tables.
2. Delete-then-reload under the same name made it WORSE in production —
   randomly 0 rows / stale schema, a same-name delete+recreate race.
3. Load-to-temp + `CREATE OR REPLACE TABLE ... AS SELECT` still failed
   intermittently for a different 2-of-6 tables each run — the common
   thread across every failed attempt was a SEPARATE QUERY JOB (dbt's
   CREATE VIEW, or our own CREATE OR REPLACE ... AS SELECT) reading a table
   moments after another job finished writing it, hitting the BigQuery
   query engine's own schema-cache lag. The Tables API (get_table) never
   once showed stale in diagnosis — only query-engine reads did.

The fix that stuck: load into a temp table, promote it via the Table Copy
API (a metadata/storage-level operation, not a query-engine read), and
verify schema via the Tables API (with retry) before and after — so any
remaining lag surfaces as a loud error instead of a silently incomplete
schema.
"""
from unittest.mock import MagicMock, patch

import pytest

from connectors._base.schemas import RunMode
from src.load.load_to_bigquery import load_gcs_to_bigquery_staging, wait_for_table_schema


def _table_with_columns(columns):
    t = MagicMock()
    t.schema = [MagicMock(name=c) for c in columns]
    for field, name in zip(t.schema, columns):
        field.name = name
    t.num_rows = 1
    return t


def _fake_client(table_exists: bool, final_columns=("id", "tenant_slug")):
    client = MagicMock()
    if table_exists:
        existing = _table_with_columns(("id",))
        temp_after_load = _table_with_columns(final_columns)
        target_after_copy = _table_with_columns(final_columns)
        # Order of get_table calls for ONE table in the target_exists branch:
        # 1) pre-load existence check (existing, old schema)
        # 2) after temp load, to compute temp_columns
        # 3) wait_for_table_schema poll on temp table
        # 4) wait_for_table_schema poll on target table (post-copy)
        # 5) post-load row count (end of loop, on target_table_ref)
        client.get_table.side_effect = [
            existing, temp_after_load, temp_after_load, target_after_copy, target_after_copy
        ] * 6
    else:
        from google.cloud.exceptions import NotFound
        post_load_table = _table_with_columns(final_columns)
        client.get_table.side_effect = [NotFound("no table"), post_load_table] * 6

    load_job = MagicMock()
    load_job.result.return_value = None
    client.load_table_from_uri.return_value = load_job
    copy_job = MagicMock()
    copy_job.result.return_value = None
    client.copy_table.return_value = copy_job
    return client


def _fake_bucket():
    bucket = MagicMock()
    blob = MagicMock()
    blob.exists.return_value = True
    bucket.blob.return_value = blob
    return bucket


def test_full_refresh_uses_copy_table_api_not_a_select_query():
    client = _fake_client(table_exists=True)
    with patch("src.load.load_to_bigquery.get_bigquery_client", return_value=client), \
         patch("src.load.load_to_bigquery.get_storage_client") as mock_storage:
        mock_storage.return_value.bucket.return_value = _fake_bucket()
        load_gcs_to_bigquery_staging(mode=RunMode.FULL_REFRESH, connector_name="postgres_db")

    assert client.copy_table.called, "must promote the temp table via Table Copy API"
    assert not client.query.called, (
        "must never use a SELECT-based query-engine read to promote the temp "
        "table — that is the exact mechanism that failed twice in production"
    )


def test_full_refresh_never_deletes_the_destination_table_by_its_real_name():
    client = _fake_client(table_exists=True)
    with patch("src.load.load_to_bigquery.get_bigquery_client", return_value=client), \
         patch("src.load.load_to_bigquery.get_storage_client") as mock_storage:
        mock_storage.return_value.bucket.return_value = _fake_bucket()
        load_gcs_to_bigquery_staging(mode=RunMode.FULL_REFRESH, connector_name="postgres_db")

    real_table_names = {"stg_raw_customers", "stg_raw_orders", "stg_raw_order_items",
                         "stg_raw_payments", "stg_raw_products", "stg_raw_reviews"}
    for call in client.delete_table.call_args_list:
        table_ref = call.args[0]
        deleted_name = table_ref.table_id if hasattr(table_ref, "table_id") else str(table_ref)
        assert deleted_name not in real_table_names


def test_full_refresh_does_not_touch_temp_machinery_when_table_absent():
    client = _fake_client(table_exists=False)
    with patch("src.load.load_to_bigquery.get_bigquery_client", return_value=client), \
         patch("src.load.load_to_bigquery.get_storage_client") as mock_storage:
        mock_storage.return_value.bucket.return_value = _fake_bucket()
        load_gcs_to_bigquery_staging(mode=RunMode.FULL_REFRESH, connector_name="postgres_db")

    assert not client.delete_table.called
    assert not client.copy_table.called


def test_wait_for_table_schema_raises_after_exhausting_retries():
    client = MagicMock()
    client.get_table.return_value = _table_with_columns(("id",))  # never gains tenant_slug
    with pytest.raises(RuntimeError, match="tenant_slug"):
        wait_for_table_schema(
            client, MagicMock(), {"id", "tenant_slug"},
            table_label="staging.stg_raw_test", max_attempts=2, delay_sec=0
        )


def test_wait_for_table_schema_succeeds_once_column_appears():
    client = MagicMock()
    client.get_table.side_effect = [
        _table_with_columns(("id",)),
        _table_with_columns(("id", "tenant_slug")),
    ]
    wait_for_table_schema(
        client, MagicMock(), {"id", "tenant_slug"},
        table_label="staging.stg_raw_test", max_attempts=3, delay_sec=0
    )
