import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Numeric, Integer, Text, Date
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    industry = Column(String(100), default="Retail & E-Commerce")
    contact_phone = Column(String(50), nullable=True)
    contact_email = Column(String(255), nullable=True)
    website_url = Column(String(255), nullable=True)
    status = Column(String(50), default="active", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="tenant", cascade="all, delete-orphan")
    dashboards = relationship("LookerDashboard", back_populates="tenant", cascade="all, delete-orphan")

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_tier = Column(String(50), nullable=False, default="growth_pro")
    price_monthly = Column(Numeric(15, 2), nullable=False, default=4490000.00)
    billing_cycle = Column(String(20), default="monthly")
    start_date = Column(Date, default=datetime.utcnow)
    next_billing_date = Column(Date, nullable=True)
    payment_status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="subscriptions")

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="client_owner")
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="users")

class LookerDashboard(Base):
    __tablename__ = "looker_dashboards"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    category = Column(String(100), default="Finance & Operations")
    embed_url = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False)
    sort_order = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="dashboards")

class PipelineAuditLog(Base):
    __tablename__ = "pipeline_audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True)
    run_id = Column(String(100), nullable=False, index=True)
    connector_name = Column(String(100), nullable=False)
    run_mode = Column(String(50), default="incremental")
    status = Column(String(50), nullable=False)
    records_extracted = Column(Integer, default=0)
    duration_sec = Column(Numeric(10, 2), default=0.0)
    error_message = Column(Text, nullable=True)
    executed_at = Column(DateTime, default=datetime.utcnow, index=True)
