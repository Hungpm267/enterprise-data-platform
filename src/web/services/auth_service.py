from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from src.web.db.models import User, Tenant
from src.web.core.security import verify_password, get_password_hash, create_access_token
from src.web.schemas.auth import LoginRequest, TokenResponse, UserOut, RegisterRequest

class AuthService:
    @staticmethod
    def login(db: Session, req: LoginRequest) -> TokenResponse:
        user = db.query(User).filter(User.email == req.email.strip().lower()).first()
        if not user or not verify_password(req.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email hoặc mật khẩu không chính xác."
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản của bạn đã bị tạm khóa."
            )
        
        user_id_str = str(user.id)
        tenant_id_str = str(user.tenant_id) if user.tenant_id else None

        token_payload = {
            "sub": user_id_str,
            "email": user.email,
            "role": user.role,
            "tenant_id": tenant_id_str,
            "tenant_slug": user.tenant.slug if user.tenant else "dashgrow-hq"
        }
        access_token = create_access_token(token_payload)
        
        return TokenResponse(
            access_token=access_token,
            user_id=user_id_str,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            tenant_id=tenant_id_str,
            tenant_name=user.tenant.name if user.tenant else "DashGrow HQ",
            tenant_slug=user.tenant.slug if user.tenant else "dashgrow-hq"
        )

    @staticmethod
    def register_client(db: Session, req: RegisterRequest) -> TokenResponse:
        existing_user = db.query(User).filter(User.email == req.email.strip().lower()).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email này đã được đăng ký trên hệ thống."
            )
        
        tenant = db.query(Tenant).filter(Tenant.slug == req.company_slug.strip().lower()).first()
        if not tenant:
            tenant = Tenant(
                name=req.company_name.strip(),
                slug=req.company_slug.strip().lower()
            )
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
        
        new_user = User(
            tenant_id=tenant.id,
            email=req.email.strip().lower(),
            hashed_password=get_password_hash(req.password),
            full_name=req.full_name.strip(),
            role="client_owner",
            is_active=True
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return AuthService.login(db, LoginRequest(email=req.email, password=req.password))

    @staticmethod
    def get_user_profile(user: User) -> UserOut:
        plan = "growth_pro"
        if user.tenant and user.tenant.subscriptions:
            plan = user.tenant.subscriptions[0].plan_tier

        return UserOut(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            tenant_id=str(user.tenant_id) if user.tenant_id else None,
            tenant_name=user.tenant.name if user.tenant else "DashGrow HQ",
            tenant_slug=user.tenant.slug if user.tenant else "dashgrow-hq",
            tenant_plan=plan,
            created_at=user.created_at
        )
