import os
import glob
from typing import List, Optional
from src.utils.gcp_client import get_storage_client
from src.utils.config import Config
from src.utils.logger import logger

def upload_landing_to_gcs(
    landing_dir: Optional[str] = None,
    connector_name: Optional[str] = None
) -> List[str]:
    """
    Uploads Parquet files from local landing zone to GCS Data Lake Bucket.
    Organizes files into namespaced GCS prefix: gs://<bucket>/landing/<connector_name>/<filename>.parquet
    - If connector_name is given (e.g. 'crypto_api'): uploads only files for that connector.
    - If connector_name is None / 'all': scans all connector subdirectories in landing/.
    """
    base_landing = landing_dir or Config.LANDING_DIR
    client = get_storage_client()
    bucket_name = Config.GCP_GCS_BUCKET

    try:
        bucket = client.bucket(bucket_name)
        if not bucket.exists():
            logger.info(f"GCS Bucket '{bucket_name}' does not exist. Creating bucket in region 'asia-southeast1'...")
            bucket = client.create_bucket(bucket_name, location="asia-southeast1")
            logger.info(f"Created GCS Bucket '{bucket_name}' successfully.")
    except Exception as e:
        logger.warning(f"Bucket check notice: {e}")
        bucket = client.bucket(bucket_name)

    # Build the upload plan keyed by DESTINATION blob path, never as a flat
    # list. Two local locations can map to the same destination — the
    # namespaced landing/<connector>/ directory the extractor writes to today,
    # and legacy root-level files from before namespacing existed. Appending
    # both to a list meant uploading two different files to one blob path
    # concurrently, so whichever finished last silently won: in production,
    # stale pre-tenant_slug root files randomly overwrote fresh ones, and a
    # different subset of staging tables lost the column on every run.
    # Namespaced files win; a root-level file is only used when nothing
    # namespaced claims that destination.
    namespaced_plan = {}
    fallback_plan = {}

    if connector_name and connector_name != "all":
        # Specific connector directory (authoritative source)
        conn_dir = os.path.join(base_landing, connector_name)
        if os.path.exists(conn_dir):
            for f in glob.glob(os.path.join(conn_dir, "*.parquet")):
                namespaced_plan[f"landing/{connector_name}/{os.path.basename(f)}"] = f
        # Legacy root-level landing files, used only where no namespaced file exists
        for f in glob.glob(os.path.join(base_landing, "*.parquet")):
            basename = os.path.basename(f)
            if connector_name == "postgres_db" and "raw_" in basename:
                fallback_plan[f"landing/postgres_db/{basename}"] = f
            elif connector_name == "crypto_api" and "crypto_" in basename:
                fallback_plan[f"landing/crypto_api/{basename}"] = f
    else:
        # Upload all subdirectories and files
        for root, _, files in os.walk(base_landing):
            for f in files:
                if f.endswith(".parquet"):
                    full_path = os.path.join(root, f)
                    rel_dir = os.path.relpath(root, base_landing)
                    if rel_dir == ".":
                        # Guess connector from filename prefix (legacy layout)
                        conn_sub = "crypto_api" if f.startswith("crypto_") else "postgres_db"
                        fallback_plan[f"landing/{conn_sub}/{f}"] = full_path
                    else:
                        clean_rel_dir = rel_dir.replace("\\", "/")
                        namespaced_plan[f"landing/{clean_rel_dir}/{f}"] = full_path

    for blob_path, local_path in fallback_plan.items():
        if blob_path in namespaced_plan:
            logger.warning(
                f"Ignoring stale legacy landing file '{local_path}': "
                f"'{namespaced_plan[blob_path]}' already provides "
                f"'{blob_path}'. Delete the legacy copy to silence this."
            )
            continue
        namespaced_plan[blob_path] = local_path

    files_to_upload = [(local_path, blob_path) for blob_path, local_path in namespaced_plan.items()]

    if not files_to_upload:
        logger.warning(f"No Parquet files found in '{base_landing}' for connector '{connector_name or 'all'}'.")
        return []

    from concurrent.futures import ThreadPoolExecutor, as_completed

    uploaded_uris = []
    logger.info(f"Found {len(files_to_upload)} parquet files for connector '{connector_name or 'all'}'. Uploading in parallel (4 workers) to GCS Bucket '{bucket_name}'...")

    def _upload_single_file(item):
        local_path, blob_path = item
        blob = bucket.blob(blob_path)
        blob.upload_from_filename(local_path)
        gcs_uri = f"gs://{bucket_name}/{blob_path}"
        logger.info(f"Uploaded: {gcs_uri}")
        return gcs_uri

    with ThreadPoolExecutor(max_workers=min(len(files_to_upload), 4)) as executor:
        futures = [executor.submit(_upload_single_file, item) for item in files_to_upload]
        for future in as_completed(futures):
            uploaded_uris.append(future.result())

    logger.info(f"GCS Data Lake upload finished. {len(uploaded_uris)} files uploaded successfully.")
    return uploaded_uris

if __name__ == "__main__":
    upload_landing_to_gcs()