"""Regression tests: PipelineService must degrade gracefully on CI runners
without GCP credentials (same contract as AnalyticsService), and the SCD-2
search must never interpolate user input into SQL.
"""
from unittest.mock import MagicMock, patch

import pandas as pd
from google.auth.exceptions import DefaultCredentialsError

import src.utils.gcp_client as gcp
import src.web.services.pipeline_service as svc
from src.web.services.pipeline_service import PipelineService


def _raise_no_credentials(*args, **kwargs):
    raise DefaultCredentialsError("Your default credentials were not found.")


def setup_function():
    svc._PIPE_CACHE.clear()


def test_audit_logs_degrade_to_demo_when_client_construction_fails():
    with patch.object(gcp, "get_bigquery_client", side_effect=_raise_no_credentials):
        res = PipelineService.get_audit_logs(limit=5)
    assert isinstance(res, list) and len(res) > 0
    assert "run_id" in res[0]


def test_scd2_search_degrades_to_demo_when_client_construction_fails():
    with patch.object(gcp, "get_bigquery_client", side_effect=_raise_no_credentials):
        res = PipelineService.search_scd2_orders(query_str="ORD_1", limit=5)
    assert isinstance(res, list)


def test_scd2_search_is_parameterized_not_interpolated():
    """User-supplied search text must reach BigQuery as a bound parameter,
    never spliced into the SQL string (SQL injection guard)."""
    client = MagicMock()
    client.query.return_value.to_dataframe.return_value = pd.DataFrame()
    with patch.object(svc, "get_bigquery_client_or_none", return_value=client):
        PipelineService.search_scd2_orders(query_str="ORD' OR 1=1 --", limit=5)

    sql = client.query.call_args.args[0]
    assert "ORD' OR 1=1" not in sql, "user input must never be interpolated into SQL"
    job_config = client.query.call_args.kwargs["job_config"]
    assert any(
        p.name == "search_pattern" and "ORD' OR 1=1 --" in p.value
        for p in job_config.query_parameters
    )
