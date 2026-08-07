import sys
import os
from datetime import datetime, timedelta

# Ensure src modules are resolvable by Airflow
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from airflow import DAG
from airflow.operators.python import PythonOperator

from src.extract.extract_db import extract_all_tables
from src.load.load_to_dw import load_landing_to_dw
from src.transform.run_transform import run_in_warehouse_transformations

default_args = {
    'owner': 'data_engineer',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='elt_ecommerce_pipeline',
    default_args=default_args,
    description='Pipeline ELT tu dong cho eCommerce Postgres Data Warehouse',
    schedule_interval='0 2 * * *',  # Chay vao 02:00 sáng mỗi ngày
    catchup=False,
    tags=['elt', 'ecommerce', 'postgres'],
) as dag:

    extract_task = PythonOperator(
        task_id='extract_raw_tables',
        python_callable=extract_all_tables,
    )

    load_task = PythonOperator(
        task_id='load_to_dw_staging',
        python_callable=load_landing_to_dw,
    )

    transform_task = PythonOperator(
        task_id='transform_to_marts',
        python_callable=run_in_warehouse_transformations,
    )

    # Airflow task dependency chain
    extract_task >> load_task >> transform_task
