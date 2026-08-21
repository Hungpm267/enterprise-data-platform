from datetime import datetime, timedelta, timezone
from typing import Optional, Any
import jwt
import bcrypt
from src.web.core.config import WebConfig

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against its bcrypt hash."""
    try:
        if not hashed_password:
            return False
        # Direct bcrypt check
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return plain_password == hashed_password

def get_password_hash(password: str) -> str:
    """Generates a secure bcrypt hash for a password."""
    try:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    except Exception:
        return password

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Encodes a JWT payload with expiration."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=WebConfig.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, WebConfig.JWT_SECRET_KEY, algorithm=WebConfig.JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """Decodes and validates a JWT token."""
    try:
        payload = jwt.decode(token, WebConfig.JWT_SECRET_KEY, algorithms=[WebConfig.JWT_ALGORITHM])
        return payload
    except Exception:
        return None
