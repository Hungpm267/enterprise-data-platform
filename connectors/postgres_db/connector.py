from typing import List
from connectors._base.base_connector import BaseConnector
from connectors._base.schemas import RunArgs
from connectors.postgres_db.extract import extract_postgres_tables

class PostgresConnector(BaseConnector):
    """
    PostgreSQL Source Connector for Enterprise E-Commerce OLTP Database.
    """
    def __init__(self):
        super().__init__(name="postgres_db")

    def extract(self, args: RunArgs) -> List[str]:
        return extract_postgres_tables(args)