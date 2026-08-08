import os
import json
from google.cloud import storage, bigquery
from google.oauth2 import service_account
from src.utils.config import Config
from src.utils.logger import logger

def get_gcp_credentials():
    """
    Authenticate using GCP_SA_KEY env var (JSON string) or local gcp_key.json file.
    """
    gcp_sa_key_str = os.getenv("GCP_SA_KEY")
    if gcp_sa_key_str and gcp_sa_key_str.strip():
        try:
            info = json.loads(gcp_sa_key_str)
            logger.info("Authenticated with GCP using GCP_SA_KEY environment secret.")
            return service_account.Credentials.from_service_account_info(info)
        except Exception as e:
            logger.warning(f"Failed to parse GCP_SA_KEY JSON string: {e}")

    key_file = Config.GCP_KEY_FILE
    if os.path.exists(key_file):
        logger.info(f"Authenticated with GCP using local key file '{key_file}'.")
        return service_account.Credentials.from_service_account_file(key_file)

    logger.info("Using GCP Application Default Credentials.")
    return None

def get_storage_client():
    creds = get_gcp_credentials()
    if creds:
        return storage.Client(credentials=creds, project=Config.GCP_PROJECT_ID)
    return storage.Client(project=Config.GCP_PROJECT_ID)

def get_bigquery_client():
    creds = get_gcp_credentials()
    if creds:
        return bigquery.Client(credentials=creds, project=Config.GCP_PROJECT_ID)
    return bigquery.Client(project=Config.GCP_PROJECT_ID)
