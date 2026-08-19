import os
import json
import pandas as pd
from typing import Dict, Any, List, Tuple

METRICS_FILE = "data/pipeline_metrics.json"

def record_pipeline_metrics(
    connector_name: str,
    status: str,
    duration_sec: float,
    tables_count: int = 0,
    rows_count: int = 0,
    error_msg: str = None
):
    """
    Persists execution metrics (status, duration, row count, table count) for a connector run.
    """
    os.makedirs("data", exist_ok=True)
    metrics = {}
    if os.path.exists(METRICS_FILE):
        try:
            with open(METRICS_FILE, "r", encoding="utf-8") as f:
                metrics = json.load(f)
        except Exception:
            metrics = {}

    metrics[connector_name] = {
        "status": status,
        "duration_sec": round(duration_sec, 1),
        "tables_count": tables_count,
        "rows_count": rows_count,
        "error_msg": str(error_msg) if error_msg else None
    }

    with open(METRICS_FILE, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

def calculate_extracted_rows(extracted_files: List[str]) -> Tuple[int, int]:
    """
    Returns (tables_count, total_rows_count) from extracted Parquet files.
    """
    tables_count = len(extracted_files)
    rows_count = 0
    for f in extracted_files:
        if os.path.exists(f):
            try:
                df = pd.read_parquet(f)
                rows_count += len(df)
            except Exception:
                pass
    return tables_count, rows_count
