import psycopg2
from sqlalchemy import create_engine
from src.utils.config import Config
from src.utils.logger import logger

class PostgresConnector:
    def __init__(self):
        self.db_url = Config.get_db_url()
        self.engine = None

    def get_engine(self):
        if not self.engine:
            logger.info(f"Connecting to PostgreSQL database: {Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}")
            self.engine = create_engine(self.db_url)
        return self.engine

    def get_raw_connection(self):
        return psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            dbname=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )
