from typing import Optional
from fastapi import APIRouter, Depends, Query
from src.web.core.dependencies import get_current_user
from src.web.db.models import User
from src.web.services.pipeline_service import PipelineService

router = APIRouter(prefix="/explorer", tags=["Data Observability & SCD Type 2 Explorer"])

@router.get("/audit-logs")
def get_audit_logs(
    limit: int = Query(15, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Retrieve audit history records from BigQuery _pipeline_audit_log."""
    return PipelineService.get_audit_logs(limit=limit)

@router.get("/scd2/orders")
def search_scd2_orders(
    query: Optional[str] = Query(None, description="Search by order_id or customer_id"),
    limit: int = Query(15, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Search and inspect SCD Type 2 order history with valid_from/to intervals."""
    return PipelineService.search_scd2_orders(query_str=query, limit=limit)

@router.get("/quality-tests")
def get_quality_tests(current_user: User = Depends(get_current_user)):
    """Retrieve summary of 35 dbt Data Quality test suite."""
    return PipelineService.get_quality_test_summary()
