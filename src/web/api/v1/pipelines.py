from fastapi import APIRouter, Depends, Body
from src.web.core.dependencies import get_current_user, require_platform_admin
from src.web.db.models import User
from src.web.services.pipeline_service import PipelineService
from pydantic import BaseModel

class TriggerRequest(BaseModel):
    connector: str = "postgres_db"  # postgres_db, crypto_api, all
    full_refresh: bool = False

router = APIRouter(prefix="/pipelines", tags=["Pipeline Operations & Orchestration"])

@router.post("/trigger")
def trigger_pipeline(
    req: TriggerRequest,
    admin_user: User = Depends(require_platform_admin)
):
    """Trigger background pipeline execution. Requires Platform Super Admin permissions."""
    return PipelineService.trigger_pipeline_async(
        connector=req.connector,
        full_refresh=req.full_refresh
    )

@router.get("/status")
def get_pipeline_status(current_user: User = Depends(get_current_user)):
    """Fetch current execution status and live terminal logs stream."""
    return PipelineService.get_execution_status()
