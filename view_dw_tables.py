import sys
import pandas as pd
from sqlalchemy import text

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from src.utils.db_connector import PostgresConnector

def inspect_dw():
    connector = PostgresConnector()
    engine = connector.get_engine()

    print("\n=======================================================")
    print(" DATA WAREHOUSE INSPECTOR (Kiem tra Schemas & Tables)")
    print("=======================================================\n")

    with engine.connect() as conn:
        # List tables in staging schema
        staging_tables = conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'staging';"
        )).fetchall()
        print("SCHEMA 'staging' (Du lieu nap tho vao Data Warehouse):")
        for row in staging_tables:
            count = conn.execute(text(f"SELECT COUNT(*) FROM staging.{row[0]}")).scalar()
            print(f"   - staging.{row[0]} ({count} rows)")

        print("\n-------------------------------------------------------")
        
        # List tables in marts schema
        marts_tables = conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'marts';"
        )).fetchall()
        print("SCHEMA 'marts' (Bang Fact & Dimension cho Bao cao/PowerBI):")
        for row in marts_tables:
            count = conn.execute(text(f"SELECT COUNT(*) FROM marts.{row[0]}")).scalar()
            print(f"   - marts.{row[0]} ({count} rows)")

        print("\n=======================================================")
        print(" XEM THU NOI DUNG BANG FACT & DIM (Preview Top 5 rows)")
        print("=======================================================\n")

        for row in marts_tables:
            table_name = row[0]
            print(f"--- Bang: marts.{table_name} ---")
            df = pd.read_sql(text(f"SELECT * FROM marts.{table_name} LIMIT 5;"), con=conn)
            print(df.to_string(index=False))
            print("\n")

if __name__ == "__main__":
    inspect_dw()
