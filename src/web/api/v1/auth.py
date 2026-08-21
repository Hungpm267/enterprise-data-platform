from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from src.web.db.session import get_db, init_app_db
from src.web.db.models import User
from src.web.schemas.auth import LoginRequest, TokenResponse, UserOut, RegisterRequest
from src.web.services.auth_service import AuthService
from src.web.core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication & Tenant Management"])

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user with email/password and issue JWT token with tenant claims."""
    return AuthService.login(db, req)

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new SMB Client Tenant and Owner Account."""
    return AuthService.register_client(db, req)

@router.get("/me", response_model=UserOut)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get profile of current authenticated user and tenant information."""
    return AuthService.get_user_profile(current_user)

@router.post("/seed-demo")
def seed_demo_accounts():
    """Initializes App DB and ensures default Admin & SMB Client accounts exist."""
    init_app_db()
    return {
        "status": "success",
        "message": "Demo accounts verified/seeded successfully.",
        "accounts": [
            {"email": "admin@dashgrow.io", "password": "admin123", "role": "platform_admin", "persona": "DashGrow Team (Bên Bán)"},
            {"email": "owner@olist-store.vn", "password": "client123", "role": "client_owner", "persona": "SMB Client (Bên Mua)"}
        ]
    }
