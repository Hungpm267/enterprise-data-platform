import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from src.utils.config import Config
from src.utils.logger import logger

class PostgresConnector:
    """
    Singleton Database Connector with NullPool to prevent connection leaks
    and connection slot exhaustion on cloud PostgreSQL instances.
    """
    _engine = None

    def __init__(self):
        self.db_url = Config.get_db_url()

    def get_engine(self):
        if PostgresConnector._engine is None:
            logger.info(f"Initializing connection to PostgreSQL database: {Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}")
            PostgresConnector._engine = create_engine(
                self.db_url,
                poolclass=NullPool,  # Closes connections immediately after use to prevent pool bloat
                connect_args={
                    "connect_timeout": 15,
                    "application_name": "enterprise_data_platform_elt"
                }
            )
        return PostgresConnector._engine

    def get_raw_connection(self):
        return psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            dbname=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            connect_timeout=15
        )

    def close(self):
        if PostgresConnector._engine is not None:
            try:
                PostgresConnector._engine.dispose()
                logger.info("PostgreSQL engine connections disposed cleanly.")
            except Exception as e:
                logger.warning(f"Error disposing engine: {e}")
            PostgresConnector._engine = None
