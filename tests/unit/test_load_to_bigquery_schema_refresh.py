"""Regression test: full-refresh into a pre-existing BigQuery table must
rebuild its schema from source, without racing BigQuery's own eventual
consistency for same-name table delete+recreate.

History: WRITE_TRUNCATE alone silently kept the old schema on pre-existing
tables (new source columns dropped). A first fix (delete the table, then
reload under the same name) made things *worse* in production — freshly
"recreated" tables randomly came back with 0 rows or a stale/empty-inferred
schema, because deleting and immediately reloading under the same name races
BigQuery's own eventual consistency for that name. The fix that stuck: load
into a differently-named temp table, then atomically replace the destination
via `CREATE OR REPLACE TABLE ... AS SELECT * FROM temp` — a single DDL
operation, never a delete+recreate under the same name.
"""
from unittest.mock import MagicMock, patch

from connectors._base.schemas import RunMode
from src.load.load_to_bigquery import load_gcs_to_bigquery_staging


def _fake_client(table_exists: bool):
    client = MagicMock()
    post_load_table = MagicMock()
    post_load_table.num_rows = 0
    if table_exists:
        existing = MagicMock()
        existing.schema = []
        client.get_table.return_value = existing
    else:
        from google.cloud.exceptions import NotFound
        # 6 tables in the postgres_db mapping, each calling get_table twice
        # (pre-load existence check, post-load row count): the pre-load call
        # never finds the table (that's the scenario under test); the
        # post-load call always succeeds, since the load just created it.
        calls_per_table = [NotFound("no table"), post_load_table]
        client.get_table.side_effect = calls_per_table * 6
    load_job = MagicMock()
    load_job.result.return_value = None
    client.load_table_from_uri.return_value = load_job
    replace_job = MagicMock()
    replace_job.result.return_value = None
    client.query.return_value = replace_job
    return client


def _fake_bucket():
    bucket = MagicMock()
    blob = MagicMock()
    blob.exists.return_value = True
    bucket.blob.return_value = blob
    return bucket


def test_full_refresh_never_deletes_the_destination_table_by_its_real_name():
    """The destination table (the name dbt/analytics queries) must never be
    the target of client.delete_table — only a temp table may be dropped,
    and only after the atomic replace has already succeeded."""
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
        assert deleted_name not in real_table_names, (
            f"deleted '{deleted_name}' by its real name — this races BigQuery's "
            f"same-name delete+recreate consistency; only temp tables may be dropped"
        )


def test_full_refresh_loads_into_temp_table_then_atomically_replaces():
    client = _fake_client(table_exists=True)
    with patch("src.load.load_to_bigquery.get_bigquery_client", return_value=client), \
         patch("src.load.load_to_bigquery.get_storage_client") as mock_storage:
        mock_storage.return_value.bucket.return_value = _fake_bucket()
        load_gcs_to_bigquery_staging(mode=RunMode.FULL_REFRESH, connector_name="postgres_db")

    # Every load in this run must have targeted a "_full_refresh_temp" table,
    # never the real destination table directly.
    for call in client.load_table_from_uri.call_args_list:
        table_ref = call.args[1]
        loaded_name = table_ref.table_id if hasattr(table_ref, "table_id") else str(table_ref)
        assert loaded_name.endswith("_full_refresh_temp"), (
            f"loaded directly into '{loaded_name}' instead of a temp table"
        )

    # And a CREATE OR REPLACE TABLE ... AS SELECT must have run to promote
    # each temp table into its real destination.
    replace_calls = [c.args[0] for c in client.query.call_args_list]
    assert any("CREATE OR REPLACE TABLE" in sql for sql in replace_calls)


def test_full_refresh_does_not_touch_temp_machinery_when_table_absent():
    """When the destination table doesn't exist yet, there's no same-name
    race to avoid — load it directly, no temp table needed."""
    client = _fake_client(table_exists=False)
    with patch("src.load.load_to_bigquery.get_bigquery_client", return_value=client), \
         patch("src.load.load_to_bigquery.get_storage_client") as mock_storage:
        mock_storage.return_value.bucket.return_value = _fake_bucket()
        load_gcs_to_bigquery_staging(mode=RunMode.FULL_REFRESH, connector_name="postgres_db")

    assert not client.delete_table.called
    for call in client.load_table_from_uri.call_args_list:
        table_ref = call.args[1]
        loaded_name = table_ref.table_id if hasattr(table_ref, "table_id") else str(table_ref)
        assert not loaded_name.endswith("_full_refresh_temp")
