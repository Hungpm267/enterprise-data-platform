from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr

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
    tenant_id: str
    tenant_name: str
    tenant_slug: str

class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    tenant_id: str
    tenant_name: str
    tenant_slug: str
    tenant_plan: str
    created_at: Optional[datetime] = None

class RegisterRequest(BaseModel):
    company_name: str
    company_slug: str
    email: str
    password: str
    full_name: str
