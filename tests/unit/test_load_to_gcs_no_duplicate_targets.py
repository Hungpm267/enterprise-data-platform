"""Regression test for a silent data-corruption bug found in production.

`upload_landing_to_gcs` scanned TWO local locations for a connector's parquet
files and mapped both to the SAME GCS blob path:

  1. data/landing/<connector>/raw_x.parquet  -> landing/<connector>/raw_x.parquet
  2. data/landing/raw_x.parquet  (legacy)    -> landing/<connector>/raw_x.parquet

Both were then uploaded concurrently by a 4-worker pool, so whichever upload
finished LAST won. In production, stale root-level files from Aug 17 (before
the tenant_slug column existed) raced against fresh namespaced files and
randomly overwrote them — which is why a different, seemingly random subset of
staging tables came out missing `tenant_slug` on every pipeline run, while the
local files always looked correct.

The upload plan must never map two different local files onto one blob path.
When both a namespaced and a legacy root-level file exist, the namespaced one
wins (it is the path the extractor actually writes to today).
"""
import os
from unittest.mock import MagicMock, patch

import pytest

from src.load.load_to_gcs import upload_landing_to_gcs


@pytest.fixture
def landing_with_stale_root_duplicates(tmp_path):
    """Mirrors the production layout: fresh namespaced files plus stale
    legacy root-level files of the same name."""
    (tmp_path / "postgres_db").mkdir()
    fresh = tmp_path / "postgres_db" / "raw_products.parquet"
    fresh.write_bytes(b"FRESH-with-tenant-slug")
    stale = tmp_path / "raw_products.parquet"
    stale.write_bytes(b"STALE-no-tenant-slug")
    return tmp_path, str(fresh), str(stale)


def _capture_uploads(landing_dir, connector_name):
    """Runs the uploader against a mocked GCS client and returns the list of
    (local_path, blob_path) pairs it actually uploaded."""
    uploads = []
    bucket = MagicMock()

    def make_blob(blob_path):
        blob = MagicMock()
        blob.upload_from_filename.side_effect = (
            lambda local, _bp=blob_path: uploads.append((local, _bp))
        )
        return blob

    bucket.blob.side_effect = make_blob
    bucket.exists.return_value = True
    client = MagicMock()
    client.bucket.return_value = bucket

    with patch("src.load.load_to_gcs.get_storage_client", return_value=client):
        upload_landing_to_gcs(landing_dir=landing_dir, connector_name=connector_name)
    return uploads


def test_no_two_local_files_target_the_same_blob_path(landing_with_stale_root_duplicates):
    landing_dir, _fresh, _stale = landing_with_stale_root_duplicates
    uploads = _capture_uploads(str(landing_dir), "postgres_db")

    blob_paths = [blob for _local, blob in uploads]
    assert len(blob_paths) == len(set(blob_paths)), (
        f"two local files were uploaded to the same GCS blob path — whichever "
        f"finishes last silently wins: {uploads}"
    )


def test_namespaced_file_wins_over_stale_root_level_duplicate(landing_with_stale_root_duplicates):
    landing_dir, fresh, _stale = landing_with_stale_root_duplicates
    uploads = _capture_uploads(str(landing_dir), "postgres_db")

    target = "landing/postgres_db/raw_products.parquet"
    sources = [local for local, blob in uploads if blob == target]
    assert sources == [os.path.normpath(fresh)] or sources == [fresh], (
        f"expected the namespaced file to be the sole source for {target}, got {sources}"
    )


def test_root_level_file_still_uploads_when_no_namespaced_counterpart(tmp_path):
    """The legacy root-level fallback must keep working when it is the only
    copy — removing duplicates must not remove legitimate files."""
    (tmp_path / "postgres_db").mkdir()
    orphan = tmp_path / "raw_orders.parquet"
    orphan.write_bytes(b"only-copy")

    uploads = _capture_uploads(str(tmp_path), "postgres_db")
    blob_paths = [blob for _local, blob in uploads]
    assert "landing/postgres_db/raw_orders.parquet" in blob_paths
