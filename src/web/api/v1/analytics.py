from fastapi import APIRouter, Depends
from src.web.core.dependencies import get_current_user
from src.web.db.models import User
from src.web.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Executive Analytics & Business Intelligence"])

@router.get("/kpis")
def get_kpis(current_user: User = Depends(get_current_user)):
    """Fetch high-level business KPIs for the active tenant."""
    return AnalyticsService.get_kpis(current_user.tenant_id)

@router.get("/revenue-trend")
def get_revenue_trend(current_user: User = Depends(get_current_user)):
    """Fetch revenue timeline trends for Chart.js line charts."""
    return AnalyticsService.get_revenue_trend(current_user.tenant_id)

@router.get("/order-status")
def get_order_status(current_user: User = Depends(get_current_user)):
    """Fetch order status distribution for donut charts."""
    return AnalyticsService.get_order_status_distribution(current_user.tenant_id)

@router.get("/top-categories")
def get_top_categories(current_user: User = Depends(get_current_user)):
    """Fetch top product categories by volume."""
    return AnalyticsService.get_top_categories(current_user.tenant_id)

@router.get("/crypto-market")
def get_crypto_market(current_user: User = Depends(get_current_user)):
    """Fetch real-time market coin metrics from crypto staging dataset."""
    return AnalyticsService.get_crypto_market_summary()
