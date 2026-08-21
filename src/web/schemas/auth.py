from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: str
    role: str
    tenant_id: Optional[str] = None
    tenant_name: Optional[str] = "DashGrow HQ"
    tenant_slug: Optional[str] = "dashgrow-hq"

class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    tenant_id: Optional[str] = None
    tenant_name: Optional[str] = "DashGrow HQ"
    tenant_slug: Optional[str] = "dashgrow-hq"
    tenant_plan: Optional[str] = "growth_pro"
    created_at: Optional[datetime] = None

class RegisterRequest(BaseModel):
    company_name: str
    company_slug: str
    email: str
    password: str
    full_name: str
