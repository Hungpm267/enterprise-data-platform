"""Regression tests for CI runners without GCP credentials.

On GitHub Actions there is no gcp_key.json and no Application Default
Credentials, so constructing a BigQuery client raises DefaultCredentialsError
at the constructor — before AnalyticsService's try/except around the query
can catch anything. The service is designed to degrade to demo data when
BigQuery is unavailable; these tests pin that behaviour for client
construction failures, not just query failures.
"""
from unittest.mock import patch

from google.auth.exceptions import DefaultCredentialsError

import src.utils.gcp_client as gcp
import src.web.services.analytics_service as svc
from src.web.services.analytics_service import AnalyticsService


def _raise_no_credentials():
    raise DefaultCredentialsError("Your default credentials were not found.")


def setup_function():
    svc._MEMORY_CACHE.clear()


def test_get_kpis_degrades_to_demo_when_client_construction_fails():
    with patch.object(gcp, "get_bigquery_client", side_effect=_raise_no_credentials):
        res = AnalyticsService.get_kpis("tenant_ci")
    assert res["data_source"] == "cached_demo"
    assert res["total_orders"] > 0


def test_revenue_trend_degrades_to_demo_when_client_construction_fails():
    with patch.object(gcp, "get_bigquery_client", side_effect=_raise_no_credentials):
        res = AnalyticsService.get_revenue_trend("tenant_ci")
    assert len(res["labels"]) == len(res["revenue"])


def test_crypto_summary_degrades_to_demo_when_client_construction_fails():
    with patch.object(gcp, "get_bigquery_client", side_effect=_raise_no_credentials):
        res = AnalyticsService.get_crypto_market_summary()
    assert isinstance(res, list) and len(res) > 0
