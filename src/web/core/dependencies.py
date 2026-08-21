from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src.web.db.session import get_db
from src.web.db.models import User
from src.web.core.security import decode_access_token

security_bearer = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
    db: Session = Depends(get_db)
) -> User:
    """Validates JWT bearer token and injects current user with tenant relationship."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or Expired Authentication Token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload["sub"]
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

def require_platform_admin(current_user: User = Depends(get_current_user)) -> User:
    """Ensures caller has DashGrow Platform Admin permissions (Bên Bán)."""
    if current_user.role != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: DashGrow Platform Super Admin role required",
        )
    return current_user
