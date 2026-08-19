import os
import json
import ast
import base64
from typing import Optional, Dict, Any
from google.cloud import storage, bigquery
from google.oauth2 import service_account
from src.utils.config import Config
from src.utils.logger import logger

def parse_service_account_content(raw_content: str) -> Dict[str, Any]:
    """
    Robustly parses GCP Service Account credentials from:
    1. Standard JSON string
    2. Base64 encoded JSON string
    3. Python dictionary string with single quotes (ast.literal_eval)
    """
    raw_content = raw_content.strip()
    if not raw_content:
        raise ValueError("Service account content is empty.")

    # 1. Try standard JSON
    try:
        return json.loads(raw_content)
    except Exception:
        pass

    # 2. Try Base64 decoded JSON
    try:
        decoded = base64.b64decode(raw_content).decode("utf-8").strip()
        return json.loads(decoded)
    except Exception:
        pass

    # 3. Try Python dict string (single quotes)
    try:
        parsed = ast.literal_eval(raw_content)
        if isinstance(parsed, dict) and "type" in parsed:
            return parsed
    except Exception:
        pass

    raise ValueError("Failed to parse Service Account key as valid JSON, Base64, or Python dict.")

def get_gcp_credentials():
    """
    Authenticate using GCP_SA_KEY env var or local gcp_key.json file.
    Ensures gcp_key.json is cleanly written to disk for dbt-bigquery compatibility.
    """
    key_file = Config.GCP_KEY_FILE
    gcp_sa_key_str = os.getenv("GCP_SA_KEY")

    # Case 1: Environment variable GCP_SA_KEY provided (GitHub Actions / Cloud)
    if gcp_sa_key_str and gcp_sa_key_str.strip():
        try:
            info = parse_service_account_content(gcp_sa_key_str)
            logger.info("Authenticated with GCP using GCP_SA_KEY environment secret.")
            
            # Ensure gcp_key.json exists on disk for dbt profiles.yml
            try:
                with open(key_file, "w", encoding="utf-8") as f:
                    json.dump(info, f, indent=2)
            except Exception as fe:
                logger.warning(f"Could not sync gcp_key.json to disk for dbt: {fe}")

            return service_account.Credentials.from_service_account_info(info)
        except Exception as e:
            logger.warning(f"Failed to parse GCP_SA_KEY: {e}")

    # Case 2: Local key file exists on disk
    if os.path.exists(key_file):
        try:
            with open(key_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
            info = parse_service_account_content(content)
            logger.info(f"Authenticated with GCP using local key file '{key_file}'.")
            return service_account.Credentials.from_service_account_info(info)
        except Exception as e:
            logger.warning(f"Failed to load credentials from key file '{key_file}': {e}")

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
