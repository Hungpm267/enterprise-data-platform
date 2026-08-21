from src.web.core.security import get_password_hash, verify_password, create_access_token, decode_access_token
from src.web.db.session import init_app_db, SessionLocal
from src.web.db.models import User, Tenant

def test_password_hashing_and_verification():
    raw = "super_secure_pass_2026"
    hashed = get_password_hash(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("wrong_pass", hashed) is False

def test_jwt_token_encoding_and_decoding():
    payload = {"sub": "user_123", "role": "client_owner", "tenant_id": "tenant_abc"}
    token = create_access_token(payload)
    assert isinstance(token, str)
    
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user_123"
    assert decoded["role"] == "client_owner"
    assert decoded["tenant_id"] == "tenant_abc"

def test_app_db_initialization_and_seeding():
    init_app_db()
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@dashgrow.io").first()
        assert admin is not None
        assert admin.role == "platform_admin"
        assert admin.tenant is not None
        
        client = db.query(User).filter(User.email == "owner@olist-store.vn").first()
        assert client is not None
        assert client.role == "client_owner"
        assert client.tenant.slug == "olist-retail"
    finally:
        db.close()
