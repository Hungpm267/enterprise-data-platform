from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.web.core.config import WebConfig
from src.web.db.models import Base, Tenant, User, Subscription, LookerDashboard
from src.web.core.security import get_password_hash

database_url = WebConfig.get_database_url()

# For PostgreSQL on Aiven, use connection pool recycling
if "postgresql" in database_url:
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=300
    )
else:
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_app_db():
    """Initializes tables and seeds initial platform users if empty."""
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check Super Admin
        admin_user = db.query(User).filter(User.email == "admin@dashgrow.io").first()
        if not admin_user:
            admin_user = User(
                email="admin@dashgrow.io",
                hashed_password=get_password_hash("admin123"),
                full_name="DashGrow Super Admin",
                role="platform_admin",
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            print("[INFO] Seeded default DashGrow Platform Admin (admin@dashgrow.io) into Aiven DB.")

        # Check Demo Client Tenant
        tenant = db.query(Tenant).filter(Tenant.slug == "olist-retail").first()
        if not tenant:
            tenant = Tenant(
                name="Olist Retail E-Commerce",
                slug="olist-retail",
                industry="E-Commerce & Retail",
                contact_phone="+84 901 234 567",
                status="active"
            )
            db.add(tenant)
            db.commit()
            db.refresh(tenant)

            # Subscription
            sub = Subscription(
                tenant_id=tenant.id,
                plan_tier="growth_pro",
                price_monthly=4490000.00,
                billing_cycle="monthly",
                payment_status="active"
            )
            db.add(sub)

            # Client User
            client_user = User(
                tenant_id=tenant.id,
                email="owner@olist-store.vn",
                hashed_password=get_password_hash("client123"),
                full_name="Nguyễn Văn An",
                role="client_owner",
                is_active=True
            )
            db.add(client_user)

            # Seed Default Looker Dashboards for Olist
            looker_1 = LookerDashboard(
                tenant_id=tenant.id,
                title="Báo Cáo Doanh Thu & P&L Tổng Hợp",
                category="Finance & P&L",
                embed_url="https://lookerstudio.google.com/embed/reporting/3c393ee1-sample-finance/page/p_1",
                is_default=True,
                sort_order=1
            )
            looker_2 = LookerDashboard(
                tenant_id=tenant.id,
                title="Báo Cáo Tồn Kho & Vận Hành Logistics",
                category="Logistics & Operations",
                embed_url="https://lookerstudio.google.com/embed/reporting/3c393ee1-sample-logistics/page/p_2",
                is_default=False,
                sort_order=2
            )
            db.add(looker_1)
            db.add(looker_2)
            db.commit()
            print("[INFO] Seeded default Olist Tenant and Looker Dashboards into Aiven DB.")

    except Exception as e:
        print(f"[WARN] Error during Aiven database auto-seeding: {e}")
        db.rollback()
    finally:
        db.close()
