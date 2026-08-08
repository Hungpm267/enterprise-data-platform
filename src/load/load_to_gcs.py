import os
import glob
from src.utils.gcp_client import get_storage_client
from src.utils.config import Config
from src.utils.logger import logger

def upload_landing_to_gcs(landing_dir: str = None) -> list:
    """
    Uploads all Parquet files from local landing zone to GCS Data Lake Bucket.
    Auto-creates the GCS Bucket if it does not exist.
    """
    landing_path = landing_dir or Config.LANDING_DIR
    parquet_files = glob.glob(os.path.join(landing_path, "*.parquet"))

    if not parquet_files:
        logger.warning(f"No Parquet files found in '{landing_path}' to upload to GCS.")
        return []

    client = get_storage_client()
    bucket_name = Config.GCP_GCS_BUCKET

    try:
        bucket = client.bucket(bucket_name)
        if not bucket.exists():
            logger.info(f"GCS Bucket '{bucket_name}' does not exist. Creating bucket in region 'asia-southeast1'...")
            bucket = client.create_bucket(bucket_name, location="asia-southeast1")
            logger.info(f"Created GCS Bucket '{bucket_name}' successfully.")
    except Exception as e:
        logger.warning(f"Bucket check/creation notice: {e}")
        bucket = client.bucket(bucket_name)

    uploaded_uris = []
    logger.info(f"Found {len(parquet_files)} parquet files. Starting upload to GCS Bucket '{bucket_name}'...")

    for file_path in parquet_files:
        filename = os.path.basename(file_path)
        blob_path = f"landing/{filename}"
        blob = bucket.blob(blob_path)

        logger.info(f"Uploading '{filename}' to 'gs://{bucket_name}/{blob_path}'...")
        blob.upload_from_filename(file_path)
        gcs_uri = f"gs://{bucket_name}/{blob_path}"
        uploaded_uris.append(gcs_uri)
        logger.info(f"Successfully uploaded to '{gcs_uri}'.")

    logger.info(f"GCS Data Lake upload finished. {len(uploaded_uris)} files uploaded successfully.")
    return uploaded_uris

if __name__ == "__main__":
    upload_landing_to_gcs()
