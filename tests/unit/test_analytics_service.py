from src.web.services.analytics_service import AnalyticsService

def test_get_kpis_structure():
    res = AnalyticsService.get_kpis("tenant_123")
    assert "total_revenue" in res
    assert "total_orders" in res
    assert "aov" in res
    assert "delivery_success_rate" in res
    assert res["total_revenue"] > 0

def test_get_revenue_trend_structure():
    res = AnalyticsService.get_revenue_trend("tenant_123")
    assert "labels" in res
    assert "revenue" in res
    assert len(res["labels"]) == len(res["revenue"])

def test_get_crypto_market_summary():
    res = AnalyticsService.get_crypto_market_summary()
    assert isinstance(res, list)
    assert len(res) > 0
    assert "symbol" in res[0]
    assert "price" in res[0]
