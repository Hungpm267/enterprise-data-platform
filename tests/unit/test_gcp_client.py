import json
import base64
from src.utils.gcp_client import parse_service_account_content

def test_parse_valid_json_string():
    """Verify parsing standard JSON service account content."""
    sample_dict = {"type": "service_account", "project_id": "test-proj", "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC..."}
    json_str = json.dumps(sample_dict)
    parsed = parse_service_account_content(json_str)
    assert parsed["type"] == "service_account"
    assert parsed["project_id"] == "test-proj"

def test_parse_base64_encoded_string():
    """Verify parsing Base64-encoded service account key."""
    sample_dict = {"type": "service_account", "project_id": "b64-proj"}
    b64_str = base64.b64encode(json.dumps(sample_dict).encode("utf-8")).decode("utf-8")
    parsed = parse_service_account_content(b64_str)
    assert parsed["type"] == "service_account"
    assert parsed["project_id"] == "b64-proj"

def test_parse_python_single_quoted_dict_string():
    """Verify resilience when secrets contain Python single-quoted dict strings."""
    python_dict_str = "{'type': 'service_account', 'project_id': 'single-quote-proj', 'client_email': 'test@proj.iam.gserviceaccount.com'}"
    parsed = parse_service_account_content(python_dict_str)
    assert parsed["type"] == "service_account"
    assert parsed["project_id"] == "single-quote-proj"
