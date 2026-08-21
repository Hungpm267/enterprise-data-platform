from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.web.db.session import get_db
from src.web.db.models import User, Tenant, Subscription
from src.web.core.dependencies import require_platform_admin
from src.web.core.security import get_password_hash
from src.web.schemas.auth import RegisterRequest, UserOut
from pydantic import BaseModel

class CreateUserTenantRequest(BaseModel):
    company_name: str
    company_slug: str
    plan: str = "growth_pro"  # starter, growth_pro, enterprise
    industry: str = "Retail & E-Commerce"
    full_name: str
    email: str
    password: str
    role: str = "client_owner"

class ToggleStatusRequest(BaseModel):
    is_active: bool

router = APIRouter(prefix="/users", tags=["Admin User & Tenant Management"])

@router.get("", response_model=List[UserOut])
def list_all_users(
    admin_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db)
):
    """Retrieve all users across all tenants (Admin only)."""
    users = db.query(User).all()
    results = []
    for u in users:
        plan = "growth_pro"
        if u.tenant and u.tenant.subscriptions:
            plan = u.tenant.subscriptions[0].plan_tier

        results.append(UserOut(
            id=str(u.id),
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            is_active=u.is_active,
            tenant_id=str(u.tenant_id) if u.tenant_id else None,
            tenant_name=u.tenant.name if u.tenant else "DashGrow HQ",
            tenant_slug=u.tenant.slug if u.tenant else "dashgrow-hq",
            tenant_plan=plan,
            created_at=u.created_at
        ))
    return results

@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_tenant_and_user(
    req: CreateUserTenantRequest,
    admin_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db)
):
    """Admin creates a new client company (tenant) and provisions an owner account."""
    existing = db.query(User).filter(User.email == req.email.strip().lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email này đã tồn tại trên hệ thống.")

    # Find or create tenant
    tenant = db.query(Tenant).filter(Tenant.slug == req.company_slug.strip().lower()).first()
    if not tenant:
        tenant = Tenant(
            name=req.company_name.strip(),
            slug=req.company_slug.strip().lower(),
            industry=req.industry
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

        # Create subscription
        price = 1990000.00 if req.plan == "starter" else 8990000.00 if req.plan == "enterprise" else 4490000.00
        sub = Subscription(
            tenant_id=tenant.id,
            plan_tier=req.plan,
            price_monthly=price,
            billing_cycle="monthly",
            payment_status="active"
        )
        db.add(sub)
        db.commit()

    new_user = User(
        tenant_id=tenant.id,
        email=req.email.strip().lower(),
        hashed_password=get_password_hash(req.password),
        full_name=req.full_name.strip(),
        role=req.role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserOut(
        id=str(new_user.id),
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role,
        is_active=new_user.is_active,
        tenant_id=str(tenant.id),
        tenant_name=tenant.name,
        tenant_slug=tenant.slug,
        tenant_plan=req.plan,
        created_at=new_user.created_at
    )

@router.put("/{user_id}/status")
def toggle_user_status(
    user_id: str,
    req: ToggleStatusRequest,
    admin_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db)
):
    """Lock or unlock a user account (Admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User không tồn tại.")
    if str(user.id) == str(admin_user.id):
        raise HTTPException(status_code=400, detail="Không thể tự khóa tài khoản Admin của chính bạn.")

    user.is_active = req.is_active
    db.commit()
    return {"status": "success", "message": f"Tài khoản {user.email} đã được {'kích hoạt' if req.is_active else 'khóa'}."}

@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    admin_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db)
):
    """Delete a user account (Admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User không tồn tại.")
    if str(user.id) == str(admin_user.id):
        raise HTTPException(status_code=400, detail="Không thể xóa tài khoản Admin của chính bạn.")

    db.delete(user)
    db.commit()
    return {"status": "success", "message": f"Đã xóa vĩnh viễn tài khoản {user.email}."}
