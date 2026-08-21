from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.web.db.session import get_db
from src.web.db.models import LookerDashboard, Tenant, User
from src.web.core.dependencies import get_current_user, require_platform_admin
from pydantic import BaseModel

def normalize_looker_url(url: str) -> str:
    """Ensures Looker Studio URLs always have the /embed/ path."""
    clean = url.strip()
    if "lookerstudio.google.com/reporting/" in clean and "/embed/" not in clean:
        clean = clean.replace("lookerstudio.google.com/reporting/", "lookerstudio.google.com/embed/reporting/")
    elif "datastudio.google.com/reporting/" in clean and "/embed/" not in clean:
        clean = clean.replace("datastudio.google.com/reporting/", "datastudio.google.com/embed/reporting/")
    return clean

class LookerDashboardOut(BaseModel):
    id: str
    tenant_id: str
    title: str
    category: str
    embed_url: str
    is_default: bool
    sort_order: int

class CreateLookerDashboardRequest(BaseModel):
    title: str
    category: str = "Finance & P&L"
    embed_url: str
    is_default: bool = False
    sort_order: int = 1

router = APIRouter(prefix="/looker", tags=["Looker Studio Embedding"])

@router.get("/my-dashboards", response_model=List[LookerDashboardOut])
def get_my_dashboards(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve Looker Studio dashboards assigned to current user's tenant."""
    if not current_user.tenant_id:
        dashboards = db.query(LookerDashboard).order_by(LookerDashboard.sort_order).all()
    else:
        dashboards = db.query(LookerDashboard).filter(
            LookerDashboard.tenant_id == current_user.tenant_id
        ).order_by(LookerDashboard.sort_order).all()

    return [
        LookerDashboardOut(
            id=str(d.id),
            tenant_id=str(d.tenant_id),
            title=d.title,
            category=d.category or "General",
            embed_url=normalize_looker_url(d.embed_url),
            is_default=d.is_default,
            sort_order=d.sort_order
        ) for d in dashboards
    ]

@router.post("/tenants/{tenant_id}", response_model=LookerDashboardOut, status_code=status.HTTP_201_CREATED)
def assign_looker_dashboard(
    tenant_id: str,
    req: CreateLookerDashboardRequest,
    admin_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db)
):
    """Admin assigns a new Looker Studio Embed URL to a client tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant không tồn tại.")

    normalized_url = normalize_looker_url(req.embed_url)

    new_dash = LookerDashboard(
        tenant_id=tenant.id,
        title=req.title.strip(),
        category=req.category.strip(),
        embed_url=normalized_url,
        is_default=req.is_default,
        sort_order=req.sort_order
    )
    db.add(new_dash)
    db.commit()
    db.refresh(new_dash)

    return LookerDashboardOut(
        id=str(new_dash.id),
        tenant_id=str(new_dash.tenant_id),
        title=new_dash.title,
        category=new_dash.category,
        embed_url=new_dash.embed_url,
        is_default=new_dash.is_default,
        sort_order=new_dash.sort_order
    )

@router.delete("/{dashboard_id}")
def remove_looker_dashboard(
    dashboard_id: str,
    admin_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db)
):
    """Admin removes a Looker Studio Dashboard from a tenant."""
    dash = db.query(LookerDashboard).filter(LookerDashboard.id == dashboard_id).first()
    if not dash:
        raise HTTPException(status_code=404, detail="Dashboard không tồn tại.")

    db.delete(dash)
    db.commit()
    return {"status": "success", "message": "Đã gỡ bỏ Looker Dashboard."}
