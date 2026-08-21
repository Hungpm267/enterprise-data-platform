import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.web.core.config import WebConfig
from src.web.db.models import Base, Tenant, User
from src.web.core.security import get_password_hash

engine = create_engine(
    WebConfig.APP_DB_URL,
    connect_args={"check_same_thread": False} if "sqlite" in WebConfig.APP_DB_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """FastAPI Dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_app_db():
    """Initializes tables and seeds default DashGrow platform admin and SMB client demo users."""
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    try:
        # Seed Tenant 1: DashGrow Platform HQ (Admin)
        dg_tenant = db.query(Tenant).filter(Tenant.slug == "dashgrow-hq").first()
        if not dg_tenant:
            dg_tenant = Tenant(
                id="tenant_dashgrow_hq",
                name="DashGrow Technologies HQ",
                slug="dashgrow-hq",
                plan="enterprise",
                industry="Data-as-a-Service Platform"
            )
            db.add(dg_tenant)
            db.commit()

        # Seed Tenant 2: Olist Store SMB Client (E-Commerce Client)
        olist_tenant = db.query(Tenant).filter(Tenant.slug == "olist-retail").first()
        if not olist_tenant:
            olist_tenant = Tenant(
                id="tenant_olist_retail",
                name="Olist Retail E-Commerce",
                slug="olist-retail",
                plan="growth_pro",
                industry="E-Commerce & Retail"
            )
            db.add(olist_tenant)
            db.commit()

        # Seed User 1: DashGrow Platform Super Admin (Bên Bán)
        admin_user = db.query(User).filter(User.email == "admin@dashgrow.io").first()
        if not admin_user:
            admin_user = User(
                id="user_admin_dg",
                tenant_id=dg_tenant.id,
                email="admin@dashgrow.io",
                hashed_password=get_password_hash("admin123"),
                full_name="DashGrow Lead Engineer",
                role="platform_admin",
                is_active=True
            )
            db.add(admin_user)

        # Seed User 2: SMB Client Owner (Bên Mua - Chủ Shop)
        client_user = db.query(User).filter(User.email == "owner@olist-store.vn").first()
        if not client_user:
            client_user = User(
                id="user_client_olist",
                tenant_id=olist_tenant.id,
                email="owner@olist-store.vn",
                hashed_password=get_password_hash("client123"),
                full_name="Nguyễn Văn An (Chủ Chuỗi Olist)",
                role="client_owner",
                is_active=True
            )
            db.add(client_user)

        db.commit()
    finally:
        db.close()
