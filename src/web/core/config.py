import os
from dotenv import load_dotenv

load_dotenv()

class WebConfig:
    PROJECT_NAME: str = "DashGrow Multi-Tenant Enterprise Data Portal"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # JWT Security Configuration
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dashgrow-super-secret-key-2026-production-grade")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # App Metadata Database (SQLite for portable zero-config dev/demo, or Postgres URI)
    APP_DB_URL: str = os.getenv("APP_DB_URL", "sqlite:///./dashgrow_metadata.db")
