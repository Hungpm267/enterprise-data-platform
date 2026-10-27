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

    # Only the namespaced landing/<connector>/ directories are uploaded — the
    # layout every extractor writes to. Root-level parquet files are ignored:
    # they are stale leftovers from before namespacing, and uploading them
    # once raced against fresh files on the same blob path and silently
    # overwrote them in production.
    upload_plan = {}

    if connector_name and connector_name != "all":
        conn_dir = os.path.join(base_landing, connector_name)
        for f in glob.glob(os.path.join(conn_dir, "*.parquet")):
            upload_plan[f"landing/{connector_name}/{os.path.basename(f)}"] = f
    else:
        for root, _, files in os.walk(base_landing):
            rel_dir = os.path.relpath(root, base_landing)
            if rel_dir == ".":
                continue
            clean_rel_dir = rel_dir.replace("\\", "/")
            for f in files:
                if f.endswith(".parquet"):
                    upload_plan[f"landing/{clean_rel_dir}/{f}"] = os.path.join(root, f)

    stale_root_files = glob.glob(os.path.join(base_landing, "*.parquet"))
    if stale_root_files:
        logger.warning(f"Ignoring {len(stale_root_files)} stale root-level landing file(s) in '{base_landing}': {stale_root_files}")

    files_to_upload = [(local_path, blob_path) for blob_path, local_path in upload_plan.items()]

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