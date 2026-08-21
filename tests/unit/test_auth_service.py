import pytest
from fastapi import HTTPException
from src.web.db.session import init_app_db, SessionLocal
from src.web.services.auth_service import AuthService
from src.web.schemas.auth import LoginRequest, RegisterRequest

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    init_app_db()

def test_auth_login_admin_success():
    db = SessionLocal()
    try:
        req = LoginRequest(email="admin@dashgrow.io", password="admin123")
        res = AuthService.login(db, req)
        assert res.role == "platform_admin"
        assert res.access_token is not None
        assert res.tenant_slug == "dashgrow-hq"
    finally:
        db.close()

def test_auth_login_client_success():
    db = SessionLocal()
    try:
        req = LoginRequest(email="owner@olist-store.vn", password="client123")
        res = AuthService.login(db, req)
        assert res.role == "client_owner"
        assert res.tenant_slug == "olist-retail"
    finally:
        db.close()

def test_auth_login_invalid_password():
    db = SessionLocal()
    try:
        req = LoginRequest(email="admin@dashgrow.io", password="wrongpassword")
        with pytest.raises(HTTPException) as exc_info:
            AuthService.login(db, req)
        assert exc_info.value.status_code == 401
    finally:
        db.close()
