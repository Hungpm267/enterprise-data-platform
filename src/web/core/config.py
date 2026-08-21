import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

class WebConfig:
    PROJECT_NAME: str = "DashGrow Enterprise Data Portal"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    
    # JWT Authentication Secrets
    SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dashgrow_super_secret_production_key_2026_dg_ai_data")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dashgrow_super_secret_production_key_2026_dg_ai_data")
    ALGORITHM: str = "HS256"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 Days

    # Aiven.io Production PostgreSQL App Database
    APP_DB_HOST = os.getenv("APP_DB_HOST")
    APP_DB_PORT = os.getenv("APP_DB_PORT", "24878")
    APP_DB_NAME = os.getenv("APP_DB_NAME", "dashgrow_app_db")
    APP_DB_USER = os.getenv("APP_DB_USER", "avnadmin")
    APP_DB_PASSWORD = os.getenv("APP_DB_PASSWORD")
    APP_DB_SSL_MODE = os.getenv("APP_DB_SSL_MODE", "require")

    @classmethod
    def get_database_url(cls) -> str:
        if cls.APP_DB_HOST and cls.APP_DB_USER and cls.APP_DB_PASSWORD:
            encoded_password = quote_plus(cls.APP_DB_PASSWORD)
            return f"postgresql+psycopg2://{cls.APP_DB_USER}:{encoded_password}@{cls.APP_DB_HOST}:{cls.APP_DB_PORT}/{cls.APP_DB_NAME}?sslmode={cls.APP_DB_SSL_MODE}"
        
        # Fallback to local SQLite if Aiven is not configured
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return f"sqlite:///{os.path.join(base_dir, 'dashgrow_app.db')}"
