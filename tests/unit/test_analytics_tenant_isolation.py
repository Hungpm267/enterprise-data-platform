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
    with patch.object(svc, "get_bigquery_client_or_none", return_value=client):
        AnalyticsService.get_kpis("acme-coffee")

    sql = client.query.call_args.args[0]
    job_config = client.query.call_args.kwargs["job_config"]
    assert "acme-coffee" not in sql, "tenant value must never be interpolated into SQL"
    assert "@tenant_slug" in sql
    assert job_config.query_parameters[0].value == "acme-coffee"


def test_admin_none_tenant_runs_unfiltered_query():
    client = _fake_client(_kpi_rows(9999.0))
    with patch.object(svc, "get_bigquery_client_or_none", return_value=client):
        AnalyticsService.get_kpis(None)

    sql = client.query.call_args.args[0]
    assert "@tenant_slug" not in sql


def test_two_tenants_get_distinct_results():
    with patch.object(svc, "get_bigquery_client_or_none", return_value=_fake_client(_kpi_rows(1000.0))):
        first = AnalyticsService.get_kpis("tenant-a")
    with patch.object(svc, "get_bigquery_client_or_none", return_value=_fake_client(_kpi_rows(5000.0))):
        second = AnalyticsService.get_kpis("tenant-b")

    assert first["total_revenue"] == 1000.0
    assert second["total_revenue"] == 5000.0


def test_empty_string_tenant_does_not_share_cache_with_admin():
    """
    Regression guard for the exploit chain surfaced by the re-review: a
    company_slug of only whitespace can (pre-fix, at the schema layer) yield
    a real tenant row with slug="". Even with the SQL predicate fixed
    (_tenant_clause / _tenant_job_config), the in-memory cache keys used
    `tenant_slug or 'ALL'`, which put an empty-string caller on the exact
    same cache entry as a platform admin's unfiltered ('ALL' / None) query.
    Prime the cache as admin, then call as "" and assert the empty-string
    caller does NOT receive the admin's cross-tenant payload.
    """
    admin_client = _fake_client(_kpi_rows(999999.0))
    with patch.object(svc, "get_bigquery_client_or_none", return_value=admin_client):
        admin_result = AnalyticsService.get_kpis(None)
    assert admin_result["total_revenue"] == 999999.0

    # A second, distinct BigQuery response for the empty-string tenant. If
    # the empty-string caller shares the admin's cache key, this client is
    # never even queried and the stale admin payload leaks through instead.
    empty_tenant_client = _fake_client(_kpi_rows(0.0))
    with patch.object(svc, "get_bigquery_client_or_none", return_value=empty_tenant_client):
        empty_tenant_result = AnalyticsService.get_kpis("")

    assert empty_tenant_result["total_revenue"] != admin_result["total_revenue"], (
        "empty-string tenant must not receive the platform admin's cached, "
        "cross-tenant payload"
    )


def test_empty_string_tenant_slug_produces_a_filter_not_unfiltered_access():
    # An empty string must NOT be treated like None (admin/unfiltered). It
    # must still bind a tenant_slug filter parameter (yielding zero rows for
    # a slug no tenant has), never fall through to an unfiltered query.
    assert svc._tenant_clause("") == " WHERE tenant_slug = @tenant_slug"
    assert svc._tenant_clause(None) == ""

    job_config = svc._tenant_job_config("")
    assert job_config.query_parameters[0].value == ""

    admin_job_config = svc._tenant_job_config(None)
    assert admin_job_config.query_parameters == []
