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

    files_to_upload = []

    if connector_name and connector_name != "all":
        # Specific connector directory
        conn_dir = os.path.join(base_landing, connector_name)
        if os.path.exists(conn_dir):
            for f in glob.glob(os.path.join(conn_dir, "*.parquet")):
                files_to_upload.append((f, f"landing/{connector_name}/{os.path.basename(f)}"))
        # Also check root landing for fallback
        for f in glob.glob(os.path.join(base_landing, "*.parquet")):
            if connector_name == "postgres_db" and "raw_" in os.path.basename(f):
                files_to_upload.append((f, f"landing/postgres_db/{os.path.basename(f)}"))
            elif connector_name == "crypto_api" and "crypto_" in os.path.basename(f):
                files_to_upload.append((f, f"landing/crypto_api/{os.path.basename(f)}"))
    else:
        # Upload all subdirectories and files
        for root, _, files in os.walk(base_landing):
            for f in files:
                if f.endswith(".parquet"):
                    full_path = os.path.join(root, f)
                    rel_dir = os.path.relpath(root, base_landing)
                    if rel_dir == ".":
                        # Guess connector from filename prefix
                        conn_sub = "crypto_api" if f.startswith("crypto_") else "postgres_db"
                        blob_path = f"landing/{conn_sub}/{f}"
                    else:
                        blob_path = f"landing/{rel_dir.replace('\\', '/')}/{f}"
                    files_to_upload.append((full_path, blob_path))

    if not files_to_upload:
        logger.warning(f"No Parquet files found in '{base_landing}' for connector '{connector_name or 'all'}'.")
        return []

    uploaded_uris = []
    logger.info(f"Found {len(files_to_upload)} parquet files for connector '{connector_name or 'all'}'. Uploading to GCS Bucket '{bucket_name}'...")

    for local_path, blob_path in files_to_upload:
        blob = bucket.blob(blob_path)
        logger.info(f"Uploading '{os.path.basename(local_path)}' to 'gs://{bucket_name}/{blob_path}'...")
        blob.upload_from_filename(local_path)
        gcs_uri = f"gs://{bucket_name}/{blob_path}"
        uploaded_uris.append(gcs_uri)
        logger.info(f"Successfully uploaded: {gcs_uri}")

    logger.info(f"GCS Data Lake upload finished. {len(uploaded_uris)} files uploaded successfully.")
    return uploaded_uris

if __name__ == "__main__":
    upload_landing_to_gcs()