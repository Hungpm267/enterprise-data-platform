import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DB_HOST = os.getenv("DB_HOST") or "localhost"
    
    _port = os.getenv("DB_PORT")
    DB_PORT = int(_port) if _port and _port.strip().isdigit() else 5432
    
    DB_NAME = os.getenv("DB_NAME") or "postgres"
    DB_USER = os.getenv("DB_USER") or "postgres"
    DB_PASSWORD = os.getenv("DB_PASSWORD") or "postgres"
    DB_SCHEMA = os.getenv("DB_SCHEMA") or "public"
    
    LANDING_DIR = os.getenv("LANDING_DIR") or "data/landing"

    @classmethod
    def get_db_url(cls) -> str:
        ssl_param = "?sslmode=require" if ("aivencloud.com" in cls.DB_HOST or "cockroachlabs.cloud" in cls.DB_HOST) else ""
        return f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}{ssl_param}"
