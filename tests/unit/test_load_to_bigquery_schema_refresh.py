"""Regression test: WRITE_TRUNCATE against a pre-existing BigQuery table does
not reliably replace its schema (observed in production: new source columns
were silently dropped for tables that already existed, while newly-created
tables picked up the new schema correctly). Full-refresh must guarantee a
clean schema by dropping the table first, not rely on WRITE_TRUNCATE's
schema-merge behavior against an existing table.
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
        # First get_table call (pre-load schema check) finds the table;
        # the second (post-load row count) also finds it — both real.
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
    return client


def _fake_bucket():
    bucket = MagicMock()
    blob = MagicMock()
    blob.exists.return_value = True
    bucket.blob.return_value = blob
    return bucket


def test_full_refresh_drops_preexisting_table_before_reload():
    client = _fake_client(table_exists=True)
    with patch("src.load.load_to_bigquery.get_bigquery_client", return_value=client), \
         patch("src.load.load_to_bigquery.get_storage_client") as mock_storage:
        mock_storage.return_value.bucket.return_value = _fake_bucket()
        load_gcs_to_bigquery_staging(mode=RunMode.FULL_REFRESH, connector_name="postgres_db")

    assert client.delete_table.called, (
        "full-refresh into an existing table must drop it first to guarantee "
        "the schema is rebuilt from the source, not silently merged/kept"
    )


def test_full_refresh_does_not_drop_when_table_absent():
    client = _fake_client(table_exists=False)
    with patch("src.load.load_to_bigquery.get_bigquery_client", return_value=client), \
         patch("src.load.load_to_bigquery.get_storage_client") as mock_storage:
        mock_storage.return_value.bucket.return_value = _fake_bucket()
        load_gcs_to_bigquery_staging(mode=RunMode.FULL_REFRESH, connector_name="postgres_db")

    assert not client.delete_table.called, "nothing to drop when the table doesn't exist yet"
