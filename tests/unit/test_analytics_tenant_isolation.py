from unittest.mock import MagicMock, patch

import pandas as pd

import src.web.services.analytics_service as svc
from src.web.services.analytics_service import AnalyticsService


def _fake_client(rows: pd.DataFrame):
    client = MagicMock()
    client.query.return_value.to_dataframe.return_value = rows
    return client


def _kpi_rows(revenue):
    return pd.DataFrame([{
        "total_revenue": revenue,
        "total_orders": 10,
        "aov": revenue / 10,
        "delivery_success_rate": 90.0,
    }])


def setup_function():
    svc._MEMORY_CACHE.clear()


def test_tenant_query_is_parameterized_not_interpolated():
    client = _fake_client(_kpi_rows(1000.0))
    with patch.object(svc, "get_bigquery_client", return_value=client):
        AnalyticsService.get_kpis("acme-coffee")

    sql = client.query.call_args.args[0]
    job_config = client.query.call_args.kwargs["job_config"]
    assert "acme-coffee" not in sql, "tenant value must never be interpolated into SQL"
    assert "@tenant_slug" in sql
    assert job_config.query_parameters[0].value == "acme-coffee"


def test_admin_none_tenant_runs_unfiltered_query():
    client = _fake_client(_kpi_rows(9999.0))
    with patch.object(svc, "get_bigquery_client", return_value=client):
        AnalyticsService.get_kpis(None)

    sql = client.query.call_args.args[0]
    assert "@tenant_slug" not in sql


def test_two_tenants_get_distinct_results():
    with patch.object(svc, "get_bigquery_client", return_value=_fake_client(_kpi_rows(1000.0))):
        first = AnalyticsService.get_kpis("tenant-a")
    with patch.object(svc, "get_bigquery_client", return_value=_fake_client(_kpi_rows(5000.0))):
        second = AnalyticsService.get_kpis("tenant-b")

    assert first["total_revenue"] == 1000.0
    assert second["total_revenue"] == 5000.0
